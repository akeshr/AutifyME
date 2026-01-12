# /eval - Unified Evaluation Skill

## Purpose

Make AutifyME system better: higher autonomy, fewer HITL corrections, faster completion, no regressions.

This is the single entry point for all evaluation activities. Claude Code reasons about approach; this skill provides tools and knowledge.

---

## Modes

| Mode | Purpose | When Used |
|------|---------|-----------|
| `analyze` | Score, investigate, compare existing traces | Have trace_id, want to understand quality |
| `test` | Execute scenarios, generate new traces | Want to validate behavior with controlled input |
| `improve` | Diagnose and fix agent issues | Found problem, need to fix it |
| `trends` | Analyze workflow_outcomes for patterns | Want system-wide insights |
| (implicit) | Claude infers from context | User describes need, Claude determines mode |

---

## Invocation

```bash
# Explicit modes
/eval analyze <trace_id>              # Score and investigate trace
/eval test <scenario>                 # Run scenario, evaluate result
/eval improve <agent>                 # Diagnose and fix agent
/eval trends                          # Analyze system-wide patterns

# Sub-modes
/eval analyze <trace_id> --quick      # Fast sanity check (code graders only)
/eval analyze <trace_id> --thorough   # Full grader suite
/eval analyze <trace_id> --compare <other_trace>  # A/B comparison
/eval test <scenario> --save-baseline # Run and save as baseline
/eval test --batch <scenario_list>    # Run multiple scenarios

# Implicit (Claude infers)
/eval trace123                        # Analyze mode
/eval "test PM with sneaker image"    # Test mode
/eval "PM is routing incorrectly"     # Investigate then improve
```

---

## Tools Available

### trace_loader
Load traces from LangSmith at different detail levels:
- `load_overview(trace_id)` - Level 0: Metadata only (~500 tokens)
- `load_for_eval(trace_id)` - Level 1: Evaluation-ready (~2000 tokens)
- `load_full(trace_id)` - Level 2: Complete trace (~10000 tokens)
- `load_node(run_id)` - Single node with INPUT/REASONING/OUTPUT
- `load_handoff(parent_id, child_id)` - Context handoff analysis

### graders
Run evaluation checks:
- Code graders: Fast, deterministic, catch rule violations
- Model graders: Semantic evaluation, quality assessment

### scenario_runner
Execute scenarios against PM:
- `run_scenario(scenario)` - Execute single scenario
- `run_conversation(messages, media)` - Multi-turn interaction
- `replay_production(trace_id)` - Replay production scenario

### eval_storage
Store and retrieve evaluation results:
- `store_result(result)` - Store evaluation in LangSmith
- `get_history(scenario_id)` - Historical results
- `get_baseline(scenario_id)` - Known-good baseline
- `set_baseline(result_id)` - Promote to baseline
- `detect_regression(current, baseline)` - Compare against baseline

### pattern_library
Manage failure patterns:
- `match(symptoms)` - Find matching known pattern
- `store(pattern)` - Add new pattern
- `list()` - All known patterns

---

## Knowledge

### Architecture

```
PM (Project Manager - Orchestrator)
  |
  +-- Analysts (Read-Only Research Layer)
  |     +-- visual_analyst    - Image/visual analysis
  |     +-- product_analyst   - External market research
  |     +-- catalog_analyst   - Internal catalog lookup
  |
  +-- Specialists (Execution Layer with HITL)
        +-- creative_specialist - Asset generation
        +-- catalog_specialist  - Data persistence
```

### What Good Looks Like

**PM:**
- Protocol loaded FIRST (before any delegation)
- Media downloaded FIRST (before delegation when image present)
- Correct wave execution (analysts parallel, then specialists)
- Two-phase: analysts before specialists
- Files read before synthesis
- Open-ended questions (not numbered options)
- Good context handoff to delegated agents

**Analysts:**
- Protocol loaded first
- Complete observations
- Accurate findings (no hallucination)
- Findings written to FILE (not just returned)
- Correct file format

**Specialists:**
- Protocol loaded first
- Read upstream analyst findings
- Verified before acting
- HITL triggered before persisting
- HITL decision respected (approval/rejection/edit)
- Domain-accurate output

### Common Failure Patterns

| Pattern | Symptoms | Fix |
|---------|----------|-----|
| PROTOCOL_NOT_LOADED | Inconsistent behavior, missing domain reasoning | Add protocol loading to prompt |
| CONTEXT_LOSS | Child missing info parent had | Fix PM delegation context |
| HITL_SKIPPED | Data persisted without approval | Add HITL gate to specialist |
| WRONG_ROUTING | Task to wrong agent | Fix PM routing logic |
| PREMATURE_TERMINATION | Research tools unused | Fix analyst thoroughness |
| COGNITIVE_OVERLOAD | "Dream vs nightmare" behavior | Protocol-based decomposition |

### Metrics That Matter

| Metric | Target | Source |
|--------|--------|--------|
| Autonomy Score | 8.5/10 | workflow_outcomes |
| HITL Correction Rate | < 10% | Approval edits |
| Workflow Completion | > 90% | Trace terminal state |
| Time to Completion | < 2 min | Trace timing |

---

## Evaluation Approach

### Pillars (Universal)

Every agent evaluated on same 5 pillars:
1. **UNDERSTAND** - Did agent understand its input?
2. **REASON** - Did agent reason correctly?
3. **ACT** - Did agent take right actions?
4. **COMMUNICATE** - Did agent communicate properly?
5. **RECOVER** - Did agent handle errors?

### Grading Strategy (Layered)

```
1. Run code graders (fast, free)
   |
   +-- All pass? Quick check done
   |
   +-- Failures? Already know what's structurally wrong
         |
         +-- Run model graders for severity/quality assessment
         |
         +-- Investigate root cause
```

### Agent-Specific Checks

Same pillars, different checks per agent type:

**ACT pillar example:**
- PM: Routed correctly? Correct waves?
- Analyst: Observed thoroughly? Wrote to file?
- Specialist: Verified first? Triggered HITL?

---

## Workflow

Claude reasons dynamically (NOT rigid phases):

1. **What mode?** Explicit or infer from input
2. **What tools?** Select based on mode and need
3. **What first?** Code graders for quick structural check
4. **What did I find?** Pass -> report, Fail -> investigate
5. **Known pattern?** Match -> suggest fix, New -> deeper analysis
6. **Can I fix?** Suggest fix, implement with approval, validate
7. **Store learning?** New pattern -> add to pattern library

**Freedom to deviate:** If analysis reveals need to test, shift. If test reveals need to improve, shift. Modes prime but don't constrain.

---

## Output Format

### Analyze Mode Output

```
## Trace Analysis: <trace_id>

**Verdict:** PASS | NEEDS_IMPROVEMENT | FAILED

### Grader Results
| Grader | Result | Evidence |
|--------|--------|----------|
| protocol_load_first | PASS | First call was load_protocol |
| ... | ... | ... |

### Issues Found
1. [Issue description with evidence]

### Recommendations
1. [Specific actionable recommendation]

### Next Steps
- [What user should do next]
```

### Test Mode Output

```
## Test Result: <scenario>

**Trace ID:** <new_trace_id>
**Verdict:** PASS | FAIL

### Comparison to Baseline
| Metric | Baseline | Current | Delta |
|--------|----------|---------|-------|
| ... | ... | ... | ... |

### Regressions Detected
- [Any regressions]

### Recommendations
- [What to do if failed]
```

### Improve Mode Output

```
## Improvement: <agent>

### Diagnosis
[Root cause analysis]

### Proposed Fix
[Specific changes to make]

### Validation Plan
[How to verify fix works]

---
Awaiting approval to implement fix.
```

---

## Related Resources

- Design doc: `docs/architecture/testing/evaluation/UNIFIED_EVAL_REDESIGN.md`
- Trace tools: `tests/tools/trace_analysis.py`, `tests/tools/trace_loader.py`
- Graders: `tests/tools/graders/` (to be implemented)
- Models: `tests/tools/models.py`
