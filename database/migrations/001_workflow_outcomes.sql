-- Migration: Workflow Outcomes Table for Agentic Learning (Phase 1.2)
-- Purpose: Track workflow execution outcomes for continuous learning
-- Created: 2025-10-09
-- Dependencies: PostgreSQL 12+, pgvector extension (Phase 2)

-- ============================================================================
-- TABLE: workflow_outcomes
-- Stores complete workflow execution records for learning and analysis
-- ============================================================================

CREATE TABLE IF NOT EXISTS workflow_outcomes (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tracking_id TEXT NOT NULL UNIQUE,
    thread_id TEXT NOT NULL,

    -- Incoming message
    sender_id TEXT NOT NULL,
    message_text TEXT,
    message_hash TEXT NOT NULL,  -- For deduplication and similarity
    media_id TEXT,
    media_type TEXT,
    platform TEXT DEFAULT 'whatsapp',
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Routing decision (PM delegation)
    intent TEXT,
    department TEXT,
    routing_reasoning TEXT,
    routing_confidence FLOAT,
    alternative_departments TEXT[],  -- Array of fallback options
    routed_at TIMESTAMP WITH TIME ZONE,

    -- Workflow outcome
    success BOOLEAN NOT NULL,
    error_type TEXT,
    error_message TEXT,
    resolution_strategy TEXT,  -- auto/manual/escalated
    result_data JSONB,  -- Structured result if successful

    -- Performance metrics
    duration_seconds FLOAT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,

    -- Learning metadata (populated by adaptive components)
    learned_patterns JSONB DEFAULT '[]'::jsonb,  -- Success patterns extracted
    failure_warnings JSONB DEFAULT '[]'::jsonb,  -- Failure cases identified
    applied_strategies TEXT[],  -- Which learned strategies were applied

    -- Future: Vector embeddings for similarity search (Phase 2)
    -- message_embedding VECTOR(1536),  -- Requires pgvector extension

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES for query performance
-- ============================================================================

-- Primary lookup by thread_id (most common query)
CREATE INDEX IF NOT EXISTS idx_workflow_outcomes_thread_id
    ON workflow_outcomes(thread_id);

-- Lookup by tracking_id
CREATE INDEX IF NOT EXISTS idx_workflow_outcomes_tracking_id
    ON workflow_outcomes(tracking_id);

-- Time-based queries (analytics, pattern extraction)
CREATE INDEX IF NOT EXISTS idx_workflow_outcomes_created_at
    ON workflow_outcomes(created_at DESC);

-- Intent-based routing analysis
CREATE INDEX IF NOT EXISTS idx_workflow_outcomes_intent_dept
    ON workflow_outcomes(intent, department)
    WHERE intent IS NOT NULL AND department IS NOT NULL;

-- Failure analysis
CREATE INDEX IF NOT EXISTS idx_workflow_outcomes_failures
    ON workflow_outcomes(error_type, created_at DESC)
    WHERE success = false;

-- Message hash for similarity detection (exact duplicates)
CREATE INDEX IF NOT EXISTS idx_workflow_outcomes_message_hash
    ON workflow_outcomes(message_hash);

-- Success rate analysis
CREATE INDEX IF NOT EXISTS idx_workflow_outcomes_success
    ON workflow_outcomes(success, department, created_at DESC);

-- Future: Vector similarity search (Phase 2)
-- CREATE INDEX IF NOT EXISTS idx_workflow_outcomes_embedding
--     ON workflow_outcomes USING ivfflat (message_embedding vector_cosine_ops)
--     WITH (lists = 100);

-- ============================================================================
-- TRIGGERS for automatic timestamp updates
-- ============================================================================

CREATE OR REPLACE FUNCTION update_workflow_outcomes_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER workflow_outcomes_updated_at
    BEFORE UPDATE ON workflow_outcomes
    FOR EACH ROW
    EXECUTE FUNCTION update_workflow_outcomes_timestamp();

-- ============================================================================
-- TABLE: routing_history (lightweight routing metrics)
-- Separate table for high-volume routing analytics without full outcome data
-- ============================================================================

CREATE TABLE IF NOT EXISTS routing_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflow_outcomes(id) ON DELETE CASCADE,

    -- Routing decision
    intent TEXT NOT NULL,
    department TEXT NOT NULL,
    confidence_score FLOAT,

    -- Outcome (simplified)
    success BOOLEAN NOT NULL,
    duration_seconds FLOAT NOT NULL,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for routing analytics
CREATE INDEX IF NOT EXISTS idx_routing_history_intent_dept
    ON routing_history(intent, department);

CREATE INDEX IF NOT EXISTS idx_routing_history_created
    ON routing_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_routing_history_workflow
    ON routing_history(workflow_id);

-- ============================================================================
-- VIEWS for common queries
-- ============================================================================

-- Success rate by department and intent
CREATE OR REPLACE VIEW v_success_rates AS
SELECT
    department,
    intent,
    COUNT(*) as total_workflows,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    ROUND(
        100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) as success_rate_pct,
    ROUND(AVG(duration_seconds)::numeric, 2) as avg_duration_seconds
FROM workflow_outcomes
WHERE intent IS NOT NULL
  AND department IS NOT NULL
  AND created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY department, intent
ORDER BY total_workflows DESC;

-- Recent failures for regression test generation
CREATE OR REPLACE VIEW v_recent_failures AS
SELECT
    tracking_id,
    thread_id,
    message_text,
    media_id,
    media_type,
    error_type,
    error_message,
    resolution_strategy,
    duration_seconds,
    created_at
FROM workflow_outcomes
WHERE success = false
  AND created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
ORDER BY created_at DESC
LIMIT 50;

-- Edge cases (low frequency patterns)
CREATE OR REPLACE VIEW v_edge_cases AS
WITH pattern_counts AS (
    SELECT
        message_hash,
        COUNT(*) as occurrence_count,
        MAX(message_text) as sample_text,
        MAX(intent) as intent,
        MAX(department) as department,
        MAX(created_at) as last_seen,
        ROUND(AVG(duration_seconds)::numeric, 2) as avg_duration
    FROM workflow_outcomes
    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
    GROUP BY message_hash
)
SELECT *
FROM pattern_counts
WHERE occurrence_count <= 3  -- Edge case threshold
ORDER BY occurrence_count ASC, last_seen DESC;

-- ============================================================================
-- COMMENTS for documentation
-- ============================================================================

COMMENT ON TABLE workflow_outcomes IS
'Stores complete workflow execution records for agentic learning (Phase 1.2).
Tracks incoming messages, routing decisions, outcomes, and performance metrics.
Used by AdaptivePromptManager, AdaptiveRouter, and TestSynthesizer.';

COMMENT ON COLUMN workflow_outcomes.message_hash IS
'SHA-256 hash of message content for similarity detection and deduplication.
Generated from text + media_type. Used for clustering similar messages.';

COMMENT ON COLUMN workflow_outcomes.learned_patterns IS
'JSONB array of success patterns extracted by AdaptivePromptManager.
Each pattern: {pattern_id, strategy_summary, success_count, avg_duration}.';

COMMENT ON COLUMN workflow_outcomes.failure_warnings IS
'JSONB array of failure cases recorded by AdaptivePromptManager.
Each warning: {warning_id, error_type, failure_summary, mitigation_hint}.';

COMMENT ON VIEW v_success_rates IS
'Success rate analytics by department and intent for last 7 days.
Used by AdaptiveRouter to learn optimal routing strategies.';

COMMENT ON VIEW v_recent_failures IS
'Recent failures for automated regression test generation.
Used by TestSynthesizer to create pytest regression tests.';

COMMENT ON VIEW v_edge_cases IS
'Low-frequency patterns (≤3 occurrences in 30 days) for test synthesis.
Prioritized for test scenario generation to improve edge case coverage.';

-- ============================================================================
-- GRANT permissions (adjust for your deployment)
-- ============================================================================

-- For local development: grant to current user
-- For production: grant to application service account
-- Example:
-- GRANT SELECT, INSERT, UPDATE ON workflow_outcomes TO autifyme_app;
-- GRANT SELECT, INSERT ON routing_history TO autifyme_app;
-- GRANT SELECT ON v_success_rates, v_recent_failures, v_edge_cases TO autifyme_app;
