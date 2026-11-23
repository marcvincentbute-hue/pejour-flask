> Historical report for the November 15 build. Its former seed limits were superseded on November 16; see common-settings-verification.md for the current release.

# Verification — November 15, 2026

This report describes tests actually run on the Flask/PostgreSQL version. It does not certify production readiness or replace the live laboratory demonstration.

## Automated PostgreSQL integration checks

**20 tests passed:** 18 in the combined security/edge run, plus one real database setup/permission test and one CLI administrator/OTP test. Python 3.12, Flask 3.1.3, psycopg 3.3.9 and PostgreSQL 18.6 were used. Tests used a separate local server on port 55439, a database ending `_test`, random isolated schemas and disposable database/role names. Original MySQL data and existing PostgreSQL databases were not used.

Covered behavior:

- Core/system registration validation without browser trust; exact name errors, dates, allowlists, uniqueness, consent and hidden honeypot.
- CSRF and CAPTCHA rejection, security headers on assets/pages/errors and private file/script URLs returning 404.
- Argon2id hashes, AES-256-GCM ciphertext, fresh nonce, wrong owner/context failure and no secrets in activity details.
- Unverified login refused; authentication cannot bypass email OTP; 3 wrong codes cancel the OTP; expiry, cooldown, actual resend accounting, single-use and SMTP failure preserving the prior code.
- Generic credential/recovery failures, SQL-looking usernames, server-side lockouts at 20/40/80 seconds, shared account failure counters, success reset, alert events and cross-account 15-failure IP block.
- Opaque cookie rotation and flags, 5-minute idle expiry, heartbeat extension, logout, version invalidation and protected data unavailable before full login.
- Recovery question/answer confirmation, reset-purpose OTP, five-minute reset authorization, last-three password refusal, older password behavior and single-use grant.
- Owner-only journal operations, encrypted title/body, escaped script text, stale edit version and another user's edit/delete attempts refused.
- Admin-only dashboard/JSON, seven cards, 24 rolling-hour chart buckets, filters, access-denied audit, DB trigger rejecting activity deletion.
- Four monitor patterns, rolling OTP window, Philippine off-hours time and duplicate suppression.
- Optional synthetic legacy import: original hashes/ciphertext/IDs/version preserved, sequence restored, bad ciphertext aborts and rolls back, populated destination refused. This was not a migration of the student's real accounts.
- Actual setup command created a new disposable database and non-owner runtime role; SELECT/INSERT logs worked, UPDATE/DELETE/TRUNCATE and schema CREATE failed. Cleanup touched only the exact generated test database/role.
- CLI-created admin still needed password, CAPTCHA and email OTP to access the monitoring data.

## Browser checks

Headless installed Chrome was used at **1440 × 1000** and **390 × 844**. Tests exercised live username checking, field validation, duplicate-ID AJAX errors retaining password/recovery answers in the current DOM, registration email OTP, login email OTP, journal create/list, dashboard filters, mobile width and logout/Back protection. No JavaScript exceptions or alert dialogs occurred. QA mail and CAPTCHA inputs were mocked in an external test harness; production code does not expose test-control routes. Screenshots were visually reviewed against the requested mint/teal/lavender palette.

The final dashboard uses a bounded scrollable event table and mobile navigation. The real application starts empty and has no bundled default accounts or mock inbox.

## Remaining live work

1. Run setup with your own PostgreSQL administrator credentials; the generated `.env` remains private.
2. Configure Gmail App Password and receive a **real test email on this Flask version**. Automated mocks are not proof of SMTP connectivity. The earlier PHP test email does not prove the new configuration works.
3. Create your real admin and two demo users with accessible inboxes; demonstrate alert emails and every flow on the actual lab network.
4. If wanted, back up and migrate real MySQL data using the optional instructions; otherwise re-register test accounts. No real accounts were copied by this build.
5. Preserve genuine Git/checkpoint evidence and complete your own weekly journal, signed proposal, populated SQL dump and live explanations.

## Rerunning tests

Install `pytest` separately from the runtime requirements. Create a disposable PostgreSQL database whose name ends `_test`, then set its connection URL in `PEJOUR_TEST_DSN`. Run `python -m pytest tests -q`. The setup test also creates/removes one disposable database and role, so its test administrator needs those privileges. Never use your production/database-owner credentials against a real database for a test run. Tests do not run automatically during normal setup or server startup.
