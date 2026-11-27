"""Shared registration rules. Browser validation mirrors these; the server decides."""
import re
import unicodedata
from datetime import date
from .security import now, PHT
from .settings import USERNAME_MIN, USERNAME_MAX, PASSWORD_MIN, NAME_MAX
QUESTIONS = {
    1: 'What was the name of your first pet?',
    2: 'Who was your best friend in elementary school?',
    3: 'Who was your favorite teacher in high school?',
    4: 'What is your mother’s maiden first name?',
    5: 'What street did you live on in Grade 1?',
    6: 'What was the first song you learned by heart?',
    7: 'What was the name of your elementary school?',
    8: 'What dish did you cook for the first time?'
}
GOALS = ['Self Reflection', 'Gratitude', 'Daily Memories', 'Personal Growth']
MOODS = ['Calm', 'Happy', 'Hopeful', 'Tired', 'Sad', 'Anxious']

def today():
    return now().astimezone(PHT).date()

def date_value(value):
    try:
        parsed = date.fromisoformat(value)
        return parsed if len(value) == 10 and parsed <= today() else None
    except (ValueError, TypeError):
        return None

def age(value):
    birth = date_value(value)
    day = today()
    return day.year - birth.year - ((day.month, day.day) < (birth.month, birth.day)) if birth else None

def strength(value):
    groups = sum((bool(re.search(p, value)) for p in ['[a-z]', '[A-Z]', '[0-9]', '[^A-Za-z0-9\\s]']))
    if not PASSWORD_MIN <= len(value) <= 64 or re.search('\\s', value) or groups < 3:
        return 'Weak'
    return 'Strong' if len(value) >= 14 and groups == 4 else 'Medium'

def name_error(value, label, required=True):
    if not value:
        return f'{label} is required.' if required else ''
    if re.search('[0-9]', value):
        return f'Numbers are not allowed in {label}.'
    if not re.fullmatch('[A-Za-z ]+', value):
        return f'Special characters are not allowed in {label}.'
    if '  ' in value:
        return 'Double space is not allowed.'
    if value.strip() != value:
        return f'{label} must not start or end with a space.'
    if value.upper() == value:
        return 'Do not use all capital letters.'
    if re.search('([a-z])\\1\\1', value, re.I):
        return 'Three consecutive identical letters are not allowed.'
    if not re.fullmatch('[A-Z][a-z]*(?: [A-Z][a-z]*)*', value):
        return 'First letter of your name must be capital.'
    if not 2 <= len(value) <= NAME_MAX:
        return f'{label} must be 2–{NAME_MAX} characters.'
    return ''

def username_valid(value):
    return USERNAME_MIN <= len(value) <= USERNAME_MAX and bool(re.fullmatch('[A-Za-z][A-Za-z0-9]*', value))

def selected_questions(data):
    return [int(data.get(
        f'question_{slot}',
        '0'
    )) if str(data.get(f'question_{slot}', '')).isdigit() else 0 for slot in range(1, 4)]

def answer_valid(value):
    return 2 <= len(value) <= 50 and bool(re.fullmatch('[A-Za-z]+(?: [A-Za-z]+)*', value))

def registration_errors(data):
    errors = {}

    def check(key, valid, message):
        if not valid:
            errors[key] = message
    check(
        'id',
        re.fullmatch('[0-9]{4}-[0-9]{4}', data.get('id', '')),
        'ID Number must follow the format xxxx-xxxx.'
    )
    for key, label in [
        ('first_name', 'First Name'),
        ('middle_name', 'Middle Name'),
        ('family_name', 'Family Name')
    ]:
        message = name_error(data.get(key, ''), label, key != 'middle_name')
        if message:
            errors[key] = message
    check(
        'name_extension',
        data.get('name_extension', '') in ['', 'Jr.', 'Sr.', 'Other'],
        'Please select a valid name extension.'
    )
    if data.get('name_extension') == 'Other':
        check(
            'extension_other',
            data.get('extension_other') in ['I', 'II', 'III', 'IV', 'IX', 'X'],
            'Name Extension must be I, II, III, IV, IX or X.'
        )
    years = age(data.get('birthdate', ''))
    check('birthdate', years is not None, 'Please enter a valid birthdate that is not in the future.')
    if years is not None:
        check('birthdate', years >= 18, 'You must be at least 18 years old to register.')
    street = data.get('street', '')
    check(
        'street',
        re.fullmatch('[A-Za-z0-9]+(?: [A-Za-z0-9]+)*', street) and 3 <= len(street) <= 50,
        'Purok / Street must be 3–50 letters, digits and single spaces without leading or trailing spaces.'
    )
    for key, label in [
        ('barangay', 'Barangay'),
        ('city', 'Municipality / City'),
        ('province', 'Province'),
        ('country', 'Country')
    ]:
        value = data.get(key, '')
        maximum = 100 if key == 'country' else 50
        check(
            key,
            2 <= len(value) <= maximum and re.fullmatch('[A-Z][a-z]*(?: [A-Z][a-z]*)*', value),
            f'{label} must be 2–{maximum} letters and single spaces in Title Case.'
        )
    check(
        'zip_code',
        re.fullmatch('[0-9]{4}', data.get('zip_code', '')),
        'ZIP Code must contain exactly 4 digits.'
    )
    email = data.get('email', '')
    check(
        'email',
        len(email) <= 100 and re.fullmatch('[^@\\s]+@[^@\\s]+\\.[^@\\s]+', email),
        'Please enter a valid email address.'
    )
    check(
        'username',
        username_valid(data.get('username', '')),
        f'Username must start with a letter and contain {USERNAME_MIN}–{USERNAME_MAX} letters and digits.'
    )
    check(
        'password',
        strength(data.get('password', '')) != 'Strong',
        'Use 14-64 characters with uppercase, lowercase, a number, and a symbol. No spaces.'
    )
    check(
        'password_confirm',
        data.get('password') == data.get('password_confirm'),
        'Passwords do not match.'
    )
    selected = selected_questions(data)
    for slot, q in enumerate(selected, 1):
        check(f'question_{slot}', q in QUESTIONS, 'Please select a question from the question bank.')
        if q in QUESTIONS and selected.count(q) > 1:
            errors[f'question_{slot}'] = 'Choose three different security questions.'
        check(
            f'answer_{slot}',
            answer_valid(data.get(f'answer_{slot}', '')),
            'Answer must be 2–50 letters and single spaces.'
        )
    errors.update(journal_profile_errors(data))
    intention = data.get('intention', '')
    check(
        'intention',
        10 <= len(intention.strip()) and len(intention) <= 300 and (not any((unicodedata.category(c) == 'Cc' for c in intention))),
        'Private Journaling Intention must be 10–300 characters without control characters.'
    )
    check('consent', data.get('consent') == '1', 'You must agree to the Privacy Notice to register.')
    return errors


def journal_profile_errors(data):
    errors = {}

    def check(key, valid, message):
        if not valid:
            errors[key] = message

    display = data.get('display_name', '')
    check(
        'display_name',
        2 <= len(display) <= 30 and re.fullmatch('[A-Za-z0-9]+(?: [A-Za-z0-9]+)*', display),
        'Journal Display Name must be 2–30 letters, digits and single spaces.'
    )
    check(
        'journal_start',
        date_value(data.get('journal_start', '')),
        'Journaling Start Date must be a valid date that is not in the future.'
    )
    check('writing_goal', data.get('writing_goal') in GOALS, 'Please select a valid writing goal.')
    return errors
