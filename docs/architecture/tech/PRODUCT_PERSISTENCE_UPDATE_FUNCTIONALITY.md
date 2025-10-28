# Product Persistence UPDATE Functionality

**Status**: ✅ Implemented
**Date**: 2025-01-28
**Files Modified**: `product_persistence_tools.py`

---

## Problem

Users experienced duplicate key errors when attempting to catalog the same product multiple times. The system only supported CREATE operations, not UPDATE operations for existing product families.

**User Feedback**: _"users can request to update as well right any attributes of the product all tables"_

---

## Solution

Implemented intelligent UPSERT logic that automatically detects whether to CREATE or UPDATE based on `product_group_id` existence.

### Operation Types

1. **CREATE** - New product family (`product_group_id` doesn't exist)
2. **UPDATE** - Existing product family (merges changes into existing data)
3. **ADD_VARIANT** - Add variants to existing family (via `match_recommendation`)

---

## Implementation Details

### Step-by-Step Logic

| Step | Table | CREATE | UPDATE | ADD_VARIANT |
|------|-------|--------|--------|-------------|
| 1 | `product_families` | INSERT | UPDATE | Skip (use existing) |
| 2 | `variant_axes` | INSERT all | MERGE (update existing, insert new) | Use existing |
| 3 | `variant_values` | INSERT all | MERGE (update existing, insert new) | INSERT new only |
| 4 | `products` | INSERT all | MERGE (update existing SKUs, insert new) | INSERT new only |
| 5 | `product_variant_values` | INSERT all | DELETE per product + INSERT | INSERT new only |
| 6 | `product_family_industries` | INSERT all | DELETE all + INSERT all | INSERT new only |
| 7 | `customer_segments` | INSERT all | DELETE all + INSERT all | INSERT new only |
| 8 | `product_images` | INSERT all | DELETE all + INSERT all | INSERT new only |
| 9 | `marketing_content` | INSERT all | DELETE all + INSERT all | INSERT new only |

### Existence Check

```python
# Before any operations
existing_check = client.table("product_families")
    .select("id")
    .eq("product_group_id", product_family.product_group_id)
    .execute()

if existing_check.data:
    operation_type = "update"
    family_id = UUID(existing_check.data[0]["id"])
else:
    operation_type = "create"
```

### Merge Strategy

**Core Tables (variant_axes, variant_values, products):**
- Load existing records
- For each input record:
  - If exists → UPDATE
  - If doesn't exist → INSERT

**Supporting Tables (industries, segments, images, content):**
- DELETE all existing records
- INSERT all new records
- Simpler than diff logic, acceptable for supporting data

---

## API Changes

### PersistenceResult Enhancement

```python
class PersistenceResult(BaseModel):
    success: bool
    operation: str | None  # NEW: "create", "update", or "add_variant"
    product_family_id: UUID | None
    # ... existing fields
```

### Logging Enhancement

```python
# Before
logger.info("Product family persistence completed successfully", ...)

# After
logger.info(f"Product family {operation_type.upper()} completed successfully",
    extra={"operation": operation_type, ...})
```

---

## Testing

**Test Scenario**: Catalog PET Bottles multiple times
- **First run**: Creates new product family
- **Second run**: Updates existing product family (no duplicate key error)

**Expected Results**:
- ✅ No duplicate key violations
- ✅ `operation="update"` returned in PersistenceResult
- ✅ Existing data preserved, new changes merged
- ✅ Database triggers fire for audit trail

---

## Benefits

1. **User Experience**: Natural workflow - users can repeatedly refine product data
2. **Error Resilience**: No more duplicate key errors from repeated requests
3. **Data Integrity**: Merge logic preserves existing relationships
4. **Audit Trail**: Database triggers capture all UPDATE operations
5. **Transparency**: Clear operation type returned to caller

---

## Migration Path

**Backward Compatibility**: ✅ Fully backward compatible
- Existing CREATE-only code paths continue to work
- UPDATE automatically triggers when `product_group_id` exists
- No changes required to calling code

---

## Related Docs

- [Product Persistence Architecture](./PRODUCT_PERSISTENCE_DESIGN.md) _(if exists)_
- [Database Schema](../../database/schema/) _(if exists)_
- [SPECIALIST_BUILD_UP_PLAN.md](../workflows/SPECIALIST_BUILD_UP_PLAN.md)

---

## Future Enhancements

**Potential Improvements:**
1. **Selective DELETE** for supporting tables (diff logic instead of DELETE all)
2. **Conflict Resolution** for concurrent updates (optimistic locking)
3. **Partial UPDATE** capability (update specific fields only)
4. **DELETE Operations** (soft delete vs hard delete)
5. **Version History** (track changes over time)

---

## Commit Reference

**Commit**: _(to be added after commit)_

**Files Changed**:
- `agents/src/autifyme_agents/tools/product_persistence_tools.py`

**Lines of Code**: ~250 lines modified/added
