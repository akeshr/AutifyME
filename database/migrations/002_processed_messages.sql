-- ============================================================================
-- Migration: 002_processed_messages
-- Purpose: Webhook idempotency to prevent duplicate processing on retries
-- Created: 2025-10-13
-- Dependencies: PostgreSQL 12+
-- ============================================================================

-- TABLE: processed_messages (Webhook Idempotency)
-- Stores WhatsApp message_id to deduplicate webhook retries across server restarts
CREATE TABLE IF NOT EXISTS processed_messages (
    -- WhatsApp message identifiers
    message_id TEXT PRIMARY KEY,  -- WhatsApp's unique message ID (wamid.*)
    sender_id TEXT NOT NULL,      -- Phone number (917258067800)
    thread_id TEXT NOT NULL,      -- LangGraph thread ID (whatsapp:917258067800)

    -- Message metadata
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,  -- When webhook received
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- TTL for cleanup (24 hours)
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours'),

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for TTL cleanup (find expired rows)
CREATE INDEX IF NOT EXISTS idx_processed_messages_expires
    ON processed_messages(expires_at)
    WHERE expires_at IS NOT NULL;

-- Index for sender lookup (analytics/debugging)
CREATE INDEX IF NOT EXISTS idx_processed_messages_sender
    ON processed_messages(sender_id, created_at DESC);

-- ============================================================================
-- STORED PROCEDURE: Atomic idempotency check + insert
-- Returns: {is_duplicate: boolean, message_id: text}
-- ============================================================================

CREATE OR REPLACE FUNCTION check_and_mark_processed(
    p_message_id TEXT,
    p_sender_id TEXT,
    p_thread_id TEXT,
    p_received_at TIMESTAMPTZ
) RETURNS JSON AS $$
DECLARE
    v_inserted BOOLEAN;
BEGIN
    -- Atomic insert with conflict detection
    -- Returns true if INSERT succeeded (new message)
    -- Returns NULL if conflict occurred (duplicate message)
    INSERT INTO processed_messages (message_id, sender_id, thread_id, received_at)
    VALUES (p_message_id, p_sender_id, p_thread_id, p_received_at)
    ON CONFLICT (message_id) DO NOTHING
    RETURNING true INTO v_inserted;

    -- Return JSON with result
    RETURN json_build_object(
        'is_duplicate', v_inserted IS NULL,
        'message_id', p_message_id
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CLEANUP FUNCTION: Remove expired rows
-- Run daily via cron: SELECT cleanup_expired_processed_messages();
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_expired_processed_messages()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM processed_messages
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Log cleanup (appears in PostgreSQL logs)
    RAISE NOTICE 'Cleaned up % expired processed_messages', deleted_count;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MONITORING VIEW: Checkpoint forks detection
-- Detects when multiple workflows process same thread concurrently
-- ============================================================================

CREATE OR REPLACE VIEW v_checkpoint_forks AS
SELECT
    parent_checkpoint_id,
    thread_id,
    COUNT(*) as fork_count,
    ARRAY_AGG(checkpoint_id) as fork_checkpoint_ids,
    MAX(metadata->>'step') as latest_step
FROM checkpoints
WHERE thread_id LIKE 'whatsapp:%'
  AND parent_checkpoint_id IS NOT NULL
GROUP BY parent_checkpoint_id, thread_id
HAVING COUNT(*) > 1;

-- ============================================================================
-- COMMENTS (Documentation)
-- ============================================================================

COMMENT ON TABLE processed_messages IS
'Idempotency tracking for WhatsApp webhook deduplication.
Stores message_id from WhatsApp to prevent duplicate processing when webhooks retry.
TTL: 24 hours (auto-cleanup via expires_at).
Used by: whatsapp_webhook.py IdempotencyChecker';

COMMENT ON COLUMN processed_messages.message_id IS
'WhatsApp unique message ID (e.g., wamid.HBgLOTE3MjU4MDY3ODAw...).
Preserved across webhook retries - use this for deduplication.
Format: wamid.{base64_encoded_data}';

COMMENT ON COLUMN processed_messages.expires_at IS
'TTL for cleanup. After 24 hours, message_id can be reused (extremely unlikely).
Run cleanup_expired_processed_messages() daily via cron or scheduled task.';

COMMENT ON FUNCTION check_and_mark_processed IS
'Atomic idempotency check + insert. Single DB round-trip.
Returns {is_duplicate: true} if message already processed.
Returns {is_duplicate: false} if new message (now marked as processed).
Used by webhook handler to deduplicate before processing.';

COMMENT ON FUNCTION cleanup_expired_processed_messages IS
'Removes expired messages (expires_at < NOW()).
Returns count of deleted rows.
Schedule: Run daily via pg_cron or application scheduler.
Example: SELECT cron.schedule(''cleanup-processed-messages'', ''0 2 * * *'', $$SELECT cleanup_expired_processed_messages()$$);';

COMMENT ON VIEW v_checkpoint_forks IS
'Monitoring view to detect checkpoint forks (race condition indicator).
Fork = multiple checkpoints with same parent_checkpoint_id.
Indicates concurrent workflow processing on same thread.
Alert if fork_count > 0 frequently.';

-- ============================================================================
-- GRANT PERMISSIONS (Adjust for your deployment)
-- ============================================================================

-- For local development: Permissions already granted to current user
-- For production: Grant to application service account
-- Example:
-- GRANT SELECT, INSERT, DELETE ON processed_messages TO autifyme_app;
-- GRANT EXECUTE ON FUNCTION check_and_mark_processed TO autifyme_app;
-- GRANT EXECUTE ON FUNCTION cleanup_expired_processed_messages TO autifyme_app;
-- GRANT SELECT ON v_checkpoint_forks TO autifyme_app;
