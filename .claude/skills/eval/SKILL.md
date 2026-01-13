---
name: eval
description: Unified Evaluation Skill (project)
---

# /eval Skill

Make AutifyME better: higher autonomy, fewer corrections, no regressions.

---

## Mode Selection

| Input Pattern | Mode | Action |
|---------------|------|--------|
| `/eval <trace_id>` | analyze | Score trace with graders |
| `/eval analyze <trace_id>` | analyze | Score trace with graders |
| `/eval test <scenario_id>` | test | Execute scenario, grade result |
| `/eval improve <agent>` | improve | Diagnose and fix agent |
| `/eval trends` | trends | Query workflow_outcomes patterns |
| `/eval "<description>"` | (infer) | Determine from context |

---

## Analyze Mode

Score and investigate an existing trace.

### Workflow

```
1. Load trace data
   result = load_trace_for_eval(trace_id)

2. Run code graders
   grades = run_code_graders(trace_id)

3. Branch on result
   IF grades.verdict == "PASS":
       Report summary and exit
   ELSE:
       Investigate failures
```

### Investigation (when graders fail)

```python
# For failed graders, drill into specifics:
from tests.tools.evaluation.helpers import show_node, show_handoff

# Examine specific nodes
show_node(run_id)  # Full INPUT/REASONING/OUTPUT

# Examine context handoffs
show_handoff(parent_id, child_id)  # What was passed vs received

# Check delegation flow
show_orchestrator_flow(trace_id)  # PM's decision sequence
```

### Output Template

```markdown
## Trace Analysis: <trace_id>

**Verdict:** PASS | PARTIAL | FAIL
**Score:** X.XX (N/M graders passed)

### Grader Results
| Grader | Result | Severity | Evidence |
|--------|--------|----------|----------|

### Issues Found
1. [Issue with evidence from show_node/show_handoff]

### Recommendations
1. [Actionable fix - which file, what change]
```

---

## Test Mode

Execute scenario and grade the result.

### Workflow

```python
1. Load scenario definition
   from tests.scenarios import load_scenario
   scenario = load_scenario(scenario_id)  # e.g., "PM-01"

2. Execute against PM
   from tests.tools.pm_interaction import chat_with_pm
   result = chat_with_pm(
       scenario.input.message,
       media_paths=scenario.resolve_media_paths(test_assets_dir)
   )

3. Grade result
   from tests.tools.graders import run_code_graders
   grades = run_code_graders(result.trace_id)

4. Compare to baseline (if exists)
   IF scenario.baseline_trace_id:
       compare_traces(scenario.baseline_trace_id, result.trace_id)

5. Report pass/fail
```

### Available Scenarios

```python
from tests.scenarios import list_scenarios
list_scenarios()  # Returns: ['PM-01', 'PM-02', 'PM-03', 'PM-04']
```

### Output Template

```markdown
## Test Result: <scenario_id>

**Verdict:** PASS | FAIL
**Trace ID:** <new_trace_id>
**Scenario:** <scenario.name>

### Grader Results
[table from grades.format_summary()]

### Baseline Comparison
[if baseline exists - from compare_traces()]

### Next Steps
- [If PASS: consider setting as new baseline]
- [If FAIL: investigate with /eval analyze <trace_id>]
```

---

## Improve Mode

Diagnose root cause and propose fix.

### Workflow

```
1. Identify failing behavior
   - From analyze mode results
   - From user description

2. Diagnose root cause
   - Match to known pattern (protocol_not_loaded, context_loss, etc.)
   - Examine agent prompt in prompts/<agent>/
   - Check tool implementations

3. Propose fix
   - Show diff of proposed changes
   - Explain why this fixes the issue

4. Await approval
   - DO NOT implement without explicit approval

5. Implement and validate
   - Make changes
   - Re-run test scenario
   - Verify fix worked
```

### Pattern Matching

| Symptom | Pattern | Fix Location |
|---------|---------|--------------|
| First call not load_protocol | PROTOCOL_NOT_LOADED | Agent prompt instructions section |
| Child missing parent's context | CONTEXT_LOSS | PM delegation description |
| No HITL before persist | HITL_SKIPPED | Specialist interrupt gate |
| Wrong agent selected | WRONG_ROUTING | PM routing logic |
| Incomplete research | PREMATURE_TERMINATION | Analyst thoroughness instructions |

### Output Template

```markdown
## Improvement: <agent>

### Diagnosis
**Pattern:** <matched_pattern>
**Root Cause:** [Explanation]
**Evidence:** [From trace analysis]

### Proposed Fix
**File:** <path>
**Change:**
\`\`\`diff
- old line
+ new line
\`\`\`

### Validation Plan
1. Run `/eval test <scenario>`
2. Verify grader `<grader_name>` passes
3. Check no regressions in other scenarios

---
Awaiting approval to implement fix.
```

---

## Trends Mode

Query workflow_outcomes for system-wide patterns.

### Workflow

```sql
-- Via Supabase MCP or direct query
SELECT outcome, count(*)
FROM workflow_outcomes
WHERE created_at > now() - interval '7 days'
GROUP BY outcome
ORDER BY count(*) DESC;

-- Failure analysis
SELECT trace_id, failure_reason, created_at
FROM workflow_outcomes
WHERE outcome = 'failed'
ORDER BY created_at DESC
LIMIT 10;
```

### Output Template

```markdown
## System Trends (Last 7 Days)

### Outcome Distribution
| Outcome | Count | Percentage |
|---------|-------|------------|

### Top Failure Patterns
1. [Pattern]: N occurrences
2. ...

### Recommendations
- [Prioritized improvements based on data]
```

---

## Tool Reference

### Trace Loading

```python
from tests.tools.trace_loader import load_trace_for_eval, TraceForEval
result: TraceForEval = load_trace_for_eval(trace_id)
# result.tool_call_sequence, result.delegation_graph, result.detected_issues
```

### Grading

```python
from tests.tools.graders import run_code_graders, GraderSuiteResult
grades: GraderSuiteResult = run_code_graders(trace_id)
# grades.verdict, grades.overall_score, grades.format_summary()
```

### Scenarios

```python
from tests.scenarios import load_scenario, list_scenarios
scenario = load_scenario("PM-01")
# scenario.input.message, scenario.expected, scenario.success_criteria
```

### REPL Helpers

```python
from tests.tools.evaluation.helpers import (
    show_tree,           # Hierarchical trace view
    show_node,           # Single node detail
    show_handoff,        # Context handoff analysis
    show_orchestrator_flow,  # PM decision sequence
    detect_issues,       # Auto-detect problems
    compare_traces,      # Before/after comparison
)
```

---

## Design Reference

Full architecture: `docs/architecture/testing/evaluation/EVALUATION_FRAMEWORK.md`
