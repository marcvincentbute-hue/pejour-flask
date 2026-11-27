"""SMTP STARTTLS. Secrets come from .env; email bodies are never logged."""
import smtplib
import ssl
from email.message import EmailMessage
from flask import current_app
from .security import audit, now, PHT

class DeliveryError(Exception):
    pass

def send_email(to, subject, body):
    message = EmailMessage()
    message['From'] = 'Pejour <' + current_app.config['MAIL_FROM'] + '>'
    message['To'] = to
    message['Subject'] = 'Pejour — ' + subject
    message.set_content(body)
    # Only injected by automated tests, never selected by a browser parameter.
    if current_app.config.get('TEST_MAILER') and current_app.testing:
        current_app.config['TEST_MAILER'](to, subject, body)
        return
    try:
        with smtplib.SMTP(
            current_app.config['SMTP_HOST'],
            current_app.config['SMTP_PORT'],
            timeout=15
        ) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(current_app.config['SMTP_USERNAME'], current_app.config['SMTP_PASSWORD'])
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        # Avoid logging SMTP exception messages that may include server content.
        current_app.logger.error('SMTP delivery failed (%s)', type(error).__name__)
        raise DeliveryError('Email could not be sent. Please try again later.') from None

def alert(user, subject, failures):
    from flask import request
    text = f"{subject}\nFailed attempts: {failures}\nTime: {now().astimezone(PHT):%Y-%m-%d %H:%M:%S} PHT\nIP address: {request.remote_addr}\nBrowser: {request.headers.get(
        'User-Agent',
        'Unknown'
    )}\nIf this was not you, reset your password now:\n" + current_app.config['BASE_URL'] + '/forgot-password'
    try:
        send_email(user['email'], subject, text)
        audit('ALERT_EMAIL_SENT', user['username'], user['id'], subject)
    except DeliveryError:
        audit('ALERT_EMAIL_FAILED', user['username'], user['id'], 'Delivery failed; see private error log.')
