"""Run `python manage.py --help`. Administrative commands run in the terminal only."""
import argparse
import base64
import getpass
import os
from pathlib import Path
import secrets
from urllib.parse import quote
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parent

def schema(conn):
    conn.execute((ROOT / 'pejour' / 'schema.sql').read_text(encoding='utf-8'))

def upgrade_database(app):
    """Widen only the existing username column. Never change data or encryption keys."""
    from psycopg.conninfo import conninfo_to_dict
    settings = conninfo_to_dict(app.config['DATABASE_URL'])
    with psycopg.connect(**settings) as conn:
        width = conn.execute("SELECT character_maximum_length FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='username'").fetchone()
    if width and width[0] >= 20:
        print('Database already supports 20-character usernames. No data changed.')
        return
    print('This upgrade widens usernames from 18 to 20 characters. Accounts, answers, logs and encrypted data are preserved.')
    settings['user'] = input('PostgreSQL schema owner [postgres]: ').strip() or 'postgres'
    settings['password'] = getpass.getpass('PostgreSQL schema-owner password: ')
    with psycopg.connect(**settings) as conn:
        conn.execute("SET LOCAL lock_timeout='5s'")
        conn.execute('ALTER TABLE users ALTER COLUMN username TYPE varchar(20)')
    print('Database upgrade complete. Existing accounts and encryption keys are unchanged.')

def setup_database():
    """Create a NEW database and least-privilege app role, preserving all old databases."""
    print('Create a separate PostgreSQL database. Your PHP/MySQL database will not be changed.')
    host = input('PostgreSQL host [127.0.0.1]: ').strip() or '127.0.0.1'
    port = input('PostgreSQL port [5432]: ').strip() or '5432'
    admin = input('PostgreSQL administrator [postgres]: ').strip() or 'postgres'
    password = getpass.getpass('PostgreSQL administrator password: ')
    dbname = input('NEW database name [pejour_flask]: ').strip() or 'pejour_flask'
    role = input('NEW app role [pejour_flask_app]: ').strip() or 'pejour_flask_app'
    env = ROOT / '.env'
    if env.exists():
        raise RuntimeError('.env already exists. Keep it safe; this command will not overwrite your keys.')
    app_password = secrets.token_urlsafe(32)
    with psycopg.connect(
        host=host,
        port=port,
        user=admin,
        password=password,
        dbname='postgres',
        autocommit=True
    ) as conn:
        if conn.execute('SELECT 1 FROM pg_database WHERE datname=%s', (dbname,)).fetchone():
            raise RuntimeError('That database already exists. Choose a new name; nothing was changed.')
        if conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,)).fetchone():
            raise RuntimeError('That role already exists. Choose a new name; nothing was changed.')
        # PostgreSQL utility DDL does not accept bind parameters for identifiers or
        # role passwords. psycopg Identifier/Literal quote these CLI-only values.
        conn.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(
            sql.Identifier(role),
            sql.Literal(app_password)
        ))
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(dbname)))
    with psycopg.connect(host=host, port=port, user=admin, password=password, dbname=dbname) as conn:
        schema(conn)
        conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
        conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(
            sql.Identifier(dbname),
            sql.Identifier(role)
        ))
        conn.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
        conn.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {}').format(sql.Identifier(role)))
        conn.execute(sql.SQL('REVOKE UPDATE,DELETE,TRUNCATE ON activity_log FROM {}').format(sql.Identifier(role)))
        conn.execute(sql.SQL('GRANT USAGE,SELECT,UPDATE ON ALL SEQUENCES IN SCHEMA public TO {}').format(sql.Identifier(role)))
    template = (ROOT / '.env.example').read_text(encoding='utf-8')
    dsn = f"postgresql://{quote(role, safe='')}:{quote(
        app_password,
        safe=''
    )}@{host}:{port}/{quote(dbname, safe='')}"
    template = template.replace('postgresql://pejour_app:CHANGE_ME@127.0.0.1:5432/pejour', dsn)
    template = template.replace(
        'REPLACE_WITH_BASE64_32_BYTE_KEY',
        base64.b64encode(secrets.token_bytes(32)).decode()
    )
    env.write_text(template, encoding='utf-8')
    print('Separate database created. .env saved privately. Add your Gmail App Password in .env next.')

def main():
    parser = argparse.ArgumentParser(description='Pejour Flask project tools')
    parser.add_argument(
        'command',
        choices=['setup-database', 'upgrade', 'generate-keys', 'create-admin', 'test-email', 'monitor', 'serve', 'cleanup-sessions']
    )
    parser.add_argument('--port', type=int, default=8088)
    args = parser.parse_args()
    if args.command == 'generate-keys':
        print(base64.b64encode(secrets.token_bytes(32)).decode())
        return
    if args.command == 'setup-database':
        setup_database()
        return
    from pejour import create_app
    from pejour.db import connection, execute, one
    from pejour.security import hash_secret, encrypt, now, PHT
    app = create_app()
    if args.command == 'upgrade':
        upgrade_database(app)
        return
    if args.command == 'serve':
        from waitress import serve
        print(f'Pejour is running at http://127.0.0.1:{args.port} (Ctrl+C to stop).')
        serve(app, host='127.0.0.1', port=args.port, threads=6)
        return
    with app.app_context():
        if args.command == 'monitor':
            from pejour.monitor import scan
            result = scan()
            connection().commit()
            print(f'IT 107 Monitoring Report — {now().astimezone(PHT):%Y-%m-%d %H:%M} PHT')
            print(f"Scanned: {result['scanned']} events (last 24 hours)")
            for (pattern, target), (severity, details) in result['findings'].items():
                print(f'[{severity}] {pattern}: {target} — {details}')
            print(f"New flags: {result['added']}; already flagged today: {result['existing']}")
        elif args.command == 'test-email':
            from pejour.mail import send_email
            to = input('Send test email to: ').strip()
            send_email(to, 'Test email', 'Your Pejour Flask SMTP connection is working.')
            print('Test email sent. Check your inbox and Spam folder.')
        elif args.command == 'cleanup-sessions':
            result = execute('DELETE FROM web_sessions WHERE expires_at<%s', (now(),))
            connection().commit()
            print(f'Removed {result.rowcount} expired sessions. Activity logs were preserved.')
        elif args.command == 'create-admin':
            from pejour.validation import QUESTIONS, registration_errors, selected_questions, today
            from pejour.auth import account
            print('Create a NEW admin. Admins still log in with password, CAPTCHA and email OTP.')
            uid = input('ID Number (xxxx-xxxx): ').strip()
            username = input('Username (6–20 letters/digits): ').strip()
            email = input('Real email inbox: ').strip().lower()
            password = getpass.getpass('Password: ')
            confirm = getpass.getpass('Re-enter Password: ')
            first = input('First Name (Title Case): ').strip()
            family = input('Family Name (Title Case): ').strip()
            for number, question in QUESTIONS.items():
                print(f'{number}. {question}')
            answers = {}
            for slot in range(1, 4):
                answers[f'question_{slot}'] = input(f'Choose security question {slot} (1–8; different from the others): ').strip()
                answers[f'answer_{slot}'] = getpass.getpass(f'Answer {slot}: ')
            profile = dict(
                first_name=first,
                middle_name='',
                family_name=family,
                name_extension='',
                extension_other='',
                birthdate='2000-01-01',
                street='Admin Office',
                barangay='Campus',
                city='Butuan City',
                province='Agusan Del Norte',
                country='Philippines',
                zip_code='8600',
                display_name='Administrator',
                journal_start=today().isoformat(),
                writing_goal='Self Reflection',
                age_at_registration=26
            )
            data = dict(
                profile,
                id=uid,
                username=username,
                email=email,
                password=password,
                password_confirm=confirm,
                intention='Maintain a safe space for personal reflection.',
                consent='1',
                **answers
            )
            errors = registration_errors(data)
            if errors:
                raise RuntimeError('; '.join(errors.values()))
            if account(username) or one('SELECT id FROM users WHERE id=%s OR email=%s', (uid, email)):
                raise RuntimeError('An account already uses those details. Existing accounts were not changed.')
            encoded = hash_secret(password)
            execute(
                'INSERT INTO users(id,username,email,password_hash,role,verified,profile,intention) VALUES(%s,%s,%s,%s,%s,true,%s,%s)',
                (uid, username, email, encoded, 'admin', Jsonb(profile), encrypt(data['intention'], uid + ':intention'))
            )
            execute('INSERT INTO password_history(user_id,password_hash) VALUES(%s,%s)', (uid, encoded))
            for slot, q in enumerate(selected_questions(data), 1):
                execute(
                    'INSERT INTO security_answers(user_id,question,answer_hash) VALUES(%s,%s,%s)',
                    (uid, q, hash_secret(answers[f'answer_{slot}'].lower()))
                )
            execute(
                'INSERT INTO activity_log(event_type,username_typed,user_id,ip_address,user_agent,details) VALUES(%s,%s,%s,%s,%s,%s)',
                ('ADMIN_CREATED', username, uid, 'CLI', 'Terminal', 'Administrator created through protected CLI; fictional classroom address, replace with your own verified documentation.')
            )
            connection().commit()
            print('Admin created. Use the normal Log-in page; email OTP is required.')
if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        # Configuration/database exceptions may include credentials; don't print them.
        from pejour.mail import DeliveryError
        if isinstance(error, (RuntimeError, DeliveryError)):
            print(str(error))
        else:
            print('Operation failed. Check your settings and whether PostgreSQL is running. No passwords were printed.')
        raise SystemExit(1)
