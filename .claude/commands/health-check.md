# Health Check

System health and connectivity check.

## Usage

```
/health-check
```

## Task

Verify all system components are healthy and accessible.

### 1. Check Database Connections

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')

print('=== Database Health Check ===')

# Supabase
try:
    from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
    storage = SupabaseStorageClient()

    # Test read
    profile = storage.get_company_profile()

    # Test table access
    result = storage.supabase.table('products').select('id').limit(1).execute()

    print('✅ Supabase: Connected and responsive')
    print(f'   Company: {profile.name}')
    print(f'   Products table: Accessible')
except Exception as e:
    print(f'❌ Supabase: {str(e)[:150]}')

# PostgreSQL
try:
    from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
    import psycopg
    from autifyme_agents.core.config import settings

    # Test checkpointer
    checkpointer = get_checkpointer()

    # Test direct connection
    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM checkpoints')
            count = cur.fetchone()[0]

    print('✅ PostgreSQL: Connected and responsive')
    print(f'   Checkpoints: {count}')
except Exception as e:
    print(f'❌ PostgreSQL: {str(e)[:150]}')
"
```

### 2. Check API Services

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')

print('=== API Services Health Check ===')

# OpenAI
try:
    from openai import OpenAI
    client = OpenAI()

    # Test with minimal request
    response = client.chat.completions.create(
        model='gpt-5-mini-2025-08-07',
        messages=[{'role': 'user', 'content': 'test'}],
        max_tokens=5
    )

    print('✅ OpenAI: Accessible and responsive')
except Exception as e:
    print(f'❌ OpenAI: {str(e)[:150]}')

# LangSmith
try:
    from langsmith import Client
    client = Client()

    # Test with minimal query
    runs = list(client.list_runs(limit=1))

    print('✅ LangSmith: Accessible and responsive')
except Exception as e:
    print(f'⚠️  LangSmith: {str(e)[:150]}')
    print('   (Non-critical - tracing will be unavailable)')
"
```

### 3. Check WhatsApp Integration

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.core.config import settings

print('=== WhatsApp Integration Health Check ===')

# Check configuration
required_vars = [
    'WHATSAPP_PHONE_NUMBER_ID',
    'WHATSAPP_ACCESS_TOKEN',
    'WHATSAPP_WEBHOOK_VERIFY_TOKEN',
]

all_set = True
for var in required_vars:
    value = getattr(settings, var, None)
    if not value:
        print(f'❌ {var}: Not set')
        all_set = False
    else:
        # Show masked value
        masked = value[:4] + '...' + value[-4:] if len(value) > 8 else '***'
        print(f'✅ {var}: {masked}')

if all_set:
    print('✅ WhatsApp: Configuration complete')

    # Test client initialization
    try:
        from autifyme_agents.integrations.communication.whatsapp_client import WhatsAppClient
        client = WhatsAppClient()
        print('✅ WhatsApp: Client initialized')
    except Exception as e:
        print(f'⚠️  WhatsApp: Client error: {str(e)[:100]}')
else:
    print('❌ WhatsApp: Incomplete configuration')
"
```

### 4. Check LLM Configuration

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')

print('=== LLM Configuration Health Check ===')

try:
    from autifyme_agents.core.llm_factory import get_llm

    # Test default LLM
    llm = get_llm()
    print(f'✅ Default LLM: {llm.model_name if hasattr(llm, \"model_name\") else \"configured\"}')

    # Test vision LLM
    vision_llm = get_llm(provider='openai', model='gpt-5-mini-2025-08-07')
    print(f'✅ Vision LLM: {vision_llm.model_name if hasattr(vision_llm, \"model_name\") else \"gpt-5-mini-2025-08-07\"}')

except Exception as e:
    print(f'❌ LLM Configuration: {str(e)[:150]}')
"
```

### 5. Check Workflow Components

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')

print('=== Workflow Components Health Check ===')

# Check PM creation
try:
    from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
    from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
    from autifyme_agents.workflows.project_manager import create_project_manager

    storage = SupabaseStorageClient()
    profile = storage.get_company_profile()
    checkpointer = get_checkpointer()

    pm = create_project_manager(
        company_profile=profile,
        checkpointer=checkpointer,
        storage=storage
    )

    print('✅ Project Manager: Initialized successfully')
except Exception as e:
    print(f'❌ Project Manager: {str(e)[:150]}')

# Check department creation
try:
    from autifyme_agents.departments.cataloging_department import create_cataloging_department

    dept = create_cataloging_department(
        checkpointer=checkpointer,
        storage=storage
    )

    print('✅ Cataloging Department: Initialized successfully')
except Exception as e:
    print(f'❌ Cataloging Department: {str(e)[:150]}')

# Check specialists
try:
    from autifyme_agents.specialists.image_analysis_specialist import create_image_analysis_specialist
    from autifyme_agents.specialists.cataloging_specialist import create_cataloging_specialist

    image_spec = create_image_analysis_specialist()
    cat_spec = create_cataloging_specialist()

    print('✅ Specialists: Initialized successfully')
except Exception as e:
    print(f'❌ Specialists: {str(e)[:150]}')
"
```

### 6. Check Storage Health

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')

print('=== Storage Health Check ===')

# Check pending approvals
try:
    from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
    from autifyme_agents.workflows.orchestration.state_manager import StateManager

    storage = SupabaseStorageClient()
    state = StateManager(storage)

    # Count pending approvals
    result = storage.supabase.table('pending_approvals').select('*', count='exact').execute()
    count = result.count

    print(f'✅ Pending Approvals: {count} active')

    if count > 10:
        print(f'   ⚠️  High number of pending approvals - review and clear old ones')

except Exception as e:
    print(f'❌ State Manager: {str(e)[:150]}')

# Check checkpoint storage
try:
    import psycopg
    from autifyme_agents.core.config import settings

    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM checkpoints')
            checkpoint_count = cur.fetchone()[0]

    print(f'✅ Checkpoints: {checkpoint_count} stored')

    if checkpoint_count > 10000:
        print(f'   ⚠️  High checkpoint count - consider cleanup')

except Exception as e:
    print(f'❌ Checkpoint Storage: {str(e)[:150]}')
"
```

### 7. Check Media Storage

```bash
echo "=== Media Storage Health Check ==="

# Check media directory
if [ -d "/tmp/media_downloads" ]; then
    FILE_COUNT=$(ls -1 /tmp/media_downloads/ 2>/dev/null | wc -l)
    DISK_USAGE=$(du -sh /tmp/media_downloads/ 2>/dev/null | cut -f1)

    echo "✅ Media Directory: Exists"
    echo "   Files: $FILE_COUNT"
    echo "   Disk usage: $DISK_USAGE"

    if [ "$FILE_COUNT" -gt 100 ]; then
        echo "   ⚠️  High file count - consider cleanup"
    fi
else
    echo "⚠️  Media Directory: Not found (will be created on first use)"
fi
```

### 8. Check System Resources

```bash
echo "=== System Resources Health Check ==="

# Memory usage (works on macOS and Linux)
if command -v free &> /dev/null; then
    free -h
elif command -v vm_stat &> /dev/null; then
    vm_stat
fi

# Disk space
echo "Disk usage:"
df -h | grep -E "Filesystem|/$"

# Check /tmp space
echo ""
echo "/tmp space:"
df -h /tmp | tail -1
```

### 9. Generate Health Report

```markdown
## System Health Report

**Generated**: [timestamp]

### 🟢 Healthy Components

#### Databases
- ✅ Supabase: Connected (company: [name])
- ✅ PostgreSQL: Connected (checkpoints: [count])

#### APIs
- ✅ OpenAI: Accessible
- ✅ LangSmith: Accessible

#### Integrations
- ✅ WhatsApp: Configured
- ✅ LLM Factory: Working

#### Workflows
- ✅ Project Manager: Initialized
- ✅ Cataloging Department: Initialized
- ✅ Specialists: Initialized

### ⚠️  Warnings

- [Component]: [Issue - non-critical]

### ❌ Critical Issues

- [Component]: [Issue - requires immediate attention]

### 📊 Statistics

- Pending approvals: [count]
- Checkpoints stored: [count]
- Media files: [count] ([size])
- Disk usage: [percentage]%

### 🔧 Recommendations

- [Action item if needed]

---

**Overall Status**: 🟢 Healthy / ⚠️  Degraded / ❌ Critical

**Action Required**: [Yes/No]
```

## Quick Health Check

For rapid validation:
```bash
cd agents && uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from openai import OpenAI

# Quick checks
storage = SupabaseStorageClient()
checkpointer = get_checkpointer()
client = OpenAI()

print('✅ All critical systems healthy')
" && echo "✅ Quick health check passed"
```

## Notes

- Run regularly to catch issues early
- Automate as part of monitoring
- Check after deployments
- Verify after infrastructure changes
