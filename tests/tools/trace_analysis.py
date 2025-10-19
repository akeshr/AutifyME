"""Trace analysis tools for hierarchical LangSmith trace inspection.

Implements 3-level hierarchical analysis for token efficiency:
- Level 0: get_trace_overview() - Metadata only (~500 tokens)
- Level 1: get_run_details() - Specific run with inputs/outputs (~1,500 tokens)
- Level 2: get_run_messages() - Full conversation (~5K+ tokens, rare)

Token savings: 25x vs naive full dump approach.
"""
from typing import Dict, List
from langsmith import Client
from datetime import datetime
from dotenv import load_dotenv

from .models import (
    TraceOverview,
    RunNode,
    RunDetails,
    RunMetadata,
    RunMessages,
    Message,
    ToolCall,
    ToolResult,
    WorkflowStory,
    WorkflowTrace,
    HITLDecision,
)


# Initialize LangSmith client
_client = None


def _get_client() -> Client:
    """Get or create LangSmith client."""
    global _client
    if _client is None:
        # Load environment variables from .env
        load_dotenv()
        _client = Client()
    return _client


def get_trace_overview(trace_id: str) -> TraceOverview:
    """Get hierarchical trace structure with metadata only (Level 0).

    This is the starting point for all trace analysis. Fetches ONLY metadata
    (no inputs/outputs) to minimize token usage. Returns full run tree for
    identifying failures, slow runs, and expensive runs.

    Token cost: ~500 tokens (vs 50K+ for full dump)

    Args:
        trace_id: LangSmith trace ID from ExecutionResult

    Returns:
        TraceOverview with hierarchical run tree and summary statistics

    Example:
        >>> overview = get_trace_overview(trace_id)
        >>> print(f"Total runs: {overview.total_runs}")
        >>> # Find failures
        >>> def find_failures(node):
        ...     if node.status == "error":
        ...         print(f"Failed: {node.name} - {node.error}")
        ...     for child in node.children:
        ...         find_failures(child)
        >>> find_failures(overview.run_tree[0])
    """
    client = _get_client()

    # Fetch all runs for this trace with select parameter for metadata only
    # Exclude inputs/outputs to save massive tokens
    selected_fields = [
        "id",
        "name",
        "run_type",
        "status",
        "start_time",
        "end_time",
        "error",
        "parent_run_id",
        "trace_id",
        "total_tokens",
        "total_cost",
    ]

    runs = list(client.list_runs(trace_id=trace_id, select=selected_fields))

    if not runs:
        # Return empty overview
        return TraceOverview(
            trace_id=trace_id,
            total_runs=0,
            total_cost=0.0,
            total_latency_ms=0,
            run_tree=[],
        )

    # Build hierarchy and collect stats
    runs_by_id = {str(run.id): run for run in runs}
    root_runs = []
    total_cost = 0.0
    total_latency_ms = 0

    def build_node(run) -> RunNode:
        """Recursively build RunNode tree."""
        nonlocal total_cost, total_latency_ms

        # Calculate duration
        duration_ms = 0
        if run.end_time and run.start_time:
            duration_ms = int((run.end_time - run.start_time).total_seconds() * 1000)
            total_latency_ms += duration_ms

        # Accumulate cost
        if run.total_cost:
            total_cost += float(run.total_cost)

        # Build node
        node = RunNode(
            run_id=str(run.id),
            name=run.name,
            run_type=run.run_type,
            status=run.status,
            start_time=run.start_time,
            end_time=run.end_time,
            duration_ms=duration_ms,
            error=run.error,
            children=[],
        )

        # Find and add children
        for other_run in runs:
            if other_run.parent_run_id and str(other_run.parent_run_id) == str(run.id):
                child_node = build_node(other_run)
                node.children.append(child_node)

        return node

    # Build trees from root runs (those without parent)
    for run in runs:
        if not run.parent_run_id:
            root_node = build_node(run)
            root_runs.append(root_node)

    return TraceOverview(
        trace_id=trace_id,
        total_runs=len(runs),
        total_cost=round(total_cost, 4),
        total_latency_ms=total_latency_ms,
        run_tree=root_runs,
    )


def get_run_details(run_id: str) -> RunDetails:
    """Get detailed information for a specific run (Level 1).

    Fetches inputs, outputs, and error details for a single run.
    Use this after get_trace_overview() identifies a failure or
    interesting run to investigate.

    Token cost: ~1,500 tokens per run

    Args:
        run_id: Run ID from TraceOverview (e.g., from failed_runs)

    Returns:
        RunDetails with full inputs, outputs, error, and metadata

    Example:
        >>> # After finding failures in overview
        >>> overview = get_trace_overview(trace_id)
        >>> for node in overview.run_tree:
        ...     if node.status == "error":
        ...         details = get_run_details(node.run_id)
        ...         print(f"Error: {details.error}")
        ...         print(f"Inputs: {details.inputs}")
    """
    client = _get_client()

    # Fetch full run with inputs/outputs
    run = client.read_run(run_id)

    # Build metadata
    metadata = RunMetadata(
        model=run.extra.get("model") if run.extra else None,
        total_tokens=run.total_tokens,
        latency_ms=int((run.end_time - run.start_time).total_seconds() * 1000)
        if run.end_time and run.start_time
        else None,
        parent_run_id=str(run.parent_run_id) if run.parent_run_id else None,
    )

    return RunDetails(
        run_id=str(run.id),
        name=run.name,
        run_type=run.run_type,
        inputs=run.inputs if run.inputs else {},
        outputs=run.outputs if run.outputs else None,
        error=run.error,
        metadata=metadata,
    )


def get_run_messages(run_id: str) -> RunMessages:
    """Get full conversation messages for a run (Level 2).

    Fetches complete message history for an LLM run. This is expensive
    in tokens and should only be used when get_run_details() doesn't
    provide enough information to understand the failure.

    Token cost: ~5,000+ tokens (varies with conversation length)

    Usage criteria - Only use when:
    - Root cause unclear from Level 0 + Level 1
    - Need to see exact prompt/response
    - Debugging complex multi-step reasoning
    - Investigating context leakage

    Args:
        run_id: Run ID (should be an LLM run type)

    Returns:
        RunMessages with full conversation history

    Example:
        >>> # Only after Level 1 doesn't explain the issue
        >>> details = get_run_details(specialist_run_id)
        >>> if "unclear why agent made wrong decision":
        ...     messages = get_run_messages(specialist_run_id)
        ...     for msg in messages.messages:
        ...         print(f"[{msg.role}]: {msg.content[:100]}...")
    """
    client = _get_client()

    # Fetch full run
    run = client.read_run(run_id)

    # Extract messages from inputs
    messages_list = []

    # For LLM runs, messages are typically in inputs
    if run.inputs and "messages" in run.inputs:
        raw_messages = run.inputs["messages"]

        for raw_msg in raw_messages:
            # Handle different message formats
            if isinstance(raw_msg, dict):
                role = raw_msg.get("role", raw_msg.get("type", "unknown"))
                content = raw_msg.get("content", "")

                # Extract tool calls if present
                tool_calls = None
                if "tool_calls" in raw_msg and raw_msg["tool_calls"]:
                    tool_calls = [
                        ToolCall(
                            name=tc.get("function", {}).get("name", "unknown"),
                            arguments=tc.get("function", {}).get("arguments", {}),
                        )
                        for tc in raw_msg["tool_calls"]
                    ]

                messages_list.append(
                    Message(role=role, content=str(content), tool_calls=tool_calls)
                )

    # Also check outputs for assistant response
    if run.outputs:
        if isinstance(run.outputs, dict):
            if "content" in run.outputs:
                messages_list.append(
                    Message(
                        role="assistant",
                        content=str(run.outputs["content"]),
                    )
                )

    return RunMessages(run_id=str(run.id), messages=messages_list)


def get_workflow_story(trace_ids: List[str]) -> WorkflowStory:
    """Get complete HITL workflow narrative across multiple traces.

    HITL workflows span multiple traces (initial → interrupt → resume).
    This function correlates all traces to show the complete story:
    - Initial extraction
    - User HITL decisions (approved/edited/rejected)
    - Final outcomes

    IMPORTANT: Use Supabase MCP to get trace_ids first:
    ```sql
    SELECT trace_id, created_at
    FROM workflow_outcomes
    WHERE thread_id = 'your_thread_id'
    ORDER BY created_at ASC
    ```

    Then pass all trace_ids to this function for analysis.

    Token cost: ~500 tokens per trace (uses get_trace_overview internally)

    Args:
        trace_ids: List of trace IDs in chronological order

    Returns:
        WorkflowStory with complete multi-trace narrative

    Example:
        >>> # Step 1: Get trace_ids from Supabase MCP
        >>> # mcp__supabase__execute_sql(
        >>> #   query="SELECT trace_id FROM workflow_outcomes
        >>> #          WHERE thread_id = '...' ORDER BY created_at"
        >>> # )
        >>>
        >>> # Step 2: Analyze all traces
        >>> story = get_workflow_story(['trace1', 'trace2', 'trace3'])
        >>> print(f"Products extracted: {story.products_extracted}")
        >>> print(f"Products saved: {story.products_saved}")
        >>> print(f"Products rejected: {story.products_rejected}")
    """
    client = _get_client()

    if not trace_ids:
        raise ValueError("trace_ids cannot be empty")

    # Analyze each trace
    workflow_traces = []
    thread_id = None
    total_cost = 0.0
    total_latency_ms = 0

    for idx, trace_id in enumerate(trace_ids, 1):
        # Get trace overview
        overview = get_trace_overview(trace_id)

        # Extract thread_id from first trace
        if thread_id is None:
            # Get thread_id from trace metadata
            run = client.read_run(overview.run_tree[0].run_id)
            thread_id = run.metadata.get("thread_id", "unknown")

        # Accumulate costs
        total_cost += overview.total_cost
        total_latency_ms += overview.total_latency_ms

        # Detect HITL interrupt
        is_hitl_interrupt = _detect_hitl_interrupt(overview)

        # Extract HITL decisions from next trace if this was an interrupt
        hitl_decisions = []
        if is_hitl_interrupt and idx < len(trace_ids):
            # Decisions are in the NEXT trace's inputs
            next_trace_id = trace_ids[idx]
            hitl_decisions = _extract_hitl_decisions(next_trace_id)

        workflow_traces.append(
            WorkflowTrace(
                trace_id=trace_id,
                trace_url=f"https://smith.langchain.com/public/{trace_id}/r",
                sequence=idx,
                overview=overview,
                is_hitl_interrupt=is_hitl_interrupt,
                hitl_decisions=hitl_decisions,
            )
        )

    # Count products
    products_extracted = _count_extracted_products(workflow_traces[0].overview)
    products_saved = _count_saved_products(workflow_traces[-1].overview)

    # Count edited/rejected from HITL decisions
    products_edited = 0
    products_rejected = 0
    for trace in workflow_traces:
        for decision in trace.hitl_decisions:
            if decision.action == "edited":
                products_edited += 1
            elif decision.action == "rejected":
                products_rejected += 1

    return WorkflowStory(
        thread_id=thread_id or "unknown",
        total_traces=len(trace_ids),
        traces=workflow_traces,
        products_extracted=products_extracted,
        products_saved=products_saved,
        products_rejected=products_rejected,
        products_edited=products_edited,
        total_cost=round(total_cost, 4),
        total_latency_ms=total_latency_ms,
    )


def _detect_hitl_interrupt(overview: TraceOverview) -> bool:
    """Detect if trace ended with HITL interrupt."""

    def has_interrupt(node: RunNode) -> bool:
        # Check if node is HumanInTheLoopMiddleware
        if "HumanInTheLoop" in node.name or "interrupt" in node.name.lower():
            return True
        # Check children recursively
        for child in node.children:
            if has_interrupt(child):
                return True
        return False

    for root in overview.run_tree:
        if has_interrupt(root):
            return True
    return False


def _extract_hitl_decisions(trace_id: str) -> List[HITLDecision]:
    """Extract user HITL decisions from resume trace inputs."""
    client = _get_client()

    # Get first run of trace (should have HITL response in inputs)
    runs = list(client.list_runs(trace_id=trace_id, limit=1))
    if not runs:
        return []

    run = client.read_run(runs[0].id)
    inputs = run.inputs

    # Look for approval decisions in inputs
    # This is simplified - real implementation would parse approval_analyzer output
    decisions = []

    # Check if inputs contain approval data structure
    if isinstance(inputs, dict) and "messages" in inputs:
        messages = inputs["messages"]
        for msg in messages:
            if isinstance(msg, dict) and msg.get("type") == "human":
                content = msg.get("content", "")
                # Parse approval responses (simplified)
                # Real implementation would match actual approval_analyzer format
                if "approved" in content.lower():
                    # Extract product data from content
                    # This is a placeholder - actual parsing would be more sophisticated
                    decisions.append(
                        HITLDecision(
                            product_index=len(decisions),
                            action="approved",
                            original_data={},
                        )
                    )

    return decisions


def _count_extracted_products(overview: TraceOverview) -> int:
    """Count products extracted in initial trace."""
    count = 0

    def count_extractions(node: RunNode):
        nonlocal count
        # Look for extraction specialist tool calls
        if node.run_type == "tool" and "extract" in node.name.lower():
            count += 1
        for child in node.children:
            count_extractions(child)

    for root in overview.run_tree:
        count_extractions(root)

    return count


def _count_saved_products(overview: TraceOverview) -> int:
    """Count products saved in final trace."""
    count = 0

    def count_saves(node: RunNode):
        nonlocal count
        if node.run_type == "tool" and node.name == "save_product":
            count += 1
        for child in node.children:
            count_saves(child)

    for root in overview.run_tree:
        count_saves(root)

    return count
