# Failure Taxonomy

**Part of**: [Universal Evaluation Framework](00_INDEX.md)

---

## Overview

Every agent failure falls into one of five categories. Understanding these pillars is essential for designing comprehensive evaluation scenarios and choosing appropriate graders.

---

## The Five Pillars of Agent Failure

```text
+------------------+------------------+------------------+------------------+------------------+
|   UNDERSTAND     |     REASON       |      ACT         |    COMMUNICATE   |     RECOVER      |
+------------------+------------------+------------------+------------------+------------------+
| Intent parsing   | Logic errors     | Tool selection   | Output quality   | Error handling   |
| Context reading  | Hallucination    | Tool parameters  | Synthesis        | Graceful degrade |
| Reference resol. | Constraint viol. | Tool sequencing  | HITL compliance  | Escalation       |
| Multi-turn state | Over/under conf. | Execution errors | Feedback integr. | State recovery   |
+------------------+------------------+------------------+------------------+------------------+
```

---

## Universal Failure Matrix

| Pillar | Failure Type | Applies To | Detection Method | Grader Type |
|--------|--------------|------------|------------------|-------------|
| **UNDERSTAND** | Intent misclassification | PM | Compare routed vs expected specialist | Code |
| | Ambiguity not detected | PM | Check for clarification when ambiguous | Model |
| | Multi-intent missed | PM | Count intents handled vs present | Code |
| | Context ignored | All | Compare context in vs context used | Model |
| | Reference unresolved | PM | Check "this", "it" resolution | Model |
| | Media not processed | PM, Analysts | Check media handling in trace | Code |
| **REASON** | Hallucination | All | Compare claims to source data | Model |
| | Wrong conclusion | Analysts, Specialists | Compare output to ground truth | Code/Model |
| | Constraint violation | Specialists | Validate against business rules | Code |
| | Overconfidence | Analysts | Compare confidence to accuracy | Model |
| | Underconfidence | Analysts | Check unnecessary escalations | Model |
| | Logic error | All | Trace reasoning chain | Model |
| **ACT** | Wrong tool selected | All | Compare tool used vs optimal | Code |
| | Wrong tool parameters | All | Validate parameters against schema | Code |
| | Wrong tool sequence | All | Compare sequence vs required | Code |
| | Tool not called | All | Check required tool presence | Code |
| | Redundant tool calls | All | Count duplicate/unnecessary calls | Code |
| | Execution failure | All | Check tool return success | Code |
| **COMMUNICATE** | Schema violation | Specialists | Pydantic validation | Code |
| | Incomplete output | All | Check required fields present | Code |
| | Poor synthesis | PM | Rate synthesis quality | Model |
| | HITL bypassed | Specialists | Check approval gate presence | Code |
| | Edit ignored | All | Compare pre/post edit values | Code |
| | Unclear message | All | Rate clarity/completeness | Model |
| **RECOVER** | Error not handled | All | Check error propagation | Code |
| | Wrong escalation | All | Compare escalation to severity | Model |
| | State corruption | All | Validate state consistency | Code |
| | Infinite loop | All | Check iteration counts | Code |
| | Silent failure | All | Check for swallowed errors | Code |
| | No fallback | All | Check fallback attempted | Code |

---

## Agent-Specific Failure Profiles

### PM (Orchestrator)

| Priority | Failure | Impact | Frequency Target |
|----------|---------|--------|------------------|
| P0 | Wrong specialist routed | Workflow fails | <2% |
| P0 | HITL bypassed | Data integrity | 0% |
| P1 | Context not passed | Specialist lacks info | <5% |
| P1 | Multi-intent missed | Incomplete workflow | <10% |
| P2 | Suboptimal parallelization | Latency | <20% |
| P2 | Poor synthesis | User confusion | <15% |

**Key insight**: PM failures cascade. A routing error at the top wastes all downstream work.

---

### Analysts (Visual, Product, Catalog)

| Priority | Failure | Impact | Frequency Target |
|----------|---------|--------|------------------|
| P0 | Hallucination | Wrong downstream decisions | <5% |
| P0 | Missed critical data | Incomplete analysis | <10% |
| P1 | Overconfidence | False certainty | <15% |
| P1 | Wrong tool usage | Inefficient exploration | <20% |
| P2 | Excessive token usage | Cost | <30% over baseline |

**Key insight**: Analyst hallucinations poison the entire data flow. Ground truth verification is critical.

---

### Specialists (Catalog, Creative, etc.)

| Priority | Failure | Impact | Frequency Target |
|----------|---------|--------|------------------|
| P0 | Schema violation | Execution fails | 0% |
| P0 | Business rule violation | Bad data saved | 0% |
| P0 | HITL bypass | Unauthorized writes | 0% |
| P1 | Wrong family assignment | Miscategorization | <10% |
| P1 | Incomplete data | Partial records | <15% |
| P2 | Suboptimal structure | Technical debt | <25% |

**Key insight**: Specialists write to production. P0 failures are non-negotiable - they must be 0%.

---

### Tools

| Priority | Failure | Impact | Frequency Target |
|----------|---------|--------|------------------|
| P0 | Data corruption | Integrity loss | 0% |
| P0 | Silent failure | Hidden errors | 0% |
| P1 | Timeout | UX degradation | <5% |
| P1 | Wrong result | Bad decisions | <2% |
| P2 | Performance degradation | Latency | <20% over baseline |

**Key insight**: Tools should never silently fail. Always return structured errors.

---

## Failure Detection Strategy

### By Grader Type

| Grader Type | Best For | Examples |
|-------------|----------|----------|
| **Code** | Deterministic checks | Schema validation, tool sequence, HITL compliance |
| **Model** | Semantic understanding | Hallucination, synthesis quality, intent classification |
| **Human** | Calibration, edge cases | Novel failures, ambiguous judgments |

### Priority-Based Testing

1. **P0 failures**: Test exhaustively, 100% coverage, no tolerance
2. **P1 failures**: Test comprehensively, track trends, fix within sprint
3. **P2 failures**: Sample testing, improve over time

---

## Mapping Failures to Scenarios

| Failure Pillar | Scenario Category | Primary Grader |
|----------------|-------------------|----------------|
| UNDERSTAND | Intent Understanding | Code + Model |
| UNDERSTAND | Context Understanding | Model |
| REASON | Agent Behavior (hallucination) | Model |
| ACT | Tool Usage | Code |
| COMMUNICATE | HITL Compliance | Code |
| RECOVER | Error Recovery | Code |

---

## Related Documents

- [03_GRADER_ARCHITECTURE.md](03_GRADER_ARCHITECTURE.md) - How to detect these failures
- [04_SCENARIO_FRAMEWORK.md](04_SCENARIO_FRAMEWORK.md) - Test cases for each pillar
- [05_INTELLIGENCE_LAYER.md](05_INTELLIGENCE_LAYER.md) - Root cause analysis when failures occur
