BEGIN;
ALTER TABLE public.otps DROP CONSTRAINT IF EXISTS otps_purpose_check;
ALTER TABLE public.otps ADD CONSTRAINT otps_purpose_check
    CHECK (purpose IN ('register', 'login', 'reset', 'email_change'));
COMMIT;
