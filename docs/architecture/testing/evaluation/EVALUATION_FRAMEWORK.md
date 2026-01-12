# Evaluation Framework

**Version:** 1.0
**Date:** 2026-01-12

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
          |
          +-- TOOLS
          |     +-- trace_loader    - Load traces at any detail level
          |     +-- graders         - Run code and model graders
          |     +-- scenario_runner - Execute scenarios against PM
          |     +-- eval_storage    - Store/retrieve results
          |     +-- pattern_library - Match/store failure patterns
          |
          +-- KNOWLEDGE
                +-- Agent behaviors - What good looks like per agent type
                +-- Evaluation rubric - How to score
                +-- Failure patterns - Common issues and fixes
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

| Criterion | Type | Description |
|-----------|------|-------------|
| `pm_protocol_first` | Code | Loaded protocol before any delegation |
| `pm_media_download_first` | Code | Downloaded media before delegation |
| `pm_wave_execution` | Code | Correct parallel/serial wave structure |
| `pm_analyst_before_specialist` | Code | Two-phase: research before execution |
| `pm_file_read_before_synthesis` | Code | Read analysis files before synthesizing |
| `pm_routing_appropriate` | Model | Delegated to correct agents |
| `pm_synthesis_quality` | Model | Effectively combined specialist outputs |
| `pm_context_handoff` | Model | Passed sufficient context to delegated agents |

**Analyst Criteria:**

| Criterion | Type | Description |
|-----------|------|-------------|
| `analyst_protocol_first` | Code | Loaded domain protocol before analysis |
| `analyst_observation_complete` | Model | Observed all relevant aspects |
| `analyst_finding_accuracy` | Model | Findings match actual content |
| `analyst_file_written` | Code | Wrote findings to file |
| `analyst_no_hallucination` | Model | No fabricated observations |

**Specialist Criteria:**

| Criterion | Type | Description |
|-----------|------|-------------|
| `specialist_protocol_first` | Code | Loaded domain protocol before execution |
| `specialist_verified_before_act` | Code | Called verification tools before write |
| `specialist_read_upstream` | Code | Read relevant analyst findings |
| `specialist_hitl_triggered` | Code | Requested approval before persisting |
| `specialist_hitl_respected` | Code | Honored approval/rejection/edit |
| `specialist_domain_accuracy` | Model | Domain-specific output quality |

### Grading Strategy

Layered approach - code graders first, model graders for depth:

```
1. Run code graders (fast, free)
   |
   +-- All pass? Quick check done
   |
   +-- Failures? Know what's structurally wrong
         |
         +-- Run model graders for severity/quality
         |
         +-- Investigate root cause
```

| Layer | Purpose | Speed | Cost |
|-------|---------|-------|------|
| Code graders | Rule violations | Fast (ms) | Free |
| Model graders | Quality issues | Slow (sec) | Tokens |

---

## The /eval Skill

### Invocation

```bash
# Explicit modes
/eval analyze <trace_id>              # Score and investigate trace
/eval test <scenario>                 # Run scenario, evaluate result
/eval improve <agent>                 # Diagnose and fix agent
/eval trends                          # Analyze system-wide patterns

# Sub-modes
/eval analyze <trace_id> --quick      # Code graders only
/eval analyze <trace_id> --thorough   # Full grader suite
/eval analyze <trace_id> --compare <other>  # A/B comparison
/eval test <scenario> --save-baseline # Save as baseline
/eval test --batch <list>             # Run multiple scenarios

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

---

## Pattern Learning

The evaluation framework IS the learning system. When Claude fixes an issue, it stores the pattern.

| Activity | Mechanism |
|----------|-----------|
| Pattern recognition | Claude notes symptoms + fix when resolving |
| Pattern storage | LangSmith feedback |
| Pattern matching | During analysis, check known patterns first |
| Trend analysis | Query workflow_outcomes |

**Common Patterns:**

| Pattern | Symptoms | Fix |
|---------|----------|-----|
| PROTOCOL_NOT_LOADED | Inconsistent behavior | Add protocol loading to prompt |
| CONTEXT_LOSS | Child missing parent info | Fix PM delegation context |
| HITL_SKIPPED | Data persisted without approval | Add HITL gate to specialist |
| WRONG_ROUTING | Task to wrong agent | Fix PM routing logic |
| COGNITIVE_OVERLOAD | "Dream vs nightmare" behavior | Protocol-based decomposition |

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

### Graders

```
graders/
  base.py           # GraderResult, BaseGrader
  code_graders.py   # Deterministic checks
  model_graders.py  # LLM-as-judge evaluations
  orchestrator.py   # GradingOrchestrator
```

**Code Graders:**
- `protocol_load_first`
- `media_download_first`
- `analyst_before_specialist`
- `wave_execution`
- `hitl_triggered`
- `hitl_respected`
- `schema_compliance`
- `error_free`

**Model Graders:**
- `intent_classification`
- `context_utilization`
- `hallucination_check`
- `synthesis_quality`
- `helpfulness`

### EvalStorage

```python
class EvalStorage:
    def store_result(result: EvalResult) -> str
    def get_history(scenario_id: str) -> list[EvalResult]
    def get_baseline(scenario_id: str) -> EvalResult
    def set_baseline(result_id: str) -> None
    def detect_regression(current, baseline) -> RegressionReport
```

### PatternLibrary

```python
class PatternLibrary:
    def match(symptoms: list[str]) -> Pattern | None
    def store(pattern: Pattern) -> None
    def list() -> list[Pattern]
```

---

## Implementation Plan

### Phase 1: Data Models

| Task | Description |
|------|-------------|
| 1.1 | Define `EvalResult` schema |
| 1.2 | Define `GraderResult` schema |
| 1.3 | Define `TraceForEval` schema |
| 1.4 | Define `Pattern` schema |

### Phase 2: Trace Loader

| Task | Description |
|------|-------------|
| 2.1 | Implement `TraceLoader` class |
| 2.2 | Implement load methods |
| 2.3 | Implement handoff analysis |

### Phase 3: Graders

| Task | Description |
|------|-------------|
| 3.1 | Implement base grader classes |
| 3.2 | Implement code graders |
| 3.3 | Implement model graders |
| 3.4 | Implement GradingOrchestrator |

### Phase 4: Storage & Patterns

| Task | Description |
|------|-------------|
| 4.1 | Implement `EvalStorage` |
| 4.2 | Implement `PatternLibrary` |
| 4.3 | Seed common patterns |

### Phase 5: Validation

| Task | Description |
|------|-------------|
| 5.1 | Test all modes on real traces |
| 5.2 | Establish baselines |
| 5.3 | Document initial patterns |

---

## Directory Structure

```
tests/tools/
  models.py
  trace_loader.py
  trace_analysis.py
  scenario_runner.py
  eval_storage.py
  graders/
    __init__.py
    base.py
    code_graders.py
    model_graders.py
    orchestrator.py

.claude/skills/eval/
  SKILL.md
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
