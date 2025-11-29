---
name: autonomous-testing
description: Execute autonomous testing where AI monitors PM behavior and triggers debugging when issues arise
---

# Autonomous Testing

## Your Role

**AI monitors AI, you debug root causes.**

AI (gpt-4.1-nano) acts as real user, reads PM messages, responds contextually (answers questions, approves/rejects), and triggers debug mode when PM violates architecture (doesn't call save_product_family, gets stuck, repeats).

## Workflow

**1. Execute Test**
```python
from tests.tools import intelligent_execute_scenario

result = intelligent_execute_scenario(
    scenario_id="user scenario or request",
    media_path="path/to/image.jpg",  # optional
    max_turns=10
)
```

**2. Check Result**
```python
if result.success:
    print(f"Success in {result.execution_time_seconds}s")
    print(f"HITL: {result.interrupt_occurred}")
    print(f"Trace: {result.trace_url}")
else:
    print(f"Debug triggered: {result.errors[0]}")
    print(f"Trace: {result.trace_url}")
    # Proceed to analysis
```

**3. Analyze Trace (When Debug Triggered)**

Always start with Level 0 (overview), then drill Level 1 (details) only for failures:

```python
from tests.tools import get_trace_overview, get_llm_trace_tree

# Level 0: Check tool calls (~500 tokens)
overview = get_trace_overview(result.trace_id)

def find_tool(node, tool_name):
    if tool_name in node.name:
        return True
    return any(find_tool(c, tool_name) for c in node.children)

if not find_tool(overview.run_tree[0], "save_product_family"):
    print("Root cause: PM never called save_product_family")

# Level 1: Check PM reasoning (~2-5k tokens)
llm_tree = get_llm_trace_tree(result.trace_id)
for node in llm_tree.llm_tree:
    if "project_manager" in node.agent_name.lower():
        print("PM System Prompt (excerpt):", node.system_prompt[:300])
        print("PM Output:", node.assistant_output)
```

**4. Fix Root Cause**

Common issues:
- **PM didn't call save_product_family**: Update PM prompt with explicit tool calling example
- **PM stuck in loop**: Add termination condition to PM prompt
- **Tool configuration issue**: Verify save_product_family in pm_tools, check interrupt_on config

**5. Validate Fix**

Re-run same test after fix:
```python
result2 = intelligent_execute_scenario(scenario_id, media_path)
assert result2.success, f"Still failing: {result2.errors}"
assert result2.interrupt_occurred, "PM should trigger HITL"
```

## Available Tools

- `intelligent_execute_scenario(scenario_id, media_path, max_turns)` - Execute test with AI monitoring
- `get_trace_overview(trace_id)` - Level 0: Check tool calls, failures (~500 tokens)
- `get_llm_trace_tree(trace_id)` - Level 1: LLM reasoning, prompts (~2-5k tokens)
- `get_run_details(run_id)` - Level 1: Drill into specific run (~1,500 tokens)
- `get_workflow_story(trace_ids)` - Multi-trace analysis (~500 tokens/trace)
- `list_recent_tests(limit)` - Test execution history

## Success Criteria

✅ Always start with `get_trace_overview()` before drilling deeper
✅ When debug triggered, analyze trace → identify root cause → fix → re-test
✅ Validate database persistence with Supabase MCP after successful tests
✅ Track progress with `list_recent_tests()`

## References

- **Architecture**: `docs/architecture/testing/AUTONOMOUS_TESTING_FRAMEWORK.md`
- **Implementation**: `tests/tools/intelligent_execution.py`
