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
| `/eval analyze <trace_id> --quick` | analyze | Code graders only (skip model criteria) |
| `/eval analyze <trace_id> --thorough` | analyze | Code graders + model criteria + outcome |
| `/eval analyze <trace_id> --thread` | analyze | Multi-turn thread analysis |
| `/eval analyze <trace_id> --thorough --thread` | analyze | Full depth: model criteria per trace + cross-trace |
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
| `--thread` | Multi-turn: get workflow window, code graders per trace, cross-trace rubrics |
| `--thorough --thread` | Multi-turn deep: model criteria per trace + cross-trace rubrics (most comprehensive) |

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

### Model Criteria Evaluation (Single-Trace Deep Analysis)

For `--thorough` mode or when investigating failures, evaluate each rubric one at a time.

#### Step-by-Step Workflow

```text
1. Run code graders first (fast, free)
2. If --thorough OR code graders failed:
   a. Pull data for each applicable rubric
   b. Evaluate against criteria
   c. Record pass/fail with evidence
3. Always evaluate workflow_outcome_achieved last (overall quality)
```

#### PM Rubrics

**`pm_routing_appropriate`**

```python
# Data to pull:
from tests.tools.trace_analysis import get_delegation_graph
graph = get_delegation_graph(trace_id)
# Also read PM's system prompt and specialist descriptions
```

```text
Evaluate: For each delegation in graph.delegations:
- Does the task match the specialist's domain?
- Could another specialist have done it better?
- Was the routing decision logical?

Pass: All delegations go to appropriate specialists
Fail: Task sent to wrong specialist, or better option existed
Evidence: List each delegation with specialist name, task summary, assessment
```

**`pm_synthesis_quality`**

```python
# Data to pull:
from tests.tools.trace_analysis import get_agent_final_message, get_file_io_trace
pm_response = get_agent_final_message(trace_id, agent="PM")
files = get_file_io_trace(trace_id)  # See what specialists produced
```

```text
Evaluate:
- Does PM's final response incorporate key findings from all specialists?
- Is anything important omitted?
- Is the synthesis coherent and well-structured?

Pass: Final response addresses user's request using specialist outputs appropriately
Fail: Missing key information, contradicts specialist findings, or incoherent
Evidence: Quote what specialists provided vs what PM synthesized
```

**`pm_context_handoff`**

```python
# Data to pull:
from tests.tools.evaluation.helpers import show_handoff
# For each delegation:
show_handoff(pm_run_id, specialist_run_id)
```

```text
Evaluate: For each delegation:
- Did PM provide enough context for specialist to work autonomously?
- Did specialist have to guess or make assumptions?
- Was user intent clearly communicated?

Pass: Specialist had sufficient context (user intent, relevant data, expected output)
Fail: Specialist lacked critical info, made incorrect assumptions
Evidence: Quote PM's delegation message, note any context gaps
```

#### Analyst Rubrics

**`analyst_observation_complete`**

```python
# Data to pull:
# 1. Analyst's input (image or data)
# 2. Analyst's output file
# 3. Analyst's protocol (what should be observed)
from tests.tools.trace_analysis import get_file_io_trace
files = get_file_io_trace(trace_id)
# Read the analyst's output file content
```

```text
Evaluate:
- Did analyst observe all aspects specified in their protocol?
- Any obvious elements missed?
- Coverage vs protocol requirements?

Pass: All protocol-specified observation areas covered
Fail: Missed obvious elements or skipped required observations
Evidence: List what was observed vs what protocol requires
```

**`analyst_finding_accuracy`**

```python
# Data to pull:
# 1. Analyst's input (the actual image/data)
# 2. Analyst's findings (output file)
# Need to VIEW the input to verify findings
```

```text
Evaluate:
- Are stated findings actually present in the input?
- Do descriptions match reality?
- Any mischaracterizations?

Pass: Findings accurately describe what's in the input
Fail: Findings don't match input (wrong colors, counts, attributes)
Evidence: Quote specific findings, compare to actual input
```

**`analyst_no_hallucination`**

```text
Evaluate:
- Did analyst invent details not present in input?
- Did analyst claim to see things that aren't there?
- All observations traceable to actual input?

Pass: All observations traceable to actual input
Fail: Contains fabricated details, invented attributes
Evidence: Quote hallucinated content, note what input actually shows
```

#### Specialist Rubrics

**`specialist_domain_accuracy`**

```python
# Data to pull:
# 1. Specialist's output (generated assets, data, etc.)
# 2. Domain protocol (rules for this domain)
# 3. Upstream analyst findings (what specialist should work with)
```

```text
Evaluate:
- Is specialist's output correct for the domain?
- Does it follow domain rules from protocol?
- Is it consistent with analyst findings?

Pass: Output is domain-appropriate, follows protocol, consistent with inputs
Fail: Domain errors, violates protocol rules, contradicts analyst findings
Evidence: Quote specific output, note domain issues
```

#### Outcome Rubric (Always Evaluate in --thorough)

**`workflow_outcome_achieved`**

```python
# Data to pull:
# 1. User's original request (from trace input)
# 2. PM's final response
# 3. Any generated artifacts (files, listings, images)
from tests.tools.trace_analysis import get_agent_final_message
from tests.tools.trace_loader import load_trace_for_eval
trace = load_trace_for_eval(trace_id)
pm_response = get_agent_final_message(trace_id, agent="PM")
```

```text
Evaluate (5 questions):
1. What did the user ask for?
2. What was actually delivered?
3. Does delivery match request?
4. Any critical omissions or errors?
5. Would user accept this result?

Pass: Output directly addresses user's request, complete, no critical issues
Fail: Output misses user's intent, incomplete, or contains defeating errors
Evidence: Quote user request, summarize delivery, note gaps
```

#### Model Grader Output Format

For each rubric evaluated:

```markdown
**[Rubric Name]:** PASS | FAIL

Data Pulled:
- [What data was examined]

Assessment:
- [Evaluation against criteria]

Evidence:
- [Specific quotes, comparisons, observations]

Issues (if FAIL):
- [What went wrong and why]
```

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

Evaluate workflow sessions spanning multiple traces.

**CRITICAL:** Thread/session IDs can span lifetime conversations. Use workflow window for bounded retrieval.

### Invocation

```bash
/eval analyze <trace_id> --thread
```

### Complete Workflow (Step-by-Step)

#### Step 1: Get Workflow Window

```python
from tests.tools.evaluation.helpers import get_workflow_window

# Bounded retrieval - O(window) not O(thread history)
window = get_workflow_window(trace_id, hours_before=2.0, hours_after=2.0)
# Returns: [{trace_id, start_time, end_time, is_starting_trace, session_break_before, status, error}, ...]
```

#### Step 2: Collect Per-Trace Data

For each trace in window, gather:

```python
from tests.tools.graders import run_code_graders
from tests.tools.trace_analysis import get_agent_final_message, get_tool_call_sequence

trace_data = []
for t in window:
    tid = t['trace_id']

    # Code graders
    grades = run_code_graders(tid)

    # PM's final message (for context continuity)
    pm_msg = get_agent_final_message(tid, agent="PM")

    # Tool sequence (for HITL detection)
    seq = get_tool_call_sequence(tid)

    # Check for HITL interrupt
    hitl_tools = ["interrupt", "interrupt_with_approval", "request_approval"]
    has_hitl = any(tc.tool_name in hitl_tools or "interrupt" in tc.tool_name.lower()
                   for tc in seq.tool_calls)

    trace_data.append({
        "trace_id": tid,
        "grades": grades,
        "pm_message": pm_msg.message if pm_msg else None,
        "has_hitl_interrupt": has_hitl,
        "status": t['status'],
        "error": t['error'],
        "session_break_before": t['session_break_before'],
    })
```

#### Step 3: Identify HITL Flows

HITL flows span two traces:

- Trace N: Specialist triggers HITL interrupt (workflow pauses)
- Trace N+1: User responds (approve/reject/edit), specialist acts

```python
hitl_flows = []
for i, td in enumerate(trace_data[:-1]):  # Skip last (no next trace)
    if td['has_hitl_interrupt']:
        next_td = trace_data[i + 1]

        # Determine decision from next trace's user input or specialist behavior
        # - If specialist persisted: likely approved
        # - If specialist did NOT persist: likely rejected
        # - If data differs from interrupt: likely edited

        hitl_flows.append({
            "interrupt_trace": td['trace_id'],
            "response_trace": next_td['trace_id'],
            "decision": "unknown",  # Infer from next trace analysis
        })
```

#### Step 4: Evaluate Cross-Trace Rubrics

For each rubric, pull specific data and evaluate:

**4a. `thread_context_continuity`**

```text
Data: PM messages from consecutive traces
Evaluate:
- Does PM reference prior conversation appropriately?
- Does PM avoid unnecessary repetition?
- Does PM maintain awareness of what was discussed?

Pass: PM demonstrates context awareness
Fail: PM acts like each turn is new, or repeats info already provided
```

**4b. `thread_hitl_respected`**

```text
Data: HITL flows identified in Step 3
For each flow:
1. Examine response trace's user input for decision signal
2. Check specialist actions in response trace:
   - Approved -> should see persist call
   - Rejected -> should NOT see persist call
   - Edited -> should see persist with different data

Pass: All HITL decisions honored
Fail: Specialist contradicted user's decision
```

**4c. `thread_state_progression`**

```text
Data: What each trace accomplished (delegations, outputs)
Evaluate:
- Did each trace move workflow forward?
- Any stuck loops (same delegation pattern repeated)?
- Proper completion or abandonment?

Pass: Linear or branching progress toward goal
Fail: Stuck in loop, regressed, or stalled without reason
```

**4d. `thread_error_recovery`**

```text
Data: Traces with status=error or error field set
Evaluate:
- If error in trace N, did trace N+1 attempt recovery?
- Was alternative approach taken?
- Graceful degradation if unrecoverable?

Pass: Errors acknowledged with recovery attempts
Fail: Error ignored, same approach repeated, or conversation abandoned
```

#### Step 5: Handle Session Boundaries

Session breaks (gaps > 60 min) indicate different workflow sessions:

```text
- Traces BEFORE break: One workflow session
- Traces AFTER break: Different workflow session
- Cross-trace rubrics should NOT span session breaks
- Evaluate each session segment separately
```

### Navigation Helpers

```python
from tests.tools.evaluation.helpers import prev_trace, next_trace

# O(1) navigation with session boundary awareness
prev_id = prev_trace(trace_id)  # Stops at 60+ min gaps
next_id = next_trace(trace_id)  # Stops at 60+ min gaps

# Ignore boundaries if needed
prev_id = prev_trace(trace_id, session_gap_minutes=0)
```

### Output Template

```markdown
## Multi-Turn Analysis: Workflow Window

**Starting trace:** <trace_id>
**Window:** +/- 2 hours
**Traces in window:** N (session boundaries: M)

### Workflow Sessions

[If session boundaries exist, list each session segment]

### Per-Trace Results

| # | Trace | Time | Verdict | Score | HITL? | Session Break |
|---|-------|------|---------|-------|-------|---------------|
| 1 | abc123 | 10:00 | PASS | 0.95 | No | - |
| 2 | def456 | 10:02 | PASS | 0.90 | Yes | - |
| 3 | ghi789 | 10:05 | PASS | 1.00 | No | - |

### HITL Flows

| Interrupt Trace | Response Trace | Decision | Honored? |
|-----------------|----------------|----------|----------|
| def456 | ghi789 | Approved | Yes |

### Cross-Trace Evaluation

**Context Continuity:** [PASS/FAIL]
- [Evidence: Quote PM references to prior context]
- [Issues: Note any context losses]

**HITL Respected:** [PASS/FAIL]
- [Evidence: Decision type, subsequent actions]
- [Issues: Any violations]

**State Progression:** [PASS/FAIL]
- [Evidence: What each trace accomplished]
- [Issues: Loops, regressions, stalls]

**Error Recovery:** [PASS/FAIL or N/A if no errors]
- [Evidence: Error details, recovery actions]

### Overall Verdict: [PASS/PARTIAL/FAIL]

### Conversation Flow Summary
[Narrative: How conversation progressed across turns]
```

---

## Combined Mode: --thorough --thread

Full-depth evaluation: model criteria on every trace PLUS cross-trace rubrics.

**Use when:** Investigating complex issues, regression analysis, or building confidence in workflow behavior.

**Cost:** Most expensive mode - Claude evaluates ~8 rubrics per trace plus cross-trace.

```bash
/eval analyze <trace_id> --thorough --thread
```

### Combined Mode Workflow

```text
1. Get workflow window (same as --thread)
   - get_workflow_window(trace_id, hours_before=2.0, hours_after=2.0)
   - Identify session boundaries

2. For EACH trace in window (--thorough per trace):
   a. Run code graders
   b. Evaluate single-trace model rubrics:
      - PM: pm_routing_appropriate, pm_synthesis_quality, pm_context_handoff
      - Analysts: analyst_observation_complete, analyst_finding_accuracy, analyst_no_hallucination
      - Specialists: specialist_domain_accuracy
      - Outcome: workflow_outcome_achieved
   c. Collect HITL interrupt status

3. Evaluate cross-trace rubrics (--thread rubrics):
   - thread_context_continuity
   - thread_hitl_respected
   - thread_state_progression
   - thread_error_recovery

4. Aggregate results:
   - Per-trace verdicts with model rubric details
   - Cross-trace verdicts
   - Overall workflow verdict
```

### Key Difference from --thread Alone

| Aspect        | --thread   | --thorough --thread     |
|---------------|------------|-------------------------|
| Code graders  | Per trace  | Per trace               |
| Model rubrics | None       | All per trace           |
| Cross-trace   | Yes        | Yes                     |
| Cost          | Low        | High                    |
| Depth         | Structural | Behavioral + Quality    |

### Output Template

```markdown
## Full-Depth Analysis: Workflow Window

**Starting trace:** <trace_id>
**Window:** +/- 2 hours
**Traces in window:** N
**Mode:** thorough + thread

### Per-Trace Deep Analysis

#### Trace 1: <trace_id> (HH:MM)

**Code Graders:** PASS (5/5)
**Model Rubrics:**

| Rubric | Result | Evidence |
|--------|--------|----------|
| pm_routing_appropriate | PASS | All delegations matched specialist domains |
| pm_synthesis_quality | PASS | Final response incorporated analyst findings |
| workflow_outcome_achieved | PASS | User request fully addressed |

**HITL:** No interrupt

---

#### Trace 2: <trace_id> (HH:MM)

[Same structure for each trace...]

---

### Cross-Trace Evaluation

**Context Continuity:** PASS
- PM referenced prior image analysis in turn 2
- No context loss detected

**HITL Respected:** PASS
- 1 HITL flow: interrupt in T2, approved in T3
- creative_specialist persisted as approved

**State Progression:** PASS
- T1: Initial analysis
- T2: HITL approval request
- T3: Final synthesis
- Linear progress toward completion

**Error Recovery:** N/A (no errors)

### Summary

| Trace | Code | Model | HITL | Status |
|-------|------|-------|------|--------|
| abc123 | PASS | PASS | - | success |
| def456 | PASS | PASS | Interrupt | success |
| ghi789 | PASS | PASS | Responded | success |

**Cross-Trace:** 4/4 PASS

### Overall Verdict: PASS

### Recommendations
- [Any issues found across all evaluations]
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

### Multi-Turn Navigation

```python
from tests.tools.evaluation.helpers import (
    get_workflow_window,  # Bounded trace retrieval around starting trace
    prev_trace,           # O(1) previous trace with session boundary awareness
    next_trace,           # O(1) next trace with session boundary awareness
)

# Get workflow context - O(window) not O(thread history)
window = get_workflow_window(trace_id, hours_before=2.0, hours_after=2.0)

# Navigate with session boundary awareness (stops at 60+ min gaps)
prev_id = prev_trace(trace_id)
next_id = next_trace(trace_id)

# Ignore boundaries if needed
prev_id = prev_trace(trace_id, session_gap_minutes=0)
```

---

## Design Reference

Full architecture: `docs/architecture/testing/evaluation/EVALUATION_FRAMEWORK.md`
