"""Trace loading utilities for /evaluate skill.

Provides evaluation-friendly trace loading that combines multiple
trace_analysis.py functions into a single coherent structure
optimized for LLM-as-Judge evaluation.

Enhanced with helpers.py integration for:
- Proper user message extraction (multimodal support)
- LangChain message/output parsing
- Auto-detected issues (errors, high tokens, broken handoffs)
- Handoff quality analysis

Usage:
    from tests.tools.trace_loader import load_trace_for_eval, format_trace_for_display

    trace = load_trace_for_eval("trace_id_here")
    print(format_trace_for_display(trace))
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from langsmith import Client

from .evaluation.helpers import (
    _extract_pm_output,
    _extract_user_input,
    detect_issues,
    parse_lc_messages,
    scan_all_handoffs,
)
from .trace_analysis import (
    get_agent_final_message,
    get_delegation_graph,
    get_protocol_loads,
    get_tool_call_sequence,
    get_trace_overview,
)

# Lazy client initialization
_client: Client | None = None


def _get_client() -> Client:
    """Get or create LangSmith client."""
    global _client
    if _client is None:
        load_dotenv()
        _client = Client()
    return _client


@dataclass
class DetectedIssue:
    """Auto-detected issue in trace."""

    type: str  # ERROR, HIGH_TOKENS, TOOL_LOOP, MISSING_CONTEXT
    severity: str  # HIGH, MEDIUM, LOW
    node_id: str
    node_name: str
    description: str


@dataclass
class HandoffAnalysis:
    """Analysis of context handoff quality."""

    from_agent: str
    to_agent: str
    context_passed: str
    has_file_path: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class TraceForEval:
    """Evaluation-optimized trace representation.

    Combines data from multiple trace_analysis functions into
    a single structure designed for LLM-as-Judge evaluation.
    """

    # Identifiers
    trace_id: str
    thread_id: str | None = None
    session_id: str | None = None
    timestamp: datetime | None = None

    # User interaction (enhanced with proper extraction)
    user_message: str = ""
    user_message_raw: str = ""  # Full untruncated message
    has_image: bool = False
    media_paths: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    # PM behavior
    pm_reasoning: str = ""
    pm_output_preview: str = ""
    delegations: list[dict[str, Any]] = field(default_factory=list)
    delegation_order: list[str] = field(default_factory=list)
    waves: dict[int, list[str]] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    protocols_loaded: dict[str, str] = field(default_factory=dict)
    interrupts: list[dict[str, Any]] = field(default_factory=list)

    # Output
    final_response: str = ""
    final_response_agent: str = "PM"
    state_changes: dict[str, Any] = field(default_factory=dict)

    # Quality indicators
    has_numbered_options: bool = False
    has_open_question: bool = False
    is_approval_request: bool = False
    mentions_error: bool = False
    mentions_success: bool = False

    # Auto-detected issues (from helpers.detect_issues)
    detected_issues: list[DetectedIssue] = field(default_factory=list)
    handoff_issues: list[HandoffAnalysis] = field(default_factory=list)

    # Metrics
    total_tokens: int = 0
    latency_ms: int = 0
    total_cost: float = 0.0
    total_runs: int = 0
    llm_calls: int = 0
    tool_call_count: int = 0
    error: str | None = None
    status: str = "unknown"


def _extract_user_message_from_root(root_run) -> tuple[str, str, bool]:
    """Extract user message from root run using helpers pattern.

    Returns:
        Tuple of (preview, full_message, has_image)
    """
    preview = _extract_user_input(root_run)

    # Check for image indicators - multiple formats:
    # - "[Image]" from multimodal parsing
    # - "[1 media attachment(s):" from WhatsApp integration
    # - "media attachment" general pattern
    has_image = (
        "[Image]" in preview
        or "media attachment" in preview.lower()
    )

    # Get full message if available
    full_message = ""
    if root_run.inputs and "messages" in root_run.inputs:
        messages = parse_lc_messages(root_run.inputs["messages"])
        for msg in messages:
            if msg["type"] == "HumanMessage":
                full_message = msg.get("content", "")
                break

    return preview, full_message, has_image


def load_trace_for_eval(trace_id: str, include_issues: bool = True) -> TraceForEval:
    """Load trace in evaluation-friendly format.

    Combines data from multiple sources:
    - Direct LangSmith API for root run data
    - trace_analysis functions for structured data
    - helpers.py for issue detection and handoff analysis

    Args:
        trace_id: LangSmith trace ID
        include_issues: Whether to run issue detection (adds latency)

    Returns:
        TraceForEval with all data needed for rubric evaluation

    Example:
        >>> trace = load_trace_for_eval("f264838e-...")
        >>> print(f"User: {trace.user_message}")
        >>> print(f"Response: {trace.final_response}")
        >>> print(f"Issues: {len(trace.detected_issues)}")
    """
    result = TraceForEval(trace_id=trace_id)
    client = _get_client()

    # Get root run directly for rich data extraction
    # Note: No limit - large traces (200+ runs) need full fetch to find root
    try:
        runs = list(client.list_runs(trace_id=trace_id))
        root_run = next((r for r in runs if not r.parent_run_id), None)

        if root_run:
            result.status = root_run.status or "unknown"
            result.session_id = str(root_run.session_id) if root_run.session_id else None
            result.timestamp = root_run.start_time

            # Extract user message using helpers pattern
            preview, full_msg, has_image = _extract_user_message_from_root(root_run)
            result.user_message = preview
            result.user_message_raw = full_msg
            result.has_image = has_image

            # Extract PM output preview
            result.pm_output_preview = _extract_pm_output(root_run)

            # Calculate metrics from all runs
            result.total_runs = len(runs)
            result.total_cost = sum(r.total_cost or 0 for r in runs)
            result.total_tokens = sum(r.total_tokens or 0 for r in runs)
            result.llm_calls = sum(1 for r in runs if r.run_type == "llm")
            result.tool_call_count = sum(1 for r in runs if r.run_type == "tool")

            if root_run.end_time and root_run.start_time:
                result.latency_ms = int(
                    (root_run.end_time - root_run.start_time).total_seconds() * 1000
                )

    except Exception as e:
        result.error = f"Failed to load root run: {e}"

    # Get trace overview for tree structure
    try:
        overview = get_trace_overview(trace_id)

        # Check for errors in tree
        def find_errors(node) -> list[str]:
            errors = []
            if node.error:
                errors.append(f"{node.name}: {node.error}")
            for child in node.children:
                errors.extend(find_errors(child))
            return errors

        all_errors = []
        for root in overview.run_tree:
            all_errors.extend(find_errors(root))
        if all_errors:
            result.error = "; ".join(all_errors[:3])

    except Exception as e:
        if not result.error:
            result.error = f"Failed to load overview: {e}"

    # Get tool call sequence
    try:
        tool_seq = get_tool_call_sequence(trace_id)

        result.tool_calls = [
            {
                "sequence": tc.sequence,
                "agent": tc.agent,
                "tool_name": tc.tool_name,
                "args": tc.parsed_args,
                "status": tc.status,
                "error": tc.error,
            }
            for tc in tool_seq.tool_calls
        ]

        # Extract media paths
        for tc in tool_seq.tool_calls:
            if tc.tool_name == "download_whatsapp_media":
                result.media_paths.append(tc.parsed_args.get("media_id", "media"))

        # Check for HITL interrupts
        for tc in tool_seq.tool_calls:
            if "interrupt" in tc.tool_name.lower() or "approval" in tc.tool_name.lower():
                result.interrupts.append(
                    {
                        "type": tc.tool_name,
                        "agent": tc.agent,
                        "sequence": tc.sequence,
                    }
                )

    except Exception as e:
        if not result.error:
            result.error = f"Failed to load tool sequence: {e}"

    # Get delegation graph
    try:
        graph = get_delegation_graph(trace_id)
        result.delegation_order = graph.delegation_order
        result.waves = graph.waves

        result.delegations = [
            {
                "from": d.from_agent,
                "to": d.to_agent,
                "context": d.context_passed,
                "wave": d.wave,
                "parallel_with": d.parallel_with,
            }
            for d in graph.delegations
        ]

    except Exception as e:
        if not result.error:
            result.error = f"Failed to load delegation graph: {e}"

    # Get protocol loads
    try:
        protocols = get_protocol_loads(trace_id)
        result.protocols_loaded = protocols.agent_protocols

    except Exception as e:
        if not result.error:
            result.error = f"Failed to load protocols: {e}"

    # Get final message
    try:
        final_msg = get_agent_final_message(trace_id, agent="PM")
        if not final_msg:
            final_msg = get_agent_final_message(trace_id, any_agent=True)

        if final_msg:
            result.final_response = final_msg.message
            result.final_response_agent = final_msg.agent
            result.has_numbered_options = final_msg.has_numbered_options
            result.has_open_question = final_msg.has_open_question
            result.is_approval_request = final_msg.is_approval_request
            result.mentions_error = final_msg.mentions_error
            result.mentions_success = final_msg.mentions_success

            if final_msg.token_count:
                result.total_tokens = max(result.total_tokens, final_msg.token_count)

    except Exception as e:
        if not result.error:
            result.error = f"Failed to load final message: {e}"

    # Run issue detection if requested
    if include_issues:
        try:
            # Suppress print output from detect_issues
            import io
            import sys

            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            try:
                issues = detect_issues(trace_id)
                for issue in issues:
                    result.detected_issues.append(
                        DetectedIssue(
                            type=issue.get("type", "UNKNOWN"),
                            severity=issue.get("severity", "MEDIUM"),
                            node_id=issue.get("node_id", ""),
                            node_name=issue.get("node_name", ""),
                            description=issue.get("description", ""),
                        )
                    )
            finally:
                sys.stdout = old_stdout

        except Exception:
            pass  # Issue detection is optional

        try:
            # Scan handoffs (suppress output)
            import io
            import sys

            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            try:
                handoff_issues = scan_all_handoffs(trace_id)
                for hi in handoff_issues:
                    result.handoff_issues.append(
                        HandoffAnalysis(
                            from_agent="PM",
                            to_agent=hi.get("subagent", "unknown"),
                            context_passed=hi.get("description", "")[:100],
                            has_file_path="inbox/" in hi.get("description", ""),
                            issues=[hi.get("issue", "")],
                        )
                    )
            finally:
                sys.stdout = old_stdout

        except Exception:
            pass  # Handoff analysis is optional

    return result


def format_trace_for_display(trace: TraceForEval) -> str:
    """Format trace data for Claude Code to read.

    Creates a structured markdown format optimized for LLM evaluation.

    Args:
        trace: TraceForEval from load_trace_for_eval()

    Returns:
        Formatted markdown string
    """
    lines = [
        f"# Trace: {trace.trace_id}",
        "",
        "## Metadata",
        f"- **Status**: {trace.status}",
        f"- **Timestamp**: {trace.timestamp or 'Unknown'}",
        f"- **Session ID**: {trace.session_id or 'Unknown'}",
        f"- **Latency**: {trace.latency_ms}ms ({trace.latency_ms/1000:.1f}s)",
        f"- **Cost**: ${trace.total_cost:.4f}",
        f"- **Total Runs**: {trace.total_runs}",
        f"- **LLM Calls**: {trace.llm_calls}",
        f"- **Tool Calls**: {trace.tool_call_count}",
        f"- **Tokens**: {trace.total_tokens:,}",
        "",
    ]

    # Auto-detected issues (prominent placement for evaluation)
    if trace.detected_issues:
        lines.extend([
            "## Detected Issues",
        ])
        high_issues = [i for i in trace.detected_issues if i.severity == "HIGH"]
        medium_issues = [i for i in trace.detected_issues if i.severity == "MEDIUM"]

        if high_issues:
            lines.append("### HIGH Severity")
            for issue in high_issues:
                lines.append(f"- **[{issue.type}]** {issue.node_name}: {issue.description}")

        if medium_issues:
            lines.append("### MEDIUM Severity")
            for issue in medium_issues:
                lines.append(f"- **[{issue.type}]** {issue.node_name}: {issue.description}")

        lines.append("")
    else:
        lines.extend([
            "## Detected Issues",
            "- None detected",
            "",
        ])

    if trace.error:
        lines.extend([
            "## Errors",
            "```",
            trace.error,
            "```",
            "",
        ])

    # User interaction (enhanced)
    lines.extend([
        "## User Input",
        f"- **Message**: {trace.user_message}",
        f"- **Has Image**: {trace.has_image}",
        f"- **Media Paths**: {', '.join(trace.media_paths) if trace.media_paths else 'None'}",
        "",
    ])

    # PM output preview
    if trace.pm_output_preview:
        lines.extend([
            "## PM Output (Preview)",
            f"{trace.pm_output_preview}",
            "",
        ])

    # Delegations
    lines.extend([
        "## Delegation Graph",
        f"- **Order**: {' -> '.join(trace.delegation_order) if trace.delegation_order else 'None'}",
    ])

    if trace.waves:
        for wave_num, agents in sorted(trace.waves.items()):
            lines.append(f"- **Wave {wave_num}**: {', '.join(agents)}")
    lines.append("")

    if trace.delegations:
        lines.append("### Delegation Details")
        lines.append("| From | To | Context | Wave |")
        lines.append("|------|-----|---------|------|")
        for d in trace.delegations:
            context_str = d.get("context", "")
            if isinstance(context_str, list):
                context_str = ", ".join(context_str)
            context_str = str(context_str)[:50]
            lines.append(f"| {d['from']} | {d['to']} | {context_str} | {d.get('wave', '-')} |")
        lines.append("")

    # Handoff issues
    if trace.handoff_issues:
        lines.extend([
            "### Handoff Issues",
        ])
        for hi in trace.handoff_issues:
            lines.append(f"- **{hi.to_agent}**: {'; '.join(hi.issues)}")
        lines.append("")

    # Tool calls
    lines.extend([
        "## Tool Calls",
        f"- **Total**: {len(trace.tool_calls)}",
        "",
    ])

    if trace.tool_calls:
        lines.append("### Tool Call Sequence")
        lines.append("| # | Agent | Tool | Status |")
        lines.append("|---|-------|------|--------|")
        for tc in trace.tool_calls[:20]:
            status_icon = "OK" if tc["status"] == "success" else "ERR"
            lines.append(f"| {tc['sequence']} | {tc['agent']} | {tc['tool_name']} | {status_icon} |")
        if len(trace.tool_calls) > 20:
            lines.append(f"| ... | ... | ({len(trace.tool_calls) - 20} more) | ... |")
        lines.append("")

    # Protocols
    if trace.protocols_loaded:
        lines.extend([
            "## Protocols Loaded",
            "| Agent | Protocol |",
            "|-------|----------|",
        ])
        for agent, protocol in trace.protocols_loaded.items():
            lines.append(f"| {agent} | {protocol} |")
        lines.append("")

    # HITL Interrupts
    if trace.interrupts:
        lines.extend([
            "## HITL Interrupts",
            "| Type | Agent | Sequence |",
            "|------|-------|----------|",
        ])
        for intr in trace.interrupts:
            lines.append(f"| {intr['type']} | {intr['agent']} | {intr['sequence']} |")
        lines.append("")

    # Final response
    lines.extend([
        "## Final Response",
        f"- **Agent**: {trace.final_response_agent}",
        f"- **Is Approval Request**: {trace.is_approval_request}",
        f"- **Has Open Question**: {trace.has_open_question}",
        f"- **Has Numbered Options**: {trace.has_numbered_options}",
        f"- **Mentions Error**: {trace.mentions_error}",
        f"- **Mentions Success**: {trace.mentions_success}",
        "",
        "### Response Text",
        "```",
        trace.final_response[:2000] if trace.final_response else "[No response]",
        "```" if len(trace.final_response) <= 2000 else f"... (truncated, {len(trace.final_response)} chars total)\n```",
        "",
    ])

    return "\n".join(lines)


def load_traces_for_comparison(
    trace_id_a: str,
    trace_id_b: str,
) -> tuple[TraceForEval, TraceForEval, dict[str, Any]]:
    """Load two traces for A/B comparison.

    Args:
        trace_id_a: First trace ID
        trace_id_b: Second trace ID

    Returns:
        Tuple of (trace_a, trace_b, comparison_dict)

    Example:
        >>> a, b, diff = load_traces_for_comparison("trace1", "trace2")
        >>> print(f"Latency diff: {diff['latency_diff_ms']}ms")
    """
    trace_a = load_trace_for_eval(trace_id_a)
    trace_b = load_trace_for_eval(trace_id_b)

    comparison = {
        "status_a": trace_a.status,
        "status_b": trace_b.status,
        "latency_diff_ms": trace_b.latency_ms - trace_a.latency_ms,
        "latency_pct_change": (
            ((trace_b.latency_ms - trace_a.latency_ms) / trace_a.latency_ms * 100)
            if trace_a.latency_ms else 0
        ),
        "cost_diff": trace_b.total_cost - trace_a.total_cost,
        "token_diff": trace_b.total_tokens - trace_a.total_tokens,
        "delegation_diff": {
            "a_only": [d for d in trace_a.delegation_order if d not in trace_b.delegation_order],
            "b_only": [d for d in trace_b.delegation_order if d not in trace_a.delegation_order],
            "common": [d for d in trace_a.delegation_order if d in trace_b.delegation_order],
        },
        "issues_a": len(trace_a.detected_issues),
        "issues_b": len(trace_b.detected_issues),
        "a_errors": trace_a.error,
        "b_errors": trace_b.error,
        "a_success_mentioned": trace_a.mentions_success,
        "b_success_mentioned": trace_b.mentions_success,
        "a_error_mentioned": trace_a.mentions_error,
        "b_error_mentioned": trace_b.mentions_error,
    }

    # Verdict
    latency_pct: float = float(comparison["latency_pct_change"])
    if trace_a.status != "success" and trace_b.status == "success":
        comparison["verdict"] = "FIX_SUCCESSFUL"
    elif trace_a.status == "success" and trace_b.status != "success":
        comparison["verdict"] = "REGRESSION"
    elif latency_pct < -10:
        comparison["verdict"] = f"IMPROVED ({-latency_pct:.0f}% faster)"
    elif latency_pct > 10:
        comparison["verdict"] = f"DEGRADED ({latency_pct:.0f}% slower)"
    else:
        comparison["verdict"] = "NO_SIGNIFICANT_CHANGE"

    return trace_a, trace_b, comparison


def list_recent_traces(hours: int = 24, limit: int = 10) -> list[str]:
    """List recent trace IDs for evaluation.

    Returns trace IDs sorted oldest-to-newest for sequential evaluation.

    Args:
        hours: Look back this many hours
        limit: Max traces to return

    Returns:
        List of trace IDs in chronological order (oldest first)

    Example:
        >>> traces = list_recent_traces(hours=24, limit=5)
        >>> for tid in traces:
        ...     trace = load_trace_for_eval(tid)
        ...     print(f"{tid[:12]}: {trace.status}")
    """
    from datetime import timedelta

    client = _get_client()
    start_time = datetime.now() - timedelta(hours=hours)

    runs = list(
        client.list_runs(
            project_name="autifyme-dev",
            is_root=True,
            start_time=start_time,
            limit=limit,
        )
    )

    # Sort chronologically (oldest first)
    runs.sort(key=lambda x: x.start_time or datetime.min)

    return [str(r.id) for r in runs]


def get_trace_quick_summary(trace_id: str) -> dict[str, Any]:
    """Get quick summary without full trace loading.

    Faster than load_trace_for_eval() for batch overview.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        Dict with key metrics
    """
    client = _get_client()

    runs = list(client.list_runs(trace_id=trace_id, limit=100))
    root = next((r for r in runs if not r.parent_run_id), None)

    if not root:
        return {"error": "No root run found"}

    total_ms = 0
    if root.end_time and root.start_time:
        total_ms = int((root.end_time - root.start_time).total_seconds() * 1000)

    return {
        "trace_id": trace_id,
        "status": root.status,
        "latency_ms": total_ms,
        "cost": sum(r.total_cost or 0 for r in runs),
        "tokens": sum(r.total_tokens or 0 for r in runs),
        "llm_calls": sum(1 for r in runs if r.run_type == "llm"),
        "tool_calls": sum(1 for r in runs if r.run_type == "tool"),
        "user_input": _extract_user_input(root),
        "pm_output": _extract_pm_output(root),
    }


# CLI entry point for testing
if __name__ == "__main__":
    import sys

    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python trace_loader.py <trace_id> [trace_id_b]")
        print("       python trace_loader.py --recent [hours] [limit]")
        sys.exit(1)

    if sys.argv[1] == "--recent":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        traces = list_recent_traces(hours=hours, limit=limit)
        print(f"Recent traces ({hours}h, limit {limit}):")
        for i, tid in enumerate(traces, 1):
            summary = get_trace_quick_summary(tid)
            print(f"  {i}. {tid[:12]} | {summary['status']:8} | {summary['latency_ms']/1000:.1f}s | {summary['user_input'][:50]}")
    elif len(sys.argv) >= 3:
        # Comparison mode
        trace_id_b = sys.argv[2]
        a, b, diff = load_traces_for_comparison(sys.argv[1], trace_id_b)
        print("=== TRACE A ===")
        print(format_trace_for_display(a))
        print("\n=== TRACE B ===")
        print(format_trace_for_display(b))
        print("\n=== COMPARISON ===")
        for key, value in diff.items():
            print(f"{key}: {value}")
    else:
        # Single trace mode
        trace = load_trace_for_eval(sys.argv[1])
        print(format_trace_for_display(trace))
