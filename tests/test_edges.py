import base64
from datetime import timedelta
import json
from pathlib import Path
import sys
from psycopg.types.json import Jsonb
import pytest
from pejour.security import now, encrypt, decrypt, verify
from pejour.validation import registration_errors, name_error, strength
from pejour.db import connection

def test_precise_validation_rules_and_aes_tamper(env):
    e = env
    for value, expected in [
        ('juan', 'First letter'),
        ('JUAN', 'all capital'),
        ('Ju4n', 'Numbers'),
        ('Juan!', 'Special'),
        ('Juan  Carlo', 'Double space'),
        ('Juaaan', 'Three consecutive')
    ]:
        assert expected in name_error(value, 'First Name')
    assert not name_error('Juan Carlo', 'First Name')
    assert strength('short') == 'Weak' and strength('GoodPassword2026') == 'Medium' and (strength('GoodPassword!2026') == 'Strong')
    for field, value in [
        ('id', '2026-001'),
        ('birthdate', '2999-01-01'),
        ('street', 'Purok  One'),
        ('zip_code', '123'),
        ('email', 'juan@'),
        ('username', '1BadUserName'),
        ('name_extension', 'Fake'),
        ('intention', 'Too short')
    ]:
        data = dict(e['data'])
        data[field] = value
        assert field in registration_errors(data)
    data = dict(e['data'], name_extension='Other', extension_other='III')
    assert not registration_errors(data)
    with e['app'].app_context():
        first = encrypt('A private thought', '2026-0001:intention')
        second = encrypt('A private thought', '2026-0001:intention')
        assert first != second and decrypt(first, '2026-0001:intention') == 'A private thought'
        with pytest.raises(Exception):
            decrypt(first, '2026-0002:intention')

def test_registration_mail_failure_can_resume_and_old_otp_survives(env):
    e = env
    from pejour.mail import DeliveryError
    original = e['app'].config['TEST_MAILER']

    def failed(*args):
        raise DeliveryError('Email could not be sent. Please try again later.')
    e['app'].config['TEST_MAILER'] = failed
    result = e['post']('/register', dict(e['data'], captcha=e['challenge']()))
    assert result.location.endswith('/verify')
    assert e['conn'].execute('SELECT count(*) AS n FROM users').fetchone()['n'] == 1
    assert e['conn'].execute('SELECT count(*) AS n FROM otps').fetchone()['n'] == 0
    e['app'].config['TEST_MAILER'] = original
    assert e['post']('/verify', {'action': 'resend'}).status_code == 200
    code = e['code']()
    e['conn'].execute('UPDATE otps SET created_at=%s', (now() - timedelta(seconds=61),))
    e['app'].config['TEST_MAILER'] = failed
    assert b'could not be sent' in e['post']('/verify', {'action': 'resend'}).data
    assert not e['conn'].execute('SELECT used FROM otps').fetchone()['used']
    assert e['post']('/verify', {'code': code}).status_code == 302

def test_unverified_login_blocked_and_otp_replay_prevented(env):
    e = env
    e['post']('/register', dict(e['data'], captcha=e['challenge']()))
    register_code = e['code']()
    assert b'Invalid username or password.' in e['post'](
        '/login',
        dict(username=e['data']['username'], password=e['data']['password'], captcha=e['challenge']())
    ).data
    assert e['post']('/verify', {'code': register_code}).status_code == 302
    e['login']()
    auth_cookie = e['client'].get_cookie('pejour_session').value
    assert e['client'].get('/verify').location.endswith('/login')
    assert e['conn'].execute("SELECT used FROM otps WHERE purpose='login'").fetchone()['used']

def test_generic_500_and_security_headers_even_on_assets(env):
    e = env

    @e['app'].route('/test-only-error')
    def injected_error():
        raise RuntimeError('private internal exception detail')
    response = e['client'].get('/test-only-error')
    assert response.status_code == 500 and b'private internal exception' not in response.data and (b'Traceback' not in response.data)
    for path in ['/login', '/static/css/app.css', '/static/js/app.js', '/not-a-route']:
        response = e['client'].get(path)
        assert response.headers['X-Frame-Options'] == 'DENY'
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
        assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']

def test_recent_three_passwords_and_grant_single_use(env):
    e = env
    e['registered']()
    passwords = [e['data']['password'], 'SecondJournal!2026', 'ThirdJournal!2026', 'FourthJournal!2026']
    for value in passwords[1:]:
        user = e['conn'].execute('SELECT * FROM users').fetchone()
        e['set_session']({'reset': {
            'id': user['id'],
            'version': user['version'],
            'expires': now().timestamp() + 300
        }})
        assert e['post'](
            '/change-password',
            dict(password=value, password_confirm=value)
        ).status_code == 302
        assert 'reset' not in e['session']()
    user = e['conn'].execute('SELECT * FROM users').fetchone()
    e['set_session']({'reset': {
        'id': user['id'],
        'version': user['version'],
        'expires': now().timestamp() + 300
    }})
    for value in passwords[1:]:
        assert b'cannot reuse a recent password' in e['post'](
            '/change-password',
            dict(password=value, password_confirm=value)
        ).data
    # The initial password is older than the last three and can be chosen again.
    assert e['post'](
        '/change-password',
        dict(password=passwords[0], password_confirm=passwords[0])
    ).status_code == 302

def test_import_preserves_hash_ciphertext_and_rolls_back(env, tmp_path, monkeypatch):
    e = env
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    import migrate_mysql
    monkeypatch.setattr(migrate_mysql, 'create_app', lambda: e['app'])
    from pejour.security import hash_secret
    uid = '2026-7777'
    password = hash_secret('MigrationJournal!2026')
    stamp = now().replace(tzinfo=None).isoformat(sep=' ')
    with e['app'].app_context():
        intention = encrypt('Preserve the original private intention.', uid + ':intention')
        title = encrypt('Preserved entry', uid + ':entry:91:title')
        body = encrypt('Preserved private journal content.', uid + ':entry:91:body')
    user = dict(
        e['data'],
        id=uid,
        username='MigratedUser1',
        email='migrated@example.invalid',
        password_hash=password,
        role='user',
        email_verified_at=stamp,
        session_version=4,
        intention_cipher=intention,
        consent_at=stamp,
        created_at=stamp,
        failed_attempts=2
    )
    tables = dict(
        users=[user],
        security_answers=[],
        password_history=[dict(id=10, user_id=uid, password_hash=password, created_at=stamp)],
        activity_log=[dict(id=50, event_type='REGISTERED', username_typed=user['username'], user_id=uid, ip_address='192.0.2.99', user_agent='Migration test', details='Test', created_at=stamp)],
        security_flags=[],
        ip_blocks=[],
        otps=[],
        journal_entries=[dict(id=91, user_id=uid, title_cipher=title, body_cipher=body, entry_date=e['data']['journal_start'], mood='Calm', version=2, created_at=stamp, updated_at=stamp)]
    )
    path = tmp_path / 'private-export.json'
    payload = dict(
        format='pejour-mysql-v1',
        encryption_key=e['app'].config['ENCRYPTION_KEY'],
        tables=tables
    )
    # A bad authentication tag occurs after the user is inserted; the entire import rolls back.
    saved = tables['journal_entries'][0]['body_cipher']
    tables['journal_entries'][0]['body_cipher'] = 'v1:AAAA'
    path.write_text(json.dumps(payload))
    with pytest.raises(Exception):
        migrate_mysql.migrate(path)
    assert e['conn'].execute('SELECT count(*) AS n FROM users').fetchone()['n'] == 0
    tables['journal_entries'][0]['body_cipher'] = saved
    path.write_text(json.dumps(payload))
    migrate_mysql.migrate(path)
    row = e['conn'].execute('SELECT * FROM users').fetchone()
    assert row['password_hash'] == password and row['intention'] == intention and (row['version'] == 4)
    assert verify(row['password_hash'], 'MigrationJournal!2026')
    assert e['conn'].execute('SELECT body FROM journal_entries').fetchone()['body'] == body
    with pytest.raises(RuntimeError):
        migrate_mysql.migrate(path)
    assert e['conn'].execute('SELECT count(*) AS n FROM users').fetchone()['n'] == 1
    next_id = e['conn'].execute("SELECT nextval(pg_get_serial_sequence('journal_entries','id')) AS n").fetchone()['n']
    assert next_id == 92
