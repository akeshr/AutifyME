"""Trace analysis tools for hierarchical LangSmith trace inspection.

Implements 3-level hierarchical analysis for token efficiency:
- Level 0: get_trace_overview() - Metadata only (~500 tokens)
- Level 1: get_run_details() - Specific run with inputs/outputs (~1,500 tokens)
- Level 2: get_run_messages() - Full conversation (~5K+ tokens, rare)

Token savings: 25x vs naive full dump approach.
"""
import re
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv
from langsmith import Client

from .models import (
    AgentDelegation,
    AgentFinalMessage,
    DelegationGraph,
    EvaluationCriterion,
    EvaluationResult,
    FileIOTrace,
    FileOperation,
    HITLDecision,
    LLMCallNode,
    LLMTraceTree,
    Message,
    ProtocolLoad,
    ProtocolLoadTrace,
    RunDetails,
    RunMessages,
    RunMetadata,
    RunNode,
    ScenarioHistory,
    ScenarioRunSummary,
    SequencedToolCall,
    ToolCall,
    ToolCallSequence,
    TraceBaseline,
    TraceOverview,
    WorkflowStory,
    WorkflowTrace,
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
    {str(run.id): run for run in runs}
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
    if run.outputs and isinstance(run.outputs, dict) and "content" in run.outputs:
        messages_list.append(
            Message(
                role="assistant",
                content=str(run.outputs["content"]),
            )
        )

    return RunMessages(run_id=str(run.id), messages=messages_list)


def get_workflow_story(trace_ids: list[str]) -> WorkflowStory:
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
        return any(has_interrupt(child) for child in node.children)

    return any(has_interrupt(root) for root in overview.run_tree)


def _extract_hitl_decisions(trace_id: str) -> list[HITLDecision]:
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


# ============================================================================
# LLM Trace Extraction (for prompt analysis)
# ============================================================================

def _classify_hierarchy_level(agent_name: str) -> str:
    """Classify agent hierarchy level from name.

    Args:
        agent_name: Agent/run name (e.g., "PM", "CatalogingDept", "ImageAnalysisSpecialist")

    Returns:
        Hierarchy level: "orchestrator" | "department" | "specialist" | "unknown"
    """
    name_lower = agent_name.lower()

    # Orchestrators (PM, project manager, LangGraph root)
    if (name_lower == "pm" or
        "project" in name_lower and "manager" in name_lower or
        "langgraph" in name_lower):
        return "orchestrator"

    # Departments (ends with Dept or Department)
    if "dept" in name_lower or "department" in name_lower:
        return "department"

    # Specialists (ends with Specialist)
    if "specialist" in name_lower:
        return "specialist"

    return "unknown"


def _extract_system_prompt(messages: list) -> str:
    """Extract system prompt from messages list.

    Args:
        messages: LLM input messages (can be nested list or flat list)

    Returns:
        System prompt content, or empty string if not found
    """
    if not messages:
        return ""

    # Flatten if nested (LangSmith sometimes wraps in extra list)
    if messages and isinstance(messages[0], list):
        messages = messages[0]

    for msg in messages:
        if isinstance(msg, dict):
            # LangChain serialized format: check id or type
            msg_id = msg.get("id", [])
            if isinstance(msg_id, list) and "SystemMessage" in msg_id:
                # Extract content from kwargs
                kwargs = msg.get("kwargs", {})
                content = kwargs.get("content", "")
                return content if isinstance(content, str) else ""

            # Standard format: check for system role
            msg_type = msg.get("type") or msg.get("role")
            if msg_type == "system":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    # Handle multimodal content
                    text_parts = [
                        part.get("text", "") for part in content
                        if isinstance(part, dict) and part.get("type") == "text"
                    ]
                    return "\n".join(text_parts)

    return ""


def get_llm_trace_tree(trace_id: str) -> LLMTraceTree:
    """Extract hierarchical tree of LLM calls with prompts and outputs.

    This function filters a trace to show ONLY LLM invocations (excludes chains
    and tools) with full prompt content and outputs. Designed for prompt analysis
    and optimization by the prompt-fixer agent.

    Unlike get_trace_overview() which shows ALL runs with metadata only, this
    provides FILTERED LLM-only runs with FULL prompt content.

    Token cost: ~2-5k tokens per trace (vs 50k+ for full dump)

    Args:
        trace_id: LangSmith trace ID from ExecutionResult

    Returns:
        LLMTraceTree with hierarchical LLM call structure and full prompts

    Example:
        >>> tree = get_llm_trace_tree(trace_id)
        >>> for llm_call in tree.llm_tree:
        ...     print(f"{llm_call.agent_name} ({llm_call.hierarchy_level})")
        ...     print(f"System: {llm_call.system_prompt[:100]}...")
        ...     print(f"Output: {llm_call.assistant_output}")
    """
    client = _get_client()

    # Fetch all runs with inputs/outputs (need full data for prompts)
    runs = list(client.list_runs(trace_id=trace_id))

    if not runs:
        # Return empty tree
        return LLMTraceTree(
            trace_id=trace_id,
            trace_url=f"https://smith.langchain.com/public/unknown/r/{trace_id}",
            total_llm_calls=0,
            total_tokens=0,
            total_cost=0.0,
            llm_tree=[],
        )

    # Build lookup and filter to LLM runs only
    runs_by_id = {str(run.id): run for run in runs}
    llm_runs = [run for run in runs if run.run_type == "llm"]

    if not llm_runs:
        # No LLM calls in trace
        return LLMTraceTree(
            trace_id=trace_id,
            trace_url=f"https://smith.langchain.com/public/{runs[0].session_id if runs else 'unknown'}/r/{trace_id}",
            total_llm_calls=0,
            total_tokens=0,
            total_cost=0.0,
            llm_tree=[],
        )

    # Accumulate stats
    total_tokens = 0
    total_cost = 0.0

    def build_llm_node(run) -> LLMCallNode:
        """Recursively build LLMCallNode tree."""
        nonlocal total_tokens, total_cost

        # Calculate latency
        latency_ms = None
        if run.end_time and run.start_time:
            latency_ms = int((run.end_time - run.start_time).total_seconds() * 1000)

        # Accumulate tokens and cost
        if run.total_tokens:
            total_tokens += run.total_tokens
        if run.total_cost:
            total_cost += float(run.total_cost)

        # Extract model from extra metadata
        model = None
        if run.extra:
            model = run.extra.get("invocation_params", {}).get("model")
            if not model:
                model = run.extra.get("model")

        # Extract system prompt and user messages from inputs
        system_prompt = ""
        user_messages = []

        if run.inputs and "messages" in run.inputs:
            raw_messages = run.inputs["messages"]
            if isinstance(raw_messages, list):
                # Flatten if nested
                if raw_messages and isinstance(raw_messages[0], list):
                    raw_messages = raw_messages[0]

                system_prompt = _extract_system_prompt(raw_messages)

                # Extract user/human/ai messages (exclude system)
                for msg in raw_messages:
                    if isinstance(msg, dict):
                        # LangChain serialized format
                        msg_id = msg.get("id", [])
                        if isinstance(msg_id, list):
                            # Check if it's NOT a SystemMessage
                            if "SystemMessage" not in msg_id:
                                # Extract simplified version with content
                                kwargs = msg.get("kwargs", {})
                                msg_type_str = msg_id[-1] if msg_id else "unknown"
                                user_messages.append({
                                    "type": msg_type_str,
                                    "content": kwargs.get("content", ""),
                                })
                        else:
                            # Standard format: check for non-system messages
                            msg_type = msg.get("type") or msg.get("role")
                            if msg_type and msg_type != "system":
                                user_messages.append(msg)

        # Extract assistant output from outputs
        assistant_output = None
        if run.outputs:
            assistant_output = run.outputs

        # Find meaningful agent name by traversing up parent chain
        # Skip generic names like "model", "ChatOpenAI", "tools"
        agent_name = run.name
        current_run = run

        # Traverse up to find meaningful agent name
        generic_names = {"model", "ChatOpenAI", "tools", "model_to_tools"}
        while current_run.parent_run_id and agent_name in generic_names:
            parent_run = runs_by_id.get(str(current_run.parent_run_id))
            if parent_run:
                if parent_run.name not in generic_names:
                    agent_name = parent_run.name
                    break
                current_run = parent_run
            else:
                break

        # Find parent agent name (for context)
        parent_agent = None
        if run.parent_run_id:
            parent_run = runs_by_id.get(str(run.parent_run_id))
            if parent_run:
                # Traverse up to find meaningful parent agent name
                parent_agent = parent_run.name
                temp_run = parent_run
                while temp_run.parent_run_id and parent_agent in generic_names:
                    temp_parent = runs_by_id.get(str(temp_run.parent_run_id))
                    if temp_parent:
                        if temp_parent.name not in generic_names:
                            parent_agent = temp_parent.name
                            break
                        temp_run = temp_parent
                    else:
                        break

        # Classify hierarchy level based on resolved agent name
        hierarchy_level = _classify_hierarchy_level(agent_name)

        # Build node
        node = LLMCallNode(
            run_id=str(run.id),
            agent_name=agent_name,
            hierarchy_level=hierarchy_level,
            system_prompt=system_prompt,
            user_messages=user_messages,
            assistant_output=assistant_output,
            model=model,
            total_tokens=run.total_tokens,
            latency_ms=latency_ms,
            status=run.status,
            error=run.error,
            parent_agent=parent_agent,
            children=[],
        )

        # Find and add child LLM runs (only LLM children, skip chains/tools)
        for other_run in llm_runs:
            if other_run.parent_run_id and str(other_run.parent_run_id) == str(run.id):
                child_node = build_llm_node(other_run)
                node.children.append(child_node)

        return node

    # Build tree from root LLM runs (those without LLM parents)
    root_llm_nodes = []
    for run in llm_runs:
        # Check if parent is also an LLM run
        is_root = True
        if run.parent_run_id:
            parent_run = runs_by_id.get(str(run.parent_run_id))
            if parent_run and parent_run.run_type == "llm":
                is_root = False

        if is_root:
            root_node = build_llm_node(run)
            root_llm_nodes.append(root_node)

    # Get trace URL from first run
    trace_url = f"https://smith.langchain.com/public/{runs[0].session_id if runs else 'unknown'}/r/{trace_id}"

    return LLMTraceTree(
        trace_id=trace_id,
        trace_url=trace_url,
        total_llm_calls=len(llm_runs),
        total_tokens=total_tokens,
        total_cost=round(total_cost, 4),
        llm_tree=root_llm_nodes,
    )


# ============================================================================
# Evaluation Data Extraction Functions (for e2e-testing skill)
# ============================================================================

# Tool name constants (actual tool names from LangSmith traces)
TOOL_DELEGATION = "task"  # PM delegates via 'task' tool with subagent_type
TOOL_PROTOCOL = "load_protocol"  # Protocol loading tool
TOOL_READ_DATA = "read_data"  # Data reading tool
TOOL_WRITE_FILE = "write_file"  # File writing tool
TOOL_VIEW_IMAGE = "view_image"  # Image viewing tool
TOOL_IMAGE_STUDIO = "image_studio"  # Image generation tool


def _normalize_agent_name(name: str) -> str:
    """Normalize agent name to canonical form."""
    if not name:
        return "unknown"

    name_lower = name.lower().replace(" ", "_").replace("-", "_")

    # Known agent types
    known_agents = {
        "visual_analyst",
        "product_analyst",
        "catalog_analyst",
        "creative_specialist",
        "catalog_specialist",
    }

    if name_lower in known_agents:
        return name_lower

    # Pattern matching for variations
    if "visual" in name_lower and "analyst" in name_lower:
        return "visual_analyst"
    if "product" in name_lower and "analyst" in name_lower:
        return "product_analyst"
    if "catalog" in name_lower and "analyst" in name_lower:
        return "catalog_analyst"
    if "creative" in name_lower and "specialist" in name_lower:
        return "creative_specialist"
    if "catalog" in name_lower and "specialist" in name_lower:
        return "catalog_specialist"

    return name


def _get_parent_chain(run, runs_by_id: dict) -> list[str]:
    """Get the full parent chain of run names from root to this run.

    Returns list like ['LangGraph', 'tools', 'task', 'LangGraph', 'tools', 'load_protocol']
    """
    chain = [run.name]
    current_id = run.parent_run_id

    while current_id:
        parent = runs_by_id.get(str(current_id))
        if not parent:
            break
        chain.append(parent.name)
        current_id = parent.parent_run_id

    return list(reversed(chain))


def _find_parent_agent(run, runs_by_id: dict, task_agents: dict[str, str]) -> str:
    """Find which agent made this tool call using chain structure.

    Logic:
    - LangGraph > tools > X = PM called X (including task itself)
    - LangGraph > tools > task > LangGraph > tools > X = subagent called X

    The subagent identity comes from the 'task' tool's subagent_type argument,
    which we track in task_agents dict.

    Args:
        run: The tool run to find parent for
        runs_by_id: Dict of all runs keyed by ID
        task_agents: Dict mapping task run_id -> subagent_type
    """
    chain = _get_parent_chain(run, runs_by_id)

    # If this IS the task tool, PM called it
    if run.name == TOOL_DELEGATION:
        return "PM"

    # Find if there's a 'task' in the PARENT chain (not including current run)
    # Chain: LangGraph > tools > task > LangGraph > tools > X
    # We want to find 'task' in parents, not in current run
    parent_chain = chain[:-1]  # Exclude current run from chain

    task_in_parents = TOOL_DELEGATION in parent_chain

    if not task_in_parents:
        # No task in parent chain = PM made this call directly
        return "PM"

    # Find the task run to get subagent_type
    # Walk up from current run to find the task run
    current_id = run.parent_run_id
    while current_id:
        parent = runs_by_id.get(str(current_id))
        if not parent:
            break
        if parent.name == TOOL_DELEGATION:
            # Found the task run - get its subagent_type
            agent = task_agents.get(str(parent.id))
            if agent:
                return _normalize_agent_name(agent)
            break
        current_id = parent.parent_run_id

    return "unknown"


def _extract_content_from_parts(content: Any) -> str:
    """Extract text from content that may be string or list of parts.

    Handles:
    - Direct string: "hello"
    - List of parts: [{"type": "text", "text": "hello"}, ...]
    - Empty list/string: returns ""
    """
    if not content:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        # Multi-part format: [{"type": "text", "text": "..."}, ...]
        parts = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text", "")
                if text:
                    parts.append(str(text))
            elif isinstance(part, str):
                parts.append(part)
        return "\n".join(parts)

    return str(content)


def _extract_llm_message(outputs: Any) -> str:
    """Extract message content from various LLM output formats.

    LangSmith stores LLM outputs in different formats depending on:
    - LangChain version
    - LLM provider (OpenAI, Anthropic, Gemini, etc.)
    - Whether using chat models or completion models

    Common formats:
    - {"generations": [[{"text": "...", "message": {"kwargs": {"content": [...]}}}]]}
    - {"generations": [[{"text": "...", "message": {"content": "..."}}]]}
    - {"content": "..."}
    - {"output": "..."}
    - {"messages": [{"content": "..."}]}
    - AIMessage/BaseMessage objects with .content attribute

    Content can be:
    - String: "hello world"
    - List of parts: [{"type": "text", "text": "hello"}, {"type": "image", ...}]

    Returns:
        Extracted message string, or empty string if not found
    """
    if not outputs:
        return ""

    # Handle string directly
    if isinstance(outputs, str):
        return outputs

    # Handle objects with .content attribute (AIMessage, etc.)
    if hasattr(outputs, "content"):
        content = getattr(outputs, "content", "")
        return _extract_content_from_parts(content)

    # Must be dict-like from here
    if not isinstance(outputs, dict):
        return str(outputs)

    # Try 'generations' format (LangChain standard)
    # Format: {"generations": [[{"text": "...", "message": {"kwargs": {"content": ...}}}]]}
    generations = outputs.get("generations")
    if generations and isinstance(generations, list) and len(generations) > 0:
        first_gen = generations[0]
        if isinstance(first_gen, list) and len(first_gen) > 0:
            gen_item = first_gen[0]
            if isinstance(gen_item, dict):
                # Try text first (often has the content for completion models)
                text_val = gen_item.get("text")
                if text_val and isinstance(text_val, str) and text_val.strip():
                    return text_val

                # Try message structure (chat models)
                msg = gen_item.get("message")
                if isinstance(msg, dict):
                    # LangChain serialized format: {"kwargs": {"content": ...}}
                    kwargs = msg.get("kwargs", {})
                    if isinstance(kwargs, dict) and "content" in kwargs:
                        return _extract_content_from_parts(kwargs["content"])

                    # Direct content format: {"content": ...}
                    if "content" in msg:
                        return _extract_content_from_parts(msg["content"])

    # Try direct content keys
    for key in ["content", "output", "text", "response"]:
        val = outputs.get(key)
        if val:
            extracted = _extract_content_from_parts(val)
            if extracted:
                return extracted

    # Try messages array
    messages = outputs.get("messages")
    if messages and isinstance(messages, list) and len(messages) > 0:
        last_msg = messages[-1]
        if isinstance(last_msg, dict):
            # Check kwargs.content first (LangChain serialized)
            kwargs = last_msg.get("kwargs", {})
            if isinstance(kwargs, dict) and "content" in kwargs:
                return _extract_content_from_parts(kwargs["content"])
            if "content" in last_msg:
                return _extract_content_from_parts(last_msg["content"])
        if hasattr(last_msg, "content"):
            return _extract_content_from_parts(getattr(last_msg, "content", ""))

    # Try output.content nested structure
    output_obj = outputs.get("output")
    if isinstance(output_obj, dict):
        kwargs = output_obj.get("kwargs", {})
        if isinstance(kwargs, dict) and "content" in kwargs:
            return _extract_content_from_parts(kwargs["content"])
        if "content" in output_obj:
            return _extract_content_from_parts(output_obj["content"])
    if hasattr(output_obj, "content"):
        return _extract_content_from_parts(getattr(output_obj, "content", ""))

    # Fallback: stringify entire output (indicates parsing failure)
    return str(outputs)


def _safe_parse_dict(value: Any) -> dict[str, Any]:
    """Safely parse a string representation of a dict.

    Handles:
    - Already a dict -> return as-is
    - String repr like "{'key': 'value'}" -> ast.literal_eval
    - JSON string -> json.loads
    - Unparseable -> return empty dict

    This eliminates fragile regex parsing.
    """
    import ast
    import json

    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        return {}

    # Try ast.literal_eval first (handles Python dict repr)
    try:
        result = ast.literal_eval(value)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    # Try JSON parsing
    try:
        result = json.loads(value)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    return {}


def _extract_subagent_type(inputs: dict | None) -> str | None:
    """Extract subagent_type from task tool inputs.

    Inputs look like: {'input': "{'subagent_type': 'creative_specialist', ...}"}
    """
    if not inputs:
        return None

    input_val = inputs.get("input", inputs)

    # Parse to dict if string
    parsed = _safe_parse_dict(input_val)
    if parsed:
        return parsed.get("subagent_type")

    # Fallback to regex for edge cases
    if isinstance(input_val, str) and "subagent_type" in input_val:
        match = re.search(r"['\"]subagent_type['\"]:\s*['\"]([^'\"]+)['\"]", input_val)
        if match:
            return match.group(1)

    return None


def get_tool_call_sequence(trace_id: str) -> ToolCallSequence:
    """Get ordered sequence of ALL tool calls in a trace.

    This is the PRIMARY function for evaluation. Returns every tool call
    with agent attribution, timing, and arguments for analyzing:
    - Protocol loading order (was load_protocol first for PM?)
    - Delegation sequence (which subagent_type in which order?)
    - File I/O patterns (who called read_data/write_file?)

    Args:
        trace_id: LangSmith trace ID

    Returns:
        ToolCallSequence with ordered tool calls and quick lookups

    Example:
        >>> seq = get_tool_call_sequence(trace_id)
        >>> # Check if PM loaded protocol first
        >>> if seq.first_tool_call and seq.first_tool_call.tool_name == "load_protocol":
        ...     if seq.first_tool_call.agent == "PM":
        ...         print("PM loaded protocol first")
        >>> # Check delegation order
        >>> for d in seq.delegation_calls:
        ...     subagent = d.tool_args.get("subagent_type")
        ...     print(f"{d.agent} -> {subagent}")
    """
    client = _get_client()

    # Fetch all tool runs
    runs = list(client.list_runs(trace_id=trace_id, run_type="tool"))

    if not runs:
        return ToolCallSequence(
            trace_id=trace_id,
            total_tool_calls=0,
            tool_calls=[],
        )

    # Build lookup for parent resolution
    all_runs = list(client.list_runs(trace_id=trace_id))
    runs_by_id = {str(r.id): r for r in all_runs}

    # Sort by start time
    runs.sort(key=lambda r: r.start_time if r.start_time else datetime.min)

    # First pass: build task_agents dict (task_run_id -> subagent_type)
    task_agents: dict[str, str] = {}
    for run in runs:
        if run.name == TOOL_DELEGATION:
            subagent = _extract_subagent_type(run.inputs)
            if subagent:
                task_agents[str(run.id)] = subagent

    tool_calls = []
    delegation_calls = []
    file_read_calls = []
    file_write_calls = []
    protocol_load_calls = []

    for seq_num, run in enumerate(runs, 1):
        # Find parent agent using chain structure
        parent_agent = _find_parent_agent(run, runs_by_id, task_agents)

        # Calculate duration
        duration_ms = None
        if run.end_time and run.start_time:
            duration_ms = int((run.end_time - run.start_time).total_seconds() * 1000)

        # Extract tool arguments (raw)
        tool_args = {}
        if run.inputs:
            if isinstance(run.inputs, dict):
                input_val = run.inputs.get("input", run.inputs)
                if isinstance(input_val, str):
                    tool_args = {"input": input_val}
                elif isinstance(input_val, dict):
                    tool_args = input_val

        # Parse arguments properly (eliminates need for regex in evaluation)
        parsed_args = {}
        if run.inputs:
            input_val = run.inputs.get("input", run.inputs)
            parsed_args = _safe_parse_dict(input_val)
            if not parsed_args and isinstance(input_val, dict):
                parsed_args = input_val

        # Extract output
        tool_output = None
        if run.outputs:
            if isinstance(run.outputs, dict):
                # Common output patterns
                tool_output = (
                    run.outputs.get("output")
                    or run.outputs.get("result")
                    or run.outputs.get("content")
                    or run.outputs
                )
            else:
                tool_output = run.outputs

        # Detect error status
        status = "success"
        error_msg = None
        if run.error:
            status = "error"
            error_msg = str(run.error)
        elif hasattr(run, "status") and run.status == "error":
            status = "error"
            error_msg = getattr(run, "error_message", None)

        tc = SequencedToolCall(
            sequence=seq_num,
            agent=parent_agent,
            tool_name=run.name,
            tool_args=tool_args,
            parsed_args=parsed_args,
            tool_output=tool_output,
            timestamp=run.start_time,
            duration_ms=duration_ms,
            run_id=str(run.id),
            parent_agent=parent_agent,
            status=status,
            error=error_msg,
        )
        tool_calls.append(tc)

        # Categorize by actual tool names
        if run.name == TOOL_DELEGATION:
            delegation_calls.append(tc)
        elif run.name == TOOL_READ_DATA:
            file_read_calls.append(tc)
        elif run.name == TOOL_WRITE_FILE:
            file_write_calls.append(tc)
        elif run.name == TOOL_PROTOCOL:
            protocol_load_calls.append(tc)

    return ToolCallSequence(
        trace_id=trace_id,
        total_tool_calls=len(tool_calls),
        tool_calls=tool_calls,
        first_tool_call=tool_calls[0] if tool_calls else None,
        delegation_calls=delegation_calls,
        file_read_calls=file_read_calls,
        file_write_calls=file_write_calls,
    )


def get_delegation_graph(trace_id: str) -> DelegationGraph:
    """Get hierarchical graph of agent delegations.

    Extracts all 'task' tool calls (PM's delegation mechanism) and builds
    a graph showing:
    - Who delegated to whom (via subagent_type)
    - Wave structure (parallel vs serial based on timing)
    - Context passed between agents (description field)

    Args:
        trace_id: LangSmith trace ID

    Returns:
        DelegationGraph with delegations, waves, and involved agents

    Example:
        >>> graph = get_delegation_graph(trace_id)
        >>> # Check wave structure
        >>> print(f"Wave 1: {graph.waves.get(1, [])}")
        >>> print(f"Wave 2: {graph.waves.get(2, [])}")
        >>> # Verify creative_specialist was delegated
        >>> if "creative_specialist" in graph.delegation_order:
        ...     print("PM delegated to creative_specialist")
    """
    # Get tool call sequence first
    seq = get_tool_call_sequence(trace_id)

    delegations = []
    agents_involved = set()
    delegation_order = []

    # Track timing for wave detection
    delegation_times = []

    for tc in seq.delegation_calls:
        # 'task' tool uses subagent_type for target agent
        # Use parsed_args (properly parsed dict) instead of tool_args (raw)
        to_agent = tc.parsed_args.get("subagent_type")

        # Extract description as context passed (using parsed_args)
        context_passed = []
        description = tc.parsed_args.get("description", "")
        if description:
            # Truncate long descriptions
            context_passed.append(description[:100] + "..." if len(description) > 100 else description)

        if to_agent:
            to_agent = _normalize_agent_name(str(to_agent))
            delegation = AgentDelegation(
                from_agent=tc.agent,  # Usually PM
                to_agent=to_agent,
                context_passed=context_passed,
                timestamp=tc.timestamp,
            )
            delegations.append(delegation)
            agents_involved.add(to_agent)
            delegation_order.append(to_agent)
            delegation_times.append((to_agent, tc.timestamp))

    # Detect waves based on timing
    # Wave = delegations that happen close together (within 5 seconds)
    waves: dict[int, list[str]] = {}
    if delegation_times:
        current_wave = 1
        wave_start = delegation_times[0][1]
        waves[current_wave] = [delegation_times[0][0]]

        for agent, timestamp in delegation_times[1:]:
            if timestamp and wave_start:
                time_diff = (timestamp - wave_start).total_seconds()
                if time_diff > 5:  # More than 5 seconds = new wave
                    current_wave += 1
                    wave_start = timestamp
                    waves[current_wave] = []
            waves[current_wave].append(agent)

        # Mark parallel delegations
        for wave_num, wave_agents in waves.items():
            if len(wave_agents) > 1:
                for d in delegations:
                    if d.to_agent in wave_agents:
                        d.wave = wave_num
                        d.parallel_with = [a for a in wave_agents if a != d.to_agent]

    # Find root agent
    root_agent = "PM"
    if delegations:
        root_agent = delegations[0].from_agent

    return DelegationGraph(
        trace_id=trace_id,
        root_agent=root_agent,
        delegations=delegations,
        waves=waves,
        agents_involved=list(agents_involved),
        delegation_order=delegation_order,
    )


def get_file_io_trace(trace_id: str) -> FileIOTrace:
    """Get all file operations in a trace.

    Extracts all read_data and write_file calls to analyze:
    - Did agents write output files?
    - Did PM read analysis/output files?
    - What data was queried?

    Note: Protocol loading is tracked separately via get_protocol_loads()
    which uses the load_protocol tool.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        FileIOTrace with all file operations categorized

    Example:
        >>> fio = get_file_io_trace(trace_id)
        >>> # Check write operations
        >>> for w in fio.writes:
        ...     print(f"{w.agent} wrote {w.file_path}")
    """
    seq = get_tool_call_sequence(trace_id)

    operations = []
    writes = []
    reads = []
    analysis_files_written = []
    analysis_files_read_by_pm = []
    protocol_files_read = []

    for tc in seq.file_read_calls + seq.file_write_calls:
        # Determine operation type
        is_read = tc.tool_name == TOOL_READ_DATA
        op_type = "read" if is_read else "write"

        # Extract relevant info from parsed_args (properly parsed dict)
        file_path = ""
        content_preview = None

        # Use parsed_args which has properly parsed the JSON input
        args = tc.parsed_args if tc.parsed_args else {}

        if is_read:
            # read_data uses 'table' and 'search_patterns'
            file_path = f"table:{args.get('table', 'unknown')}" if args.get('table') else ""
        else:
            # write_file uses 'file_path' (or 'path') and 'content'
            file_path = (
                args.get("file_path")
                or args.get("path")
                or args.get("filename")
                or ""
            )
            content = args.get("content", args.get("data", ""))
            if isinstance(content, str):
                content_preview = content[:200]

        op = FileOperation(
            operation=op_type,
            agent=tc.agent,
            file_path=str(file_path),
            timestamp=tc.timestamp,
            sequence=tc.sequence,
            content_preview=content_preview,
        )
        operations.append(op)

        if is_read:
            reads.append(op)
        else:
            writes.append(op)
            # Track analysis files written
            path_lower = str(file_path).lower()
            if any(p in path_lower for p in ["analysis", "research", "output"]):
                analysis_files_written.append(str(file_path))

    # Sort operations by sequence
    operations.sort(key=lambda o: o.sequence)

    return FileIOTrace(
        trace_id=trace_id,
        operations=operations,
        writes=writes,
        reads=reads,
        analysis_files_written=analysis_files_written,
        analysis_files_read_by_pm=analysis_files_read_by_pm,
        protocol_files_read=protocol_files_read,  # Now handled by get_protocol_loads
    )


def get_protocol_loads(trace_id: str) -> ProtocolLoadTrace:
    """Get all protocol loads in a trace.

    Uses the load_protocol tool calls to identify which agents loaded
    which protocols and whether protocol loading was the first action.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        ProtocolLoadTrace with all protocol loads and compliance info

    Example:
        >>> protocols = get_protocol_loads(trace_id)
        >>> if protocols.pm_first_action_was_protocol:
        ...     print(f"PM loaded {protocols.pm_protocol} first")
        >>> for agent, protocol in protocols.agent_protocols.items():
        ...     print(f"{agent} loaded {protocol}")
    """
    seq = get_tool_call_sequence(trace_id)

    protocol_loads = []
    agent_protocols: dict[str, str] = {}
    agent_first_actions: dict[str, int] = {}

    # Track first action per agent
    for tc in seq.tool_calls:
        if tc.agent not in agent_first_actions:
            agent_first_actions[tc.agent] = tc.sequence

    # Find load_protocol tool calls
    for tc in seq.tool_calls:
        if tc.tool_name != TOOL_PROTOCOL:
            continue

        # Extract protocol info from args
        # Args look like: {'input': "{'protocol_names': ['hitl'], 'domain': 'pm'}"}
        protocol_names = []
        domain = None

        input_str = tc.tool_args.get("input", "")
        if isinstance(input_str, str):
            # Extract protocol_names
            names_match = re.search(r"['\"]protocol_names['\"]:\s*\[([^\]]+)\]", input_str)
            if names_match:
                # Parse list of names
                names_str = names_match.group(1)
                protocol_names = re.findall(r"['\"]([^'\"]+)['\"]", names_str)

            # Extract domain
            domain_match = re.search(r"['\"]domain['\"]:\s*['\"]([^'\"]+)['\"]", input_str)
            if domain_match:
                domain = domain_match.group(1)

        is_first = agent_first_actions.get(tc.agent) == tc.sequence

        for protocol_name in protocol_names:
            pl = ProtocolLoad(
                agent=tc.agent,
                protocol_path=f"{domain}/{protocol_name}" if domain else protocol_name,
                protocol_name=protocol_name,
                timestamp=tc.timestamp,
                sequence=tc.sequence,
                is_first_action=is_first,
            )
            protocol_loads.append(pl)

            # Track first protocol per agent
            if tc.agent not in agent_protocols:
                agent_protocols[tc.agent] = protocol_name

    # Check PM compliance
    pm_first_action_was_protocol = False
    pm_protocol = None

    pm_loads = [pl for pl in protocol_loads if pl.agent == "PM"]
    if pm_loads:
        pm_protocol = pm_loads[0].protocol_name
        pm_first_action_was_protocol = pm_loads[0].is_first_action

    return ProtocolLoadTrace(
        trace_id=trace_id,
        protocol_loads=protocol_loads,
        pm_first_action_was_protocol=pm_first_action_was_protocol,
        pm_protocol=pm_protocol,
        agent_protocols=agent_protocols,
    )


def get_agent_final_message(
    trace_id: str,
    agent: str = "PM",
    any_agent: bool = False,
) -> AgentFinalMessage | None:
    """Get the final message from an agent to the user.

    Used to evaluate:
    - Did PM present open-ended question at approval gate?
    - Does message contain numbered options (anti-pattern)?
    - What model generated the response?
    - Token usage and performance metrics

    Args:
        trace_id: LangSmith trace ID
        agent: Agent name to get final message for (default: PM)
        any_agent: If True, find last message from ANY agent (ignores agent param).
                   Useful when PM orchestrates but specialists produce user messages.

    Returns:
        AgentFinalMessage or None if no message found

    Example:
        >>> # Get PM's final message
        >>> msg = get_agent_final_message(trace_id, "PM")
        >>>
        >>> # Get last message from any agent (when PM just orchestrates)
        >>> msg = get_agent_final_message(trace_id, any_agent=True)
        >>> print(f"Message from {msg.agent}: {msg.message_preview}")
    """
    client = _get_client()

    # Get all runs to build lookups
    all_runs = list(client.list_runs(trace_id=trace_id))
    runs_by_id = {str(r.id): r for r in all_runs}

    # Build task_agents dict from tool runs (needed for agent attribution)
    task_agents: dict[str, str] = {}
    for run in all_runs:
        if run.run_type == "tool" and run.name == TOOL_DELEGATION:
            subagent = _extract_subagent_type(run.inputs)
            if subagent:
                task_agents[str(run.id)] = subagent

    # Find LLM runs - either for specific agent or all agents
    candidate_llm_runs = []
    for run in all_runs:
        if run.run_type == "llm":
            parent_agent = _find_parent_agent(run, runs_by_id, task_agents)
            if any_agent:
                # Include all LLM runs with their attributed agent
                candidate_llm_runs.append((run, parent_agent))
            elif parent_agent == agent:
                candidate_llm_runs.append((run, parent_agent))

    if not candidate_llm_runs:
        return None

    # Sort by time (newest first) and find last run WITH actual content
    # LLM runs that only make tool calls often have empty content
    candidate_llm_runs.sort(
        key=lambda x: x[0].end_time if x[0].end_time else datetime.min,
        reverse=True,
    )

    last_run = None
    message = ""
    found_agent = agent
    for run, run_agent in candidate_llm_runs:
        extracted = _extract_llm_message(run.outputs)
        if extracted and extracted.strip():
            last_run = run
            message = extracted
            found_agent = run_agent
            break

    if not last_run or not message:
        return None

    # Extract model name from various locations
    model_name = None
    extra = last_run.extra or {}
    if isinstance(extra, dict):
        # Try invocation_params first (most common)
        invocation = extra.get("invocation_params", {})
        model_name = (
            invocation.get("model")
            or invocation.get("model_name")
            or extra.get("model")
            or extra.get("model_name")
        )
    # Also check run.name for model info
    if not model_name and last_run.name:
        # Run names often contain model: "ChatOpenAI", "ChatAnthropic", etc.
        if "gpt" in last_run.name.lower():
            model_name = last_run.name
        elif "claude" in last_run.name.lower():
            model_name = last_run.name

    # Extract token count from usage metadata
    token_count = None
    if hasattr(last_run, "total_tokens") and last_run.total_tokens:
        token_count = last_run.total_tokens
    elif isinstance(extra, dict):
        usage = extra.get("usage", {})
        if isinstance(usage, dict):
            token_count = usage.get("total_tokens")

    # Analyze message content
    message_lower = message.lower()

    has_numbered_options = bool(re.search(r"^\s*[1-9]\.", message, re.MULTILINE))
    has_open_question = message.strip().endswith("?")

    is_approval_request = any(
        phrase in message_lower
        for phrase in ["approve", "confirm", "proceed", "would you like", "what would you"]
    )

    mentions_error = any(
        phrase in message_lower
        for phrase in ["error", "failed", "failure", "couldn't", "unable to", "problem"]
    )

    mentions_success = any(
        phrase in message_lower
        for phrase in ["success", "completed", "saved", "created", "done", "ready"]
    )

    has_product_details = any(
        phrase in message_lower
        for phrase in ["price", "sku", "product", "catalog", "rs.", "rs ", "inr", "$"]
    )

    return AgentFinalMessage(
        agent=found_agent,
        message=message,
        message_preview=message[:200] + "..." if len(message) > 200 else message,
        timestamp=last_run.end_time,
        run_id=str(last_run.id),
        model_name=model_name,
        token_count=token_count,
        has_numbered_options=has_numbered_options,
        has_open_question=has_open_question,
        is_approval_request=is_approval_request,
        mentions_error=mentions_error,
        mentions_success=mentions_success,
        has_product_details=has_product_details,
    )


# ============================================================================
# LangSmith Feedback Integration (for storing evaluations)
# ============================================================================


def record_evaluation(
    trace_id: str,
    scenario_id: str,
    result: EvaluationResult,
) -> bool:
    """Store evaluation result in LangSmith as feedback.

    Records each criterion as a separate feedback entry plus
    an overall result, enabling queries like:
    - "Show all traces where wave_execution failed"
    - "What's the pass rate for PM-01?"

    Args:
        trace_id: LangSmith trace ID
        scenario_id: Scenario that was evaluated
        result: Complete evaluation result

    Returns:
        True if feedback was recorded successfully

    Example:
        >>> result = EvaluationResult(
        ...     scenario_id="PM-01",
        ...     trace_id=trace_id,
        ...     status="FAIL",
        ...     ...
        ... )
        >>> record_evaluation(trace_id, "PM-01", result)
    """
    client = _get_client()

    try:
        # Get root run ID for the trace
        runs = list(client.list_runs(trace_id=trace_id, limit=1))
        if not runs:
            return False

        run_id = str(runs[0].id)

        # Record overall result
        client.create_feedback(
            run_id=run_id,
            key="scenario_result",
            score=result.overall_score,
            value=result.status,
            comment=f"Scenario {scenario_id}: {result.status}. "
            f"Passed {result.passed_criteria}/{result.passed_criteria + result.failed_criteria} criteria.",
        )

        # Record each criterion
        for criterion in result.criteria_results:
            client.create_feedback(
                run_id=run_id,
                key=criterion.criterion,
                score=criterion.score,
                value="PASS" if criterion.passed else "FAIL",
                comment=criterion.reasoning,
            )

        return True

    except Exception as e:
        print(f"Failed to record evaluation: {e}")
        return False


def get_scenario_history(
    scenario_id: str,
    days: int = 30,
    project_name: str | None = None,
) -> ScenarioHistory:
    """Get historical runs and evaluations for a scenario.

    Queries LangSmith for past runs of this scenario and aggregates
    evaluation feedback for pattern detection.

    Args:
        scenario_id: Scenario to get history for
        days: How many days of history (default: 30)
        project_name: LangSmith project name (optional)

    Returns:
        ScenarioHistory with aggregate stats and individual runs

    Example:
        >>> history = get_scenario_history("PM-01", days=7)
        >>> print(f"Pass rate: {history.pass_rate:.1%}")
        >>> print(f"Most common failure: {history.most_common_failure}")
    """
    client = _get_client()

    start_time = datetime.now() - timedelta(days=days)

    # Query runs with scenario metadata
    filter_str = f'eq(metadata.scenario_id, "{scenario_id}")'

    try:
        if project_name:
            runs = list(
                client.list_runs(
                    project_name=project_name,
                    filter=filter_str,
                    start_time=start_time,
                )
            )
        else:
            # Try to find runs across projects
            runs = list(
                client.list_runs(
                    filter=filter_str,
                    start_time=start_time,
                )
            )
    except Exception:
        runs = []

    if not runs:
        return ScenarioHistory(
            scenario_id=scenario_id,
            total_runs=0,
            date_range_days=days,
            pass_rate=0.0,
            avg_score=0.0,
        )

    # Collect run summaries and feedback
    run_summaries = []
    failure_counts: dict[str, int] = {}
    total_score = 0.0
    pass_count = 0

    for run in runs:
        # Get feedback for this run
        try:
            feedbacks = list(client.list_feedback(run_id=str(run.id)))
        except Exception:
            feedbacks = []

        # Find overall result
        status = "UNKNOWN"
        score = 0.0
        failed_criteria = []

        for fb in feedbacks:
            if fb.key == "scenario_result":
                status = fb.value or "UNKNOWN"
                score = fb.score or 0.0
            elif fb.value == "FAIL":
                failed_criteria.append(fb.key)
                failure_counts[fb.key] = failure_counts.get(fb.key, 0) + 1

        if status == "PASS":
            pass_count += 1
        total_score += score

        # Calculate duration
        duration_ms = None
        if run.end_time and run.start_time:
            duration_ms = int((run.end_time - run.start_time).total_seconds() * 1000)

        summary = ScenarioRunSummary(
            trace_id=str(run.trace_id) if run.trace_id else str(run.id),
            run_date=run.start_time or datetime.now(),
            status=status,
            score=score,
            failed_criteria=failed_criteria,
            duration_ms=duration_ms,
            cost=float(run.total_cost) if run.total_cost else None,
        )
        run_summaries.append(summary)

    # Sort by date, newest first
    run_summaries.sort(key=lambda r: r.run_date, reverse=True)

    # Calculate aggregates
    total_runs = len(run_summaries)
    pass_rate = pass_count / total_runs if total_runs > 0 else 0.0
    avg_score = total_score / total_runs if total_runs > 0 else 0.0

    # Find most common failure
    most_common_failure = None
    if failure_counts:
        most_common_failure = max(failure_counts, key=failure_counts.get)  # type: ignore

    # Determine trend (compare recent 5 vs previous 5)
    recent_trend = None
    if len(run_summaries) >= 10:
        recent_5 = run_summaries[:5]
        previous_5 = run_summaries[5:10]
        recent_pass = sum(1 for r in recent_5 if r.status == "PASS")
        previous_pass = sum(1 for r in previous_5 if r.status == "PASS")
        if recent_pass > previous_pass:
            recent_trend = "improving"
        elif recent_pass < previous_pass:
            recent_trend = "degrading"
        else:
            recent_trend = "stable"

    return ScenarioHistory(
        scenario_id=scenario_id,
        total_runs=total_runs,
        date_range_days=days,
        pass_rate=pass_rate,
        avg_score=avg_score,
        failure_counts=failure_counts,
        most_common_failure=most_common_failure,
        recent_trend=recent_trend,
        runs=run_summaries,
    )


def get_baseline(scenario_id: str, dataset_name: str = "scenario-baselines") -> TraceBaseline | None:
    """Get known-good baseline for a scenario.

    Retrieves the reference trace from LangSmith dataset for comparison.

    Args:
        scenario_id: Scenario to get baseline for
        dataset_name: LangSmith dataset name (default: scenario-baselines)

    Returns:
        TraceBaseline or None if no baseline exists

    Example:
        >>> baseline = get_baseline("PM-01")
        >>> if baseline:
        ...     print(f"Expected delegation order: {baseline.expected_delegation_order}")
    """
    client = _get_client()

    try:
        # Find dataset
        datasets = list(client.list_datasets(dataset_name=dataset_name))
        if not datasets:
            return None

        dataset = datasets[0]

        # Find example for this scenario
        examples = list(client.list_examples(dataset_id=dataset.id))
        for example in examples:
            if example.metadata and example.metadata.get("scenario_id") == scenario_id:
                # Extract baseline from example
                outputs = example.outputs or {}

                return TraceBaseline(
                    scenario_id=scenario_id,
                    trace_id=outputs.get("trace_id", ""),
                    created_at=example.created_at or datetime.now(),
                    expected_tool_sequence=outputs.get("expected_tool_sequence", []),
                    expected_delegation_order=outputs.get("expected_delegation_order", []),
                    expected_waves=outputs.get("expected_waves", {}),
                    expected_protocol_loads=outputs.get("expected_protocol_loads", {}),
                    baseline_duration_ms=outputs.get("baseline_duration_ms"),
                    baseline_cost=outputs.get("baseline_cost"),
                    baseline_tool_count=outputs.get("baseline_tool_count"),
                    notes=example.metadata.get("notes") if example.metadata else None,
                )

        return None

    except Exception as e:
        print(f"Failed to get baseline: {e}")
        return None


def store_baseline(
    trace_id: str,
    scenario_id: str,
    dataset_name: str = "scenario-baselines",
    notes: str | None = None,
) -> bool:
    """Store a trace as the known-good baseline for a scenario.

    Extracts patterns from the trace and stores them in LangSmith
    dataset for future comparison.

    Args:
        trace_id: Trace ID to use as baseline
        scenario_id: Scenario this baseline is for
        dataset_name: LangSmith dataset name (default: scenario-baselines)
        notes: Why this trace was chosen as baseline

    Returns:
        True if baseline was stored successfully

    Example:
        >>> # After verifying a trace is correct
        >>> store_baseline(trace_id, "PM-01", notes="Verified correct wave execution")
    """
    client = _get_client()

    try:
        # Get or create dataset
        datasets = list(client.list_datasets(dataset_name=dataset_name))
        if datasets:
            dataset = datasets[0]
        else:
            dataset = client.create_dataset(
                dataset_name=dataset_name,
                description="Known-good baseline traces for scenario evaluation",
            )

        # Extract patterns from trace
        seq = get_tool_call_sequence(trace_id)
        graph = get_delegation_graph(trace_id)
        protocols = get_protocol_loads(trace_id)
        overview = get_trace_overview(trace_id)

        # Build baseline data
        baseline_data = {
            "trace_id": trace_id,
            "expected_tool_sequence": [tc.tool_name for tc in seq.tool_calls],
            "expected_delegation_order": graph.delegation_order,
            "expected_waves": {str(k): v for k, v in graph.waves.items()},
            "expected_protocol_loads": protocols.agent_protocols,
            "baseline_duration_ms": overview.total_latency_ms,
            "baseline_cost": overview.total_cost,
            "baseline_tool_count": seq.total_tool_calls,
        }

        # Check if example already exists for this scenario
        existing_examples = list(client.list_examples(dataset_id=dataset.id))
        for example in existing_examples:
            if example.metadata and example.metadata.get("scenario_id") == scenario_id:
                # Update existing - mark as superseded and create new
                if example.outputs:
                    example.outputs["superseded_by"] = trace_id
                # Delete old and create new
                client.delete_example(example.id)
                break

        # Create new example
        client.create_example(
            dataset_id=dataset.id,
            inputs={"scenario_id": scenario_id},
            outputs=baseline_data,
            metadata={
                "scenario_id": scenario_id,
                "notes": notes,
                "created_at": datetime.now().isoformat(),
            },
        )

        return True

    except Exception as e:
        print(f"Failed to store baseline: {e}")
        return False


def compare_to_baseline(
    trace_id: str,
    scenario_id: str,
    dataset_name: str = "scenario-baselines",
) -> dict[str, Any]:
    """Compare a trace to its known-good baseline.

    Returns a structured comparison showing what matches and what deviates
    from the expected behavior.

    Args:
        trace_id: Trace ID to compare
        scenario_id: Scenario to get baseline for
        dataset_name: LangSmith dataset name (default: scenario-baselines)

    Returns:
        Dict with comparison results:
        {
            "has_baseline": True/False,
            "matches": ["delegation_order", "wave_structure"],
            "deviations": [{"field": "protocol_loading", "expected": "hitl", "actual": None}],
            "metrics": {"duration_diff_ms": 500, "cost_diff": 0.01, "tool_count_diff": 2}
        }

    Example:
        >>> comparison = compare_to_baseline(trace_id, "PM-01")
        >>> if comparison["deviations"]:
        ...     for d in comparison["deviations"]:
        ...         print(f"{d['field']}: expected {d['expected']}, got {d['actual']}")
    """
    result: dict[str, Any] = {
        "has_baseline": False,
        "matches": [],
        "deviations": [],
        "metrics": {},
    }

    # Get baseline
    baseline = get_baseline(scenario_id, dataset_name)
    if not baseline:
        return result

    result["has_baseline"] = True

    # Get current trace data
    seq = get_tool_call_sequence(trace_id)
    graph = get_delegation_graph(trace_id)
    protocols = get_protocol_loads(trace_id)
    overview = get_trace_overview(trace_id)

    # Compare delegation order
    current_delegation = graph.delegation_order
    if current_delegation == baseline.expected_delegation_order:
        result["matches"].append("delegation_order")
    else:
        result["deviations"].append({
            "field": "delegation_order",
            "expected": baseline.expected_delegation_order,
            "actual": current_delegation,
        })

    # Compare wave structure
    current_waves = {str(k): v for k, v in graph.waves.items()}
    expected_waves = {str(k): v for k, v in baseline.expected_waves.items()}
    if current_waves == expected_waves:
        result["matches"].append("wave_structure")
    else:
        result["deviations"].append({
            "field": "wave_structure",
            "expected": expected_waves,
            "actual": current_waves,
        })

    # Compare protocol loading
    if protocols.agent_protocols == baseline.expected_protocol_loads:
        result["matches"].append("protocol_loads")
    else:
        result["deviations"].append({
            "field": "protocol_loads",
            "expected": baseline.expected_protocol_loads,
            "actual": protocols.agent_protocols,
        })

    # Compare tool sequence (just count for now)
    current_tools = [tc.tool_name for tc in seq.tool_calls]
    if current_tools == baseline.expected_tool_sequence:
        result["matches"].append("tool_sequence")
    else:
        result["deviations"].append({
            "field": "tool_sequence",
            "expected": baseline.expected_tool_sequence,
            "actual": current_tools,
        })

    # Metrics comparison
    if baseline.baseline_duration_ms and overview.total_latency_ms:
        result["metrics"]["duration_diff_ms"] = overview.total_latency_ms - baseline.baseline_duration_ms

    if baseline.baseline_cost and overview.total_cost:
        result["metrics"]["cost_diff"] = round(overview.total_cost - baseline.baseline_cost, 4)

    if baseline.baseline_tool_count:
        result["metrics"]["tool_count_diff"] = seq.total_tool_calls - baseline.baseline_tool_count

    return result


# ============================================================================
# Multi-Turn Thread Analysis
# ============================================================================


def get_thread_traces(
    thread_id: str, enrich: bool = False, days: int = 7
) -> "ThreadTraces":
    """Get all traces in a conversation thread for multi-turn evaluation.

    Queries workflow_outcomes by thread_id. Optionally enriches with agent messages.
    Use this when evaluating scenarios that span multiple conversation turns.

    Args:
        thread_id: Thread ID linking conversation turns
        enrich: If True, fetch final message for each trace (slow but detailed)
        days: Only include traces from last N days (default: 7)

    Returns:
        ThreadTraces with all traces in chronological order

    Example:
        >>> # Quick: just get trace list
        >>> thread = get_thread_traces("whatsapp:123:456")
        >>> for t in thread.traces:
        ...     print(f"Turn {t.turn}: {t.user_message[:50]}...")
        >>>
        >>> # Detailed: include agent responses (slower)
        >>> thread = get_thread_traces("whatsapp:123:456", enrich=True)
        >>> for t in thread.traces:
        ...     print(f"  -> {t.agent_that_responded}: {t.agent_message_preview}")
    """
    from tests.tools.models import ThreadTrace, ThreadTraces

    # Use supabase-py client directly with env vars
    try:
        import os

        from supabase import create_client

        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get(
            "SUPABASE_ANON_KEY"
        )

        if not url or not key:
            raise ValueError("Missing SUPABASE_URL or key env vars")

        supabase = create_client(url, key)

        # Calculate date filter
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        # Query workflow_outcomes for this thread (recent only, with trace_id)
        response = (
            supabase.table("workflow_outcomes")
            .select("trace_id, message_text, created_at, duration_seconds")
            .eq("thread_id", thread_id)
            .gte("created_at", cutoff_str)
            .not_.is_("trace_id", "null")
            .order("created_at", desc=False)
            .execute()
        )

        outcomes = response.data if response.data else []
    except Exception:
        outcomes = []

    traces = []
    total_duration = 0

    for i, outcome in enumerate(outcomes, start=1):
        trace_id = outcome.get("trace_id")
        duration_ms = int((outcome.get("duration_seconds") or 0) * 1000)
        total_duration += duration_ms

        # Optionally enrich with final message (slow - makes API call per trace)
        agent_preview = None
        agent_name = None
        if enrich and trace_id:
            try:
                msg = get_agent_final_message(trace_id, any_agent=True)
                if msg:
                    agent_preview = msg.message_preview
                    agent_name = msg.agent
            except Exception:
                pass

        traces.append(
            ThreadTrace(
                trace_id=trace_id or "",
                turn=i,
                timestamp=outcome.get("created_at"),
                duration_ms=duration_ms,
                user_message=outcome.get("message_text"),
                agent_message_preview=agent_preview,
                agent_that_responded=agent_name,
            )
        )

    return ThreadTraces(
        thread_id=thread_id,
        traces=traces,
        total_traces=len(traces),
        total_duration_ms=total_duration,
    )


# ============================================================================
# LangSmith Annotation Queue Integration
# ============================================================================

# Default queue ID for PM evaluations
PM_EVALUATION_QUEUE_ID = "355dae58-585f-475d-89ce-f632a9d81af3"


def add_to_evaluation_queue(
    trace_id: str,
    queue_id: str = PM_EVALUATION_QUEUE_ID,
) -> bool:
    """Add a trace to LangSmith annotation queue for human review.

    Use this after running a scenario to queue it for structured evaluation
    in the LangSmith UI.

    Args:
        trace_id: LangSmith trace ID to add
        queue_id: Annotation queue ID (defaults to PM Evaluation queue)

    Returns:
        True if successfully added, False otherwise

    Example:
        >>> result = chat_with_pm("Catalog this", media_path="img.jpg")
        >>> add_to_evaluation_queue(result.trace_id)
        >>> print("Trace queued for review at: https://smith.langchain.com/annotation-queues")
    """
    client = _get_client()
    try:
        client.add_runs_to_annotation_queue(
            queue_id=queue_id,
            run_ids=[trace_id],
        )
        return True
    except Exception:
        return False


def get_evaluation_queue_url(queue_id: str = PM_EVALUATION_QUEUE_ID) -> str:
    """Get URL to view annotation queue in LangSmith.

    Returns:
        LangSmith annotation queue URL
    """
    return f"https://smith.langchain.com/annotation-queues/{queue_id}"
