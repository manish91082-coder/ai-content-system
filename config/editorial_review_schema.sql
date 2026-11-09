-- Secure human editorial decision endpoint.
-- Review this file before applying it to the hosted Supabase project.
-- This migration is intentionally NOT auto-deployed by GitHub Actions.

CREATE TABLE IF NOT EXISTS public.editorial_review_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id uuid NOT NULL REFERENCES public.content_items(id),
    decision text NOT NULL CHECK (decision IN ('approve', 'reject')),
    reviewer_login text NOT NULL CHECK (length(trim(reviewer_login)) > 0),
    content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    reviewed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_editorial_review_events_content
    ON public.editorial_review_events(content_id, reviewed_at DESC);

-- The earlier pipeline serialized JSONB metadata as a JSON string. Normalize
-- valid object-shaped legacy values so the review RPC can inspect their keys.
UPDATE public.content_items
SET metadata = ((metadata #>> '{}')::jsonb)
WHERE jsonb_typeof(metadata) = 'string'
  AND (metadata #>> '{}') ~ '^\\s*\\{';

GRANT USAGE ON SCHEMA public TO service_role;
GRANT SELECT, INSERT, UPDATE ON TABLE public.content_items TO service_role;

ALTER TABLE public.editorial_review_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.editorial_review_events FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.editorial_review_events TO service_role;

CREATE OR REPLACE FUNCTION public.prevent_editorial_review_event_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    RAISE EXCEPTION 'Editorial review events are append-only';
END;
$$;

REVOKE ALL ON FUNCTION public.prevent_editorial_review_event_mutation() FROM PUBLIC, anon, authenticated;

DROP TRIGGER IF EXISTS editorial_review_events_immutable
    ON public.editorial_review_events;
CREATE TRIGGER editorial_review_events_immutable
    BEFORE UPDATE OR DELETE ON public.editorial_review_events
    FOR EACH ROW EXECUTE FUNCTION public.prevent_editorial_review_event_mutation();

CREATE OR REPLACE FUNCTION public.editorial_review_decide(
    p_content_id uuid,
    p_decision text,
    p_reviewer_login text,
    p_expected_content_hash text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_item public.content_items%ROWTYPE;
    v_metadata jsonb;
    v_now timestamptz := clock_timestamp();
    v_status text;
BEGIN
    IF COALESCE(
           NULLIF(current_setting('request.jwt.claim.role', true), ''),
           current_setting('request.jwt.claims', true)::json->>'role'
       ) IS DISTINCT FROM 'service_role'
       AND current_user <> 'service_role' THEN
        RAISE EXCEPTION 'service_role is required for editorial decisions'
            USING ERRCODE = '42501';
    END IF;

    IF p_decision NOT IN ('approve', 'reject') THEN
        RAISE EXCEPTION 'Decision must be approve or reject';
    END IF;
    IF p_reviewer_login IS NULL OR length(trim(p_reviewer_login)) = 0 THEN
        RAISE EXCEPTION 'Reviewer identity is required';
    END IF;
    IF p_expected_content_hash !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'A valid expected content hash is required';
    END IF;

    SELECT * INTO v_item
    FROM public.content_items
    WHERE id = p_content_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Content item not found';
    END IF;
    IF v_item.status <> 'pending_editorial_review' THEN
        RAISE EXCEPTION 'Content is not pending review (current status: %)', v_item.status;
    END IF;

    v_metadata := COALESCE(v_item.metadata, '{}'::jsonb);
    IF v_metadata->>'review_content_hash' IS DISTINCT FROM p_expected_content_hash THEN
        RAISE EXCEPTION 'Reviewed content changed; prepare a fresh review before deciding';
    END IF;

    v_status := CASE WHEN p_decision = 'approve'
                     THEN 'editorially_approved' ELSE 'rejected' END;

    UPDATE public.content_items
    SET status = v_status,
        metadata = v_metadata || jsonb_build_object(
            'editorial_status', CASE WHEN p_decision = 'approve'
                                     THEN 'approved' ELSE 'rejected' END,
            'editorial_approved', (p_decision = 'approve'),
            'editorial_review_decision', p_decision,
            'reviewed_by', trim(p_reviewer_login),
            'reviewed_at', v_now,
            'approved_by', CASE WHEN p_decision = 'approve'
                                THEN trim(p_reviewer_login) ELSE NULL END,
            'approved_at', CASE WHEN p_decision = 'approve'
                                THEN v_now ELSE NULL END,
            'rejected_by', CASE WHEN p_decision = 'reject'
                                THEN trim(p_reviewer_login) ELSE NULL END,
            'rejected_at', CASE WHEN p_decision = 'reject'
                                THEN v_now ELSE NULL END
        ),
        updated_at = v_now
    WHERE id = p_content_id;

    INSERT INTO public.editorial_review_events
        (content_id, decision, reviewer_login, content_hash, reviewed_at)
    VALUES
        (p_content_id, p_decision, trim(p_reviewer_login),
         p_expected_content_hash, v_now);

    RETURN jsonb_build_object(
        'content_id', p_content_id,
        'status', v_status,
        'decision', p_decision,
        'reviewer', trim(p_reviewer_login),
        'reviewed_at', v_now,
        'content_hash', p_expected_content_hash
    );
END;
$$;

REVOKE ALL ON FUNCTION public.editorial_review_decide(uuid, text, text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.editorial_review_decide(uuid, text, text, text)
    TO service_role;
