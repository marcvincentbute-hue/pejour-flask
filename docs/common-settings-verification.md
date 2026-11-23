# November 16 class-wide settings verification

The release follows the announcement pasted by the student. The supplied PDF was inspected but still has the older formulas; see security-settings.md for the source discrepancy. No instructor approval evidence is fabricated.

**24 automated tests verified successfully across the full run and targeted reruns.** The first run reported 22 passing tests and one test-harness transaction-cleanup failure; the harness was corrected and that database setup/upgrade test passed on a new disposable database. The added exact-ten monitor-threshold test also passed. All tests used an isolated PostgreSQL server/database and generated test schemas. No student's real database or credentials were used.

New or updated assertions include:

- Username 5 rejected, 6 accepted, 20 accepted, 21 rejected; functional uniqueness retained.
- Password 8 accepted when it satisfies the existing strength policy, 7 rejected; current/recent password rejection unchanged.
- Valid 50-character name accepted and 51 rejected; other name rules preserved.
- Forgot Password appears after exactly two consecutive failures.
- Locks at 3/6/9 failures have 15/30/60-second stored deadlines.
- New OTP expires after five minutes and email text says five minutes; purpose, cancellation, attempts, resends and single-use checks retained.
- Idle session warning in the final minute of a 900-second lifetime, heartbeat extension and expiry after 900 seconds; five-minute reset grant remains separate.
- IP blocked at the tenth failure across usernames; no block after nine. Monitor detects ten failures but not nine.
- Duplicate/missing/fake question choices rejected; exactly the selected three rows stored as hashes. Selecting Q1/Q4/Q7 works; recovery offers only those questions and rejects a forged Q8. Existing Q3/Q5/Q8 rows remain usable and unchanged. Unknown usernames receive three stable dummy choices and generic failures.
- CLI admin chooses three questions and still requires CAPTCHA/password/email OTP to access admin data.
- Upgrade widens an old 18-character username column to 20, runs idempotently and preserves fixture hashes/ciphertext. Runtime role remains unable to update/delete/truncate security logs or create schema tables.
- Existing authentication, journal ownership/encryption, CSRF/CAPTCHA, protected routes, headers, dashboard and four-pattern monitor tests retained.

**Chrome browser flow passed:** a 20-character username, an eight-character accepted password, duplicate-question feedback, Q1/Q4/Q7 registration, OTP verification, login, journal creation, recovery through the actual registered question, reset OTP, eight-character new password, dashboard filters, desktop/mobile width and logout/Back protection. No JavaScript exceptions or alert dialogs occurred. Test email/CAPTCHA were mocked in an external harness, not in the release's routes.

**Update helper passed on a disposable project copy:** copied source files, invoked upgrade, preserved the byte-for-byte synthetic .env, virtual-environment marker and runtime marker, and removed the obsolete seed table. The real desktop installation was not modified by these tests.

Remaining user step: stop the server, run install-update.ps1 against the existing desktop project and supply the PostgreSQL schema-owner password when asked. Keep the .env and encryption key. Restart and receive real emails in the student's lab setup; mocks are not SMTP evidence. Signed proposal, genuine Git/weekly journal, SQL dump and live explanation requirements remain.
