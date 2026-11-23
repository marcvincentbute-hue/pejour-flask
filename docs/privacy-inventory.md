# Privacy inventory

This educational inventory is not legal advice. Follow the course's RA 10173 discussion and your institution's instructions when classifying or retaining data.

| Data | Why collected | Protection / sensitivity |
| --- | --- | --- |
| ID number, first/middle/family names, extension | Required core identity record | Personal information, unique ID primary key |
| Birthdate, derived age | Enforce age 18 and above | Personal information; age may be sensitive personal information under RA 10173 |
| Street, barangay, city, province, country, ZIP | Core address required by handout | Personal location information; no claim that journal personalization requires a full address |
| Email | OTP and security alert delivery | Personal information; lowercase unique; Gmail receives recipient/address metadata |
| Username | Identify account for login/recovery | Personal information; case-insensitive unique; availability lookup intentionally public per registration requirement |
| Password, security answers, OTP | Authentication/recovery comparison only | Security-sensitive credentials; salted Argon2id hashes, never plaintext logs |
| Privacy consent timestamp | Show consent before account creation | Personal/accountability metadata |
| Display name | Personalize journal UI | Personal information; 2–30 letters/digits/single spaces |
| Journal start date | Bound entry dates and show writing history | Personal behavioral metadata; plaintext database field |
| Writing goal | Select a relevant reflection prompt | Personal preference; fixed allowed values |
| Private intention | Remember the owner's reason for journaling | AES-256-GCM; may contain sensitive personal information depending on content |
| Journal title/body | The system's core private writing | AES-256-GCM; content may disclose health, beliefs or other sensitive information |
| Journal date/mood | Organize and reflect on entries | Plaintext metadata; mood may imply health information depending on use |
| IP, user agent, typed username, event time | Detect attacks, show read-only security dashboard | Personal/security metadata; values escaped; journal content and secrets omitted |

Only owners receive decrypted intention and entries; admins read security metadata. Server operators with the encryption key and database are trusted. No advertising/tracking integration is included. Keep test data through assessment, then perform documented manual cleanup within 30 days of final grading, including private exports/backups. Application logs are append-only until final owner-admin retention cleanup. Contact pejourproject@gmail.com.
