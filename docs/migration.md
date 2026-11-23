# Optional existing-account migration

The normal setup starts a separate PostgreSQL database with no accounts. It leaves your original PHP/MySQL project untouched. Re-registering test accounts is the simplest option. Migration is optional, and was not performed on the student's real database by this build.

For a one-time import:

1. Back up your original MySQL database and private `config.php`. Stop both applications so the source stays consistent.
2. Use a **fresh empty** PostgreSQL destination created with `manage.py setup-database`. Do not open its web pages or create accounts before importing, since that creates web session data. The importer refuses a populated destination.
3. Run the read-only export bridge from PowerShell, replacing paths as needed:

   ```powershell
   New-Item -ItemType Directory -Force .\backups | Out-Null
   & 'C:\xampp\php\php.exe' .\scripts\export_mysql.php 'C:\xampp\htdocs\pejour' '.\backups\private-mysql-export.json'
   ```

4. The export contains the original encryption key and personal data. Keep it local and private. Open your **old** `config.php`, copy its `encryption_key` value into the **new** `.env` `ENCRYPTION_KEY`. Do not generate another key. Do not copy this file into static assets, a public folder, Git or an uploaded submission ZIP.
5. Import:

   ```powershell
   .\.venv\Scripts\python.exe .\scripts\migrate_mysql.py .\backups\private-mysql-export.json
   ```

All destination writes run in one PostgreSQL transaction. Duplicate IDs/usernames/emails, wrong ciphertext keys or a schema mismatch roll it back. It never deletes or writes to MySQL. It preserves IDs, Argon2id hashes, consent times, profiles, password history, encrypted journal text, events, flags, IP blocks and known account lock state. It verifies every encrypted field's authentication tag before commit and repairs sequence counters after importing explicit row IDs. Existing OTP records remain for accounting, but are marked used; web sessions and reset grants do not transfer. Log in again with a fresh OTP. Unknown username attempt states whose hashed keys cannot be matched to retained log usernames cannot be reconstructed; exported events still retain IP failure evidence.

The exporter targets the supplied Pejour PHP schema. Do not use it for unrelated databases. If a required table is missing, update the original schema first or re-register in the new application. Delete the private export securely after verifying your backup and migration. Keep your original encryption key backed up for as long as encrypted records exist.
