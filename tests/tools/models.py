"""Pydantic models for autonomous testing framework tools.

Return types for:
- PM interaction tool (chat_with_pm)
- Trace analysis tools (get_trace_overview, get_run_details, etc.)
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# PM Interaction Models
# ============================================================================


class PMChatResult(BaseModel):
    """Result of sending a message to PM via chat_with_pm().

    This is the primary interface for Claude Code to interact with the PM
    and evaluate its behavior in real-time.
    """

    thread_id: str
    """Thread ID for conversation continuity and trace lookup."""

    pm_response: str
    """The PM's response text."""

    is_approval_request: bool = False
    """Whether PM is requesting user approval (HITL interrupt)."""

    approval_products: list[dict[str, Any]] | None = None
    """Products awaiting approval if is_approval_request is True."""

    conversation_turn: int
    """Which turn in the conversation (1-indexed)."""

    response_time_ms: int
    """PM response time in milliseconds."""

    trace_id: str | None = None
    """LangSmith trace ID if available (may require brief delay to populate)."""

    trace_url: str | None = None
    """LangSmith trace URL for browser viewing."""

    scenario_id: str | None = None
    """Scenario ID for evaluation tracking (passed to LangSmith metadata)."""

    workflow_complete: bool = False
    """Whether the workflow has completed (PM sent completion message)."""

    error: str | None = None
    """Error message if something went wrong."""

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


class ThreadTrace(BaseModel):
    """Single trace in a conversation thread."""

    trace_id: str
    """LangSmith trace ID."""

    turn: int
    """Conversation turn (1-indexed)."""

    timestamp: datetime
    """When this trace started."""

    duration_ms: int
    """Trace duration in milliseconds."""

    user_message: str | None = None
    """User message that triggered this trace (from workflow_outcomes)."""

    agent_message_preview: str | None = None
    """Preview of agent's final message in this trace."""

    agent_that_responded: str | None = None
    """Which agent produced the final message (PM or specialist)."""


class ThreadTraces(BaseModel):
    """All traces in a conversation thread for multi-turn evaluation.

    Use this to evaluate scenarios that span multiple conversation turns.
    """

    thread_id: str
    """Thread ID linking all traces."""

    traces: list[ThreadTrace]
    """Traces in chronological order."""

    total_traces: int
    """Number of traces in thread."""

    total_duration_ms: int
    """Total duration across all traces."""


class MediaPath(BaseModel):
    """Media file path extracted from download_whatsapp_media tool output.

    Used to reconstruct scenarios from production traces.
    """

    storage_path: str
    """Local path where media was downloaded (e.g., 'inbox/20260107_134205_123.jpg')."""

    mime_type: str | None = None
    """MIME type (e.g., 'image/jpeg')."""

    media_id: str | None = None
    """Original WhatsApp media ID from tool input."""


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


# ============================================================================
# Evaluation Data Extraction Models (for e2e-testing skill)
# ============================================================================


class SequencedToolCall(BaseModel):
    """Single tool call with sequence and agent attribution.

    Used by get_tool_call_sequence() for evaluating:
    - Protocol loading order
    - Delegation sequence
    - Wave execution patterns
    """

    sequence: int
    """Order in which tool was called (1-indexed)."""

    agent: str
    """Agent that made the tool call (e.g., 'PM', 'visual_analyst')."""

    tool_name: str
    """Name of the tool called."""

    tool_args: dict[str, Any] = Field(default_factory=dict)
    """Arguments passed to tool (raw, may be string repr)."""

    parsed_args: dict[str, Any] = Field(default_factory=dict)
    """Properly parsed arguments dict (use this for evaluation)."""

    tool_output: Any = None
    """Output/result from the tool call."""

    timestamp: datetime | None = None
    """When tool was called."""

    duration_ms: int | None = None
    """How long tool took to execute."""

    run_id: str
    """Run ID for drilling down."""

    parent_agent: str | None = None
    """Parent agent that delegated to this agent."""

    status: str = "success"
    """Run status: 'success' | 'error' | 'pending'."""

    error: str | None = None
    """Error message if tool failed."""


class ToolCallSequence(BaseModel):
    """Ordered sequence of all tool calls in a trace.

    Primary model for evaluating:
    - Did PM load protocol first?
    - Did PM delegate in correct order?
    - Did PM read files at approval gate?
    """

    trace_id: str
    """LangSmith trace ID."""

    total_tool_calls: int
    """Total number of tool calls."""

    tool_calls: list[SequencedToolCall]
    """Ordered list of all tool calls."""

    # Quick lookup helpers
    first_tool_call: SequencedToolCall | None = None
    """First tool call in sequence (for protocol check)."""

    delegation_calls: list[SequencedToolCall] = Field(default_factory=list)
    """All delegate_to_agent calls (for wave analysis)."""

    file_read_calls: list[SequencedToolCall] = Field(default_factory=list)
    """All read_file calls (for approval gate check)."""

    file_write_calls: list[SequencedToolCall] = Field(default_factory=list)
    """All write_file calls (for output tracking)."""


class AgentDelegation(BaseModel):
    """Single delegation from one agent to another."""

    from_agent: str
    """Agent that delegated."""

    to_agent: str
    """Agent that was delegated to."""

    context_passed: list[str] = Field(default_factory=list)
    """File paths or context keys passed to delegated agent."""

    timestamp: datetime | None = None
    """When delegation occurred."""

    wave: int | None = None
    """Wave number if part of wave execution (1, 2, etc)."""

    parallel_with: list[str] = Field(default_factory=list)
    """Other agents delegated in parallel (same wave)."""


class DelegationGraph(BaseModel):
    """Hierarchical graph of agent delegations.

    Primary model for evaluating:
    - Wave execution (V first, then P || C)
    - Context handoff (file paths passed)
    - Parallel vs serial execution
    """

    trace_id: str
    """LangSmith trace ID."""

    root_agent: str
    """Root agent (usually 'PM')."""

    delegations: list[AgentDelegation]
    """All delegations in order."""

    # Wave analysis
    waves: dict[int, list[str]] = Field(default_factory=dict)
    """Agents grouped by wave: {1: ['visual_analyst'], 2: ['product_analyst', 'catalog_analyst']}."""

    # Quick lookups
    agents_involved: list[str] = Field(default_factory=list)
    """All agents that participated."""

    delegation_order: list[str] = Field(default_factory=list)
    """Order in which agents were delegated to."""


class FileOperation(BaseModel):
    """Single file read or write operation."""

    operation: str
    """Operation type: 'read' | 'write'."""

    agent: str
    """Agent that performed operation."""

    file_path: str
    """Path to file."""

    timestamp: datetime | None = None
    """When operation occurred."""

    sequence: int
    """Order in trace."""

    content_preview: str | None = None
    """First 200 chars of content (for writes)."""


class FileIOTrace(BaseModel):
    """All file operations in a trace.

    Primary model for evaluating:
    - Did analysts write analysis files?
    - Did PM read analysis files at approval gate?
    - Was file communication correct?
    """

    trace_id: str
    """LangSmith trace ID."""

    operations: list[FileOperation]
    """All file operations in order."""

    # Grouped by type
    writes: list[FileOperation] = Field(default_factory=list)
    """All write operations."""

    reads: list[FileOperation] = Field(default_factory=list)
    """All read operations."""

    # Analysis-specific
    analysis_files_written: list[str] = Field(default_factory=list)
    """Analysis files written by analysts (visual_analysis_*.md, etc)."""

    analysis_files_read_by_pm: list[str] = Field(default_factory=list)
    """Analysis files read by PM at approval gate."""

    protocol_files_read: list[str] = Field(default_factory=list)
    """Protocol files read by any agent."""


class ProtocolLoad(BaseModel):
    """Single protocol load by an agent."""

    agent: str
    """Agent that loaded protocol."""

    protocol_path: str
    """Path to protocol file."""

    protocol_name: str | None = None
    """Extracted protocol name (e.g., 'discovery_mindset')."""

    timestamp: datetime | None = None
    """When protocol was loaded."""

    sequence: int
    """Order in trace (was this FIRST action?)."""

    is_first_action: bool = False
    """Whether this was the agent's first action."""


class ProtocolLoadTrace(BaseModel):
    """All protocol loads in a trace.

    Primary model for evaluating:
    - Did PM load protocol as FIRST action?
    - Did each agent load their correct protocol?
    """

    trace_id: str
    """LangSmith trace ID."""

    protocol_loads: list[ProtocolLoad]
    """All protocol loads."""

    # Quick lookups
    pm_first_action_was_protocol: bool = False
    """Whether PM's first action was loading a protocol."""

    pm_protocol: str | None = None
    """Protocol loaded by PM."""

    agent_protocols: dict[str, str] = Field(default_factory=dict)
    """Map of agent -> protocol loaded."""


class AgentFinalMessage(BaseModel):
    """Final message from an agent to user.

    Used for evaluating:
    - Did PM present open-ended question at approval gate?
    - Was message format correct?
    - What model generated this response?
    """

    agent: str
    """Agent that sent message."""

    message: str
    """The message content (full)."""

    message_preview: str = ""
    """First 200 chars for quick glance."""

    timestamp: datetime | None = None
    """When message was sent."""

    run_id: str | None = None
    """LLM run ID for drilling down."""

    model_name: str | None = None
    """Model that generated the message (e.g., 'gpt-4', 'claude-3')."""

    token_count: int | None = None
    """Total tokens used for this LLM call."""

    # Content analysis flags
    has_numbered_options: bool = False
    """Whether message contains numbered options (anti-pattern)."""

    has_open_question: bool = False
    """Whether message ends with open-ended question."""

    is_approval_request: bool = False
    """Whether this is a HITL approval request."""

    mentions_error: bool = False
    """Whether message mentions error/failure."""

    mentions_success: bool = False
    """Whether message mentions success/completion."""

    has_product_details: bool = False
    """Whether message contains product-related details."""


# ============================================================================
# Evaluation Feedback Models (for LangSmith storage)
# ============================================================================


class EvaluationCriterion(BaseModel):
    """Single evaluation criterion result."""

    criterion: str
    """Criterion name: 'protocol_loading', 'wave_execution', etc."""

    passed: bool
    """Whether criterion passed."""

    score: float = Field(ge=0.0, le=1.0)
    """Score from 0.0 to 1.0."""

    reasoning: str
    """Why this score was given."""

    evidence: dict[str, Any] = Field(default_factory=dict)
    """Supporting evidence from trace."""


class EvaluationResult(BaseModel):
    """Complete evaluation result for a scenario run.

    Stored in LangSmith feedback for historical tracking and pattern detection.
    """

    scenario_id: str
    """Scenario that was evaluated."""

    trace_id: str
    """LangSmith trace ID."""

    thread_id: str
    """Thread ID for conversation."""

    # Overall result
    status: str
    """Overall status: 'PASS' | 'PARTIAL' | 'FAIL' | 'ERROR'."""

    overall_score: float = Field(ge=0.0, le=1.0)
    """Aggregate score."""

    # Per-criterion results
    criteria_results: list[EvaluationCriterion]
    """Results for each evaluation criterion."""

    # Summary
    passed_criteria: int
    """Number of criteria that passed."""

    failed_criteria: int
    """Number of criteria that failed."""

    failure_reasons: list[str] = Field(default_factory=list)
    """Summary of why criteria failed."""

    # Metadata
    evaluated_at: datetime
    """When evaluation was performed."""

    evaluator: str = "claude"
    """Who/what performed evaluation."""

    notes: str | None = None
    """Additional notes from evaluator."""


# ============================================================================
# Historical Analysis Models (for continuous improvement)
# ============================================================================


class ScenarioRunSummary(BaseModel):
    """Summary of a single scenario run."""

    trace_id: str
    """LangSmith trace ID."""

    run_date: datetime
    """When scenario was run."""

    status: str
    """Result: 'PASS' | 'PARTIAL' | 'FAIL' | 'ERROR'."""

    score: float
    """Overall score."""

    failed_criteria: list[str] = Field(default_factory=list)
    """Which criteria failed."""

    duration_ms: int | None = None
    """Execution time."""

    cost: float | None = None
    """Execution cost."""


class ScenarioHistory(BaseModel):
    """Historical runs of a scenario for pattern detection.

    Used for:
    - Identifying common failure modes
    - Detecting regressions
    - Tracking improvement over time
    """

    scenario_id: str
    """Scenario being analyzed."""

    total_runs: int
    """Total number of runs in history."""

    date_range_days: int
    """How many days of history."""

    # Aggregate stats
    pass_rate: float
    """Percentage of runs that passed."""

    avg_score: float
    """Average score across runs."""

    # Failure analysis
    failure_counts: dict[str, int] = Field(default_factory=dict)
    """Count of failures by criterion: {'wave_execution': 10, 'protocol_loading': 3}."""

    most_common_failure: str | None = None
    """Most frequently failed criterion."""

    # Trend
    recent_trend: str | None = None
    """'improving' | 'degrading' | 'stable'."""

    # Individual runs
    runs: list[ScenarioRunSummary] = Field(default_factory=list)
    """Individual run summaries, newest first."""


class TraceBaseline(BaseModel):
    """Known-good reference trace for comparison.

    Used for:
    - Regression detection
    - Behavior comparison
    - Evolving expected behavior
    """

    scenario_id: str
    """Scenario this baseline is for."""

    trace_id: str
    """Reference trace ID."""

    created_at: datetime
    """When baseline was created."""

    # Expected patterns
    expected_tool_sequence: list[str] = Field(default_factory=list)
    """Expected tool call sequence (tool names only)."""

    expected_delegation_order: list[str] = Field(default_factory=list)
    """Expected agent delegation order."""

    expected_waves: dict[int, list[str]] = Field(default_factory=dict)
    """Expected wave structure."""

    expected_protocol_loads: dict[str, str] = Field(default_factory=dict)
    """Expected agent -> protocol mapping."""

    # Metrics for comparison
    baseline_duration_ms: int | None = None
    """Reference duration."""

    baseline_cost: float | None = None
    """Reference cost."""

    baseline_tool_count: int | None = None
    """Reference tool call count."""

    # Metadata
    notes: str | None = None
    """Why this trace was chosen as baseline."""

    superseded_by: str | None = None
    """If baseline was updated, new baseline trace_id."""


# Enable forward references for recursive models
RunNode.model_rebuild()
LLMCallNode.model_rebuild()
