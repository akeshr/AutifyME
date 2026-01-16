---
name: eval
description: Analyze traces, run scenarios, diagnose issues, improve agents
---

# /eval Skill

Make AutifyME better: higher autonomy, fewer corrections, no regressions.

---

## Mode Selection

| Input Pattern | Mode | Action |
|---------------|------|--------|
| `/eval <trace_id>` | analyze | Score trace with code graders |
| `/eval analyze <trace_id>` | analyze | Score trace with code graders |
| `/eval analyze <trace_id> --thorough` | analyze | Code graders + model criteria + outcome |
| `/eval analyze <trace_id> --thread` | analyze | Multi-turn thread analysis |
| `/eval test <scenario_id>` | test | Execute scenario, grade result |
| `/eval improve <agent>` | improve | Diagnose and fix agent |
| `/eval trends` | trends | Query workflow_outcomes patterns |
| `/eval replay` | replay | Replay production workflows |
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
   IF grades.verdict == "PASS" AND --quick:
       Report summary and exit
   ELSE IF grades.verdict == "PASS" AND --thorough:
       Continue to model criteria evaluation
   ELSE:
       Investigate failures

4. Evaluate model criteria (--thorough or failures)
   - Pull data specified in each rubric
   - Evaluate against rubrics in EVALUATION_FRAMEWORK.md
   - Include workflow_outcome_achieved for outcome quality

5. Report efficiency metrics (always)
   - Latency (total time)
   - Cost (token estimate)
   - Token breakdown per agent
```

### Sub-modes

| Flag | Behavior |
|------|----------|
| `--quick` | Code graders only |
| `--thorough` | Code graders + model criteria + outcome evaluation |
| `--thread` | Multi-turn: get all traces in thread, grade each, evaluate cross-trace concerns |

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

### Model Criteria Evaluation

When doing thorough analysis, evaluate these rubrics (see EVALUATION_FRAMEWORK.md for details):

**PM:**
- `pm_routing_appropriate` - Did PM route to correct specialists?
- `pm_synthesis_quality` - Did PM synthesize outputs well?
- `pm_context_handoff` - Did PM pass sufficient context?

**Analyst:**
- `analyst_observation_complete` - All aspects observed?
- `analyst_finding_accuracy` - Findings match input?
- `analyst_no_hallucination` - No fabricated details?

**Specialist:**
- `specialist_domain_accuracy` - Output correct for domain?

**Outcome (always in thorough):**
- `workflow_outcome_achieved` - Did workflow satisfy user's goal?

### Output Template

```markdown
## Trace Analysis: <trace_id>

**Verdict:** PASS | PARTIAL | FAIL
**Score:** X.XX (N/M code graders passed)

### Efficiency Metrics
- **Latency:** X.Xs
- **Cost:** ~$X.XX (estimated)
- **Tokens:** X,XXX total (PM: X, analysts: X, specialists: X)

### Code Grader Results
| Grader | Result | Severity | Evidence |
|--------|--------|----------|----------|

### Model Criteria (if --thorough)
| Criterion | Pass/Fail | Notes |
|-----------|-----------|-------|

### Outcome Assessment
[workflow_outcome_achieved evaluation]

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

2. Query known patterns first
   - get_pattern_fixes() to retrieve historical fixes
   - Match current symptoms to known patterns

3. Diagnose root cause
   - If pattern matched: use known fix as starting point
   - If new: examine agent prompt, check tool implementations

4. Propose fix
   - Show diff of proposed changes
   - Explain why this fixes the issue

5. Await approval
   - DO NOT implement without explicit approval

6. Implement and validate
   - Make changes
   - Re-run test scenario
   - Verify fix worked

7. Store pattern (if fix successful)
   - store_pattern_fix() with symptoms, fix location, description
   - Builds pattern library for future fixes
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

```python
from tests.tools.workflow_outcomes import get_outcomes, get_outcome_stats

# Get aggregate stats
stats = get_outcome_stats(days=7)
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"Top intent: {max(stats['intent_distribution'], key=stats['intent_distribution'].get)}")

# Get recent failures for investigation
failures = get_outcomes(days=7, success=False, limit=10)
for f in failures:
    print(f"{f.error_type}: {f.message_text[:50]}...")
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

## Replay Mode

Replay production workflows for regression testing.

### Workflow

```python
from tests.tools.replay_runner import replay_outcome, replay_batch, format_batch_summary

# Replay single outcome
from tests.tools.workflow_outcomes import get_outcomes
outcomes = get_outcomes(days=7, with_media=True, success=True, limit=1)
result = replay_outcome(outcomes[0])
print(f"Verdict: {result.grader_verdict}, Regression: {result.is_regression}")

# Replay batch with filters
results = replay_batch(days=7, success=True, with_media=True, limit=5)
print(format_batch_summary(results))

# Stop on first regression
results = replay_batch(days=7, limit=10, stop_on_regression=True)
```

---

## Multi-Turn Analysis

Evaluate conversation threads spanning multiple traces.

### Workflow

```
1. Get starting trace
   outcome = get_outcome_by_trace(trace_id)

2. Get all traces in thread
   thread_outcomes = get_outcome_by_thread(outcome.thread_id)

3. Grade each trace individually
   for outcome in thread_outcomes:
       grades = run_code_graders(outcome.trace_id)

4. Evaluate cross-trace concerns (Claude reasoning)
   - Context continuity: Did PM remember prior conversation?
   - HITL handling: Did PM respect approval/rejection/edit?
   - State progression: Did workflow advance correctly?
   - Error recovery: Did PM handle mid-conversation failures?
```

### Invocation

```bash
/eval analyze <trace_id> --thread
```

### Output Template

```markdown
## Multi-Turn Analysis: Thread <thread_id>

**Traces in thread:** N
**Overall verdict:** PASS | FAIL

### Per-Trace Results
| Trace | Verdict | Score | Key Issues |
|-------|---------|-------|------------|

### Cross-Trace Evaluation
- **Context continuity:** [assessment]
- **HITL handling:** [assessment]
- **State progression:** [assessment]

### Conversation Flow
[Summary of how conversation progressed across turns]
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
from tests.tools.graders import (
    run_code_graders,        # Run all graders (PM + specialists + analysts + universal)
    run_pm_graders,          # Run only PM graders
    run_specialist_graders,  # Run only specialist graders (auto-detects from trace)
    run_analyst_graders,     # Run only analyst graders (auto-detects from trace)
    GraderSuiteResult,
)

grades: GraderSuiteResult = run_code_graders(trace_id)
# grades.verdict, grades.overall_score, grades.format_summary()
# grades.warnings - list of non-fatal issues (e.g., unclassified agents)

# Graders use taxonomy-based classification:
# - Agents ending in _analyst are graded as analysts
# - Agents ending in _specialist are graded as specialists
# - Agents ending in _reviewer are graded as reviewers
# - Unclassified agents trigger a warning but still run universal graders
# - Universal graders (like error_recovery_attempted) run on ALL agents
```

### Scenarios

```python
from tests.scenarios import load_scenario, list_scenarios
scenario = load_scenario("PM-01")
# scenario.input.message, scenario.expected, scenario.success_criteria
```

### Production Data (workflow_outcomes)

```python
from tests.tools.workflow_outcomes import (
    get_outcomes,              # Query with any filter combination
    get_outcome_by_trace,      # Get outcome for specific trace
    get_outcome_by_thread,     # Get all outcomes for a thread
    get_media_for_outcome,     # Get media from Supabase storage
    create_scenario_from_outcome,  # Convert to replay scenario
    get_outcome_stats,         # Aggregate statistics
    list_distinct_values,      # List unique intents/departments/etc
)
```

### Baseline Management

```python
from tests.tools.eval_results import (
    store_baseline,          # Store grader results on trace (LangSmith feedback)
    get_baseline,            # Get baseline from trace's feedback
    compare_to_baseline,     # Compare trace against baseline
    format_baseline_comparison,  # Format comparison for display
)

# Store baseline (then update scenario YAML's baseline_trace_id)
store_baseline("PM-01", trace_id, score=0.85, grader_results={"protocol": True})

# Compare new trace to baseline (pass baseline_trace_id from scenario)
from tests.scenarios import load_scenario
scenario = load_scenario("PM-01")
comparison = compare_to_baseline(
    "PM-01", new_trace_id, 0.80, {"protocol": True},
    baseline_trace_id=scenario.baseline_trace_id
)
```

### Pattern Storage (LangSmith Feedback)

```python
from tests.tools.eval_results import (
    store_pattern_fix,       # Store fix pattern after successful improvement
    get_pattern_fixes,       # Query historical fix patterns
)

# Store pattern after successful fix
store_pattern_fix(
    trace_id=trace_id,
    pattern_name="PROTOCOL_NOT_LOADED",
    symptoms=["first call not load_protocol", "inconsistent behavior"],
    agent="catalog_specialist",
    fix_location="prompts/specialists/catalog_specialist.prompt",
    fix_description="Added protocol load instruction to Process section",
    success=True
)

# Query patterns for matching
fixes = get_pattern_fixes(pattern_name="PROTOCOL_NOT_LOADED")  # By name
fixes = get_pattern_fixes(agent="catalog_specialist")  # By agent
fixes = get_pattern_fixes()  # All patterns
```

### Replay Runner

```python
from tests.tools.replay_runner import (
    replay_outcome,      # Replay single production outcome
    replay_batch,        # Replay batch of outcomes
    format_batch_summary,  # Format batch results
    ReplayResult,        # Result dataclass
)
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
