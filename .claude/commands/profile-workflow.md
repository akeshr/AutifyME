# Profile Workflow

Performance profiling for workflows.

## Usage

```
/profile-workflow [workflow-name]
```

**Workflows**: `cataloging`, `hitl`, `image-analysis`

## Task

Profile workflow execution to identify performance bottlenecks.

### 1. Time Full Workflow

```bash
cd agents
echo "=== Full Workflow Profiling ==="

time uv run python scripts/simulate.py \
  --text "Catalog test product, $99" \
  --image /tmp/test.jpg \
  --hitl

echo ""
echo "Check output above for total execution time"
```

### 2. Profile Individual Components

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
import time
load_dotenv('../.env')

print('=== Component Profiling ===')
print()

# 1. Media Download
print('1. Media Download')
start = time.time()
# Simulate download (actual download would be via WhatsApp API)
from pathlib import Path
test_file = Path('/tmp/test_product.jpg')
if test_file.exists():
    with open(test_file, 'rb') as f:
        data = f.read()
download_time = time.time() - start
print(f'   Time: {download_time:.3f}s')
print()

# 2. Image Analysis
print('2. Image Analysis (Base64 + Vision API)')
start = time.time()
from autifyme_agents.specialists.image_analysis_specialist import image_analysis_specialist_invoke
if test_file.exists():
    result = image_analysis_specialist_invoke(
        image_url=str(test_file),
        company_profile={'brand_voice': 'casual', 'target_audience': 'young adults'}
    )
    analysis_time = time.time() - start
    print(f'   Time: {analysis_time:.3f}s')
    print(f'   Result: {len(result.visual_description)} chars')
else:
    print('   Skipped (test file not found)')
print()

# 3. Product Structuring
print('3. Cataloging Specialist')
start = time.time()
from autifyme_agents.specialists.cataloging_specialist import cataloging_specialist_invoke
product = cataloging_specialist_invoke(
    user_message='Test product, \$99',
    image_analysis=result.model_dump() if test_file.exists() else None
)
cataloging_time = time.time() - start
print(f'   Time: {cataloging_time:.3f}s')
print()

# 4. Database Save
print('4. Database Persistence')
start = time.time()
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
storage = SupabaseStorageClient()
# Note: Would actually call save_product tool
save_time = time.time() - start
print(f'   Time: {save_time:.3f}s (mocked)')
print()

# Summary
total = download_time + analysis_time + cataloging_time + save_time
print('=== Summary ===')
print(f'Media download: {download_time:.3f}s ({100*download_time/total:.1f}%)')
print(f'Image analysis: {analysis_time:.3f}s ({100*analysis_time/total:.1f}%)')
print(f'Cataloging: {cataloging_time:.3f}s ({100*cataloging_time/total:.1f}%)')
print(f'DB save: {save_time:.3f}s ({100*save_time/total:.1f}%)')
print(f'Total: {total:.3f}s')
"
```

### 3. Profile LLM Calls

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
import time
load_dotenv('../.env')
from openai import OpenAI

client = OpenAI()

print('=== LLM Call Profiling ===')
print()

# Test different operations
operations = [
    ('Simple completion', {'messages': [{'role': 'user', 'content': 'Say hello'}], 'max_tokens': 10}),
    ('Vision API', {'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': 'Describe briefly'},
        {'type': 'image_url', 'image_url': {'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg'}}
    ]}], 'max_tokens': 50}),
    ('Structured output', {'messages': [{'role': 'user', 'content': 'Extract: Product, Price'}], 'max_tokens': 50}),
]

for name, kwargs in operations:
    print(f'{name}:')
    start = time.time()
    try:
        response = client.chat.completions.create(model='gpt-4o', **kwargs)
        duration = time.time() - start
        tokens = response.usage.total_tokens
        print(f'  Time: {duration:.3f}s')
        print(f'  Tokens: {tokens}')
        print(f'  Speed: {tokens/duration:.0f} tokens/s')
    except Exception as e:
        print(f'  Error: {str(e)[:100]}')
    print()
"
```

### 4. Profile Database Operations

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
import time
load_dotenv('../.env')

print('=== Database Operation Profiling ===')
print()

# Supabase operations
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
storage = SupabaseStorageClient()

operations = [
    ('Get company profile', lambda: storage.get_company_profile()),
    ('List products (10)', lambda: storage.supabase.table('products').select('*').limit(10).execute()),
    ('Count approvals', lambda: storage.supabase.table('pending_approvals').select('*', count='exact').execute()),
]

for name, op in operations:
    print(f'{name}:')
    start = time.time()
    try:
        result = op()
        duration = time.time() - start
        print(f'  Time: {duration:.3f}s')
    except Exception as e:
        print(f'  Error: {str(e)[:100]}')
    print()

# PostgreSQL operations
import psycopg
from autifyme_agents.core.config import settings

print('Checkpoint operations:')
start = time.time()
with psycopg.connect(settings.DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM checkpoints')
        count = cur.fetchone()[0]
duration = time.time() - start
print(f'  Time: {duration:.3f}s')
print(f'  Checkpoints: {count}')
"
```

### 5. Profile HITL Workflow

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
import time
load_dotenv('../.env')

print('=== HITL Workflow Profiling ===')
print()

# This requires actual workflow execution
# Use LangSmith trace timing instead

from langsmith import Client
client = Client()

# Find HITL traces
runs = list(client.list_runs(order='desc', limit=100))
hitl_runs = [r for r in runs if 'interrupted' in str(r.status).lower() or '__interrupt__' in str(r.outputs)]

if hitl_runs:
    print(f'Found {len(hitl_runs)} HITL workflows')
    print()

    durations = []
    for run in hitl_runs[:10]:
        if run.end_time and run.start_time:
            duration = (run.end_time - run.start_time).total_seconds()
            durations.append(duration)
            print(f'Run {run.id}: {duration:.1f}s until interrupt')

    if durations:
        avg_duration = sum(durations) / len(durations)
        print()
        print(f'Average time to interrupt: {avg_duration:.1f}s')
else:
    print('No HITL workflows found in recent traces')
"
```

### 6. Identify Bottlenecks

```bash
echo "=== Performance Bottleneck Analysis ==="
echo ""
echo "Common bottlenecks:"
echo ""
echo "1. Vision API Calls (2-5s)"
echo "   - Base64 encoding: ~0.1s"
echo "   - API latency: 2-4s"
echo "   - Solution: Cache results, optimize image size"
echo ""
echo "2. LLM Calls (1-3s each)"
echo "   - Network latency: 0.5-1s"
echo "   - Generation time: varies with tokens"
echo "   - Solution: Use streaming, batch when possible"
echo ""
echo "3. Database Queries (0.1-0.5s)"
echo "   - Checkpoint read/write: 0.1-0.3s"
echo "   - Product save: 0.1-0.2s"
echo "   - Solution: Connection pooling, indexes"
echo ""
echo "4. Media Download (0.5-2s)"
echo "   - WhatsApp API: variable"
echo "   - File size dependent"
echo "   - Solution: Async download, optimize size"
```

### 7. Generate Performance Report

```markdown
## Workflow Performance Profile

**Workflow**: Cataloging (with image)
**Date**: [timestamp]

### Component Breakdown

| Component | Time (s) | % of Total | Tokens | Bottleneck? |
|-----------|----------|------------|--------|-------------|
| Media download | 1.2 | 15% | - | ⚠️ Variable |
| Image analysis | 3.8 | 48% | 450 | ❌ Slow |
| Base64 encoding | 0.1 | 1% | - | ✅ Fast |
| Vision API | 3.7 | 47% | 450 | ❌ Slow |
| Cataloging | 2.1 | 26% | 320 | ⚠️ OK |
| Product structuring | 2.0 | 25% | 310 | ⚠️ OK |
| Context injection | 0.1 | 1% | 10 | ✅ Fast |
| DB save | 0.2 | 3% | - | ✅ Fast |
| **Total** | **7.9** | **100%** | **770** | |

### Performance Characteristics

- **Average workflow**: 7-10 seconds
- **HITL add-on**: +0.5s (interrupt + state save)
- **Resume time**: 2-3s (checkpoint load + continuation)

### Bottlenecks Identified

1. **Vision API** (3.7s, 47% of time)
   - Largest single bottleneck
   - API latency dominates
   - Improvement: Cache results, async processing

2. **LLM Calls** (5.8s combined, 73%)
   - Multiple sequential calls
   - Improvement: Parallel where possible, use mini models

3. **Media Download** (1.2s, 15%)
   - Variable based on file size
   - Improvement: Optimize image resolution

### Optimization Recommendations

**High Impact** (>1s improvement):
1. Cache image analysis results (save 3.7s on repeats)
2. Use GPT-4o-mini for simple structuring (save 1-2s)
3. Parallel tool calls where possible (save 1-2s)

**Medium Impact** (0.5-1s improvement):
1. Optimize image size before encoding
2. Connection pooling for DB
3. Async media download

**Low Impact** (<0.5s):
1. Reduce prompt verbosity
2. Optimize checkpoint size

### Target Performance

- **Current**: 7-10s per workflow
- **Optimized**: 4-6s per workflow
- **Savings**: 40-50% reduction

---

**Next Steps**: Implement high-impact optimizations first
```

## Notes

- Focus on user-perceivable latency
- API calls dominate execution time
- Caching provides biggest wins
- Monitor after optimizations
- Balance speed vs cost vs quality
