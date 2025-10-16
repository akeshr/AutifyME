# Quick Reference - Autonomous Testing Framework Cheat Sheet

**Date**: 2025-01-16
**Purpose**: Quick reference for common testing workflows and tool usage

---

## Common Commands

### Test Single Scenario
```python
result = execute_scenario("cataloging_with_image", "auto_approve")
if not result.success:
    structure = get_trace_structure(result.trace_id)
    failure = analyze_failure_chain(structure.failed_runs[0])
```

### Test Multiple Scenarios
```python
scenarios = load_scenario_list("cataloging_*")
for scenario_id in scenarios:
    result = execute_scenario(scenario_id, "auto_approve")
    # Analyze results...
```

### Analyze Failure
```python
# Level 0: Overview
structure = get_trace_structure(trace_id)

# Level 1: Focused
if structure.failed_runs:
    failure = analyze_failure_chain(structure.failed_runs[0])
    validation = validate_structured_output(related_run_id, "Product")

# Level 2: Deep Dive (rare)
if not failure.root_cause_clear:
    details = get_full_run_details(failed_run_id)
```

### Check Database
```python
# Quick check
check = quick_db_check("cataloging_with_image")

# Get details
if not check.matches_expected:
    result = get_product_record(scenario_id="cataloging_with_image")
```

### Generate & Apply Fix
```python
# Generate
improvement = generate_prompt_improvement(
    issue_description="Specialist returns price as string",
    current_prompt=read_file("..."),
    trace_examples=["run_id"]
)

# Apply
result = apply_improvement("prompt", target_file, improvement.proposed_prompt)

# Validate
new_result = execute_scenario(scenario_id)
comparison = compare_execution_metrics(baseline, new_result)
```

---

## Tool Categories

### Execution (2 tools)
- `execute_scenario` - Run single scenario
- `execute_conversation` - Run multi-turn conversation

### Analysis - Level 0 (3 tools)
- `get_trace_structure` - Lightweight overview (~500 tokens)
- `get_scenario_outcome` - High-level result
- `quick_db_check` - Fast DB validation

### Analysis - Level 1 (4 tools)
- `analyze_failure_chain` - Focused failure analysis (~1,500 tokens)
- `validate_structured_output` - Schema compliance
- `get_product_record` - DB record details
- `analyze_decision_point` - PM/dept routing validation

### Analysis - Level 2 (3 tools)
- `get_full_run_details` - Complete run data (expensive)
- `trace_data_lineage` - Track data transformations
- `compare_traces` - Side-by-side comparison

### Improvement (4 tools)
- `generate_prompt_improvement` - Fix prompts
- `generate_code_fix` - Fix code
- `apply_improvement` - Apply changes
- `compare_execution_metrics` - Validate improvements

### Helpers (4 tools)
- `load_scenario_list` - Get scenarios by pattern
- `select_next_scenario` - Priority queue selection
- `generate_iteration_report` - Formatted reports
- `track_improvement_history` - Log changes

---

## Decision Tree

```
execute_scenario()
    ↓
Success?
    ├─ YES → quick_db_check() → All good? → ✅ DONE
    │                         → Issue? → Level 1 Analysis
    │
    └─ NO → get_trace_structure()
              ↓
          Identify failed_runs
              ↓
          For each: analyze_failure_chain()
              ↓
          Root cause clear?
              ├─ YES → generate_improvement() → ✅ DONE
              │
              └─ NO → Level 2 Deep Dive
                      ↓
                  get_full_run_details()
                      ↓
                  Manual analysis → ✅ DONE
```

---

## Token Budgets

| Analysis Level | Token Cost | When to Use |
|----------------|------------|-------------|
| Level 0 | ~500 | Always (first step) |
| Level 1 | ~1,500 | If issues detected |
| Level 2 | ~5,000+ | If root cause unclear |

**Target**: 90% of analyses stay at Level 0-1 (< 2,000 tokens)

---

## Common Issue Patterns

### ValidationError: Type Mismatch
**Symptom**: "price must be float, got str"
**Cause**: Specialist returns wrong type
**Fix**: Add type emphasis to prompt
**Tool**: `validate_structured_output()`

### Missing DB Record
**Symptom**: Scenario passes but no DB record
**Cause**: save_product not called or failed silently
**Fix**: Check delegation logic
**Tool**: `quick_db_check()` + `get_trace_structure()`

### Context Leakage
**Symptom**: Excessive token usage (10K+)
**Cause**: Full history passed to specialist
**Fix**: Add context engineering to prompt + code
**Tool**: `get_full_run_details()` to inspect inputs

### Multi-Turn Context Loss
**Symptom**: Info from turn 1 lost by turn 3
**Cause**: State not preserved across turns
**Fix**: Update department state management
**Tool**: `trace_data_lineage()`

---

## Validation Checklist

After applying improvement:
- [ ] Re-test affected scenario(s)
- [ ] Compare metrics (success rate, latency, cost)
- [ ] Check DB records created
- [ ] Test passing scenarios (regression check)
- [ ] Review comparison.recommendation
- [ ] Keep if improved, revert if worse

---

## Risk Levels

| Risk | Examples | Approval |
|------|----------|----------|
| Low | Prompt additions, error handling | Auto-apply OK |
| Medium | Prompt removals, logic changes | Review recommended |
| High | Multi-component, architecture | Always review |

---

## Quick Workflows

### Single Scenario Analysis (2-5 min)
1. `execute_scenario()`
2. `get_trace_structure()` if failed
3. `analyze_failure_chain()` for details
4. `validate_structured_output()` or `quick_db_check()`
5. Report findings

### Batch Testing (10-30 min)
1. `load_scenario_list(pattern)`
2. Loop: `execute_scenario()` for each
3. Aggregate results
4. Deep analysis on failures
5. Report summary

### Fix & Validate (3-10 min)
1. `generate_prompt_improvement()` or `generate_code_fix()`
2. Present to user
3. `apply_improvement()`
4. `execute_scenario()` to retest
5. `compare_execution_metrics()`
6. KEEP or REVERT

---

## MCP Tools (Supabase)

ALL DB operations use Supabase MCP:
```python
# Execute SQL
result = mcp__supabase__execute_sql("SELECT * FROM products ...")

# List tables
tables = mcp__supabase__list_tables(schemas=["public"])

# Get advisors (security/performance)
advisors = mcp__supabase__get_advisors(type="security")
```

---

## Key Files

### Tools Implementation
- `tests/tools/execution_tools.py`
- `tests/tools/trace_analysis_tools.py`
- `tests/tools/database_validation_tools.py`
- `tests/tools/improvement_tools.py`

### Documentation
- `AUTONOMOUS_TESTING_FRAMEWORK.md` - Main framework
- `HIERARCHICAL_TRACE_ANALYSIS.md` - Analysis strategy
- `TOOL_SPECIFICATIONS.md` - API reference
- `WORKFLOW_PATTERNS.md` - Detailed examples
- `IMPROVEMENT_METHODOLOGY.md` - Fix strategies

---

## Common Mistakes to Avoid

❌ **Don't fetch full traces upfront** - Start with Level 0
❌ **Don't analyze successful runs** - Focus on failures
❌ **Don't write raw SQL** - Use MCP tools
❌ **Don't skip validation** - Always retest after fix
❌ **Don't batch improvements** - Apply one at a time

✅ **Do use hierarchical analysis** - Save tokens
✅ **Do explain reasoning** - Show evidence
✅ **Do track improvements** - Log all changes
✅ **Do check regressions** - Test passing scenarios
✅ **Do create backups** - Always before applying

---

## Support

- **Full Framework**: [AUTONOMOUS_TESTING_FRAMEWORK.md](./AUTONOMOUS_TESTING_FRAMEWORK.md)
- **Tool Reference**: [TOOL_SPECIFICATIONS.md](./TOOL_SPECIFICATIONS.md)
- **Workflow Examples**: [WORKFLOW_PATTERNS.md](./WORKFLOW_PATTERNS.md)
- **Fix Strategies**: [IMPROVEMENT_METHODOLOGY.md](./IMPROVEMENT_METHODOLOGY.md)

---

**Last Updated**: 2025-01-16
