# Universal Evaluation Framework for AutifyME

> **SUPERSEDED**: This document series (00-10) has been superseded by the unified design.
>
> **New Source of Truth**: [`UNIFIED_EVAL_REDESIGN.md`](UNIFIED_EVAL_REDESIGN.md)
>
> **Key Changes:**
> - 5 skills consolidated into single `/eval` skill with modes (analyze, test, improve, trends)
> - On-demand pipeline (Claude Code + LangSmith only, no CI/CD)
> - Evaluation framework IS the learning system
> - Goal-oriented skill, not procedural
> - Layered grading: code graders first, model graders for depth
>
> These docs remain for historical reference. For implementation, use the unified design.

---

**Date**: 2026-01-11
**Status**: SUPERSEDED - See UNIFIED_EVAL_REDESIGN.md
**Version**: 4.1 - Claude Code as Judge (legacy)

---

## Overview

A **universal evaluation framework** for measuring and continuously improving ANY agent behavior across the AutifyME system.

```text
+===========================================================================+
|                    COMPLETE ARCHITECTURE (v4.1)                           |
+===========================================================================+
|                                                                           |
|  LANGSMITH FOUNDATION (with local fallback)                               |
|  - Local-first tracing with async LangSmith sync                          |
|  - Datasets for scenario storage (versioned)                              |
|  - Annotation queues with SLA management                                  |
|                                                                           |
|  CLAUDE CODE AS JUDGE (Primary)                                           |
|  - /evaluate skill: Claude Code IS the evaluator                          |
|  - Rubric-based scoring with evidence                                     |
|  - Nuanced 0.0-1.0 scores with reasoning                                  |
|                                                                           |
|  MODEL-FIRST GRADER ARCHITECTURE                                          |
|  - Model graders (~70%): Intent, routing, synthesis, helpfulness          |
|  - Code graders (~30%): Schema, HITL, DB state (structural only)          |
|  - Human graders: Calibration, edge cases (5-10% sample)                  |
|                                                                           |
|  OUTPUT-ONLY GRADING (Default)                                            |
|  - Grade final output, not path taken                                     |
|  - Path deviations logged but not scored                                  |
|  - PATH_STRICT only for safety-critical (HITL)                            |
|                                                                           |
|  SKILL ECOSYSTEM (Claude Code)                                            |
|  - /evaluate: PRIMARY - Claude Code as Judge (development)                |
|  - /e2e-testing: Orchestrate automated evaluation (CI/CD)                 |
|  - /workflow-evaluation: Deep failure investigation                       |
|  - /agent-improvement: Fix implementation & validation                    |
|  - /eval-writer: Scenario generation (6 modes, 7 quality gates)           |
|  - /eval-coverage: Gap analysis and prioritization                        |
|                                                                           |
|  SECURITY & BOUNDARY TESTING (Category 7)                                 |
|  - Prompt injection resistance                                            |
|  - Tenant isolation verification                                          |
|  - Sensitive data leak prevention                                         |
|                                                                           |
|  OPERATIONAL CONTROLS                                                     |
|  - Cost tracking with budget caps                                         |
|  - ROI-based investigation prioritization                                 |
|  - Human review SLA with auto-fallback                                    |
|  - Scenario versioning with migration                                     |
|                                                                           |
+===========================================================================+
```

---

## Core Philosophy

**Key Insight**: Claude Code IS the judge. No separate "Judge Agent" needed.

From Anthropic's "Demystifying Evals for AI Agents" + our Model-First approach:

- **Start from failures**: Real failures become test cases
- **Grade outputs, not paths**: Agents find creative solutions
- **Model-first, code for verification**: LLM intelligence primary (~70%), code for structural checks (~30%)
- **Balanced problem sets**: Test both positive and negative cases
- **Continuous measurement**: Capability evals graduate to regression suites

---

## Document Structure

| Document | Purpose | Key Topics |
|----------|---------|------------|
| [01_LANGSMITH_FOUNDATION.md](01_LANGSMITH_FOUNDATION.md) | Observability layer | Trace capture, datasets, fallback mechanism |
| [02_FAILURE_TAXONOMY.md](02_FAILURE_TAXONOMY.md) | What can go wrong | Five pillars, agent-specific profiles |
| [03_GRADER_ARCHITECTURE.md](03_GRADER_ARCHITECTURE.md) | How to evaluate | Code/Model/Human graders, output-only mode |
| [04_SCENARIO_FRAMEWORK.md](04_SCENARIO_FRAMEWORK.md) | Test case design | 7 categories including security |
| [05_INTELLIGENCE_LAYER.md](05_INTELLIGENCE_LAYER.md) | Deep analysis | Claude investigation, fix generation |
| [06_EVALUATION_PIPELINE.md](06_EVALUATION_PIPELINE.md) | Execution flow | Pipeline, improvement loop, metrics |
| [07_OPERATIONAL_GUIDE.md](07_OPERATIONAL_GUIDE.md) | Running in production | Cost, HITL testing, versioning, CLI |
| [08_SCHEMAS.md](08_SCHEMAS.md) | **Data models** | **Single source of truth for all schemas** |
| [09_IMPLEMENTATION_GUIDE.md](09_IMPLEMENTATION_GUIDE.md) | **How to build** | **Bootstrap order, dependencies, contracts** |
| [10_SKILL_ARCHITECTURE.md](10_SKILL_ARCHITECTURE.md) | **LLM as Judge** | **Skill ecosystem, eval-writer, invocation contracts** |

---

## The Four Layers

| Layer | Role | Components | When Active |
|-------|------|------------|-------------|
| **LangSmith** | Observability | Traces, Datasets, Annotation Queues | Always (every run) |
| **Grader** | Automated Eval | Code Graders, Model Graders | On eval trigger |
| **Intelligence** | Deep Analysis | Claude via skills | On failures |
| **Improvement** | Enhancement | Tracker, Validator | Post-analysis |

---

## Three Evaluation Modes

| Mode | Method | Executes PM? | Use Case |
|------|--------|--------------|----------|
| **Scenario Execution** | `pipeline.run()` | Yes | Regression testing, capability validation |
| **Direct Trace Evaluation** | `pipeline.run_monitoring()` | No | Continuous monitoring, historical analysis |
| **Trace-to-Scenario** | `langsmith.convert_feedback_to_scenario()` | No | Build regression suite from production failures |

**Key Insight**: Not all evaluation requires re-execution. Direct Trace Evaluation grades existing production traces for continuous quality monitoring without the cost of re-running scenarios.

---

## Data Flow

```text
                              PRODUCTION
+------------------------------------------------------------------------+
|  User Message --> PM --> Specialists --> Tools --> Response             |
|                     |                                                   |
|                     v                                                   |
|              [LANGSMITH TRACE]                                          |
+------------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------------+
|                        EVALUATION TRIGGER                               |
|  - Scheduled (daily regression)                                         |
|  - On-demand (new feature validation)                                   |
|  - On-commit (CI/CD integration)                                        |
+------------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------------+
|                         GRADER LAYER                                    |
|  +------------------+  +------------------+  +------------------+        |
|  | CODE GRADERS     |  | MODEL GRADERS    |  | HUMAN GRADERS    |       |
|  | (Preferred)      |  | (When nuance)    |  | (Calibration)    |       |
|  +------------------+  +------------------+  +------------------+        |
|                              |                                          |
|                    [PASS/FAIL + SCORES]                                 |
+------------------------------------------------------------------------+
                              |
              +---------------+---------------+
              |                               |
              v (PASS)                        v (FAIL)
+-------------------------+    +------------------------------------------+
| UPDATE BASELINE         |    |           INTELLIGENCE LAYER             |
| - Store new scores      |    |  1. Load trace (L0 -> L1 -> L2)          |
| - Graduate to regression|    |  2. Identify root cause                  |
+-------------------------+    |  3. Generate fix hypothesis              |
                               |  4. Create regression scenarios          |
                               +------------------------------------------+
                                              |
                                              v
                               +------------------------------------------+
                               |          IMPROVEMENT LAYER               |
                               |  1. Implement proposed fix               |
                               |  2. Run k-out-of-n validation            |
                               |  3. If pass: update baseline             |
                               |  4. Document pattern for future          |
                               +------------------------------------------+
```

---

## Quick Start

```bash
# 1. Ensure LangSmith is configured
export LANGCHAIN_API_KEY=<your-key>
export LANGCHAIN_PROJECT=autifyme-evals

# 2. Create initial scenarios from real failures
uv run python -m tests.evaluation.cli create-from-failures --hours 24

# 3. Run first evaluation
uv run python -m tests.evaluation.cli run --suite initial --parallelism 5

# 4. Review report and investigation
uv run python -m tests.evaluation.cli report --latest

# 5. Validate fixes
uv run python -m tests.evaluation.cli validate --all-pending
```

---

## Success Criteria

### Framework Health

| Metric | Target | Measurement |
|--------|--------|-------------|
| Grader accuracy | >90% agreement with human | LangSmith calibration |
| Coverage | All 5 pillars + security tested | Scenario audit |
| Regression detection | <1 day latency | CI integration |
| Investigation success | >50% | Validated fixes / total |
| Pattern reuse | >30% | Known patterns matched |

### System Health (via evals)

| Metric | Initial Target | Stretch Target | Notes |
|--------|----------------|----------------|-------|
| Intent classification | >90% | >98% | |
| Routing accuracy | >90% | >98% | |
| Context utilization | >80% | >95% | |
| HITL compliance | 100% | 100% | |
| Schema compliance | 100% | 100% | |
| Hallucination rate | <10% | <2% | |
| pass^3 (consistency) | >80% | >95% | **See note below** |

**pass^k Applicability Note**: pass^k measures consistency across k runs. Use pass^k ONLY for:
- **Deterministic checks**: State changes, schema compliance, HITL compliance
- **Do NOT use** for semantic quality (use pass@k instead - passes at least once in k tries)

For non-deterministic outputs (response wording, creative content), semantic equivalence varies run-to-run. This is expected and not a consistency failure.

---

## Integration Points

| System | Integration | Purpose |
|--------|-------------|---------|
| **LangSmith** | Native SDK | Trace capture, datasets, annotation queues |
| **chat_with_pm** | Direct call | Scenario execution |
| **Claude Skills** | workflow-evaluation, agent-improvement | Intelligence layer |
| **Supabase** | Storage | Baselines, scenarios, improvements |
| **CI/CD** | GitHub Actions | Regression on commit |

---

## Skill Integration

**Full specification**: [10_SKILL_ARCHITECTURE.md](10_SKILL_ARCHITECTURE.md)

```yaml
# evaluate skill - PRIMARY (NEW)
/evaluate:
  purpose: Claude Code as Judge - development-time evaluation
  modes:
    - single: Evaluate one trace against rubric
    - batch: Evaluate multiple traces
    - comparative: A/B comparison
  rubrics: intent, routing, synthesis, tool_usage, helpfulness
  output: Score (0.0-1.0) + Reasoning + Evidence

# e2e-testing skill - automation entry point (REWRITE)
/e2e-testing:
  - Orchestrate automated evaluation cycle (CI/CD)
  - Load scenarios, execute, grade
  - On failures: invoke /workflow-evaluation
  - On gaps: invoke /eval-coverage

# workflow-evaluation skill - deep investigation (REWRITE)
/workflow-evaluation:
  - Hierarchical trace loading (L0 -> L1 -> L2)
  - Token-budgeted investigation
  - Pattern matching against known failures
  - Root cause + fix proposal generation
  - On approval: invoke /agent-improvement

# agent-improvement skill - fix implementation (REWRITE)
/agent-improvement:
  - Apply fix proposal to codebase
  - Run k-out-of-n validation
  - Update baseline on success
  - Document pattern for reuse
  - Create regression scenario via /eval-writer

# eval-writer skill - scenario generation (NEW)
/eval-writer:
  modes:
    - from-trace: Production trace -> scenario
    - from-failure: Investigation -> regression scenario
    - from-spec: Feature doc -> capability scenarios
    - from-gap: Coverage gap -> synthetic scenarios
    - adversarial: Security -> attack scenarios
    - mutate: Existing -> edge case variations
  quality_gates:
    - Schema validation
    - Grader appropriateness
    - Dry run (pass@1)
    - Consistency check (pass^3)
    - Balance check
    - Duplicate check
    - Abstraction validation

# eval-coverage skill - gap analysis (NEW)
/eval-coverage:
  - Map scenarios to 5 failure pillars
  - Map scenarios to 7 categories
  - Identify and prioritize gaps
  - Invoke /eval-writer to fill gaps
```

---

## Key Principles

- **Claude Code IS the judge**: Use /evaluate skill for development-time evaluation
- **Model-first, code for verification**: LLM intelligence (~70%), structural checks (~30%)
- **Start small**: 20-50 scenarios from real failures
- **Grade outputs, not paths**: Let agents find creative solutions
- **Continuous measurement** beats big-bang evaluation
- **Let Claude investigate failures**: Deep analysis on what matters
