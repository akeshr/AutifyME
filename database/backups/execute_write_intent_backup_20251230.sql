-- Backup of execute_write_intent and related functions
-- Created: 2025-12-30
-- Reason: Before applying array type fix

-- ============================================================================
-- Function: build_write_where_clause
-- ============================================================================

CREATE OR REPLACE FUNCTION public.build_write_where_clause(p_filters jsonb)
 RETURNS TABLE(where_clause text, params jsonb)
 LANGUAGE plpgsql
AS $function$
DECLARE
    clauses text[] := '{}';
    key text;
    val jsonb;
    op text;
    operand jsonb;
BEGIN
    IF p_filters IS NULL OR p_filters = '{}'::jsonb THEN
        RETURN QUERY SELECT 'TRUE'::text, '{}'::jsonb;
        RETURN;
    END IF;

    FOR key, val IN SELECT * FROM jsonb_each(p_filters) LOOP
        IF jsonb_typeof(val) = 'object' THEN
            -- Operator syntax: {"column": {"op": value}}
            FOR op, operand IN SELECT * FROM jsonb_each(val) LOOP
                CASE op
                    WHEN 'in' THEN
                        -- IN operator - expects array of UUIDs
                        clauses := array_append(clauses,
                            format('%I = ANY(SELECT jsonb_array_elements_text($2->%L->%L)::uuid)', key, key, op));
                    WHEN 'eq' THEN
                        clauses := array_append(clauses,
                            format('%I = ($2->%L->>%L)::%s', key, key, op,
                                CASE
                                    WHEN jsonb_typeof(operand) = 'number' THEN 'numeric'
                                    WHEN jsonb_typeof(operand) = 'boolean' THEN 'boolean'
                                    WHEN (operand #>> '{}') ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN 'uuid'
                                    ELSE 'text'
                                END));
                    WHEN 'neq' THEN
                        clauses := array_append(clauses,
                            format('%I <> ($2->%L->>%L)::%s', key, key, op,
                                CASE
                                    WHEN jsonb_typeof(operand) = 'number' THEN 'numeric'
                                    WHEN jsonb_typeof(operand) = 'boolean' THEN 'boolean'
                                    WHEN (operand #>> '{}') ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN 'uuid'
                                    ELSE 'text'
                                END));
                    WHEN 'gt' THEN
                        clauses := array_append(clauses,
                            format('%I > ($2->%L->>%L)::numeric', key, key, op));
                    WHEN 'gte' THEN
                        clauses := array_append(clauses,
                            format('%I >= ($2->%L->>%L)::numeric', key, key, op));
                    WHEN 'lt' THEN
                        clauses := array_append(clauses,
                            format('%I < ($2->%L->>%L)::numeric', key, key, op));
                    WHEN 'lte' THEN
                        clauses := array_append(clauses,
                            format('%I <= ($2->%L->>%L)::numeric', key, key, op));
                    ELSE
                        RAISE EXCEPTION 'Unsupported filter operator: %', op;
                END CASE;
            END LOOP;
        ELSIF jsonb_typeof(val) = 'array' THEN
            -- Implicit IN operator for array values
            clauses := array_append(clauses,
                format('%I = ANY(SELECT jsonb_array_elements_text($2->%L)::uuid)', key, key));
        ELSE
            -- Simple equality - detect UUID pattern
            clauses := array_append(clauses,
                format('%I = ($2->>%L)::%s', key, key,
                    CASE
                        WHEN jsonb_typeof(val) = 'number' THEN 'numeric'
                        WHEN jsonb_typeof(val) = 'boolean' THEN 'boolean'
                        WHEN (val #>> '{}') ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN 'uuid'
                        ELSE 'text'
                    END));
        END IF;
    END LOOP;

    RETURN QUERY SELECT array_to_string(clauses, ' AND '), p_filters;
END;
$function$;


-- ============================================================================
-- Function: resolve_write_references
-- ============================================================================

CREATE OR REPLACE FUNCTION public.resolve_write_references(p_data jsonb, p_context jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
DECLARE
    result jsonb;
    key text;
    val jsonb;
    val_text text;
    ref_match text[];
    ref_name text;
    ref_index int;
    ref_field text;
    resolved_val jsonb;
    ctx_val jsonb;
    field_parts text[];
    i int;
BEGIN
    -- Handle NULL or non-object inputs
    IF p_data IS NULL THEN
        RETURN NULL;
    END IF;

    -- Handle arrays - recursively resolve each element
    IF jsonb_typeof(p_data) = 'array' THEN
        result := '[]'::jsonb;
        FOR i IN 0..jsonb_array_length(p_data) - 1 LOOP
            result := result || jsonb_build_array(
                resolve_write_references(p_data->i, p_context)
            );
        END LOOP;
        RETURN result;
    END IF;

    -- Handle non-objects (primitives)
    IF jsonb_typeof(p_data) != 'object' THEN
        RETURN p_data;
    END IF;

    -- Process object keys
    result := '{}'::jsonb;
    FOR key, val IN SELECT * FROM jsonb_each(p_data) LOOP
        IF jsonb_typeof(val) = 'string' THEN
            val_text := val #>> '{}';  -- Extract text value

            IF val_text LIKE '@%' THEN
                -- Parse reference: @name.field or @name[idx].field
                -- Pattern 1: @name[idx].field
                ref_match := regexp_match(val_text, '^@([a-zA-Z_][a-zA-Z0-9_]*)\[(\d+)\]\.(.+)$');
                IF ref_match IS NOT NULL THEN
                    ref_name := ref_match[1];
                    ref_index := ref_match[2]::int;
                    ref_field := ref_match[3];

                    -- Get context value
                    ctx_val := p_context->ref_name;
                    IF ctx_val IS NULL THEN
                        RAISE EXCEPTION 'Reference "@%" not found in context. Available: %',
                            ref_name, (SELECT string_agg(k, ', ') FROM jsonb_object_keys(p_context) k);
                    END IF;

                    -- Handle array index
                    IF jsonb_typeof(ctx_val) = 'array' THEN
                        ctx_val := ctx_val->ref_index;
                    ELSE
                        RAISE EXCEPTION 'Reference "@%" is not an array, cannot use index [%]', ref_name, ref_index;
                    END IF;

                    -- Navigate to field (supports nested paths like metadata.sku)
                    field_parts := string_to_array(ref_field, '.');
                    resolved_val := ctx_val;
                    FOREACH ref_field IN ARRAY field_parts LOOP
                        resolved_val := resolved_val->ref_field;
                        IF resolved_val IS NULL THEN
                            RAISE EXCEPTION 'Field "%" not found in "@%[%]"', ref_field, ref_name, ref_index;
                        END IF;
                    END LOOP;

                    result := jsonb_set(result, ARRAY[key], resolved_val);
                    CONTINUE;
                END IF;

                -- Pattern 2: @name.field (simple)
                ref_match := regexp_match(val_text, '^@([a-zA-Z_][a-zA-Z0-9_]*)\.(.+)$');
                IF ref_match IS NOT NULL THEN
                    ref_name := ref_match[1];
                    ref_field := ref_match[2];

                    -- Get context value
                    ctx_val := p_context->ref_name;
                    IF ctx_val IS NULL THEN
                        RAISE EXCEPTION 'Reference "@%" not found in context. Available: %',
                            ref_name, (SELECT string_agg(k, ', ') FROM jsonb_object_keys(p_context) k);
                    END IF;

                    -- If context value is an array, use first element (for batch returns)
                    IF jsonb_typeof(ctx_val) = 'array' AND jsonb_array_length(ctx_val) > 0 THEN
                        ctx_val := ctx_val->0;
                    END IF;

                    -- Navigate to field (supports nested paths)
                    field_parts := string_to_array(ref_field, '.');
                    resolved_val := ctx_val;
                    FOREACH ref_field IN ARRAY field_parts LOOP
                        resolved_val := resolved_val->ref_field;
                        IF resolved_val IS NULL THEN
                            RAISE EXCEPTION 'Field "%" not found in "@%"', ref_field, ref_name;
                        END IF;
                    END LOOP;

                    result := jsonb_set(result, ARRAY[key], resolved_val);
                    CONTINUE;
                END IF;

                -- Invalid reference format
                RAISE EXCEPTION 'Invalid reference syntax: "%". Expected @name.field or @name[idx].field', val_text;
            ELSE
                -- Not a reference, keep as-is
                result := jsonb_set(result, ARRAY[key], val);
            END IF;
        ELSIF jsonb_typeof(val) = 'object' THEN
            -- Recursively resolve nested objects
            result := jsonb_set(result, ARRAY[key], resolve_write_references(val, p_context));
        ELSIF jsonb_typeof(val) = 'array' THEN
            -- Recursively resolve arrays
            result := jsonb_set(result, ARRAY[key], resolve_write_references(val, p_context));
        ELSE
            -- Keep primitives (numbers, booleans, null)
            result := jsonb_set(result, ARRAY[key], val);
        END IF;
    END LOOP;

    RETURN result;
END;
$function$;


-- ============================================================================
-- Function: execute_write_intent (MAIN FUNCTION)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.execute_write_intent(p_operations jsonb, p_context jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
    v_context jsonb := COALESCE(p_context, '{}'::jsonb);
    v_results jsonb := '[]'::jsonb;
    v_operation jsonb;
    v_action text;
    v_table text;
    v_data jsonb;
    v_filters jsonb;
    v_updates jsonb;
    v_returns text;
    v_on_conflict text;
    v_conflict_fields text[];
    v_soft_delete boolean;
    v_resolved_data jsonb;
    v_resolved_filters jsonb;
    v_resolved_updates jsonb;
    v_where_clause text;
    v_result jsonb;
    v_batch_results jsonb;
    v_count int;
    v_sql text;
    v_item jsonb;
    v_op_index int := 0;
    v_columns text[];
    v_values text[];
    v_update_sets text[];
BEGIN
    -- Validate input
    IF p_operations IS NULL OR jsonb_typeof(p_operations) != 'array' THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'p_operations must be a non-null JSONB array',
            'error_code', 'INVALID_INPUT'
        );
    END IF;

    IF jsonb_array_length(p_operations) = 0 THEN
        RETURN jsonb_build_object(
            'success', true,
            'results', '[]'::jsonb,
            'context', v_context,
            'message', 'No operations to execute'
        );
    END IF;

    -- Process each operation in order
    FOR v_operation IN SELECT * FROM jsonb_array_elements(p_operations) LOOP
        v_op_index := v_op_index + 1;

        -- Extract operation fields (handle JSON null vs SQL NULL)
        v_action := v_operation->>'action';
        v_table := v_operation->>'table';
        v_data := CASE WHEN jsonb_typeof(v_operation->'data') = 'null' THEN NULL ELSE v_operation->'data' END;
        v_filters := CASE WHEN jsonb_typeof(v_operation->'filters') = 'null' THEN NULL ELSE v_operation->'filters' END;
        v_updates := CASE WHEN jsonb_typeof(v_operation->'updates') = 'null' THEN NULL ELSE v_operation->'updates' END;
        v_returns := v_operation->>'returns';
        v_on_conflict := COALESCE(v_operation->>'on_conflict', 'error');
        v_soft_delete := COALESCE((v_operation->>'soft_delete')::boolean, true);

        -- Parse conflict_fields array (handle JSON null)
        IF v_operation->'conflict_fields' IS NOT NULL AND jsonb_typeof(v_operation->'conflict_fields') = 'array' THEN
            SELECT array_agg(cf::text) INTO v_conflict_fields
            FROM jsonb_array_elements_text(v_operation->'conflict_fields') cf;
        ELSE
            v_conflict_fields := NULL;
        END IF;

        -- Resolve references in data, filters, updates
        v_resolved_data := resolve_write_references(v_data, v_context);
        v_resolved_filters := resolve_write_references(v_filters, v_context);
        v_resolved_updates := resolve_write_references(COALESCE(v_updates, v_data), v_context);

        -- Execute based on action
        CASE v_action
            WHEN 'create' THEN
                IF v_resolved_data IS NULL THEN
                    RAISE EXCEPTION 'CREATE requires data field';
                END IF;

                IF jsonb_typeof(v_resolved_data) = 'array' THEN
                    v_batch_results := '[]'::jsonb;

                    FOR v_item IN SELECT * FROM jsonb_array_elements(v_resolved_data) LOOP
                        SELECT array_agg(k), array_agg(format('($1->>%L)::%s', k,
                            CASE
                                WHEN jsonb_typeof(v_item->k) = 'number' THEN
                                    CASE WHEN (v_item->>k) ~ '^\d+$' THEN 'bigint' ELSE 'numeric' END
                                WHEN jsonb_typeof(v_item->k) = 'boolean' THEN 'boolean'
                                WHEN jsonb_typeof(v_item->k) = 'object' THEN 'jsonb'
                                WHEN jsonb_typeof(v_item->k) = 'array' THEN 'jsonb'
                                WHEN (v_item->>k) ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN 'uuid'
                                WHEN (v_item->>k) ~ '^\d{4}-\d{2}-\d{2}' THEN 'timestamptz'
                                ELSE 'text'
                            END))
                        INTO v_columns, v_values
                        FROM jsonb_object_keys(v_item) k;

                        v_sql := format(
                            'INSERT INTO %I (%s) VALUES (%s) RETURNING to_jsonb(%I.*)',
                            v_table,
                            array_to_string(ARRAY(SELECT quote_ident(c) FROM unnest(v_columns) c), ', '),
                            array_to_string(v_values, ', '),
                            v_table
                        );

                        EXECUTE v_sql INTO v_result USING v_item;
                        v_batch_results := v_batch_results || jsonb_build_array(v_result);
                    END LOOP;

                    IF v_returns IS NOT NULL THEN
                        v_context := jsonb_set(v_context, ARRAY[v_returns], v_batch_results);
                    END IF;

                    v_results := v_results || jsonb_build_array(jsonb_build_object(
                        'action', 'create',
                        'table', v_table,
                        'count', jsonb_array_length(v_batch_results),
                        'data', v_batch_results
                    ));
                ELSE
                    SELECT array_agg(k), array_agg(format('($1->>%L)::%s', k,
                        CASE
                            WHEN jsonb_typeof(v_resolved_data->k) = 'number' THEN
                                CASE WHEN (v_resolved_data->>k) ~ '^\d+$' THEN 'bigint' ELSE 'numeric' END
                            WHEN jsonb_typeof(v_resolved_data->k) = 'boolean' THEN 'boolean'
                            WHEN jsonb_typeof(v_resolved_data->k) = 'object' THEN 'jsonb'
                            WHEN jsonb_typeof(v_resolved_data->k) = 'array' THEN 'jsonb'
                            WHEN (v_resolved_data->>k) ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN 'uuid'
                            WHEN (v_resolved_data->>k) ~ '^\d{4}-\d{2}-\d{2}' THEN 'timestamptz'
                            ELSE 'text'
                        END))
                    INTO v_columns, v_values
                    FROM jsonb_object_keys(v_resolved_data) k;

                    v_sql := format(
                        'INSERT INTO %I (%s) VALUES (%s) RETURNING to_jsonb(%I.*)',
                        v_table,
                        array_to_string(ARRAY(SELECT quote_ident(c) FROM unnest(v_columns) c), ', '),
                        array_to_string(v_values, ', '),
                        v_table
                    );

                    EXECUTE v_sql INTO v_result USING v_resolved_data;

                    IF v_returns IS NOT NULL THEN
                        v_context := jsonb_set(v_context, ARRAY[v_returns], v_result);
                    END IF;

                    v_results := v_results || jsonb_build_array(jsonb_build_object(
                        'action', 'create',
                        'table', v_table,
                        'count', 1,
                        'data', v_result
                    ));
                END IF;

            WHEN 'update' THEN
                IF v_resolved_filters IS NULL OR v_resolved_filters = '{}'::jsonb THEN
                    RAISE EXCEPTION 'UPDATE requires filters field';
                END IF;

                IF v_resolved_updates IS NULL OR v_resolved_updates = '{}'::jsonb THEN
                    RAISE EXCEPTION 'UPDATE requires updates or data field';
                END IF;

                SELECT array_agg(format('%I = ($1->>%L)::%s', k, k,
                    CASE
                        WHEN jsonb_typeof(v_resolved_updates->k) = 'number' THEN
                            CASE WHEN (v_resolved_updates->>k) ~ '^\d+$' THEN 'bigint' ELSE 'numeric' END
                        WHEN jsonb_typeof(v_resolved_updates->k) = 'boolean' THEN 'boolean'
                        WHEN jsonb_typeof(v_resolved_updates->k) = 'object' THEN 'jsonb'
                        WHEN jsonb_typeof(v_resolved_updates->k) = 'array' THEN 'jsonb'
                        WHEN (v_resolved_updates->>k) ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN 'uuid'
                        WHEN (v_resolved_updates->>k) ~ '^\d{4}-\d{2}-\d{2}' THEN 'timestamptz'
                        ELSE 'text'
                    END))
                INTO v_update_sets
                FROM jsonb_object_keys(v_resolved_updates) k;

                SELECT wc.where_clause INTO v_where_clause
                FROM build_write_where_clause(v_resolved_filters) wc;

                v_sql := format(
                    'WITH updated AS (UPDATE %I SET %s WHERE %s RETURNING 1) SELECT count(*) FROM updated',
                    v_table,
                    array_to_string(v_update_sets, ', '),
                    v_where_clause
                );

                EXECUTE v_sql INTO v_count USING v_resolved_updates, v_resolved_filters;

                v_results := v_results || jsonb_build_array(jsonb_build_object(
                    'action', 'update',
                    'table', v_table,
                    'count', COALESCE(v_count, 0)
                ));

            WHEN 'delete' THEN
                IF v_resolved_filters IS NULL OR v_resolved_filters = '{}'::jsonb THEN
                    RAISE EXCEPTION 'DELETE requires filters field';
                END IF;

                SELECT wc.where_clause INTO v_where_clause
                FROM build_write_where_clause(v_resolved_filters) wc;

                v_where_clause := replace(v_where_clause, '$2', '$1');

                IF v_soft_delete THEN
                    v_sql := format(
                        'WITH updated AS (UPDATE %I SET is_active = false, deleted_at = now(), updated_at = now() WHERE %s AND is_active = true RETURNING 1) SELECT count(*) FROM updated',
                        v_table,
                        v_where_clause
                    );
                ELSE
                    v_sql := format(
                        'WITH deleted AS (DELETE FROM %I WHERE %s RETURNING 1) SELECT count(*) FROM deleted',
                        v_table,
                        v_where_clause
                    );
                END IF;

                EXECUTE v_sql INTO v_count USING v_resolved_filters;

                v_results := v_results || jsonb_build_array(jsonb_build_object(
                    'action', 'delete',
                    'table', v_table,
                    'count', COALESCE(v_count, 0),
                    'soft_delete', v_soft_delete
                ));

            WHEN 'upsert' THEN
                IF v_resolved_data IS NULL THEN
                    RAISE EXCEPTION 'UPSERT requires data field';
                END IF;

                IF v_conflict_fields IS NULL OR array_length(v_conflict_fields, 1) = 0 THEN
                    v_conflict_fields := ARRAY['id'];
                END IF;

                IF jsonb_typeof(v_resolved_data) = 'array' THEN
                    v_batch_results := '[]'::jsonb;

                    FOR v_item IN SELECT * FROM jsonb_array_elements(v_resolved_data) LOOP
                        SELECT array_agg(k), array_agg(format('($1->>%L)::%s', k,
                            CASE
                                WHEN jsonb_typeof(v_item->k) = 'number' THEN
                                    CASE WHEN (v_item->>k) ~ '^\d+$' THEN 'bigint' ELSE 'numeric' END
                                WHEN jsonb_typeof(v_item->k) = 'boolean' THEN 'boolean'
                                WHEN jsonb_typeof(v_item->k) = 'object' THEN 'jsonb'
                                WHEN jsonb_typeof(v_item->k) = 'array' THEN 'jsonb'
                                WHEN (v_item->>k) ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN 'uuid'
                                WHEN (v_item->>k) ~ '^\d{4}-\d{2}-\d{2}' THEN 'timestamptz'
                                ELSE 'text'
                            END))
                        INTO v_columns, v_values
                        FROM jsonb_object_keys(v_item) k;

                        IF v_on_conflict = 'skip' THEN
                            v_sql := format(
                                'INSERT INTO %I (%s) VALUES (%s) ON CONFLICT (%s) DO NOTHING RETURNING to_jsonb(%I.*)',
                                v_table,
                                array_to_string(ARRAY(SELECT quote_ident(c) FROM unnest(v_columns) c), ', '),
                                array_to_string(v_values, ', '),
                                array_to_string(ARRAY(SELECT quote_ident(c) FROM unnest(v_conflict_fields) c), ', '),
                                v_table
                            );
                        ELSE
                            SELECT array_agg(format('%I = EXCLUDED.%I', c, c))
                            INTO v_update_sets
                            FROM unnest(v_columns) c
                            WHERE c != ALL(v_conflict_fields);

                            v_sql := format(
                                'INSERT INTO %I (%s) VALUES (%s) ON CONFLICT (%s) DO UPDATE SET %s RETURNING to_jsonb(%I.*)',
                                v_table,
                                array_to_string(ARRAY(SELECT quote_ident(c) FROM unnest(v_columns) c), ', '),
                                array_to_string(v_values, ', '),
                                array_to_string(ARRAY(SELECT quote_ident(c) FROM unnest(v_conflict_fields) c), ', '),
                                array_to_string(v_update_sets, ', '),
                                v_table
                            );
                        END IF;

                        EXECUTE v_sql INTO v_result USING v_item;
                        IF v_result IS NOT NULL THEN
                            v_batch_results := v_batch_results || jsonb_build_array(v_result);
                        END IF;
                    END LOOP;

                    IF v_returns IS NOT NULL THEN
                        v_context := jsonb_set(v_context, ARRAY[v_returns], v_batch_results);
                    END IF;

                    v_results := v_results || jsonb_build_array(jsonb_build_object(
                        'action', 'upsert',
                        'table', v_table,
                        'count', jsonb_array_length(v_batch_results),
                        'data', v_batch_results
                    ));
                ELSE
                    SELECT array_agg(k), array_agg(format('($1->>%L)::%s', k,
                        CASE
                            WHEN jsonb_typeof(v_resolved_data->k) = 'number' THEN
                                CASE WHEN (v_resolved_data->>k) ~ '^\d+$' THEN 'bigint' ELSE 'numeric' END
                            WHEN jsonb_typeof(v_resolved_data->k) = 'boolean' THEN 'boolean'
                            WHEN jsonb_typeof(v_resolved_data->k) = 'object' THEN 'jsonb'
                            WHEN jsonb_typeof(v_resolved_data->k) = 'array' THEN 'jsonb'
                            WHEN (v_resolved_data->>k) ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN 'uuid'
                            WHEN (v_resolved_data->>k) ~ '^\d{4}-\d{2}-\d{2}' THEN 'timestamptz'
                            ELSE 'text'
                        END))
                    INTO v_columns, v_values
                    FROM jsonb_object_keys(v_resolved_data) k;

                    IF v_on_conflict = 'skip' THEN
                        v_sql := format(
                            'INSERT INTO %I (%s) VALUES (%s) ON CONFLICT (%s) DO NOTHING RETURNING to_jsonb(%I.*)',
                            v_table,
                            array_to_string(ARRAY(SELECT quote_ident(c) FROM unnest(v_columns) c), ', '),
                            array_to_string(v_values, ', '),
                            array_to_string(ARRAY(SELECT quote_ident(c) FROM unnest(v_conflict_fields) c), ', '),
                            v_table
                        );
                    ELSE
                        SELECT array_agg(format('%I = EXCLUDED.%I', c, c))
                        INTO v_update_sets
                        FROM unnest(v_columns) c
                        WHERE c != ALL(v_conflict_fields);

                        v_sql := format(
                            'INSERT INTO %I (%s) VALUES (%s) ON CONFLICT (%s) DO UPDATE SET %s RETURNING to_jsonb(%I.*)',
                            v_table,
                            array_to_string(ARRAY(SELECT quote_ident(c) FROM unnest(v_columns) c), ', '),
                            array_to_string(v_values, ', '),
                            array_to_string(ARRAY(SELECT quote_ident(c) FROM unnest(v_conflict_fields) c), ', '),
                            array_to_string(v_update_sets, ', '),
                            v_table
                        );
                    END IF;

                    EXECUTE v_sql INTO v_result USING v_resolved_data;

                    IF v_returns IS NOT NULL AND v_result IS NOT NULL THEN
                        v_context := jsonb_set(v_context, ARRAY[v_returns], v_result);
                    END IF;

                    v_results := v_results || jsonb_build_array(jsonb_build_object(
                        'action', 'upsert',
                        'table', v_table,
                        'count', CASE WHEN v_result IS NOT NULL THEN 1 ELSE 0 END,
                        'data', v_result
                    ));
                END IF;

            ELSE
                RAISE EXCEPTION 'Unknown action: %. Supported: create, update, delete, upsert', v_action;
        END CASE;
    END LOOP;

    RETURN jsonb_build_object(
        'success', true,
        'results', v_results,
        'context', v_context,
        'operations_executed', v_op_index
    );

EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM,
            'error_code', SQLSTATE,
            'failed_operation_index', v_op_index,
            'failed_operation', v_operation
        );
END;
$function$;
