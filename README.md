# Pejour — Flask + PostgreSQL

**November 16 update:** the instructor replaced student-number formulas with shared settings and user-selected questions. For your existing installed project, follow `docs/update-nov16.md` and `install-update.ps1`; do not create another database or overwrite your private `.env`. No seed table is required. See `docs/security-settings.md`.

Private Personal Journal for student **241-01057**. English UI; mint, teal and lavender glass theme throughout. Instructor stack flexibility was confirmed by the student on November 15, 2026. The original PHP/MySQL project is preserved separately.

## Windows setup

1. Install Python **3.12 or newer** from https://www.python.org/downloads/windows/ and select **Add Python to PATH**. PostgreSQL 18 is already present on this computer. Reopen PowerShell after installing Python.
2. Extract this ZIP to a new folder, for example `C:\xampp\htdocs\pejour-flask`. Flask does not need XAMPP Apache or MySQL. Keep your old `pejour` folder.
3. Open PowerShell in the extracted folder and run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup.ps1
   ```

4. The setup asks for your **PostgreSQL administrator password**, chosen when PostgreSQL was installed. This is different from your Gmail password and the blank MySQL password. It creates a separate database `pejour_flask` and app role `pejour_flask_app`. Existing databases and accounts are not changed. If the names already exist, choose other names. The app role does not own the schema and cannot change/delete/truncate activity logs.
5. Open `.env` in your editor. Put your Google **App Password** in `SMTP_PASSWORD` without the display spaces. Keep it private. The database password and encryption key are generated automatically. Keep a safe private backup of this file; changing the encryption key makes existing journal text unreadable.
6. Test email and start:

   ```powershell
   .\.venv\Scripts\python.exe manage.py test-email
   .\start.ps1
   ```

7. Open **http://127.0.0.1:8088**. Stop the old PHP server first if port 8088 is occupied, or run `manage.py serve --port 8089` and change `BASE_URL` in `.env` to match.

If PowerShell blocks a script, use `powershell -ExecutionPolicy Bypass -File .\start.ps1` for that run. No permanent system policy change is needed. To use HTTPS hosting, set `COOKIE_SECURE=true`, set your public `BASE_URL`, use a TLS reverse proxy, and keep the application bound to a private interface. Do not enable Flask debug mode. Forwarded IP headers are deliberately not trusted on this local setup.

## Admin and monitoring

```powershell
.\.venv\Scripts\python.exe manage.py create-admin
.\.venv\Scripts\python.exe manage.py monitor
```

The admin is created only through the terminal and uses the normal email OTP login. No default admin password exists. Register two user accounts with real inboxes separately. The Security monitor link appears for admins. The monitor scans 24 hours and writes deduplicated PHT-day flags. Run it manually in the demo; see `docs/design-decisions.md` for Windows Task Scheduler.

## Existing PHP accounts

This is a **separate database**. It starts with no accounts. Your original accounts remain in MySQL and cannot log in here until re-registered or explicitly migrated. Nothing deletes or automatically copies your real personal data or SMTP secrets. `scripts/migrate_mysql.py` provides an optional one-way, transaction-protected import from the previous Pejour schema; read `docs/migration.md` before using it. It preserves password hashes and encrypted payloads when the original encryption key is configured. Back up first.

## Project map

| File/folder | Purpose |
| --- | --- |
| `manage.py` | Start server, database setup, create admin, SMTP test, monitor |
| `pejour/__init__.py` | App factory, CSRF gate, transaction/session lifecycle, headers/errors |
| `pejour/db.py` | Parameterized PostgreSQL access and transaction locks |
| `pejour/security.py` | Argon2id, AES-256-GCM, opaque server-side sessions, CSRF |
| `pejour/auth.py` | OTPs, lockouts, alerts, reset grant and password history |
| `pejour/validation.py` | Registration validation and eight-question bank |
| `pejour/settings.py` | Shared security limits from the November 16 announcement |
| `pejour/views.py` | Routes; owner/admin authorization and journal actions |
| `pejour/monitor.py` | Four security detection patterns, no browser route |
| `pejour/templates/` | Autoescaped Jinja HTML and consistent header/footer |
| `pejour/static/css/app.css` | Shared mint/teal/lavender design tokens |
| `pejour/static/js/` | Validation, CAPTCHA, DOM-only form preservation, timers and dashboard |
| `pejour/schema.sql` | PostgreSQL schema; append-only log trigger |
| `.env` | Your private local configuration, excluded from ZIP and Git |

## Security behavior

Class-wide settings: username 6–20, password 8–64, name maximum 50; 2 failures show reset link; lockouts 15/30/60 seconds at 3/6/9 failures; 5-minute OTP; 15-minute idle session; IP blocks at 10 failures/10 minutes for 10 minutes; three user-selected questions. Passwords need at least 3 character groups and no whitespace. Last 3 passwords cannot be reused. OTPs allow 3 wrong guesses, 60-second resend cooldown and 3 actual resends per 15 minutes.

Tokens, passwords and recovery answers never enter browser storage. Registration with JavaScript keeps typed secrets in the current page while errors are fixed. Without JavaScript, server errors still work, but secret fields are cleared after the page reloads. Admins see security metadata, never another owner's decrypted journal. Logs intentionally omit passwords, answers, codes and journal text.

The old handout's PHP/GD/PHPMailer mechanisms are replaced by equivalent Python implementations: Pillow CAPTCHA, `secrets` random values, `smtplib` STARTTLS, Argon2id and `cryptography` AES-GCM. JavaScript files must be served to the browser and remain readable. Real authorization stays on the server; private modules, scripts, `.env` and logs have no web routes.

## Assessment and tests

See `docs/common-settings-verification.md` for actual automated results and remaining live checks. Install test dependencies with `python -m pip install pytest`; tests require a dedicated PostgreSQL test database and refuse non-test database names. Never point them at your real project database.

Keep your genuine Git history and weekly journal. This package does not fabricate 30 commits, four weeks of work, signatures or live email delivery evidence. Read the source and practice explaining it; the live additional requirement must be completed without AI.

Implementation references: [Flask quickstart](https://flask.palletsprojects.com/en/stable/quickstart/) and [Psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html).
