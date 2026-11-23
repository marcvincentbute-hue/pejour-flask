"""Optional CLI import, never a web route. Original MySQL is read-only and unchanged."""
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime,timezone
import base64
from psycopg.types.json import Jsonb

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pejour import create_app
from pejour.db import connection,execute,one
from pejour.security import decrypt

def timestamp(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc) if value else None

def migrate(path):
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if data.get('format')!='pejour-mysql-v1': raise RuntimeError('Unsupported export format.')
    app=create_app()
    if data['encryption_key']!=app.config['ENCRYPTION_KEY']:
        raise RuntimeError('Encryption keys differ. Copy the original key into the NEW .env before importing. Do not rotate it.')
    tables=data['tables']
    with app.app_context():
        # Empty destination only: no merges, deletes or overwrites.
        if any(one(query)['n'] for query in ['SELECT count(*) AS n FROM users','SELECT count(*) AS n FROM activity_log','SELECT count(*) AS n FROM journal_entries','SELECT count(*) AS n FROM otps','SELECT count(*) AS n FROM web_sessions','SELECT count(*) AS n FROM security_flags','SELECT count(*) AS n FROM ip_blocks','SELECT count(*) AS n FROM attempt_state']):
            raise RuntimeError('Destination is not empty. Create a new destination database; no existing data was changed.')
        profile_fields=['first_name','middle_name','family_name','name_extension','birthdate','street','barangay','city','province','country','zip_code','display_name','journal_start','writing_goal']
        names={}
        for user in tables['users']:
            uid=user['id']; names[hashlib.sha256(user['username'].lower().encode()).hexdigest()]=user['username'].lower()
            # Verify authentication tag before saving any data.
            decrypt(user['intention_cipher'],uid+':intention')
            profile={key:(user.get(key) or '') for key in profile_fields}
            execute('INSERT INTO users(id,username,email,password_hash,role,verified,version,profile,intention,consent_at,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(uid,user['username'],user['email'].lower(),user['password_hash'],user['role'],bool(user['email_verified_at']),user.get('session_version',1),Jsonb(profile),user['intention_cipher'],timestamp(user['consent_at']),timestamp(user['created_at'])))
            execute('INSERT INTO attempt_state(username,failures,locked_until) VALUES(%s,%s,%s)',(user['username'].lower(),user.get('failed_attempts',0),timestamp(user.get('locked_until'))))
        for row in tables['security_answers']:
            execute('INSERT INTO security_answers(user_id,question,answer_hash) VALUES(%s,%s,%s)',(row['user_id'],row['question_number'],row['answer_hash']))
        for row in tables['password_history']:
            execute('INSERT INTO password_history(id,user_id,password_hash,created_at) VALUES(%s,%s,%s,%s)',(row['id'],row['user_id'],row['password_hash'],timestamp(row['created_at'])))
        for row in tables['activity_log']:
            name=row.get('username_typed') or ''
            names[hashlib.sha256(name.lower().encode()).hexdigest()]=name.lower()
            execute('INSERT INTO activity_log(id,event_type,username_typed,user_id,ip_address,user_agent,details,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',(row['id'],row['event_type'],name,row.get('user_id'),row['ip_address'],row['user_agent'],row.get('details') or '',timestamp(row['created_at'])))
        for row in tables.get('login_attempt_state',[]):
            name=names.get(row['username_key'])
            if name:
                execute('INSERT INTO attempt_state(username,failures,locked_until) VALUES(%s,%s,%s) ON CONFLICT(username) DO UPDATE SET failures=greatest(attempt_state.failures,EXCLUDED.failures),locked_until=greatest(attempt_state.locked_until,EXCLUDED.locked_until)',(name,row['failures'],timestamp(row.get('locked_until'))))
        for row in tables['otps']:
            # Imported OTPs deliberately expire/cancel; sessions are never migrated.
            execute('INSERT INTO otps(id,user_id,purpose,code_hash,expires_at,attempts,used,is_resend,created_at) VALUES(%s,%s,%s,%s,%s,%s,true,%s,%s)',(row['id'],row['user_id'],row['purpose'],row['code_hash'],timestamp(row['expires_at']),row['attempts'],bool(row.get('is_resend',False)),timestamp(row.get('sent_at') or row['created_at'])))
        for row in tables['ip_blocks']:
            execute('INSERT INTO ip_blocks(ip_address,blocked_until) VALUES(%s,%s)',(row['ip_address'],timestamp(row['blocked_until'])))
        for row in tables['security_flags']:
            execute('INSERT INTO security_flags(id,pattern,target,severity,details,flag_date,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s)',(row['id'],row['pattern'],row['target'],row['severity'],row['details'],row['flag_date'],timestamp(row['created_at'])))
        for row in tables['journal_entries']:
            for field in ['title','body']: decrypt(row[field+'_cipher'],f"{row['user_id']}:entry:{row['id']}:{field}")
            execute('INSERT INTO journal_entries(id,user_id,title,body,entry_date,mood,version,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',(row['id'],row['user_id'],row['title_cipher'],row['body_cipher'],row['entry_date'],row['mood'],row.get('version',1),timestamp(row['created_at']),timestamp(row['updated_at'])))
        execute("SELECT setval(pg_get_serial_sequence('password_history','id'),coalesce(max(id),1),count(*)>0) FROM password_history")
        for query in ["SELECT setval(pg_get_serial_sequence('activity_log','id'),coalesce(max(id),1),count(*)>0) FROM activity_log", "SELECT setval(pg_get_serial_sequence('otps','id'),coalesce(max(id),1),count(*)>0) FROM otps", "SELECT setval(pg_get_serial_sequence('security_flags','id'),coalesce(max(id),1),count(*)>0) FROM security_flags", "SELECT setval(pg_get_serial_sequence('journal_entries','id'),coalesce(max(id),1),count(*)>0) FROM journal_entries"]:execute(query)
        connection().commit()
        print(f'Imported {len(tables["users"])} accounts and {len(tables["journal_entries"])} entries. Source unchanged. Log in again using a fresh email OTP.')

if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Usage: python scripts/migrate_mysql.py PRIVATE_EXPORT.json')
    try:migrate(Path(sys.argv[1]))
    except Exception as error:
        if isinstance(error,RuntimeError):print(str(error))
        else:print('Import failed and was rolled back. Check source schema, uniqueness and encryption key. No credentials were printed.')
        raise SystemExit(1)
