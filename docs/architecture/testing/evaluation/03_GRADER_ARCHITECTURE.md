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

**When to use**: Deterministic outcomes, protocol compliance, structural verification

### PM-Specific Graders (Derived from PM Prompts/Protocols)

These graders verify PM behavioral rules from `project_manager.prompt` and protocols.

```python
class PMCodeGraders:
    """PM-specific deterministic graders based on protocol rules."""

    # --- Protocol Loading (CRITICAL) ---
    @staticmethod
    def protocol_load_first(trace: TraceForEval) -> GradeResult:
        """PM must load protocol BEFORE delegation on new workflows.

        Source: project_manager.prompt lines 19-101
        Rule: "Your FIRST tool call on any new workflow MUST be load_protocol."
        """
        if not trace.tool_calls:
            return GradeResult(passed=True, score=1.0, evidence="No tool calls")

        # Check if first substantive action was protocol load
        first_tool = trace.tool_calls[0]["tool_name"]
        is_protocol_first = first_tool == "load_protocol"

        return GradeResult(
            passed=is_protocol_first,
            score=1.0 if is_protocol_first else 0.0,
            evidence=f"First tool: {first_tool}"
        )

    # --- Media Acquisition (CRITICAL) ---
    @staticmethod
    def media_download_first(trace: TraceForEval) -> GradeResult:
        """When media_id present, download BEFORE delegation.

        Source: project_manager.prompt lines 125-151
        Rule: "When user message contains [media_id: xxx], images are NOT in storage yet."
        """
        # Check if user message has media_id
        has_media_id = "[media_id:" in trace.user_message or "[media attachments" in trace.user_message

        if not has_media_id:
            return GradeResult(passed=True, score=1.0, evidence="No media_id in message")

        # Find download and delegation calls
        download_idx = None
        delegate_idx = None
        for i, tc in enumerate(trace.tool_calls):
            if "download" in tc["tool_name"] and "media" in tc["tool_name"]:
                download_idx = i
                break
        for i, tc in enumerate(trace.tool_calls):
            if tc["tool_name"] == "delegate_to_agent":
                delegate_idx = i
                break

        if download_idx is None:
            return GradeResult(passed=False, score=0.0, evidence="Media not downloaded")
        if delegate_idx is None:
            return GradeResult(passed=True, score=1.0, evidence="Downloaded, no delegation")

        passed = download_idx < delegate_idx
        return GradeResult(
            passed=passed,
            score=1.0 if passed else 0.0,
            evidence=f"download at {download_idx}, delegate at {delegate_idx}"
        )

    # --- Visual Analysis Boundary ---
    @staticmethod
    def visual_boundary(trace: TraceForEval) -> GradeResult:
        """PM must delegate to visual_analyst when image present.

        Source: project_manager.prompt lines 110-123
        Rule: "YOU NEVER ANALYZE IMAGE CONTENT. That's visual_analyst's exclusive domain."
        """
        if not trace.has_image:
            return GradeResult(passed=True, score=1.0, evidence="No image in workflow")

        has_visual_analyst = "visual_analyst" in trace.delegation_order
        return GradeResult(
            passed=has_visual_analyst,
            score=1.0 if has_visual_analyst else 0.0,
            evidence=f"Delegation order: {trace.delegation_order}"
        )

    # --- File Reading Before Synthesis ---
    @staticmethod
    def file_read_before_synthesis(trace: TraceForEval) -> GradeResult:
        """PM must read analysis files before synthesis/presentation.

        Source: synthesis.protocol lines 10-20
        Rule: "Summaries are lies. Files are truth. Before you synthesize, you MUST read."
        """
        # Check if read_file was called for analysis files
        read_calls = [tc for tc in trace.tool_calls if tc["tool_name"] == "read_file"]
        analysis_reads = [
            rc for rc in read_calls
            if any(pattern in str(rc.get("args", {}))
                   for pattern in ["visual_analysis", "product_research", "catalog_analysis"])
        ]

        # Check if we had delegations that would produce analysis files
        has_analysts = any(
            agent in trace.delegation_order
            for agent in ["visual_analyst", "product_analyst", "catalog_analyst"]
        )

        if not has_analysts:
            return GradeResult(passed=True, score=1.0, evidence="No analysts delegated")

        has_reads = len(analysis_reads) > 0
        return GradeResult(
            passed=has_reads,
            score=1.0 if has_reads else 0.0,
            evidence=f"Analysis file reads: {len(analysis_reads)}"
        )

    # --- Two-Phase Commit ---
    @staticmethod
    def analyst_before_specialist(trace: TraceForEval) -> GradeResult:
        """Analysts must run before specialists (analysis -> execution).

        Source: project_manager.prompt lines 320-341 (Flow Doctrine)
        Rule: "Phase 1: INTELLIGENCE (analysts), Gate: USER APPROVAL, Phase 2: EXECUTION (specialists)"
        """
        analysts = ["visual_analyst", "product_analyst", "catalog_analyst"]
        specialists = ["creative_specialist", "catalog_specialist"]

        last_analyst_idx = -1
        first_specialist_idx = len(trace.delegation_order)

        for i, agent in enumerate(trace.delegation_order):
            if agent in analysts:
                last_analyst_idx = max(last_analyst_idx, i)
            if agent in specialists and first_specialist_idx == len(trace.delegation_order):
                first_specialist_idx = i

        # If no specialists or no analysts, pass
        if first_specialist_idx == len(trace.delegation_order) or last_analyst_idx == -1:
            return GradeResult(passed=True, score=1.0, evidence="Single phase workflow")

        passed = last_analyst_idx < first_specialist_idx
        return GradeResult(
            passed=passed,
            score=1.0 if passed else 0.0,
            evidence=f"Last analyst at {last_analyst_idx}, first specialist at {first_specialist_idx}"
        )

    # --- Dependency Order ---
    @staticmethod
    def visual_before_others(trace: TraceForEval) -> GradeResult:
        """Visual analyst should run before product/catalog when image present.

        Source: discovery_mindset.protocol lines 70-87
        Rule: "When image is involved, visual_analyst is ALMOST ALWAYS Wave 1."
        """
        if not trace.has_image:
            return GradeResult(passed=True, score=1.0, evidence="No image")

        if "visual_analyst" not in trace.delegation_order:
            return GradeResult(passed=False, score=0.0, evidence="Visual analyst not called for image workflow")

        visual_idx = trace.delegation_order.index("visual_analyst")

        # Check if product/catalog analysts ran before visual
        violations = []
        for other in ["product_analyst", "catalog_analyst"]:
            if other in trace.delegation_order:
                other_idx = trace.delegation_order.index(other)
                if other_idx < visual_idx:
                    violations.append(f"{other} at {other_idx}")

        passed = len(violations) == 0
        return GradeResult(
            passed=passed,
            score=1.0 if passed else 0.5,
            evidence=f"Visual at {visual_idx}, violations: {violations}" if violations else f"Visual first at {visual_idx}"
        )

    # --- HITL Signal Handling ---
    @staticmethod
    def hitl_signal_handling(trace: TraceForEval) -> GradeResult:
        """PM must load hitl protocol when subagent returns HITL markers.

        Source: hitl.protocol - PM handles HITL signals FROM subagents
        Rule: When agent response contains HITL markers, PM loads hitl protocol.

        Note: HITL happens at subagent level. PM interprets the signals.
        """
        # Check if any delegation returned with HITL markers
        # (This would be in the delegation results/agent responses)
        # For now, check if hitl protocol was loaded when there were interrupts

        if not trace.interrupts:
            return GradeResult(passed=True, score=1.0, evidence="No HITL events")

        hitl_loaded = trace.protocols_loaded.get("PM", "").find("hitl") >= 0
        return GradeResult(
            passed=hitl_loaded,
            score=1.0 if hitl_loaded else 0.5,
            evidence=f"HITL events: {len(trace.interrupts)}, hitl protocol loaded: {hitl_loaded}"
        )

    # --- File Path Propagation ---
    @staticmethod
    def file_propagation(trace: TraceForEval) -> GradeResult:
        """Downstream agents must receive upstream analysis files.

        Source: project_manager.prompt lines 495-522 (Context Bridge)
        Rule: "Include source image AND all relevant upstream files"
        """
        # Check handoff_issues from trace_loader
        issues = [hi for hi in trace.handoff_issues if hi.issues]

        if not trace.delegations:
            return GradeResult(passed=True, score=1.0, evidence="No delegations")

        issue_count = len(issues)
        delegation_count = len(trace.delegations)

        score = 1.0 - (issue_count / delegation_count) if delegation_count > 0 else 1.0
        return GradeResult(
            passed=issue_count == 0,
            score=max(0.0, score),
            evidence=f"Handoff issues: {issue_count}/{delegation_count} delegations"
        )

    # --- Error Free ---
    @staticmethod
    def error_free(trace: TraceForEval) -> GradeResult:
        """Trace completes without errors."""
        has_error = trace.status == "error" or trace.error is not None
        high_severity_issues = [i for i in trace.detected_issues if i.severity == "HIGH"]

        if has_error:
            return GradeResult(passed=False, score=0.0, evidence=trace.error or "Status: error")
        if high_severity_issues:
            return GradeResult(passed=False, score=0.3, evidence=f"High severity issues: {len(high_severity_issues)}")

        return GradeResult(passed=True, score=1.0, evidence="No errors")

    # --- Tool Success Rate ---
    @staticmethod
    def tool_success_rate(trace: TraceForEval) -> GradeResult:
        """Tools execute successfully."""
        if not trace.tool_calls:
            return GradeResult(passed=True, score=1.0, evidence="No tool calls")

        success_count = sum(1 for tc in trace.tool_calls if tc.get("status") == "success")
        total = len(trace.tool_calls)
        rate = success_count / total

        return GradeResult(
            passed=rate >= 0.9,
            score=rate,
            evidence=f"{success_count}/{total} tools succeeded"
        )
```

### Generic Graders (Scenario-Specific)

These are used when scenarios specify expected values:

```python
class GenericCodeGraders:
    """Generic graders - parameterized by scenario."""

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

    # --- Required Tools ---
    @staticmethod
    def required_tools_called(
        trace: TraceForEval,
        required: list[str]
    ) -> GradeResult:
        """Check that required tools were called."""
        called = {tc["tool_name"] for tc in trace.tool_calls}
        missing = set(required) - called
        return GradeResult(
            passed=len(missing) == 0,
            score=len(called & set(required)) / len(required) if required else 1.0,
            evidence=f"Missing: {missing}" if missing else "All required tools called"
        )

    # --- Expected Routing ---
    @staticmethod
    def expected_routing(
        trace: TraceForEval,
        expected_agents: list[str]
    ) -> GradeResult:
        """Verify PM routed to expected agents."""
        routed = set(trace.delegation_order)
        expected = set(expected_agents)
        missing = expected - routed
        extra = routed - expected  # Not penalized, just noted

        score = len(expected & routed) / len(expected) if expected else 1.0
        return GradeResult(
            passed=len(missing) == 0,
            score=score,
            evidence=f"Missing: {missing}, Extra: {extra}" if missing else f"All expected agents called"
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
