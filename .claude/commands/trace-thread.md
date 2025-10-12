# Trace Thread

Find LangSmith traces for a specific thread or sender.

## Usage

```
/trace-thread [thread-id or sender]
```

## Task

Find and analyze all LangSmith traces for a conversation thread.

### 1. Search by Thread ID

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from langsmith import Client

client = Client()
thread_id = '<thread-id>'  # e.g., whatsapp_+1234567890

print(f'Searching for traces with thread_id={thread_id}')

# Search recent runs
runs = client.list_runs(order='desc', limit=500)
matching_runs = []

for run in runs:
    config = (run.inputs or {}).get('config', {})
    if isinstance(config, dict):
        configurable = config.get('configurable', {})
        if configurable.get('thread_id') == thread_id:
            matching_runs.append(run)

print(f'Found {len(matching_runs)} traces')
print()

for run in matching_runs[:10]:  # Show latest 10
    print(f'Trace ID: {run.id}')
    print(f'  Name: {run.name}')
    print(f'  Status: {run.status}')
    print(f'  Start: {run.start_time}')
    print(f'  Duration: {run.end_time - run.start_time if run.end_time else \"running\"}')
    print()
"
```

### 2. Get Latest Trace for Thread

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from langsmith import Client

client = Client()
thread_id = '<thread-id>'

runs = client.list_runs(order='desc', limit=200)
for run in runs:
    config = (run.inputs or {}).get('config', {})
    if isinstance(config, dict):
        configurable = config.get('configurable', {})
        if configurable.get('thread_id') == thread_id:
            print(f'Latest trace: {run.id}')
            print(f'Name: {run.name}')
            print(f'Status: {run.status}')
            print(f'URL: https://smith.langchain.com/o/<org>/projects/p/<project>/r/{run.id}')
            break
"
```

### 3. Analyze Workflow History

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from langsmith import Client
from datetime import datetime

client = Client()
thread_id = '<thread-id>'

runs = client.list_runs(order='desc', limit=500)
thread_runs = []

for run in runs:
    config = (run.inputs or {}).get('config', {})
    if isinstance(config, dict):
        configurable = config.get('configurable', {})
        if configurable.get('thread_id') == thread_id:
            thread_runs.append(run)

print(f'=== Workflow History for {thread_id} ===')
print(f'Total runs: {len(thread_runs)}')
print()

# Group by status
from collections import Counter
statuses = Counter(run.status for run in thread_runs)

print('Status breakdown:')
for status, count in statuses.items():
    print(f'  {status}: {count}')
print()

# Show chronological order
print('Timeline:')
for run in sorted(thread_runs, key=lambda r: r.start_time):
    print(f'{run.start_time.strftime(\"%Y-%m-%d %H:%M:%S\")} - {run.name} ({run.status})')
"
```

### 4. Find Failed Traces

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from langsmith import Client

client = Client()
thread_id = '<thread-id>'

runs = client.list_runs(order='desc', limit=500)
failed_runs = []

for run in runs:
    config = (run.inputs or {}).get('config', {})
    if isinstance(config, dict):
        configurable = config.get('configurable', {})
        if configurable.get('thread_id') == thread_id and run.status == 'error':
            failed_runs.append(run)

print(f'=== Failed Traces ({len(failed_runs)}) ===')
for run in failed_runs:
    print(f'Trace ID: {run.id}')
    print(f'  Name: {run.name}')
    print(f'  Error: {run.error}')
    print(f'  Time: {run.start_time}')
    print()
"
```

### 5. Find Interrupted Traces (HITL)

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from langsmith import Client

client = Client()
thread_id = '<thread-id>'

runs = client.list_runs(order='desc', limit=500)
interrupted_runs = []

for run in runs:
    config = (run.inputs or {}).get('config', {})
    if isinstance(config, dict):
        configurable = config.get('configurable', {})
        if configurable.get('thread_id') == thread_id:
            # Check if interrupted (status or outputs)
            if run.status == 'interrupted' or (run.outputs and '__interrupt__' in str(run.outputs)):
                interrupted_runs.append(run)

print(f'=== Interrupted Traces / HITL ({len(interrupted_runs)}) ===')
for run in interrupted_runs:
    print(f'Trace ID: {run.id}')
    print(f'  Name: {run.name}')
    print(f'  Time: {run.start_time}')
    print()
"
```

### 6. Quick Analysis

For the latest trace, automatically analyze:
```bash
cd agents
# Get latest trace ID
TRACE_ID=$(uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from langsmith import Client
client = Client()
thread_id = '<thread-id>'
runs = client.list_runs(order='desc', limit=200)
for run in runs:
    config = (run.inputs or {}).get('config', {})
    if isinstance(config, dict):
        configurable = config.get('configurable', {})
        if configurable.get('thread_id') == thread_id:
            print(run.id)
            break
")

# Dump and analyze
uv run python scripts/dump_langsmith_thread.py --run-id $TRACE_ID > ../trace_latest.txt
echo "Trace dumped to trace_latest.txt"
```

### 7. Report

```markdown
## Thread Trace Analysis: <thread-id>

### Overview
- Total traces: [count]
- Latest: [trace-id] ([timestamp])
- Status breakdown:
  - Success: [count]
  - Error: [count]
  - Interrupted: [count]

### Recent Activity
1. [timestamp] - [name] ([status])
2. [timestamp] - [name] ([status])
3. ...

### Failed Traces
[List with error messages]

### Interrupted Traces (HITL)
[List with interrupt reasons]

### Patterns
- [Common issues across traces]
- [Workflow progression]

### Quick Actions
- Analyze latest: `/analyze-traces [latest-trace-id]`
- Compare success vs failure: `/compare-traces [success-id] [failure-id]`
- Check state: `/check-state [thread-id]`
```

## Notes

- Thread IDs format: `whatsapp_<phone>` or `<platform>_<sender>`
- LangSmith keeps traces for 14 days (free tier)
- Traces may take a few seconds to appear after workflow
- Use LangSmith web UI for visual exploration
