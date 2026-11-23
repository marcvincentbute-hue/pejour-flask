# Install the November 16 settings update

Keep your existing database and `.env`. Do not run setup-database again, re-generate keys, delete accounts, or replace your existing folder with an empty installation.

1. Stop the running server with Ctrl+C in its terminal.
2. Extract the updated ZIP to a **separate temporary folder**.
3. Open PowerShell inside that extracted `pejour-flask` folder and run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\install-update.ps1 -Target "C:\Users\nenia\OneDrive\Desktop\Marc\pejour-flask"
   ```

4. The helper copies release files only, preserving your `.env`, virtual environment, runtime logs and backups. It removes the obsolete generated `docs/seed.md` table. The database-upgrade command asks for the PostgreSQL **schema owner** (usually postgres) and its password, because the restricted application account is deliberately not allowed to alter tables. Nothing prints or changes your private credentials.
5. The only database structure change is widening `users.username` from 18 to 20 characters. The upgrade is safe to run again. It preserves IDs, names, password hashes, selected security answers, consent timestamps, logs, flags, journal ciphertext and the encryption key. No data is deleted and no permission is elevated for the normal runtime role.
6. In your existing project folder, start the server again:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\start.ps1
   ```

If the helper reports a database connection error, check PostgreSQL and the owner password, then run `.\.venv\Scripts\python.exe manage.py upgrade`. Do not use your Gmail App Password at the database prompt.

Log in again and reload any old registration tabs. Request a fresh OTP if one was issued before the update; previously issued codes and lockouts keep their original stored deadlines, while new codes and lockouts use the new settings. No new Python packages are required.

For a completely new installation, follow README.md and setup.ps1. Do not use this update helper to copy a folder onto itself.
