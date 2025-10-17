# Batch Approval Fix Summary

**Date**: 2025-10-17
**Issue**: Multi-product batch approval only showing ONE product instead of ALL products

---

## Problems Fixed

### 1. **Batch Approval UI Issue** ✅
**Problem**: User only saw ONE product in approval request instead of ALL products
**Root Cause**: When PM made parallel delegations (2+ task() calls), runner was only showing the last interrupt
**Fix**: Accumulate ALL interrupts across stream events before displaying to user

### 2. **Edit KeyError** ✅
**Problem**: `KeyError('action')` when user tried to edit product in batch approval
**Root Cause**: HITL middleware expected `{"type": "edit", "action": "tool_name", "args": {...}}` but we were sending `{"type": "edit", "args": {...}}`
**Fix**: Include `action` field in edit responses (runner_v2.py:674-678)

### 3. **Accept TypeError** ✅
**Problem**: `TypeError: 'NoneType' object is not subscriptable` when accepting
**Root Cause**: Returning `None` for accept responses instead of `{"type": "accept"}`
**Fix**: Return proper dict format for accept (runner_v2.py:686-688)

---

## Technical Details

### Core Issue: Interrupt Collection

When PM makes parallel delegations:
```python
# PM calls task() twice in same response
task("Catalog jar...") # Creates interrupt event 1
task("Catalog mug...") # Creates interrupt event 2
```

LangGraph streams **TWO SEPARATE events**, each with 1 interrupt:
```python
Event 1: __interrupt__ = [Interrupt(value=[{jar}], id='abc')]
Event 2: __interrupt__ = [Interrupt(value=[{mug}], id='def')]
```

**Old Code** (BROKEN):
```python
for event in pm.stream(...):
    if "__interrupt__" in event:
        interrupt_value = event["__interrupt__"][0].value  # Overwrites!
# Only last interrupt kept
```

**New Code** (FIXED):
```python
accumulated_interrupts = []
for event in pm.stream(...):
    if "__interrupt__" in event:
        accumulated_interrupts.extend(event["__interrupt__"])  # Collect all!

# Flatten after stream completes
interrupt_value = []
for intr in accumulated_interrupts:
    if isinstance(intr.value, list):
        interrupt_value.extend(intr.value)  # Flatten [{jar}], [{mug}] → [{jar}, {mug}]
    else:
        interrupt_value.append(intr.value)
```

### Batch Approval Display

Created `_send_batch_approval()` method to format ALL products in single message:

```
**Batch Approval Request** (3 products)

**Product 1:**
  - Name: Storage Jar 500ml
  - Price: Rs 30.0
  - Sizes: 500ml

**Product 2:**
  - Name: Ceramic Mug 300ml
  - Price: Rs 25.0
  - Sizes: 300ml

**Product 3:**
  - Name: 10-Inch Dinner Plate
  - Price: Rs 45.0
  - Sizes: 10-inch

---

**How to respond:**
- To approve all: 'approve' or 'yes'
- To approve some: 'approve 1 and 2'
- To edit: 'edit product 3 price to 50'
- To reject all: 'reject' or 'no'
```

---

## Files Modified

### 1. `runner_v2.py`
- **Lines 576-655**: Accumulate interrupts across stream events (fixed collection bug)
- **Lines 674-698**: Fixed edit/accept response formats for HITL middleware
- **Lines 889-940**: Added `_send_batch_approval()` method for batch UI
- **Lines 783-859**: Updated `_handle_interrupt()` to use batch approval

### 2. `project_manager.prompt`
- **Lines 110-125**: Added instruction to prefer parallel delegation for multi-product requests
- **Lines 217-244**: Updated example to show parallel delegation

---

## Test Results

### ✅ Batch Approval (2 Products)
```bash
uv run python tests/cli/simulate.py "Catalog two products: jar 500ml 30rs and mug 300ml 25rs"
```
**Result**: Both products displayed in single batch approval message

### ✅ Batch Approval (3 Products)
```bash
uv run python tests/cli/simulate.py "Catalog three products: jar 500ml 30rs, mug 300ml 25rs, and plate 10inch 45rs"
```
**Result**: All 3 products displayed in single batch approval message

### ✅ Mixed Approval Scenario (To Test)
```bash
# 1. Request 3 products
uv run python tests/cli/simulate.py --hitl-mode interactive

# 2. Enter: Catalog three products: jar 500ml 30rs, mug 300ml 25rs, plate 10inch 45rs
# 3. See batch approval with all 3 products
# 4. Respond: approve 1 and 2, edit product 3 price to 50
# 5. Verify: Products 1 & 2 saved, product 3 saved with price=50
```

---

## Architecture Changes

### Before (Sequential/Partial)
```
PM → Task(jar) → Interrupt → Show jar → User approves → Resume
                                    ↓
                                PM → Task(mug) → Interrupt → Show mug → User approves → Resume
```
**Problem**: Sequential approvals, poor UX

### After (Parallel/Batch)
```
PM → Task(jar) + Task(mug) → Stream Event 1 (jar interrupt)
                           → Stream Event 2 (mug interrupt)
                           → Accumulate both
                           → Flatten to [{jar}, {mug}]
                           → Show batch approval with BOTH
                           → User approves both at once
                           → Resume with N responses for N interrupts
```
**Benefit**: Better UX, true parallel execution, batch operations

---

## Key Insights

1. **LangGraph Behavior**: Parallel tool calls create MULTIPLE stream events, not one event with multiple interrupts
2. **DeepAgents Format**: Each interrupt.value is wrapped as a list, requiring flattening
3. **HITL Middleware Contract**: Edit responses MUST include `action` field matching tool name
4. **PM Delegation Pattern**: PM needs explicit instruction to prefer parallel delegation for similar tasks

---

## HITL Middleware Format Requirements ✅

**Critical Discovery**: HITL middleware expects specific response formats:

1. **Accept**: `{"type": "accept"}`
2. **Edit**: `{"type": "edit", "args": {"action": "tool_name", "args": {merged_args}}}`
   - Note: `args` field contains an ActionRequest object with `action` and `args`
3. **Reject/Response**: `{"type": "response", "args": "rejection message"}`

**Final Fix** (runner_v2.py:708-734):
```python
if response.type == "edit":
    hitl_response = {
        "type": "edit",
        "args": {
            "action": tool_name,
            "args": merged_args  # Merge edited + original args
        }
    }
elif response.type == "accept":
    hitl_response = {"type": "accept"}
elif response.type == "response":
    hitl_response = {
        "type": "response",
        "args": response.args  # Rejection message
    }
```

---

## Test Results Summary

### ✅ Batch Approval (3 Products) - WORKS
```bash
uv run python tests/cli/simulate.py "Catalog three products: jar 500ml 30rs, mug 300ml 25rs, plate 10inch 45rs"
```
**Result**: All 3 products displayed in single batch approval message

### ✅ Auto-Approve - WORKS
Products automatically approved and saved to database

### ⚠️ Mixed Approval (Approve/Reject/Edit) - Format Fixed
**Status**: HITL middleware format requirements discovered and fixed
**Next**: Manual testing with actual user input for mixed scenarios

---

## Next Steps

1. ✅ HITL middleware format requirements - COMPLETE
2. Test mixed approval scenario manually (approve 1, reject 2, edit 3)
3. Add test coverage for mixed approval scenarios
4. Update documentation for batch approval UX patterns
