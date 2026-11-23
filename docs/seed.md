# Personal Seed Table

D1 = 5
D2 = 7

Derived from the last two digits of student number 241-01057.
Place this completed table on the first page of final documentation.

| Parameter | Formula | Mine |
| --- | --- | --- |
| Minimum username length | 6 + (D1 mod 3) | 8 characters |
| Maximum username length | 16 + (D2 mod 5) | 18 characters |
| Minimum password length | 8 + (D2 mod 4) | 11 characters |
| Maximum name length | 20 + D2 | 27 characters |
| Failures before Forgot Password link | 2 + (D1 mod 2) | 3 failures |
| Lockout tier 1 seconds, at 3 failures | 15 + D1 | 20 seconds |
| Lockout tier 2 seconds, at 6 failures | 30 + 2 * D1 | 40 seconds |
| Lockout tier 3 seconds, at 9 failures | 60 + 4 * D1 | 80 seconds |
| OTP expiry minutes | 3 + (D2 mod 3) | 4 minutes |
| Idle timeout minutes | 5 + (D1 mod 5) | 5 minutes |
| IP failures in 10 minutes | 8 + D2 | 15 failures |
| Question A | Q[(D2 mod 8) + 1] | Q8 |
| Question B | Q[((D2 + 3) mod 8) + 1] | Q3 |
| Question C | Q[((D2 + 5) mod 8) + 1] | Q5 |

## Authentication Questions

- Q8: What dish did you cook for the first time?
- Q3: Who was your favorite teacher in high school?
- Q5: What street did you live on in Grade 1?