---
description: Test AutifyME workflows with AI-powered monitoring. AI (OpenAI) acts as a real user, reads PM messages, responds intelligently, and triggers debug mode when architectural issues are detected.
---

Execute intelligent testing where AI monitors PM behavior and triggers debugging when issues are detected.

## Core Principle

**AI monitors AI, you debug root causes.**

AI (gpt-4.1-nano) acts as a real user:
1. **Reads PM's messages** intelligently
2. **Decides how to respond** based on context
3. **Detects architectural violations** (PM doesn't call save_product_family, gets stuck, repeats itself)
4. **Stops execution** and triggers debug mode for you to investigate

## How It Works

### Step 1: AI Monitors PM

```python
from tests.tools import intelligent_execute_scenario

result = intelligent_execute_scenario(
    scenario_id="Onboard this PET jar 500ml at Rs 30",
    media_path="tests/fixtures/images/PET_CAN_JAR_500ml.jpeg",
    max_turns=10  # Max conversation turns
)
```

### Step 2: AI Makes Decisions

Each turn, AI analyzes PM's output and chooses:

| Action | When | Example |
|--------|------|---------|
| **respond** | PM asks question | PM: "What material?" → AI: "PET plastic" |
| **approve** | PM requests approval | PM: "Please approve..." → AI: "approved" |
| **reject** | Data has issues | PM: "Price: -50" → AI: "rejected" |
| **debug** ⛔ | PM violates architecture | PM: "Complete!" but never called save_product_family |

### Step 3: Debug Triggers

AI stops execution when PM behavior violates architecture:

```
[PM → USER] Product onboarding complete!

[AI] Analyzing PM's messages...
[AI] Decision: debug
[AI] Reasoning: PM says complete but never called save_product_family tool

================================================================================
DEBUG MODE ACTIVATED
================================================================================
Reason: PM completed workflow but never called save_product_family tool

Stopping test for manual debugging...
```

**Common triggers:**
- PM says "complete" but didn't call save_product_family
- PM stopped responding (stuck in loop)
- PM repeating itself (infinite loop)
- PM calls specialists but doesn't persist results
- PM asks for approval via text instead of tool

### Step 4: You Investigate Trace

```python
if not result.success:
    print(f"Debug triggered: {result.errors[0]}")
    print(f"Trace: {result.trace_url}")

    # Analyze what PM did
    from tests.tools import get_trace_overview, get_llm_trace_tree

    # Check if PM called persistence tool
    overview = get_trace_overview(result.trace_id)

    # Check PM's reasoning
    llm_tree = get_llm_trace_tree(result.trace_id)
```

### Step 5: Fix Root Cause

**If PM didn't call save_product_family:**
1. Read PM prompt: `agents/src/autifyme_agents/prompts/project_manager.prompt`
2. Check: Does it have explicit tool calling examples?
3. Fix: Add clear example of calling save_product_family
4. Re-test

**If PM got stuck:**
1. Check PM's last messages in trace
2. Identify repeating pattern
3. Fix: Add termination condition
4. Re-test

**If tool configuration issue:**
1. Check: `agents/src/autifyme_agents/workflows/project_manager.py`
2. Verify save_product_family is in pm_tools
3. Verify interrupt_on configuration
4. Re-test

## Example Execution

```bash
# Run intelligent test
uv run python -c "
from tests.tools import intelligent_execute_scenario

result = intelligent_execute_scenario(
    'Onboard PET jar 500ml at Rs 30',
    media_path='tests/fixtures/images/PET_CAN_JAR_500ml.jpeg'
)

print(f'Success: {result.success}')
if not result.success:
    print(f'Debug: {result.errors[0]}')
print(f'Trace: {result.trace_url}')
"
```

## Output Format

**Successful execution:**

```
================================================================================
INTELLIGENT TESTING MODE - AI as Test User (OpenAI gpt-4.1-nano)
================================================================================
Scenario: Onboard this PET jar 500ml at Rs 30
Thread: console:test_5e047675
================================================================================

[USER -> PM] Onboard this PET jar 500ml at Rs 30

[PM -> USER] I'll analyze this product...

[AI] Analyzing PM's messages...
[AI] Decision: respond
[AI] Reasoning: PM is working on analysis, let it continue

[PM -> USER] Product analysis complete! Please approve...

[AI] Analyzing PM's messages...
[AI] Decision: approve
[AI] Reasoning: PM requesting approval with complete data

[USER -> PM] approved

[PM -> USER] [COMPLETION]

================================================================================
Result: SUCCESS
Time: 92.5s
HITL: Yes
Trace: https://smith.langchain.com/...
================================================================================
```

**When debug triggered:**

```
[PM -> USER] Onboarding complete!

[AI] Decision: debug
[AI] Reasoning: PM says complete but never called save_product_family

================================================================================
DEBUG MODE ACTIVATED
================================================================================
Reason: PM completed workflow but never called save_product_family tool

Result: FAILED
Errors:
  - Debug triggered: PM completed workflow but never called save_product_family tool

Trace: https://smith.langchain.com/...
================================================================================
```

## Debug Workflow

```
┌────────────────────────────────────────────────────┐
│ 1. Run intelligent_execute_scenario()              │
│ 2. AI monitors PM, detects issue                   │
│ 3. AI triggers debug → execution stops             │
│ 4. You get ExecutionResult with errors             │
│ 5. You analyze trace:                              │
│    • get_trace_overview() - check tool calls       │
│    • get_llm_trace_tree() - check PM reasoning     │
│ 6. You identify root cause:                        │
│    • Prompt missing tool examples?                 │
│    • Tool not configured?                          │
│    • Architecture violation?                       │
│ 7. You fix issue                                   │
│ 8. You re-test to validate fix                     │
└────────────────────────────────────────────────────┘
```

## API Reference

```python
from tests.tools import intelligent_execute_scenario

def intelligent_execute_scenario(
    scenario_id: str,                    # Scenario text or identifier
    media_path: str | None = None,      # Optional media file path
    max_turns: int = 10,                 # Max conversation turns
) -> ExecutionResult:
    """Execute test with AI as intelligent user.

    Returns ExecutionResult with:
        - success: bool
        - errors: list[str]              # Debug reasons if failed
        - trace_id: str
        - trace_url: str
        - interrupt_occurred: bool
        - products_created: int
        - execution_time_seconds: float
        - thread_id: str
    """
```

## Testing Patterns

### Pattern 1: Test After PM Prompt Changes

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

### Pattern 2: Test Multiple Scenarios

```python
scenarios = [
    ("Single product", "tests/fixtures/images/jar.jpg"),
    ("No image", None),
    ("Different product", "tests/fixtures/images/bottle.jpg"),
]

for name, media in scenarios:
    result = intelligent_execute_scenario(name, media_path=media)
    print(f"{name}: {'PASS' if result.success else 'FAIL'}")
    if not result.success:
        print(f"  Debug: {result.errors[0]}")
```

### Pattern 3: Debug & Fix Workflow

```python
# 1. Test
result = intelligent_execute_scenario("Onboard product")

# 2. If debug triggered
if not result.success:
    # 3. Analyze
    overview = get_trace_overview(result.trace_id)
    llm_tree = get_llm_trace_tree(result.trace_id)

    # 4. Fix root cause
    # 5. Re-test
    result2 = intelligent_execute_scenario("Onboard product")
    assert result2.success
```

### Pattern 4: Validate Database

```python
result = intelligent_execute_scenario("Onboard product")

if result.success:
    # Verify persistence
    products = mcp__supabase__execute_sql(f"""
        SELECT * FROM products
        WHERE thread_id = '{result.thread_id}'
    """)
    assert len(products) > 0, "Product not persisted!"
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ INTELLIGENT TESTING ARCHITECTURE                     │
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
│  AI detects violations → Triggers debug → You fix   │
└─────────────────────────────────────────────────────┘
```

## Requirements

- **OpenAI API Key** must be set in `.env` (OPENAI_API_KEY)
- Uses **gpt-4.1-nano** for AI test user (fast & cheap)
- PM uses gpt-4-turbo-mini (same API key)

## Token Usage

- **AI Test User**: ~500 tokens per decision
- **PM Agent**: Normal workflow tokens (~15-20k)
- **Total**: Similar cost, but with intelligence

## Success Criteria

**Test succeeds when:**
- PM calls save_product_family (triggers HITL)
- AI (user) approves
- Product persists to database
- No errors in execution

**Test fails (debug triggered) when:**
- PM doesn't call save_product_family
- PM gets stuck or repeats
- PM behavior violates architecture
- Tools not configured correctly

---

**This is autonomous testing: AI monitoring AI, with you debugging when architectural issues arise.**
