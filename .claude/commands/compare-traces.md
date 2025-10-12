# Compare Traces

Compare two traces to identify differences (success vs failure).

## Usage

```
/compare-traces <trace-id-1> <trace-id-2>
```

Typically: success trace vs failure trace for same workflow.

## Task

Dump and compare two traces to identify where they diverge.

### 1. Dump Both Traces

```bash
cd agents
# Dump both traces in parallel
uv run python scripts/dump_langsmith_thread.py --run-id <trace-1> > ../trace_1.txt &
uv run python scripts/dump_langsmith_thread.py --run-id <trace-2> > ../trace_2.txt &
wait

echo "✅ Traces dumped to trace_1.txt and trace_2.txt"
```

### 2. Compare Tool Calls

Read both traces and extract:
- Tools called in each trace
- Order of tool calls
- Tool arguments
- Tool results

Create comparison table:
```markdown
| Step | Trace 1 (Success) | Trace 2 (Failure) |
|------|-------------------|-------------------|
| 1    | image_analysis(path) | image_analysis(path) |
| 2    | cataloging(msg, analysis) | cataloging(msg, **None**) ❌ |
| 3    | save_product(...) | ❌ Not called |
```

### 3. Compare State Changes

Track state evolution:
- Message count at each step
- Variables in state
- Checkpoint progression

### 4. Identify Divergence Point

Find the first difference:
- Different tool called
- Same tool, different arguments
- Tool called vs not called
- Different tool result

### 5. Analyze Error Context

For the failure trace:
- Extract error message
- Find line in trace where error occurred
- Show context (5 lines before/after)
- Identify root cause

### 6. Compare PM Behavior

Check PM decisions:
- Intent classification
- Department selection
- Task description passed to department
- Planning tool usage

### 7. Compare Department Behavior

Check department execution:
- Planning tool used?
- Tools called in sequence or parallel?
- Tool results passed between steps?
- HITL triggered correctly?

### 8. Compare Middleware

Check middleware execution:
- CompanyContextMiddleware: Context injected?
- SummarizationMiddleware: Summarization triggered?
- HumanInTheLoopMiddleware: HITL config applied?

### 9. Generate Detailed Report

```markdown
## Trace Comparison Report

### Traces
- **Trace 1 (Success)**: [trace-id]
  - Status: Success
  - Duration: [seconds]
- **Trace 2 (Failure)**: [trace-id]
  - Status: Error
  - Duration: [seconds]
  - Error: [error message]

### User Input
- **Trace 1**: [text + media]
- **Trace 2**: [text + media]
- **Difference**: [same/different]

### Tool Call Comparison

| Step | Trace 1 | Trace 2 | Status |
|------|---------|---------|--------|
| 1 | image_analysis | image_analysis | ✅ Same |
| 2 | cataloging(text, analysis) | cataloging(text, None) | ❌ **Diff: missing analysis** |
| 3 | save_product(...) | ❌ Not reached | ❌ **Missing** |

### Divergence Point

**Line**: [line number in trace_2.txt]
**Context**:
```
[5 lines before]
>>> DIVERGENCE HERE <<<
[5 lines after]
```

**Root Cause**:
[Detailed explanation of why they diverged]

### PM Behavior Comparison

| Aspect | Trace 1 | Trace 2 | Status |
|--------|---------|---------|--------|
| Intent | catalog product | catalog product | ✅ Same |
| Department | cataloging_dept | cataloging_dept | ✅ Same |
| Task description | [description] | [description] | ✅/❌ |
| Planning tool | ✅ Used | ❌ **Not used** | ❌ Diff |

### Department Behavior Comparison

| Aspect | Trace 1 | Trace 2 | Status |
|--------|---------|---------|--------|
| Planning | ✅ write_todos called | ❌ Not called | ❌ **Missing** |
| Tool sequence | Sequential | Parallel | ❌ **Wrong** |
| Result passing | ✅ Passed | ❌ Not passed | ❌ **Missing** |

### Middleware Comparison

| Middleware | Trace 1 | Trace 2 | Status |
|------------|---------|---------|--------|
| CompanyContext | ✅ Executed | ✅ Executed | ✅ Same |
| Summarization | ✅ Executed | ✅ Executed | ✅ Same |
| HITL | ✅ Configured | ❌ Not configured | ❌ **Missing** |

### Root Cause Analysis

**Primary Issue**: [Main problem]

**Contributing Factors**:
1. [Factor 1]
2. [Factor 2]

**Why Success Worked**:
- [Reason 1]
- [Reason 2]

**Why Failure Failed**:
- [Reason 1]
- [Reason 2]

### Evidence

**From Trace 1** (trace_1.txt:line):
```
[relevant excerpt]
```

**From Trace 2** (trace_2.txt:line):
```
[relevant excerpt]
```

### Recommended Fix

```python
# File: path/to/file.py
# Change:
[before code]

# To:
[after code]
```

**Rationale**: [Why this fixes it]

**Testing**: [How to verify fix]
```

## Notes

- Best used with one success and one failure trace
- Can also compare two failures to find common issues
- Look for missing DeepAgents planning tools
- Check if tool results are passed between steps
- Verify HITL configuration is consistent
