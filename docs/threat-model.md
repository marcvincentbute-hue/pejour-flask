# Threat model

| # | Threat and weakness | Countermeasure | CIA | Verification |
| --- | --- | --- | --- | --- |
| 1 | SQL input changes a query | psycopg bind parameters, fixed dynamic-filter fragments | C/I | SQL-looking username refused without SQL errors |
| 2 | Attacker text executes in owner's/admin's browser | Jinja autoescape, textContent, CSP | C/I | Script-looking journal/log values render as text |
| 3 | Another site submits an action | Random server-side CSRF token, every POST checked | I | Missing/incorrect token rejected and logged |
| 4 | Responses reveal login/recovery account existence | Same generic failures and question set, dummy hash verification | C | Known and unknown flows compared |
| 5 | Distributed usernames bypass account lock | IP counter over all account failures, 10/10 minutes ->10-minute block | A/C | Cross-account failure test |
| 6 | Stolen/fixed/stale browser session | Opaque random ID rotation, hashed server key, cookie flags, idle/version checks | C | Pre-OTP/session-expiry/logout checks |
| 7 | Password cycling reuses compromised secret | Current and last three Argon2id hashes checked under account lock | C | Recovery rejects current/recent password |
| 8 | Form-filling bots | Server-rejected hidden honeypot and CAPTCHA | A | Honeypot populated; CAPTCHA omitted/wrong |
| 9 | Attack has no evidence | Append-only event data with UTC/PHT time, IP and browser | I | Dashboard and monitor inspected |
| 10 | Error pages expose code, paths, query details | Generic error template; private runtime log; debug off | C | Injected exception produces generic 500 |
| 11 | Secrets are downloaded or committed | Private .env, no file-serving routes, Gitignore | C | Private paths 404, package exclusions checked |
| 12 | Frame embedding/MIME confusion | DENY, nosniff and same-origin CSP every response | C/I | Header assertions on pages, assets and errors |
| 13 | Database reader learns private journal | AES-256-GCM unique nonce/tag + owner/field AAD | C/I | Ciphertext unreadable, wrong owner/context fails |

Assessment evidence in verification.md states automated coverage and remaining manual checks. Never tick a live test until you have run it yourself.
