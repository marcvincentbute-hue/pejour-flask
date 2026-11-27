"""Flask application factory. Run with Waitress; debugging is always off."""
import base64
import logging
import os
from pathlib import Path
from flask import Flask, g, request, render_template, jsonify
from dotenv import load_dotenv
from .db import connection
from .security import load_session, save_session, csrf_valid, audit
ROOT = Path(__file__).resolve().parent.parent

def create_app(overrides=None):
    load_dotenv(ROOT / '.env')
    app = Flask(__name__, static_url_path='/static')
    app.config.update(
        DATABASE_URL=os.getenv('DATABASE_URL', ''),
        ENCRYPTION_KEY=os.getenv('ENCRYPTION_KEY', ''),
        SMTP_HOST=os.getenv('SMTP_HOST', 'smtp.gmail.com'),
        SMTP_PORT=int(os.getenv('SMTP_PORT', '587')),
        SMTP_USERNAME=os.getenv('SMTP_USERNAME', ''),
        SMTP_PASSWORD=os.getenv('SMTP_PASSWORD', ''),
        MAIL_FROM=os.getenv('MAIL_FROM', 'pejourproject@gmail.com'),
        PRIVACY_CONTACT=os.getenv('PRIVACY_CONTACT', 'pejourproject@gmail.com'),
        BASE_URL=os.getenv('BASE_URL', 'http://127.0.0.1:8088').rstrip('/'),
        COOKIE_SECURE=os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
        MAX_CONTENT_LENGTH=128 * 1024,
        DEBUG=False,
        TESTING=False
    )
    if overrides:
        app.config.update(overrides)
    (ROOT / 'runtime').mkdir(exist_ok=True)
    handler = logging.FileHandler(ROOT / 'runtime' / 'error.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    app.logger.handlers = [handler]
    try:
        key = base64.b64decode(app.config['ENCRYPTION_KEY'], validate=True)
        if len(key) != 32 or not app.config['DATABASE_URL']:
            raise ValueError()
    except (ValueError, TypeError):
        raise RuntimeError('Configure DATABASE_URL and a valid 32-byte ENCRYPTION_KEY in .env. See README.md.') from None

    @app.before_request
    def before():
        if request.endpoint == 'static':
            return None
        # Load the session before checking submitted forms.
        load_session()
        if request.method == 'POST' and (not csrf_valid()):
            audit('CSRF_REJECTED', request.form.get('username'))
            message = 'Your request could not be verified. Please try again.'
            if request.headers.get('Accept') == 'application/json':
                return (jsonify(ok=False, errors={'_form': message}, csrf=g.session['csrf']), 403)
            return (render_template('error.html', title='Request not verified', message=message), 403)

    @app.after_request
    def after(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Cache-Control'] = 'no-store, private'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
        if 'db' in g:
            if response.status_code >= 500:
                g.db.rollback()
            else:
                if hasattr(g, 'session'):
                    save_session(response)
                g.db.commit()
        return response

    @app.teardown_appcontext
    def close(error):
        db = g.pop('db', None)
        if db:
            db.close()

    @app.errorhandler(Exception)
    def error_handler(error):
        from werkzeug.exceptions import HTTPException
        if isinstance(error, HTTPException):
            return (
                render_template('error.html', title='Page not found' if error.code == 404 else 'Request could not be completed', message='Please use the navigation to continue.'),
                error.code
            )
        if 'db' in g:
            g.db.rollback()
        # Traceback frames contain code locations, not request bodies or configuration.
        app.logger.exception('Unhandled server error')
        return (
            render_template('error.html', title='Something went wrong', message='Please try again later.'),
            500
        )
    from .views import bp
    app.register_blueprint(bp)
    return app
