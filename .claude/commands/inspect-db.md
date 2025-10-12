# Inspect Database

Quick database queries for debugging.

## Usage

```
/inspect-db [query-type]
```

**Types**: `approvals`, `products`, `profile`, `checkpoints`, `stats`, `recent`

## Task

Run common database queries to inspect system state.

### 1. Pending Approvals

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

storage = SupabaseStorageClient()

result = storage.supabase.table('pending_approvals').select('*').execute()

print(f'=== Pending Approvals ({len(result.data)}) ===')
for approval in result.data:
    print(f\"Thread: {approval['thread_id']}\")
    print(f\"  Created: {approval.get('created_at')}\")
    print(f\"  Draft: {approval.get('approval_data', {}).get('draft', {}).get('name')}\")
    print(f\"  Media: {approval.get('media_path', 'None')}\")
    print()
"
```

### 2. Recent Products

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

storage = SupabaseStorageClient()

# Get last 10 products
result = storage.supabase.table('products') \
    .select('*') \
    .order('created_at', desc=True) \
    .limit(10) \
    .execute()

print(f'=== Recent Products ({len(result.data)}) ===')
for product in result.data:
    print(f\"ID: {product['id']}\")
    print(f\"  Name: {product['name']}\")
    print(f\"  Price: {product.get('price', 'N/A')}\")
    print(f\"  Created: {product['created_at']}\")
    print()
"
```

### 3. Company Profile

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

storage = SupabaseStorageClient()
profile = storage.get_company_profile()

print('=== Company Profile ===')
print(f'Name: {profile.name}')
print(f'Brand Voice: {profile.brand_voice[:100]}...')
print(f'Target Audience: {profile.target_audience[:100]}...')
print(f'Catalog Guidelines: {profile.catalog_guidelines[:100]}...')
"
```

### 4. Checkpoint Statistics

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
import psycopg
from autifyme_agents.core.config import settings

with psycopg.connect(settings.DATABASE_URL) as conn:
    with conn.cursor() as cur:
        # Count checkpoints
        cur.execute('SELECT COUNT(*) FROM checkpoints')
        total = cur.fetchone()[0]

        # Count by thread
        cur.execute('SELECT thread_id, COUNT(*) as count FROM checkpoints GROUP BY thread_id ORDER BY count DESC LIMIT 10')
        by_thread = cur.fetchall()

        print(f'=== Checkpoint Statistics ===')
        print(f'Total checkpoints: {total}')
        print()
        print('Top threads by checkpoint count:')
        for thread_id, count in by_thread:
            print(f'  {thread_id}: {count}')
"
```

### 5. Database Health

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
import psycopg
from autifyme_agents.core.config import settings

print('=== Database Health Check ===')

# Test Supabase
try:
    storage = SupabaseStorageClient()
    result = storage.supabase.table('company_profiles').select('count', count='exact').execute()
    print(f'✅ Supabase: Connected (profiles: {result.count})')
except Exception as e:
    print(f'❌ Supabase: {str(e)[:100]}')

# Test PostgreSQL
try:
    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM checkpoints')
            count = cur.fetchone()[0]
            print(f'✅ PostgreSQL: Connected (checkpoints: {count})')
except Exception as e:
    print(f'❌ PostgreSQL: {str(e)[:100]}')
"
```

### 6. Product Statistics

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

storage = SupabaseStorageClient()

# Count products
result = storage.supabase.table('products').select('*', count='exact').execute()
total = result.count

# Products with images
result_images = storage.supabase.table('products').select('*', count='exact').not_.is_('image_urls', 'null').execute()
with_images = result_images.count

# Products with prices
result_prices = storage.supabase.table('products').select('*', count='exact').not_.is_('price', 'null').execute()
with_prices = result_prices.count

print('=== Product Statistics ===')
print(f'Total products: {total}')
print(f'With images: {with_images} ({100*with_images//total if total > 0 else 0}%)')
print(f'With prices: {with_prices} ({100*with_prices//total if total > 0 else 0}%)')
"
```

### 7. Recent Workflow Activity

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv('../.env')
import psycopg
from autifyme_agents.core.config import settings

cutoff = (datetime.now() - timedelta(hours=24)).isoformat()

with psycopg.connect(settings.DATABASE_URL) as conn:
    with conn.cursor() as cur:
        # Recent checkpoints (proxy for activity)
        cur.execute('''
            SELECT thread_id, MAX(checkpoint_id) as latest, COUNT(*) as checkpoint_count
            FROM checkpoints
            WHERE parent_id IS NOT NULL
            GROUP BY thread_id
            ORDER BY latest DESC
            LIMIT 10
        ''')
        recent = cur.fetchall()

        print('=== Recent Workflow Activity ===')
        for thread_id, latest, count in recent:
            print(f'{thread_id}:')
            print(f'  Checkpoints: {count}')
            print()
"
```

### 8. Report

```markdown
## Database Inspection

### Connection Status
- Supabase: ✅/❌ [Connected/Error]
- PostgreSQL: ✅/❌ [Connected/Error]

### Pending Approvals
- Count: [number]
- Oldest: [timestamp]
- Threads: [list of thread_ids]

### Products
- Total: [count]
- With images: [count] ([percent]%)
- With prices: [count] ([percent]%)
- Recent (24h): [count]

### Checkpoints
- Total: [count]
- Active threads: [count]
- Most active: [thread_id] ([checkpoint_count] checkpoints)

### Company Profile
- Name: [name]
- Brand voice: [preview]
- Target audience: [preview]

### Issues
- [List any anomalies or problems]
```

## Notes

- Requires .env with database credentials
- Supabase for company profile and products
- PostgreSQL for LangGraph checkpoints
- Large result sets may take time
