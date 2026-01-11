# Universal Evaluation Framework for AutifyME

**Date**: 2026-01-11
**Status**: Design
**Version**: 2.0 - Complete Rewrite
**Purpose**: Universal framework to evaluate, measure, and improve ANY agent behavior

---

## Executive Summary

A **universal evaluation framework** designed to handle ANY failure mode across ALL agent types. Built on first principles from Anthropic's "Demystifying Evals for AI Agents" guidance.

**Core Philosophy**:
- **Start from failures**: Real failures become test cases
- **Grade outputs, not paths**: Agents find creative solutions
- **Prefer deterministic graders**: Code > Model > Human
- **Balanced problem sets**: Test both positive and negative cases
- **Continuous measurement**: Capability evals graduate to regression suites

---

## Part 1: Complete Failure Taxonomy

### 1.1 The Five Pillars of Agent Failure

Every agent failure falls into one of five categories:

```
+------------------+------------------+------------------+------------------+------------------+
|   UNDERSTAND     |     REASON       |      ACT         |    COMMUNICATE   |     RECOVER      |
+------------------+------------------+------------------+------------------+------------------+
| Intent parsing   | Logic errors     | Tool selection   | Output quality   | Error handling   |
| Context reading  | Hallucination    | Tool parameters  | Synthesis        | Graceful degrade |
| Reference resol. | Constraint viol. | Tool sequencing  | HITL compliance  | Escalation       |
| Multi-turn state | Over/under conf. | Execution errors | Feedback integr. | State recovery   |
+------------------+------------------+------------------+------------------+------------------+
```

### 1.2 Universal Failure Matrix

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

### 1.3 Agent-Specific Failure Profiles

#### PM (Orchestrator)

| Priority | Failure | Impact | Frequency Target |
|----------|---------|--------|------------------|
| P0 | Wrong specialist routed | Workflow fails | <2% |
| P0 | HITL bypassed | Data integrity | 0% |
| P1 | Context not passed | Specialist lacks info | <5% |
| P1 | Multi-intent missed | Incomplete workflow | <10% |
| P2 | Suboptimal parallelization | Latency | <20% |
| P2 | Poor synthesis | User confusion | <15% |

#### Analysts (Visual, Product, Catalog)

| Priority | Failure | Impact | Frequency Target |
|----------|---------|--------|------------------|
| P0 | Hallucination | Wrong downstream decisions | <5% |
| P0 | Missed critical data | Incomplete analysis | <10% |
| P1 | Overconfidence | False certainty | <15% |
| P1 | Wrong tool usage | Inefficient exploration | <20% |
| P2 | Excessive token usage | Cost | <30% over baseline |

#### Specialists (Catalog, Creative, etc.)

| Priority | Failure | Impact | Frequency Target |
|----------|---------|--------|------------------|
| P0 | Schema violation | Execution fails | 0% |
| P0 | Business rule violation | Bad data saved | 0% |
| P0 | HITL bypass | Unauthorized writes | 0% |
| P1 | Wrong family assignment | Miscategorization | <10% |
| P1 | Incomplete data | Partial records | <15% |
| P2 | Suboptimal structure | Technical debt | <25% |

#### Tools

| Priority | Failure | Impact | Frequency Target |
|----------|---------|--------|------------------|
| P0 | Data corruption | Integrity loss | 0% |
| P0 | Silent failure | Hidden errors | 0% |
| P1 | Timeout | UX degradation | <5% |
| P1 | Wrong result | Bad decisions | <2% |
| P2 | Performance degradation | Latency | <20% over baseline |

---

## Part 2: Three-Grader Architecture

### 2.1 Grader Hierarchy

```
                    PREFER
                      |
                      v
+------------------+     +------------------+     +------------------+
|   CODE-BASED     | --> |   MODEL-BASED    | --> |   HUMAN-BASED    |
+------------------+     +------------------+     +------------------+
| Fast, cheap      |     | Flexible         |     | Gold standard    |
| Deterministic    |     | Handles nuance   |     | Calibrates LLM   |
| Reproducible     |     | Scalable         |     | Expensive, slow  |
+------------------+     +------------------+     +------------------+

Use code when possible. Use model when nuance needed. Use human to calibrate.
```

### 2.2 Code-Based Graders

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
        trace: TraceOverview,
        required: list[str]
    ) -> GradeResult:
        """Check that required tools were called."""
        called = {run.name for run in trace.tool_runs}
        missing = set(required) - called
        return GradeResult(
            passed=len(missing) == 0,
            score=len(called & set(required)) / len(required),
            evidence=f"Missing: {missing}" if missing else "All required tools called"
        )

    # --- Tool Sequence Verification ---
    @staticmethod
    def tool_sequence(
        trace: TraceOverview,
        expected_sequence: list[str]
    ) -> GradeResult:
        """Verify tools called in correct order."""
        actual = [run.name for run in trace.tool_runs]
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
        trace: TraceOverview,
        write_tools: list[str] = ["write_data"]
    ) -> GradeResult:
        """Verify HITL approval before writes."""
        for tool_run in trace.tool_runs:
            if tool_run.name in write_tools:
                # Check for interrupt before this tool
                if not trace.has_interrupt_before(tool_run.id):
                    return GradeResult(
                        passed=False,
                        score=0.0,
                        evidence=f"Write tool {tool_run.name} called without HITL approval"
                    )
        return GradeResult(passed=True, score=1.0)

    # --- Error Handling Verification ---
    @staticmethod
    def error_surfaced(
        trace: TraceOverview,
        expected_error_type: str | None = None
    ) -> GradeResult:
        """Verify errors are surfaced, not swallowed."""
        errors = trace.get_errors()
        if not errors:
            return GradeResult(passed=True, score=1.0)

        # Check if error appears in final output
        final_output = trace.final_output
        error_surfaced = any(
            err.message in str(final_output) or
            err.type in str(final_output)
            for err in errors
        )
        return GradeResult(
            passed=error_surfaced,
            score=1.0 if error_surfaced else 0.0,
            evidence=f"Errors: {[e.message for e in errors]}, Surfaced: {error_surfaced}"
        )

    # --- Routing Verification ---
    @staticmethod
    def correct_routing(
        trace: TraceOverview,
        expected_agent: str
    ) -> GradeResult:
        """Verify PM routed to correct specialist/analyst."""
        delegations = trace.get_delegations()
        routed_to = [d.target for d in delegations]
        return GradeResult(
            passed=expected_agent in routed_to,
            score=1.0 if expected_agent in routed_to else 0.0,
            evidence=f"Expected: {expected_agent}, Routed to: {routed_to}"
        )
```

### 2.3 Model-Based Graders

**When to use**: Nuance, subjective quality, semantic correctness

```python
class ModelGraders:
    """LLM-based graders - flexible, handles nuance."""

    def __init__(self, judge_model: str = "claude-opus-4-5-20251101"):
        self.judge = ChatAnthropic(model=judge_model)

    # --- Rubric-Based Scoring ---
    async def rubric_score(
        self,
        output: str,
        rubric: str,
        context: str = ""
    ) -> GradeResult:
        """Score output against a rubric."""
        prompt = f"""You are an expert evaluator. Score the following output against the rubric.

RUBRIC:
{rubric}

CONTEXT:
{context}

OUTPUT TO EVALUATE:
{output}

Provide:
1. Score (0.0 to 1.0)
2. Reasoning (2-3 sentences)
3. Specific evidence from the output

Respond in JSON:
{{"score": float, "reasoning": str, "evidence": list[str]}}
"""
        response = await self.judge.ainvoke(prompt)
        result = json.loads(response.content)
        return GradeResult(
            passed=result["score"] >= 0.7,
            score=result["score"],
            reasoning=result["reasoning"],
            evidence=result["evidence"]
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

    # --- Confidence Calibration ---
    async def confidence_calibration(
        self,
        stated_confidence: float,
        actual_accuracy: float
    ) -> GradeResult:
        """Check if stated confidence matches actual accuracy."""
        # Perfect calibration: confidence == accuracy
        calibration_error = abs(stated_confidence - actual_accuracy)
        return GradeResult(
            passed=calibration_error < 0.2,
            score=1.0 - calibration_error,
            evidence=f"Confidence: {stated_confidence}, Accuracy: {actual_accuracy}, Error: {calibration_error}"
        )
```

### 2.4 Human Graders (Calibration)

**When to use**: Gold standard, calibrating model graders, edge cases

```python
class HumanGraders:
    """Human evaluation for calibration and gold standard."""

    @staticmethod
    def create_review_task(
        scenario: Scenario,
        trace: TraceOverview,
        output: str
    ) -> HumanReviewTask:
        """Create task for human review."""
        return HumanReviewTask(
            id=str(uuid4()),
            scenario_id=scenario.id,
            trace_id=trace.trace_id,
            user_input=scenario.message,
            agent_output=output,
            questions=[
                ScoreQuestion(
                    id="overall",
                    text="Overall, how well did the agent handle this request?",
                    scale=(1, 5)
                ),
                ScoreQuestion(
                    id="intent",
                    text="Did the agent correctly understand the user's intent?",
                    scale=(1, 5)
                ),
                ScoreQuestion(
                    id="completeness",
                    text="Was the response complete?",
                    scale=(1, 5)
                ),
                BinaryQuestion(
                    id="would_use",
                    text="Would you trust this agent with real data?"
                ),
                FreeTextQuestion(
                    id="issues",
                    text="What issues did you notice, if any?"
                )
            ]
        )

    @staticmethod
    def calibrate_model_grader(
        human_scores: list[HumanReviewResult],
        model_scores: list[GradeResult]
    ) -> CalibrationResult:
        """Compare model grader to human scores."""
        # Spearman correlation
        human_values = [h.overall_score for h in human_scores]
        model_values = [m.score for m in model_scores]
        correlation, p_value = spearmanr(human_values, model_values)

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

### 2.5 Grader Selection Matrix

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

## Part 3: Universal Scenario Framework

### 3.1 Scenario Taxonomy

```yaml
# Universal scenario structure
scenario:
  id: string                    # Unique identifier
  version: string               # Scenario version

  # Input specification
  input:
    message: string             # User message
    media: list[MediaRef]       # Attached media (optional)
    context:                    # Pre-loaded context
      company_profile: string
      catalog_state: string
      conversation_history: list[Message]

  # Expected behavior (what SHOULD happen)
  expected:
    intent: string              # Expected intent classification
    routing: list[string]       # Expected agent routing
    tools: list[ToolExpectation]
    output:
      type: string              # "approval_request" | "response" | "question"
      schema: string            # Pydantic model name
      contains: list[string]    # Required content
    state_changes:              # Expected DB/state changes
      - table: string
        operation: string
        values: dict

  # Grading configuration
  grading:
    graders:
      - type: string            # "code" | "model" | "human"
        name: string            # Grader function name
        weight: float           # Weight in final score
        config: dict            # Grader-specific config
    pass_threshold: float       # Minimum score to pass
    partial_credit: bool        # Allow partial scoring

  # Metadata
  metadata:
    domain: string              # "catalog" | "creative" | "marketing" | ...
    complexity: string          # "simple" | "medium" | "complex" | "adversarial"
    failure_mode: string        # Target failure mode (optional)
    tags: list[string]          # Searchable tags
```

### 3.2 Scenario Categories

#### Category 1: Intent Understanding

```yaml
# Test: PM correctly classifies user intent
scenarios:
  - id: intent_simple_catalog
    input:
      message: "Catalog this product for Rs 2000"
      media: [{ type: image, path: "fixtures/sneakers.jpg" }]
    expected:
      intent: "catalog_product"
      routing: ["visual_analyst", "catalog_specialist"]
    grading:
      graders:
        - type: code
          name: correct_routing
          weight: 1.0

  - id: intent_ambiguous
    input:
      message: "Help with this"
      media: [{ type: image, path: "fixtures/product.jpg" }]
    expected:
      intent: "clarification_needed"
      output:
        type: "question"
        contains: ["What would you like", "catalog", "analyze"]
    grading:
      graders:
        - type: model
          name: intent_classification
          weight: 0.5
        - type: code
          name: output_type_check
          weight: 0.5

  - id: intent_multi
    input:
      message: "Catalog these sneakers and also create a marketing banner"
    expected:
      intent: ["catalog_product", "create_asset"]
      routing: ["catalog_specialist", "creative_specialist"]
    grading:
      graders:
        - type: code
          name: multi_intent_detection
          weight: 0.6
        - type: code
          name: multi_routing
          weight: 0.4
```

#### Category 2: Context Understanding

```yaml
# Test: Agents properly use provided context
scenarios:
  - id: context_company_profile
    input:
      message: "Catalog this premium bag"
      context:
        company_profile: |
          Brand: LuxeLeather
          Price range: Rs 5000-50000
          Target: Premium segment
    expected:
      output:
        contains: ["premium", "LuxeLeather"]
      state_changes:
        - table: products
          operation: insert
          values:
            price: { min: 5000, max: 50000 }
    grading:
      graders:
        - type: model
          name: context_utilization
          weight: 0.5
        - type: code
          name: business_rules
          weight: 0.5

  - id: context_conversation_history
    input:
      message: "Update the price to Rs 3000"
      context:
        conversation_history:
          - role: user
            content: "Catalog sneakers for Rs 2500"
          - role: assistant
            content: "Created product: Canvas Sneakers"
    expected:
      intent: "update_product"
      tools:
        - name: write_data
          params:
            operation: "update"
            values:
              price: 3000
    grading:
      graders:
        - type: code
          name: tool_params_check
          weight: 1.0
```

#### Category 3: Tool Usage

```yaml
# Test: Correct tool selection and sequencing
scenarios:
  - id: tool_mandatory_sequence
    input:
      message: "Add this new product to catalog"
    expected:
      tools:
        - name: inspect_schema
          required: true
          before: [write_data]
        - name: read_data
          required: false
        - name: write_data
          required: true
          params:
            operation: "insert"
    grading:
      graders:
        - type: code
          name: tool_sequence
          weight: 0.4
        - type: code
          name: required_tools_called
          weight: 0.6

  - id: tool_image_workflow
    input:
      message: "Extract product from this image and catalog it"
      media: [{ type: image, path: "fixtures/cluttered.jpg" }]
    expected:
      tools:
        - name: view_image
          required: true
        - name: image_studio
          required: true
          params:
            operation: "extract"
        - name: view_image
          required: true
          after: [image_studio]
        - name: write_data
          required: true
    grading:
      graders:
        - type: code
          name: tool_sequence
          weight: 0.5
        - type: code
          name: tool_params_check
          weight: 0.5
```

#### Category 4: Agent Behavior

```yaml
# Test: Agent autonomy, proactiveness, and reasoning
scenarios:
  - id: behavior_autonomous_exploration
    input:
      message: "Catalog this product"
      media: [{ type: image, path: "fixtures/sneakers.jpg" }]
    expected:
      behavior:
        - explores_before_deciding: true
        - uses_protocols: true
        - verifies_before_output: true
    grading:
      graders:
        - type: model
          name: autonomy_assessment
          config:
            rubric: |
              - Did agent explore the data before making decisions?
              - Did agent load relevant protocols?
              - Did agent verify output before returning?
          weight: 1.0

  - id: behavior_proactive_suggestions
    input:
      message: "Catalog these sneakers"
      context:
        catalog_state: |
          Similar products exist: Running Shoes, Sports Sneakers
    expected:
      output:
        contains: ["similar products", "existing", "suggest"]
    grading:
      graders:
        - type: model
          name: proactiveness_check
          weight: 1.0

  - id: behavior_constraint_respect
    input:
      message: "Set price to Rs 100"
      context:
        company_profile:
          min_price: 500
    expected:
      output:
        type: "clarification"
        contains: ["below minimum", "500"]
    grading:
      graders:
        - type: code
          name: constraint_enforcement
          weight: 0.5
        - type: model
          name: explanation_quality
          weight: 0.5
```

#### Category 5: Error Recovery

```yaml
# Test: Graceful handling of failures
scenarios:
  - id: recovery_tool_failure
    input:
      message: "Catalog this product"
      context:
        inject_failure:
          tool: write_data
          error: "Connection timeout"
    expected:
      behavior:
        - error_caught: true
        - user_informed: true
        - retry_attempted: true
    grading:
      graders:
        - type: code
          name: error_surfaced
          weight: 0.5
        - type: code
          name: retry_check
          weight: 0.3
        - type: model
          name: recovery_quality
          weight: 0.2

  - id: recovery_missing_data
    input:
      message: "Catalog this"
      # No media, no context
    expected:
      output:
        type: "question"
        contains: ["need more information", "image", "details"]
    grading:
      graders:
        - type: code
          name: output_type_check
          weight: 0.5
        - type: model
          name: question_quality
          weight: 0.5

  - id: recovery_partial_success
    input:
      message: "Catalog these 3 products"
      media: [
        { type: image, path: "fixtures/valid1.jpg" },
        { type: image, path: "fixtures/corrupted.jpg" },
        { type: image, path: "fixtures/valid2.jpg" }
      ]
    expected:
      behavior:
        - partial_success_handled: true
        - user_informed_of_failure: true
        - successful_items_saved: true
    grading:
      graders:
        - type: code
          name: partial_success_check
          weight: 0.6
        - type: model
          name: communication_quality
          weight: 0.4
```

#### Category 6: HITL Compliance

```yaml
# Test: Human-in-the-loop behavior
scenarios:
  - id: hitl_approval_required
    input:
      message: "Catalog this product for Rs 5000"
    expected:
      output:
        type: "approval_request"
        contains: ["approve", "confirm", "product details"]
      behavior:
        - write_blocked_until_approval: true
    grading:
      graders:
        - type: code
          name: hitl_compliance
          weight: 0.7
        - type: model
          name: approval_synthesis_quality
          weight: 0.3

  - id: hitl_edit_respected
    input:
      message: "Approved with edit: change price to Rs 4500"
      context:
        pending_approval:
          product:
            name: "Canvas Sneakers"
            price: 5000
    expected:
      state_changes:
        - table: products
          operation: insert
          values:
            price: 4500  # Edited value, not original
    grading:
      graders:
        - type: code
          name: edit_respected
          weight: 1.0

  - id: hitl_rejection_handled
    input:
      message: "Rejected - wrong product"
      context:
        pending_approval:
          product:
            name: "Canvas Sneakers"
    expected:
      output:
        contains: ["understood", "what would you like"]
      behavior:
        - no_write_executed: true
    grading:
      graders:
        - type: code
          name: rejection_check
          weight: 0.5
        - type: model
          name: recovery_quality
          weight: 0.5
```

### 3.3 Scenario Generation Strategy

```python
class ScenarioGenerator:
    """Generate diverse scenarios for comprehensive coverage."""

    def __init__(self, domain: str):
        self.domain = domain
        self.diversity_dimensions = {
            "complexity": ["simple", "medium", "complex", "adversarial"],
            "media_type": ["none", "single_image", "multiple_images", "document"],
            "intent_type": ["single", "multi", "ambiguous", "invalid"],
            "context_state": ["empty", "partial", "full", "conflicting"],
            "error_injection": ["none", "tool_failure", "timeout", "invalid_input"]
        }

    def generate_suite(
        self,
        base_scenarios: list[Scenario],
        target_count: int = 50
    ) -> list[Scenario]:
        """Generate diverse suite from base scenarios."""
        scenarios = []

        # 1. Include all base scenarios
        scenarios.extend(base_scenarios)

        # 2. Generate variations
        for base in base_scenarios:
            for variation in self._generate_variations(base):
                scenarios.append(variation)
                if len(scenarios) >= target_count:
                    break

        # 3. Generate adversarial cases (20%)
        adversarial_count = int(target_count * 0.2)
        scenarios.extend(
            self._generate_adversarial(base_scenarios[:adversarial_count])
        )

        # 4. Validate coverage
        coverage = self._calculate_coverage(scenarios)
        if coverage.gaps:
            scenarios.extend(self._fill_gaps(coverage.gaps))

        return scenarios[:target_count]

    def _generate_variations(self, base: Scenario) -> list[Scenario]:
        """Generate variations of a base scenario."""
        variations = []
        for dim, values in self.diversity_dimensions.items():
            for value in values:
                if value != self._get_base_value(base, dim):
                    variations.append(self._apply_variation(base, dim, value))
        return variations

    def _generate_adversarial(self, bases: list[Scenario]) -> list[Scenario]:
        """Generate adversarial edge cases."""
        adversarial = []
        for base in bases:
            # Edge case 1: Inject errors
            adversarial.append(self._inject_error(base, "tool_failure"))
            # Edge case 2: Invalid input
            adversarial.append(self._corrupt_input(base))
            # Edge case 3: Conflicting context
            adversarial.append(self._add_conflicting_context(base))
        return adversarial

    def _calculate_coverage(self, scenarios: list[Scenario]) -> CoverageReport:
        """Calculate dimension coverage."""
        coverage = {}
        for dim, values in self.diversity_dimensions.items():
            coverage[dim] = {v: 0 for v in values}
            for scenario in scenarios:
                value = self._get_scenario_value(scenario, dim)
                if value in coverage[dim]:
                    coverage[dim][value] += 1

        gaps = []
        for dim, counts in coverage.items():
            for value, count in counts.items():
                if count == 0:
                    gaps.append(f"{dim}:{value}")

        return CoverageReport(coverage=coverage, gaps=gaps)
```

---

## Part 4: Evaluation Pipeline

### 4.1 Pipeline Architecture

```
+------------------+     +------------------+     +------------------+
|    SCENARIOS     | --> |     ROLLOUT      | --> |     JUDGMENT     |
+------------------+     +------------------+     +------------------+
| Load/Generate    |     | Execute parallel |     | Grade each run   |
| Validate         |     | Capture traces   |     | Aggregate scores |
| Prioritize       |     | Handle HITL      |     | Detect patterns  |
+------------------+     +------------------+     +------------------+
                                                          |
                                                          v
+------------------+     +------------------+     +------------------+
|   IMPROVEMENT    | <-- |    BASELINE      | <-- |     REPORT       |
+------------------+     +------------------+     +------------------+
| Generate fixes   |     | Compare to prev  |     | Compile findings |
| Prioritize       |     | Detect regress   |     | Summarize        |
| Track            |     | Update baseline  |     | Visualize        |
+------------------+     +------------------+     +------------------+
```

### 4.2 Implementation

```python
class EvaluationPipeline:
    """Universal evaluation pipeline."""

    def __init__(
        self,
        scenario_source: ScenarioSource,
        grader_registry: GraderRegistry,
        baseline_manager: BaselineManager
    ):
        self.scenarios = scenario_source
        self.graders = grader_registry
        self.baselines = baseline_manager
        self.results: list[EvaluationResult] = []

    async def run(
        self,
        suite_name: str,
        parallelism: int = 5
    ) -> EvaluationReport:
        """Execute full evaluation pipeline."""

        # 1. Load and validate scenarios
        scenarios = await self.scenarios.load(suite_name)
        self._validate_scenarios(scenarios)

        # 2. Execute scenarios in parallel
        rollout_results = await self._rollout(scenarios, parallelism)

        # 3. Grade each result
        judgments = await self._judge(rollout_results)

        # 4. Aggregate and analyze
        analysis = self._analyze(judgments)

        # 5. Compare to baseline
        baseline = await self.baselines.get_latest(suite_name)
        regression = self._detect_regression(analysis, baseline)

        # 6. Generate improvements
        improvements = self._generate_improvements(analysis, judgments)

        # 7. Compile report
        report = EvaluationReport(
            suite_name=suite_name,
            executed_at=datetime.now(),
            scenarios_run=len(scenarios),
            pass_rate=analysis.pass_rate,
            score=analysis.aggregate_score,
            judgments=judgments,
            regression=regression,
            improvements=improvements,
            by_category=analysis.by_category,
            by_grader=analysis.by_grader
        )

        # 8. Update baseline if improved
        if not regression.detected and analysis.aggregate_score > baseline.score:
            await self.baselines.store(suite_name, analysis)

        return report

    async def _rollout(
        self,
        scenarios: list[Scenario],
        parallelism: int
    ) -> list[RolloutResult]:
        """Execute scenarios in parallel."""
        semaphore = asyncio.Semaphore(parallelism)

        async def run_one(scenario: Scenario) -> RolloutResult:
            async with semaphore:
                try:
                    # Execute via PM
                    result = await chat_with_pm(
                        message=scenario.input.message,
                        media_paths=[m.path for m in scenario.input.media],
                        thread_id=f"eval_{scenario.id}",
                        hitl_mode="auto_approve"  # For testing
                    )
                    return RolloutResult(
                        scenario_id=scenario.id,
                        success=True,
                        trace_id=result.trace_id,
                        output=result.response,
                        execution_time_ms=result.latency_ms
                    )
                except Exception as e:
                    return RolloutResult(
                        scenario_id=scenario.id,
                        success=False,
                        error=str(e)
                    )

        return await asyncio.gather(*[run_one(s) for s in scenarios])

    async def _judge(
        self,
        results: list[RolloutResult]
    ) -> list[Judgment]:
        """Grade each rollout result."""
        judgments = []

        for result in results:
            if not result.success:
                judgments.append(Judgment(
                    scenario_id=result.scenario_id,
                    passed=False,
                    score=0.0,
                    error=result.error
                ))
                continue

            # Get scenario for grading config
            scenario = self.scenarios.get(result.scenario_id)

            # Get trace for analysis
            trace = await get_trace_overview(result.trace_id)

            # Run all graders
            grader_results = []
            for grader_config in scenario.grading.graders:
                grader = self.graders.get(grader_config.type, grader_config.name)
                grade = await grader.grade(
                    scenario=scenario,
                    result=result,
                    trace=trace,
                    config=grader_config.config
                )
                grader_results.append(GraderResult(
                    grader=grader_config.name,
                    weight=grader_config.weight,
                    grade=grade
                ))

            # Calculate weighted score
            total_weight = sum(g.weight for g in grader_results)
            weighted_score = sum(
                g.weight * g.grade.score for g in grader_results
            ) / total_weight

            judgments.append(Judgment(
                scenario_id=result.scenario_id,
                passed=weighted_score >= scenario.grading.pass_threshold,
                score=weighted_score,
                grader_results=grader_results,
                trace_id=result.trace_id
            ))

        return judgments

    def _analyze(self, judgments: list[Judgment]) -> Analysis:
        """Aggregate and analyze judgments."""
        passed = [j for j in judgments if j.passed]
        failed = [j for j in judgments if not j.passed]

        # Group by category
        by_category = defaultdict(list)
        for j in judgments:
            scenario = self.scenarios.get(j.scenario_id)
            by_category[scenario.metadata.domain].append(j)

        # Group by grader
        by_grader = defaultdict(list)
        for j in judgments:
            for gr in j.grader_results:
                by_grader[gr.grader].append(gr.grade)

        return Analysis(
            pass_rate=len(passed) / len(judgments),
            aggregate_score=sum(j.score for j in judgments) / len(judgments),
            passed_count=len(passed),
            failed_count=len(failed),
            by_category={
                cat: {
                    "pass_rate": len([j for j in js if j.passed]) / len(js),
                    "avg_score": sum(j.score for j in js) / len(js)
                }
                for cat, js in by_category.items()
            },
            by_grader={
                grader: {
                    "avg_score": sum(g.score for g in grades) / len(grades),
                    "pass_rate": len([g for g in grades if g.passed]) / len(grades)
                }
                for grader, grades in by_grader.items()
            }
        )

    def _detect_regression(
        self,
        current: Analysis,
        baseline: Baseline | None
    ) -> RegressionResult:
        """Detect performance regression."""
        if not baseline:
            return RegressionResult(detected=False, reason="No baseline")

        score_delta = current.aggregate_score - baseline.score
        pass_rate_delta = current.pass_rate - baseline.pass_rate

        # Significant regression: >5% drop
        if score_delta < -0.05 or pass_rate_delta < -0.05:
            return RegressionResult(
                detected=True,
                severity="major" if score_delta < -0.1 else "minor",
                score_delta=score_delta,
                pass_rate_delta=pass_rate_delta,
                regressed_categories=[
                    cat for cat, stats in current.by_category.items()
                    if stats["avg_score"] < baseline.by_category.get(cat, {}).get("avg_score", 0) - 0.05
                ]
            )

        return RegressionResult(detected=False)

    def _generate_improvements(
        self,
        analysis: Analysis,
        judgments: list[Judgment]
    ) -> list[Improvement]:
        """Generate improvement recommendations."""
        improvements = []

        # Analyze failed judgments for patterns
        failed = [j for j in judgments if not j.passed]

        # Pattern: Same grader failing repeatedly
        grader_failures = defaultdict(list)
        for j in failed:
            for gr in j.grader_results:
                if not gr.grade.passed:
                    grader_failures[gr.grader].append(gr.grade)

        for grader, failures in grader_failures.items():
            if len(failures) >= 3:  # Pattern threshold
                improvements.append(Improvement(
                    priority="HIGH",
                    domain=self._grader_to_domain(grader),
                    finding=f"Grader '{grader}' failed {len(failures)} times",
                    evidence=[f.evidence for f in failures[:3]],
                    recommendation=self._generate_fix_recommendation(grader, failures)
                ))

        # Pattern: Category underperforming
        for cat, stats in analysis.by_category.items():
            if stats["avg_score"] < 0.7:
                improvements.append(Improvement(
                    priority="MEDIUM",
                    domain=cat,
                    finding=f"Category '{cat}' scoring {stats['avg_score']:.2f}",
                    recommendation=f"Review {cat} agent prompt and protocols"
                ))

        return sorted(improvements, key=lambda i: i.priority)
```

---

## Part 5: Continuous Improvement System

### 5.1 Improvement Lifecycle

```
+------------------+
|  EVAL FAILURE    |
+------------------+
        |
        v
+------------------+
|  PATTERN DETECT  | --> "Hallucination in 15% of visual analyst outputs"
+------------------+
        |
        v
+------------------+
|  ROOT CAUSE      | --> "Prompt lacks grounding instruction"
+------------------+
        |
        v
+------------------+
|  IMPROVEMENT     | --> Add grounding section to visual_analyst.prompt
+------------------+
        |
        v
+------------------+
|  IMPLEMENT       | --> Edit prompt file
+------------------+
        |
        v
+------------------+
|  RE-EVALUATE     | --> Run same eval suite
+------------------+
        |
        v
+------------------+
|  VALIDATE FIX    | --> Hallucination rate now 3%
+------------------+
        |
        v
+------------------+
|  UPDATE BASELINE | --> New baseline stored
+------------------+
```

### 5.2 Improvement Generation

```python
class ImprovementEngine:
    """Generate concrete improvements from eval failures."""

    IMPROVEMENT_PATTERNS = {
        "intent_misclassification": {
            "domain": "PROMPT",
            "component": "project_manager.prompt",
            "fix_type": "add_examples",
            "template": "Add canonical examples for intent: {missed_intents}"
        },
        "hallucination": {
            "domain": "PROMPT",
            "component": "{agent_name}.prompt",
            "fix_type": "add_grounding",
            "template": "Add grounding instruction: 'Only report information visible in source data'"
        },
        "tool_sequence_violation": {
            "domain": "PROMPT",
            "component": "{agent_name}.prompt",
            "fix_type": "add_protocol",
            "template": "Add tool sequence protocol: {required_sequence}"
        },
        "schema_violation": {
            "domain": "CODE",
            "component": "{tool_name}.py",
            "fix_type": "add_validation",
            "template": "Add Pydantic validation for: {violated_fields}"
        },
        "context_not_used": {
            "domain": "PROMPT",
            "component": "{agent_name}.prompt",
            "fix_type": "emphasize_context",
            "template": "Add instruction: 'Always incorporate provided context: {context_type}'"
        },
        "hitl_bypass": {
            "domain": "CODE",
            "component": "{specialist_name}.py",
            "fix_type": "enforce_hitl",
            "template": "Add HITL check before tool: {tool_name}"
        }
    }

    def generate(
        self,
        failure_pattern: str,
        evidence: list[str],
        context: dict
    ) -> Improvement:
        """Generate improvement from failure pattern."""
        pattern = self.IMPROVEMENT_PATTERNS.get(failure_pattern)
        if not pattern:
            return Improvement(
                priority="MEDIUM",
                domain="UNKNOWN",
                finding=f"Unknown failure pattern: {failure_pattern}",
                recommendation="Manual investigation required"
            )

        return Improvement(
            priority=self._calculate_priority(failure_pattern, len(evidence)),
            domain=pattern["domain"],
            component=pattern["component"].format(**context),
            fix_type=pattern["fix_type"],
            finding=failure_pattern,
            evidence=evidence,
            recommendation=pattern["template"].format(**context),
            estimated_impact=self._estimate_impact(failure_pattern, len(evidence))
        )

    def _calculate_priority(self, pattern: str, occurrence_count: int) -> str:
        """Calculate improvement priority."""
        critical_patterns = ["hitl_bypass", "schema_violation", "hallucination"]
        if pattern in critical_patterns:
            return "CRITICAL"
        elif occurrence_count >= 5:
            return "HIGH"
        elif occurrence_count >= 3:
            return "MEDIUM"
        return "LOW"

    def _estimate_impact(self, pattern: str, occurrences: int) -> str:
        """Estimate impact of fixing this issue."""
        return f"Could reduce {pattern} by ~{min(occurrences * 10, 90)}%"
```

### 5.3 Improvement Tracking

```python
class ImprovementTracker:
    """Track improvements across eval cycles."""

    def __init__(self, storage: Storage):
        self.storage = storage

    async def log_improvement(
        self,
        improvement: Improvement,
        eval_report_id: str
    ) -> str:
        """Log a new improvement."""
        record = ImprovementRecord(
            id=str(uuid4()),
            created_at=datetime.now(),
            source_eval_id=eval_report_id,
            improvement=improvement,
            status="proposed"
        )
        await self.storage.save(record)
        return record.id

    async def mark_implemented(
        self,
        improvement_id: str,
        implementation_details: str
    ):
        """Mark improvement as implemented."""
        record = await self.storage.get(improvement_id)
        record.status = "implemented"
        record.implemented_at = datetime.now()
        record.implementation_details = implementation_details
        await self.storage.save(record)

    async def mark_validated(
        self,
        improvement_id: str,
        validation_eval_id: str,
        success: bool
    ):
        """Mark improvement as validated (or failed)."""
        record = await self.storage.get(improvement_id)
        record.status = "validated" if success else "failed"
        record.validation_eval_id = validation_eval_id
        record.validated_at = datetime.now()
        await self.storage.save(record)

    async def get_pending(self) -> list[ImprovementRecord]:
        """Get all pending improvements."""
        return await self.storage.query(
            status__in=["proposed", "implemented"]
        )

    async def get_success_rate(self) -> float:
        """Get improvement success rate."""
        all_validated = await self.storage.query(status="validated")
        all_failed = await self.storage.query(status="failed")
        total = len(all_validated) + len(all_failed)
        return len(all_validated) / total if total > 0 else 0.0
```

---

## Part 6: Metrics and Reporting

### 6.1 Core Metrics

```python
class EvalMetrics:
    """Core evaluation metrics."""

    # --- Pass Rates ---
    @staticmethod
    def pass_at_1(judgments: list[Judgment]) -> float:
        """% of scenarios passed on first try."""
        return len([j for j in judgments if j.passed]) / len(judgments)

    @staticmethod
    def pass_at_k(judgments_per_scenario: dict[str, list[Judgment]], k: int) -> float:
        """% of scenarios with at least 1 pass in k tries."""
        passed = 0
        for scenario_id, runs in judgments_per_scenario.items():
            if any(j.passed for j in runs[:k]):
                passed += 1
        return passed / len(judgments_per_scenario)

    @staticmethod
    def pass_k(judgments_per_scenario: dict[str, list[Judgment]], k: int) -> float:
        """% of scenarios passing all k tries (consistency)."""
        consistent = 0
        for scenario_id, runs in judgments_per_scenario.items():
            if all(j.passed for j in runs[:k]):
                consistent += 1
        return consistent / len(judgments_per_scenario)

    # --- Scores ---
    @staticmethod
    def aggregate_score(judgments: list[Judgment]) -> float:
        """Average score across all judgments."""
        return sum(j.score for j in judgments) / len(judgments)

    @staticmethod
    def score_by_category(
        judgments: list[Judgment],
        scenarios: dict[str, Scenario]
    ) -> dict[str, float]:
        """Average score per category."""
        by_cat = defaultdict(list)
        for j in judgments:
            cat = scenarios[j.scenario_id].metadata.domain
            by_cat[cat].append(j.score)
        return {cat: sum(scores) / len(scores) for cat, scores in by_cat.items()}

    # --- Regression ---
    @staticmethod
    def regression_delta(current: float, baseline: float) -> float:
        """Score delta from baseline (negative = regression)."""
        return current - baseline

    # --- Distribution ---
    @staticmethod
    def severity_distribution(judgments: list[Judgment]) -> dict[str, float]:
        """Distribution of failure severities."""
        failed = [j for j in judgments if not j.passed]
        if not failed:
            return {"none": 1.0}

        severities = defaultdict(int)
        for j in failed:
            severities[j.severity] += 1

        total = len(failed)
        return {sev: count / total for sev, count in severities.items()}
```

### 6.2 Report Generation

```python
class ReportGenerator:
    """Generate evaluation reports."""

    def generate(
        self,
        suite_name: str,
        analysis: Analysis,
        judgments: list[Judgment],
        regression: RegressionResult,
        improvements: list[Improvement]
    ) -> EvaluationReport:
        """Generate comprehensive report."""
        return EvaluationReport(
            # Header
            suite_name=suite_name,
            executed_at=datetime.now(),
            version=self._get_system_version(),

            # Summary
            summary=ReportSummary(
                status=self._determine_status(analysis, regression),
                pass_rate=analysis.pass_rate,
                aggregate_score=analysis.aggregate_score,
                regression_detected=regression.detected
            ),

            # Details
            by_category=analysis.by_category,
            by_grader=analysis.by_grader,
            by_severity=EvalMetrics.severity_distribution(judgments),

            # Failures
            failed_scenarios=[
                FailedScenario(
                    scenario_id=j.scenario_id,
                    score=j.score,
                    failed_graders=[
                        gr.grader for gr in j.grader_results
                        if not gr.grade.passed
                    ],
                    evidence=[
                        gr.grade.evidence for gr in j.grader_results
                        if not gr.grade.passed
                    ],
                    trace_link=f"https://smith.langchain.com/o/.../runs/{j.trace_id}"
                )
                for j in judgments if not j.passed
            ],

            # Regression
            regression=regression,

            # Improvements
            improvements=improvements,

            # Trends (if baseline exists)
            trends=self._calculate_trends(suite_name)
        )

    def _determine_status(
        self,
        analysis: Analysis,
        regression: RegressionResult
    ) -> str:
        """Determine overall status."""
        if regression.detected and regression.severity == "major":
            return "CRITICAL"
        elif regression.detected:
            return "WARN"
        elif analysis.pass_rate < 0.8:
            return "FAIL"
        elif analysis.pass_rate < 0.95:
            return "WARN"
        return "PASS"
```

---

## Part 7: Integration

### 7.1 File Structure

```
tests/
|-- evaluation/
    |-- __init__.py
    |-- pipeline.py              # Main evaluation pipeline
    |-- graders/
    |   |-- __init__.py
    |   |-- code_graders.py      # Deterministic graders
    |   |-- model_graders.py     # LLM-based graders
    |   |-- registry.py          # Grader registry
    |-- scenarios/
    |   |-- __init__.py
    |   |-- loader.py            # Load scenarios from YAML
    |   |-- generator.py         # Generate scenario variations
    |   |-- suites/              # Scenario YAML files
    |       |-- intent.yaml
    |       |-- context.yaml
    |       |-- tools.yaml
    |       |-- behavior.yaml
    |       |-- recovery.yaml
    |       |-- hitl.yaml
    |-- analysis/
    |   |-- __init__.py
    |   |-- metrics.py           # Metric calculations
    |   |-- patterns.py          # Pattern detection
    |   |-- regression.py        # Regression detection
    |-- improvements/
    |   |-- __init__.py
    |   |-- generator.py         # Improvement generation
    |   |-- tracker.py           # Improvement tracking
    |-- baseline/
    |   |-- __init__.py
    |   |-- manager.py           # Baseline storage/comparison
    |-- reporting/
    |   |-- __init__.py
    |   |-- generator.py         # Report generation
    |   |-- templates/           # Report templates
    |-- cli.py                   # Command-line interface
    |-- models.py                # Pydantic models
```

### 7.2 CLI Interface

```bash
# Run full evaluation suite
uv run python -m tests.evaluation.cli run --suite all

# Run specific category
uv run python -m tests.evaluation.cli run --suite intent

# Run with specific parallelism
uv run python -m tests.evaluation.cli run --suite all --parallelism 10

# Compare to baseline
uv run python -m tests.evaluation.cli compare --suite intent

# Generate improvements
uv run python -m tests.evaluation.cli improvements --report latest

# Track improvement status
uv run python -m tests.evaluation.cli track-improvements

# Export report
uv run python -m tests.evaluation.cli export --report latest --format html
```

### 7.3 Skill Integration

```yaml
# .claude/skills/e2e-testing.md

## Evaluation Commands

/evaluate [suite]
  - Runs evaluation suite (default: all)
  - Returns summary with pass rate, regressions, top improvements

/evaluate-category [category]
  - Runs evaluation for specific category
  - Categories: intent, context, tools, behavior, recovery, hitl

/check-regression
  - Compares current system to baseline
  - Flags any degradations

/improvements
  - Lists pending improvements
  - Prioritized by impact
```

---

## Part 8: Quick Start

### 8.1 First Evaluation (20-50 Tasks)

```python
# 1. Start with real failures you've observed
initial_scenarios = [
    Scenario(
        id="failure_001",
        input=ScenarioInput(
            message="The actual user message that failed",
            media=[...]
        ),
        expected=Expected(
            intent="what_should_have_happened",
            routing=["correct_specialist"]
        ),
        grading=GradingConfig(
            graders=[
                GraderConfig(type="code", name="correct_routing", weight=1.0)
            ]
        ),
        metadata=Metadata(
            domain="catalog",
            complexity="simple",
            failure_mode="intent_misclassification"
        )
    ),
    # ... 19-49 more from real failures
]

# 2. Run evaluation
pipeline = EvaluationPipeline(...)
report = await pipeline.run("initial_suite")

# 3. Review failures
for failure in report.failed_scenarios:
    print(f"Failed: {failure.scenario_id}")
    print(f"Evidence: {failure.evidence}")
    print(f"Trace: {failure.trace_link}")

# 4. Implement improvements
for improvement in report.improvements:
    print(f"Fix: {improvement.recommendation}")

# 5. Re-run and validate
```

### 8.2 Graduation to Regression Suite

```python
# When pass_rate > 95%, graduate to regression

if report.summary.pass_rate > 0.95:
    # Store as baseline
    await baseline_manager.store("initial_suite", report.analysis)

    # Create regression configuration
    regression_config = {
        "suite": "initial_suite",
        "schedule": "on_commit",  # Run on every commit
        "alert_on_regression": True,
        "threshold": 0.05  # Alert on >5% degradation
    }
```

---

## Part 9: Success Criteria

### 9.1 Framework Health

| Metric | Target | Measurement |
|--------|--------|-------------|
| Grader accuracy | >90% agreement with human | Sample validation |
| Coverage | All 5 pillars tested | Coverage report |
| Regression detection latency | <1 day | Time to alert |
| Improvement success rate | >50% | Validated fixes / total fixes |

### 9.2 System Health (via evals)

| Metric | Initial Target | Stretch Target |
|--------|----------------|----------------|
| Intent classification | >90% | >98% |
| Routing accuracy | >90% | >98% |
| Context utilization | >80% | >95% |
| Tool sequence compliance | >85% | >98% |
| HITL compliance | 100% | 100% |
| Schema compliance | 100% | 100% |
| Hallucination rate | <10% | <2% |
| Error recovery | >80% | >95% |

---

## Summary

This framework provides:

1. **Complete failure taxonomy** covering all 5 pillars (Understand, Reason, Act, Communicate, Recover)
2. **Three-grader architecture** (Code > Model > Human) with selection matrix
3. **Universal scenario framework** with 6 categories and generation strategy
4. **Full evaluation pipeline** with parallel rollout, judgment, and analysis
5. **Continuous improvement system** with pattern detection and fix tracking
6. **Comprehensive metrics** including pass@k, pass^k, regression detection
7. **Integration ready** with CLI, skills, and existing infrastructure

**Start small**: 20-50 scenarios from real failures. **Grade outputs, not paths**. **Prefer deterministic graders**. **Continuous measurement** beats big-bang evaluation.
