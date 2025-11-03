# Batch Update Analysis: LLM Entity-Specific Updates

**Status:** Analysis Complete
**Date:** 2025-11-03
**Context:** Universal CRUD tool batch update capability gap

---

## Executive Summary

**Current State:** LLMs create separate operations for each record when different records need different field values.

**Root Cause:** Validation layer anticipates entity-specific batch updates, but execution layer doesn't implement it.

**Impact:** N separate DB round-trips instead of 1 batch operation → increased latency, reduced efficiency.

**Recommendation:** Implement Option 2 (UPSERT pattern) for immediate impact, refactor to Option 3 (true batch UPDATE) when storage layer evolves.

---

## Problem Statement

### Current Behavior

When LLM needs to update multiple records with different values:

```python
# LLM must create 3 separate operations
operations = [
    {
        "table": "products",
        "op_type": "update",
        "target_filter": {"id": "uuid-1"},
        "field_updates": {"price": 29.99, "stock": 100}
    },
    {
        "table": "products",
        "op_type": "update",
        "target_filter": {"id": "uuid-2"},
        "field_updates": {"price": 39.99, "stock": 50}
    },
    {
        "table": "products",
        "op_type": "update",
        "target_filter": {"id": "uuid-3"},
        "field_updates": {"price": 49.99}  # Only price, not stock
    }
]
```

**Result:** 3 DB round-trips, 3 execution steps, increased transaction time.

### Intended Architecture (Not Implemented)

Validation code (`universal_crud_tool.py:85-98`) expects single operation with entity-specific values:

```python
# Single operation with entity-specific field updates
{
    "table": "products",
    "op_type": "update",
    "target_filter": {"id": {"in": ["uuid-1", "uuid-2", "uuid-3"]}},
    "field_updates": {
        "price": {
            "uuid-1": 29.99,
            "uuid-2": 39.99,
            "uuid-3": 49.99
        },
        "stock": {
            "uuid-1": 100,
            "uuid-2": 50
            # uuid-3 omitted - don't update stock for this record
        }
    }
}
```

**Expected Result:** 1 DB operation, 1 execution step, minimal transaction time.

---

## Architecture Gap Analysis

### Validation Layer (`_validate_operation_completeness`)

**Location:** `universal_crud_tool.py:85-98`

**Expectation:**
```python
# Check if any field_update value is a dict mapping UUID -> value
for field_name, field_value in operation.field_updates.items():
    if isinstance(field_value, dict):
        actual_count = len(field_value)
        # Validate all entities have values
```

Explicitly anticipates `field_updates` as dict-of-dicts format for entity-specific updates.

### Execution Layer (`_execute_update`)

**Location:** `universal_crud_tool.py:572-620`

**Current Implementation:**
```python
async def _execute_update(self, operation, table_schema, context):
    resolved_filter = self._resolve_references(operation.target_filter, context)
    resolved_updates = self._resolve_references(operation.field_updates, context)

    # Updates ALL matching records with SAME values
    count = await self._update_entities(
        table_schema.name, resolved_filter, resolved_updates
    )
```

**Gap:** Passes `field_updates` directly to storage layer, which applies uniform updates to all matching records. No logic to handle entity-specific value mapping.

### Storage Interface

**Location:** `core/ports.py:374-394`

```python
async def update_entities(
    self,
    table: str,
    filters: dict[str, Any],
    updates: dict[str, Any],  # Uniform updates only
) -> int:
```

**Gap:** No port method for batch updates with entity-specific values. Current signature only supports uniform updates.

---

## Technical Research

### PostgreSQL Native Capabilities

**UPDATE...FROM with VALUES** (most elegant for batch updates):

```sql
UPDATE products as p
SET
    price = v.price,
    stock = v.stock
FROM (VALUES
    ('uuid-1', 29.99, 100),
    ('uuid-2', 39.99, 50),
    ('uuid-3', 49.99, NULL)  -- NULL means don't update stock
) as v(id, price, stock)
WHERE p.id = v.id;
```

**Pros:**
- Single DB round-trip
- Efficient execution plan
- NULL handling for sparse updates (don't update specific fields)
- PostgreSQL-native, well-optimized

**Cons:**
- Requires SQL generation (PostgREST doesn't expose this pattern)
- Complex NULL handling for optional field updates

### Supabase/PostgREST Patterns

**UPSERT with primary keys** (recommended by Supabase):

```python
# Supabase async client upsert
await client.table('products').upsert([
    {"id": "uuid-1", "price": 29.99, "stock": 100},
    {"id": "uuid-2", "price": 39.99, "stock": 50},
    {"id": "uuid-3", "price": 49.99}  # Omit stock to keep existing value
])
```

**Pros:**
- Native PostgREST support (no SQL generation)
- Single network request
- Batch processing built-in
- Field omission = keep existing value (natural sparse update support)

**Cons:**
- Semantically "upsert" not "update" (creates if not exists)
- Requires primary key in payload
- May not fit "update-only" mental model

**Verification:**
```bash
# Confirmed via REPL inspection
upsert(json: JSON, ..., on_conflict: str = '', ...) -> AsyncQueryRequestBuilder
```

PostgREST `upsert()` method exists and supports batch operations.

### LangChain Patterns

LangChain doesn't prescribe batch update patterns - this is application architecture decision. Specialists can generate whatever operation format the tool accepts.

---

## Implementation Options

### Option 1: Sequential Updates (Status Quo)

**Keep current behavior** - LLMs create N operations for N records with different values.

**Architecture:**
```python
# No changes to validation, execution, or storage layers
# LLM generates multiple operations as currently done
```

**Pros:**
- Zero implementation effort
- No risk of breaking existing workflows
- Simple mental model

**Cons:**
- N DB round-trips (latency scales with record count)
- Inefficient for bulk pricing updates, inventory adjustments, etc.
- Validation code serves no purpose (validates format that execution ignores)
- Larger transaction windows (higher conflict risk)

**Recommendation:** ❌ Doesn't align with intelligence-first principle (LLM is smart enough to batch, we block it)

---

### Option 2: UPSERT Pattern (Immediate Implementation)

**Use Supabase upsert for batch updates** - map entity-specific updates to upsert semantics.

**Architecture Changes:**

1. **Add storage port method:**
```python
# core/ports.py
@abstractmethod
async def upsert_entities(
    self,
    table: str,
    entities: list[dict[str, Any]],
    on_conflict: str = "id",  # Primary key column(s)
) -> int:
    """
    Upsert entities (insert or update).

    Each entity dict must include primary key.
    Omitted fields keep existing values.

    Args:
        table: Table name
        entities: List of entity dicts (id + fields to update)
        on_conflict: Conflict resolution column (default: "id")

    Returns:
        Count of upserted rows
    """
```

2. **Implement in Supabase adapter:**
```python
# integrations/storage/supabase_client.py
async def upsert_entities(
    self,
    table: str,
    entities: list[dict[str, Any]],
    on_conflict: str = "id",
) -> int:
    client = await self._ensure_async_client()
    normalized = _normalize_numeric_types(entities)

    response = await (
        client.table(table)
        .upsert(normalized, on_conflict=on_conflict)
        .execute()
    )

    return len(response.data)
```

3. **Update execution layer:**
```python
# tools/universal_crud_tool.py
async def _execute_update(self, operation, table_schema, context):
    # Detect entity-specific update format
    has_entity_specific = any(
        isinstance(v, dict) for v in operation.field_updates.values()
    )

    if has_entity_specific:
        # Transform to upsert format
        entities = self._transform_to_upsert_entities(
            operation.target_filter,
            operation.field_updates,
            context
        )

        count = await self.storage.upsert_entities(
            table_schema.name,
            entities,
            on_conflict="id"
        )
    else:
        # Uniform update (existing path)
        resolved_filter = self._resolve_references(operation.target_filter, context)
        resolved_updates = self._resolve_references(operation.field_updates, context)
        count = await self._update_entities(table_schema.name, resolved_filter, resolved_updates)

    return {"count": count}

def _transform_to_upsert_entities(
    self,
    target_filter: dict[str, Any],
    field_updates: dict[str, Any],
    context: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Transform entity-specific field_updates to upsert entity list.

    Input:
        target_filter: {"id": {"in": ["uuid-1", "uuid-2"]}}
        field_updates: {
            "price": {"uuid-1": 29.99, "uuid-2": 39.99},
            "stock": {"uuid-1": 100}  # Sparse - only uuid-1
        }

    Output:
        [
            {"id": "uuid-1", "price": 29.99, "stock": 100},
            {"id": "uuid-2", "price": 39.99}  # Stock omitted
        ]
    """
    # Extract entity IDs from target_filter
    entity_ids = self._extract_entity_ids(target_filter, context)

    # Build entity dicts
    entities = []
    for entity_id in entity_ids:
        entity = {"id": entity_id}

        # Add field values for this entity
        for field_name, field_value in field_updates.items():
            if isinstance(field_value, dict):
                # Entity-specific value mapping
                if entity_id in field_value:
                    resolved_value = self._resolve_references(
                        field_value[entity_id], context
                    )
                    entity[field_name] = resolved_value
                # Else: omit field (keeps existing value in DB)
            else:
                # Uniform value for all entities
                resolved_value = self._resolve_references(field_value, context)
                entity[field_name] = resolved_value

        entities.append(entity)

    return entities

def _extract_entity_ids(
    self,
    target_filter: dict[str, Any],
    context: dict[int, dict[str, Any]]
) -> list[str]:
    """Extract entity IDs from target_filter."""
    resolved_filter = self._resolve_references(target_filter, context)

    # Handle common patterns
    if "id" in resolved_filter:
        id_value = resolved_filter["id"]
        if isinstance(id_value, dict) and "in" in id_value:
            return id_value["in"]
        elif isinstance(id_value, list):
            return id_value
        else:
            return [id_value]
    else:
        raise ToolException(
            "Batch updates require target_filter with explicit entity IDs. "
            "Use format: {'id': {'in': ['uuid-1', 'uuid-2']}} or {'id': ['uuid-1', 'uuid-2']}"
        )
```

4. **Update specialist prompt guidance:**
```xml
<batch_update_pattern>
When updating multiple records with DIFFERENT values per record, use entity-specific format:

{
  "table": "products",
  "op_type": "update",
  "target_filter": {"id": {"in": ["uuid-1", "uuid-2", "uuid-3"]}},
  "field_updates": {
    "price": {
      "uuid-1": 29.99,
      "uuid-2": 39.99,
      "uuid-3": 49.99
    },
    "stock": {
      "uuid-1": 100,
      "uuid-2": 50
      // Omit uuid-3 to keep existing stock value
    }
  }
}

This executes as single DB operation. Field omission preserves existing values.
</batch_update_pattern>
```

**Pros:**
- ✅ Single DB round-trip for batch updates
- ✅ Native PostgREST support (no SQL generation)
- ✅ Field omission = natural sparse update handling
- ✅ Leverages existing validation code (validates the intended format)
- ✅ Backward compatible (uniform updates still work)
- ✅ Aligns with intelligence-first principle (LLM decides when to batch)

**Cons:**
- ⚠️ Semantic mismatch: "upsert" creates if not exists (rarely desired for updates)
- ⚠️ Requires primary key in target_filter (validation needed)
- ⚠️ Additional storage port method (minor interface expansion)

**Mitigation:**
- Document upsert semantics clearly in specialist prompts
- Add validation: reject batch updates without explicit entity IDs
- Most product operations have stable IDs (upsert = update in practice)

**Recommendation:** ✅ **Implement this option** - best balance of impact vs. effort.

---

### Option 3: True Batch UPDATE (Future Evolution)

**PostgreSQL UPDATE...FROM pattern** - generate SQL for entity-specific updates.

**Architecture Changes:**

1. **Add storage port method:**
```python
@abstractmethod
async def batch_update_entities(
    self,
    table: str,
    updates: list[dict[str, Any]],  # [{"id": "uuid-1", "price": 29.99}, ...]
    id_column: str = "id",
) -> int:
    """
    Update multiple entities with different values.

    Uses PostgreSQL UPDATE...FROM pattern for true batch updates
    (not upsert - fails if entities don't exist).
    """
```

2. **Implement with raw SQL:**
```python
async def batch_update_entities(
    self,
    table: str,
    updates: list[dict[str, Any]],
    id_column: str = "id",
) -> int:
    # Build UPDATE...FROM query
    # Extract fields and build VALUES clause
    # Execute raw SQL via Supabase RPC or direct PostgreSQL connection
```

**Pros:**
- ✅ Pure UPDATE semantics (fails if entity doesn't exist)
- ✅ PostgreSQL-optimal execution plan
- ✅ True batch operation (not upsert workaround)

**Cons:**
- ⚠️ Requires SQL generation (complexity, SQL injection risks)
- ⚠️ PostgREST doesn't expose UPDATE...FROM (need raw SQL or RPC function)
- ⚠️ More complex NULL handling for sparse updates
- ⚠️ Higher implementation effort

**Recommendation:** ⏳ **Future refactor** - when storage layer abstracts away Supabase specifics (e.g., adding direct PostgreSQL port for advanced operations).

---

### Option 4: Hybrid (Smart Routing)

**Route based on operation characteristics** - batch via upsert, single via update.

**Architecture:**
```python
async def _execute_update(self, operation, table_schema, context):
    has_entity_specific = any(isinstance(v, dict) for v in operation.field_updates.values())
    entity_count = self._count_target_entities(operation.target_filter)

    if has_entity_specific and entity_count > 1:
        # Batch update via upsert
        return await self._execute_batch_update_via_upsert(...)
    else:
        # Single entity or uniform update via traditional update
        return await self._execute_uniform_update(...)
```

**Pros:**
- ✅ Optimal path for each scenario
- ✅ Semantic clarity (batch = upsert, single = update)

**Cons:**
- ⚠️ Increased complexity (two code paths)
- ⚠️ Validation complexity (which path will execute?)

**Recommendation:** ⚠️ **Defer** - Option 2 handles both cases with single path (simpler, equally performant).

---

## Recommended Implementation Plan

### Phase 1: Immediate (Option 2 - UPSERT)

**Goal:** Enable batch updates for LLM-driven workflows.

**Tasks:**
1. Add `upsert_entities()` to `StorageInterface` (port)
2. Implement in `SupabaseStorageClient` (adapter)
3. Update `_execute_update()` to detect and transform entity-specific format
4. Add `_transform_to_upsert_entities()` helper
5. Update specialist prompts with batch update guidance
6. Add integration tests for batch update scenarios

**Validation Checklist:**
- ✅ Single operation updates N records with different values
- ✅ Field omission preserves existing values (sparse updates)
- ✅ Uniform updates still work (backward compatibility)
- ✅ Validation errors provide clear guidance to LLM

**Estimated Effort:** 4-6 hours (implementation + tests + prompt updates)

### Phase 2: Future (Option 3 - True Batch UPDATE)

**Trigger:** When storage layer evolves beyond Supabase (multi-database support, direct PostgreSQL port, etc.)

**Tasks:**
1. Add `batch_update_entities()` to `StorageInterface`
2. Implement UPDATE...FROM SQL generation
3. Migrate upsert-based batch updates to true UPDATE
4. Add RPC function to Supabase for UPDATE...FROM pattern

**Estimated Effort:** TBD (depends on storage layer abstraction maturity)

---

## Edge Cases & Considerations

### Sparse Updates (Different Fields Per Entity)

**Scenario:** Entity 1 updates price+stock, Entity 2 updates only price.

**UPSERT Handling:**
```python
# Entity-specific format
field_updates = {
    "price": {"uuid-1": 29.99, "uuid-2": 39.99},
    "stock": {"uuid-1": 100}  # uuid-2 omitted
}

# Transforms to
entities = [
    {"id": "uuid-1", "price": 29.99, "stock": 100},
    {"id": "uuid-2", "price": 39.99}  # Stock omitted = keeps existing value
]
```

**Result:** ✅ Field omission naturally preserves existing values.

### Concurrent Updates

**Scenario:** Two workflows update same entity simultaneously.

**Risk:** Last-write-wins (PostgreSQL default).

**Mitigation:**
- Use optimistic locking (version column) for critical fields
- Document concurrent update semantics in specialist prompts
- LangGraph checkpoints provide workflow-level isolation

### Validation vs Execution Mismatch

**Current State:** Validation checks entity-specific format, execution ignores it.

**After Implementation:** ✅ Validation and execution aligned.

### LLM Prompt Engineering

**Challenge:** LLM must learn when to use batch vs. uniform format.

**Solution:**
```xml
<update_decision_guide>
UNIFORM UPDATE (all records same values):
- Use when: Applying same change to all matching records
- Format: field_updates = {"price": 29.99, "stock": 100}
- Example: "Set all discontinued products to stock 0"

BATCH UPDATE (different values per record):
- Use when: Each record needs different values
- Format: field_updates = {"price": {"uuid-1": 29.99, "uuid-2": 39.99}}
- Example: "Update prices based on cost analysis: SKU-A to $29.99, SKU-B to $39.99"

Choose based on user request semantics, not record count.
</update_decision_guide>
```

---

## Success Metrics

**Efficiency:**
- Batch update latency: Target <100ms for 100 records (vs. N×50ms sequential)
- Transaction window: Single atomic operation (vs. N operations)

**LLM Adoption:**
- Specialist autonomously chooses batch format for appropriate scenarios
- Zero manual intervention to trigger batch updates

**Reliability:**
- Validation errors guide LLM to correct format
- Sparse updates work correctly (field omission preserves values)

---

## Open Questions

1. **Upsert semantics acceptable?** Is creating non-existent entities on "update" acceptable, or must we fail?
   - **Recommendation:** Document clearly, leverage for flexibility (e.g., "sync 100 SKUs" = upsert)

2. **Complex target filters?** How to handle `target_filter: {"category": "electronics", "is_active": true}`?
   - **Recommendation:** Require explicit IDs for batch updates; reject implicit filters (validation error guides LLM to query first, then batch update)

3. **Cross-field dependencies?** E.g., price update requires cost recalculation.
   - **Recommendation:** Delegate to specialist reasoning (calculate all values before calling tool)

4. **NULL vs. omission semantics?** `{"price": null}` vs. `{"price": omitted}`.
   - **Recommendation:** `null` = set to NULL, omission = keep existing value (PostgREST default)

---

## References

**Code Locations:**
- Validation: `agents/src/autifyme_agents/tools/universal_crud_tool.py:85-98`
- Execution: `agents/src/autifyme_agents/tools/universal_crud_tool.py:572-620`
- Storage Port: `agents/src/autifyme_agents/core/ports.py:374-394`
- Schema: `agents/src/autifyme_agents/schemas/operation_intent.py:37-43`

**External Resources:**
- PostgreSQL UPDATE...FROM: https://stackoverflow.com/questions/18797608
- Supabase Upsert Docs: https://supabase.com/docs/reference/python/upsert
- PostgREST Bulk Update Discussion: https://github.com/supabase/postgrest-js/issues/174

**Related Docs:**
- `DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md` - Operation schema design
- `PROMPT_ENGINEERING_STANDARDS.md` - Specialist prompt guidance
- `UV_REPL_BEST_PRACTICES.md` - API verification methodology
