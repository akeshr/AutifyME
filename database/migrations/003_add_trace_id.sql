-- Migration: Add trace_id to workflow_outcomes for multi-trace HITL workflow analysis
-- Date: 2025-10-17
-- Purpose: Enable automatic correlation between LangSmith traces and Supabase workflow data

-- Add trace_id column to workflow_outcomes table
ALTER TABLE workflow_outcomes
ADD COLUMN IF NOT EXISTS trace_id TEXT;

-- Create index for faster trace_id lookups
CREATE INDEX IF NOT EXISTS idx_workflow_outcomes_trace_id
ON workflow_outcomes(trace_id);

-- Create index for thread_id + trace_id queries (multi-trace workflow analysis)
CREATE INDEX IF NOT EXISTS idx_workflow_outcomes_thread_trace
ON workflow_outcomes(thread_id, created_at);

COMMENT ON COLUMN workflow_outcomes.trace_id IS 'LangSmith trace ID for observability correlation';
