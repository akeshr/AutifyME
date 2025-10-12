# Analyze Costs

Analyze LangSmith token usage and costs.

## Usage

```
/analyze-costs [time-period]
```

**Periods**: `today`, `week`, `month`, `all`

## Task

Analyze LangSmith traces to understand token usage and API costs.

### 1. Fetch Recent Runs

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from langsmith import Client
from datetime import datetime, timedelta

client = Client()

# Get runs from last 7 days
start_time = datetime.now() - timedelta(days=7)

print('=== Fetching Recent Runs ===')
runs = list(client.list_runs(
    order='desc',
    limit=1000,
    start_time=start_time
))

print(f'Found {len(runs)} runs in last 7 days')
"
```

### 2. Aggregate Token Usage

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from langsmith import Client
from datetime import datetime, timedelta
from collections import defaultdict

client = Client()
start_time = datetime.now() - timedelta(days=7)
runs = list(client.list_runs(order='desc', limit=1000, start_time=start_time))

print('=== Token Usage Analysis ===')

total_tokens = 0
total_prompt_tokens = 0
total_completion_tokens = 0

by_run_type = defaultdict(lambda: {'total': 0, 'prompt': 0, 'completion': 0, 'count': 0})

for run in runs:
    if not run.outputs:
        continue

    # Try to extract token usage
    usage = None
    if 'usage_metadata' in run.outputs:
        usage = run.outputs['usage_metadata']
    elif hasattr(run, 'total_tokens'):
        usage = {
            'total_tokens': run.total_tokens,
            'prompt_tokens': getattr(run, 'prompt_tokens', 0),
            'completion_tokens': getattr(run, 'completion_tokens', 0)
        }

    if usage:
        tokens = usage.get('total_tokens', 0) or usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
        prompt = usage.get('prompt_tokens', 0) or usage.get('input_tokens', 0)
        completion = usage.get('completion_tokens', 0) or usage.get('output_tokens', 0)

        total_tokens += tokens
        total_prompt_tokens += prompt
        total_completion_tokens += completion

        run_type = run.name or run.run_type
        by_run_type[run_type]['total'] += tokens
        by_run_type[run_type]['prompt'] += prompt
        by_run_type[run_type]['completion'] += completion
        by_run_type[run_type]['count'] += 1

print(f'Total tokens: {total_tokens:,}')
print(f'Prompt tokens: {total_prompt_tokens:,}')
print(f'Completion tokens: {total_completion_tokens:,}')
print()
print('By run type:')
for run_type, stats in sorted(by_run_type.items(), key=lambda x: x[1]['total'], reverse=True)[:10]:
    print(f'  {run_type}:')
    print(f'    Runs: {stats[\"count\"]}')
    print(f'    Total: {stats[\"total\"]:,} tokens')
    print(f'    Avg: {stats[\"total\"]//stats[\"count\"]:,} tokens/run')
"
```

### 3. Estimate Costs

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from langsmith import Client
from datetime import datetime, timedelta

client = Client()
start_time = datetime.now() - timedelta(days=7)
runs = list(client.list_runs(order='desc', limit=1000, start_time=start_time))

print('=== Cost Estimation ===')

# OpenAI GPT-4o pricing (as of 2025)
# Input: \$2.50 / 1M tokens
# Output: \$10.00 / 1M tokens

INPUT_COST_PER_1M = 2.50
OUTPUT_COST_PER_1M = 10.00

total_input_tokens = 0
total_output_tokens = 0

for run in runs:
    if not run.outputs:
        continue

    usage = run.outputs.get('usage_metadata')
    if usage:
        total_input_tokens += usage.get('input_tokens', 0)
        total_output_tokens += usage.get('output_tokens', 0)

input_cost = (total_input_tokens / 1_000_000) * INPUT_COST_PER_1M
output_cost = (total_output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
total_cost = input_cost + output_cost

print(f'Input tokens: {total_input_tokens:,}')
print(f'Output tokens: {total_output_tokens:,}')
print()
print(f'Input cost: \${input_cost:.2f}')
print(f'Output cost: \${output_cost:.2f}')
print(f'Total cost (7 days): \${total_cost:.2f}')
print(f'Estimated monthly: \${total_cost * 4:.2f}')
"
```

### 4. Analyze by Workflow

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from langsmith import Client
from datetime import datetime, timedelta
from collections import defaultdict

client = Client()
start_time = datetime.now() - timedelta(days=7)
runs = list(client.list_runs(order='desc', limit=1000, start_time=start_time))

print('=== Cost by Workflow Type ===')

by_workflow = defaultdict(lambda: {
    'runs': 0,
    'input_tokens': 0,
    'output_tokens': 0
})

for run in runs:
    # Extract workflow from metadata or name
    workflow = 'unknown'
    if run.metadata and 'workflow' in run.metadata:
        workflow = run.metadata['workflow']
    elif 'catalog' in run.name.lower():
        workflow = 'cataloging'
    elif 'pm' in run.name.lower() or 'project' in run.name.lower():
        workflow = 'project_manager'

    if run.outputs and 'usage_metadata' in run.outputs:
        usage = run.outputs['usage_metadata']
        by_workflow[workflow]['runs'] += 1
        by_workflow[workflow]['input_tokens'] += usage.get('input_tokens', 0)
        by_workflow[workflow]['output_tokens'] += usage.get('output_tokens', 0)

INPUT_COST = 2.50 / 1_000_000
OUTPUT_COST = 10.00 / 1_000_000

for workflow, stats in sorted(by_workflow.items(), key=lambda x: x[1]['input_tokens'] + x[1]['output_tokens'], reverse=True):
    total_tokens = stats['input_tokens'] + stats['output_tokens']
    cost = (stats['input_tokens'] * INPUT_COST) + (stats['output_tokens'] * OUTPUT_COST)

    print(f'{workflow}:')
    print(f'  Runs: {stats[\"runs\"]}')
    print(f'  Tokens: {total_tokens:,}')
    print(f'  Cost: \${cost:.2f}')
    print(f'  Avg/run: {total_tokens//stats[\"runs\"] if stats[\"runs\"] > 0 else 0:,} tokens')
    print()
"
```

### 5. Identify Expensive Operations

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from langsmith import Client
from datetime import datetime, timedelta

client = Client()
start_time = datetime.now() - timedelta(days=7)
runs = list(client.list_runs(order='desc', limit=1000, start_time=start_time))

print('=== Most Expensive Operations ===')

expensive_runs = []

for run in runs:
    if run.outputs and 'usage_metadata' in run.outputs:
        usage = run.outputs['usage_metadata']
        total = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)

        if total > 5000:  # More than 5k tokens
            expensive_runs.append({
                'id': run.id,
                'name': run.name,
                'tokens': total,
                'time': run.start_time
            })

expensive_runs.sort(key=lambda x: x['tokens'], reverse=True)

print(f'Found {len(expensive_runs)} expensive runs (>5k tokens)')
print()

for run in expensive_runs[:10]:
    print(f'{run[\"name\"]}:')
    print(f'  ID: {run[\"id\"]}')
    print(f'  Tokens: {run[\"tokens\"]:,}')
    print(f'  Time: {run[\"time\"]}')
    print()
"
```

### 6. Optimization Recommendations

```bash
echo "=== Optimization Recommendations ==="
echo ""
echo "Based on token usage patterns, consider:"
echo ""
echo "1. Prompt Optimization"
echo "   - Reduce verbose system prompts"
echo "   - Use more concise instructions"
echo "   - Remove redundant examples"
echo ""
echo "2. Context Management"
echo "   - Implement message summarization"
echo "   - Trim old conversation history"
echo "   - Use SummarizationMiddleware effectively"
echo ""
echo "3. Model Selection"
echo "   - Use GPT-4o-mini for simple tasks"
echo "   - Reserve GPT-4o for complex reasoning"
echo "   - Consider GPT-3.5-turbo for deterministic tasks"
echo ""
echo "4. Caching"
echo "   - Cache image analysis results"
echo "   - Reuse company context"
echo "   - Implement prompt caching (if available)"
```

### 7. Generate Cost Report

```markdown
## Token Usage & Cost Analysis

**Period**: Last 7 days
**Total Runs**: [count]

### Token Usage

- **Input**: [count] tokens
- **Output**: [count] tokens
- **Total**: [count] tokens

### Costs (Estimated)

- Input cost: $[amount] (@$2.50/1M)
- Output cost: $[amount] (@$10.00/1M)
- **Total (7 days)**: $[amount]
- **Estimated Monthly**: $[amount * 4]

### Cost by Workflow

| Workflow | Runs | Tokens | Cost | Avg/Run |
|----------|------|--------|------|---------|
| Cataloging | [n] | [n] | $[n] | [n] |
| PM | [n] | [n] | $[n] | [n] |
| [Other] | [n] | [n] | $[n] | [n] |

### Expensive Operations

Top 5 runs by token usage:
1. [name]: [tokens] tokens ($[cost])
2. [name]: [tokens] tokens ($[cost])
...

### Recommendations

**High Impact**:
- [Specific optimization with estimated savings]

**Medium Impact**:
- [Specific optimization]

**Monitoring**:
- [Metrics to track]

---

**Projected Annual Cost**: $[monthly * 12]
```

## Notes

- Costs are estimates based on OpenAI pricing
- Actual costs may vary with pricing changes
- Does not include LangSmith tracing costs
- Focus on high-token operations first
- Monitor after optimizations
