BEGIN;

ALTER TABLE public.journal_entries
    ADD COLUMN IF NOT EXISTS word_count integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_pinned boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS is_draft boolean NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_journal_entries_user_date_desc
    ON public.journal_entries (user_id, entry_date DESC);

CREATE INDEX IF NOT EXISTS idx_journal_entries_user_mood
    ON public.journal_entries (user_id, mood);

COMMIT;
