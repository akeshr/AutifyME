# Grader Architecture

**Part of**: [Universal Evaluation Framework](00_INDEX.md)

**Version**: 4.1 - Model-First, Code for Verification

---

## Overview

The grader architecture follows **Model-First, Code for Verification**:

- **Claude Code Skills** (`/evaluate`): Primary evaluation during development
- **Model Graders** (Python API calls): Automated CI/CD pipelines
- **Code Graders**: Structural verification only (schema, HITL, DB state)
- **Human Graders**: Calibration and edge cases

```text
                    EVALUATION HIERARCHY
                           |
       +-------------------+-------------------+
       |                                       |
       v                                       v
+-------------------+                +-------------------+
| CLAUDE CODE       |                | AUTOMATED         |
| /evaluate skill   |                | PIPELINE          |
| (development)     |                | (CI/CD)           |
+-------------------+                +-------------------+
       |                                       |
       |                   +-------------------+-------------------+
       |                   |                                       |
       v                   v                                       v
+-------------------+  +-------------------+  +-------------------+
| MODEL GRADERS     |  | CODE GRADERS      |  | HUMAN GRADERS     |
| (~70% of evals)   |  | (~30% of evals)   |  | (calibration)     |
+-------------------+  +-------------------+  +-------------------+
| Intent, Routing   |  | Schema compliance |  | Gold standard     |
| Synthesis, Tools  |  | HITL compliance   |  | Edge cases        |
| Helpfulness       |  | DB state          |  | 5-10% sample      |
+-------------------+  +-------------------+  +-------------------+
```

**Rationale for Model-First**:

- PM behavior is ~70% semantic (intent, routing appropriateness, synthesis quality)
- Modern LLMs achieve 85-95% agreement with human judges
- Model graders provide nuanced 0.0-1.0 scores with reasoning
- Code graders only for truly structural checks

**Full specification**: See [10_SKILL_ARCHITECTURE.md](10_SKILL_ARCHITECTURE.md) for /evaluate skill

---

## Grading Modes

**Critical insight from Anthropic**: "Grade outputs, not paths." Agents may find creative solutions that differ from expected paths but produce correct results.

```python
class GradingMode(Enum):
    OUTPUT_ONLY = "output_only"      # Grade final output, ignore path (DEFAULT)
    PATH_ADVISORY = "path_advisory"  # Log path deviation, don't fail
    PATH_STRICT = "path_strict"      # Fail on path deviation (safety-critical only)
```

### Mode Selection Guide

| Scenario Type | Recommended Mode | Rationale |
|---------------|------------------|-----------|
| Output quality | OUTPUT_ONLY | We care about result, not how |
| HITL compliance | PATH_STRICT | Safety-critical, path matters |
| Tool usage | PATH_ADVISORY | Log deviations, investigate patterns |
| Business rules | OUTPUT_ONLY | Verify state, not process |
| Creative tasks | OUTPUT_ONLY | Multiple valid approaches |

---

## Code-Based Graders

**When to use**: Deterministic outcomes, schema validation, state verification

```python
class CodeGraders:
    """Deterministic graders - fast, cheap, reproducible."""

    # --- State Verification ---
    @staticmethod
    def db_state_check(
        table: str,
        expected: dict,
        actual_query: str
    ) -> GradeResult:
        """Verify database state matches expected."""
        actual = execute_sql(actual_query)
        matches = all(
            actual.get(k) == v for k, v in expected.items()
        )
        return GradeResult(
            passed=matches,
            score=1.0 if matches else 0.0,
            evidence=f"Expected: {expected}, Actual: {actual}"
        )

    # --- Schema Validation ---
    @staticmethod
    def schema_compliance(
        output: dict,
        schema: type[BaseModel]
    ) -> GradeResult:
        """Validate output against Pydantic schema."""
        try:
            schema.model_validate(output)
            return GradeResult(passed=True, score=1.0)
        except ValidationError as e:
            return GradeResult(
                passed=False,
                score=0.0,
                evidence=str(e.errors())
            )

    # --- Tool Call Verification ---
    @staticmethod
    def required_tools_called(
        trace: TraceForEval,
        required: list[str]
    ) -> GradeResult:
        """Check that required tools were called."""
        called = {tc.tool_name for tc in trace.tool_calls}
        missing = set(required) - called
        return GradeResult(
            passed=len(missing) == 0,
            score=len(called & set(required)) / len(required),
            evidence=f"Missing: {missing}" if missing else "All required tools called"
        )

    # --- Tool Sequence Verification ---
    @staticmethod
    def tool_sequence(
        trace: TraceForEval,
        expected_sequence: list[str]
    ) -> GradeResult:
        """Verify tools called in correct order."""
        actual = [tc.tool_name for tc in trace.tool_calls]
        # Check subsequence (allows other tools between)
        seq_idx = 0
        for tool in actual:
            if seq_idx < len(expected_sequence) and tool == expected_sequence[seq_idx]:
                seq_idx += 1
        return GradeResult(
            passed=seq_idx == len(expected_sequence),
            score=seq_idx / len(expected_sequence),
            evidence=f"Expected: {expected_sequence}, Actual: {actual}"
        )

    # --- Constraint Verification ---
    @staticmethod
    def business_rules(
        output: dict,
        rules: list[Callable[[dict], bool]]
    ) -> GradeResult:
        """Validate against business rules."""
        violations = []
        for rule in rules:
            try:
                if not rule(output):
                    violations.append(rule.__name__)
            except Exception as e:
                violations.append(f"{rule.__name__}: {e}")
        return GradeResult(
            passed=len(violations) == 0,
            score=1 - (len(violations) / len(rules)),
            evidence=f"Violations: {violations}" if violations else "All rules passed"
        )

    # --- HITL Gate Verification ---
    @staticmethod
    def hitl_compliance(
        trace: TraceForEval,
        write_tools: list[str] = ["write_data"]
    ) -> GradeResult:
        """Verify HITL approval before writes."""
        for tool_call in trace.tool_calls:
            if tool_call.tool_name in write_tools:
                # Check for interrupt before this tool
                if not any(
                    i.timestamp < tool_call.timestamp
                    for i in trace.interrupts
                ):
                    return GradeResult(
                        passed=False,
                        score=0.0,
                        evidence=f"Write tool {tool_call.tool_name} called without HITL approval"
                    )
        return GradeResult(passed=True, score=1.0)

    # --- Routing Verification ---
    @staticmethod
    def correct_routing(
        trace: TraceForEval,
        expected_agent: str
    ) -> GradeResult:
        """Verify PM routed to correct specialist/analyst."""
        routed_to = [d.target for d in trace.delegations]
        return GradeResult(
            passed=expected_agent in routed_to,
            score=1.0 if expected_agent in routed_to else 0.0,
            evidence=f"Expected: {expected_agent}, Routed to: {routed_to}"
        )
```

---

## Model-Based Graders

**When to use**: Nuance, subjective quality, semantic correctness

```python
class ModelGraders:
    """LLM-based graders - flexible, handles nuance."""

    def __init__(self, judge_model: str = "claude-sonnet-4-20250514"):
        self.judge = ChatAnthropic(model=judge_model)

    # --- Hallucination Detection ---
    async def hallucination_check(
        self,
        output: str,
        source_data: str
    ) -> GradeResult:
        """Check if output contains hallucinated information."""
        prompt = f"""You are a hallucination detector. Check if the output contains claims not supported by the source data.

SOURCE DATA (ground truth):
{source_data}

OUTPUT TO CHECK:
{output}

For each claim in the output:
1. Is it supported by source data?
2. Is it a reasonable inference?
3. Is it hallucinated (not in source, not inferable)?

Respond in JSON:
{{
    "hallucinated_claims": list[str],
    "supported_claims": list[str],
    "score": float (1.0 = no hallucination, 0.0 = all hallucinated)
}}
"""
        response = await self.judge.ainvoke(prompt)
        result = json.loads(response.content)
        return GradeResult(
            passed=len(result["hallucinated_claims"]) == 0,
            score=result["score"],
            evidence=result["hallucinated_claims"]
        )

    # --- Synthesis Quality ---
    async def synthesis_quality(
        self,
        pm_synthesis: str,
        specialist_outputs: list[str]
    ) -> GradeResult:
        """Evaluate PM's synthesis of specialist outputs."""
        rubric = """
SYNTHESIS QUALITY RUBRIC:
- Completeness (0.3): All specialist findings incorporated
- Coherence (0.3): Logical flow, no contradictions
- Actionability (0.2): Clear next steps for user
- Conciseness (0.2): No unnecessary verbosity
"""
        context = f"Specialist outputs to synthesize:\n" + "\n---\n".join(specialist_outputs)
        return await self.rubric_score(pm_synthesis, rubric, context)

    # --- Context Utilization ---
    async def context_utilization(
        self,
        context_provided: str,
        agent_output: str
    ) -> GradeResult:
        """Check if agent properly used provided context."""
        prompt = f"""Evaluate how well the agent utilized the provided context.

CONTEXT PROVIDED:
{context_provided}

AGENT OUTPUT:
{agent_output}

Score on:
1. Relevance (0.4): Used relevant parts of context
2. Completeness (0.3): Didn't miss critical context
3. Accuracy (0.3): Correctly interpreted context

Respond in JSON:
{{"score": float, "missed_context": list[str], "misinterpreted": list[str]}}
"""
        response = await self.judge.ainvoke(prompt)
        result = json.loads(response.content)
        return GradeResult(
            passed=result["score"] >= 0.7,
            score=result["score"],
            evidence={
                "missed": result["missed_context"],
                "misinterpreted": result["misinterpreted"]
            }
        )

    # --- Intent Classification ---
    async def intent_classification(
        self,
        user_message: str,
        classified_intent: str,
        valid_intents: list[str]
    ) -> GradeResult:
        """Evaluate intent classification accuracy."""
        prompt = f"""You are an intent classification expert.

USER MESSAGE:
{user_message}

VALID INTENTS:
{valid_intents}

SYSTEM'S CLASSIFICATION:
{classified_intent}

Evaluate:
1. Is the classification correct?
2. If wrong, what should it be?
3. Is this an ambiguous case?

Respond in JSON:
{{
    "correct": bool,
    "expected_intent": str,
    "ambiguity_score": float (0=clear, 1=very ambiguous),
    "reasoning": str
}}
"""
        response = await self.judge.ainvoke(prompt)
        result = json.loads(response.content)
        return GradeResult(
            passed=result["correct"],
            score=1.0 if result["correct"] else 0.0,
            reasoning=result["reasoning"],
            evidence={
                "expected": result["expected_intent"],
                "ambiguity": result["ambiguity_score"]
            }
        )
```

---

## Human Graders (via LangSmith)

**When to use**: Gold standard, calibrating model graders, edge cases

```python
class HumanGraders:
    """Human evaluation via LangSmith annotation queues."""

    def __init__(self, langsmith: LangSmithIntegration):
        self.langsmith = langsmith

    async def queue_for_review(
        self,
        scenario: Scenario,
        trace: TraceForEval,
        output: str,
        queue_name: str = "calibration"
    ):
        """Queue trace for human review in LangSmith."""
        await self.langsmith.queue_for_human_review(
            trace_ids=[trace.trace_id],
            queue_name=queue_name
        )

    async def get_calibration_data(
        self,
        queue_name: str = "calibration"
    ) -> list[CalibrationSample]:
        """Retrieve human annotations for calibration."""
        annotations = await self.langsmith.get_human_annotations(queue_name)
        return [
            CalibrationSample(
                trace_id=a.trace_id,
                human_score=a.scores.get("overall", 0),
                human_notes=a.notes
            )
            for a in annotations
        ]

    @staticmethod
    def calibrate_model_grader(
        human_scores: list[float],
        model_scores: list[float]
    ) -> CalibrationResult:
        """Compare model grader to human scores."""
        from scipy.stats import spearmanr
        correlation, p_value = spearmanr(human_scores, model_scores)

        return CalibrationResult(
            correlation=correlation,
            p_value=p_value,
            calibrated=correlation > 0.8,
            recommendation=(
                "Model grader well-calibrated" if correlation > 0.8
                else f"Model grader needs adjustment (correlation: {correlation:.2f})"
            )
        )
```

---

## Grading Orchestration

**IMPORTANT**: The single implementation of grading orchestration is `GradingOrchestrator` defined in [09_IMPLEMENTATION_GUIDE.md](09_IMPLEMENTATION_GUIDE.md). This section describes the conceptual approach.

### Output-Only Grading (Default)

The default mode implements "grade outputs, not paths":

```python
# See 09_IMPLEMENTATION_GUIDE.md for full GradingOrchestrator implementation

class GradingOrchestrator:
    """
    SINGLE implementation of grading orchestration.
    All grading flows through this class.
    """

    def __init__(self, registry: GraderRegistry):
        self.registry = registry

    async def grade(
        self,
        scenario: Scenario,
        result: RolloutResult,
        trace: TraceForEval
    ) -> Judgment:
        """
        Grade a scenario execution.

        Implements output-only grading by default:
        - Runs configured graders against output
        - Logs path deviations but does NOT score them
        - Only PATH_STRICT mode penalizes path deviations

        Returns:
            Judgment with aggregated scores and path analysis
        """
        grader_outputs: list[GraderOutput] = []
        path_deviations: list[PathDeviation] = []

        # 1. Run all configured graders
        for spec in scenario.grading.graders:
            grader = self.registry.get(spec.name)
            grade = await grader.grade(
                output=result.response,
                expected=scenario.expected,
                trace=trace,
                config=spec.config
            )
            grader_outputs.append(GraderOutput(
                grader_name=spec.name,
                grader_type=grader.grader_type,
                grade=grade,
                weight=spec.weight
            ))

        # 2. Log path deviations (all modes)
        if scenario.expected.routing:
            actual_routing = [d.target for d in trace.delegations]
            if set(actual_routing) != set(scenario.expected.routing):
                path_deviations.append(PathDeviation(
                    type="routing",
                    expected=scenario.expected.routing,
                    actual=actual_routing,
                    analysis=self._analyze_routing_deviation(
                        scenario.expected.routing, actual_routing
                    )
                ))

        # 3. Calculate weighted score (graders only)
        total_weight = sum(go.weight for go in grader_outputs)
        weighted_score = sum(
            go.grade.score * go.weight for go in grader_outputs
        ) / total_weight if total_weight > 0 else 0.0

        # 4. Apply path penalty ONLY in PATH_STRICT mode
        if scenario.grading.mode == GradingMode.PATH_STRICT and path_deviations:
            weighted_score *= 0.5  # 50% penalty

        return Judgment(
            scenario_id=scenario.id,
            trace_id=result.trace_id,
            passed=weighted_score >= scenario.grading.pass_threshold,
            score=weighted_score,
            grader_outputs=grader_outputs,
            path_deviations=path_deviations,
            grading_mode=scenario.grading.mode
        )

    def _analyze_routing_deviation(
        self,
        expected: list[str],
        actual: list[str]
    ) -> str:
        """Explain why routing differed (for investigation, not scoring)."""
        if set(actual).issubset(set(expected)):
            return "Agent found shorter path (skipped unnecessary specialists)"
        if set(expected).issubset(set(actual)):
            return "Agent used additional specialists (more thorough)"
        return "Different routing strategy"
```

**Key principle**: Path deviations are INFORMATION, not FAILURE. Only safety-critical scenarios (HITL) use PATH_STRICT.

---

## Grader Selection Matrix

| Evaluation Target | Primary Grader | Secondary Grader | Human Check |
|-------------------|----------------|------------------|-------------|
| Schema compliance | Code (Pydantic) | - | Never |
| DB state | Code (SQL) | - | Never |
| Tool calls | Code (trace) | - | Never |
| HITL compliance | Code (interrupt) | - | Never |
| Business rules | Code (rules) | Model (edge cases) | 5% sample |
| Intent classification | Code (if deterministic) | Model (ambiguous) | 10% sample |
| Synthesis quality | Model (rubric) | - | 10% sample |
| Hallucination | Model (check) | - | 5% sample |
| Context usage | Model (evaluation) | - | 10% sample |
| Overall quality | Model (rubric) | Human | 5% sample |

---

## Related Documents

- [01_LANGSMITH_FOUNDATION.md](01_LANGSMITH_FOUNDATION.md) - LangSmith evaluator integration
- [04_SCENARIO_FRAMEWORK.md](04_SCENARIO_FRAMEWORK.md) - Scenario grading configuration
- [07_OPERATIONAL_GUIDE.md](07_OPERATIONAL_GUIDE.md) - Human review SLA
- [08_SCHEMAS.md](08_SCHEMAS.md) - Canonical schema definitions (GradeResult, Judgment, GraderRegistry)
- [09_IMPLEMENTATION_GUIDE.md](09_IMPLEMENTATION_GUIDE.md) - GradingOrchestrator implementation details
