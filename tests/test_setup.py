"""Exercise the real least-privilege setup on NEW disposable databases only."""
import os
from pathlib import Path
import shutil
import sys
from urllib.parse import urlparse
import uuid
import psycopg
from psycopg import sql
from dotenv import dotenv_values
import pytest

def test_setup_creates_separate_database_with_append_only_runtime_role(monkeypatch, tmp_path):
    dsn = os.getenv('PEJOUR_TEST_DSN', '')
    if not dsn or not urlparse(dsn).path.endswith('_test'):
        pytest.skip('Requires explicit separate PostgreSQL test database.')
    source = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(source))
    import manage
    endpoint = urlparse(dsn)
    assert endpoint.hostname == '127.0.0.1', 'Setup test is restricted to the local isolated server.'
    suffix = uuid.uuid4().hex[:10]
    dbname = 'pejour_setup_' + suffix + '_test'
    role = 'pejour_setup_role_' + suffix
    monkeypatch.setattr(manage, 'ROOT', tmp_path)
    (tmp_path / 'pejour').mkdir()
    shutil.copyfile(source / 'pejour/schema.sql', tmp_path / 'pejour/schema.sql')
    shutil.copyfile(source / '.env.example', tmp_path / '.env.example')
    answers = iter([endpoint.hostname, str(endpoint.port or 5432), endpoint.username, dbname, role])
    monkeypatch.setattr('builtins.input', lambda prompt: next(answers))
    monkeypatch.setattr(manage.getpass, 'getpass', lambda prompt: endpoint.password or '')
    admin = psycopg.connect(dsn, autocommit=True)
    try:
        manage.setup_database()
        configuration = dotenv_values(tmp_path / '.env')
        with psycopg.connect(configuration['DATABASE_URL'], autocommit=True) as app:
            assert app.execute('SELECT current_user').fetchone()[0] == role
            app.execute(
                'INSERT INTO activity_log(event_type,ip_address,user_agent) VALUES(%s,%s,%s)',
                ('TEST', '127.0.0.1', 'test')
            )
            assert app.execute('SELECT count(*) FROM activity_log').fetchone()[0] == 1
        # Simulate the previously installed 18-character schema, then exercise the
        # owner-authorized upgrade twice. Existing account data must stay intact.
        with psycopg.connect(
            host=endpoint.hostname,
            port=endpoint.port,
            user=endpoint.username,
            password=endpoint.password or '',
            dbname=dbname
        ) as owner:
            owner.execute('ALTER TABLE users ALTER COLUMN username TYPE varchar(18)')
            owner.execute(
                'INSERT INTO users(id,username,email,password_hash,profile,intention) VALUES(%s,%s,%s,%s,%s,%s)',
                ('2026-7001', 'LegacyUser', 'legacy@example.invalid', 'unchanged-hash', '{}', 'unchanged-cipher')
            )
        from pejour import create_app
        application = create_app(dict(
            DATABASE_URL=configuration['DATABASE_URL'],
            ENCRYPTION_KEY=configuration['ENCRYPTION_KEY']
        ))
        monkeypatch.setattr('builtins.input', lambda prompt: endpoint.username)
        manage.upgrade_database(application)
        manage.upgrade_database(application)
        with psycopg.connect(configuration['DATABASE_URL'], autocommit=True) as app:
            assert app.execute("SELECT character_maximum_length FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='username'").fetchone()[0] == 20
            assert app.execute("SELECT password_hash,intention FROM users WHERE id='2026-7001'").fetchone() == (
                'unchanged-hash',
                'unchanged-cipher'
            )
            for command in [
                'DELETE FROM activity_log',
                'UPDATE activity_log SET details=%s',
                'TRUNCATE activity_log',
                'CREATE TABLE forbidden(id integer)'
            ]:
                with pytest.raises(psycopg.Error):
                    app.execute(command, ('attempt',) if '%s' in command else ())
            assert app.execute('SELECT count(*) FROM activity_log').fetchone()[0] == 1
        assert admin.execute('SELECT current_database()').fetchone()[0] == urlparse(dsn).path[1:]
    finally:
        assert dbname.startswith('pejour_setup_') and dbname.endswith('_test') and role.startswith('pejour_setup_role_')
        admin.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(dbname)))
        admin.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(role)))
        admin.close()

def test_cli_admin_creation_requires_normal_otp_login(env, monkeypatch):
    e = env
    import manage
    import pejour
    monkeypatch.setattr(pejour, 'create_app', lambda: e['app'])
    monkeypatch.setattr(sys, 'argv', ['manage.py', 'create-admin'])
    inputs = iter(['2026-9001', 'CliAdminTest', 'admin@example.invalid', 'Marco', 'Deloso', '8', '3', '5'])
    secrets = iter(['AdminJournal!2026', 'AdminJournal!2026', 'Adobo', 'Maria', 'Mabini'])
    monkeypatch.setattr('builtins.input', lambda prompt: next(inputs))
    monkeypatch.setattr(manage.getpass, 'getpass', lambda prompt: next(secrets))
    manage.main()
    admin = e['conn'].execute("SELECT * FROM users WHERE id='2026-9001'").fetchone()
    assert admin['role'] == 'admin' and admin['verified']
    assert e['client'].get('/dashboard-data').status_code == 401
    response = e['post'](
        '/login',
        {'username': 'CliAdminTest', 'password': 'AdminJournal!2026', 'captcha': e['challenge']()}
    )
    assert response.location.endswith('/verify')
    assert e['client'].get('/dashboard-data').status_code == 401
    assert e['post']('/verify', {'code': e['code']()}).location.endswith('/account')
    assert e['client'].get('/dashboard-data').status_code == 200
