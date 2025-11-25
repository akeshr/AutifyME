# Trace Correlation Architecture

**Status**: Implemented | **Date**: 2025-10-19

---

## Overview

Complete correlation between LangSmith traces and database records via **`trace_id = tracking_id`**.

## Implementation

**Official LangSmith Approach**: Pass `run_id` in RunnableConfig when invoking workflows.

```python
# runner.py
tracking_id = outcome_tracker.track_workflow_start(thread_id, incoming_message)

# Pass tracking_id as run_id → becomes trace_id in LangSmith
result, interrupt = self._invoke_pm(thread_id, raw_payload, run_id=tracking_id)

# No querying needed - trace_id known immediately
outcome_tracker.set_trace_id(tracking_id, tracking_id)
```

## HITL Workflow Structure

**3 Records Per HITL Execution**:

1. **Initial PM Execution**
   - Type: LangGraph workflow
   - Status: `pending_hitl`
   - Action: Cataloging request → HITL interrupt

2. **Approval Analyzer**
   - Type: `approval_analysis`
   - Status: null
   - Action: Process user approval decision

3. **Resume PM Execution**
   - Type: LangGraph workflow
   - Status: `completed`
   - Action: Command → department → specialist → completion

## Database Schema

```sql
workflow_outcomes:
  - tracking_id (UUID, UNIQUE)  -- Workflow execution ID
  - trace_id (UUID)              -- LangSmith trace ID (equals tracking_id)
  - thread_id (TEXT)             -- Conversation thread
  - result_data (JSONB)          -- Business outcome with type/status
```

## Query Patterns

**Get all phases by thread_id**:
```sql
SELECT tracking_id, trace_id, result_data->>'type' as type, result_data->>'status' as status
FROM workflow_outcomes
WHERE thread_id = 'console:local_test_...'
ORDER BY created_at
```

**Link to LangSmith trace**:
```sql
SELECT * FROM workflow_outcomes
WHERE trace_id = '<trace_id_from_langsmith>'
```

**Identify workflow type**:
```sql
-- PM workflows
WHERE result_data->>'type' IS NULL AND result_data->>'status' IN ('pending_hitl', 'completed')

-- Approval analyzer
WHERE result_data->>'type' = 'approval_analysis'
```

## Benefits

✅ **No Querying**: trace_id known immediately (no LangSmith API calls)
✅ **Guaranteed 1:1 Mapping**: tracking_id = trace_id
✅ **Complete Observability**: 3 traces per HITL workflow
✅ **Bidirectional Correlation**: DB ↔ LangSmith via trace_id

## Related Files

- `agents/src/autifyme_agents/workflows/outcome_tracker.py` - Tracking implementation
- `agents/src/autifyme_agents/workflows/orchestration/runner.py` - run_id injection
- `agents/src/autifyme_agents/workflows/approval_analyzer.py` - Approval tracking
- `.claude/skills/autonomous-testing.md` - Testing guidance
- `.claude/agents/workflow-tester.md` - Agent instructions
