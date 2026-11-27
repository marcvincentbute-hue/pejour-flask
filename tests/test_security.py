from datetime import timedelta
import hashlib
import re
from psycopg.types.json import Jsonb
from pejour.security import now, verify, decrypt, PHT
from pejour.validation import registration_errors

def test_registration_validation_and_secrets(env):
    e = env
    e['client'].get('/register')
    bad = dict(
        e['data'],
        first_name='Ju4n',
        province='Agusan del Norte',
        consent='',
        writing_goal='Fake',
        captcha=e['challenge']()
    )
    response = e['post']('/register', bad, headers={'Accept': 'application/json'})
    assert response.status_code == 422
    assert set(['first_name', 'province', 'consent', 'writing_goal']) <= response.json['errors'].keys()
    assert e['conn'].execute('SELECT count(*) AS n FROM users').fetchone()['n'] == 0
    e['registered']()
    user = e['conn'].execute('SELECT * FROM users').fetchone()
    assert user['role'] == 'user' and user['verified']
    assert verify(user['password_hash'], e['data']['password'])
    assert e['data']['intention'] not in user['intention']
    with e['app'].app_context():
        assert decrypt(user['intention'], user['id'] + ':intention') == e['data']['intention']
    assert all(('code_hash' in row for row in e['conn'].execute('SELECT * FROM otps').fetchall()))
    logs = str(e['conn'].execute('SELECT * FROM activity_log').fetchall())
    assert e['data']['password'] not in logs and e['data']['intention'] not in logs

def test_csrf_captcha_honeypot_and_duplicate(env):
    e = env
    e['client'].get('/register')
    assert e['client'].post('/register', data=e['data']).status_code == 403
    response = e['post'](
        '/register',
        dict(e['data'], captcha='WRONG'),
        headers={'Accept': 'application/json'}
    )
    assert 'captcha' in response.json['errors']
    response = e['post'](
        '/register',
        dict(e['data'], website='bot'),
        headers={'Accept': 'application/json'}
    )
    assert response.status_code == 422
    e['registered']()
    response = e['post'](
        '/register',
        dict(e['data'], captcha=e['challenge']()),
        headers={'Accept': 'application/json'}
    )
    assert all((key in response.json['errors'] for key in ['id', 'email', 'username']))

def test_no_auth_before_otp_purpose_and_cancel(env):
    e = env
    e['registered']()
    response = e['post'](
        '/login',
        dict(username=e['data']['username'], password=e['data']['password'], captcha=e['challenge']())
    )
    assert response.location.endswith('/verify')
    assert e['client'].get('/account').status_code == 302
    code = e['code']()
    for i in range(3):
        response = e['post']('/verify', {'code': '000000' if code != '000000' else '999999'})
        assert response.status_code == 200
    otp = e['conn'].execute("SELECT * FROM otps WHERE purpose='login'").fetchone()
    assert otp['used'] and otp['attempts'] == 3
    assert e['client'].get('/account').status_code == 302
    state = e['conn'].execute('SELECT * FROM attempt_state').fetchone()
    assert state['failures'] == 3 and state['locked_until'] > now()
    assert e['conn'].execute("SELECT count(*) AS n FROM activity_log WHERE event_type='ALERT_EMAIL_SENT'").fetchone()['n'] == 1

def test_resends_expiry_and_single_use(env):
    e = env
    values = dict(e['data'], captcha=e['challenge']())
    assert e['post']('/register', values).status_code == 302
    original = e['code']()
    assert b'wait 60 seconds' in e['post']('/verify', {'action': 'resend'}).data
    for i in range(3):
        e['conn'].execute(
            'UPDATE otps SET created_at=%s WHERE id=(SELECT max(id) FROM otps)',
            (now() - timedelta(seconds=61),)
        )
        e['post']('/verify', {'action': 'resend'})
    e['conn'].execute(
        'UPDATE otps SET created_at=%s WHERE id=(SELECT max(id) FROM otps)',
        (now() - timedelta(seconds=61),)
    )
    assert b'resend limit' in e['post']('/verify', {'action': 'resend'}).data
    assert e['conn'].execute('SELECT count(*) AS n FROM otps WHERE is_resend').fetchone()['n'] == 3
    latest = e['code']()
    assert latest != original or len(e['messages']) == 4
    e['conn'].execute('UPDATE otps SET expires_at=%s', (now() - timedelta(seconds=1),))
    assert b'incorrect, expired or cancelled' in e['post']('/verify', {'code': latest}).data
    assert not e['conn'].execute('SELECT verified FROM users').fetchone()['verified']

def test_generic_login_lockout_cookie_reset_and_ip(env):
    e = env
    e['registered']()
    names = [e['data']['username'], "' OR '1'='1", '<script>alert(1)</script>']
    for name in names:
        response = e['post'](
            '/login',
            dict(username=name, password='Wrong!Password1', captcha=e['challenge']())
        )
        assert b'Invalid username or password.' in response.data and response.status_code == 200
    # Different browser cookies do not reset the server's per-account lockout.
    for _ in range(2):
        e['post']('/login', dict(username=names[0], password='Wrong!Password1', captcha=e['challenge']()))
    e['client'].delete_cookie('pejour_session')
    response = e['post'](
        '/login',
        dict(username=names[0], password=e['data']['password'], captcha=e['challenge']())
    )
    assert b'Too many attempts' in response.data
    # Build remaining cross-account failures using different usernames, all same IP.
    for i in range(5):
        e['post'](
            '/login',
            dict(username='Unknown' + str(i), password='Wrong!Password1', captcha=e['challenge']())
        )
    block = e['conn'].execute('SELECT * FROM ip_blocks').fetchone()
    assert block and 590 < (block['blocked_until'] - now()).total_seconds() <= 600

def test_all_lockout_tiers_and_success_reset(env):
    e = env
    e['registered']()
    for number in range(1, 10):
        e['conn'].execute('UPDATE attempt_state SET locked_until=NULL')
        e['post'](
            '/login',
            dict(username=e['data']['username'], password='Wrong!Password1', captcha=e['challenge']())
        )
        if number in [3, 6, 9]:
            state = e['conn'].execute('SELECT * FROM attempt_state').fetchone()
            expected = {3: 15, 6: 30, 9: 60}[number]
            assert expected - 3 < (state['locked_until'] - now()).total_seconds() <= expected
    assert e['conn'].execute("SELECT count(*) AS n FROM activity_log WHERE event_type='ALERT_EMAIL_SENT'").fetchone()['n'] == 3
    e['conn'].execute('UPDATE attempt_state SET locked_until=NULL')
    e['login']()
    assert e['conn'].execute('SELECT count(*) AS n FROM attempt_state').fetchone()['n'] == 0

def test_session_idle_logout_and_private_routes(env):
    e = env
    e['registered']()
    e['login']()
    response = e['client'].get('/account')
    assert response.status_code == 200
    cookie = e['client'].get_cookie('pejour_session')
    assert cookie.http_only and cookie.same_site == 'Lax'
    auth = e['session']()['auth']
    auth['last_activity'] = now().timestamp() - 841
    e['set_session']({'auth': auth})
    assert 55 <= e['client'].get('/session').json['remaining'] <= 59
    assert e['post']('/session').json['remaining'] == 900
    auth = e['session']()['auth']
    auth['last_activity'] = now().timestamp() - 901
    e['set_session']({'auth': auth})
    assert e['client'].get('/account').status_code == 302
    e['conn'].execute('UPDATE otps SET created_at=%s', (now() - timedelta(seconds=61),))
    e['login']()
    assert e['post']('/logout').status_code == 302
    assert e['client'].get('/session').status_code == 401
    for path in [
        '/pejour/security.py',
        '/.env',
        '/runtime/error.log',
        '/scripts/monitor.py',
        '/static/',
        '/manage.py'
    ]:
        response = e['client'].get(path)
        assert response.status_code == 404
        assert response.headers['X-Frame-Options'] == 'DENY' and response.headers['X-Content-Type-Options'] == 'nosniff'

def test_recovery_password_history_and_other_session_invalidation(env):
    e = env
    e['registered']()
    e['login']()
    old_cookie = e['client'].get_cookie('pejour_session').value
    e['client'].delete_cookie('pejour_session')
    e['client'].get('/forgot-password')
    assert e['client'].get('/change-password').status_code == 302
    assert e['post'](
        '/forgot-password',
        dict(username=e['data']['username'], captcha=e['challenge']())
    ).status_code == 302
    assert b'Answers do not match' in e['post'](
        '/security-question',
        {'question': '8', 'answer': 'Adobo', 'answer_confirm': 'Different'}
    ).data
    assert e['post'](
        '/security-question',
        {'question': '8', 'answer': 'adobo', 'answer_confirm': 'adobo'}
    ).location.endswith('/verify')
    assert e['post']('/verify', {'code': e['code']()}).location.endswith('/change-password')
    assert b'cannot reuse a recent password' in e['post'](
        '/change-password',
        dict(password=e['data']['password'], password_confirm=e['data']['password'])
    ).data
    new = 'NewJournal!2026'
    assert e['post'](
        '/change-password',
        dict(password=new, password_confirm=new)
    ).location.endswith('/login')
    assert e['client'].get('/change-password').status_code == 302
    e['client'].set_cookie('pejour_session', old_cookie)
    assert e['client'].get('/account').status_code == 302
    user = e['conn'].execute('SELECT * FROM users').fetchone()
    assert verify(user['password_hash'], new)
    assert user['version'] == 2

def test_unknown_recovery_same_questions_and_shared_failures(env):
    e = env
    e['registered']()
    for name in [e['data']['username'], 'UnknownUser1']:
        e['post']('/forgot-password', dict(username=name, captcha=e['challenge']()))
        page = e['client'].get('/security-question').data
        assert page.count(b'<option value=') == 3
        response = e['post'](
            '/security-question',
            dict(question='8', answer='Wrong', answer_confirm='Wrong')
        )
        assert b'The account details could not be verified.' in response.data
    state = e['conn'].execute(
        'SELECT failures FROM attempt_state WHERE username=%s',
        (e['data']['username'].lower(),)
    ).fetchone()
    assert state['failures'] == 1

def test_owner_journal_encryption_concurrent_edit_and_delete(env):
    e = env
    e['registered']()
    e['login']()
    payload = dict(
        title='A private day',
        body='Secret journal text <script>alert(1)</script>',
        entry_date=e['data']['journal_start'],
        mood='Calm'
    )
    assert e['post']('/journal/new', payload).status_code == 302
    entry = e['conn'].execute('SELECT * FROM journal_entries').fetchone()
    assert 'private' not in entry['title'] and 'Secret' not in entry['body']
    page = e['client'].get('/journal')
    assert b'&lt;script&gt;' in page.data and b'<script>alert' not in page.data
    assert e['post'](
        f"/journal/{entry['id']}/edit",
        dict(payload, version=str(entry['version']))
    ).status_code == 302
    assert b'changed in another tab' in e['post'](
        f"/journal/{entry['id']}/edit",
        dict(payload, version=str(entry['version']))
    ).data
    e['post']('/logout')
    other = e['registered'](uid='2026-0002')
    e['login'](other)
    assert e['client'].get(f"/journal/{entry['id']}/edit").status_code == 404
    assert e['post'](
        f"/journal/{entry['id']}/delete",
        {'version': '3', 'confirm': 'yes'}
    ).status_code == 404
    assert e['conn'].execute('SELECT count(*) AS n FROM journal_entries').fetchone()['n'] == 1

def test_admin_read_only_json_filters_and_log_trigger(env):
    e = env
    assert e['client'].get('/dashboard-data').status_code == 401
    e['registered']()
    e['login']()
    assert e['client'].get('/dashboard').status_code == 403
    assert e['client'].get('/dashboard-data').status_code == 403
    e['conn'].execute("UPDATE users SET role='admin'")
    assert e['client'].get('/dashboard').status_code == 200
    response = e['client'].get('/dashboard-data')
    assert response.status_code == 200
    assert len(response.json['cards']) == 7 and len(response.json['chart']['labels']) == 24
    assert e['client'].get('/dashboard-data?event=REGISTERED').json['events'][0]['event_type'] == 'REGISTERED'
    assert e['client'].get('/dashboard-data?from=wrong').status_code == 422
    import psycopg
    try:
        e['conn'].execute("DELETE FROM activity_log WHERE event_type='REGISTERED'")
    except psycopg.Error:
        pass
    else:
        assert False, 'Log mutation was allowed'
    assert e['conn'].execute("SELECT count(*) AS n FROM activity_log WHERE event_type='REGISTERED'").fetchone()['n'] == 1

def test_monitor_four_patterns_rolling_window_pht_and_dedup(env):
    e = env

    def insert(event, name, ip, at, user=None):
        e['conn'].execute(
            'INSERT INTO activity_log(event_type,username_typed,user_id,ip_address,user_agent,created_at) VALUES(%s,%s,%s,%s,%s,%s)',
            (event, name, user, ip, 'test', at)
        )
    for i in range(15):
        insert('LOGIN_FAILED', 'TargetUser', '192.0.2.1', now() - timedelta(minutes=3))
    for ip in ['192.0.2.2', '192.0.2.3']:
        insert('LOGIN_FAILED', 'TARGETUSER', ip, now())
    for i in range(5):
        insert(
            'OTP_FAILED',
            'TargetUser',
            '192.0.2.1',
            now() - timedelta(seconds=100 + i),
            user='2026-0001'
        )
    midnight = now().astimezone(PHT).replace(hour=1, minute=0, second=0, microsecond=0)
    if midnight > now():
        midnight -= timedelta(days=1)
    insert('LOGIN_SUCCESS', 'TargetUser', '192.0.2.1', midnight)
    with e['app'].app_context():
        from pejour.monitor import scan
        from pejour.db import connection
        first = scan()
        connection().commit()
        second = scan()
        connection().commit()
    assert first['added'] == 4 and second['added'] == 0 and (second['existing'] == 4)
