# Batch Approval Order Mismatch Issue

**Date**: 2025-10-17
**Status**: ❌ CRITICAL BUG FOUND
**Priority**: P0 - Blocks mixed approval scenarios

---

## Problem

Mixed batch approval is broken due to **order mismatch** between display and resume phases.

### Test Case
User requests: "Catalog three products: jar 500ml 30rs, mug 300ml 25rs, plate 10inch 45rs"

**Display Phase** (_handle_interrupt):
```
Product 1: Ceramic Mug 300ml - Rs 25
Product 2: 500ml Storage Jar - Rs 30
Product 3: 10-Inch Dinner Plate - Rs 45
```

User responds: `"approve 1, reject 2, edit 3 price to 50"`

**Expected Outcome**:
- Product 1 (Mug): APPROVED at 25
- Product 2 (Jar): REJECTED
- Product 3 (Plate): EDITED to 50

**Actual Outcome** (from database):
- 500ml Storage Jar: SAVED at 30 (should be rejected)
- 10-Inch Dinner Plate: SAVED at 50 (correct)
- Ceramic Mug: NOT SAVED (should be approved)

---

## Root Cause

### Display Order (_handle_interrupt, runner_v2.py:798-821)
When PM creates interrupt, runner iterates through `interrupt_value` list:

```python
for idx, action in enumerate(interrupt_value):
    # Extract product and display
    products_to_approve.append(draft)
```

Display order determined by: **Order of actions in interrupt_value list**

### Resume Order (_invoke_pm, runner_v2.py:354-390)
When resuming, runner extracts interrupts from checkpoint:

```python
for base_idx, interrupt_obj in enumerate(state_snapshot.interrupts):
    interrupt_value = interrupt_obj.value
    if isinstance(interrupt_value, list):
        for action_idx, action in enumerate(interrupt_value):
            pending_interrupts_list.append(interrupt_info)
```

Resume order determined by: **Order of actions extracted from checkpoint state**

### The Mismatch
The order of products in `interrupt_value` during display phase **does NOT match** the order when extracting from checkpoint during resume phase.

This causes:
- "Product 1" in display != interrupt index 0 in resume
- approval_analyzer gets correct context but responses misalign
- Wrong products approved/rejected/edited

---

## Evidence

### Test Run (2025-10-17 10:15:02)

**Display** (from console output):
```
Product 1: Ceramic Mug 300ml (25rs)
Product 2: 500ml Storage Jar (30rs)
Product 3: 10-Inch Dinner Plate (45rs)
```

**User Input**: `"approve 1, reject 2, edit 3 price to 50"`

**Database Results**:
```sql
SELECT name, price FROM products WHERE created_at > NOW() - INTERVAL '2 minutes';

| name                    | price |
|------------------------|-------|
| 10-Inch Dinner Plate   | 50.0  |
| 500ml Storage Jar      | 30.0  |
```

Mug NOT saved (should be Product 1 - approved).
Jar saved (should be Product 2 - rejected).
Plate saved at 50 (should be Product 3 - edited) ✓

---

## Impact

**Severity**: CRITICAL - Batch approval completely broken for mixed scenarios

**User Experience**: Dangerous - user thinks they approved/rejected specific products, but system acts on different products

**Business Risk**: HIGH - Could catalog wrong products, reject correct ones, or apply edits to wrong items

---

## Solution Options

### Option 1: Ensure Consistent Ordering (Recommended)
Force same iteration order in both phases:
- Use deterministic sorting when building interrupt_value list
- Use same sorting when extracting from checkpoint
- Options: sort by product name, creation time, or interrupt ID

**Pros**: Guarantees consistency, minimal changes
**Cons**: Requires understanding LangGraph checkpoint internals

### Option 2: Include Product Metadata in Display
Add product IDs/interrupt IDs to batch approval message:
```
Product 1 [ID: int_0_0]: Ceramic Mug
Product 2 [ID: int_0_1]: Storage Jar
```

Then match by ID instead of position during resume.

**Pros**: Explicit mapping, no ordering dependency
**Cons**: Exposes internal IDs to user, more complex approval_analyzer

### Option 3: Single-Pass Architecture
Display products, get approval, and execute immediately without checkpoint resume.

**Pros**: No ordering issues
**Cons**: Requires rearchitecture of HITL flow, loses LangGraph checkpoint benefits

---

## Recommended Fix

**Option 1 with explicit logging**:

1. **Add sort key to interrupt extraction** (runner_v2.py:369-390):
   ```python
   # Sort actions by product name for deterministic order
   if isinstance(interrupt_value, list):
       sorted_actions = sorted(interrupt_value, key=lambda a: a.get("action_request", {}).get("args", {}).get("name", ""))
       for action_idx, action in enumerate(sorted_actions):
           # ... extract ...
   ```

2. **Add same sort to display** (runner_v2.py:801-821):
   ```python
   # Sort actions by product name (must match resume order)
   sorted_interrupt_value = sorted(interrupt_value, key=lambda a: a.get("action_request", {}).get("args", {}).get("name", ""))
   for idx, action in enumerate(sorted_interrupt_value):
       # ... display ...
   ```

3. **Add validation logs**:
   - Log product order during display
   - Log interrupt order during resume
   - Assert they match before building Command

---

## Next Steps

1. Verify root cause with [DISPLAY ORDER] / [RESUME ORDER] logs added to runner_v2.py
2. Implement sort-based fix (Option 1)
3. Add test case for 3-product mixed approval
4. Verify database saves match user intent
5. Update BATCH_APPROVAL_FIX_SUMMARY.md with order fix

---

## Test Commands

```bash
# Run mixed approval test
uv run python tests/cli/simulate.py "Catalog three products: jar 500ml 30rs, mug 300ml 25rs, plate 10inch 45rs" --hitl-mode mixed

# Verify database
SELECT name, price FROM products WHERE created_at > NOW() - INTERVAL '5 minutes' ORDER BY created_at DESC;
```

**Expected after fix**:
- Ceramic Mug 300ml: SAVED at 25
- 500ml Storage Jar: NOT SAVED (rejected)
- 10-Inch Dinner Plate: SAVED at 50 (edited)
