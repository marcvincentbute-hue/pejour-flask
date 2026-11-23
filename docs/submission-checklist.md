# Student submission tasks

- Keep the approved Pejour proposal, with instructor signature and date. Record the allowed Flask/PostgreSQL substitution accurately; this package does not supply instructor evidence.
- No seed table is required after the November 16 announcement. Use the exact class-wide values in `security-settings.md`; the approved System Proposal and Checkpoint 1 still apply.
- Preserve genuine existing Git history. Create a repository for the new source and commit meaningful changes; the required 30 commits across four weeks cannot be manufactured retroactively.
- Complete the weekly development journal in your own words. Use the blank template, not invented progress.
- Review the threat model, design decisions, privacy inventory and complete error mapping. Explain the Python equivalents to the handout's PHP functions.
- Configure real SMTP; receive a test email. Create one admin and two users with inboxes you can open. Run registration, login, alerts and recovery with real email on this Flask version.
- Export a populated PostgreSQL SQL dump using pgAdmin Backup (plain SQL) or `pg_dump`, with the required tables and at least five test records. Save it privately; it contains personal data and hashes. The supplied schema file is not a populated dump.
- Keep application runtime role separate from the database owner. Protect backups and .env. Use fictional journal content during the demo.
- Practice the six-minute flow demo, six-minute code explanation and eight-minute new requirement without AI. A feature you cannot explain still scores zero.
- The monitor command is `python manage.py monitor`. If scheduled, show your own Task Scheduler configuration; no OS task was silently installed.
- The live dates supplied in chat are checkpoints 2–4 November 16, 2026 and tentative demo November 21, 2026. Confirm any updated schedule with your instructor.
