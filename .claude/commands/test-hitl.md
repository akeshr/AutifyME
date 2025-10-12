# Test HITL

Test Human-in-the-Loop approval flows end-to-end.

## Usage

```
/test-hitl [flow]
```

**Flows**: `approve`, `reject`, `edit`, `timeout`, `nested`, `all`

## Task

Test HITL (Human-in-the-Loop) approval workflows to ensure proper interrupt/resume behavior.

### 1. Test Interrupt Triggering

```bash
cd agents
# Start workflow that should trigger HITL
uv run python scripts/simulate.py \
  --text "Catalog test product, $99" \
  --image /tmp/test.jpg \
  --hitl
```

**Verify**:
- Interrupt triggered before save_product
- Approval request generated correctly
- State persisted to storage
- Media file preserved at download path

### 2. Test Approval Flow

```bash
# Get thread_id from previous output
uv run python scripts/simulate.py --approve <thread-id>
```

**Verify**:
- Workflow resumes at PM level (not department)
- save_product executes after approval
- Product saved to database
- Success message generated
- No GeneratorExit errors

### 3. Test Rejection Flow

```bash
# Start new workflow
uv run python scripts/simulate.py --text "Test reject" --image /tmp/test.jpg --hitl

# Reject it
uv run python scripts/simulate.py --reject <thread-id>
```

**Verify**:
- Workflow terminates gracefully
- No product saved
- State cleaned up
- Friendly rejection message

### 4. Test Edit Flow (if supported)

```bash
# Approve with edits
uv run python scripts/simulate.py \
  --approve <thread-id> \
  --edit '{"price": 89.99, "name": "Updated Name"}'
```

**Verify**:
- Edits applied before save
- Product saved with updated values

### 5. Test Edge Cases

**Nested Interrupts**:
```python
# Check if multiple approvals in sequence cause issues
```

**Timeout Handling**:
```python
# Verify approval state expires/cleans up if no response
```

**Concurrent Approvals**:
```python
# Test thread-safety with multiple pending approvals
```

### 6. Inspect State

```bash
# Check pending approvals
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.workflows.orchestration.state_manager import StateManager

storage = SupabaseStorageClient()
state = StateManager(storage)
approval = state.get_pending_approval('<thread-id>')
print(approval)
"
```

### 7. Check Interrupt Coordinator

Read and verify:
- `agents/src/autifyme_agents/workflows/orchestration/interrupt_coordinator.py`
- `resume_workflow()` uses pm_factory (not fresh department)
- Command.resume format correct: `{"interrupt_id": {"type": "accept"}}`
- Stream fully consumed to avoid GeneratorExit

### 8. Report

```markdown
## HITL Test Results

### Interrupt Triggering
- ✅/❌ Interrupt triggered at correct point
- ✅/❌ State persisted correctly
- ✅/❌ Approval request formatted properly

### Approval Flow
- ✅/❌ Resume at PM level
- ✅/❌ Tool executed after approval
- ✅/❌ No GeneratorExit errors
- ✅/❌ Product saved successfully

### Rejection Flow
- ✅/❌ Workflow terminated gracefully
- ✅/❌ State cleaned up
- ✅/❌ No orphaned approvals

### Edge Cases
- ✅/❌ Nested interrupts handled
- ✅/❌ Timeout behavior correct
- ✅/❌ Concurrent approvals safe

**Issues Found**: [list]
**Recommendations**: [fixes needed]
```
