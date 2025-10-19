# Autonomous Testing Framework - Quick Reference

**Date**: 2025-10-17 | **For**: Claude (Jarvis)

---

## Core Philosophy

**Tools provide visibility, Claude provides intelligence.**

- Framework gives you information-gathering tools (5 total)
- You use existing tools (Edit, Write, Read, MCP) for analysis and fixes
- Focus on hierarchical observation to save 25x tokens

---

## 5 Essential Tools

```python
# 1. Execute test
execute_scenario("cataloging_with_image", "auto_approve", "sneakers.jpg")
→ ExecutionResult (success, trace_id, products_created, errors)

# 2. Level 0: Get trace structure (~500 tokens)
get_trace_overview(trace_id)
→ TraceOverview (run tree, identify failures)

# 3. Level 1: Get run details (~1,500 tokens)
get_run_details(failed_run_id)
→ RunDetails (inputs, outputs, error)

# 4. Level 2: Get full messages (~5K+ tokens, rare)
get_run_messages(run_id)
→ RunMessages (full conversation)

# 5. List test history
list_recent_tests(limit=10)
→ TestHistory (recent executions for comparison)
```

---

## Standard Workflow

```
1. EXECUTE
   result = execute_scenario("cataloging_with_image", "auto_approve")

2. OBSERVE (Level 0)
   overview = get_trace_overview(result.trace_id)
   # Identify which runs failed

3. INVESTIGATE (Level 1)
   for failed_run_id in overview.failed_runs:
       details = get_run_details(failed_run_id)
       # Analyze error, inputs, outputs

4. ANALYZE (Your Reasoning)
   "save_product failed with ValidationError: price must be float.
    Cataloging specialist returned price as string.
    This is a prompt issue - needs type emphasis."

5. FIX (Existing Tools)
   Read: prompts/cataloging_specialist.prompt
   Edit: Add type requirements section

6. VALIDATE
   result2 = execute_scenario("cataloging_with_image", "auto_approve")
   # Compare: Success rate 0% → 100%
```

---

## Decision Tree

```
execute_scenario()
    ↓
get_trace_overview() [~500 tokens]
    ↓
Success?
    ├─ YES → Validate DB with mcp__supabase__execute_sql
    │        All good? DONE
    │
    └─ NO → get_run_details(failed_run_id) [~1,500 tokens]
              ↓
          Root cause clear?
              ├─ YES → Fix with Edit/Write → DONE
              └─ NO → get_run_messages(run_id) [~5K tokens]
                      Deep investigation → Fix
```

---

## Token Budgets

| Analysis Level | Tokens | When |
|----------------|--------|------|
| Level 0 | ~500 | Always start here |
| Level 1 | ~1,500 | Drill into failures |
| Level 2 | ~5,000+ | Complex reasoning bugs only |

**Target**: < 3K tokens per scenario (90% stay at Level 0+1)
**Savings**: 25x vs full dump (50K → 2K)

---

## Common Commands

### Execute Tests

```python
# Single test
result = execute_scenario("cataloging_with_image", "auto_approve")

# With media
result = execute_scenario(
    scenario_id="cataloging_with_image",
    hitl_mode="auto_approve",
    media_path="tests/fixtures/images/sneakers.jpg"
)

# Custom prompt
result = execute_scenario("Catalog blue jeans for $49", "auto_approve")
```

### Analyze Traces

```python
# Level 0: Overview
overview = get_trace_overview(trace_id)

# Find failures
failed_ids = []
for node in overview.run_tree:
    if node.status == "error":
        failed_ids.append(node.run_id)

# Level 1: Details
for run_id in failed_ids:
    details = get_run_details(run_id)
    print(f"{details.name}: {details.error}")
```

### Database Validation

```python
# Check record exists
result = mcp__supabase__execute_sql(
    f"SELECT COUNT(*) FROM products WHERE metadata->>'scenario_id' = '{scenario_id}'"
)

# Get full record
result = mcp__supabase__execute_sql(
    f"SELECT * FROM products WHERE metadata->>'scenario_id' = '{scenario_id}'"
)
```

### Fix Issues

```python
# Read current code
current = Read("agents/src/.../cataloging_specialist.prompt")

# Fix prompt
Edit(
    file_path="agents/src/.../cataloging_specialist.prompt",
    old_string="<existing section>",
    new_string="<updated section with type emphasis>"
)

# Validate fix
result = execute_scenario("cataloging_with_image", "auto_approve")
```

### Track Progress

```python
# Recent tests
history = list_recent_tests(limit=20)

for test in history.tests:
    status = "✅" if test.success else "❌"
    print(f"{status} {test.scenario_id} ({test.execution_time_seconds:.1f}s)")

# Compare before/after
baseline = history.tests[-1]  # Oldest
current = history.tests[0]    # Newest
print(f"Improvement: {baseline.success} → {current.success}")
```

---

## Issue Patterns

| Issue Type | Detection | Fix Tool |
|------------|-----------|----------|
| **Prompt** (40%) | Wrong types, missing fields | Edit prompt file |
| **Code** (30%) | Exceptions, KeyErrors | Edit Python code |
| **Architecture** (20%) | Context loss, state bugs | Edit workflow code |
| **Data** (10%) | Schema violations | Edit Pydantic models |

### Prompt Issues

**Symptom**: Agent returns wrong output format
**Detection**: get_run_details() shows type mismatches
**Fix**: Edit prompt to add type emphasis and examples

### Code Issues

**Symptom**: Exceptions in traceback
**Detection**: get_run_details() shows error traceback
**Fix**: Edit code to add error handling and validation

### Architecture Issues

**Symptom**: Multi-turn context loss
**Detection**: get_trace_overview() shows context not flowing
**Fix**: Edit workflow orchestration to fix context injection

---

## Quick Scenarios

### Single Test (2-5 min)

```python
# Execute
result = execute_scenario("cataloging_with_image", "auto_approve")

# Analyze (if failure)
overview = get_trace_overview(result.trace_id)
details = get_run_details(failed_run_id)

# Fix
Read + Edit prompt/code

# Validate
execute_scenario() again
```

### Batch Testing (10-20 min)

```python
scenarios = ["cataloging_basic", "cataloging_with_image", "multi_product"]

for scenario in scenarios:
    result = execute_scenario(scenario, "auto_approve")

# Analyze patterns
history = list_recent_tests(limit=len(scenarios))
# Fix common issues once, validate all benefit
```

### Improvement Validation (3-10 min)

```python
# Before
baseline = execute_scenario("cataloging_with_image", "auto_approve")

# Fix
Edit prompt/code

# After
current = execute_scenario("cataloging_with_image", "auto_approve")

# Compare
if current.success and not baseline.success:
    print("✅ Improvement successful")
else:
    print("❌ Revert or iterate")
```

---

## Success Metrics

**Token Efficiency**:
- Target: < 3K tokens per analysis
- Savings: 25x vs naive approach

**Improvement Velocity**:
- Issue ID: < 5 min
- Fix: < 10 min
- Validation: < 5 min
- **Full cycle**: < 20 min

**System Quality**:
- Success rate: 90%+ on core scenarios
- Regression rate: < 5% after improvements

---

## Key Principles

1. **Information First** - Tools provide data, you provide intelligence
2. **Hierarchical Efficiency** - Always start with Level 0
3. **Use Existing Tools** - Don't reinvent Edit/Write/MCP
4. **Systematic** - Execute → Observe → Analyze → Fix → Validate
5. **Iterate Rapidly** - Small improvements, frequent validation

---

## Related Docs

- `AUTONOMOUS_TESTING_FRAMEWORK.md` - Complete framework
- `TOOL_SPECIFICATIONS.md` - Detailed API reference
- `HIERARCHICAL_TRACE_ANALYSIS.md` - Token optimization strategy
- `LOCAL_TESTING_STRATEGY.md` - CLI tools guide
