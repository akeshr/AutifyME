# Production Data → Test Scenario Reconstruction

**Vision**: Use production user data to recreate test scenarios, validate fixes, and detect regressions.

---

## The Problem

**Two separate systems**:
1. **LangSmith**: Stores traces (execution flow, errors, performance)
2. **Supabase**: Stores user data (messages, products, checkpoints, outcomes)

**Current state**: NO automatic correlation between trace_id and thread_id in database.

---

## Correlation Strategy

### LangSmith → Supabase (One-Way Correlation)

**LangSmith metadata includes**:
```json
{
  "metadata": {
    "langsmith.thread_id": "whatsapp:857147627470406:917258067800",
    "workflow": "cataloging",
    "thread_id": "whatsapp:857147627470406:917258067800"
  }
}
```

**Correlation path**:
```
trace_id (LangSmith)
  → query LangSmith Run metadata
  → extract thread_id
  → query Supabase tables by thread_id
  → get user data (messages, outcomes, products)
```

### Database Tables for Reconstruction

**workflow_outcomes**: Complete workflow execution record
- thread_id, sender_id, message_text, media_id, platform
- success, error_type, error_message
- duration_seconds, created_at
- result_data (JSONB)

**checkpoints**: LangGraph state snapshots
- thread_id, checkpoint_id
- checkpoint JSONB (contains messages, state)
- metadata JSONB

**products**: Created products
- name, description, price, sizes, colors, image_urls
- created_at (for time-based correlation)

**processed_messages**: Deduplication tracking
- message_id, sender_id, thread_id
- received_at, processed_at

---

## Reconstruction Scenarios

### Scenario 1: Given trace_id from LangSmith

**Use case**: "I saw an issue in LangSmith trace abc123, reproduce it"

**Workflow**:
```python
# 1. Get thread_id from trace metadata
overview = get_trace_overview("abc123")
# Extract thread_id from trace metadata (if available)

# 2. Query Supabase for user data
mcp__supabase__execute_sql(query="""
    SELECT sender_id, message_text, media_id, platform, created_at
    FROM workflow_outcomes
    WHERE thread_id = 'whatsapp:...'
    ORDER BY created_at DESC
    LIMIT 1
""")

# 3. Recreate scenario
result = execute_scenario(
    scenario_id=message_text,  # Use original user message
    hitl_mode="auto_approve",   # Or extract approval from checkpoint
    media_path=media_id          # If media was involved
)

# 4. Compare traces
old_overview = get_trace_overview("abc123")  # Original
new_overview = get_trace_overview(result.trace_id)  # New

# Compare:
# - Run counts (did we fix missing department calls?)
# - Error status (did fix resolve errors?)
# - Latency (did we improve performance?)
# - Cost (did we reduce token usage?)
```

**Limitation**: trace_id → thread_id requires querying LangSmith metadata first.

---

### Scenario 2: Given thread_id from Database

**Use case**: "Query DB for failed workflows, recreate them"

**Workflow**:
```python
# 1. Find failed workflows
mcp__supabase__execute_sql(query="""
    SELECT thread_id, sender_id, message_text, media_id, error_message
    FROM workflow_outcomes
    WHERE success = false
    ORDER BY created_at DESC
    LIMIT 10
""")

# 2. For each failure, recreate
for outcome in failures:
    result = execute_scenario(
        scenario_id=outcome['message_text'],
        hitl_mode="auto_approve",
        media_path=outcome['media_id']
    )

    # 3. Validate fix
    if result.success:
        print(f"✅ FIXED: {outcome['thread_id']}")
    else:
        print(f"❌ STILL FAILING: {outcome['thread_id']}")
        # Analyze new trace
        overview = get_trace_overview(result.trace_id)
```

---

### Scenario 3: Regression Testing

**Use case**: "After fixing PM prompt, validate all recent workflows still work"

**Workflow**:
```python
# 1. Get recent successful workflows
mcp__supabase__execute_sql(query="""
    SELECT thread_id, message_text, media_id, duration_seconds
    FROM workflow_outcomes
    WHERE success = true
      AND created_at > NOW() - INTERVAL '7 days'
    ORDER BY created_at DESC
    LIMIT 20
""")

# 2. Re-execute all scenarios
results = []
for outcome in successes:
    result = execute_scenario(
        scenario_id=outcome['message_text'],
        hitl_mode="auto_approve"
    )

    results.append({
        'original_thread': outcome['thread_id'],
        'new_success': result.success,
        'original_duration': outcome['duration_seconds'],
        'new_duration': result.execution_time_seconds,
        'regression': not result.success  # Was successful, now fails
    })

# 3. Report regressions
regressions = [r for r in results if r['regression']]
if regressions:
    print(f"⚠️ REGRESSIONS DETECTED: {len(regressions)} workflows now failing")
```

---

### Scenario 4: Extract Full Conversation from Checkpoints

**Use case**: "Get exact messages exchanged for complex multi-turn scenario"

**Workflow**:
```python
# 1. Query checkpoint for conversation history
mcp__supabase__execute_sql(query="""
    SELECT checkpoint_id, checkpoint->'channel_values'->'messages' as messages
    FROM checkpoints
    WHERE thread_id = 'whatsapp:...'
    ORDER BY checkpoint_id DESC
    LIMIT 1
""")

# 2. Extract user messages and approvals
# checkpoint.messages contains full LangChain message history
# Parse to reconstruct multi-turn conversation

# 3. Replay conversation
# For each user message in checkpoint:
#   execute_scenario(message, hitl_mode based on approval in checkpoint)
```

---

## Missing Link: Storing trace_id in Database

**Current Gap**: Database doesn't store trace_id, so can't go from thread_id → trace_id directly.

**Solution Options**:

### Option 1: Add trace_id to workflow_outcomes (Recommended)

**Migration**:
```sql
ALTER TABLE workflow_outcomes
ADD COLUMN trace_id TEXT;

CREATE INDEX idx_workflow_outcomes_trace_id ON workflow_outcomes(trace_id);
```

**Update runner_v2.py** to capture trace_id:
```python
# In _execute_workflow(), after execution:
try:
    run_tree = get_current_run_tree()
    if run_tree:
        trace_id = str(run_tree.trace_id)
        # Store in workflow_outcomes
except:
    pass
```

**Benefit**: Bidirectional correlation
- trace_id → thread_id (via LangSmith metadata)
- thread_id → trace_id (via Supabase query)

### Option 2: Query LangSmith by thread_id (Current Workaround)

**Workflow**:
```python
# Given thread_id from DB, find trace
from langsmith import Client
client = Client()

runs = list(client.list_runs(
    project_name="autifyme-dev",
    filter=f'eq(metadata_key, "langsmith.thread_id") and eq(metadata_value, "{thread_id}")',
    is_root=True,
    limit=1
))

if runs:
    trace_id = str(runs[0].trace_id)
```

**Limitation**: Requires LangSmith API call, slower, requires exact metadata match.

---

## Reconstruction Playbook

### For workflow-tester Agent

**New capabilities to add**:

1. **reconstruct_from_trace(trace_id)**
   - Query LangSmith for metadata → extract thread_id
   - Query Supabase for user data
   - Execute scenario with original inputs
   - Compare old vs new trace

2. **reconstruct_from_thread(thread_id)**
   - Query Supabase for workflow_outcomes
   - Execute scenario with original inputs
   - Analyze new trace, validate fix

3. **regression_test(since_date, limit)**
   - Query successful workflows from Supabase
   - Re-execute all scenarios
   - Report any that now fail (regressions)

4. **find_and_fix_failures(limit)**
   - Query failed workflows from Supabase
   - Re-execute each failure
   - Identify if fix resolved issue
   - Document remaining failures

---

## Implementation Plan

### Phase 1: Basic Reconstruction (No Code Changes)

**Use existing tools**:
1. Manually query LangSmith metadata for thread_id
2. Use MCP to query Supabase by thread_id
3. Use execute_scenario() with extracted data
4. Use get_trace_overview() to compare

**Agent workflow**: Manual but systematic

---

### Phase 2: Add trace_id to Database (Recommended)

**Changes required**:
1. Migration: Add trace_id column to workflow_outcomes
2. Update runner_v2.py: Capture and store trace_id
3. Update workflow-tester agent: Direct correlation queries

**Benefit**: Seamless bidirectional correlation

---

### Phase 3: Automated Regression Suite

**Build on Phase 2**:
1. Scheduled job: Query recent successful workflows
2. Re-execute all scenarios
3. Compare traces (latency, cost, success)
4. Alert on regressions

---

## Example: Full Reconstruction Workflow

**Given**: trace_id = "87d9e336-f814-42c5-9819-5591a4ba7be9"

**Step 1**: Get thread_id from trace
```python
overview = get_trace_overview("87d9e336-f814-42c5-9819-5591a4ba7be9")
# Manually extract thread_id from metadata (or query LangSmith Run)
thread_id = "console:test_fb095336"
```

**Step 2**: Query user data
```python
mcp__supabase__execute_sql(query=f"""
    SELECT message_text, media_id, success, error_message, created_at
    FROM workflow_outcomes
    WHERE thread_id = '{thread_id}'
    ORDER BY created_at DESC
    LIMIT 1
""")
# Result: message_text = "I want to catalog a product: Nike Air Max..."
```

**Step 3**: Recreate scenario
```python
result = execute_scenario(
    scenario_id="I want to catalog a product: Nike Air Max sneakers, white/blue colorway, sizes 8-12, price Rs 8500",
    hitl_mode="auto_approve"
)
```

**Step 4**: Compare traces
```python
old_overview = get_trace_overview("87d9e336-f814-42c5-9819-5591a4ba7be9")
new_overview = get_trace_overview(result.trace_id)

print(f"Old: {old_overview.total_runs} runs, {old_overview.total_latency_ms}ms")
print(f"New: {new_overview.total_runs} runs, {new_overview.total_latency_ms}ms")

# Check if fix resolved issue
if old_overview.total_runs == 6 and new_overview.total_runs > 6:
    print("✅ FIX VALIDATED: Department runs now present")
```

---

## Key Insights

1. **Use Supabase MCP directly** - No wrapper tools needed
2. **Correlation exists via thread_id** - LangSmith metadata → Supabase queries
3. **Production data is test data** - Real user scenarios for validation
4. **Reconstruction enables**:
   - Bug reproduction
   - Fix validation
   - Regression detection
   - Performance comparison

5. **Missing piece**: Store trace_id in database for bidirectional correlation (simple migration)

---

## Next Steps

1. **Immediate**: Update workflow-tester agent with reconstruction playbook
2. **Short-term**: Add trace_id to workflow_outcomes table
3. **Long-term**: Automated regression suite using production data
