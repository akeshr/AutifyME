"""Pydantic models for the Workflow Evaluation Framework.

These models structure the data that evaluation scripts return,
making it easy for intelligent agents to consume and analyze.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Evaluation Context Models
# =============================================================================


class ToolCallSummary(BaseModel):
    """Summary of a tool call for quick analysis."""

    name: str
    """Tool name."""

    args_summary: str
    """Human-readable summary of arguments."""

    result_summary: str
    """Human-readable summary of result."""

    success: bool
    """Whether tool call succeeded."""


class ExecutionNode(BaseModel):
    """Minimal representation of a workflow execution node.

    Captures the essential information for evaluation without
    the noise of full LangSmith run data.
    """

    id: str
    """Run ID for drilling down if needed."""

    agent: str
    """Meaningful agent name (not 'ChatOpenAI')."""

    type: str
    """Node type: orchestrator | department | specialist | tool."""

    sequence: int
    """Execution order (1-indexed)."""

    # Decision information
    decision_summary: str | None = None
    """What this node decided (one line)."""

    reasoning_visible: bool = False
    """Whether the agent showed its reasoning."""

    reasoning_snippet: str | None = None
    """Key reasoning excerpt if visible."""

    # Tool usage
    tool_calls: list[ToolCallSummary] = Field(default_factory=list)
    """Summary of tool calls made."""

    # Output information
    output_summary: str | None = None
    """Key output (not full blob)."""

    output_complete: bool = True
    """Whether output has all expected fields."""

    # Context tracking
    context_received_summary: str | None = None
    """Summary of input context."""

    context_keys_used: list[str] = Field(default_factory=list)
    """Which context keys were utilized."""

    context_keys_ignored: list[str] = Field(default_factory=list)
    """Which context keys were NOT utilized."""

    # Status
    status: str
    """Status: success | error."""

    error_summary: str | None = None
    """Error message if failed."""

    latency_ms: int = 0
    """Execution time in milliseconds."""

    cost: float = 0.0
    """Cost in dollars."""

    # Hierarchy
    children: list["ExecutionNode"] = Field(default_factory=list)
    """Child nodes (recursive)."""


class MinimalExecutionTree(BaseModel):
    """Compact representation of workflow execution.

    The minimal tree captures who/what/why/how without
    the noise of full LangSmith traces.
    """

    trace_id: str
    """LangSmith trace ID."""

    trace_url: str
    """LangSmith trace URL for browser viewing."""

    outcome: str
    """Workflow outcome: success | failure | partial."""

    total_nodes: int
    """Total number of execution nodes."""

    total_llm_calls: int
    """Number of LLM invocations."""

    total_tool_calls: int
    """Number of tool calls."""

    total_cost: float
    """Total cost in dollars."""

    total_latency_ms: int
    """Total execution time in milliseconds."""

    nodes: list[ExecutionNode]
    """Flat list of nodes in execution order."""

    tree: list[ExecutionNode]
    """Hierarchical tree structure."""


class Anomaly(BaseModel):
    """Detected anomaly in trace execution."""

    type: str
    """Anomaly type: CONTEXT_LOSS | UNEXPECTED_ROUTING | TOOL_FAILURE | etc."""

    severity: str
    """Severity: critical | major | minor."""

    location: str
    """Which node/agent has the anomaly."""

    description: str
    """Human-readable description."""

    evidence: dict[str, Any] = Field(default_factory=dict)
    """Evidence supporting the anomaly detection."""

    suggested_investigation: str | None = None
    """What to look at next."""


class ComponentInfo(BaseModel):
    """Information about a workflow component (agent/specialist)."""

    name: str
    """Component name."""

    type: str
    """Type: orchestrator | department | specialist."""

    prompt_file: str
    """Path to prompt file."""

    prompt_content: str
    """Actual prompt text."""

    code_file: str | None = None
    """Path to implementation file."""

    tools: list[str] = Field(default_factory=list)
    """Tools available to this component."""


class HistoricalIssue(BaseModel):
    """Past issue for pattern matching."""

    pattern: str
    """Issue pattern description."""

    frequency: str
    """How often this occurs."""

    root_cause: str
    """Identified root cause."""

    fix_applied: str | None = None
    """What fix was applied."""

    fix_worked: bool | None = None
    """Whether the fix resolved it."""


class GoldenComparison(BaseModel):
    """Comparison to golden (known-good) trace."""

    golden_trace_id: str
    """ID of golden trace."""

    structural_match: bool
    """Whether execution paths match."""

    decision_differences: list[dict[str, Any]] = Field(default_factory=list)
    """Where decisions diverged."""

    output_differences: list[dict[str, Any]] = Field(default_factory=list)
    """Where outputs differed."""

    performance_delta: dict[str, float] = Field(default_factory=dict)
    """Latency/cost differences."""


class EvaluationContext(BaseModel):
    """Complete context for evaluating a single trace.

    This is the primary output of get_evaluation_context().
    Contains everything an intelligent agent needs to evaluate
    a workflow execution.
    """

    # Trace data
    trace: MinimalExecutionTree
    """Minimal execution tree of the trace."""

    anomalies: list[Anomaly] = Field(default_factory=list)
    """Pre-detected anomalies."""

    # Workflow expectations
    workflow_name: str
    """Name of the workflow being evaluated."""

    expected_flow: str
    """Expected execution flow description."""

    success_criteria: list[str] = Field(default_factory=list)
    """What constitutes success."""

    # Component details
    components: dict[str, ComponentInfo] = Field(default_factory=dict)
    """Information about each component in the trace."""

    # Historical context
    similar_issues: list[HistoricalIssue] = Field(default_factory=list)
    """Past issues matching patterns in this trace."""

    recent_improvements: list[dict[str, Any]] = Field(default_factory=list)
    """Recent changes to this workflow."""

    # Golden comparison
    golden_comparison: GoldenComparison | None = None
    """Comparison to golden trace if available."""

    # Metadata
    evaluated_at: datetime = Field(default_factory=datetime.now)
    """When this context was generated."""


# =============================================================================
# Batch Analysis Models
# =============================================================================


class FailureCluster(BaseModel):
    """Group of similar failures."""

    pattern: str
    """Failure pattern description."""

    count: int
    """Number of occurrences."""

    trace_ids: list[str]
    """IDs of traces with this failure."""

    common_cause: str | None = None
    """Identified common cause."""

    suggested_fix: str | None = None
    """Suggested fix for this pattern."""


class ImprovementCandidate(BaseModel):
    """Potential improvement identified from batch analysis."""

    issue: str
    """Issue description."""

    frequency: str
    """How often this occurs (e.g., '12%')."""

    impact: str
    """Impact level: high | medium | low."""

    affected_traces: int
    """Number of traces affected."""

    suggested_fix: str
    """Suggested improvement."""

    domain: str
    """Improvement domain: prompt | tool | architecture | context."""


class BatchAnalysis(BaseModel):
    """Analysis of multiple traces for pattern detection."""

    # Summary statistics
    total_traces: int
    """Number of traces analyzed."""

    success_rate: float
    """Proportion of successful traces."""

    avg_latency_ms: float
    """Average latency across traces."""

    avg_cost: float
    """Average cost per trace."""

    # Time range
    start_time: datetime
    """Start of analysis period."""

    end_time: datetime
    """End of analysis period."""

    # Failure analysis
    failure_clusters: list[FailureCluster] = Field(default_factory=list)
    """Groups of similar failures."""

    # Decision distribution
    decision_distribution: dict[str, dict[str, float]] = Field(default_factory=dict)
    """Distribution of decisions per decision point."""

    # Outliers
    outliers: list[dict[str, Any]] = Field(default_factory=list)
    """Traces with unusual characteristics."""

    # Improvement opportunities
    improvement_candidates: list[ImprovementCandidate] = Field(default_factory=list)
    """Identified improvement opportunities ranked by impact."""


# =============================================================================
# Trace Comparison Models
# =============================================================================


class TraceComparison(BaseModel):
    """Side-by-side comparison of two traces."""

    trace_a_id: str
    """First trace ID."""

    trace_b_id: str
    """Second trace ID."""

    # Structural comparison
    structural_match: bool
    """Whether execution paths match."""

    nodes_only_in_a: list[str] = Field(default_factory=list)
    """Nodes present only in trace A."""

    nodes_only_in_b: list[str] = Field(default_factory=list)
    """Nodes present only in trace B."""

    # Decision comparison
    decision_differences: list[dict[str, Any]] = Field(default_factory=list)
    """Nodes where different decisions were made."""

    # Output comparison
    output_differences: list[dict[str, Any]] = Field(default_factory=list)
    """Nodes where outputs differed."""

    # Performance comparison
    latency_delta_ms: int
    """Latency difference (B - A)."""

    latency_delta_pct: float
    """Latency difference as percentage."""

    cost_delta: float
    """Cost difference (B - A)."""

    cost_delta_pct: float
    """Cost difference as percentage."""

    # Outcome comparison
    outcome_a: str
    """Outcome of trace A."""

    outcome_b: str
    """Outcome of trace B."""


# =============================================================================
# Verification Models
# =============================================================================


class CriterionResult(BaseModel):
    """Result of checking a single criterion."""

    criterion: str
    """What was being checked."""

    passed: bool
    """Whether criterion was met."""

    evidence: str | None = None
    """Evidence for the result."""


class VerificationResult(BaseModel):
    """Result of improvement verification."""

    # Execution info
    scenario_executed: str
    """Description of scenario that was run."""

    trace_id: str
    """ID of the new trace."""

    trace_url: str
    """URL to view the trace."""

    # Criteria checking
    criteria_results: list[CriterionResult]
    """Results for each criterion."""

    all_passed: bool
    """Whether all criteria passed."""

    # Comparison to before
    compared_to_trace: str | None = None
    """ID of trace compared against."""

    issues_resolved: list[str] = Field(default_factory=list)
    """Issues that are now fixed."""

    issues_remaining: list[str] = Field(default_factory=list)
    """Issues that persist."""

    new_issues: list[str] = Field(default_factory=list)
    """New issues introduced (regressions)."""

    # Performance impact
    latency_delta_pct: float | None = None
    """Latency change as percentage."""

    cost_delta_pct: float | None = None
    """Cost change as percentage."""


# Enable forward references
ExecutionNode.model_rebuild()
