import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import current_app, g, request
from psycopg.types.json import Jsonb
from .db import execute, one, lock
from .settings import IDLE_SECONDS
PHT = ZoneInfo('Asia/Manila')
HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(24))

def now():
    return datetime.now(timezone.utc)

def hash_secret(value):
    return HASHER.hash(value)

def verify(encoded, value):
    try:
        return HASHER.verify(encoded or DUMMY_HASH, value)
    except (VerificationError, InvalidHashError):
        return False

def encrypt(value, context):
    key = base64.b64decode(current_app.config['ENCRYPTION_KEY'], validate=True)
    nonce = secrets.token_bytes(12)
    data = AESGCM(key).encrypt(nonce, value.encode(), context.encode())
    # Compatible with the PHP Pejour v1 payload: nonce + tag + ciphertext.
    return 'v1:' + base64.b64encode(nonce + data[-16:] + data[:-16]).decode()

def decrypt(value, context):
    if not value.startswith('v1:'):
        raise ValueError('Unknown encryption version')
    data = base64.b64decode(value[3:], validate=True)
    key = base64.b64decode(current_app.config['ENCRYPTION_KEY'], validate=True)
    return AESGCM(key).decrypt(data[:12], data[28:] + data[12:28], context.encode()).decode()

def audit(event, username=None, user_id=None, details=''):
    execute(
        'INSERT INTO activity_log(event_type,username_typed,user_id,ip_address,user_agent,details) VALUES(%s,%s,%s,%s,%s,%s)',
        (event, (username or '')[:256], user_id, request.remote_addr or 'unknown', request.headers.get('User-Agent', '')[:500], details[:1000])
    )

def load_session():
    token = request.cookies.get('pejour_session', '')
    if len(token) != 64:
        token = secrets.token_hex(32)
    g.token = token
    g.token_hash = hashlib.sha256(token.encode()).hexdigest()
    lock('session:' + g.token_hash)
    row = one('SELECT data FROM web_sessions WHERE token_hash=%s AND expires_at>%s', (g.token_hash, now()))
    g.session = row['data'] if row else {}
    if not row:
        rotate_session({})
    g.session.setdefault('csrf', secrets.token_hex(32))
    g.user = None
    auth = g.session.get('auth')
    if auth:
        user = one('SELECT * FROM users WHERE id=%s', (auth['id'],))
        if not user or user['version'] != auth['version'] or now().timestamp() - auth['last_activity'] >= IDLE_SECONDS:
            rotate_session({})
            g.session['notice'] = 'Your session expired. Please log in again.'
        else:
            g.user = user

def rotate_session(data):
    if hasattr(g, 'token_hash'):
        execute('DELETE FROM web_sessions WHERE token_hash=%s', (g.token_hash,))
    g.token = secrets.token_hex(32)
    g.token_hash = hashlib.sha256(g.token.encode()).hexdigest()
    g.session = dict(data, csrf=secrets.token_hex(32))

def save_session(response):
    expires = now() + timedelta(hours=1)
    auth = g.session.get('auth')
    if auth:
        expires = datetime.fromtimestamp(auth['last_activity'] + IDLE_SECONDS, timezone.utc)
    execute(
        'INSERT INTO web_sessions(token_hash,data,expires_at) VALUES(%s,%s,%s) ON CONFLICT(token_hash) DO UPDATE SET data=EXCLUDED.data,expires_at=EXCLUDED.expires_at',
        (g.token_hash, Jsonb(g.session), expires)
    )
    response.set_cookie(
        'pejour_session',
        g.token,
        httponly=True,
        secure=current_app.config['COOKIE_SECURE'],
        samesite='Lax',
        path='/'
    )
    return response

def csrf_valid():
    supplied = request.form.get('csrf', '') or request.headers.get('X-CSRF-Token', '')
    return bool(supplied) and hmac.compare_digest(supplied, g.session.get('csrf', ''))

def captcha_valid():
    expected = g.session.pop('captcha', '')
    answer = request.form.get('captcha', '').upper()
    actual = hashlib.sha256(answer.encode()).hexdigest()
    valid = bool(expected) and hmac.compare_digest(expected, actual)
    if not valid:
        audit('CAPTCHA_FAILED', request.form.get('username'))
    return valid
