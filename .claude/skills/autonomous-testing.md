# Autonomous Testing Framework Skill

You are Claude, orchestrating autonomous testing of the AutifyME agentic system using a specialized testing framework.

## Core Philosophy

**"Tools provide visibility, Claude provides intelligence."**

You have 7 observation tools that gather information. You use your existing capabilities (Edit, Write, Read, MCP) to analyze findings and implement improvements.

## Available Tools (7 Essential)

### 1. `execute_scenario(scenario_id, hitl_mode, media_path)`
**Execute workflow tests programmatically**

```python
from tests.tools import execute_scenario

result = execute_scenario(
    scenario_id="Catalog these sneakers",  # Or custom prompt
    hitl_mode="auto_approve",  # "auto_approve" | "auto_reject"
    media_path=None  # Optional path to media file
)

# Returns ExecutionResult with:
# - success: bool
# - trace_id: str (for analysis)
# - trace_url: str (LangSmith link)
# - thread_id: str
# - products_created: int
# - execution_time_seconds: float
# - errors: list[str]
```

**When to use**: Starting point for all testing. Run scenarios to validate workflows.

**CRITICAL - Intelligent HITL Detection (Game-Changer)**:

The framework now intelligently reads PM's approval request BEFORE responding, instead of blindly sending approve/reject.

**How It Works**:
1. Executes workflow until PM sends a message
2. Inspects ALL messages sent by PM during execution
3. Detects approval request patterns (keywords: "approve"/"review" + "product"/"campaign"/"family")
4. Only sends follow-up ("approve"/"reject") if interrupt actually occurred
5. Reports error if expected HITL didn't happen (PM asked question or workflow failed)

**New ExecutionResult Fields**:
```python
result.interrupt_occurred        # True if PM sent approval request
result.approval_message         # Full approval message from PM
result.approval_type           # "product" or "campaign"
result.is_batch_approval       # True if batch approval (multiple items)
```

**Debugging Pattern**:
```python
result = execute_scenario("Onboard product", hitl_mode="auto_approve")

if not result.interrupt_occurred:
    # Expected HITL but didn't happen - PM may have asked a question
    print(f"No HITL detected. Errors: {result.errors}")
    overview = get_trace_overview(result.trace_id)
    # Analyze what PM actually sent

if result.approval_type == "product" and not result.success:
    # Product workflow failed after approval
    details = get_run_details(product_specialist_run_id)
    # Drill into specialist execution

if result.is_batch_approval:
    # Batch approval - validate all products processed
    # Query database for products created
```

**Impact**: Tests now validate HITL actually occurred (not just assumed). Prevents false positives where workflow failed but we blindly sent "approve".

---

### 2. `get_trace_overview(trace_id)`
**Level 0 hierarchical analysis (~500 tokens)**

```python
from tests.tools import get_trace_overview

overview = get_trace_overview(result.trace_id)

# Returns TraceOverview with:
# - trace_id: str
# - total_runs: int
# - total_cost: float
# - total_latency_ms: int
# - run_tree: list[RunNode]  # Hierarchical tree

# Traverse tree to find failures
def find_failures(node):
    if node.status == "error":
        print(f"Failed: {node.name} - {node.error}")
    for child in node.children:
        find_failures(child)
```

**When to use**: ALWAYS after execute_scenario(). Identifies failures, slow runs, expensive runs without loading full inputs/outputs.

**Token efficiency**: 25x savings (500 tokens vs 50K for full dump)

---

### 3. `get_run_details(run_id)`
**Level 1 specific run analysis (~1,500 tokens)**

```python
from tests.tools import get_run_details

# After finding interesting run in overview
details = get_run_details(failed_node.run_id)

# Returns RunDetails with:
# - run_id: str
# - name: str
# - run_type: str ("chain" | "llm" | "tool")
# - inputs: dict
# - outputs: dict | None
# - error: str | None
# - metadata: RunMetadata (model, tokens, latency)
```

**When to use**: After Level 0 identifies failure/issue. Drill into specific runs to see inputs, outputs, errors.

---

### 4. `get_run_messages(run_id)`
**Level 2 full conversation (~5K+ tokens, RARE)**

```python
from tests.tools import get_run_messages

# Only when Level 1 doesn't explain the issue
messages = get_run_messages(llm_run_id)

# Returns RunMessages with:
# - run_id: str
# - messages: list[Message]  # Full conversation with tool calls
```

**When to use**: ONLY when:
- Root cause unclear from Level 0 + Level 1
- Need to see exact prompt/response
- Debugging complex multi-step reasoning
- Investigating context leakage

**Cost**: Expensive in tokens. Use sparingly.

---

### 5. `get_llm_trace_tree(trace_id)`
**LLM-only trace extraction (~2-5k tokens)**

```python
from tests.tools import get_llm_trace_tree

# Extract hierarchical tree of ONLY LLM calls with full prompts
llm_tree = get_llm_trace_tree(trace_id)

# Returns LLMTraceTree with:
# - trace_id: str
# - trace_url: str
# - total_llm_calls: int
# - total_tokens: int
# - total_cost: float
# - llm_tree: list[LLMCallNode]  # Hierarchical tree of LLM calls

# Each LLMCallNode contains:
# - run_id: str
# - agent_name: str  # "PM" | "CatalogingDept" | "ImageAnalysisSpecialist"
# - hierarchy_level: str  # "orchestrator" | "department" | "specialist"
# - system_prompt: str  # Full system prompt
# - user_messages: list[dict]  # All user/context messages
# - assistant_output: dict  # LLM response
# - model: str  # "gpt-4o-mini"
# - total_tokens: int
# - latency_ms: int
# - status: str
# - error: str | None
# - parent_agent: str | None
# - children: list[LLMCallNode]  # Nested LLM calls
```

**When to use**:
- Prompt analysis and optimization
- Understanding agent decision-making and reasoning
- Analyzing context flow between hierarchy levels (PM → Dept → Specialist)
- Debugging LLM outputs without tool/chain noise
- Identifying prompt engineering issues

**Key benefit**: Filters out chains and tools to show ONLY LLM reasoning with full prompts and outputs. Perfect for prompt analysis, much cleaner than get_run_messages() for understanding multi-agent LLM interactions.

**Token efficiency**: ~2-5k tokens per trace (includes ALL LLM prompts + outputs, but excludes chain/tool runs)

---

### 6. `get_workflow_story(trace_ids)`
**Multi-trace HITL workflow analysis (~500 tokens per trace)**

```python
from tests.tools import get_workflow_story

# Analyze complete HITL workflow across multiple traces
story = get_workflow_story([
    'trace_id_1',  # Initial extraction
    'trace_id_2',  # First HITL resume
    'trace_id_3',  # Second HITL resume
])

# Returns WorkflowStory with:
# - thread_id: str
# - total_traces: int
# - traces: list[WorkflowTrace]  # Each with overview, HITL interrupt detection
# - products_extracted: int
# - products_saved: int
# - products_edited: int
# - products_rejected: int
# - total_cost: float (across all traces)
# - total_latency_ms: int (across all traces)
```

**When to use**: Analyzing complete HITL workflows that span multiple traces (initial → interrupt → resume). Essential for validating user approval decisions, price edits, and rejection handling.

**Token efficiency**: Uses get_trace_overview() internally for each trace (~500 tokens per trace vs 50K+ for naive approach)

**How to get trace_ids**:
```python
# Option 1: Query from Supabase (future workflows auto-populate trace_id)
trace_ids = mcp__supabase__execute_sql(
    "SELECT trace_id FROM workflow_outcomes
     WHERE thread_id = '...'
     ORDER BY created_at"
)

# Option 2: Manual from LangSmith dashboard (current approach)
trace_ids = ['trace1', 'trace2', 'trace3']

story = get_workflow_story(trace_ids)
```

---

### 7. `list_recent_tests(limit)`
**Test history for progress tracking**

```python
from tests.tools import list_recent_tests

history = list_recent_tests(limit=10)

# Returns TestHistory with:
# - tests: list[TestExecution]
#   - timestamp: datetime
#   - scenario_id: str
#   - success: bool
#   - trace_url: str
#   - execution_time_seconds: float
#   - errors_summary: str
```

**When to use**: Track testing progress, identify trends, compare execution times.

---

## Testing Workflow (Decision Tree)

### Phase 1: Execute & Observe
```
1. execute_scenario(scenario_id, hitl_mode)
   └─> If success=False → Check errors in result.errors
   └─> Always proceed to Level 0 analysis
```

### Phase 2: Hierarchical Analysis
```
2. get_trace_overview(trace_id)
   └─> Scan run_tree for:
       - status == "error" → Identify failed runs
       - High duration_ms → Identify slow runs
       - Check total_cost → Budget analysis

   └─> IF failures found:
       └─> 3. get_run_details(failed_run_id)
           └─> Examine inputs, outputs, error
           └─> IF root cause unclear:
               └─> 4. get_run_messages(llm_run_id)  # RARE
```

### Phase 3: Diagnosis & Fix
```
5. Use existing tools to fix issues:
   - Edit: Update code
   - Read: Inspect related files
   - MCP (Supabase): Validate database state
   - WebSearch/WebFetch: Research solutions
```

### Phase 4: Validate Fix
```
6. execute_scenario(same_scenario, hitl_mode)
   └─> get_trace_overview(new_trace_id)
       └─> Compare: old vs new (cost, latency, success)
```

### Phase 5: Track Progress
```
7. list_recent_tests(limit=10)
   └─> Identify trends
   └─> Document improvements
```

---

## Best Practices

### Token Budget Management
- **Level 0 (Overview)**: Always use. Only 500 tokens.
- **Level 1 (Details)**: Use selectively. 1,500 tokens per run.
- **Level 2 (Messages)**: Use rarely. 5K+ tokens. Only when absolutely necessary.

**Example**: Trace with 20 runs
- Naive approach: Load all inputs/outputs = 50K tokens
- Hierarchical approach: Level 0 (500) + Level 1 for 2 failures (3K) = 3.5K tokens
- **Savings**: 93% token reduction

### Error Investigation Priority
1. Check `ExecutionResult.errors` first (immediate failures)
2. Run `get_trace_overview()` (find where in hierarchy it failed)
3. Use `get_run_details()` on failed runs only
4. Reserve `get_run_messages()` for mysterious LLM behavior

### Iterative Testing Pattern
```python
# Iteration 1: Discover issue
result = execute_scenario("test scenario")
overview = get_trace_overview(result.trace_id)
# → Find PM failed with ToolException

# Iteration 2: Investigate
details = get_run_details(pm_run_id)
# → See inputs show invalid media_id format

# Iteration 3: Fix
# Use Edit to fix media handling in PM

# Iteration 4: Validate
result2 = execute_scenario("test scenario")
overview2 = get_trace_overview(result2.trace_id)
# → All runs successful, compare metrics
```

### Database Validation
Use Supabase MCP tools alongside trace analysis:
```python
# After successful execution
result = execute_scenario("catalog product")
if result.success and result.products_created > 0:
    # Validate in database
    # Use MCP: mcp__supabase__execute_sql
    # Query: SELECT * FROM products WHERE thread_id = '{result.thread_id}'
```

---

## Common Scenarios

### Scenario: Test fails immediately
```python
result = execute_scenario("catalog product")
if not result.success:
    print(f"Errors: {result.errors}")
    # Often shows: ConnectionError, ImportError, ToolException
    # Fix code directly, no need for trace analysis
```

### Scenario: Workflow completes but wrong output
```python
result = execute_scenario("catalog product")
overview = get_trace_overview(result.trace_id)

# Find tool runs
def find_tool_runs(node):
    if node.run_type == "tool":
        print(f"Tool: {node.name}, Status: {node.status}")
    for child in node.children:
        find_tool_runs(child)

# Check if save_product was called
# If not called → PM routing issue
# If called but wrong data → Specialist extraction issue
```

### Scenario: HITL approval not working
```python
result = execute_scenario("catalog product", hitl_mode="auto_approve")
overview = get_trace_overview(result.trace_id)

# Look for HumanInTheLoopMiddleware in tree
# Check if interrupt occurred
# Examine approval_analyzer runs
```

### Scenario: High latency
```python
overview = get_trace_overview(trace_id)
print(f"Total latency: {overview.total_latency_ms}ms")

# Find slowest runs
def find_slow_runs(node, threshold_ms=2000):
    if node.duration_ms > threshold_ms:
        print(f"Slow: {node.name} - {node.duration_ms}ms")
    for child in node.children:
        find_slow_runs(child, threshold_ms)
```

---

## Integration with Existing Tools

### Use Edit/Write for fixes
After identifying issues via trace analysis, use standard tools:
```python
# DON'T create code generation tools
# DO use Edit directly:
# Edit(file_path="...", old_string="...", new_string="...")
```

### Use MCP for database validation
```python
# DON'T create database wrapper tools
# DO use MCP directly:
# mcp__supabase__execute_sql(query="SELECT * FROM products WHERE ...")
```

### Production Data Reconstruction & Trace Correlation
**Capability**: Recreate test scenarios from real production user data. Link LangSmith traces to database records.

**Correlation**: `trace_id` = `tracking_id` (set via `run_id` in config)
- Query DB by `trace_id` → get business outcome
- Query LangSmith by `trace_id` → get technical metrics
- Query by `thread_id` → get all phases of a conversation

**HITL Workflow = 3 Records**:
1. Initial PM execution (`status: pending_hitl`)
2. Approval analyzer (`type: approval_analysis`)
3. Resume PM execution (`status: completed`)

**Query Examples**:
```sql
-- Get all phases by thread_id
SELECT tracking_id, trace_id, result_data->>'type' as type, result_data->>'status' as status
FROM workflow_outcomes WHERE thread_id = '...' ORDER BY created_at

-- Link to LangSmith trace
SELECT * FROM workflow_outcomes WHERE trace_id = '<from_langsmith>'
```

**Key Tables**: workflow_outcomes, checkpoints, products

### Use WebSearch/WebFetch for research
```python
# If error message is unclear, research:
# WebSearch(query="LangChain ToolException best practices")
# WebFetch(url="https://docs.langchain.com/...")
```

---

## Documentation References

**Primary**: `docs/architecture/testing/AUTONOMOUS_TESTING_FRAMEWORK.md`
**Quick Reference**: `docs/architecture/testing/QUICK_REFERENCE.md`
**Tool Specs**: `docs/architecture/testing/TOOL_SPECIFICATIONS.md`

---

## Remember

1. **Always start with execute_scenario()** → Captures trace for analysis
2. **Always run get_trace_overview()** → Only 500 tokens, massive value
3. **Be selective with get_run_details()** → 1,500 tokens per run
4. **Rarely use get_run_messages()** → 5K+ tokens, last resort
5. **Use existing tools for fixes** → Edit, Write, MCP (not custom tools)
6. **Validate fixes iteratively** → Re-run scenarios, compare traces
7. **Track progress** → Use list_recent_tests() for trend analysis

---

## Success Criteria

You are successfully using the framework when:
- ✅ Tests execute programmatically without manual CLI usage
- ✅ Failures are identified via hierarchical trace analysis
- ✅ Token usage is efficient (Level 0 → Level 1 → rarely Level 2)
- ✅ Fixes are validated by re-running scenarios
- ✅ Database state is validated via MCP
- ✅ Progress is tracked and documented
- ✅ You iterate quickly: test → analyze → fix → validate
