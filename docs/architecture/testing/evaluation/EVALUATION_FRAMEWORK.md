# Evaluation Framework

**Version:** 1.1
**Date:** 2026-01-13

---

## Entry Point

**Primary interface:** `/eval` skill - all evaluation workflows go through this single entry point.

**Deprecated commands:** `/evaluate` and `/test-intelligent` - use `/eval` modes instead.

---

## Bootstrap Sequence (CRITICAL - Start Here)

The framework requires baselines before automated testing works. Follow this sequence:

### Step 1: Manual Baseline Creation

```bash
# 1. Run PM workflow manually with known-good input
uv run python -c "
from tests.tools.pm_interaction import chat_with_pm
result = chat_with_pm('Catalog these sneakers for \$79.99', media_paths=['tests/test_assets/sneaker_single.jpg'])
print(f'Trace ID: {result.get(\"trace_id\")}')
"

# 2. Verify trace in LangSmith - confirm workflow completed successfully
# 3. Note the trace_id for next step
```

### Step 2: Store Baseline

```python
from tests.tools.eval_results import store_baseline
from tests.tools.graders import run_code_graders

trace_id = "<trace_id_from_step_1>"
grades = run_code_graders(trace_id)

store_baseline(
    scenario_id="PM-01",
    trace_id=trace_id,
    score=grades.overall_score,
    grader_results={r.name: r.passed for r in grades.results},
    metadata={"bootstrap": True, "date": "2026-01-14"}
)
```

### Step 3: Update Scenario YAML

```yaml
# tests/scenarios/pm/PM-01.yaml
baseline_trace_id: "<trace_id_from_step_1>"
```

### Step 4: Validate Framework

```bash
/eval analyze <trace_id> --thorough
```

**Without baselines, regression detection is impossible.**

---

## Purpose

Make AutifyME better: higher autonomy, fewer HITL corrections, faster completion, no regressions.

The evaluation framework is operated by Claude Code via the `/eval` skill. Claude Code is the intelligence; the framework provides tools and knowledge.

---

## Architecture

```
Claude Code (Intelligence)
    |
    +-- /eval skill (Entry Point)
          |
          +-- MODES
          |     +-- analyze  - Work with existing traces
          |     +-- test     - Generate new traces via scenarios
          |     +-- improve  - Fix agents based on findings
          |     +-- trends   - Analyze system-wide patterns
          |     +-- replay   - Replay production workflows
          |
          +-- TOOLS
          |     +-- trace_loader      - Load traces at any detail level
          |     +-- graders           - Run code graders (model = Claude reasoning)
          |     +-- scenario_runner   - Execute scenarios against PM
          |     +-- eval_storage      - Store/retrieve results & patterns
          |     +-- workflow_outcomes - Query production data
          |     +-- replay_runner     - Orchestrate production replays
          |
          +-- KNOWLEDGE
                +-- Agent behaviors   - What good looks like per agent type
                +-- Model rubrics     - How Claude evaluates quality
                +-- Failure patterns  - Common issues and fixes (LangSmith feedback)
```

---

## Agent Taxonomy

```
PM (Project Manager - Orchestrator)
  |
  +-- Analysts (Read-Only Research Layer)
  |     +-- visual_analyst    - Image/visual analysis
  |     +-- product_analyst   - External market research
  |     +-- catalog_analyst   - Internal catalog lookup
  |
  +-- Specialists (Execution Layer with HITL)
  |     +-- creative_specialist - Asset generation
  |     +-- catalog_specialist  - Data persistence
  |
  +-- Reviewers (Quality Gate Layer - Future)
        +-- compliance_reviewer
        +-- safety_reviewer
        +-- brand_reviewer
```

---

## Evaluation Approach

### Pillars

Every agent evaluated on 5 pillars:

| Pillar | Question |
|--------|----------|
| UNDERSTAND | Did agent understand its input? |
| REASON | Did agent reason correctly? |
| ACT | Did agent take right actions? |
| COMMUNICATE | Did agent communicate properly? |
| RECOVER | Did agent handle errors? |

### Agent-Specific Checks

Same pillars, different checks per agent type.

**PM Criteria:**

| Criterion | Type | Status | Description |
|-----------|------|--------|-------------|
| `pm_protocol_first` | Code | Implemented | Loaded protocol before any delegation |
| `pm_media_download_first` | Code | Implemented | Downloaded media before delegation |
| `pm_wave_execution` | Code | Implemented | Taxonomy-based wave validation |
| `pm_analyst_before_specialist` | Code | Implemented | Two-phase: research before execution |
| `pm_file_read_before_synthesis` | Code | Implemented | Read analysis files before synthesizing |
| `pm_routing_appropriate` | Model | Rubric defined | Delegated to correct agents |
| `pm_synthesis_quality` | Model | Rubric defined | Effectively combined specialist outputs |
| `pm_context_handoff` | Model | Rubric defined | Passed sufficient context to delegated agents |

**Analyst Criteria:**

| Criterion | Type | Status | Description |
|-----------|------|--------|-------------|
| `analyst_protocol_first` | Code | Implemented | Loaded domain protocol before analysis |
| `analyst_file_written` | Code | Implemented | Wrote findings to file |
| `analyst_observation_complete` | Model | Rubric defined | Observed all relevant aspects |
| `analyst_finding_accuracy` | Model | Rubric defined | Findings match actual content |
| `analyst_no_hallucination` | Model | Rubric defined | No fabricated observations |

**Specialist Criteria:**

| Criterion | Type | Status | Description |
|-----------|------|--------|-------------|
| `specialist_protocol_first` | Code | Implemented | Loaded domain protocol before execution |
| `specialist_hitl_triggered` | Code | Implemented | Requested approval before persisting |
| `specialist_read_upstream` | Code | Implemented | Read relevant analyst findings before action |
| `specialist_verified_before_act` | Code | Planned | Called verification tools before write |
| `specialist_hitl_respected` | Code | Implemented | Honored approval/rejection/edit (requires thread context for full check) |
| `specialist_domain_accuracy` | Model | Rubric defined | Domain-specific output quality |

**Creative Specialist Criteria (creative_specialist only):**

| Criterion                          | Type | Status      | Description                                                                 |
|------------------------------------|------|-------------|-----------------------------------------------------------------------------|
| `image_studio_fidelity_included`   | Code | Implemented | Fidelity spec present (prevents product identity loss)                      |
| `image_studio_core_specs_included` | Code | Implemented | Core specs present (fidelity, focus, lighting/material, composition/output) |
| `image_studio_output_verified`     | Code | Implemented | view_image called after image_studio to verify quality                      |

**Universal Criteria (all agents):**

| Criterion | Type | Status | Description |
|-----------|------|--------|-------------|
| `error_recovery_attempted` | Code | Implemented | If error occurred, agent attempted recovery |

**`error_recovery_attempted` specification:**
- Trigger: Any run with status=error or tool returning error
- Check: Did agent make subsequent tool calls after the error?
- Pass: No errors OR (error occurred AND agent continued with alternative action)
- Fail: Error occurred AND agent stopped without attempting recovery
- Evidence: `{agent, total_calls, error_calls, first_error_seq, first_error_tool, calls_after_error}`

**Taxonomy Warning System:**
- Orchestrator detects agents that don't match `_analyst`, `_specialist`, or `_reviewer` naming convention
- Warning added to `GraderSuiteResult.warnings` field
- Unclassified agents skip type-specific graders but still run universal graders
- PM is excluded from warnings (expected to not have suffix)

### Efficiency Metrics (Non-Graded)

**Decision:** Latency and cost are reported metrics, not pass/fail graders.

**Rationale:** An agent can behave perfectly but be slow/expensive. Slowness is a signal for optimization, not a defect. Failing traces for efficiency would conflate correctness with performance.

**What Claude reports in every analysis:**
- **Latency:** Total workflow time (from trace start/end)
- **Cost:** Estimated from token counts
- **Token breakdown:** Per-agent token usage

**Scenario thresholds (`max_latency_ms`, `max_cost`) are advisory:**
- Claude flags when exceeded
- Not automatic failures
- Used for trend analysis ("are we getting slower?")

### Grading Strategy

Layered approach - code graders first, model graders for depth:

```
1. Run code graders (fast, free)
   |
   +-- All pass? Quick structural check done
   |
   +-- Failures? Know what's structurally wrong
         |
         +-- Claude evaluates model criteria for severity/quality
         |
         +-- Investigate root cause
```

| Layer | What | How | Cost |
|-------|------|-----|------|
| Code graders | Process/structural rules | Python functions in `graders/` | Free (ms) |
| Model graders | Semantic quality | Claude reasoning with rubrics below | Conversation context |

**Key Distinction:**
- **Code graders** = Deterministic Python checks (implemented in code)
- **Model graders** = Claude Code's intelligence evaluating against rubrics (no separate code)

### Model Grader Rubrics

Claude uses these rubrics when evaluating model criteria. For each, pull the specified data and answer the evaluation questions.

#### PM Model Criteria

**`pm_routing_appropriate`**

| Aspect | Details |
|--------|---------|
| Data to pull | `get_delegation_graph()`, PM's system prompt, specialist descriptions |
| Evaluate | For each delegation: Does the task match the specialist's domain? Could another specialist have done it better? |
| Pass | All delegations go to appropriate specialists based on their descriptions |
| Fail | Task sent to wrong specialist, or specialist's domain doesn't match task |
| Evidence | List each delegation with specialist name and task summary |

**`pm_synthesis_quality`**

| Aspect | Details |
|--------|---------|
| Data to pull | `get_agent_final_message()`, all specialist outputs (via `get_file_io_trace()` or handoff analysis) |
| Evaluate | Does PM's final response incorporate key findings from all specialists? Is anything important omitted? Is the synthesis coherent? |
| Pass | Final response addresses user's request using specialist outputs appropriately |
| Fail | Missing key information, contradicts specialist findings, or incoherent combination |
| Evidence | Quote what specialists provided vs what PM synthesized |

**`pm_context_handoff`**

| Aspect | Details |
|--------|---------|
| Data to pull | `show_handoff(pm_run_id, specialist_run_id)` for each delegation |
| Evaluate | Did PM provide enough context for specialist to work autonomously? Did specialist have to guess or ask clarifying questions? |
| Pass | Specialist had sufficient context (user intent, relevant data, expected output) |
| Fail | Specialist lacked critical info, made incorrect assumptions, or produced off-target output due to missing context |
| Evidence | Quote PM's delegation message and note any context gaps |

#### Analyst Model Criteria

**`analyst_observation_complete`**

| Aspect | Details |
|--------|---------|
| Data to pull | Analyst's input (image/data), analyst's output file, analyst's protocol |
| Evaluate | Did analyst observe all aspects specified in their protocol? Any obvious elements missed? |
| Pass | All protocol-specified observation areas covered |
| Fail | Missed obvious elements or skipped protocol-required observations |
| Evidence | List what was observed vs what protocol requires |

**`analyst_finding_accuracy`**

| Aspect | Details |
|--------|---------|
| Data to pull | Analyst's input (image/data), analyst's findings |
| Evaluate | Are the stated findings actually present in the input? Do descriptions match reality? |
| Pass | Findings accurately describe what's in the input |
| Fail | Findings don't match input (wrong colors, wrong counts, wrong attributes) |
| Evidence | Quote specific findings and compare to actual input |

**`analyst_no_hallucination`**

| Aspect | Details |
|--------|---------|
| Data to pull | Analyst's input, analyst's output |
| Evaluate | Did analyst invent details not present in input? Did analyst claim to see things that aren't there? |
| Pass | All observations traceable to actual input |
| Fail | Contains fabricated details, invented attributes, or claims about non-existent elements |
| Evidence | Quote hallucinated content and note what input actually shows |

#### Specialist Model Criteria

**`specialist_domain_accuracy`**

| Aspect | Details |
|--------|---------|
| Data to pull | Specialist's output, domain protocol, upstream analyst findings |
| Evaluate | Is the specialist's output correct for the domain? Does it follow domain rules? Is it consistent with analyst findings? |
| Pass | Output is domain-appropriate, follows protocol rules, consistent with inputs |
| Fail | Domain errors, violates protocol rules, contradicts analyst findings |
| Evidence | Quote specific output and note domain issues |

#### Outcome Model Criteria (Workflow-Level)

**`workflow_outcome_achieved`**

| Aspect | Details |
|--------|---------|
| Data to pull | User's original request, PM's final response, any generated artifacts (files, listings, etc.) |
| Evaluate | Did the workflow achieve what the user asked for? Is the output complete and correct? |
| Pass | Output directly addresses user's request, contains expected elements, no critical omissions |
| Fail | Output misses user's intent, incomplete, or contains errors that defeat the purpose |
| Evidence | Quote user request, summarize what was delivered, note any gaps |

**Outcome vs Process:**
- Process graders: Did agents follow correct steps?
- Outcome grader: Did the result satisfy the user's goal?

**Outcome evaluation questions:**
1. What did the user ask for?
2. What was actually delivered?
3. Does delivery match request?
4. Any critical omissions or errors?
5. Would user accept this result?

---

## The /eval Skill

### Invocation

```bash
# Explicit modes
/eval analyze <trace_id>              # Score and investigate trace
/eval test <scenario>                 # Run scenario, evaluate result
/eval improve <agent>                 # Diagnose and fix agent
/eval trends                          # Analyze system-wide patterns
/eval replay                          # Replay production workflows

# Sub-modes
/eval analyze <trace_id> --quick      # Code graders only
/eval analyze <trace_id> --thorough   # Code + model criteria
/eval analyze <trace_id> --thread     # Multi-turn thread analysis
/eval analyze <trace_id> --compare <other>  # A/B comparison
/eval test <scenario> --save-baseline # Save as baseline
/eval test --batch <list>             # Run multiple scenarios
/eval replay --days 7 --success       # Replay recent successes
/eval replay --intent "catalog"       # Replay specific intent

# Implicit (Claude infers mode)
/eval trace123                        # Analyze mode
/eval "test PM with sneaker"          # Test mode
/eval "PM routes incorrectly"         # Investigate + improve
```

### Claude's Workflow

Claude reasons dynamically:

1. **What mode?** Explicit or infer from input
2. **What tools?** Select based on need
3. **What first?** Code graders for quick structural check
4. **What found?** Pass -> report, Fail -> investigate
5. **Known pattern?** Match -> suggest fix, New -> deeper analysis
6. **Can fix?** Suggest, implement with approval, validate
7. **Store learning?** New pattern -> add to library

---

## Pipeline

On-demand pipeline triggered by `/eval` invocation:

```
User runs PM workflow
        |
        v
Trace stored in LangSmith
        |
        v
User invokes /eval  <-- TRIGGER
        |
        v
Claude loads trace, grades, investigates
        |
        v
Claude suggests fixes
        |
        v
User approves
        |
        v
Claude implements fix
        |
        v
Claude validates
        |
        v
Results stored in LangSmith
```

### Usage Patterns

**Post-workflow check:**
```
/eval analyze abc123
```

**Something seems wrong:**
```
/eval analyze <trace> --thorough
```

**Before deploying prompt change:**
```
/eval test "catalog a sneaker" --save-baseline
```

**Systematic improvement:**
```
/eval improve pm
```

**Multi-turn workflow:**
```
/eval analyze <trace_id> --thread
```

**Production regression check:**
```
/eval replay --days 7 --success --limit 10
```

### Multi-Turn Evaluation

**Decision:** No special multi-turn infrastructure. Multi-turn = linked traces evaluated via workflow window.

#### Thread vs Workflow Distinction (CRITICAL)

| Concept | Scope | Lifetime |
|---------|-------|----------|
| Thread ID | WhatsApp conversation | Potentially forever (lifetime chat) |
| Session ID | LangSmith session | Also potentially very long |
| Workflow Window | Bounded time range | Hours around starting trace |

**The Problem:** Thread/session IDs can represent lifetime conversations with thousands of traces. Loading entire thread history is O(n) where n = entire conversation history - catastrophically slow.

**The Solution:** Workflow Window - bounded trace retrieval around a starting point.

**Approach:**

1. User provides starting trace (the trace they want to evaluate)
2. Use `get_workflow_window(trace_id)` to get bounded context (default: +/- 2 hours)
3. Window includes session boundary detection (gaps > 60 min)
4. Run code graders on each trace in window
5. Claude reasons about cross-trace concerns within the window

```python
from tests.tools.evaluation.helpers import get_workflow_window

# Get workflow context - O(window) not O(thread history)
window = get_workflow_window(trace_id, hours_before=2.0, hours_after=2.0)

for t in window:
    if t['session_break_before']:
        print("--- session boundary ---")
    marker = "*" if t['is_starting_trace'] else " "
    print(f"{marker} {t['trace_id'][:8]}: {t['start_time']}")
```

**Cross-trace concerns Claude evaluates:**
- **Context continuity:** Did PM remember prior conversation?
- **HITL handling:** Did PM respect user's approval/rejection/edit?
- **State progression:** Did workflow advance correctly across turns?
- **Error recovery:** Did PM handle mid-conversation failures?

**Session Boundary Detection:**

- Large gaps (>60 min by default) between traces indicate session boundaries
- Window functions mark these boundaries in results
- Helps distinguish "same workflow" from "different workflow in same thread"

**Efficient Navigation:**
```python
from tests.tools.evaluation.helpers import prev_trace, next_trace

# O(1) navigation with session boundary awareness
prev_id = prev_trace(trace_id)  # Stops at session boundaries
next_id = next_trace(trace_id)  # Stops at session boundaries

# Ignore boundaries if needed
prev_id = prev_trace(trace_id, session_gap_minutes=0)
```

#### Cross-Trace Model Rubrics

Claude uses these rubrics when evaluating `--thread` mode. For each, pull data from all traces in the thread.

**`thread_context_continuity`**

| Aspect | Details |
|--------|---------|
| Data to pull | Sequential PM messages across traces, user messages |
| Evaluate | Does PM reference prior conversation appropriately? Does PM avoid unnecessary repetition? Does PM maintain awareness of what was already discussed? |
| Pass | PM demonstrates awareness of conversation history without redundant re-explanation |
| Fail | PM acts as if each turn is new, repeats information already provided, or loses track of conversation state |
| Evidence | Quote PM references to prior context, note any context losses |

**`thread_hitl_respected`**

| Aspect | Details |
|--------|---------|
| Data to pull | HITL interrupt from trace N, user response, subsequent actions in trace N+1 |
| Evaluate | Did user approve, reject, or edit? Did specialist act accordingly? |
| Pass | Approved -> persisted; Rejected -> did not persist; Edited -> persisted with edits |
| Fail | Actions contradict HITL decision (e.g., persisted after rejection, ignored edits) |
| Evidence | HITL decision type, subsequent persist calls, data comparison if edited |

**`thread_state_progression`**

| Aspect | Details |
|--------|---------|
| Data to pull | Workflow state at end of each trace, delegations across traces |
| Evaluate | Did workflow advance correctly? No stuck loops? Proper completion? |
| Pass | Each trace moves workflow forward toward completion |
| Fail | Workflow stuck in loop, regresses, or fails to progress |
| Evidence | State transitions across traces, any repeated patterns |

**`thread_error_recovery`**

| Aspect | Details |
|--------|---------|
| Data to pull | Errors in any trace, subsequent traces in thread |
| Evaluate | If error occurred mid-conversation, did PM attempt recovery in next turn? |
| Pass | Error acknowledged and alternative approach taken, or graceful degradation |
| Fail | Error ignored, same failing approach repeated, or conversation abandoned |
| Evidence | Error details, recovery actions in subsequent traces |

**Example:**
```python
# Get all traces in a thread
outcomes = get_outcome_by_thread(thread_id)

# Grade each individually
for outcome in outcomes:
    grades = run_code_graders(outcome.trace_id)

# Claude reasons about the sequence
```

---

## Pattern Learning

The evaluation framework IS the learning system. When Claude fixes an issue, it stores the pattern.

| Activity | Mechanism |
|----------|-----------|
| Pattern recognition | Claude notes symptoms + fix when resolving |
| Pattern storage | LangSmith feedback (key: `pattern_fix`) |
| Pattern matching | During analysis, query historical fixes first |
| Trend analysis | Query workflow_outcomes |

### Implementation Decision

**Decision:** Use LangSmith Feedback API for pattern storage (no separate infrastructure).

**Rationale:**
- Zero new infrastructure - already using feedback for eval results
- Patterns tied to actual traces (evidence-backed)
- Searchable via `client.list_feedback(feedback_key="pattern_fix")`
- Pragmatic start; can formalize later if needed

**Storage Schema:**
```python
client.create_feedback(
    run_id=trace_root_run_id,
    key="pattern_fix",
    comment="PATTERN_NAME",  # e.g., "PROTOCOL_NOT_LOADED"
    correction={
        "symptoms": ["symptom1", "symptom2"],
        "agent": "affected_agent_name",
        "fix_location": "path/to/file.py or .prompt",
        "fix_description": "What was changed",
        "fix_diff": "Optional: actual diff or key changes",
        "success": True  # Did fix resolve issue?
    }
)
```

**Retrieval:**
```python
fixes = client.list_feedback(feedback_key="pattern_fix")
# Match current symptoms to known patterns
# Suggest fix based on historical success
```

### Common Patterns

| Pattern | Symptoms | Fix |
|---------|----------|-----|
| PROTOCOL_NOT_LOADED | First call not load_protocol, inconsistent behavior | Add protocol loading to prompt Process section |
| CONTEXT_LOSS | Child missing parent info | Fix PM delegation context/description |
| HITL_SKIPPED | Data persisted without approval | Add HITL gate to specialist interrupt_on |
| WRONG_ROUTING | Task to wrong agent | Fix PM routing logic or specialist descriptions |
| COGNITIVE_OVERLOAD | "Dream vs nightmare" behavior | Protocol-based decomposition |
| PREMATURE_TERMINATION | Incomplete research | Analyst thoroughness instructions |

---

## Metrics

| Metric | Target | Source |
|--------|--------|--------|
| Autonomy Score | 8.5/10 | workflow_outcomes |
| HITL Correction Rate | < 10% | Approval edits |
| Workflow Completion | > 90% | Trace terminal state |
| Time to Completion | < 2 min | Trace timing |

---

## Tools

### TraceLoader

```python
class TraceLoader:
    def load_overview(trace_id: str) -> TraceOverview
        # Level 0: Metadata only (~500 tokens)

    def load_for_eval(trace_id: str) -> TraceForEval
        # Level 1: Evaluation-ready (~2000 tokens)

    def load_full(trace_id: str) -> TraceFull
        # Level 2: Complete trace (~10000 tokens)

    def load_node(run_id: str) -> RunNode
        # Single node with INPUT/REASONING/OUTPUT

    def load_handoff(parent_id: str, child_id: str) -> HandoffAnalysis
        # Context handoff analysis
```

### ImageExtraction

Extract and compare images from traces - sources (user uploads) and generated outputs.

```python
from tests.tools.trace_analysis import get_trace_images, get_image_pairs, view_trace_images
from tests.tools.models import TraceImage, ImagePair

# Get ALL images from a trace (unified view)
images = get_trace_images(trace_id)
sources = [i for i in images if i.role == "source"]
generated = [i for i in images if i.role == "generated"]

# Get source-to-generated pairs (for comparison)
pairs = get_image_pairs(trace_id)
for p in pairs:
    print(f"Source: {p.source.storage_path if p.source else 'None'}")
    print(f"Generated: {p.generated.storage_path if p.generated else 'FAILED'}")
    print(f"Specs: {p.specs.get('fidelity', {})}")

# Quick summary
print(view_trace_images(trace_id))
```

**Models:**

| Model | Purpose |
|-------|---------|
| `TraceImage` | Single image with role, tool, agent context |
| `ImagePair` | Source + generated pair with specs used |

**Roles:**
- `source` - User upload or product image input
- `generated` - Output from image_studio
- `style_ref` - Style/mood reference image
- `background` - Background reference
- `variant` - Additional products for family shots

**Use cases:**
- Compare source vs generated for quality assessment
- Track which specs were used for each generation
- Debug failed generations (ImagePair.error)
- Understand image flow through workflow

### Graders

```
graders/
  base.py              # GraderResult, GraderSuiteResult
  pm_graders.py        # PM-specific code graders
  specialist_graders.py # Specialist/Analyst code graders
  orchestrator.py      # run_code_graders(), run_pm_graders()
```

**Code Graders (Implemented):**
- `protocol_load_first` - Agent loaded protocol first
- `media_download_first` - PM downloaded media before delegation
- `analyst_before_specialist` - Two-phase delegation pattern
- `wave_execution_correct` - Wave structure (needs taxonomy refactor)
- `file_read_before_synthesis` - PM read outputs before synthesizing
- `hitl_triggered` - Specialist requested approval before persist

**Code Graders (Additional Implemented):**
- `specialist_read_upstream` - Specialist read analyst findings
- `specialist_hitl_respected` - Honored HITL decision (full verification requires thread context)
- `error_recovery_attempted` - Universal: Recovery attempted after tool error

**Creative Specialist Graders (Implemented):**

- `image_studio_fidelity_included` - Fidelity spec present (product identity protection)
- `image_studio_core_specs_included` - Core specs present (prevents garbage output)
- `image_studio_output_verified` - view_image called after generation (quality check)

**Code Graders (Planned):**

- `specialist_verified_before_act` - Verification before write

**Model Graders (Claude Reasoning - No Code):**
- See "Model Grader Rubrics" section above
- PM: `pm_routing_appropriate`, `pm_synthesis_quality`, `pm_context_handoff`
- Analyst: `analyst_observation_complete`, `analyst_finding_accuracy`, `analyst_no_hallucination`
- Specialist: `specialist_domain_accuracy`
- Workflow: `workflow_outcome_achieved`

### EvalStorage

```python
class EvalStorage:
    def store_result(result: EvalResult) -> str
    def get_history(scenario_id: str) -> list[EvalResult]
    def get_baseline(scenario_id: str) -> EvalResult
    def set_baseline(result_id: str) -> None
    def detect_regression(current, baseline) -> RegressionReport
```

### Baseline Workflow

**Decision:** Keep it simple - baseline = any trace Claude judges as "good" after manual review.

**Process:**
1. Run scenario: `/eval test PM-01`
2. Claude analyzes result (code graders + model criteria)
3. If Claude judges trace as good reference: `/eval test PM-01 --save-baseline`
4. Baseline stored, future runs compared against it

**No automated criteria.** Claude uses judgment considering:
- All code graders pass
- Model criteria look reasonable
- Workflow completed successfully
- Output quality acceptable

**Baseline updates:** Manual only. Claude proposes update when a better trace exists.

### PatternLibrary

**Implementation:** LangSmith Feedback API (no separate class needed).

```python
# Store pattern (in eval_results.py)
def store_pattern_fix(
    trace_id: str,
    pattern_name: str,
    symptoms: list[str],
    agent: str,
    fix_location: str,
    fix_description: str,
    success: bool = True
) -> bool

# Retrieve patterns (in eval_results.py)
def get_pattern_fixes(
    pattern_name: str | None = None,
    agent: str | None = None,
    limit: int = 50
) -> list[dict]

# Match symptoms to known patterns (Claude reasoning)
# No code - Claude matches based on retrieved patterns
```

---

## Implementation Plan

### Phase 1: Data Models

| Task | Status | Description |
|------|--------|-------------|
| 1.1 | Done | Define `EvalResult` schema |
| 1.2 | Done | Define `GraderResult` schema |
| 1.3 | Done | Define `TraceForEval` schema |
| 1.4 | Done | Define `Pattern` schema (using LangSmith feedback) |

### Phase 2: Trace Loader

| Task | Status | Description |
|------|--------|-------------|
| 2.1 | Done | Implement `TraceLoader` / `load_trace_for_eval()` |
| 2.2 | Done | Implement hierarchical load methods (L0/L1/L2) |
| 2.3 | Done | Implement handoff analysis helpers |

### Phase 3: Graders

| Task | Status | Description |
|------|--------|-------------|
| 3.1 | Done | Implement base grader classes |
| 3.2 | Done | Implement PM code graders (5) |
| 3.3 | Done | Implement GradingOrchestrator |
| 3.4 | Done | Refactor `pm_wave_execution` to taxonomy-based approach |
| 3.5 | Done | Register `analyst_protocol_first` in ANALYST_GRADERS |
| 3.6 | Done | Register `specialist_protocol_loaded` in SPECIALIST_GRADERS |
| 3.7 | Done | Implement `specialist_read_upstream` grader |
| 3.8 | Planned | Implement `specialist_verified_before_act` grader |
| 3.9 | Done | Implement `specialist_hitl_respected` grader |
| 3.10 | Done | Implement `error_recovery_attempted` grader (universal) |
| 3.11 | N/A | Model graders = Claude reasoning with rubrics (no code needed) |

### Phase 4: Storage & Patterns

| Task | Status | Description |
|------|--------|-------------|
| 4.1 | Done | Implement `EvalStorage` (eval_results.py) |
| 4.2 | Done | Add `store_pattern_fix()` to eval_results.py |
| 4.3 | Done | Add `get_pattern_fixes()` to eval_results.py |
| 4.4 | Pending | Seed common patterns after first few fixes |

### Phase 5: Validation

| Task | Status | Description |
|------|--------|-------------|
| 5.1 | Pending | Test all modes on real traces |
| 5.2 | Pending | Establish baselines for PM-01 to PM-04 |
| 5.3 | Pending | Document initial patterns from first fixes |

---

## Directory Structure

```
tests/
  tools/
    models.py              # All data models
    trace_loader.py        # TraceForEval, load_trace_for_eval()
    trace_analysis.py      # Hierarchical trace analysis (L0/L1/L2)
    eval_results.py        # EvalStorage, pattern functions
    workflow_outcomes.py   # Production data bridge
    replay_runner.py       # Production replay orchestration
    graders/
      __init__.py
      base.py              # GraderResult, GraderSuiteResult
      pm_graders.py        # PM code graders
      specialist_graders.py # Specialist/Analyst code graders
      orchestrator.py      # run_code_graders()
    evaluation/
      helpers.py           # REPL helpers (show_node, detect_issues, etc.)
  scenarios/
    schema.py              # ScenarioDefinition
    loader.py              # load_scenario(), list_scenarios()
    pm/
      PM-01.yaml           # Core scenarios
      PM-02.yaml
      PM-03.yaml
      PM-04.yaml

.claude/skills/eval/
  SKILL.md                 # /eval skill definition
```

---

## Success Criteria

**Week 1:**
- Baselines established for core scenarios
- Claude can detect regressions
- First patterns documented

**Month 1:**
- 10+ patterns in library
- Common failures have known fixes
- At least one metric improved

**Quarter 1:**
- Pattern library covers most failure modes
- System autonomy measurably improved
- Debugging time significantly reduced
