# Unified Schema Definitions

**Part of**: [Universal Evaluation Framework](00_INDEX.md)

**Version**: 4.0 - Schema Unification + Skill Support

---

## Overview

This document is the **single source of truth** for all data models used across the evaluation framework. All other documents reference these schemas - they do not define their own.

---

## Core Trace Models

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel


# =============================================================================
# TRACE CAPTURE (Production -> Evaluation)
# =============================================================================

@dataclass
class TraceForEval:
    """
    Trace structure optimized for evaluation.

    This is the canonical format for traces entering the evaluation system.
    Production tracing (via LangSmith) is converted to this format.
    """

    # Identity
    trace_id: str
    thread_id: str
    timestamp: datetime

    # Input
    user_message: str
    media_paths: list[str]
    context: dict[str, Any]  # company_profile, conversation_history, etc.

    # Execution
    pm_reasoning: str
    delegations: list["Delegation"]
    tool_calls: list["ToolCall"]
    interrupts: list["Interrupt"]  # HITL pauses

    # Output
    final_response: str
    state_changes: list["StateChange"]  # DB writes

    # Metadata
    total_tokens: int
    latency_ms: int
    error: str | None = None


@dataclass
class Delegation:
    """PM delegation to sub-agent."""
    target: str  # "visual_analyst", "catalog_specialist", etc.
    task: str
    context_passed: dict[str, Any]
    response_received: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ToolCall:
    """Individual tool invocation."""
    tool_name: str
    agent: str  # Which agent called it
    params: dict[str, Any]
    result: dict[str, Any]
    success: bool
    latency_ms: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Interrupt:
    """HITL interrupt event."""
    interrupt_type: str  # "approval_request", "clarification", etc.
    agent: str
    payload: dict[str, Any]
    resolved: bool = False
    resolution: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class StateChange:
    """Database state change."""
    table: str
    operation: str  # "insert", "update", "delete"
    values: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# HIERARCHICAL TRACE VIEWS (For Investigation)
# =============================================================================

@dataclass
class TraceOverview:
    """
    Level 0: Structure overview (~500-1000 tokens).
    Used for initial triage and focus area identification.
    """
    trace_id: str
    agents: list[str]  # Agent names in execution order
    tools: list[str]  # Tool names called (not params)
    success: bool
    total_tokens: int
    latency_ms: int
    error_summary: str | None = None
    delegation_count: int = 0
    interrupt_count: int = 0


@dataclass
class TraceFocus:
    """
    Level 1: Focused investigation (~1500-3000 tokens).
    Full details for specific agent, tool, or error.
    """
    trace_id: str
    focus_area: str  # "agent:pm", "tool:write_data", "error"

    # Content depends on focus_area
    inputs: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None
    reasoning: str | None = None
    error_details: str | None = None
    surrounding_context: dict[str, Any] | None = None


@dataclass
class TraceDeep:
    """
    Level 2: Full trace (~5000-10000 tokens).
    Complete details for deep investigation.
    """
    trace_id: str
    full_trace: TraceForEval
    child_runs: list[dict[str, Any]]  # All nested runs
    complete_reasoning_chain: str
    all_tool_params: list[dict[str, Any]]
    all_tool_results: list[dict[str, Any]]
```

---

## Scenario Models

```python
# =============================================================================
# SCENARIO DEFINITION
# =============================================================================

@dataclass
class Scenario:
    """
    Atomic unit of evaluation.
    Defines input, expected behavior, and grading configuration.
    """

    # Identity
    id: str
    version: str = "1.0.0"

    # Input specification
    input: "ScenarioInput" = field(default_factory=lambda: ScenarioInput())

    # Expected behavior
    expected: "Expected" = field(default_factory=lambda: Expected())

    # Grading configuration
    grading: "GradingConfig" = field(default_factory=lambda: GradingConfig())

    # Metadata
    metadata: "ScenarioMetadata" = field(default_factory=lambda: ScenarioMetadata())


@dataclass
class ScenarioInput:
    """Input specification for a scenario."""
    message: str = ""
    media: list["MediaRef"] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    inject_failure: dict[str, Any] | None = None  # For error recovery testing


@dataclass
class MediaRef:
    """Reference to media file."""
    path: str
    type: str = "image"  # "image", "document", "video"


@dataclass
class Expected:
    """Expected behavior specification."""

    # Intent/routing (OUTPUT_ONLY: advisory, PATH_STRICT: required)
    intent: str | list[str] | None = None
    routing: list[str] = field(default_factory=list)

    # Tool expectations
    tools: list["ToolExpectation"] = field(default_factory=list)

    # Output expectations
    output: "OutputExpectation" = field(default_factory=lambda: OutputExpectation())

    # State change expectations
    state_changes: list["ExpectedStateChange"] = field(default_factory=list)

    # Behavior expectations (for agent behavior scenarios)
    behavior: list[str] = field(default_factory=list)


@dataclass
class ToolExpectation:
    """Expected tool usage."""
    name: str
    required: bool = True
    before: list[str] = field(default_factory=list)  # Must be called before these
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputExpectation:
    """Expected output characteristics."""
    type: str | None = None  # "approval_request", "response", "question", "refusal"
    schema: str | None = None  # Pydantic model name for validation
    contains: list[str] = field(default_factory=list)
    not_contains: list[str] = field(default_factory=list)


@dataclass
class ExpectedStateChange:
    """Expected database state change."""
    table: str
    operation: str  # "insert", "update", "delete"
    values: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioMetadata:
    """Scenario metadata for organization and filtering."""
    domain: str = "general"  # "catalog", "creative", "marketing", etc.
    complexity: str = "medium"  # "simple", "medium", "complex", "adversarial"
    failure_mode: str | None = None  # Target failure mode
    tags: list[str] = field(default_factory=list)
    source: str = "manual"  # "manual", "production", "generated"
    priority: str = "P1"  # "P0", "P1", "P2"
```

---

## Grading Models

```python
# =============================================================================
# GRADING CONFIGURATION
# =============================================================================

class GradingMode(Enum):
    """
    How strictly to grade execution paths.

    OUTPUT_ONLY (default): Grade final output, ignore path taken.
        - Path deviations logged but not scored
        - Use for most scenarios

    PATH_ADVISORY: Log path deviations, don't fail on them.
        - Useful for understanding agent behavior patterns
        - Deviations inform investigation, not pass/fail

    PATH_STRICT: Fail on path deviations.
        - ONLY for safety-critical scenarios (HITL compliance)
        - Use sparingly - agents should be free to find creative solutions
    """
    OUTPUT_ONLY = "output_only"
    PATH_ADVISORY = "path_advisory"
    PATH_STRICT = "path_strict"


@dataclass
class GradingConfig:
    """Grading configuration for a scenario."""
    mode: GradingMode = GradingMode.OUTPUT_ONLY
    graders: list["GraderSpec"] = field(default_factory=list)
    pass_threshold: float = 0.7
    partial_credit: bool = True


@dataclass
class GraderSpec:
    """Specification for a grader to apply."""
    type: str  # "code", "model", "human"
    name: str  # Grader function/class name
    weight: float = 1.0
    config: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# GRADING RESULTS
# =============================================================================

@dataclass
class GradeResult:
    """
    Result from a single grader.
    This is what grader functions return.
    """
    passed: bool
    score: float  # 0.0 to 1.0
    evidence: Any = None  # Supporting evidence for the grade
    reasoning: str | None = None  # Explanation (model graders)


@dataclass
class GraderOutput:
    """
    Grader result with metadata.
    Wraps GradeResult with grader identification.
    """
    grader_name: str
    grader_type: str  # "code", "model", "human"
    grade: GradeResult
    weight: float
    execution_time_ms: int = 0


@dataclass
class Judgment:
    """
    Final judgment for a scenario execution.
    Aggregates all grader results into pass/fail decision.
    """
    scenario_id: str
    trace_id: str

    # Overall result
    passed: bool
    score: float  # Weighted aggregate of grader scores

    # Grader details
    grader_outputs: list[GraderOutput] = field(default_factory=list)

    # Path analysis (logged regardless of mode, scored only in PATH_STRICT)
    path_deviations: list["PathDeviation"] = field(default_factory=list)

    # Metadata
    grading_mode: GradingMode = GradingMode.OUTPUT_ONLY
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PathDeviation:
    """Record of path deviation from expected."""
    type: str  # "routing", "tool_sequence", "tool_params"
    expected: Any
    actual: Any
    analysis: str  # Why it deviated
    severity: str = "info"  # "info", "warning", "error"
```

---

## Investigation Models

```python
# =============================================================================
# INVESTIGATION (Intelligence Layer)
# =============================================================================

@dataclass
class InvestigationTrigger:
    """What triggered the investigation."""
    type: str  # "eval_failure", "production_feedback", "manual"
    eval_report_id: str | None = None
    scenario_ids: list[str] = field(default_factory=list)
    trace_ids: list[str] = field(default_factory=list)


@dataclass
class Finding:
    """Individual finding during investigation."""
    level: int  # 0, 1, or 2 (which investigation level)
    area: str  # "pm_routing", "tool_params", "hallucination", etc.
    observation: str
    evidence: str  # Specific trace excerpt
    significance: str  # "root_cause", "contributing", "symptom"


@dataclass
class FixProposal:
    """Proposed fix for root cause."""
    target: str  # "prompt", "tool", "code", "architecture"
    component: str  # File path, e.g., "prompts/project_manager.prompt"
    change_type: str  # "add_example", "add_instruction", "modify_logic"
    description: str
    specific_changes: str  # Actual text/code to add/modify
    confidence: float  # 0.0 to 1.0
    risk_assessment: str
    validation_scenarios: list[str] = field(default_factory=list)


@dataclass
class InvestigationSession:
    """Complete investigation session state."""

    # Input
    trigger: InvestigationTrigger
    failed_judgments: list[Judgment] = field(default_factory=list)

    # Trace data (keyed by scenario_id)
    traces: dict[str, TraceOverview | TraceFocus | TraceDeep] = field(default_factory=dict)

    # Investigation state
    current_level: int = 0
    focus_areas: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    # Output
    root_cause: str | None = None
    pattern_detected: str | None = None
    fix_proposal: FixProposal | None = None
    new_scenarios: list[Scenario] = field(default_factory=list)
    confidence: float = 0.0

    # Resource tracking
    tokens_used: int = 0
    budget_exceeded: bool = False


# =============================================================================
# TOKEN BUDGET (Canonical Values)
# =============================================================================

@dataclass
class TokenBudget:
    """
    Token budget configuration.

    CANONICAL VALUES - use these throughout the framework:
    - L0: 500-1000 tokens (structure overview)
    - L1: 1500-3000 tokens (focused investigation)
    - L2: 5000-10000 tokens (deep dive)
    """
    investigation_total: int = 50000

    # Target token counts per level
    level_0_target: int = 750      # ~500-1000 range
    level_1_target: int = 2250     # ~1500-3000 range
    level_2_target: int = 7500     # ~5000-10000 range

    # Overflow handling
    overflow_strategy: str = "summarize"  # "summarize", "chunk", "abort"
```

---

## Validation Models

```python
# =============================================================================
# FIX VALIDATION
# =============================================================================

@dataclass
class ValidationConfig:
    """Configuration for k-out-of-n fix validation."""
    min_runs: int = 5
    max_runs: int = 10
    required_pass_rate: float = 0.9  # 90% must pass
    confidence_threshold: float = 0.95
    consistency_required: bool = True


@dataclass
class ValidationResult:
    """Result of fix validation."""
    passed: bool
    pass_rate: float
    consistency_score: float
    total_runs: int
    passes: int
    fails: int
    run_details: list[dict[str, Any]] = field(default_factory=list)
```

---

## Pipeline Models

```python
# =============================================================================
# PIPELINE EXECUTION
# =============================================================================

@dataclass
class PipelineOptions:
    """Options for pipeline execution."""
    parallelism: int = 5
    filter_tags: list[str] = field(default_factory=list)
    baseline_comparison: bool = True
    auto_investigate: bool = True
    hitl_mode: str = "auto_approve"  # "auto_approve", "pause", "skip"


@dataclass
class RolloutResult:
    """Result of executing a single scenario."""
    scenario_id: str
    trace_id: str
    response: str
    routing: list[str]
    tools_called: list[str]
    success: bool
    error: str | None = None
    latency_ms: int = 0


@dataclass
class EvaluationReport:
    """Complete evaluation report."""

    # Identity
    id: str
    suite: str
    timestamp: datetime

    # Summary
    total_scenarios: int
    passed: int
    failed: int

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total_scenarios if self.total_scenarios > 0 else 0.0

    # Details
    judgments: list[Judgment] = field(default_factory=list)

    @property
    def failures(self) -> list[Judgment]:
        return [j for j in self.judgments if not j.passed]

    # Metrics
    metrics: dict[str, float] = field(default_factory=dict)

    # Analysis
    regression_analysis: "RegressionAnalysis | None" = None
    investigation: InvestigationSession | None = None


@dataclass
class RegressionAnalysis:
    """Comparison to baseline."""
    baseline_id: str
    new_failures: list[str]  # Scenario IDs that newly failed
    fixed: list[str]  # Scenario IDs that newly passed
    stable_pass: list[str]
    stable_fail: list[str]
    score_delta: dict[str, float]  # scenario_id -> score change


@dataclass
class Baseline:
    """Baseline scores for comparison."""
    id: str
    suite: str
    scores: dict[str, float]  # scenario_id -> score
    updated_at: datetime
    report_id: str

    # Smoothing for noise resistance
    score_history: dict[str, list[float]] = field(default_factory=dict)
    smoothing_window: int = 3

    def get_smoothed_score(self, scenario_id: str) -> float:
        """Get smoothed score to reduce noise sensitivity."""
        history = self.score_history.get(scenario_id, [])
        if not history:
            return self.scores.get(scenario_id, 0.0)
        recent = history[-self.smoothing_window:]
        return sum(recent) / len(recent)
```

---

## Registry Interfaces

```python
# =============================================================================
# REGISTRIES AND INTERFACES
# =============================================================================

from abc import ABC, abstractmethod


class Grader(ABC):
    """Base interface for all graders."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique grader name."""
        pass

    @property
    @abstractmethod
    def grader_type(self) -> str:
        """Grader type: 'code', 'model', or 'human'."""
        pass

    @abstractmethod
    async def grade(
        self,
        output: Any,
        expected: Expected,
        trace: TraceForEval,
        config: dict[str, Any] | None = None
    ) -> GradeResult:
        """Execute grading and return result."""
        pass


class GraderRegistry:
    """
    Registry for grader lookup.

    Usage:
        registry = GraderRegistry()
        registry.register(MyCodeGrader())
        grader = registry.get("my_code_grader")
    """

    def __init__(self):
        self._graders: dict[str, Grader] = {}

    def register(self, grader: Grader) -> None:
        """Register a grader."""
        self._graders[grader.name] = grader

    def get(self, name: str) -> Grader:
        """Get grader by name."""
        if name not in self._graders:
            raise KeyError(f"Grader '{name}' not found. Available: {list(self._graders.keys())}")
        return self._graders[name]

    def list_graders(self) -> list[str]:
        """List all registered grader names."""
        return list(self._graders.keys())


class Storage(ABC):
    """Abstract storage interface."""

    @abstractmethod
    async def get(self, key: str) -> Any:
        """Get value by key."""
        pass

    @abstractmethod
    async def put(self, key: str, value: Any) -> None:
        """Store value by key."""
        pass

    @abstractmethod
    async def append(self, collection: str, item: Any) -> None:
        """Append item to collection."""
        pass

    @abstractmethod
    async def query(self, collection: str, filters: dict[str, Any]) -> list[Any]:
        """Query collection with filters."""
        pass
```

---

## Human Annotation Models

```python
# =============================================================================
# HUMAN ANNOTATION (LangSmith Integration)
# =============================================================================

@dataclass
class HumanAnnotation:
    """Human annotation from LangSmith queue."""
    trace_id: str
    scores: dict[str, float]
    notes: str | None = None
    annotator_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CalibrationSample:
    """Sample for model grader calibration."""
    trace_id: str
    human_score: float
    human_notes: str | None = None
    model_score: float | None = None  # Filled after model grading


@dataclass
class CalibrationResult:
    """Result of calibrating model grader against human."""
    correlation: float  # Spearman correlation
    p_value: float
    calibrated: bool  # correlation > 0.8
    sample_size: int
    recommendation: str
```

---

## Cost Models

```python
# =============================================================================
# COST TRACKING
# =============================================================================

@dataclass
class CostConfig:
    """Cost configuration for evaluation components (USD)."""

    # Per-unit costs
    scenario_execution: float = 0.02
    code_grader: float = 0.0
    model_grader_haiku: float = 0.01
    model_grader_sonnet: float = 0.03
    investigation_l0: float = 0.005
    investigation_l1: float = 0.02
    investigation_l2: float = 0.10
    fix_generation: float = 0.15

    # Budget caps
    daily_eval_budget: float = 50.0
    daily_investigation_budget: float = 30.0
    per_investigation_cap: float = 5.0


@dataclass
class CostEstimate:
    """Estimated cost for an operation."""
    execution: float
    grading: float
    total: float
    within_budget: bool


@dataclass
class InvestigationDecision:
    """Decision on whether to proceed with investigation."""
    should_proceed: bool
    estimated_cost: float
    remaining_budget: float
    roi: float  # Return on investment score
```

---

## Coverage Analysis Models

```python
# =============================================================================
# COVERAGE ANALYSIS (for /eval-coverage skill)
# =============================================================================

@dataclass
class CoverageGap:
    """Identified gap in scenario coverage."""
    pillar: str  # "intent", "routing", "context", "state", "output"
    category: str  # 1-7 categories from 04_SCENARIO_FRAMEWORK.md
    current_count: int
    target_count: int
    priority: int  # Higher = more urgent
    context: str  # Additional context for scenario generation
    suggested_scenarios: list[str] = field(default_factory=list)


@dataclass
class PillarCoverage:
    """Coverage statistics for a single failure pillar."""
    pillar: str
    scenario_count: int
    total_scenarios: int
    percentage: float
    is_critical: bool  # True if below 10% threshold


@dataclass
class CategoryCoverage:
    """Coverage statistics for a scenario category."""
    category: str
    category_number: int  # 1-7
    scenario_count: int
    total_scenarios: int
    percentage: float
    is_critical: bool  # True if below 5% threshold


@dataclass
class CoverageReport:
    """
    Complete coverage analysis report.

    Generated by /eval-coverage skill.
    """

    # Identity
    id: str
    timestamp: datetime
    dataset_name: str

    # Summary
    total_scenarios: int
    positive_scenarios: int
    negative_scenarios: int

    @property
    def balance_ratio(self) -> float:
        """Positive/negative ratio. Target: ~1.0 (50/50)."""
        if self.negative_scenarios == 0:
            return float('inf')
        return self.positive_scenarios / self.negative_scenarios

    # Pillar coverage (5 pillars)
    pillar_coverage: list[PillarCoverage] = field(default_factory=list)

    # Category coverage (7 categories)
    category_coverage: list[CategoryCoverage] = field(default_factory=list)

    # Identified gaps
    gaps: list[CoverageGap] = field(default_factory=list)

    @property
    def critical_gaps(self) -> list[CoverageGap]:
        """Gaps with priority >= 5."""
        return [g for g in self.gaps if g.priority >= 5]

    # Actions taken
    scenarios_created: list[str] = field(default_factory=list)  # IDs


@dataclass
class QualityGateResult:
    """
    Result of a single quality gate in /eval-writer.

    All 7 gates produce one of these.
    """
    gate_name: str  # "schema", "grader", "dry_run", "consistency", "balance", "duplicate", "abstraction"
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioCreationResult:
    """
    Result of /eval-writer scenario creation.
    """
    scenario_id: str | None  # None if creation failed
    success: bool
    mode: str  # "from-trace", "from-failure", "from-spec", "from-gap", "adversarial", "mutate"
    quality_gate_results: list[QualityGateResult] = field(default_factory=list)
    added_to_dataset: str | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
```

---

## Related Documents

- [00_INDEX.md](00_INDEX.md) - Framework overview
- [09_IMPLEMENTATION_GUIDE.md](09_IMPLEMENTATION_GUIDE.md) - How to implement using these schemas
- [10_SKILL_ARCHITECTURE.md](10_SKILL_ARCHITECTURE.md) - Skill specifications that use these schemas

