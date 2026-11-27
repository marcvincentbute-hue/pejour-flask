"""CLI-only monitoring. This module is not a Flask route."""
from collections import defaultdict, deque
from datetime import timedelta
from .db import all_rows, execute
from .security import now, PHT
from .settings import IP_FAILURE_THRESHOLD

def scan():
    events = all_rows(
        'SELECT * FROM activity_log WHERE created_at>=%s ORDER BY created_at,id',
        (now() - timedelta(hours=24),)
    )
    ip = defaultdict(list)
    names = defaultdict(set)
    guesses = defaultdict(deque)
    findings = {}

    def flag(pattern, target, severity, details):
        findings[pattern, target] = (severity, details)
    for row in events:
        target = (row['username_typed'] or row['user_id'] or 'unknown').lower()
        if row['event_type'] == 'LOGIN_FAILED':
            ip[row['ip_address']].append(target)
            names[target].add(row['ip_address'])
        if row['event_type'] == 'OTP_FAILED':
            target = row['user_id'] or target
            window = guesses[target]
            window.append(row['created_at'])
            while window and (row['created_at'] - window[0]).total_seconds() > 600:
                window.popleft()
            if len(window) >= 5:
                flag('OTP guessing', target, 'MEDIUM', '5 or more wrong OTPs within 10 minutes.')
        if row['event_type'] == 'LOGIN_SUCCESS' and row['created_at'].astimezone(PHT).hour < 5:
            flag('Off-hours log-in', target, 'MEDIUM', 'Successful log-in between midnight and 5 AM PHT.')
    for target, values in ip.items():
        if len(values) >= IP_FAILURE_THRESHOLD:
            flag(
                'IP over threshold',
                target,
                'HIGH',
                f'{len(values)} failures, {len(set(values))} usernames in 24 hours.'
            )
    for target, values in names.items():
        if len(values) >= 3:
            flag('Account targeted', target, 'MEDIUM', f'Failures from {len(values)} IP addresses.')
    added = 0
    for (pattern, target), (severity, details) in findings.items():
        result = execute(
            'INSERT INTO security_flags(pattern,target,severity,details,flag_date) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(pattern,target,flag_date) DO NOTHING',
            (pattern, target, severity, details, now().astimezone(PHT).date())
        )
        added += result.rowcount
    return {'scanned': len(events), 'added': added, 'existing': len(findings) - added, 'findings': findings}
