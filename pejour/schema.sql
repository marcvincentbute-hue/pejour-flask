CREATE TABLE IF NOT EXISTS users (
 id varchar(9) PRIMARY KEY, username varchar(20) NOT NULL, email varchar(100) NOT NULL,
 password_hash text NOT NULL, role text NOT NULL DEFAULT 'user' CHECK (role IN ('user','admin')),
 verified boolean NOT NULL DEFAULT false, version integer NOT NULL DEFAULT 1,
 profile jsonb NOT NULL, intention text NOT NULL, consent_at timestamptz NOT NULL DEFAULT now(),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower ON users(lower(username));
CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower ON users(lower(email));
CREATE TABLE IF NOT EXISTS security_answers (
 user_id varchar(9) REFERENCES users(id), question integer NOT NULL, answer_hash text NOT NULL,
 PRIMARY KEY(user_id,question)
);
CREATE TABLE IF NOT EXISTS password_history (
 id bigserial PRIMARY KEY, user_id varchar(9) REFERENCES users(id), password_hash text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS otps (
 id bigserial PRIMARY KEY, user_id varchar(9) REFERENCES users(id), purpose text NOT NULL CHECK(purpose IN ('register','login','reset','email_change')),
 code_hash text NOT NULL, expires_at timestamptz NOT NULL, attempts integer NOT NULL DEFAULT 0,
 used boolean NOT NULL DEFAULT false, is_resend boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS otps_user_purpose ON otps(user_id,purpose,created_at DESC);
CREATE TABLE IF NOT EXISTS activity_log (
 id bigserial PRIMARY KEY, event_type text NOT NULL, username_typed text,
 user_id varchar(9), ip_address text NOT NULL, user_agent text NOT NULL,
 details text NOT NULL DEFAULT '', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS activity_time ON activity_log(created_at);
CREATE INDEX IF NOT EXISTS activity_failure ON activity_log(event_type,ip_address,created_at);
CREATE TABLE IF NOT EXISTS attempt_state (
 username text PRIMARY KEY, failures integer NOT NULL DEFAULT 0, locked_until timestamptz
);
CREATE TABLE IF NOT EXISTS ip_blocks (ip_address text PRIMARY KEY, blocked_until timestamptz NOT NULL);
CREATE TABLE IF NOT EXISTS security_flags (
 id bigserial PRIMARY KEY, pattern text NOT NULL, target text NOT NULL, severity text NOT NULL,
 details text NOT NULL, flag_date date NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(pattern,target,flag_date)
);
CREATE TABLE IF NOT EXISTS journal_entries (
 id bigserial PRIMARY KEY, user_id varchar(9) NOT NULL REFERENCES users(id), title text NOT NULL, body text NOT NULL,
 entry_date date NOT NULL, mood text NOT NULL, version integer NOT NULL DEFAULT 1,
 word_count integer NOT NULL DEFAULT 0, is_pinned boolean NOT NULL DEFAULT false,
 is_draft boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_journal_entries_user_date_desc ON journal_entries (user_id, entry_date DESC);
CREATE INDEX IF NOT EXISTS idx_journal_entries_user_mood ON journal_entries (user_id, mood);
CREATE TABLE IF NOT EXISTS web_sessions (
 token_hash text PRIMARY KEY, data jsonb NOT NULL, expires_at timestamptz NOT NULL
);
-- Enforce append-only logs even if an application bug tries to mutate them.
CREATE OR REPLACE FUNCTION reject_log_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Activity logs are append-only'; END; $$;
DROP TRIGGER IF EXISTS activity_append_only ON activity_log;
CREATE TRIGGER activity_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON activity_log
FOR EACH STATEMENT EXECUTE FUNCTION reject_log_mutation();
