-- Migration 007: Fix array type handling in execute_write_intent
--
-- Problem: column "tags" is of type text[] but expression is of type jsonb (Error 42804)
-- Solution: Add helper function to convert JSONB arrays to PostgreSQL text[]
--
-- Created: 2025-12-30
-- Author: Claude (Trace Evaluation Fix)

-- ============================================================================
-- STEP 1: Create helper function (safe to run multiple times)
-- ============================================================================

CREATE OR REPLACE FUNCTION jsonb_to_text_array(p_value jsonb)
RETURNS text[]
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT ARRAY(SELECT jsonb_array_elements_text(p_value))
$$;

COMMENT ON FUNCTION jsonb_to_text_array(jsonb) IS
'Converts JSONB array to PostgreSQL text[]. Used for text[] column updates via execute_write_intent.';


-- ============================================================================
-- STEP 2: Get current execute_write_intent source (for reference)
-- Run this to see the current function before modifying:
--
--   SELECT pg_get_functiondef(oid)
--   FROM pg_proc
--   WHERE proname = 'execute_write_intent';
--
-- ============================================================================


-- ============================================================================
-- STEP 3: Patch the execute_write_intent function
--
-- Find the section that builds SET clauses for UPDATE operations.
-- It likely looks like:
--
--   v_set_clause := v_set_clause || quote_ident(v_key) || ' = ' ||
--                   quote_literal(v_value::text) || '::jsonb';
--
-- Replace with logic that detects array columns:
--
--   -- Check if target column is text[]
--   SELECT data_type INTO v_col_type
--   FROM information_schema.columns
--   WHERE table_schema = 'public'
--     AND table_name = v_table
--     AND column_name = v_key;
--
--   IF v_col_type = 'ARRAY' AND jsonb_typeof(v_value) = 'array' THEN
--       -- Use helper for text[] columns
--       v_set_clause := v_set_clause || quote_ident(v_key) || ' = ' ||
--                       'jsonb_to_text_array(' || quote_literal(v_value::text) || '::jsonb)';
--   ELSE
--       -- Original logic for non-array columns
--       v_set_clause := v_set_clause || quote_ident(v_key) || ' = ' ||
--                       format_jsonb_value(v_value);
--   END IF;
--
-- ============================================================================


-- ============================================================================
-- VERIFICATION: Test the helper function
-- ============================================================================

DO $$
DECLARE
    v_result text[];
BEGIN
    -- Test conversion
    v_result := jsonb_to_text_array('["tag1", "tag2", "tag3"]'::jsonb);

    IF array_length(v_result, 1) = 3 AND v_result[1] = 'tag1' THEN
        RAISE NOTICE 'SUCCESS: jsonb_to_text_array works correctly';
    ELSE
        RAISE EXCEPTION 'FAILED: jsonb_to_text_array test';
    END IF;
END;
$$;
