# Autonomous Testing Framework

**Status**: Design Complete | **Date**: 2025-10-17
**Purpose**: Enable Claude to orchestrate testing, analysis, and iterative improvement of the AutifyME agentic system

---

## Executive Summary

This framework equips Claude with **information-gathering tools** to execute workflows, observe system behavior through hierarchical trace analysis, and identify issues. Claude then uses existing capabilities (Edit, Write, Read, MCP) to fix problems and validate improvements.

**Core Philosophy**: Tools provide visibility, Claude provides intelligence.

**Key Innovation**: Hierarchical lazy-loading trace analysis reduces token costs 25x (50K → 2K tokens) by fetching structure first, then drilling down selectively.

**Tool Count**: 5 essential observation tools + existing Edit/Write/MCP tools

---

## I. Claude's Role

### What Claude Does

1. **Execute**: Run test scenarios
2. **Observe**: Fetch traces/logs/DB state hierarchically
3. **Analyze**: Identify root causes through reasoning
4. **Fix**: Edit code/prompts using existing tools
5. **Validate**: Re-run tests and compare results

### What Tools Are For

✅ **Testing-specific information gathering** - the capability Claude lacks
❌ NOT for automating Claude's analysis or code changes
❌ NOT for duplicating Edit/Write/MCP functionality

Claude already has powerful tools for code changes and DB queries. This framework focuses exclusively on **observing test executions and trace data**.

---

## II. Core Workflow

```
1. EXECUTE TEST
   execute_scenario("cataloging_with_image", "auto_approve", "sneakers.jpg")
   → Returns: success/failure, trace_url, products_created, errors

2. OBSERVE HIERARCHICALLY
   Level 0: get_trace_overview(trace_id)  [~500 tokens]
   → Full run tree with status, identify failures

   Level 1: get_run_details(failed_run_id)  [~1,500 tokens]
   → Inputs, outputs, error for specific failure

   Level 2: get_run_messages(run_id)  [~5K+ tokens, rare]
   → Full conversation messages (only for complex reasoning bugs)

3. ANALYZE (Claude's Reasoning)
   "save_product failed with ValidationError: price must be float.
   Cataloging specialist returned price as string.
   This is a prompt issue - needs type emphasis."

4. FIX (Existing Tools)
   Read: agents/src/.../cataloging_specialist.prompt
   Edit: Add type requirements section to prompt

5. VALIDATE
   execute_scenario() again
   Compare: Success rate 0% → 100%
   Decision: KEEP fix
```

---

## III. Essential Tools (5 Total)

### 1. execute_scenario(scenario_id, hitl_mode, media_path)

Runs workflow test via simulate.py.

**Returns**: ExecutionResult
```python
{
  "success": bool,
  "thread_id": str,
  "trace_url": str,
  "trace_id": str,
  "products_created": int,
  "execution_time_seconds": float,
  "errors": List[str]
}
```

---

### 2. get_trace_overview(trace_id) - Level 0

Fetches hierarchical structure of entire trace (metadata only, no inputs/outputs).

**Returns**: TraceOverview
```python
{
  "trace_id": str,
  "total_runs": int,
  "total_cost": float,
  "total_latency_ms": int,
  "run_tree": [
    {
      "run_id": str,
      "name": str,  # "PM" / "CatalogingDept" / "ImageAnalysisSpecialist"
      "run_type": "chain" | "llm" | "tool",
      "status": "success" | "error",
      "duration_ms": int,
      "error": Optional[str],  # High-level error message only
      "children": List[RunNode]  # Recursive tree
    }
  ]
}
```

**Token Cost**: ~500 tokens
**Use Case**: Always start here to identify which runs failed

---

### 3. get_run_details(run_id) - Level 1

Fetches specific run's inputs, outputs, and error details.

**Returns**: RunDetails
```python
{
  "run_id": str,
  "name": str,
  "inputs": Dict[str, Any],  # Prompt, tool inputs
  "outputs": Optional[Dict[str, Any]],  # Structured output
  "error": Optional[str],  # Full error message
  "metadata": {
    "model": str,
    "total_tokens": int,
    "latency_ms": int
  }
}
```

**Token Cost**: ~1,500 tokens per run
**Use Case**: Drill into specific failures identified in Level 0

---

### 4. get_run_messages(run_id) - Level 2

Fetches full conversation messages for a run (expensive, rare use).

**Returns**: RunMessages
```python
{
  "run_id": str,
  "messages": [
    {
      "role": "system" | "user" | "assistant",
      "content": str,
      "tool_calls": Optional[List[ToolCall]]
    }
  ]
}
```

**Token Cost**: ~5,000+ tokens
**Use Case**: Only when Level 1 doesn't reveal why agent made wrong decision

---

### 5. list_recent_tests(limit)

Lists recent test executions for progress tracking.

**Returns**: TestHistory
```python
{
  "tests": [
    {
      "timestamp": datetime,
      "scenario_id": str,
      "trace_url": str,
      "success": bool,
      "products_created": int,
      "execution_time_seconds": float
    }
  ]
}
```

**Use Case**: Compare baseline vs improvements across iterations

---

## IV. Existing Tools (Already Available)

**Database Queries**:
- `mcp__supabase__execute_sql(query)` - Query any table
- `mcp__supabase__list_tables()` - See schema
- `mcp__supabase__get_logs(service)` - System logs

**Code Changes**:
- `Read(file_path)` - Understand current code
- `Edit(file_path, old_string, new_string)` - Fix bugs
- `Write(file_path, content)` - Create new files

**Research**:
- `WebFetch(url, prompt)` - Fetch documentation
- `Grep(pattern)` - Search codebase
- `Glob(pattern)` - Find files

---

## V. Hierarchical Analysis Strategy

### Decision Tree

```
execute_scenario()
    ↓
get_trace_overview()  [Level 0: ~500 tokens]
    ↓
Success?
    ↓
    ├─ YES → Quick validation
    │   mcp__supabase__execute_sql("SELECT COUNT(*)...")
    │   All good? → DONE
    │
    └─ NO → Identify failed runs
          get_run_details(failed_run_id)  [Level 1: ~1,500 tokens]
              ↓
          Root cause clear?
              ↓
              ├─ YES → Fix using Edit/Write → DONE
              │
              └─ NO → Deep dive
                    get_run_messages(run_id)  [Level 2: ~5K tokens]
                    Manual inspection → Fix
```

### Token Efficiency

| Analysis Level | Token Cost | When to Use |
|----------------|------------|-------------|
| Level 0 | ~500 | Always start here |
| Level 1 | ~1,500 | Drill into failures |
| Level 2 | ~5,000+ | Complex reasoning bugs only |

**Target**: 90% of analyses stay at Level 0-1 (< 2K tokens)

**Savings**: 25x vs naive full dump (50K → 2K tokens average)

---

## VI. Common Scenarios

### Scenario 1: Single Test Analysis (2-5 min)

```
1. execute_scenario("cataloging_with_image", "auto_approve")
   Result: failure

2. get_trace_overview(trace_id)
   Identify: save_product failed, all upstream succeeded

3. get_run_details(save_product_run_id)
   Error: "ValidationError: price must be float, got str"

4. Claude analyzes:
   "Cataloging specialist returned wrong type"

5. Fix:
   Read: prompts/cataloging_specialist.prompt
   Edit: Add type emphasis section

6. Validate:
   execute_scenario() again
   Success rate: 0% → 100%
```

**Token Cost**: ~2K tokens
**Duration**: 2-5 minutes

---

### Scenario 2: Batch Testing (10-20 min)

```
1. Execute 5 scenarios
   for scenario in ["cataloging_basic", "cataloging_with_image", ...]:
       execute_scenario(scenario, "auto_approve")

2. list_recent_tests(limit=5)
   Pattern: 3/5 pass, 2/5 fail with same error

3. Investigate first failure (reuse analysis across similar failures)
   get_trace_overview() → get_run_details()

4. Root cause: Prompt issue affecting 2 scenarios

5. Fix once, validate all scenarios benefit
```

**Token Cost**: ~10K tokens for 5 scenarios
**Duration**: 10-20 minutes

---

### Scenario 3: Improvement Validation (3-10 min)

```
1. Baseline: execute_scenario() → record metrics

2. Apply fix: Edit prompt/code

3. Validation: execute_scenario() → record new metrics

4. Compare:
   Success rate: improved?
   Latency: acceptable?
   Regressions: any previously passing tests now fail?

5. Decision:
   KEEP: All metrics good
   REVERT: Regressions detected
   ITERATE: Partial improvement
```

---

## VII. Issue Categories & Fix Strategies

| Issue Type | Frequency | Detection | Fix Tool |
|------------|-----------|-----------|----------|
| **Prompt** | 40% | Wrong output format, type errors | Edit prompt file |
| **Code** | 30% | Exceptions, KeyErrors | Edit Python code |
| **Architecture** | 20% | Context loss, state bugs | Edit workflow code |
| **Data Quality** | 10% | Schema violations | Edit Pydantic models |

### Prompt Issues

**Symptoms**: Wrong output format, type mismatches

**Investigation**:
- get_run_details() - Check actual vs expected output
- Read prompt file
- Check examples match desired behavior

**Fix**:
- Edit prompt to add type emphasis
- Add canonical examples
- Add clarification instructions

---

### Code Issues

**Symptoms**: Exceptions, KeyErrors

**Investigation**:
- get_run_details() - Read error traceback
- Read code file at error location
- Check input validation

**Fix**:
- Edit code to add error handling
- Fix field extraction logic
- Add input validation

---

## VIII. Implementation Plan

### Phase 1: Core Tools (Week 1)

**Deliverables**:
1. Implement `execute_scenario()` - Wrapper around simulate.py
2. Implement `get_trace_overview()` - LangSmith metadata fetch
3. Implement `get_run_details()` - LangSmith run fetch
4. Implement `list_recent_tests()` - Local history
5. Manual testing by Claude on 5-10 scenarios

**Files to Create**:
- `tests/tools/execution.py`
- `tests/tools/trace_analysis.py`
- `tests/tools/test_history.py`

**Success Criteria**:
- All tools return correct data
- Token efficiency targets met (Level 0: ~500, Level 1: ~1,500)
- Claude can successfully test, analyze, fix, validate

---

### Phase 2: Deep Analysis (Week 2)

**Deliverables**:
1. Implement `get_run_messages()` - Level 2 deep dive
2. Add search/filter to test history
3. Run 20+ scenario iterations with improvements

**Success Criteria**:
- Level 2 works for complex bugs
- 90%+ success rate on core scenarios

---

## IX. Success Metrics

### Token Efficiency

**Target**: < 3K tokens per scenario analysis
**Savings**: 25x vs naive approach (50K → 2K)

### Improvement Velocity

- Issue identification: < 5 min
- Fix implementation: < 10 min
- Validation: < 5 min
- **Full cycle**: < 20 min per improvement

### System Quality

- Success rate: 90%+ on core scenarios
- Regression rate: < 5% after improvements
- Clear issue patterns documented

---

## X. Key Principles

1. **Information First**: Tools provide data, Claude provides intelligence
2. **Hierarchical Efficiency**: Fetch structure before details (25x savings)
3. **Use Existing Tools**: Don't duplicate Edit/Write/MCP capabilities
4. **Systematic Analysis**: Execute → Observe → Analyze → Fix → Validate
5. **Iterate Rapidly**: Small improvements, frequent validation

---

## XI. Related Documentation

**Framework Docs**:
- `TOOL_SPECIFICATIONS.md` - Detailed API reference for 5 tools
- `HIERARCHICAL_TRACE_ANALYSIS.md` - Token optimization strategy
- `QUICK_REFERENCE.md` - Cheat sheet

**Testing Infrastructure**:
- `LOCAL_TESTING_STRATEGY.md` - CLI tools and philosophy
- `../../CLAUDE.md` - Project-wide guidance

**LangSmith Integration**:
- LangSmith Docs: https://docs.smith.langchain.com
- API Reference: https://api.smith.langchain.com/docs
