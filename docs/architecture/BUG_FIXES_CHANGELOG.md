# Bug Fixes Changelog

**Purpose**: Historical record of critical bugs and their resolutions

---

## 2025-10-11: GeneratorExit Exception in Traces

**Issue**: `GeneratorExit` exception appearing in every LangSmith trace during CLI testing

**Root Cause**: Breaking out of PM stream loop when interrupt detected, leaving generator unconsumed

**Location**: `workflows/orchestration/runner.py:430`

**Fix**: Continue consuming stream after capturing interrupt
```python
# Before
if "__interrupt__" in event:
    interrupt = interrupts[0]
    break  # ← Generator not fully consumed

# After
if "__interrupt__" in event:
    interrupt = interrupts[0]
    # Continue consuming to avoid GeneratorExit
```

**Impact**: All HITL workflows now complete cleanly with proper stream consumption

**Reference**: `docs/architecture/GENERATOREXIT_FIX.md`

---

## 2025-10-11: HITL Approval Flow Bug

**Issue**: Approvals not working correctly after WhatsApp caption extraction fix

**Root Cause**: Incorrect namespace isolation and Command-based resumption logic

**Location**:
- `workflows/orchestration/interrupt_coordinator.py`
- `workflows/project_manager.py`

**Fix**:
1. Department-level checkpointing with namespace `task:cataloging_department`
2. Proper Command object construction for resumption
3. State isolation between PM and Department

**Impact**: HITL approval flow works end-to-end

**Reference**: `docs/architecture/APPROVAL_FIX_SUMMARY.md`

---

## 2025-10-10: DeepAgents API Compatibility

**Issue**: DeepAgents 0.0.11rc1 has API regression incompatible with LangChain v1

**Root Cause**: Release candidate has breaking changes in `create_agent()` parameter names

**Location**: `pyproject.toml`

**Fix**: Use stable version
```toml
# Before
"deepagents==0.0.11rc1"

# After
"deepagents==0.0.11"  # Use stable, not rc1
```

**Impact**: All agent creation works correctly

**Reference**: Root `DEEPAGENTS_FIX.md` (now consolidated here)

---

## 2025-10-08: Chat History Corruption (CRITICAL)

**Issue**:
1. `ValueError: Number of human responses (2) does not match number of hanging tool calls (1)`
2. `openai.BadRequestError: An assistant message with 'tool_calls' must be followed by tool messages`

**Root Cause**: Checkpoint corruption in HITL approval flow
- User sends product info → PM invokes `save_product` → Workflow interrupts
- State saved with pending tool call
- User sends approval → Workflow resumes
- Chat history has AIMessage with tool_calls but missing ToolMessage
- OpenAI API rejects malformed message sequence

**Why it happened**:
- Incorrect resume logic in old runner
- No recovery strategy for orphaned state
- Race condition when user sends new message during approval

**Solution**: Complete architecture refactor

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

**Files Changed**:
- `whatsapp_webhook.py` - Migrated to WorkflowRunner
- `workflows/orchestration/runner.py` - Generic orchestrator
- `workflows/orchestration/recovery_strategy.py` - Error recovery
- `workflows/orchestration/state_manager.py` - State persistence
- `workflows/orchestration/interrupt_coordinator.py` - HITL handling
- `scripts/clear_corrupted_state.py` - Cleanup utility

**Prevention**:
1. **Abandonment Detection**: Clear old state if user sends new product while approval pending
2. **Auto-Recovery**: Clear checkpoint + retry once if INVALID_CHAT_HISTORY occurs
3. **State Isolation**: Approval state persisted separately from checkpoint

**Impact**: Production-stable HITL flow with graceful error handling

**Reference**: Root `CRITICAL_BUG_FIX.md` (now consolidated here)

---

## Best Practices Learned

### Stream Consumption
Always fully consume generators to prevent `GeneratorExit`:
```python
# Good
for event in stream:
    if condition:
        captured_value = event
        # Continue consuming

# Bad
for event in stream:
    if condition:
        break  # Leaves generator open
```

### Checkpoint Isolation
Use namespace isolation for department-level checkpoints:
```python
# PM level
config = {"configurable": {"thread_id": "whatsapp:123"}}

# Department level (isolated)
config = {"configurable": {"thread_id": "whatsapp:123", "checkpoint_ns": "task:cataloging_department"}}
```

### State Recovery
Always provide multiple recovery paths:
1. Proactive detection before errors
2. Reactive recovery when errors occur
3. Manual cleanup utilities for edge cases

---

**Changelog Maintained By**: Development Team
**Last Updated**: 2025-10-11
