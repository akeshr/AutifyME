# Clear State

Clean up orphaned workflow state.

## Usage

```
/clear-state [thread-id or "all"]
```

**Options**: specific thread-id, `all`, `orphaned`, `old`

## Task

Clear workflow state to resolve stuck workflows or clean up after testing.

### 1. Clear Specific Thread

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.workflows.orchestration.state_manager import StateManager
from autifyme_agents.workflows.orchestration.recovery_strategy import RecoveryStrategy
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer

storage = SupabaseStorageClient()
state = StateManager(storage)
recovery = RecoveryStrategy(
    state_manager=state,
    checkpointer_factory=get_checkpointer
)

thread_id = '<thread-id>'
print(f'Clearing state for thread: {thread_id}')

# Clear using recovery strategy
recovery.clear_orphaned_state(thread_id)

print('✅ State cleared successfully')
"
```

### 2. Clear All Pending Approvals

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

storage = SupabaseStorageClient()

# Get all pending approvals
result = storage.supabase.table('pending_approvals').select('thread_id').execute()
thread_ids = [r['thread_id'] for r in result.data]

print(f'Found {len(thread_ids)} pending approvals')

# Delete all
for thread_id in thread_ids:
    storage.supabase.table('pending_approvals').delete().eq('thread_id', thread_id).execute()
    print(f'✅ Cleared: {thread_id}')

print(f'✅ Cleared {len(thread_ids)} pending approvals')
"
```

### 3. Clear Old Approvals (>24h)

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

storage = SupabaseStorageClient()

# Get approvals older than 24h
cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
result = storage.supabase.table('pending_approvals') \
    .select('thread_id, created_at') \
    .lt('created_at', cutoff) \
    .execute()

print(f'Found {len(result.data)} old approvals')

for approval in result.data:
    thread_id = approval['thread_id']
    storage.supabase.table('pending_approvals').delete().eq('thread_id', thread_id).execute()
    print(f'✅ Cleared old approval: {thread_id} (created: {approval[\"created_at\"]})')
"
```

### 4. Clear Checkpoints

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer

checkpointer = get_checkpointer()
thread_id = '<thread-id>'

# Clear checkpoint
config = {'configurable': {'thread_id': thread_id}}

# Note: PostgresSaver doesn't have delete method
# Need to connect directly to PostgreSQL
import psycopg
from autifyme_agents.core.config import settings

with psycopg.connect(settings.DATABASE_URL) as conn:
    with conn.cursor() as cur:
        # Delete from checkpoints table
        cur.execute(
            'DELETE FROM checkpoints WHERE thread_id = %s',
            (thread_id,)
        )
        deleted = cur.rowcount
        conn.commit()
        print(f'✅ Deleted {deleted} checkpoints for thread: {thread_id}')
"
```

### 5. Clear Media Files

```bash
# Clear all downloaded media
rm -rf /tmp/media_downloads/*
echo "✅ Cleared all media files"

# Clear specific thread media
rm -f /tmp/media_downloads/*<thread-id>*
echo "✅ Cleared media for thread"
```

### 6. Clear Message Cache (Webhook Idempotency)

```bash
# This is in-memory in webhook, clears on restart
# No persistent storage to clear
echo "⚠️  Message cache is in-memory, restart webhook to clear"
```

### 7. Full Reset (Development Only)

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
import psycopg
from autifyme_agents.core.config import settings
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

print('⚠️  WARNING: Full state reset - development only!')
print('This will clear:')
print('  - All pending approvals')
print('  - All checkpoints')
print('  - All media files')
print()
response = input('Continue? (yes/no): ')

if response.lower() == 'yes':
    # Clear pending approvals
    storage = SupabaseStorageClient()
    result = storage.supabase.table('pending_approvals').delete().neq('thread_id', '').execute()
    print(f'✅ Cleared pending approvals')

    # Clear checkpoints
    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM checkpoints')
            conn.commit()
            print(f'✅ Cleared all checkpoints')

    # Clear media (run separately)
    print('⚠️  Run: rm -rf /tmp/media_downloads/*')

    print('✅ Full reset complete')
else:
    print('❌ Cancelled')
"
```

### 8. Report

```markdown
## State Cleared

**Thread ID**: [thread-id or "all"]

### Cleared Components
- ✅ Pending approvals: [count]
- ✅ Checkpoints: [count]
- ✅ Media files: [count]
- ✅ Thread locks: [cleared on restart]

### Verification
- Pending approvals: [0 remaining]
- Checkpoint exists: [No]
- Media files: [Deleted]

**Status**: Ready for fresh workflow
```

## Warning

- ⚠️ **Irreversible**: State cannot be recovered after clearing
- ⚠️ **Production**: Use extreme caution in production
- ⚠️ **Active workflows**: May break workflows in progress
- ✅ **Development**: Safe for testing/development

## Notes

- Always backup before clearing production state
- Clear state when workflows are stuck
- Use recovery strategy for automatic cleanup
- Media files in /tmp are temporary anyway
