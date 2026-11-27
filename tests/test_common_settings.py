from datetime import timedelta
import pytest
from pejour.security import now
from pejour.validation import username_valid, name_error, strength

def test_new_boundaries_and_distinct_question_selection(env):
    e = env
    assert not username_valid('Ab123') and username_valid('Ab1234')
    assert username_valid('A' + 'b' * 19) and (not username_valid('A' + 'b' * 20))
    assert strength('Good!123') == 'Medium' and strength('Goo!123') == 'Weak'
    assert not name_error('A' + 'bc' * 24 + 'd', 'First Name')
    assert '2–50' in name_error('A' + 'bc' * 25, 'First Name')
    data = dict(
        e['data'],
        username='Six123',
        password='Good!123',
        password_confirm='Good!123',
        question_1='1',
        question_2='1',
        question_3='7',
        captcha=e['challenge']()
    )
    response = e['post']('/register', data, headers={'Accept': 'application/json'})
    assert response.status_code == 422
    assert response.json['errors']['question_1'] == 'Choose three different security questions.'
    data.update(question_2='4', captcha=e['challenge']())
    assert e['post']('/register', data).status_code == 302
    rows = e['conn'].execute('SELECT question,answer_hash FROM security_answers ORDER BY question').fetchall()
    assert [row['question'] for row in rows] == [1, 4, 7]
    assert all((row['answer_hash'].startswith('$argon2id$') for row in rows))
    otp = e['conn'].execute('SELECT * FROM otps').fetchone()
    assert 295 < (otp['expires_at'] - now()).total_seconds() <= 300
    assert '(5 minutes)' in e['messages'][-1]['body']
    e['post']('/verify', {'code': e['code']()})
    e['post']('/forgot-password', {'username': 'Six123', 'captcha': e['challenge']()})
    page = e['client'].get('/security-question').data
    for q in [1, 4, 7]:
        assert f'<option value="{q}">'.encode() in page
    for q in [2, 3, 5, 6, 8]:
        assert f'<option value="{q}">'.encode() not in page
    response = e['post'](
        '/security-question',
        {'question': '8', 'answer': 'Adobo', 'answer_confirm': 'Adobo'}
    )
    assert b'could not be verified' in response.data
    response = e['post'](
        '/security-question',
        {'question': '1', 'answer': 'adobo', 'answer_confirm': 'adobo'}
    )
    assert response.location.endswith('/verify')

def test_forgot_link_after_two_and_exact_ip_threshold(env):
    e = env
    e['registered']()
    for count in range(1, 11):
        response = e['post'](
            '/login',
            {'username': 'Unknown' + str(count), 'password': 'Wrong!123', 'captcha': e['challenge']()}
        )
        blocked = e['conn'].execute('SELECT * FROM ip_blocks').fetchone()
        assert bool(blocked) == (count == 10)
    # Distinct usernames above test the shared IP counter. Use another client IP
    # for two consecutive failures on the actual account.
    e['conn'].execute('DELETE FROM ip_blocks')
    for count in range(1, 3):
        response = e['post'](
            '/login',
            {'username': e['data']['username'], 'password': 'Wrong!123', 'captcha': e['challenge']()},
            environ_overrides={'REMOTE_ADDR': '192.0.2.240'}
        )
        assert (b'Forgot Password? Reset Here' in response.data) == (count >= 2)

def test_legacy_question_rows_survive_and_unknown_choices_are_stable(env):
    e = env
    e['registered']()
    original = e['conn'].execute('SELECT * FROM security_answers ORDER BY question').fetchall()
    e['post']('/forgot-password', {'username': e['data']['username'], 'captcha': e['challenge']()})
    page = e['client'].get('/security-question').data
    for q in [3, 5, 8]:
        assert f'<option value="{q}">'.encode() in page
    assert original == e['conn'].execute('SELECT * FROM security_answers ORDER BY question').fetchall()
    e['post']('/forgot-password', {'username': 'NoSuchPerson', 'captcha': e['challenge']()})
    first = e['session']()['recovery']['questions']
    e['post']('/forgot-password', {'username': 'NoSuchPerson', 'captcha': e['challenge']()})
    assert first == e['session']()['recovery']['questions'] and len(set(first)) == 3

def test_monitor_ip_threshold_is_exactly_ten(env):
    e = env
    from pejour.monitor import scan
    from pejour.db import connection

    def add():
        e['conn'].execute(
            'INSERT INTO activity_log(event_type,username_typed,ip_address,user_agent) VALUES(%s,%s,%s,%s)',
            ('LOGIN_FAILED', 'TargetUser', '192.0.2.100', 'test')
        )
    for _ in range(9):
        add()
    with e['app'].app_context():
        first = scan()
        connection().commit()
    assert ('IP over threshold', '192.0.2.100') not in first['findings']
    add()
    with e['app'].app_context():
        second = scan()
        connection().commit()
    assert ('IP over threshold', '192.0.2.100') in second['findings']
