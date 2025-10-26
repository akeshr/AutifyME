# Autonomous Testing Framework Skill

You are Claude, orchestrating autonomous testing of the AutifyME agentic system using **intelligent AI-powered monitoring**.

## Core Principle

**AI monitors AI, you debug root causes.**

```
┌─────────────────────────────────────────────────────┐
│ TESTING ARCHITECTURE                                 │
│                                                      │
│  ┌──────────────┐         ┌──────────────┐         │
│  │ You (Claude) │────────▶│ AI Test User │         │
│  │              │         │ (gpt-4.1-nano)│         │
│  └──────────────┘         └──────┬───────┘         │
│                                  │                  │
│                           Monitors & Decides        │
│                                  │                  │
│                           ┌──────▼───────┐         │
│                           │  PM Agent    │         │
│                           │ (gpt-4-mini) │         │
│                           └──────────────┘         │
│                                                      │
│  AI reads PM messages → Detects issues → Triggers   │
│  debug → You analyze trace → Fix root cause         │
└─────────────────────────────────────────────────────┘
```

**Flow:**
1. You invoke intelligent testing
2. AI (gpt-4.1-nano) acts as real user
3. AI reads EVERY PM message
4. AI decides: respond | approve | reject | **debug**
5. When debug triggered → execution stops
6. You analyze trace with hierarchical tools
7. You identify root cause
8. You fix (prompt/tool/architecture)
9. You re-test to validate

---

## How Intelligent Testing Works

### Step 1: Invoke Test

```python
from tests.tools import intelligent_execute_scenario

result = intelligent_execute_scenario(
    scenario_id="Onboard this PET jar 500ml at Rs 30",
    media_path="tests/fixtures/images/PET_CAN_JAR_500ml.jpeg",
    max_turns=10  # Max conversation turns before timeout
)
```

**What happens:**
- PM starts executing workflow
- AI monitors PM's messages in real-time
- Each turn, AI analyzes PM's output
- AI decides how to respond (see Decision Criteria below)
- If PM behavior violates architecture → AI triggers debug
- Execution stops, returns debug reason to you

### Step 2: AI Decision Criteria

Each conversation turn, AI chooses one action:

| Action | When | Example |
|--------|------|---------|
| **respond** | PM asks question | PM: "What material?" → AI: "PET plastic" |
| **approve** | PM requests approval | PM: "Please approve..." → AI: "approved" |
| **reject** | Data has clear issues | PM: "Price: -50" → AI: "rejected - negative price" |
| **debug** ⛔ | PM violates architecture | PM: "Complete!" but never called save_product_family |

### Step 3: Debug Triggers

AI stops execution and triggers debug when:

1. **PM says "complete" but didn't call `save_product_family`**
   - Why: PM thinks workflow is done without persistence
   - Root cause: Prompt doesn't emphasize tool calling

2. **PM stopped responding (silence for 2+ turns)**
   - Why: PM stuck in loop or waiting incorrectly
   - Root cause: Decision loop with no termination

3. **PM repeating itself**
   - Why: Infinite loop in reasoning
   - Root cause: Prompt logic issue

4. **PM calls specialists but doesn't persist results**
   - Why: PM doesn't know persistence is final step
   - Root cause: Prompt missing persistence examples

5. **PM asks for approval via text instead of tool**
   - Why: PM doesn't know about save_product_family tool
   - Root cause: Tool not configured or not in prompt

### Step 4: Check Result

```python
if result.success:
    print(f"✓ Workflow succeeded in {result.execution_time_seconds}s")
    print(f"  HITL occurred: {result.interrupt_occurred}")
    print(f"  Products created: {result.products_created}")
    print(f"  Trace: {result.trace_url}")

else:
    print(f"✗ Debug triggered: {result.errors[0]}")
    print(f"  Trace: {result.trace_url}")
    # AI detected architectural issue → investigate
```

### Step 5: Analyze Trace (When Debug Triggered)

```python
from tests.tools import get_trace_overview, get_llm_trace_tree

# Level 0: Overview - Check if PM called persistence tool
overview = get_trace_overview(result.trace_id)

def find_tool_call(node, tool_name):
    """Recursively search for tool in run tree."""
    if tool_name in node.name:
        return True
    for child in node.children:
        if find_tool_call(child, tool_name):
            return True
    return False

if not find_tool_call(overview.run_tree[0], "save_product_family"):
    print("Root cause: PM never called save_product_family")

# Level 1: LLM Reasoning - Check PM's decision-making
llm_tree = get_llm_trace_tree(result.trace_id)

for node in llm_tree.llm_tree:
    if "project_manager" in node.agent_name.lower():
        print(f"PM System Prompt (first 500 chars):")
        print(node.system_prompt[:500])
        print(f"\nPM Output:")
        print(node.assistant_output)
        # Check if PM's output mentions save_product_family
```

### Step 6: Fix Root Cause

**If PM didn't call save_product_family:**
```
1. Read PM prompt: agents/src/autifyme_agents/prompts/project_manager.prompt
2. Check: Does it have explicit tool calling examples?
3. Check: Does it show save_product_family being called?
4. Fix: Add clear example of calling save_product_family after specialists complete
5. Re-test
```

**If PM got stuck in loop:**
```
1. Check PM's last message in llm_tree
2. Identify repeating pattern
3. Fix: Add termination condition in prompt
4. Re-test
```

**If tool configuration issue:**
```
1. Check: agents/src/autifyme_agents/workflows/project_manager.py
2. Verify save_product_family is in pm_tools list
3. Verify interrupt_on configuration includes save_product_family
4. Re-test
```

### Step 7: Validate Fix

```python
# Run same test again after fix
result2 = intelligent_execute_scenario(
    "Onboard this PET jar 500ml at Rs 30",
    media_path="tests/fixtures/images/PET_CAN_JAR_500ml.jpeg"
)

assert result2.success, f"Still failing: {result2.errors}"
assert result2.interrupt_occurred, "PM should trigger HITL"
print("✓ Fix validated!")
```

---

## Available Tools

### Primary Testing Tool

#### `intelligent_execute_scenario(scenario_id, media_path, max_turns)`

```python
from tests.tools import intelligent_execute_scenario

result = intelligent_execute_scenario(
    scenario_id="Onboard PET jar 500ml at Rs 30",
    media_path="tests/fixtures/images/jar.jpg",
    max_turns=10
)
```

**Returns `ExecutionResult` with:**
- `success: bool` - True if workflow completed without debug trigger
- `interrupt_occurred: bool` - True if PM triggered HITL
- `products_created: int` - Number of products persisted
- `execution_time_seconds: float` - Total execution time
- `trace_id: str` - For trace analysis
- `trace_url: str` - LangSmith link
- `thread_id: str` - Database correlation
- `errors: list[str]` - Debug reasons if failed

**When debug triggered:**
- `success = False`
- `errors[0]` contains specific issue detected by AI
- Example: "PM completed workflow but never called save_product_family tool"

**Requirements:**
- OpenAI API key (OPENAI_API_KEY in .env)
- Uses gpt-4.1-nano for AI test user

---

### Trace Analysis Tools

#### `get_trace_overview(trace_id)` - Level 0 (~500 tokens)

```python
from tests.tools import get_trace_overview

overview = get_trace_overview(result.trace_id)
```

**Returns `TraceOverview` with:**
- `trace_id: str`
- `total_runs: int`
- `total_cost: float`
- `total_latency_ms: int`
- `run_tree: list[RunNode]` - Hierarchical tree

**Each `RunNode` has:**
- `run_id: str` - For drilling down with get_run_details()
- `name: str` - "PM" | "product_specialist" | "save_product_family"
- `run_type: str` - "chain" | "llm" | "tool"
- `status: str` - "success" | "error"
- `duration_ms: int`
- `error: str | None`
- `children: list[RunNode]` - Recursive tree structure

**Use when:** ALWAYS after test execution. Identifies missing tool calls, failures, slow runs.

**Example - Find missing tool:**
```python
def find_tool(node, tool_name):
    if tool_name in node.name:
        return True
    for child in node.children:
        if find_tool(child, tool_name):
            return True
    return False

if not find_tool(overview.run_tree[0], "save_product_family"):
    print("PM never called save_product_family!")
```

---

#### `get_llm_trace_tree(trace_id)` - LLM Only (~2-5k tokens)

```python
from tests.tools import get_llm_trace_tree

llm_tree = get_llm_trace_tree(result.trace_id)
```

**Returns `LLMTraceTree` with:**
- `trace_id: str`
- `total_llm_calls: int`
- `total_tokens: int`
- `total_cost: float`
- `llm_tree: list[LLMCallNode]` - Hierarchical LLM calls ONLY

**Each `LLMCallNode` has:**
- `run_id: str`
- `agent_name: str` - "project_manager" | "product_specialist"
- `hierarchy_level: str` - "orchestrator" | "specialist"
- `system_prompt: str` - Full system prompt
- `user_messages: list[dict]` - All user/context messages
- `assistant_output: dict` - LLM response
- `model: str` - "gpt-4o-mini"
- `total_tokens: int`
- `status: str`
- `error: str | None`
- `children: list[LLMCallNode]` - Nested LLM calls

**Use when:** Understanding PM reasoning, analyzing prompts, debugging LLM decisions.

**Example - Check PM reasoning:**
```python
for node in llm_tree.llm_tree:
    if "project_manager" in node.agent_name.lower():
        print("PM System Prompt:")
        print(node.system_prompt[:500])
        print("\nPM Output:")
        print(node.assistant_output)
```

---

#### `get_run_details(run_id)` - Level 1 (~1,500 tokens)

```python
from tests.tools import get_run_details

details = get_run_details(failed_node.run_id)
```

**Returns `RunDetails` with:**
- `run_id: str`
- `name: str`
- `run_type: str`
- `inputs: dict` - Full inputs
- `outputs: dict | None` - Full outputs if successful
- `error: str | None` - Full error with traceback
- `metadata: RunMetadata` - Model, tokens, latency

**Use when:** After Level 0 identifies failure. Drill into specific failed runs.

---

#### `get_run_messages(run_id)` - Level 2 (~5K+ tokens, RARE)

```python
from tests.tools import get_run_messages

messages = get_run_messages(llm_run_id)
```

**Returns `RunMessages` with:**
- `run_id: str`
- `messages: list[Message]` - Full LLM conversation

**Use when:** ONLY when root cause unclear from Level 0 + 1. Full conversation is expensive.

---

#### `get_workflow_story(trace_ids)` - Multi-trace (~500 tokens/trace)

```python
from tests.tools import get_workflow_story

story = get_workflow_story([trace1, trace2, trace3])
```

**Returns `WorkflowStory` with:**
- `thread_id: str`
- `total_traces: int`
- `traces: list[WorkflowTrace]`
- `products_extracted: int`
- `products_saved: int`
- `products_edited: int`
- `products_rejected: int`
- `total_cost: float`
- `total_latency_ms: int`

**Use when:** Analyzing complete HITL workflows spanning multiple traces (initial → interrupt → resume).

---

#### `list_recent_tests(limit)` - Test History

```python
from tests.tools import list_recent_tests

history = list_recent_tests(limit=10)
```

**Returns `TestHistory` with:**
- `tests: list[TestExecution]`
  - `timestamp: datetime`
  - `scenario_id: str`
  - `success: bool`
  - `trace_url: str`
  - `execution_time_seconds: float`
  - `errors_summary: str`

**Use when:** Track testing progress, identify trends, compare execution times.

---

## Testing Patterns

### Pattern 1: Test PM Prompt After Changes

```python
# After updating PM prompt
result = intelligent_execute_scenario(
    "Onboard PET jar 500ml at Rs 30",
    media_path="tests/fixtures/images/jar.jpg"
)

# Validate PM behavior
assert result.interrupt_occurred, "PM should trigger HITL"
assert result.success, f"Debug triggered: {result.errors}"
```

---

### Pattern 2: Debug Failing Workflow

```python
# 1. Run test
result = intelligent_execute_scenario("Onboard product")

# 2. Check if debug triggered
if not result.success:
    print(f"Debug: {result.errors[0]}")

    # 3. Analyze PM behavior
    overview = get_trace_overview(result.trace_id)

    # 4. Check for save_product_family
    def has_tool(node, tool):
        if tool in node.name:
            return True
        return any(has_tool(c, tool) for c in node.children)

    if not has_tool(overview.run_tree[0], "save_product_family"):
        # 5. Investigate PM prompt
        llm_tree = get_llm_trace_tree(result.trace_id)

        # 6. Fix prompt
        # 7. Re-test
```

---

### Pattern 3: Test Multiple Scenarios

```python
scenarios = [
    ("Single product", "tests/fixtures/images/jar.jpg"),
    ("No image", None),
    ("Different product", "tests/fixtures/images/bottle.jpg"),
]

results = []
for name, media in scenarios:
    result = intelligent_execute_scenario(name, media_path=media)
    results.append((name, result.success, result.errors))
    print(f"{name}: {'PASS' if result.success else 'FAIL'}")

# Analyze failures
for name, success, errors in results:
    if not success:
        print(f"\n{name} failed:")
        print(f"  Reason: {errors[0]}")
```

---

### Pattern 4: Validate Database Persistence

```python
result = intelligent_execute_scenario("Onboard product")

if result.success and result.interrupt_occurred:
    # Query database
    products = mcp__supabase__execute_sql(f"""
        SELECT * FROM products
        WHERE thread_id = '{result.thread_id}'
    """)

    assert len(products) > 0, "Product not persisted!"
    print(f"✓ Persisted: {products[0]['name']}")
```

---

## Hierarchical Trace Analysis

**Token Efficiency Strategy:**

```
┌─────────────────────────────────────────────────┐
│ Level 0: Overview (~500 tokens)                 │
│ ├─ Check run tree structure                    │
│ ├─ Identify failures                           │
│ └─ Find missing tool calls                     │
│                                                  │
│ Level 1: Details (~1,500 tokens per run)       │
│ ├─ Drill into specific failures                │
│ └─ Examine inputs/outputs/errors               │
│                                                  │
│ Level 2: Messages (~5K+ tokens, RARE)          │
│ └─ Full LLM conversation for mysteries         │
└─────────────────────────────────────────────────┘
```

**Example:** Trace with 20 runs
- Naive approach: Load all = 50K tokens
- Hierarchical: L0 (500) + L1 for 2 failures (3K) = 3.5K tokens
- **Savings: 93%**

**Rule:** Always start Level 0 → drill Level 1 only for failures → use Level 2 sparingly.

---

## Common Debug Scenarios

### Scenario 1: PM Never Calls save_product_family

**Debug trigger:**
```
Debug triggered: PM completed workflow but never called save_product_family tool
```

**Investigation:**
```python
# Check if tool exists in run tree
overview = get_trace_overview(result.trace_id)
# Result: save_product_family NOT in tree

# Check PM's reasoning
llm_tree = get_llm_trace_tree(result.trace_id)
pm_node = [n for n in llm_tree.llm_tree if "project_manager" in n.agent_name.lower()][0]

# Inspect prompt
print(pm_node.system_prompt)
# Finding: No mention of save_product_family
```

**Fix:**
```
Update PM prompt with explicit tool calling example:
"After all specialists complete, call save_product_family(data=...)"
```

---

### Scenario 2: PM Stuck in Loop

**Debug trigger:**
```
Debug triggered: PM stopped responding
```

**Investigation:**
```python
llm_tree = get_llm_trace_tree(result.trace_id)

# Check PM's last outputs
pm_nodes = [n for n in llm_tree.llm_tree if "project_manager" in n.agent_name.lower()]
for node in pm_nodes[-3:]:  # Last 3
    print(node.assistant_output)
# Finding: PM asking same question repeatedly
```

**Fix:**
```
Add termination condition in PM prompt
```

---

### Scenario 3: Tool Error

**Debug trigger:**
```
NotImplementedError: StructuredTool does not support sync invocation
```

**Investigation:**
```python
overview = get_trace_overview(result.trace_id)

def find_errors(node):
    if node.status == "error":
        print(f"Failed: {node.name}")
        details = get_run_details(node.run_id)
        print(details.error)
```

**Fix:**
```
Check tool configuration for async/sync mismatch
```

---

## Success Criteria

You're using the framework correctly when:

✅ You run `intelligent_execute_scenario()` for all PM validation
✅ AI triggers debug → you analyze trace → you fix root cause
✅ You always start with `get_trace_overview()` (Level 0)
✅ You drill to `get_run_details()` (Level 1) only for failures
✅ You rarely use `get_run_messages()` (Level 2)
✅ You validate fixes by re-running tests
✅ You track progress with `list_recent_tests()`
✅ Database persistence is validated with Supabase MCP

---

## Remember

**Core paradigm:**
```
AI monitors AI → detects violations → triggers debug → you fix
```

**Workflow:**
```
1. intelligent_execute_scenario()
2. AI monitors PM in real-time
3. Debug triggered? → analyze trace
4. Fix root cause (prompt/tool/architecture)
5. Re-test to validate
```

**You are the debugging expert. The AI is your intelligent test user who watches PM and tells you when something is architecturally wrong.**

---

## Documentation References

- **Command:** `.claude/commands/test-intelligent.md`
- **Agent:** `.claude/agents/workflow-tester.md`
- **Implementation:** `tests/tools/intelligent_execution.py`
- **Architecture:** `docs/architecture/testing/AUTONOMOUS_TESTING_FRAMEWORK.md`
