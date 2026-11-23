import hashlib
import hmac
import io
import math
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Blueprint, g, request, render_template, redirect, url_for, jsonify, send_file, current_app, abort
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from psycopg.types.json import Jsonb
from psycopg.errors import UniqueViolation
from .db import execute, one, all_rows, connection, lock
from .security import now, PHT, audit, hash_secret, verify, encrypt, decrypt, rotate_session, captcha_valid
from .validation import QUESTIONS, GOALS, MOODS, registration_errors, selected_questions, username_valid, answer_valid, strength, today, date_value, age
from .settings import IDLE_SECONDS, FORGOT_AFTER
from .auth import account, guard, fail, captcha_failure, send_otp, check_otp, finish_login, change_password
from .mail import DeliveryError
bp = Blueprint('web', __name__)

@bp.app_context_processor
def context():
    session = getattr(g, 'session', {})
    return dict(
        user=getattr(g, 'user', None),
        csrf=session.get('csrf', ''),
        notice=session.pop('notice', ''),
        questions=QUESTIONS,
        goals=GOALS,
        moods=MOODS,
        today=today().isoformat(),
        privacy_contact=current_app.config['PRIVACY_CONTACT'],
        idle_seconds=IDLE_SECONDS,
        forgot_after=FORGOT_AFTER
    )

def protected(admin=False, api=False):

    def decorate(fn):

        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not g.user:
                return ('', 401) if api else redirect(url_for('web.login'))
            if admin and g.user['role'] != 'admin':
                audit('ADMIN_ACCESS_DENIED', g.user['username'], g.user['id'])
                return ('', 403) if api else (
                    render_template('error.html', title='Access denied', message='This page is available to administrators only.'),
                    403
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorate

def json_request():
    return request.headers.get('Accept') == 'application/json'

def result_errors(template, errors, **kwargs):
    if json_request():
        return (jsonify(ok=False, errors=errors, csrf=g.session['csrf']), 422)
    return (render_template(template, errors=errors, data=request.form, **kwargs), 422)

def next_page(endpoint):
    target = url_for(endpoint)
    return jsonify(ok=True, redirect=target) if json_request() else redirect(target)

@bp.route('/')
def home():
    if g.user:
        return redirect(url_for('web.account_page'))
    return render_template('home.html', title='Your private space')

@bp.route('/captcha')
def captcha():
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    text = ''.join((secrets.choice(chars) for _ in range(6)))
    g.session['captcha'] = hashlib.sha256(text.encode()).hexdigest()
    image = Image.new('RGB', (240, 78), '#e8f3ef')
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 29)
    except OSError:
        font = ImageFont.load_default(size=29)
    for i, char in enumerate(text):
        tile = Image.new('RGBA', (38, 54), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text((5, 4), char, font=font, fill='#234d48')
        tile = tile.rotate(secrets.randbelow(31) - 15, resample=Image.Resampling.BICUBIC)
        image.paste(tile, (10 + i * 36, 10 + secrets.randbelow(8)), tile)
    for _ in range(9):
        draw.line(
            [secrets.randbelow(240), secrets.randbelow(78), secrets.randbelow(240), secrets.randbelow(78)],
            fill='#94b6ac',
            width=1
        )
    output = io.BytesIO()
    image.save(output, format='PNG')
    output.seek(0)
    return send_file(output, mimetype='image/png')

@bp.route('/username-availability')
def username_availability():
    name = request.args.get('username', '')[:100]
    valid = username_valid(name)
    available = valid and account(name) is None
    return jsonify(
        valid=valid,
        available=available,
        message='Username is available.' if available else 'This username is already registered.' if valid else 'Use 6–20 letters and digits, starting with a letter.'
    )

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('web.account_page'))
    if request.method == 'GET':
        return render_template('register.html', title='Create your account', errors={}, data={})
    if request.form.get('website'):
        return result_errors(
            'register.html',
            {'_form': 'Registration could not be completed. Please try again.'},
            title='Create your account'
        )
    errors = registration_errors(request.form)
    if not captcha_valid():
        errors['captcha'] = 'CAPTCHA did not match. Enter the new characters shown.'
    # Lock all uniqueness keys in a stable order to prevent concurrent duplicate races.
    for value in sorted([
        'id:' + request.form.get('id', ''),
        'name:' + request.form.get('username', '').lower(),
        'email:' + request.form.get('email', '').lower()
    ]):
        lock('register:' + value)
    for key, column in [('id', 'id'), ('username', 'username'), ('email', 'email')]:
        query = {
            'id': 'SELECT id FROM users WHERE id=%s',
            'username': 'SELECT id FROM users WHERE lower(username)=lower(%s)',
            'email': 'SELECT id FROM users WHERE lower(email)=lower(%s)'
        }[column]
        if one(query, (request.form.get(key, ''),)):
            errors[key] = {
                'id': 'This ID Number is already registered.',
                'username': 'This username is already registered.',
                'email': 'This email is already registered.'
            }[key]
    if errors:
        return result_errors('register.html', errors, title='Create your account')
    data = request.form
    profile = {key: data.get(key, '') for key in [
        'first_name',
        'middle_name',
        'family_name',
        'name_extension',
        'extension_other',
        'birthdate',
        'street',
        'barangay',
        'city',
        'province',
        'country',
        'zip_code',
        'display_name',
        'journal_start',
        'writing_goal'
    ]}
    profile['age_at_registration'] = age(data['birthdate'])
    encoded = hash_secret(data['password'])
    uid = data['id']
    execute(
        'INSERT INTO users(id,username,email,password_hash,profile,intention) VALUES(%s,%s,%s,%s,%s,%s)',
        (uid, data['username'], data['email'].lower(), encoded, Jsonb(profile), encrypt(data['intention'], uid + ':intention'))
    )
    for slot, q in enumerate(selected_questions(data), 1):
        execute(
            'INSERT INTO security_answers(user_id,question,answer_hash) VALUES(%s,%s,%s)',
            (uid, q, hash_secret(data[f'answer_{slot}'].lower()))
        )
    execute('INSERT INTO password_history(user_id,password_hash) VALUES(%s,%s)', (uid, encoded))
    audit('REGISTERED', data['username'], uid)
    g.session['pending'] = {'id': uid, 'purpose': 'register', 'expires': now().timestamp() + 3600}
    try:
        message = send_otp(account(data['username']), 'register')
        if message:
            g.session['notice'] = message
    except DeliveryError as error:
        g.session['notice'] = str(error) + ' Your account is pending; use Resend code to continue.'
    return next_page('web.otp')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('web.account_page'))
    errors = {}
    seconds = 0
    failures = 0
    name = request.form.get('username', '')[:256] if request.method == 'POST' else g.session.get(
        'login_name',
        ''
    )
    if name:
        seconds, failures = guard(name)
    if request.method == 'POST':
        g.session['login_name'] = name
        if seconds > 0:
            errors['_form'] = 'Too many attempts. Please wait for the countdown.'
        elif not captcha_valid():
            captcha_failure()
            errors['captcha'] = 'CAPTCHA did not match. Enter the new characters shown.'
        else:
            user = account(name)
            correct = verify(user['password_hash'] if user else None, request.form.get('password', ''))
            if not username_valid(name) or not correct or (not user) or (not user['verified']):
                fail(name, user)
                errors['_form'] = 'Invalid username or password.'
            else:
                try:
                    message = send_otp(user, 'login')
                    g.session['pending'] = {
                        'id': user['id'],
                        'purpose': 'login',
                        'version': user['version'],
                        'expires': now().timestamp() + 3600
                    }
                    if message:
                        g.session['notice'] = message
                    return redirect(url_for('web.otp'))
                except DeliveryError as error:
                    errors['_form'] = str(error)
        seconds, failures = guard(name)
    return render_template(
        'login.html',
        title='Welcome back',
        errors=errors,
        data={'username': name},
        seconds=max(seconds, 0),
        failures=failures
    )

@bp.route('/verify', methods=['GET', 'POST'])
def otp():
    pending = g.session.get('pending', {})
    if pending.get('expires', 0) <= now().timestamp():
        g.session.pop('pending', None)
        return redirect(url_for('web.login'))
    user = one('SELECT * FROM users WHERE id=%s', (pending.get('id'),))
    purpose = pending.get('purpose')
    if not user or purpose not in ['register', 'login', 'reset']:
        return redirect(url_for('web.login'))
    if purpose in ['login', 'reset'] and user['version'] != pending.get('version'):
        g.session.pop('pending', None)
        return redirect(url_for('web.login'))
    seconds, failures = guard(user['username'])
    errors = {}
    if request.method == 'POST':
        if seconds > 0:
            errors['_form'] = 'Too many attempts. Please wait for the countdown.'
        elif request.form.get('action') == 'resend':
            try:
                message = send_otp(user, purpose, True)
                if message:
                    errors['_form'] = message
                else:
                    g.session['notice'] = 'A new code has been emailed.'
            except DeliveryError as error:
                errors['_form'] = str(error)
        elif not re.fullmatch('[0-9]{6}', request.form.get('code', '')) or not check_otp(
            user,
            purpose,
            request.form.get('code', '')
        ):
            # Malformed codes count too, so HTML constraints cannot bypass attempt limits.
            if not re.fullmatch('[0-9]{6}', request.form.get('code', '')):
                check_otp(user, purpose, request.form.get('code', ''))
            errors['code'] = 'The code is incorrect, expired or cancelled. After three wrong entries, request a new code.'
        else:
            g.session.pop('pending', None)
            if purpose == 'register':
                execute('UPDATE users SET verified=true WHERE id=%s', (user['id'],))
                audit('ACCOUNT_VERIFIED', user['username'], user['id'])
                g.session['notice'] = 'Account verified. You can now log in.'
                return redirect(url_for('web.login'))
            if purpose == 'login':
                finish_login(user)
                return redirect(url_for('web.account_page'))
            g.session['reset'] = {
                'id': user['id'],
                'version': user['version'],
                'expires': now().timestamp() + 300
            }
            return redirect(url_for('web.password'))
    latest = one(
        'SELECT created_at FROM otps WHERE user_id=%s AND purpose=%s ORDER BY id DESC LIMIT 1',
        (user['id'], purpose)
    )
    cooldown = max(0, math.ceil(60 - (now() - latest['created_at']).total_seconds())) if latest else 0
    seconds, _ = guard(user['username'])
    return render_template(
        'otp.html',
        title={'register': 'Verify your account', 'login': 'Verify your log-in', 'reset': 'Verify password reset'}[purpose],
        errors=errors,
        cooldown=cooldown,
        seconds=max(seconds, 0)
    )

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot():
    errors = {}
    seconds = 0
    if request.method == 'POST':
        username = request.form.get('username', '')[:256]
        seconds, _ = guard(username)
        if seconds > 0:
            errors['_form'] = 'Too many attempts. Please wait for the countdown.'
        elif not captcha_valid():
            captcha_failure()
            errors['captcha'] = 'CAPTCHA did not match. Enter the new characters shown.'
        else:
            user = account(username)
            if user:
                choices = [row['question'] for row in all_rows(
                    'SELECT question FROM security_answers WHERE user_id=%s ORDER BY question',
                    (user['id'],)
                )]
            else:
                # A stable, keyed dummy subset avoids a changing question screen
                # advertising nonexistent accounts. Only answer+OTP authorizes reset.
                key = current_app.config['ENCRYPTION_KEY'].encode()
                choices = sorted(sorted(
                    QUESTIONS,
                    key=lambda q: hmac.digest(key, f'{username.lower()}:{q}'.encode(), 'sha256')
                )[:3])
            g.session['recovery'] = {
                'username': username,
                'questions': choices,
                'expires': now().timestamp() + 900
            }
            audit('RESET_REQUESTED', username, user['id'] if user else None)
            return redirect(url_for('web.question'))
    return render_template(
        'forgot.html',
        title='Find your account',
        errors=errors,
        data=request.form,
        seconds=max(seconds, 0)
    )

@bp.route('/security-question', methods=['GET', 'POST'])
def question():
    recovery = g.session.get('recovery', {})
    if recovery.get('expires', 0) <= now().timestamp():
        return redirect(url_for('web.forgot'))
    username = recovery['username']
    seconds, _ = guard(username)
    errors = {}
    if request.method == 'POST':
        answer = request.form.get('answer', '')
        confirm = request.form.get('answer_confirm', '')
        if seconds > 0:
            errors['_form'] = 'Too many attempts. Please wait for the countdown.'
        elif answer != confirm:
            errors['answer_confirm'] = 'Answers do not match.'
        elif not answer_valid(answer):
            errors['answer'] = 'Answer must be 2–50 letters and single spaces.'
        else:
            user = account(username)
            q = request.form.get('question', '')
            answer_row = one(
                'SELECT answer_hash FROM security_answers WHERE user_id=%s AND question=%s',
                (user['id'], int(q))
            ) if user and q in [str(number) for number in recovery.get('questions', [])] else None
            matches = verify(answer_row['answer_hash'] if answer_row else None, answer.lower())
            if not matches or not user or (not user['verified']):
                fail(username, user)
                errors['answer'] = 'The account details could not be verified.'
            else:
                try:
                    message = send_otp(user, 'reset')
                    g.session['pending'] = {
                        'id': user['id'],
                        'purpose': 'reset',
                        'version': user['version'],
                        'expires': now().timestamp() + 3600
                    }
                    if message:
                        g.session['notice'] = message
                    g.session.pop('recovery', None)
                    return redirect(url_for('web.otp'))
                except DeliveryError as error:
                    errors['_form'] = str(error)
    seconds, _ = guard(username)
    return render_template(
        'question.html',
        title='Verify it is you',
        errors=errors,
        data=request.form,
        seconds=max(seconds, 0),
        recovery_questions={q: QUESTIONS[q] for q in recovery.get('questions', []) if q in QUESTIONS}
    )

@bp.route('/change-password', methods=['GET', 'POST'])
def password():
    # Check the reset grant before accepting a new password.
    grant = g.session.get('reset', {})
    if grant.get('expires', 0) <= now().timestamp():
        return redirect(url_for('web.forgot'))
    user = one('SELECT * FROM users WHERE id=%s', (grant.get('id'),))
    if not user or user['version'] != grant.get('version'):
        return redirect(url_for('web.forgot'))
    errors = {}
    if request.method == 'POST':
        value = request.form.get('password', '')
        if strength(value) == 'Weak':
            errors['password'] = 'Use 8–64 characters, at least three character groups, and no whitespace.'
        if value != request.form.get('password_confirm'):
            errors['password_confirm'] = 'Mismatch Password.'
        if not errors:
            message = change_password(user, value)
            if message:
                errors['password'] = message
            else:
                return redirect(url_for('web.login'))
    return render_template('password.html', title='Choose a new password', errors=errors, data={})

@bp.route('/logout', methods=['POST'])
@protected()
def logout():
    audit('LOGOUT', g.user['username'], g.user['id'])
    rotate_session({})
    g.user = None
    return redirect(url_for('web.login'))

@bp.route('/session', methods=['GET', 'POST'])
@protected(api=True)
def session_status():
    if request.method == 'POST':
        g.session['auth']['last_activity'] = now().timestamp()
    return jsonify(remaining=max(
        0,
        math.ceil(IDLE_SECONDS - (now().timestamp() - g.session['auth']['last_activity']))
    ))

@bp.route('/account')
@protected()
def account_page():
    count = one('SELECT count(*) AS n FROM journal_entries WHERE user_id=%s', (g.user['id'],))['n']
    entries = all_rows(
        'SELECT id,title,entry_date,mood FROM journal_entries WHERE user_id=%s ORDER BY entry_date DESC,id DESC LIMIT 3',
        (g.user['id'],)
    )
    for entry in entries:
        entry['title'] = decrypt(entry['title'], f"{g.user['id']}:entry:{entry['id']}:title")
    return render_template(
        'account.html',
        title='Your journal, your space',
        count=count,
        entries=entries,
        intention=decrypt(g.user['intention'], g.user['id'] + ':intention')
    )

@bp.route('/my-account')
@protected()
def my_account():
    return render_template('my_account.html', title='My account')

@bp.route('/settings')
@protected()
def settings_page():
    return render_template('settings.html', title='Settings')

@bp.route('/journal')
@protected()
def journal():
    try:
        page = max(1, min(100000, int(request.args.get('page', '1'))))
    except ValueError:
        page = 1
    entries = all_rows(
        'SELECT * FROM journal_entries WHERE user_id=%s ORDER BY entry_date DESC,id DESC LIMIT 21 OFFSET %s',
        (g.user['id'], (page - 1) * 20)
    )
    if page > 1 and not entries:
        return redirect(url_for('web.journal'))
    more = len(entries) > 20
    entries = entries[:20]
    for entry in entries:
        for field in ['title', 'body']:
            entry[field] = decrypt(entry[field], f"{g.user['id']}:entry:{entry['id']}:{field}")
    return render_template(
        'journal.html',
        title='Your private journal',
        entries=entries,
        page=page,
        more=more
    )

@bp.route('/journal/new', methods=['GET', 'POST'])
@bp.route('/journal/<int:entry_id>/edit', methods=['GET', 'POST'])
@protected()
def journal_edit(entry_id=None):
    entry = one(
        'SELECT * FROM journal_entries WHERE id=%s AND user_id=%s',
        (entry_id, g.user['id'])
    ) if entry_id else None
    if entry_id and (not entry):
        abort(404)
    data = {}
    errors = {}
    if entry:
        data = dict(entry)
        for key in ['title', 'body']:
            data[key] = decrypt(entry[key], f"{g.user['id']}:entry:{entry_id}:{key}")
    if request.method == 'POST':
        data = request.form
        if not 1 <= len(data.get('title', '').strip()) <= 120:
            errors['title'] = 'Title must be 1–120 characters.'
        if not 1 <= len(data.get('body', '').strip()) <= 10000:
            errors['body'] = 'Entry must be 1–10,000 characters.'
        day = date_value(data.get('entry_date', ''))
        if not day or day.isoformat() < g.user['profile']['journal_start']:
            errors['entry_date'] = 'Choose a date from your journaling start date through today.'
        if data.get('mood') not in MOODS:
            errors['mood'] = 'Please select a valid mood.'
        if not errors:
            if entry:
                lock('journal:' + str(entry_id))
                fresh = one(
                    'SELECT version FROM journal_entries WHERE id=%s AND user_id=%s',
                    (entry_id, g.user['id'])
                )
                if not fresh or str(fresh['version']) != data.get('version'):
                    errors['_form'] = 'This entry changed in another tab. Reload before saving.'
            if not errors:
                if not entry:
                    entry_id = one(
                        'INSERT INTO journal_entries(user_id,title,body,entry_date,mood) VALUES(%s,%s,%s,%s,%s) RETURNING id',
                        (g.user['id'], '', '', day, data['mood'])
                    )['id']
                word_count = len(data['body'].split())
                title = encrypt(data['title'], f"{g.user['id']}:entry:{entry_id}:title")
                body = encrypt(data['body'], f"{g.user['id']}:entry:{entry_id}:body")
                execute(
                    'UPDATE journal_entries SET title=%s,body=%s,entry_date=%s,mood=%s,word_count=%s,version=version+1,updated_at=%s WHERE id=%s AND user_id=%s',
                    (title, body, day, data['mood'], word_count, now(), entry_id, g.user['id'])
                )
                audit(
                    'JOURNAL_UPDATED' if entry else 'JOURNAL_CREATED',
                    g.user['username'],
                    g.user['id'],
                    f'Entry {entry_id}; content omitted.'
                )
                g.session['notice'] = 'Your entry has been saved.'
                return redirect(url_for('web.journal'))
    return render_template(
        'journal_edit.html',
        title='Edit your entry' if entry else 'A moment for yourself',
        data=data,
        errors=errors,
        entry=entry
    )

@bp.route('/journal/<int:entry_id>/delete', methods=['POST'])
@protected()
def journal_delete(entry_id):
    lock('journal:' + str(entry_id))
    entry = one('SELECT version FROM journal_entries WHERE id=%s AND user_id=%s', (entry_id, g.user['id']))
    if not entry:
        abort(404)
    if str(entry['version']) != request.form.get('version') or request.form.get('confirm') != 'yes':
        return (
            render_template('error.html', title='Entry not deleted', message='Confirm deletion of the current version of this entry.'),
            409
        )
    execute('DELETE FROM journal_entries WHERE id=%s AND user_id=%s', (entry_id, g.user['id']))
    audit('JOURNAL_DELETED', g.user['username'], g.user['id'], f'Entry {entry_id}; content omitted.')
    g.session['notice'] = 'Your entry has been deleted.'
    return redirect(url_for('web.journal'))

@bp.route('/privacy')
def privacy():
    return render_template('privacy.html', title='Privacy Notice')

@bp.route('/dashboard')
@protected(admin=True)
def dashboard():
    audit('ADMIN_VIEWED_DASHBOARD', g.user['username'], g.user['id'])
    return render_template('dashboard.html', title='Security overview')

@bp.route('/dashboard-data')
@protected(admin=True, api=True)
def dashboard_data():
    start = now().astimezone(PHT).replace(hour=0, minute=0, second=0, microsecond=0)
    totals = {row['event_type']: row['n'] for row in all_rows(
        'SELECT event_type,count(*) AS n FROM activity_log WHERE created_at>=%s GROUP BY event_type',
        (start,)
    )}
    cards = [
        ['Successful log-ins', totals.get('LOGIN_SUCCESS', 0)],
        ['Failed log-ins', totals.get('LOGIN_FAILED', 0)],
        ['Accounts locked now', one('SELECT count(*) AS n FROM attempt_state s JOIN users u ON lower(u.username)=s.username WHERE s.locked_until>%s', (now(),))['n']],
        ['IPs blocked now', one('SELECT count(*) AS n FROM ip_blocks WHERE blocked_until>%s', (now(),))['n']],
        ['OTPs sent', totals.get('OTP_SENT', 0)],
        ['OTPs failed', totals.get('OTP_FAILED', 0)],
        ['Alert emails sent', totals.get('ALERT_EMAIL_SENT', 0)]
    ]
    endpoint = now()
    first = endpoint - timedelta(hours=24)
    hourly = all_rows(
        "SELECT floor(extract(epoch FROM (created_at-%s))/3600)::integer AS bucket,count(*) AS n FROM activity_log WHERE event_type='LOGIN_FAILED' AND created_at>=%s AND created_at<%s GROUP BY bucket",
        (first, first, endpoint)
    )
    lookup = {row['bucket']: row['n'] for row in hourly}
    hours = [first + timedelta(hours=i) for i in range(24)]
    top = all_rows(
        "SELECT a.ip_address,count(*) AS failures,coalesce(max(b.blocked_until)>%s,false) AS blocked FROM activity_log a LEFT JOIN ip_blocks b ON a.ip_address=b.ip_address WHERE a.event_type='LOGIN_FAILED' AND a.created_at>=%s GROUP BY a.ip_address ORDER BY failures DESC,a.ip_address LIMIT 5",
        (now(), now() - timedelta(hours=24))
    )
    clauses = []
    params = []
    for key, column in [('event', 'event_type'), ('username', 'username_typed'), ('ip', 'ip_address')]:
        value = request.args.get(key, '')[:256]
        if value:
            clauses.append({
                'event': 'event_type=%s',
                'username': 'username_typed ILIKE %s',
                'ip': 'ip_address=%s'
            }[key])
            params.append('%' + value + '%' if key == 'username' else value)
    for key, comparison in [('from', '>='), ('to', '<')]:
        value = request.args.get(key, '')
        if value:
            try:
                day = datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=PHT)
                if key == 'to':
                    day += timedelta(days=1)
            except ValueError:
                return (jsonify(error='Choose valid filter dates.'), 422)
            clauses.append('created_at >= %s' if comparison == '>=' else 'created_at < %s')
            params.append(day)
    sql = 'SELECT * FROM activity_log' + (' WHERE ' + ' AND '.join(clauses) if clauses else '') + ' ORDER BY created_at DESC,id DESC LIMIT 50'
    logs = all_rows(sql, tuple(params))
    flags = all_rows('SELECT * FROM security_flags ORDER BY created_at DESC,id DESC LIMIT 50')
    for row in logs + flags:
        row['created_at'] = row['created_at'].astimezone(PHT).strftime('%Y-%m-%d %H:%M:%S PHT')
    return jsonify(
        cards=cards,
        chart={'labels': [hour.astimezone(PHT).strftime('%H:%M') for hour in hours], 'values': [lookup.get(index, 0) for index in range(24)]},
        top=top,
        flags=flags,
        events=logs,
        updated=now().astimezone(PHT).strftime('%H:%M:%S PHT')
    )
