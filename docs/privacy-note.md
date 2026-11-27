# Pejour Privacy Note

This is a classroom data inventory and a conservative classification assessment. It explains the fields in this project; it is not a legal-compliance certificate. The statutory definitions distinguish ordinary identifying information from specified sensitive categories, including age and education. Fields may also reveal sensitive content through their context. See RA 10173 sections 3(g), 3(l) and 11 on the [National Privacy Commission’s official text](https://privacy.gov.ph/data-privacy-act/). The context-dependent classifications below are project inferences from those definitions.

| Field or group | Classification for this project | Why it is collected and how it is handled |
| --- | --- | --- |
| ID Number | Treat as sensitive education-linked identification when it identifies a student | Handout-required unique account primary key; use fictional IDs for lab tests. |
| First, Middle and Family Name; Name Extension | Personal information | Handout-required account identity. Middle name and extension are optional. |
| Birthdate and derived Age | Treat as sensitive age information | Handout-required adult eligibility check. Age is recomputed from birthdate; no separate posted age is trusted. |
| Purok / Street, Barangay, City, Province, Country and ZIP | Personal information | Required by the handout; not needed for journal prompts. Use fictional classroom addresses rather than expanding real collection. |
| Email | Personal information | Deliver verification, login, recovery and security messages to an inbox the owner controls. |
| Username | Account-linked personal information | Identifies the account during authentication. Registration availability is intentionally public; login/recovery failures remain generic. |
| Password and password-history hashes | Authentication secrets linked to personal information | Authenticate and refuse recent password reuse. Store only salted hashes; do not send in email or logs. Security sensitivity is not itself a claim that every credential is a statutory sensitive category. |
| Three security answers | Authentication secrets; may reveal sensitive education or family context | Required recovery factor, combined with email OTP. Normalize lowercase and hash; never display stored answers. |
| OTP hashes, purpose, attempts and expiry | Account-linked security data | Authorize one verification step, cancel guesses and enforce expiry/resend limits. Store only a hash of each code. |
| Journal Display Name | Personal information when linked to the account | Labels the owner’s private journal. |
| Journaling Start Date | Account-linked personal metadata | Sets the earliest permitted journal-entry date. |
| Writing Goal | Personal preference | Displays the chosen journal category and selects its matching writing prompt. |
| Private Journaling Intention | Personal information; potentially sensitive depending on disclosed content | Records the owner’s purpose. Encrypt with AES-256-GCM; display only after ownership checks. |
| Journal titles and entry text | Personal information; potentially sensitive if health, beliefs or other protected matters are written | Core private-journal content; encrypt and bind to owner, entry ID and field. |
| Mood and entry dates | Personal metadata; potentially health-sensitive in context | Organize reflections and preserve the owner’s emotional/date context. They are not encrypted in the current schema and are not presented as a diagnosis. |
| Consent timestamp | Account-linked personal metadata | Records when the required consent was given. |
| IP, browser/user agent, typed username, event time and security details | Account-linked monitoring information, which can be personal information | Detect attacks and document security actions. Do not log passwords, answers, OTPs or private journal content. |
| Security flags, account role and lockout state | Derived account/security metadata | Restrict administration, show attack findings and enforce access limits. |

The web Privacy Notice identifies collection, purposes, safeguards, retention and the project contact. Test data is intended to remain only through grading and to be removed, with backups, within thirty days afterwards. The developer must actually carry out and verify that cleanup; a policy sentence is not a deletion mechanism. Account removal must be coordinated with the separately retained append-only security history and the project’s final retention procedure.

Use fictional identity/address/journal data and real inboxes you control for demo accounts. Keep the private encryption key separate from exported data. An administrator dashboard cannot browse other users’ journals through the application, but a server maintainer possessing the key and database access can decrypt records. Treat exported backups accordingly.
