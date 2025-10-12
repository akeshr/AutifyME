# Reset Dev

Reset development environment to clean state.

## Usage

```
/reset-dev [--confirm]
```

⚠️ **WARNING**: Destructive operation. Use only in development.

## Task

Clean slate development environment by clearing all runtime state.

### 1. Confirm Action

```bash
echo "⚠️  WARNING: This will reset your development environment"
echo ""
echo "This will clear:"
echo "  - All pending approvals"
echo "  - All checkpoints"
echo "  - All downloaded media"
echo "  - Message processing cache (on webhook restart)"
echo ""
echo "This will NOT affect:"
echo "  - Company profile"
echo "  - Saved products"
echo "  - Source code"
echo ""
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Cancelled"
    exit 0
fi
```

### 2. Clear Pending Approvals

```bash
cd agents
echo "=== Clearing Pending Approvals ==="

uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

storage = SupabaseStorageClient()

# Count before
result = storage.supabase.table('pending_approvals').select('*', count='exact').execute()
before_count = result.count

# Delete all
storage.supabase.table('pending_approvals').delete().neq('thread_id', '').execute()

print(f'✅ Cleared {before_count} pending approvals')
"
```

### 3. Clear Checkpoints

```bash
cd agents
echo "=== Clearing Checkpoints ==="

uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
import psycopg
from autifyme_agents.core.config import settings

with psycopg.connect(settings.DATABASE_URL) as conn:
    with conn.cursor() as cur:
        # Count before
        cur.execute('SELECT COUNT(*) FROM checkpoints')
        before_count = cur.fetchone()[0]

        # Delete all
        cur.execute('DELETE FROM checkpoints')
        conn.commit()

        print(f'✅ Cleared {before_count} checkpoints')
"
```

### 4. Clear Media Files

```bash
echo "=== Clearing Media Files ==="

# Count files
FILE_COUNT=$(ls -1 /tmp/media_downloads/ 2>/dev/null | wc -l)

# Clear directory
rm -rf /tmp/media_downloads/*

echo "✅ Cleared $FILE_COUNT media files"
```

### 5. Clear In-Memory Caches

```bash
echo "=== In-Memory Caches ==="

echo "⚠️  To clear in-memory caches, restart the webhook:"
echo "   1. Stop the webhook process"
echo "   2. Start it again: uv run uvicorn autifyme_agents.entrypoints.whatsapp_webhook:app --reload"
echo ""
echo "This clears:"
echo "   - Message processing cache (idempotency)"
echo "   - Thread locks"
echo "   - Cached PM states"
```

### 6. Verify Clean State

```bash
cd agents
echo "=== Verifying Clean State ==="

uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
import psycopg
from autifyme_agents.core.config import settings
import os

print('Verification:')

# Check pending approvals
storage = SupabaseStorageClient()
result = storage.supabase.table('pending_approvals').select('*', count='exact').execute()
print(f'  Pending approvals: {result.count} (expected: 0)')

# Check checkpoints
with psycopg.connect(settings.DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM checkpoints')
        count = cur.fetchone()[0]
        print(f'  Checkpoints: {count} (expected: 0)')

# Check media files
media_dir = '/tmp/media_downloads'
if os.path.exists(media_dir):
    file_count = len(os.listdir(media_dir))
    print(f'  Media files: {file_count} (expected: 0)')
else:
    print(f'  Media files: 0 (directory cleared)')

print('')
print('✅ Development environment reset complete')
"
```

### 7. Optional: Clear Test Data

```bash
echo "=== Optional: Clear Test Products ==="
echo ""
echo "⚠️  This will delete ALL products from database"
read -p "Clear test products? (yes/no): " CLEAR_PRODUCTS

if [ "$CLEAR_PRODUCTS" = "yes" ]; then
    cd agents
    uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

storage = SupabaseStorageClient()

# Count
result = storage.supabase.table('products').select('*', count='exact').execute()
before_count = result.count

# Delete all
storage.supabase.table('products').delete().neq('id', '').execute()

print(f'✅ Deleted {before_count} products')
"
else
    echo "Skipped - products preserved"
fi
```

### 8. Reset Script

Create a script for quick resets:

```bash
cd agents
cat > ../scripts/reset_dev.sh << 'EOF'
#!/bin/bash
set -e

echo "🔄 Resetting Development Environment"
echo ""

cd "$(dirname "$0")/../agents"

# Clear approvals
echo "Clearing pending approvals..."
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
storage = SupabaseStorageClient()
storage.supabase.table('pending_approvals').delete().neq('thread_id', '').execute()
"

# Clear checkpoints
echo "Clearing checkpoints..."
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
import psycopg
from autifyme_agents.core.config import settings
with psycopg.connect(settings.DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute('DELETE FROM checkpoints')
        conn.commit()
"

# Clear media
echo "Clearing media files..."
rm -rf /tmp/media_downloads/*

echo ""
echo "✅ Reset complete"
echo "⚠️  Remember to restart webhook to clear in-memory caches"
EOF

chmod +x ../scripts/reset_dev.sh
echo "✅ Reset script created: scripts/reset_dev.sh"
```

### 9. Generate Reset Report

```markdown
## Development Environment Reset

**Date**: [timestamp]
**Environment**: Development

### Cleared Components

- ✅ Pending approvals: [count] cleared
- ✅ Checkpoints: [count] cleared
- ✅ Media files: [count] cleared
- ⚠️  Message cache: Restart webhook to clear
- ⚠️  Thread locks: Restart webhook to clear

### Preserved Components

- ✅ Company profile: Unchanged
- ✅ Products: [Cleared / Preserved]
- ✅ Source code: Unchanged
- ✅ Configuration: Unchanged

### Verification

- Pending approvals: [0]
- Checkpoints: [0]
- Media files: [0]

### Status

✅ Environment reset complete

### Next Steps

1. Restart webhook to clear in-memory state
2. Test with fresh workflow
3. Verify no orphaned state

---

**Ready for clean testing**
```

## Quick Reset

For frequent resets during development:
```bash
# Create alias
alias reset-dev='cd agents && \
  uv run python -c "from dotenv import load_dotenv; load_dotenv(\"../.env\"); from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient; import psycopg; from autifyme_agents.core.config import settings; storage = SupabaseStorageClient(); storage.supabase.table(\"pending_approvals\").delete().neq(\"thread_id\", \"\").execute(); conn = psycopg.connect(settings.DATABASE_URL); cur = conn.cursor(); cur.execute(\"DELETE FROM checkpoints\"); conn.commit(); print(\"✅ Reset complete\")" && \
  rm -rf /tmp/media_downloads/* && \
  echo "⚠️  Restart webhook to complete"'
```

## Safety Notes

- ⚠️ **NEVER run in production**
- ⚠️ **Backup important test data first**
- ⚠️ **Coordinate with team if shared dev env**
- ✅ **Safe for local development**
- ✅ **Does not affect production data**

## When to Use

- Starting fresh testing session
- After major refactors
- Debugging state-related issues
- Cleaning up after failed tests
- Before demo/presentation
