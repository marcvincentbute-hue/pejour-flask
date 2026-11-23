# Class-wide security settings — November 16, 2026

The instructor's announcement replaces all student-number formulas. There is no D1/D2 calculation and no required seed table in final documentation. The approved System Proposal and Checkpoint 1 remain required.

| Parameter | Required setting |
| --- | --- |
| Username | 6–20 characters; starts with a letter; letters/digits only |
| Password | Minimum 8, maximum 64; strength rules still apply |
| Each normal name field | Maximum 50; existing name validation still applies |
| Forgot Password link | After 2 consecutive failures |
| Lockout after 3/6/9 failures | 15/30/60 seconds |
| OTP expiry | 5 minutes |
| Idle timeout | 15 minutes; warning in the final minute |
| IP threshold | 10 failures across accounts in 10 minutes; block for 10 minutes |
| Authentication questions | User selects exactly 3 different questions from all 8 bank questions |

The password maximum, OTP six-digit format, three wrong OTP attempts, 60-second resend cooldown, three actual resends/15 minutes, three-password history and all other protections stay unchanged. The five-minute password-reset grant is separate from the 15-minute authenticated idle timeout.

Existing users retain their original three question/answer hashes. They are not forced to answer eight questions or re-register. New registrations and new CLI admins choose their own three distinct questions. Recovery accepts only the questions saved for that account. Nonexistent accounts receive a stable dummy subset and the same failure response; no username-existence message is shown.

Source note: the PDF supplied with this request still contains the old section 2.2 formulas and seed-table requirement; no section 2.3 appears in that file. This release follows the newer announcement pasted by the student. It does not claim the PDF itself has the revised table. Technology-stack flexibility had already been confirmed by the student.
