"""Authentication services. Advisory locks make limits work across workers."""
import math
import secrets
from datetime import timedelta
from flask import g, request
from .db import execute, one, all_rows, lock
from .security import now, audit, verify, hash_secret, rotate_session, PHT
from .mail import send_email, alert
from .settings import LOCKOUT_SECONDS, OTP_MINUTES, IP_FAILURE_THRESHOLD

def account(username):
    return one('SELECT * FROM users WHERE lower(username)=lower(%s)', (username,))

def guard(username):
    lock('ip:' + (request.remote_addr or 'unknown'))
    lock('username:' + username.lower())
    blocked = one('SELECT blocked_until FROM ip_blocks WHERE ip_address=%s', (request.remote_addr,))
    state = one('SELECT * FROM attempt_state WHERE username=%s', (username.lower(),))
    until = max([x for x in [
        blocked['blocked_until'] if blocked else None,
        state['locked_until'] if state else None,
        now()
    ] if x])
    return (math.ceil((until - now()).total_seconds()), state['failures'] if state else 0)

def ip_failure():
    total = one(
        "SELECT count(*) AS n FROM activity_log WHERE ip_address=%s AND event_type IN ('LOGIN_FAILED','IP_FAILURE') AND created_at>=%s",
        (request.remote_addr, now() - timedelta(minutes=10))
    )['n']
    if total >= IP_FAILURE_THRESHOLD:
        row = one('SELECT blocked_until FROM ip_blocks WHERE ip_address=%s', (request.remote_addr,))
        if not row or row['blocked_until'] <= now():
            execute(
                'INSERT INTO ip_blocks(ip_address,blocked_until) VALUES(%s,%s) ON CONFLICT(ip_address) DO UPDATE SET blocked_until=EXCLUDED.blocked_until',
                (request.remote_addr, now() + timedelta(minutes=10))
            )
            audit('IP_BLOCKED', details=f'{IP_FAILURE_THRESHOLD} failures within 10 minutes.')

def fail(username, user=None):
    audit('LOGIN_FAILED', username, user['id'] if user else None)
    state = one(
        'INSERT INTO attempt_state(username,failures) VALUES(%s,1) ON CONFLICT(username) DO UPDATE SET failures=attempt_state.failures+1 RETURNING failures',
        (username.lower(),)
    )
    count = state['failures']
    if count % 3 == 0:
        tier = min(count // 3, 3)
        seconds = LOCKOUT_SECONDS[tier - 1]
        execute(
            'UPDATE attempt_state SET locked_until=%s WHERE username=%s',
            (now() + timedelta(seconds=seconds), username.lower())
        )
        if count in (3, 6, 9):
            audit(
                f'LOCKOUT_TIER_{tier}',
                username,
                user['id'] if user else None,
                f'{seconds} seconds; {count} failures.'
            )
            if user:
                alert(user, 'Failed sign-in attempts on your account', count)
    ip_failure()

def captcha_failure():
    audit(
        'IP_FAILURE',
        request.form.get('username'),
        details='CAPTCHA failure; no account counter increment.'
    )
    ip_failure()

def send_otp(user, purpose, resend=False):
    lock('otp:' + user['id'] + ':' + purpose)
    latest = one(
        'SELECT * FROM otps WHERE user_id=%s AND purpose=%s ORDER BY id DESC LIMIT 1',
        (user['id'], purpose)
    )
    if latest and (now() - latest['created_at']).total_seconds() < 60:
        return 'Please wait 60 seconds before requesting another code.'
    count = one(
        'SELECT count(*) AS n FROM otps WHERE user_id=%s AND purpose=%s AND is_resend=true AND created_at>=%s',
        (user['id'], purpose, now() - timedelta(minutes=15))
    )['n']
    if resend and count >= 3:
        return 'The resend limit has been reached. Try again after 15 minutes.'
    code = f'{secrets.randbelow(1000000):06d}'
    expiry = now() + timedelta(minutes=OTP_MINUTES)
    subjects = {
        'register': 'Verify your account',
        'login': 'Your log-in code',
        'reset': 'Password reset code',
        'email_change': 'Verify your new email'
    }
    # Delivery happens before the old code is cancelled. Failure preserves it.
    send_email(
        user['email'],
        subjects[purpose],
        f'Pejour — {subjects[purpose]}\n\nYour code: {code}\nExpires: {expiry.astimezone(PHT):%Y-%m-%d %H:%M:%S} PHT ({OTP_MINUTES} minutes).\n\nIf you did not request this code, ignore this email and consider changing your password.'
    )
    execute(
        'UPDATE otps SET used=true WHERE user_id=%s AND purpose=%s AND used=false',
        (user['id'], purpose)
    )
    execute(
        'INSERT INTO otps(user_id,purpose,code_hash,expires_at,is_resend) VALUES(%s,%s,%s,%s,%s)',
        (user['id'], purpose, hash_secret(code), expiry, resend)
    )
    audit('OTP_SENT', user['username'], user['id'], purpose)
    return ''

def check_otp(user, purpose, code):
    lock('otp:' + user['id'] + ':' + purpose)
    otp = one(
        'SELECT * FROM otps WHERE user_id=%s AND purpose=%s ORDER BY id DESC LIMIT 1 FOR UPDATE',
        (user['id'], purpose)
    )
    active = otp and (not otp['used']) and (otp['attempts'] < 3) and (otp['expires_at'] > now())
    matches = verify(otp['code_hash'] if otp else None, code)
    if not active or not matches:
        if active:
            execute('UPDATE otps SET attempts=attempts+1,used=(attempts+1>=3) WHERE id=%s', (otp['id'],))
        audit('OTP_FAILED', user['username'], user['id'], purpose)
        if purpose == 'login':
            fail(user['username'], user)
        return False
    execute('UPDATE otps SET used=true WHERE id=%s', (otp['id'],))
    return True

def finish_login(user):
    execute('DELETE FROM attempt_state WHERE username=%s', (user['username'].lower(),))
    rotate_session({'auth': {
        'id': user['id'],
        'version': user['version'],
        'last_activity': now().timestamp()
    }})
    g.user = user
    audit('LOGIN_SUCCESS', user['username'], user['id'])

def change_password(user, password):
    lock('password:' + user['id'])
    fresh = one('SELECT * FROM users WHERE id=%s FOR UPDATE', (user['id'],))
    grant = g.session.get('reset', {})
    if not fresh or fresh['version'] != grant.get('version') or grant.get(
        'expires',
        0
    ) <= now().timestamp():
        return 'Your reset authorization expired. Please start again.'
    history = all_rows(
        'SELECT password_hash FROM password_history WHERE user_id=%s ORDER BY id DESC LIMIT 3',
        (user['id'],)
    )
    if any((verify(row['password_hash'], password) for row in history)) or verify(
        fresh['password_hash'],
        password
    ):
        return 'You cannot reuse a recent password.'
    encoded = hash_secret(password)
    execute('UPDATE users SET password_hash=%s,version=version+1 WHERE id=%s', (encoded, user['id']))
    execute('INSERT INTO password_history(user_id,password_hash) VALUES(%s,%s)', (user['id'], encoded))
    execute('UPDATE otps SET used=true WHERE user_id=%s', (user['id'],))
    execute('DELETE FROM attempt_state WHERE username=%s', (user['username'].lower(),))
    audit('PASSWORD_CHANGED', user['username'], user['id'])
    failures = one(
        'SELECT count(*) AS n FROM activity_log WHERE event_type=%s AND user_id=%s',
        ('LOGIN_FAILED', user['id'])
    )['n']
    alert(user, 'Your password was changed', failures)
    rotate_session({'notice': 'Successfully Change Password.'})
    return ''
