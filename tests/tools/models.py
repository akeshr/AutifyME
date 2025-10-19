"""Pydantic models for autonomous testing framework tools.

All return types for the 5 essential observation tools.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
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

    errors: List[str] = Field(default_factory=list)
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

    end_time: Optional[datetime] = None
    """When run ended."""

    duration_ms: int
    """Duration in milliseconds."""

    error: Optional[str] = None
    """High-level error message if failed (not full traceback)."""

    children: List['RunNode'] = Field(default_factory=list)
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

    run_tree: List[RunNode]
    """Hierarchical tree of all runs."""


class RunMetadata(BaseModel):
    """Metadata for a specific run."""

    model: Optional[str] = None
    """Model used (e.g., 'gpt-4')."""

    total_tokens: Optional[int] = None
    """Token usage."""

    latency_ms: Optional[int] = None
    """Latency in milliseconds."""

    parent_run_id: Optional[str] = None
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

    inputs: Dict[str, Any] = Field(default_factory=dict)
    """Full inputs (prompts, tool arguments, etc)."""

    outputs: Optional[Dict[str, Any]] = None
    """Full outputs if successful (structured output, tool results)."""

    error: Optional[str] = None
    """Full error message and traceback if failed."""

    metadata: RunMetadata
    """Additional metadata."""


class ToolCall(BaseModel):
    """Tool call made by assistant."""

    name: str
    """Tool name."""

    arguments: Dict[str, Any]
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

    tool_calls: Optional[List[ToolCall]] = None
    """Tool calls made by assistant."""

    tool_results: Optional[List[ToolResult]] = None
    """Tool results returned."""


class RunMessages(BaseModel):
    """Full conversation messages for a run (Level 2).

    Expensive - ~5,000+ tokens. Use sparingly.
    """

    run_id: str
    """Run ID."""

    messages: List[Message]
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

    original_data: Dict[str, Any]
    """Original extracted product data."""

    edited_data: Optional[Dict[str, Any]] = None
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

    hitl_decisions: List[HITLDecision] = Field(default_factory=list)
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

    traces: List[WorkflowTrace]
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

class TestExecution(BaseModel):
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


class TestHistory(BaseModel):
    """History of test executions."""

    tests: List[TestExecution]
    """List of test executions, newest first."""


# Enable forward references for recursive RunNode model
RunNode.model_rebuild()
