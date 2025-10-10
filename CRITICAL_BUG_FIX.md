# Critical Bug Fix - Chat History Corruption

**Date**: 2025-10-08
**Status**: ✅ FIXED

---

## Errors

1. `ValueError: Number of human responses (2) does not match number of hanging tool calls (1)`
2. `openai.BadRequestError: An assistant message with 'tool_calls' must be followed by tool messages`

---

## Root Cause

**Checkpoint corruption in HITL approval flow:**

1. User sends product info → PM invokes `save_product` → Workflow interrupts
2. State saved with pending tool call
3. User sends approval → Workflow resumes
4. **BUG**: Chat history has AIMessage with tool_calls but missing ToolMessage
5. OpenAI API rejects malformed message sequence

**Why it happens:**
- Incorrect resume logic in old runner
- No recovery strategy for orphaned state
- Race condition when user sends new message during approval

---

## Solution

**Refactored architecture** (already deployed in codebase):

### 1. RecoveryStrategy
- **Proactive**: Detects abandonment before errors occur
- **Reactive**: Auto-recovers from INVALID_CHAT_HISTORY errors
- Clears both checkpoint and approval state

### 2. StateManager
- Persists approval state separately from checkpoint
- Enables clean restart after corruption

### 3. InterruptCoordinator
- Proper resume logic with Command API
- Validates tool call structure before resuming

---

## Immediate Fix

### For Affected User (917258067800)

```bash
cd agents
uv run python scripts/clear_corrupted_state.py --phone 917258067800
```

### Restart Server

```bash
# Stop current server (Ctrl+C)
# Restart with refactored architecture
cd agents
uv run uvicorn autifyme_agents.entrypoints.whatsapp_webhook:app --reload --port 8000
```

**Verify**: Server logs should show:
```
AUTIFYME WHATSAPP WEBHOOK STARTING (REFACTORED ARCHITECTURE)
✅ WorkflowRunner initialized successfully
```

---

## Prevention

New architecture prevents this via:

1. **Abandonment Detection**
   - If user sends NEW product while approval pending → clear old state
   - Fresh start instead of corruption

2. **Auto-Recovery**
   - If INVALID_CHAT_HISTORY error occurs → clear checkpoint + retry once
   - Graceful degradation

3. **State Isolation**
   - Approval state persisted separately
   - Checkpoint can be cleared without losing approval context

---

## Files Changed

- ✅ `whatsapp_webhook.py` - Migrated to WorkflowRunner
- ✅ `workflows/orchestration/runner.py` - Generic orchestrator
- ✅ `workflows/orchestration/recovery_strategy.py` - Error recovery
- ✅ `workflows/orchestration/state_manager.py` - State persistence
- ✅ `workflows/orchestration/interrupt_coordinator.py` - HITL handling
- ✅ `scripts/clear_corrupted_state.py` - Cleanup utility

---

## Next Steps

1. **Immediate**: Run cleanup script for affected user
2. **Validation**: Test full approval flow in Codespace
3. **Monitoring**: Watch for similar errors in logs
4. **Cleanup**: Delete `whatsapp_cataloging_runner.py` after 1-2 days validation
