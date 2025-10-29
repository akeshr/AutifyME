# Phase 2C Continuation Plan

**Status:** 5/11 hours complete (45%)
**Branch:** `claude/review-product-specialist-architecture-011CUa5Zn1NSsuJ61Wjjm5La`

---

## ✅ Completed Tasks

### Task 2C.1: Schema Metadata Layer (3 hours) - COMPLETE
- Schema models (TableSchema, ColumnSchema, Relationship, BusinessRule)
- SchemaRegistry with versioning
- Product catalog v1 schema (9 tables as JSON)
- 27 unit tests (all passing)

### Task 2C.2: Generic Intent Models (1 hour) - COMPLETE
- OperationIntent model (replaces 7 draft types)
- Supporting models (Operation, ChangeSpecification, ImpactAnalysis, ExecutionPlan)
- Specialist updated to use OperationIntent

### Task 2C.3: Universal CRUD Tool (3 hours) - CORE COMPLETE
- OperationExecutor with dependency resolution
- Foreign key reference resolution ($step_N.field)
- Rollback mechanism
- **PENDING:** Storage adapter + unit tests

### Task 2C.4: Schema Query Tool (30 minutes) - COMPLETE
- get_product_schema, get_table_schema, list_available_tables
- Attached to specialist

---

## ⏳ Remaining Tasks (6 hours)

### Task 2C.5: Specialist Prompt Enhancement (2 hours) - HIGH PRIORITY

**Goal:** Teach specialist schema-driven operation planning

**Changes Required:**

1. **Remove Hard-Coded CRUD Classification (~200 lines)**
   - Remove lines about "VARIANT_ADDITION (VariantAdditionDraft) - CREATE"
   - Remove hard-coded rules for each of 7 draft types
   - Remove operation-specific examples tied to old drafts

2. **Add Schema-Driven Planning Section**
```markdown
## Schema-Driven Operation Planning

You have access to the complete product catalog schema via `get_product_schema` tool.

### Planning Process

**For ANY user request:**

1. **Query Schema** (if not cached):
   ```
   get_product_schema(version="latest")
   ```
   This returns all tables, columns, relationships, constraints.

2. **Analyze Request**:
   - Determine affected tables from schema
   - Identify operation types (insert/update/delete/query)
   - Calculate dependencies (parent tables before children)

3. **Generate OperationIntent**:
   ```json
   {
     "intent_type": "create",
     "change_spec": {
       "domain": "product_catalog",
       "operations": [
         {
           "op_type": "insert",
           "table": "variant_values",
           "new_entities": [{...}]
         },
         {
           "op_type": "insert",
           "table": "products",
           "new_entities": [{...}],
           "depends_on": [0]
         }
       ]
     },
     "impact_analysis": {
       "new_entities_count": {"variant_values": 1, "products": 2},
       "business_impact_summary": "Will create 2 new SKUs",
       "examples": ["BOTTLE-BLK-2L", "BOTTLE-WHT-2L"]
     },
     "execution_plan": {
       "steps": [
         {
           "step_number": 1,
           "description": "Insert 2L variant value",
           "operation": {...}
         },
         {
           "step_number": 2,
           "description": "Generate SKUs for 2L",
           "operation": {...}
         }
       ]
     }
   }
   ```

4. **Foreign Key Resolution**:
   Use `$step_N.field` syntax to reference created IDs:
   ```json
   {
     "variant_axis_id": "$step_1.axis_id"
   }
   ```

### Examples

**Example 1: Add 2L Capacity (Granular CREATE)**

User: "Add 2L capacity to water bottle family"

1. Query schema → see variant_values, products tables
2. Search existing family → get structure
3. Generate OperationIntent:
   - Operation 1: INSERT variant_values (new 2L value)
   - Operation 2: INSERT products (2 new SKUs, depends_on: [0])
   - Impact: 2 new SKUs (2L × 2 existing colors)

**Example 2: Update Base Price (UPDATE)**

User: "Change base price to Rs 35"

1. Query schema → see product_families table
2. Search family → get family_id
3. Generate OperationIntent:
   - Operation 1: UPDATE product_families
   - target_filter: {"id": "family-uuid"}
   - field_updates: {"base_price": 35.00}
   - Impact: 1 family updated

**Example 3: Delete Variant (DELETE with Impact)**

User: "Remove Amber color option"

1. Query schema → see variant_values, products (cascade)
2. Calculate impact:
   - 3 SKUs will be deleted (cascade from variant_values)
   - 5 images affected
   - 2 content pieces affected
3. Generate OperationIntent with impact_analysis

**Example 4: Query SKUs (READ)**

User: "Show all SKUs"

1. Query schema → see products table
2. Generate OperationIntent:
   - Operation 1: QUERY products
   - query_filter: {"product_family_id": "..."}
   - include_relations: ["variant_values"]
```

3. **Add Impact Calculation Guidance**
```markdown
### Impact Analysis Calculation

Calculate from schema + current data:

**For CREATE:**
- Query existing variants to calculate combinations
- Example: Add value to axis with 3 values + 2 colors = 6 new SKUs

**For UPDATE:**
- Count affected rows from filter
- Warn if changing critical fields (base_price affects all SKUs)

**For DELETE:**
- Follow cascade relationships in schema
- Count affected rows in all cascading tables
- Generate examples of what will be deleted
```

**File:** `agents/src/autifyme_agents/prompts/specialists/product_architecture_specialist.prompt`

---

### Task 2C.6: PM Workflow Simplification (1 hour)

**Goal:** Remove hard-coded routing, use generic HITL

**Changes:**

1. **Update PM Tools:**
   - Remove: 6 old specialized tools
   - Add: execute_database_operation (universal tool)
   - Add: get_product_schema (for PM context)

2. **Update PM Prompt:**
   - Remove hard-coded routing (7 case statements)
   - Add generic HITL template:
   ```
   Specialist Result:
   {user_request_summary}

   Impact:
   {business_impact_summary}

   Changes:
   {format_impact_analysis}

   Warnings: {warnings}

   Approve?
   ```

3. **Generic Tool Invocation:**
   ```python
   # PM receives OperationIntent
   specialist_result = await delegate_to_specialist(...)

   # Generic presentation
   await present_for_approval(format_impact(specialist_result))

   # Single tool call
   result = await execute_database_operation(
       intent=specialist_result.model_dump()
   )
   ```

**Files:**
- `agents/src/autifyme_agents/workflows/project_manager.py`
- `agents/src/autifyme_agents/prompts/workflows/project_manager.prompt`

---

### Task 2C.7: Business Rules Migration (1 hour)

**Goal:** Extract hard-coded business logic to metadata

**Changes:**

1. **Create Business Rule Handlers:**
   ```python
   # agents/src/autifyme_agents/business_rules/handlers.py

   class BusinessRuleHandlers:
       @staticmethod
       async def generate_sku_explosion_for_new_axis(
           operation, result, parameters, schema, storage
       ):
           # SKU generation logic
           pass

       @staticmethod
       async def validate_price_range(operation, result, parameters, **kwargs):
           # Price validation logic
           pass
   ```

2. **Update Schema with Rules:**
   ```json
   {
     "business_rules": [
       {
         "rule_type": "generate_sku_explosion",
         "trigger": "after_insert",
         "handler": "generate_sku_explosion_for_new_axis",
         "parameters": {"warn_threshold": 100}
       }
     ]
   }
   ```

3. **Integrate with OperationExecutor:**
   - Already has `_trigger_business_rules()` method
   - Just needs handler registry connection

**Files:**
- NEW: `agents/src/autifyme_agents/business_rules/handlers.py`
- UPDATE: `agents/src/autifyme_agents/schemas/registry/versions/product_catalog/v1.json`
- UPDATE: `agents/src/autifyme_agents/tools/universal_crud_tool.py` (connect handlers)

---

### Task 2C.8: Testing & Validation (2 hours)

**Goal:** Comprehensive testing of dynamic architecture

**Tests Needed:**

1. **Unit Tests:**
   - OperationExecutor tests
   - Reference resolution tests ($step_N.field)
   - Dependency ordering tests
   - Rollback tests

2. **Integration Tests:**
   - E2E test: Create full family (OperationIntent → execution)
   - E2E test: Add variant value (granular operation)
   - E2E test: Update field (single UPDATE)
   - E2E test: Delete with impact
   - E2E test: Query data

3. **Future-Proofing Test:**
   - Add fake `product_warranties` table to schema
   - Generate OperationIntent for warranty CRUD
   - Verify tool validates and would execute (dry run)

4. **Performance Benchmarks:**
   - Compare execution time vs Phase 2B
   - Target: < 2x baseline

**Files:**
- NEW: `tests/unit/tools/test_operation_executor.py`
- NEW: `tests/integration/test_dynamic_crud.py`
- NEW: `tests/integration/test_future_proofing.py`

---

### Task 2C.9: Cleanup Obsolete Code (1 hour)

**Goal:** Remove Phase 2B code

**Remove:**
- `agents/src/autifyme_agents/schemas/product_drafts.py` (7 draft types)
- `agents/src/autifyme_agents/tools/product_crud_tools.py` (old CRUD tools)
- Old tool functions in `product_persistence_tools.py`

**Update:**
- PM tool imports (remove 6 old tools)
- Remove ~200 lines from specialist prompt

**Deprecate:**
- `docs/architecture/PRODUCT_SPECIALIST_CRUD_IMPLEMENTATION.md`

---

## Storage Adapter Implementation (Critical)

**Current Issue:** OperationExecutor has placeholder methods:
- `_insert_entity()`
- `_update_entities()`
- `_delete_entities()`
- `_query_entities()`

**Solution:** Connect to actual Supabase client

```python
# In universal_crud_tool.py

async def _insert_entity(self, table: str, entity: dict[str, Any]) -> dict[str, Any]:
    """Insert single entity via Supabase."""
    client = self.storage._ensure_client()

    result = client.table(table).insert(entity).execute()

    if not result.data:
        raise ToolException(f"Failed to insert into {table}")

    return result.data[0]

async def _update_entities(
    self, table: str, filter: dict[str, Any], updates: dict[str, Any]
) -> int:
    """Update entities via Supabase."""
    client = self.storage._ensure_client()

    # Build filter query
    query = client.table(table).update(updates)
    for key, value in filter.items():
        query = query.eq(key, value)

    result = query.execute()
    return len(result.data)

# Similar for _delete_entities and _query_entities
```

---

## Commit Strategy

**Commit after each completed task:**
1. Task 2C.5 → Commit + push
2. Task 2C.6 → Commit + push
3. Task 2C.7 → Commit + push
4. Task 2C.8 → Commit + push
5. Task 2C.9 → Commit + push

**Update specialist doc** after each commit.

---

## Success Criteria

**Phase 2C Complete When:**
- ✅ All 9 tasks complete
- ✅ All tests passing (85%+ coverage)
- ✅ Storage adapter implemented
- ✅ E2E test: Add new table works without code changes
- ✅ Documentation updated

---

## Next Session Priorities

1. **Task 2C.5:** Specialist prompt enhancement (2 hours)
2. **Storage adapter:** Connect OperationExecutor to Supabase (1 hour)
3. **Task 2C.6:** PM workflow simplification (1 hour)
4. **Task 2C.8:** Testing (prioritize E2E tests)

**Estimated:** 4-5 hours of focused work to complete Phase 2C.
