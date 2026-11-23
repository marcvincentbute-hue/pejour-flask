# Pejour System Proposal

Status: The student reported instructor approval in the chat. Attach the actual signed Appendix A; this typed file does not supply a signature or approval date.
Student name: To be supplied
Student number: 241-01057

System name: Pejour Private Personal Journal
Who uses it: Adults who want a protected place to record private reflections and personal experiences.
What it stores: Required registration details, journal preferences, private journaling intention, and dated personal journal entries.
Why accounts need protecting: Reflections can reveal personal relationships, distress, and private experiences. Unauthorized access or changes can expose or misrepresent the owner.
Sensitive field to encrypt: Private Journaling Intention, using AES-256 with a fresh random IV and authenticated encryption; only its owner may view the decrypted value. Journal titles and bodies should also be encrypted.

## System registration fields

| Field name | Kind | Required | Rule | Exact error message |
| --- | --- | --- | --- | --- |
| Journal Display Name | Short text | Yes | 2–30 ASCII letters or digits, with single internal spaces; no leading or trailing space | Journal Display Name must be 2–30 letters, digits and single spaces. |
| Journaling Start Date | Date | Yes | Real calendar date, not later than today in Philippine time | Journaling Start Date must be a valid date that is not in the future. |
| Writing Goal | Dropdown | Yes | Exactly Self Reflection, Gratitude, Daily Memories, or Personal Growth; server allowlist | Please select a valid writing goal. |
| Private Journaling Intention | Long text | Yes | 10–300 characters after trimming, no control characters | Private Journaling Intention must be 10–300 characters without control characters. |

These four fields span at least three kinds: text, date and dropdown. Display name labels the private journal; start date sets its beginning; goal provides the chosen writing prompt category; intention stores the owner's private purpose. The project must implement those uses to justify collection.

## Instructor decision

[ ] Approved    [ ] Revise and resubmit
Signature: ____________________    Date: ____________________

Retain the instructor-approved system name and fields. The student must provide the actual signature, approval date and class-uniqueness evidence; code files alone do not establish these.

