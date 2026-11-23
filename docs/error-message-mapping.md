# Registration Error Message Mapping

These messages are implemented by the browser and Python where applicable. Server-only uniqueness, secret verification and persistence checks remain authoritative. When several mistakes exist, the validator uses its documented rule order and each field shows its own message.

| Field | Rule or operation | Exact message or behaviour |
| --- | --- | --- |
| ID Number | Exactly four digits, hyphen, four digits | ID Number must follow the format xxxx-xxxx. |
| ID Number | Unique primary key | This ID Number is already registered. |
| First Name | Required | First Name is required. |
| Family Name | Required | Family Name is required. |
| Middle Name | Optional | Empty is accepted; if filled, the name rules below apply. |
| First / Middle / Family Name | No digits | Numbers are not allowed in First Name. / Numbers are not allowed in Middle Name. / Numbers are not allowed in Family Name. |
| First / Middle / Family Name | Letters and spaces only | Special characters are not allowed in First Name. / Special characters are not allowed in Middle Name. / Special characters are not allowed in Family Name. |
| First / Middle / Family Name | No double spaces | Double space is not allowed. |
| First / Middle / Family Name | No leading or trailing spaces | First Name must not start or end with a space. / Middle Name must not start or end with a space. / Family Name must not start or end with a space. |
| First / Middle / Family Name | Not all capitals | Do not use all capital letters. |
| First / Middle / Family Name | No three identical consecutive letters, ignoring case | Three consecutive identical letters are not allowed. |
| First / Middle / Family Name | First letter of each word capital, remaining letters small | First letter of your name must be capital. |
| First / Middle / Family Name | 2–50 characters | First Name must be 2–50 characters. / Middle Name must be 2–50 characters. / Family Name must be 2–50 characters. |
| Name Extension | Optional; empty, Jr., Sr. or Other | Please select a valid name extension. |
| Other extension | If Other selected, exactly I, II, III, IV, IX or X | Name Extension must be I, II, III, IV, IX or X. |
| Birthdate | Required real date, not in the future | Please enter a valid birthdate that is not in the future. |
| Birthdate | Age must be at least 18 | You must be at least 18 years old to register. |
| Age | Calculated from birthdate; read-only | The server recalculates age rather than trusting a posted age. |
| Purok / Street | Required; 3–50 letters/digits/single spaces; no boundary spaces | Purok / Street must be 3–50 letters, digits and single spaces without leading or trailing spaces. |
| Barangay | Required; 2–50 letters/single spaces in Title Case | Barangay must be 2–50 letters and single spaces in Title Case. |
| Municipality / City | Required; 2–50 letters/single spaces in Title Case | Municipality / City must be 2–50 letters and single spaces in Title Case. |
| Province | Required; 2–50 letters/single spaces in Title Case | Province must be 2–50 letters and single spaces in Title Case. |
| Country | Required; 2–100 letters/single spaces in Title Case | Country must be 2–100 letters and single spaces in Title Case. |
| ZIP Code | Exactly four digits | ZIP Code must contain exactly 4 digits. |
| Email | Required valid email, no whitespace, maximum 100 characters | Please enter a valid email address. |
| Email | Unique | This email is already registered. |
| Email | Normalization | Stored in lowercase; no error for uppercase letters in an otherwise valid address. |
| Username | 6–20 letters/digits, first character a letter | Username must start with a letter and contain 6–20 letters and digits. |
| Username | Unique | This username is already registered. |
| Username | Available, live check | Username is available. |
| Password | 8–64 characters, at least three groups, no whitespace; Weak refused | Use 8–64 characters, at least three character groups, and no whitespace. |
| Re-enter Password | Must match | Passwords do not match. |
| Three selected question answers | Required; 2–50 letters and single spaces | Answer must be 2–50 letters and single spaces. |
| Security Question 1/2/3 | Required; an ID from the eight-question bank | Please select a question from the question bank. |
| Security Question 1/2/3 | All three choices must be different | Choose three different security questions. |
| Journal Display Name | Required; 2–30 letters/digits/single spaces | Journal Display Name must be 2–30 letters, digits and single spaces. |
| Journaling Start Date | Required real date, not in future | Journaling Start Date must be a valid date that is not in the future. |
| Writing Goal | Required; exact server allowlist | Please select a valid writing goal. |
| Private Journaling Intention | Required; at least 10 after trimming, at most 300 total, no control characters | Private Journaling Intention must be 10–300 characters without control characters. |
| Privacy consent | Required and unchecked initially | You must agree to the Privacy Notice to register. |
| CAPTCHA | Six displayed characters, valid unconsumed server challenge | CAPTCHA did not match. Enter the new characters shown. |
| CAPTCHA | Browser format check | Enter the six characters shown in the CAPTCHA. |
| Honeypot website | Must be empty | Registration could not be completed. Please try again. No account is saved. |

## Recovery and password change

| Field or condition | Exact message |
| --- | --- |
| Login credential failure, including unverified accounts | Invalid username or password. |
| Login/recovery CAPTCHA failure | CAPTCHA did not match. Enter the new characters shown. |
| Recovery answer mismatch | Answers do not match. |
| Incorrect recovery answer or unavailable account | The account details could not be verified. |
| OTP invalid, expired or cancelled | The code is incorrect, expired or cancelled. After three wrong entries, request a new code. |
| Login/recovery/OTP lockout | Too many attempts. Please wait for the countdown. |
| OTP resend cooldown | Please wait 60 seconds before requesting another code. |
| Fourth resend within 15 minutes | The resend limit has been reached. Try again after 15 minutes. |
| Invalid security answer format | Answer must be 2–50 letters and single spaces. |
| Recent password reuse | You cannot reuse a recent password. |
| Change Password confirmation mismatch | Mismatch Password. |
| Successful password change | Successfully Change Password. |

Native browser constraints may also refuse an input before submission. The Python rules and exact server messages remain the final authority; client validation cannot be used to bypass them.

## Journal and general protections

| Field or condition | Exact message |
| --- | --- |
| Entry title, 1–120 nonempty characters | Title must be 1–120 characters. |
| Entry body, 1–10,000 nonempty characters | Entry must be 1–10,000 characters. |
| Entry date outside journal range | Choose a date from your journaling start date through today. |
| Mood outside the six allowed values | Please select a valid mood. |
| Stale journal edit version | This entry changed in another tab. Reload before saving. |
| Delete confirmation missing/stale | Confirm deletion of the current version of this entry. |
| CSRF missing/incorrect | Your request could not be verified. Please try again. |
| Expired/reset version changed during password update | Your reset authorization expired. Please start again. |
| Dashboard date filter malformed | Choose valid filter dates. |
| SMTP failure | Email could not be sent. Please try again later. |
| Authenticated idle expiry | Your session expired. Please log in again. |

