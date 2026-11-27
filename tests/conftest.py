import base64
import hashlib
import os
from pathlib import Path
import re
import sys
import uuid
from urllib.parse import urlparse
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pejour import create_app
from pejour.security import hash_secret, encrypt
from pejour.validation import today

@pytest.fixture
def env():
    dsn = os.getenv('PEJOUR_TEST_DSN', '')
    if not dsn or not urlparse(dsn).path.endswith('_test'):
        pytest.skip('Set PEJOUR_TEST_DSN to a separate database ending in _test.')
    name = 'pejour_test_' + uuid.uuid4().hex
    conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
    conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(name)))
    conn.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(name)))
    conn.execute((Path(__file__).resolve().parents[1] / 'pejour/schema.sql').read_text())
    # Database URL options carry a test-only search path; no other schema is touched.
    test_dsn = dsn + ('&' if '?' in dsn else '?') + 'options=-csearch_path%3D' + name
    messages = []
    app = create_app({
        'TESTING': True,
        'DATABASE_URL': test_dsn,
        'ENCRYPTION_KEY': base64.b64encode(os.urandom(32)).decode(),
        'TEST_MAILER': lambda to,
        subject,
        body: messages.append({'to': to, 'subject': subject, 'body': body})
    })
    client = app.test_client()
    data = dict(
        id='2026-0001',
        first_name='Marco',
        middle_name='',
        family_name='Deloso',
        name_extension='',
        extension_other='',
        birthdate='2000-01-01',
        street='Purok Seven',
        barangay='Cabinet',
        city='Cabadbaran City',
        province='Agusan Del Norte',
        country='Philippines',
        zip_code='8605',
        email='test@example.invalid',
        username='JournalTest1',
        password='JournalTest!2026',
        password_confirm='JournalTest!2026',
        question_1='8',
        question_2='3',
        question_3='5',
        answer_1='Adobo',
        answer_2='Maria',
        answer_3='Mabini',
        display_name='Marco',
        journal_start=today().isoformat(),
        writing_goal='Gratitude',
        intention='Remember the little good things.',
        consent='1'
    )

    def session():
        cookie = client.get_cookie('pejour_session')
        return conn.execute(
            'SELECT data FROM web_sessions WHERE token_hash=%s',
            (hashlib.sha256(cookie.value.encode()).hexdigest(),)
        ).fetchone()['data'] if cookie else {}

    def set_session(values):
        current = session()
        current.update(values)
        cookie = client.get_cookie('pejour_session')
        conn.execute(
            'UPDATE web_sessions SET data=%s WHERE token_hash=%s',
            (Jsonb(current), hashlib.sha256(cookie.value.encode()).hexdigest())
        )

    def post(path, values=None, **kwargs):
        if not client.get_cookie('pejour_session'):
            client.get('/login')
        return client.post(path, data=dict(csrf=session()['csrf'], **values or {}), **kwargs)

    def challenge():
        client.get('/captcha')
        set_session({'captcha': hashlib.sha256(b'ABC234').hexdigest()})
        return 'ABC234'

    def code():
        return re.search('Your code: ([0-9]{6})', messages[-1]['body'])[1]

    def registered(admin=False, uid=None):
        values = dict(data)
        if uid:
            values.update(id=uid, username='OtherUser1', email='other@example.invalid')
        values['captcha'] = challenge()
        response = post('/register', values, headers={'Accept': 'application/json'})
        assert response.status_code == 200, response.data.decode()
        response = post('/verify', {'code': code()})
        assert response.status_code == 302, response.data.decode()
        if admin:
            conn.execute("UPDATE users SET role='admin' WHERE id=%s", (values['id'],))
        return values

    def login(values=None):
        values = values or data
        old = client.get_cookie('pejour_session')
        response = post(
            '/login',
            {'username': values['username'], 'password': values['password'], 'captcha': challenge()}
        )
        assert response.status_code == 302, response.data.decode()
        response = post('/verify', {'code': code()})
        assert response.status_code == 302, response.data.decode()
        assert client.get_cookie('pejour_session').value != old.value
        return response
    yield dict(
        app=app,
        client=client,
        conn=conn,
        data=data,
        messages=messages,
        session=session,
        set_session=set_session,
        post=post,
        challenge=challenge,
        code=code,
        registered=registered,
        login=login
    )
    conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(name)))
    conn.close()
