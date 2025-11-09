"""Pydantic models for autonomous testing framework tools.

All return types for the 5 essential observation tools.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# Execution Tool Models
# ============================================================================

class ExecutionResult(BaseModel):
    """Result of scenario execution via execute_scenario()."""

    success: bool
    """Whether scenario completed successfully."""

    thread_id: str
    """LangGraph thread ID (format: console:test_abc123)."""

    trace_url: str
    """LangSmith trace URL for viewing in browser."""

    trace_id: str
    """LangSmith trace ID for API queries."""

    products_created: int
    """Number of products created in database."""

    execution_time_seconds: float
    """Total execution time."""

    interrupt_occurred: bool = False
    """Whether HITL interrupt was detected during execution."""

    approval_message: str | None = None
    """The approval request message sent by PM (if interrupt occurred)."""

    approval_type: str | None = None
    """Type of approval: 'product' or 'campaign' (if interrupt occurred)."""

    is_batch_approval: bool = False
    """Whether this was a batch approval request (multiple items)."""

    errors: list[str] = Field(default_factory=list)
    """List of error messages if failed."""


# ============================================================================
# Trace Analysis Models
# ============================================================================

class RunNode(BaseModel):
    """Single run node in hierarchical trace tree.

    Used by TraceOverview for Level 0 analysis.
    """

    run_id: str
    """Unique run ID for drilling down with get_run_details()."""

    name: str
    """Run name: 'PM' | 'CatalogingDept' | 'ImageAnalysisSpecialist' | 'save_product'."""

    run_type: str
    """Run type: 'chain' | 'llm' | 'tool'."""

    status: str
    """Status: 'success' | 'error'."""

    start_time: datetime
    """When run started."""

    end_time: datetime | None = None
    """When run ended."""

    duration_ms: int
    """Duration in milliseconds."""

    error: str | None = None
    """High-level error message if failed (not full traceback)."""

    children: list['RunNode'] = Field(default_factory=list)
    """Child runs (recursive tree structure)."""


class TraceOverview(BaseModel):
    """Hierarchical overview of trace execution (Level 0).

    Metadata only, no inputs/outputs. ~500 tokens per trace.
    """

    trace_id: str
    """LangSmith trace ID."""

    total_runs: int
    """Total number of runs in trace."""

    total_cost: float
    """Total cost in dollars."""

    total_latency_ms: int
    """Total execution time in milliseconds."""

    run_tree: list[RunNode]
    """Hierarchical tree of all runs."""


class RunMetadata(BaseModel):
    """Metadata for a specific run."""

    model: str | None = None
    """Model used (e.g., 'gpt-4')."""

    total_tokens: int | None = None
    """Token usage."""

    latency_ms: int | None = None
    """Latency in milliseconds."""

    parent_run_id: str | None = None
    """Parent run ID for context."""


class RunDetails(BaseModel):
    """Detailed information for a specific run (Level 1).

    Includes inputs, outputs, and error. ~1,500 tokens per run.
    """

    run_id: str
    """Run ID."""

    name: str
    """Run name."""

    run_type: str
    """Run type: 'chain' | 'llm' | 'tool'."""

    inputs: dict[str, Any] = Field(default_factory=dict)
    """Full inputs (prompts, tool arguments, etc)."""

    outputs: dict[str, Any] | None = None
    """Full outputs if successful (structured output, tool results)."""

    error: str | None = None
    """Full error message and traceback if failed."""

    metadata: RunMetadata
    """Additional metadata."""


class ToolCall(BaseModel):
    """Tool call made by assistant."""

    name: str
    """Tool name."""

    arguments: dict[str, Any]
    """Tool arguments."""


class ToolResult(BaseModel):
    """Tool execution result."""

    name: str
    """Tool name."""

    result: Any
    """Tool return value."""


class Message(BaseModel):
    """Single message in conversation."""

    role: str
    """Message role: 'system' | 'user' | 'assistant'."""

    content: str
    """Message content (text, JSON, etc)."""

    tool_calls: list[ToolCall] | None = None
    """Tool calls made by assistant."""

    tool_results: list[ToolResult] | None = None
    """Tool results returned."""


class RunMessages(BaseModel):
    """Full conversation messages for a run (Level 2).

    Expensive - ~5,000+ tokens. Use sparingly.
    """

    run_id: str
    """Run ID."""

    messages: list[Message]
    """All messages in conversation."""


# ============================================================================
# Multi-Trace Workflow Story Models (for HITL workflows)
# ============================================================================

class HITLDecision(BaseModel):
    """User decision from HITL interrupt."""

    product_index: int
    """Index of product in batch."""

    action: str
    """User action: 'approved' | 'edited' | 'rejected'."""

    original_data: dict[str, Any]
    """Original extracted product data."""

    edited_data: dict[str, Any] | None = None
    """Edited data if action was 'edited'."""


class WorkflowTrace(BaseModel):
    """Single trace within multi-trace HITL workflow."""

    trace_id: str
    """LangSmith trace ID."""

    trace_url: str
    """LangSmith trace URL."""

    sequence: int
    """Trace sequence (1=initial, 2=first resume, etc)."""

    overview: TraceOverview
    """Hierarchical trace overview."""

    is_hitl_interrupt: bool
    """Whether this trace ended with HITL interrupt."""

    hitl_decisions: list[HITLDecision] = Field(default_factory=list)
    """User decisions extracted from resume trace inputs."""


class WorkflowStory(BaseModel):
    """Complete HITL workflow narrative across multiple traces.

    HITL workflows span multiple traces:
    1. Initial trace: PM → Dept → HITL interrupt
    2. Resume trace(s): User decisions → PM processes → Final save

    This model correlates all traces to show complete story.
    """

    thread_id: str
    """Thread ID linking all traces."""

    total_traces: int
    """Number of traces analyzed."""

    traces: list[WorkflowTrace]
    """All traces in chronological order."""

    products_extracted: int
    """Total products extracted in initial trace."""

    products_saved: int
    """Final products saved to database."""

    products_rejected: int
    """Products rejected by user."""

    products_edited: int
    """Products edited by user."""

    total_cost: float
    """Total cost across all traces."""

    total_latency_ms: int
    """Total execution time across all traces."""


# ============================================================================
# Test History Models
# ============================================================================

class ExecutionRecord(BaseModel):
    """Single test execution record."""

    timestamp: datetime
    """When test was executed."""

    scenario_id: str
    """Scenario identifier."""

    thread_id: str
    """LangGraph thread ID."""

    trace_url: str
    """LangSmith trace URL."""

    success: bool
    """Whether test passed."""

    products_created: int
    """Products created in database."""

    execution_time_seconds: float
    """Execution time."""

    errors_summary: str = ""
    """Brief error summary if failed."""


class ExecutionHistory(BaseModel):
    """History of test executions."""

    tests: list[ExecutionRecord]
    """List of test executions, newest first."""


# ============================================================================
# LLM Trace Extraction Models (for prompt analysis)
# ============================================================================

class LLMCallNode(BaseModel):
    """Single LLM invocation with prompt and output.

    Designed for prompt analysis and optimization. Extracts only LLM calls
    from trace tree with full prompt content and outputs.
    """

    run_id: str
    """Unique run ID for reference."""

    agent_name: str
    """Agent name: 'PM' | 'CatalogingDept' | 'ImageAnalysisSpecialist' | etc."""

    hierarchy_level: str
    """Hierarchy level: 'orchestrator' | 'department' | 'specialist'."""

    # Prompt content
    system_prompt: str | None = None
    """Full system prompt (extracted from first message if type=system)."""

    user_messages: list[dict[str, Any]] = Field(default_factory=list)
    """All user/context messages sent to LLM (excludes system message)."""

    assistant_output: dict[str, Any] | None = None
    """Generated response from LLM (structured or text)."""

    # Metadata
    model: str | None = None
    """Model used (e.g., 'gpt-4o-mini')."""

    total_tokens: int | None = None
    """Token usage for this LLM call."""

    latency_ms: int | None = None
    """Latency in milliseconds."""

    status: str
    """Status: 'success' | 'error'."""

    error: str | None = None
    """Error message if failed."""

    # Hierarchy context
    parent_agent: str | None = None
    """Parent agent name for context (who delegated to this agent)."""

    children: list['LLMCallNode'] = Field(default_factory=list)
    """Child LLM calls (recursive tree structure)."""


class LLMTraceTree(BaseModel):
    """Filtered trace showing only LLM calls with prompts and outputs.

    Optimized for prompt analysis and optimization. Provides hierarchical
    view of all LLM invocations with full prompt content.

    Token cost: ~2-5k tokens per trace (vs 50k+ for full dump)
    """

    trace_id: str
    """LangSmith trace ID."""

    trace_url: str
    """LangSmith trace URL."""

    total_llm_calls: int
    """Number of LLM calls in trace."""

    total_tokens: int
    """Total tokens across all LLM calls."""

    total_cost: float
    """Total cost in dollars."""

    llm_tree: list[LLMCallNode]
    """Hierarchical tree of LLM calls (root calls only)."""


# Enable forward references for recursive models
RunNode.model_rebuild()
LLMCallNode.model_rebuild()
