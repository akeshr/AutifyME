# Check State

Inspect workflow state for debugging.

## Usage

```
/check-state [thread-id or sender]
```

If no argument, shows all pending approvals.

## Task

Inspect current workflow state across different storage systems.

### 1. Check Pending Approvals

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.workflows.orchestration.state_manager import StateManager

storage = SupabaseStorageClient()
state = StateManager(storage)

# Get specific approval
thread_id = '<thread-id>'  # Replace with actual thread_id
approval = state.get_pending_approval(thread_id)

if approval:
    print('=== Pending Approval ===')
    print(f'Thread: {thread_id}')
    print(f'Interrupt ID: {approval.get(\"interrupt_id\")}')
    print(f'Product: {approval.get(\"draft\")}')
    print(f'Media: {approval.get(\"media_path\")}')
    print(f'Agent: {approval.get(\"agent_source\")}')
    print(f'Checkpoint NS: {approval.get(\"checkpoint_ns\")}')
else:
    print(f'No pending approval for thread {thread_id}')
"
```

### 2. List All Pending Approvals

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

storage = SupabaseStorageClient()

# Query pending_approvals table
result = storage.supabase.table('pending_approvals').select('*').execute()

print(f'=== Pending Approvals ({len(result.data)}) ===')
for approval in result.data:
    print(f\"Thread: {approval['thread_id']}\")
    print(f\"  Created: {approval.get('created_at')}\")
    print(f\"  Media: {approval.get('media_path')}\")
    print(f\"  Agent: {approval.get('agent_source')}\")
    print()
"
```

### 3. Check Checkpoint State

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer

checkpointer = get_checkpointer()
thread_id = '<thread-id>'

# Get checkpoint
config = {'configurable': {'thread_id': thread_id}}
checkpoint = checkpointer.get(config)

if checkpoint:
    print('=== Checkpoint State ===')
    print(f'Thread: {thread_id}')
    print(f'Checkpoint ID: {checkpoint.get(\"id\")}')
    print(f'Parent: {checkpoint.get(\"parent_id\")}')
    print(f'Has state: {\"channel_values\" in checkpoint}')

    # Show messages if available
    if 'channel_values' in checkpoint:
        messages = checkpoint['channel_values'].get('messages', [])
        print(f'Message count: {len(messages)}')
else:
    print(f'No checkpoint found for thread {thread_id}')
"
```

### 4. Check Last PM State

```bash
# Inspect runner's last state (requires active runner)
# This is in-memory, so only available during runtime
```

### 5. Check Media Files

```bash
# List downloaded media
ls -lh /tmp/media_downloads/

# Check specific media for thread
ls -lh /tmp/media_downloads/*<thread-id>*
```

### 6. Check Thread Locks

```bash
# Thread locks are in-memory in WorkflowRunner
# Can only inspect during runtime via logging
```

### 7. Report

```markdown
## State Inspection: <thread-id>

### Pending Approval
- **Status**: [Present/Absent]
- **Interrupt ID**: [id]
- **Draft Product**: [name, price]
- **Media Path**: [path]
- **Agent Source**: [department]
- **Checkpoint NS**: [namespace]
- **Created**: [timestamp]

### Checkpoint
- **Exists**: [Yes/No]
- **Checkpoint ID**: [id]
- **Message Count**: [count]
- **Last Tool Call**: [tool name]
- **Has Interrupt**: [Yes/No]

### Media Files
- **Downloaded**: [Yes/No]
- **Path**: [path]
- **Size**: [bytes]
- **Exists**: [Yes/No]

### Issues
- [List any inconsistencies or problems]

### Recommendations
- [Suggested actions]
```

## Notes

- Requires database access (.env configured)
- Thread IDs format: `whatsapp_<phone>`
- Media files in /tmp may be cleared on reboot
- Checkpoints in PostgreSQL persist across restarts
