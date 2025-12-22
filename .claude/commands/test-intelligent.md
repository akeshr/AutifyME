# Test PM Workflow

Execute intelligent testing where you interact with PM, evaluate responses, and fix issues.

## Arguments

- `$ARGUMENTS` - Test scenario (required). Can be:
  - A user request: `"Catalog these sneakers for $79.99"`
  - A request with media: `"Catalog this product" --media test_images/sneaker.jpg`
  - Just `run` to use a default cataloging scenario

## Workflow

### Phase 1: Test (autonomous-testing skill)

1. **Invoke the autonomous-testing skill** to load testing context
2. **Execute test** using `chat_with_pm()`:
   ```python
   from tests.tools import chat_with_pm
   result = chat_with_pm(message="<scenario>", media_path="<if provided>")
   ```
3. **Evaluate each response** for:
   - Intent understanding
   - Routing decision
   - Response quality
   - HITL compliance
4. **Continue conversation** naturally until workflow completes or issues detected

### Phase 2: Evaluate (if issues detected)

If `result.error` or unexpected behavior:

1. **Invoke the workflow-evaluation skill** to load evaluation context
2. **Analyze trace** using hierarchical approach:
   ```python
   from tests.tools import get_trace_overview, get_llm_trace_tree
   overview = get_trace_overview(result.trace_id)
   llm_tree = get_llm_trace_tree(result.trace_id)
   ```
3. **Identify root cause** - trace from symptom to actual cause

### Phase 3: Improve (if fix needed)

If root cause identified:

1. **Invoke agent-improvement skill** for diagnosis if agent underperforming
2. **Invoke prompt-engineering skill** if prompt changes needed
3. **Implement fix** with specific file:line references

### Phase 4: Retest

1. **Re-run same scenario** with `chat_with_pm()`
2. **Verify fix** - compare behavior before/after
3. **Report results** - pass/fail, what changed

## Skill Invocation Guide

| Situation | Skill to Invoke |
|-----------|-----------------|
| Starting test | `autonomous-testing` |
| Deep trace analysis | `workflow-evaluation` |
| Agent not performing well | `agent-improvement` |
| Prompt needs update | `prompt-engineering` |

## Output

Report with:
1. **Test Execution** - Scenario, turns, final status
2. **Issues Found** - Any problems detected with evidence
3. **Root Cause** - If issues, what caused them
4. **Fix Applied** - What was changed (file:line)
5. **Retest Result** - Verification that fix worked
