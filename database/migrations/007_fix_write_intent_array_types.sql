-- Migration 007: Fix execute_write_intent RPC to handle array type columns
--
-- Problem: When updating text[] columns (like 'tags'), the RPC passes JSONB arrays
-- directly, but PostgreSQL cannot implicitly cast jsonb to text[].
--
-- Error: "column 'tags' is of type text[] but expression is of type jsonb" (42804)
--
-- Solution: Add a helper function to convert JSONB arrays to PostgreSQL arrays,
-- and update execute_write_intent to use it for array-type columns.
--
-- Created: 2025-12-30
-- Author: Claude (Trace Evaluation Fix)

-- ============================================================================
-- Helper Function: Convert JSONB array to text[] array
-- ============================================================================

CREATE OR REPLACE FUNCTION jsonb_to_text_array(p_jsonb jsonb)
RETURNS text[]
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    IF p_jsonb IS NULL THEN
        RETURN NULL;
    END IF;

    IF jsonb_typeof(p_jsonb) != 'array' THEN
        RAISE EXCEPTION 'Expected JSON array, got %', jsonb_typeof(p_jsonb);
    END IF;

    RETURN ARRAY(SELECT jsonb_array_elements_text(p_jsonb));
END;
$$;

COMMENT ON FUNCTION jsonb_to_text_array(jsonb) IS
'Converts a JSONB array to a PostgreSQL text[] array. Used by execute_write_intent for array column updates.';


-- ============================================================================
-- Helper Function: Check if a column is an array type
-- ============================================================================

CREATE OR REPLACE FUNCTION is_array_column(p_table_name text, p_column_name text)
RETURNS boolean
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_data_type text;
BEGIN
    SELECT data_type INTO v_data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = p_table_name
      AND column_name = p_column_name;

    RETURN v_data_type = 'ARRAY';
END;
$$;

COMMENT ON FUNCTION is_array_column(text, text) IS
'Returns true if the specified column is an array type.';


-- ============================================================================
-- Updated execute_write_intent function with array type handling
-- ============================================================================

CREATE OR REPLACE FUNCTION execute_write_intent(
    p_operations jsonb,
    p_context jsonb DEFAULT '{}'::jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_operation jsonb;
    v_action text;
    v_table text;
    v_data jsonb;
    v_filters jsonb;
    v_updates jsonb;
    v_returns text;
    v_on_conflict text;
    v_conflict_fields jsonb;
    v_soft_delete boolean;
    v_result jsonb;
    v_results jsonb := '[]'::jsonb;
    v_context jsonb := p_context;
    v_operation_index int := 0;
    v_sql text;
    v_count int;
    v_ids uuid[];
    v_key text;
    v_value jsonb;
    v_set_clause text;
    v_where_clause text;
    v_column_list text;
    v_value_list text;
    v_insert_data jsonb;
    v_row record;
    v_created_rows jsonb;
    v_is_array boolean;
BEGIN
    -- Iterate through each operation
    FOR v_operation IN SELECT * FROM jsonb_array_elements(p_operations)
    LOOP
        v_operation_index := v_operation_index + 1;

        -- Extract operation fields
        v_action := v_operation->>'action';
        v_table := v_operation->>'table';
        v_data := v_operation->'data';
        v_filters := v_operation->'filters';
        v_updates := v_operation->'updates';
        v_returns := v_operation->>'returns';
        v_on_conflict := COALESCE(v_operation->>'on_conflict', 'error');
        v_conflict_fields := v_operation->'conflict_fields';
        v_soft_delete := COALESCE((v_operation->>'soft_delete')::boolean, false);

        -- Resolve @references in data, filters, and updates
        v_data := resolve_references(v_data, v_context);
        v_filters := resolve_references(v_filters, v_context);
        v_updates := resolve_references(v_updates, v_context);

        -- Execute based on action type
        CASE v_action
            WHEN 'create' THEN
                -- Handle single or batch create
                IF jsonb_typeof(v_data) = 'array' THEN
                    -- Batch create
                    v_created_rows := '[]'::jsonb;
                    FOR v_insert_data IN SELECT * FROM jsonb_array_elements(v_data)
                    LOOP
                        v_column_list := '';
                        v_value_list := '';

                        FOR v_key, v_value IN SELECT * FROM jsonb_each(v_insert_data)
                        LOOP
                            IF v_column_list != '' THEN
                                v_column_list := v_column_list || ', ';
                                v_value_list := v_value_list || ', ';
                            END IF;
                            v_column_list := v_column_list || quote_ident(v_key);

                            -- Check if column is array type
                            v_is_array := is_array_column(v_table, v_key);
                            IF v_is_array AND jsonb_typeof(v_value) = 'array' THEN
                                v_value_list := v_value_list || 'jsonb_to_text_array(' || quote_literal(v_value::text) || '::jsonb)';
                            ELSE
                                v_value_list := v_value_list || format_jsonb_value(v_value);
                            END IF;
                        END LOOP;

                        v_sql := format(
                            'INSERT INTO %I (%s) VALUES (%s) RETURNING to_jsonb(%I.*)',
                            v_table, v_column_list, v_value_list, v_table
                        );

                        EXECUTE v_sql INTO v_row;
                        v_created_rows := v_created_rows || v_row.to_jsonb;
                    END LOOP;

                    v_result := jsonb_build_object(
                        'action', 'create',
                        'table', v_table,
                        'count', jsonb_array_length(v_created_rows),
                        'data', v_created_rows
                    );

                    -- Store first row in context if returns specified
                    IF v_returns IS NOT NULL AND jsonb_array_length(v_created_rows) > 0 THEN
                        v_context := jsonb_set(v_context, ARRAY[v_returns], v_created_rows->0);
                    END IF;
                ELSE
                    -- Single create
                    v_column_list := '';
                    v_value_list := '';

                    FOR v_key, v_value IN SELECT * FROM jsonb_each(v_data)
                    LOOP
                        IF v_column_list != '' THEN
                            v_column_list := v_column_list || ', ';
                            v_value_list := v_value_list || ', ';
                        END IF;
                        v_column_list := v_column_list || quote_ident(v_key);

                        -- Check if column is array type
                        v_is_array := is_array_column(v_table, v_key);
                        IF v_is_array AND jsonb_typeof(v_value) = 'array' THEN
                            v_value_list := v_value_list || 'jsonb_to_text_array(' || quote_literal(v_value::text) || '::jsonb)';
                        ELSE
                            v_value_list := v_value_list || format_jsonb_value(v_value);
                        END IF;
                    END LOOP;

                    v_sql := format(
                        'INSERT INTO %I (%s) VALUES (%s) RETURNING to_jsonb(%I.*)',
                        v_table, v_column_list, v_value_list, v_table
                    );

                    EXECUTE v_sql INTO v_row;

                    v_result := jsonb_build_object(
                        'action', 'create',
                        'table', v_table,
                        'count', 1,
                        'data', v_row.to_jsonb
                    );

                    -- Store in context if returns specified
                    IF v_returns IS NOT NULL THEN
                        v_context := jsonb_set(v_context, ARRAY[v_returns], v_row.to_jsonb);
                    END IF;
                END IF;

            WHEN 'update' THEN
                -- Build SET clause with array type handling
                v_set_clause := '';
                FOR v_key, v_value IN SELECT * FROM jsonb_each(v_updates)
                LOOP
                    IF v_set_clause != '' THEN
                        v_set_clause := v_set_clause || ', ';
                    END IF;

                    -- Check if column is array type
                    v_is_array := is_array_column(v_table, v_key);
                    IF v_is_array AND jsonb_typeof(v_value) = 'array' THEN
                        v_set_clause := v_set_clause || quote_ident(v_key) || ' = jsonb_to_text_array(' || quote_literal(v_value::text) || '::jsonb)';
                    ELSE
                        v_set_clause := v_set_clause || quote_ident(v_key) || ' = ' || format_jsonb_value(v_value);
                    END IF;
                END LOOP;

                -- Build WHERE clause
                v_where_clause := build_where_clause(v_filters);

                v_sql := format(
                    'UPDATE %I SET %s WHERE %s',
                    v_table, v_set_clause, v_where_clause
                );

                EXECUTE v_sql;
                GET DIAGNOSTICS v_count = ROW_COUNT;

                v_result := jsonb_build_object(
                    'action', 'update',
                    'table', v_table,
                    'count', v_count
                );

            WHEN 'delete' THEN
                v_where_clause := build_where_clause(v_filters);

                IF v_soft_delete THEN
                    v_sql := format(
                        'UPDATE %I SET deleted_at = NOW() WHERE %s AND deleted_at IS NULL',
                        v_table, v_where_clause
                    );
                ELSE
                    v_sql := format(
                        'DELETE FROM %I WHERE %s',
                        v_table, v_where_clause
                    );
                END IF;

                EXECUTE v_sql;
                GET DIAGNOSTICS v_count = ROW_COUNT;

                v_result := jsonb_build_object(
                    'action', 'delete',
                    'table', v_table,
                    'count', v_count
                );

            WHEN 'upsert' THEN
                -- Similar to create but with ON CONFLICT handling
                -- For now, delegate to create (TODO: full upsert support)
                v_column_list := '';
                v_value_list := '';

                FOR v_key, v_value IN SELECT * FROM jsonb_each(v_data)
                LOOP
                    IF v_column_list != '' THEN
                        v_column_list := v_column_list || ', ';
                        v_value_list := v_value_list || ', ';
                    END IF;
                    v_column_list := v_column_list || quote_ident(v_key);

                    -- Check if column is array type
                    v_is_array := is_array_column(v_table, v_key);
                    IF v_is_array AND jsonb_typeof(v_value) = 'array' THEN
                        v_value_list := v_value_list || 'jsonb_to_text_array(' || quote_literal(v_value::text) || '::jsonb)';
                    ELSE
                        v_value_list := v_value_list || format_jsonb_value(v_value);
                    END IF;
                END LOOP;

                v_sql := format(
                    'INSERT INTO %I (%s) VALUES (%s) RETURNING to_jsonb(%I.*)',
                    v_table, v_column_list, v_value_list, v_table
                );

                EXECUTE v_sql INTO v_row;

                v_result := jsonb_build_object(
                    'action', 'upsert',
                    'table', v_table,
                    'count', 1,
                    'data', v_row.to_jsonb
                );

                IF v_returns IS NOT NULL THEN
                    v_context := jsonb_set(v_context, ARRAY[v_returns], v_row.to_jsonb);
                END IF;

            ELSE
                RAISE EXCEPTION 'Unknown action: %', v_action;
        END CASE;

        -- Append result
        v_results := v_results || v_result;
    END LOOP;

    RETURN jsonb_build_object(
        'success', true,
        'results', v_results,
        'context', v_context,
        'operations_executed', v_operation_index
    );

EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_code', SQLSTATE,
        'failed_operation_index', v_operation_index,
        'failed_operation', v_operation
    );
END;
$$;

COMMENT ON FUNCTION execute_write_intent(jsonb, jsonb) IS
'Executes multi-operation write intents atomically with proper array type handling. Fixed in migration 007 to handle text[] columns.';


-- ============================================================================
-- Helper Function: Format JSONB value for SQL
-- (Update if it doesn't exist or needs array handling)
-- ============================================================================

CREATE OR REPLACE FUNCTION format_jsonb_value(p_value jsonb)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    IF p_value IS NULL OR p_value = 'null'::jsonb THEN
        RETURN 'NULL';
    ELSIF jsonb_typeof(p_value) = 'string' THEN
        RETURN quote_literal(p_value #>> '{}');
    ELSIF jsonb_typeof(p_value) = 'number' THEN
        RETURN p_value::text;
    ELSIF jsonb_typeof(p_value) = 'boolean' THEN
        RETURN p_value::text;
    ELSIF jsonb_typeof(p_value) = 'object' THEN
        -- For JSONB columns, pass as JSONB
        RETURN quote_literal(p_value::text) || '::jsonb';
    ELSIF jsonb_typeof(p_value) = 'array' THEN
        -- Arrays for JSONB columns (not text[] - those are handled separately)
        RETURN quote_literal(p_value::text) || '::jsonb';
    ELSE
        RETURN quote_literal(p_value::text);
    END IF;
END;
$$;

COMMENT ON FUNCTION format_jsonb_value(jsonb) IS
'Formats a JSONB value for use in dynamic SQL. Handles NULL, strings, numbers, booleans, and nested objects.';


-- ============================================================================
-- Helper Function: Build WHERE clause from filters
-- ============================================================================

CREATE OR REPLACE FUNCTION build_where_clause(p_filters jsonb)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_clause text := '';
    v_key text;
    v_value jsonb;
    v_operator text;
    v_operand jsonb;
    v_in_values text;
    v_item jsonb;
BEGIN
    IF p_filters IS NULL OR p_filters = '{}'::jsonb THEN
        RETURN 'TRUE';
    END IF;

    FOR v_key, v_value IN SELECT * FROM jsonb_each(p_filters)
    LOOP
        IF v_clause != '' THEN
            v_clause := v_clause || ' AND ';
        END IF;

        -- Check if value is an operator object
        IF jsonb_typeof(v_value) = 'object' THEN
            -- Operator format: {"gt": 10} or {"in": [1,2,3]}
            FOR v_operator, v_operand IN SELECT * FROM jsonb_each(v_value)
            LOOP
                CASE v_operator
                    WHEN 'eq' THEN
                        v_clause := v_clause || quote_ident(v_key) || ' = ' || format_jsonb_value(v_operand);
                    WHEN 'neq' THEN
                        v_clause := v_clause || quote_ident(v_key) || ' != ' || format_jsonb_value(v_operand);
                    WHEN 'gt' THEN
                        v_clause := v_clause || quote_ident(v_key) || ' > ' || format_jsonb_value(v_operand);
                    WHEN 'gte' THEN
                        v_clause := v_clause || quote_ident(v_key) || ' >= ' || format_jsonb_value(v_operand);
                    WHEN 'lt' THEN
                        v_clause := v_clause || quote_ident(v_key) || ' < ' || format_jsonb_value(v_operand);
                    WHEN 'lte' THEN
                        v_clause := v_clause || quote_ident(v_key) || ' <= ' || format_jsonb_value(v_operand);
                    WHEN 'in' THEN
                        v_in_values := '';
                        FOR v_item IN SELECT * FROM jsonb_array_elements(v_operand)
                        LOOP
                            IF v_in_values != '' THEN
                                v_in_values := v_in_values || ', ';
                            END IF;
                            v_in_values := v_in_values || format_jsonb_value(v_item);
                        END LOOP;
                        v_clause := v_clause || quote_ident(v_key) || ' IN (' || v_in_values || ')';
                    WHEN 'like' THEN
                        v_clause := v_clause || quote_ident(v_key) || ' LIKE ' || format_jsonb_value(v_operand);
                    WHEN 'ilike' THEN
                        v_clause := v_clause || quote_ident(v_key) || ' ILIKE ' || format_jsonb_value(v_operand);
                    WHEN 'is_null' THEN
                        IF v_operand::boolean THEN
                            v_clause := v_clause || quote_ident(v_key) || ' IS NULL';
                        ELSE
                            v_clause := v_clause || quote_ident(v_key) || ' IS NOT NULL';
                        END IF;
                    ELSE
                        RAISE EXCEPTION 'Unknown operator: %', v_operator;
                END CASE;
            END LOOP;
        ELSE
            -- Simple equality
            v_clause := v_clause || quote_ident(v_key) || ' = ' || format_jsonb_value(v_value);
        END IF;
    END LOOP;

    RETURN v_clause;
END;
$$;

COMMENT ON FUNCTION build_where_clause(jsonb) IS
'Builds a WHERE clause from a JSONB filters object. Supports operators: eq, neq, gt, gte, lt, lte, in, like, ilike, is_null.';


-- ============================================================================
-- Helper Function: Resolve @references in JSONB
-- ============================================================================

CREATE OR REPLACE FUNCTION resolve_references(p_data jsonb, p_context jsonb)
RETURNS jsonb
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_result jsonb;
    v_key text;
    v_value jsonb;
    v_ref_match text[];
    v_ref_name text;
    v_ref_path text;
    v_resolved_value jsonb;
BEGIN
    IF p_data IS NULL THEN
        RETURN NULL;
    END IF;

    IF jsonb_typeof(p_data) = 'object' THEN
        v_result := '{}'::jsonb;
        FOR v_key, v_value IN SELECT * FROM jsonb_each(p_data)
        LOOP
            IF jsonb_typeof(v_value) = 'string' AND (v_value #>> '{}') LIKE '@%' THEN
                -- Parse reference: @name.field
                v_ref_match := regexp_match(v_value #>> '{}', '^@([^.]+)\.(.+)$');
                IF v_ref_match IS NOT NULL THEN
                    v_ref_name := v_ref_match[1];
                    v_ref_path := v_ref_match[2];

                    -- Resolve from context
                    v_resolved_value := p_context->v_ref_name;
                    IF v_resolved_value IS NOT NULL THEN
                        -- Navigate path (simple single-level for now)
                        v_resolved_value := v_resolved_value->v_ref_path;
                    END IF;

                    v_result := jsonb_set(v_result, ARRAY[v_key], COALESCE(v_resolved_value, 'null'::jsonb));
                ELSE
                    v_result := jsonb_set(v_result, ARRAY[v_key], v_value);
                END IF;
            ELSIF jsonb_typeof(v_value) = 'object' OR jsonb_typeof(v_value) = 'array' THEN
                v_result := jsonb_set(v_result, ARRAY[v_key], resolve_references(v_value, p_context));
            ELSE
                v_result := jsonb_set(v_result, ARRAY[v_key], v_value);
            END IF;
        END LOOP;
        RETURN v_result;
    ELSIF jsonb_typeof(p_data) = 'array' THEN
        v_result := '[]'::jsonb;
        FOR v_value IN SELECT * FROM jsonb_array_elements(p_data)
        LOOP
            v_result := v_result || resolve_references(v_value, p_context);
        END LOOP;
        RETURN v_result;
    ELSE
        RETURN p_data;
    END IF;
END;
$$;

COMMENT ON FUNCTION resolve_references(jsonb, jsonb) IS
'Resolves @name.field references in JSONB data using the provided context.';
