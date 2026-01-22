"""Helper scripts for workflow evaluation.

These are convenience functions for REPL-based evaluation.
They format LangSmith data for quick human/AI comprehension.

Usage:
    from tests.tools.evaluation.helpers import show_tree, show_node, show_handoff

    # Phase 1: Build tree
    ids = show_tree("trace_id")

    # Phase 2: Analyze nodes (use FULL UUID from ids dict)
    show_node(ids['44427c51'])  # Comprehensive node analysis

    # Phase 3: Check context handoff before recursing
    show_handoff(ids['e5c016a5'], ids['e0bdc7ae'])  # parent -> child
"""

from datetime import datetime, timedelta

from dotenv import load_dotenv
from langsmith import Client

# Import shared parsing utilities
from ..parsing import (
    extract_content_from_parts as _extract_content_from_parts,
)
from ..parsing import (
    extract_pm_output as _extract_pm_output,
)
from ..parsing import (
    extract_user_input as _extract_user_input,
)
from ..parsing import (
    parse_lc_messages,
    parse_lc_output,
)

# Initialize client lazily
_client: Client | None = None


def _safe_print(text: str) -> None:
    """Print text safely, handling console encoding issues on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback: encode to ASCII, replacing unencodable chars
        print(text.encode("ascii", errors="replace").decode("ascii"))


def _get_client() -> Client:
    """Get or create LangSmith client."""
    global _client
    if _client is None:
        load_dotenv()
        _client = Client()
    return _client


# =============================================================================
# show_tree: Hierarchical trace view
# =============================================================================


def show_tree(trace_id: str) -> dict[str, str]:
    """Print hierarchical tree of trace execution with full context.

    Shows: run IDs, names, types, timing, tokens, models, tool args, errors.
    Returns a lookup dict mapping short IDs to full IDs for drilling down.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        Dict mapping 8-char short IDs to full UUIDs for use with show_llm_detail()
    """
    client = _get_client()
    runs = list(client.list_runs(trace_id=trace_id))

    if not runs:
        print(f"No runs found for trace: {trace_id}")
        return {}

    # Build lookup for short ID -> full ID
    id_lookup: dict[str, str] = {}
    for r in runs:
        short_id = str(r.id)[:8]
        id_lookup[short_id] = str(r.id)

    # Build parent-child relationships
    children: dict[str, list] = {str(r.id): [] for r in runs}

    root = None
    for r in runs:
        if r.parent_run_id:
            parent_id = str(r.parent_run_id)
            if parent_id in children:
                children[parent_id].append(r)
        else:
            root = r

    if not root:
        print("No root run found")
        return id_lookup

    # Calculate totals
    total_cost = sum(r.total_cost or 0 for r in runs)
    total_tokens = sum(r.total_tokens or 0 for r in runs)
    llm_count = sum(1 for r in runs if r.run_type == "llm")
    tool_count = sum(1 for r in runs if r.run_type == "tool")
    total_ms = 0
    if root.end_time and root.start_time:
        total_ms = int((root.end_time - root.start_time).total_seconds() * 1000)

    # Extract user input and PM output for quick context
    user_input_preview = _extract_user_input(root)
    pm_output_preview = _extract_pm_output(root)

    # Header
    print(f"\nTRACE: {trace_id}")
    print(
        f"Status: {root.status} | Cost: ${total_cost:.4f} | Time: {total_ms / 1000:.1f}s | Tokens: {total_tokens:,}"
    )
    print(f"LLM calls: {llm_count} | Tool calls: {tool_count} | Total nodes: {len(runs)}")
    print("")
    print(f"USER: {user_input_preview}")
    print(f"PM: {pm_output_preview}")
    print("=" * 90)

    def extract_model(run) -> str:
        """Extract model name from LLM run."""
        if not run.extra:
            return ""
        model = run.extra.get("invocation_params", {}).get("model", "")
        if not model:
            model = run.extra.get("model", "")
        if not model:
            return ""
        # Clean up model names for readability
        # "models/gemini-2.5-flash-preview-05-20" -> "gemini-2.5-flash"
        model = model.replace("models/", "")
        model = model.replace("-preview", "").replace("-latest", "")
        # Remove date suffixes like "-05-20"
        parts = model.split("-")
        # Keep parts that aren't just digits
        clean_parts = [p for p in parts if not (len(p) == 2 and p.isdigit())]
        return "-".join(clean_parts)[:20]

    def extract_tool_decision(run) -> str:
        """Extract tool call decision from LLM output."""
        if not run.outputs:
            return ""
        try:
            generations = run.outputs.get("generations", [[]])
            if generations and generations[0]:
                gen = generations[0][0]
                msg = gen.get("message", {})
                tool_calls = msg.get("kwargs", {}).get("tool_calls", [])
                if tool_calls:
                    names = [tc.get("name", "?") for tc in tool_calls[:2]]
                    return " -> " + ", ".join(names)
        except Exception:
            pass
        return ""

    def extract_tool_args(run) -> str:
        """Extract key arguments from tool inputs."""
        if not run.inputs:
            return ""
        try:
            # Common delegation patterns
            if "specialist" in run.inputs:
                return f" -> {run.inputs['specialist']}"
            if "department" in run.inputs:
                return f" -> {run.inputs['department']}"
            if "agent" in run.inputs:
                return f" -> {run.inputs['agent']}"
            if "action" in run.inputs:
                return f" [{run.inputs['action']}]"
            # For other tools, show first string arg
            for k, v in run.inputs.items():
                if isinstance(v, str) and len(v) < 30 and k not in ("input", "query"):
                    return f" [{k}={v}]"
        except Exception:
            pass
        return ""

    def print_node(run, indent=0):
        prefix = "  " * indent + ("+-- " if indent > 0 else "")
        full_id = str(run.id)

        # Duration
        duration = ""
        if run.end_time and run.start_time:
            ms = int((run.end_time - run.start_time).total_seconds() * 1000)
            duration = f"{ms / 1000:.1f}s"

        # Status marker
        status = ""
        if run.status == "error":
            status = " X"
        elif run.run_type == "llm":
            status = " *"

        # Type-specific extras
        extras = ""
        if run.run_type == "llm":
            model = extract_model(run)
            tokens = f"{run.total_tokens:,}tok" if run.total_tokens else ""
            decision = extract_tool_decision(run)
            extras = f" | {model} | {tokens}{decision}" if model or tokens else ""
        elif run.run_type == "tool":
            extras = extract_tool_args(run)

        # Build line - use FULL UUID for easy copy-paste
        name = run.name[:25]
        line = f"{prefix}[{full_id}] {name} ({run.run_type})"
        if duration:
            line += f" | {duration}"
        line += extras
        line += status

        print(line)

        # Error details
        if run.status == "error" and run.error:
            error_snippet = run.error[:70].replace("\n", " ")
            print(f"{'  ' * (indent + 1)}    ERROR: {error_snippet}...")

        # Children
        child_runs = children.get(str(run.id), [])
        child_runs.sort(key=lambda x: x.start_time or datetime.min)
        for child in child_runs:
            print_node(child, indent + 1)

    print_node(root)
    print("\nLegend: * = LLM | X = Error | -> = delegates/calls")
    print("Usage: ids = show_tree('...'); show_llm_detail(ids['<short_id>'])")

    return id_lookup


# =============================================================================
# show_llm_calls: Summary of all LLM reasoning
# =============================================================================


def show_llm_calls(trace_id: str) -> None:
    """Print summary of all LLM calls in trace.

    Shows model, tokens, and key decisions for each call.

    Args:
        trace_id: LangSmith trace ID
    """
    client = _get_client()
    runs = list(client.list_runs(trace_id=trace_id, run_type="llm"))

    if not runs:
        print(f"No LLM calls found for trace: {trace_id}")
        return

    # Sort by start time
    runs.sort(key=lambda x: x.start_time or datetime.min)

    total_tokens = sum(r.total_tokens or 0 for r in runs)
    total_cost = sum(r.total_cost or 0 for r in runs)

    print(f"\nLLM CALLS: {len(runs)} total | {total_tokens:,} tokens | ${total_cost:.4f}")
    print("=" * 60)

    for i, run in enumerate(runs, 1):
        # Get parent name for context
        parent_name = "unknown"
        if run.parent_run_id:
            try:
                parent = client.read_run(run.parent_run_id)
                parent_name = parent.name
            except Exception:
                pass

        # Extract model from extra
        model = "unknown"
        if run.extra:
            model = run.extra.get("invocation_params", {}).get("model", "unknown")
            if model == "unknown":
                model = run.extra.get("model", "unknown")

        tokens = run.total_tokens or 0

        print(f"\n[{i}] {parent_name}")
        print(f"    Model: {model} | Tokens: {tokens:,}")

        # Try to extract decision/tool calls from output
        if run.outputs:
            _print_llm_decision(run.outputs)


def _print_llm_decision(outputs: dict) -> None:
    """Extract and print decision from LLM outputs."""
    try:
        # Navigate LangChain output structure
        generations = outputs.get("generations", [[]])
        if generations and generations[0]:
            gen = generations[0][0]
            msg = gen.get("message", {})
            kwargs = msg.get("kwargs", {})

            # Check for tool calls
            tool_calls = kwargs.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls[:2]:  # Show first 2
                    name = tc.get("name", "unknown")
                    args = tc.get("args", {})
                    # Summarize args
                    args_summary = ", ".join(f"{k}=..." for k in list(args.keys())[:3])
                    print(f"    Tool: {name}({args_summary})")
            else:
                # No tool calls, show content snippet
                raw_content = kwargs.get("content", "")
                # Handle multi-part content
                content = _extract_content_from_parts(raw_content)
                if content:
                    snippet = content[:100].replace("\n", " ")
                    _safe_print(f"    Output: {snippet}...")
    except Exception:
        print("    (Could not parse output)")


# =============================================================================
# show_llm_detail: Full detail for one LLM call
# =============================================================================


def show_llm_detail(run_id: str, prompt_chars: int = 500) -> None:
    """Print full detail for a specific LLM call.

    Shows system prompt, user context, and full output.

    Args:
        run_id: LangSmith run ID
        prompt_chars: Max chars to show from system prompt
    """
    client = _get_client()
    run = client.read_run(run_id)

    print(f"\n=== LLM CALL: {run.name} ===")
    print(f"ID: {run.id}")
    print(f"Status: {run.status}")
    print(f"Tokens: {run.total_tokens or 0:,}")

    # Extract system prompt from inputs
    if run.inputs and "messages" in run.inputs:
        messages = run.inputs["messages"]
        # Handle nested list
        if messages and isinstance(messages[0], list):
            messages = messages[0]

        print(f"\nSYSTEM PROMPT (first {prompt_chars} chars):")
        print("-" * 40)
        for msg in messages:
            if isinstance(msg, dict):
                # Check for SystemMessage
                msg_id = msg.get("id", [])
                if isinstance(msg_id, list) and "SystemMessage" in msg_id:
                    content = msg.get("kwargs", {}).get("content", "")
                    print(content[:prompt_chars])
                    if len(content) > prompt_chars:
                        print(f"... ({len(content) - prompt_chars} more chars)")
                    break

        # Show other messages summary
        print(f"\nOTHER MESSAGES: {len(messages) - 1} messages")

    # Show output
    print("\nOUTPUT:")
    print("-" * 40)
    if run.outputs:
        _print_llm_decision(run.outputs)

        # Show full output structure keys
        print(f"\nOutput keys: {list(run.outputs.keys())}")


# =============================================================================
# show_context_flow: Track context to specific agent
# =============================================================================


def show_context_flow(trace_id: str, target_agent: str) -> None:
    """Track how context flows to a specific agent.

    Shows what each parent passed down to identify context loss.

    Args:
        trace_id: LangSmith trace ID
        target_agent: Name of agent to trace context to
    """
    client = _get_client()
    runs = list(client.list_runs(trace_id=trace_id))

    # Find target run
    target_run = None
    for r in runs:
        if target_agent.lower() in r.name.lower():
            target_run = r
            break

    if not target_run:
        print(f"Agent '{target_agent}' not found in trace")
        return

    print(f"\nCONTEXT FLOW TO: {target_run.name}")
    print("=" * 50)

    # Build path from root to target
    path = []
    current = target_run
    by_id = {str(r.id): r for r in runs}

    while current:
        path.append(current)
        current = by_id.get(str(current.parent_run_id)) if current.parent_run_id else None

    path.reverse()

    # Show context at each step
    for i, run in enumerate(path):
        full_run = client.read_run(run.id)

        print(f"\n[{i + 1}] {run.name}")

        if full_run.inputs:
            # Summarize inputs
            for key, value in full_run.inputs.items():
                if key == "messages":
                    print(f"    {key}: {len(value)} messages")
                else:
                    val_str = str(value)[:80]
                    print(f"    {key}: {val_str}...")


# =============================================================================
# compare_traces: Before/after comparison
# =============================================================================


def compare_traces(trace_id_before: str, trace_id_after: str) -> None:
    """Compare two traces side by side.

    Useful for verifying fixes.

    Args:
        trace_id_before: First trace ID
        trace_id_after: Second trace ID
    """
    client = _get_client()

    def get_stats(trace_id):
        runs = list(client.list_runs(trace_id=trace_id))
        if not runs:
            return None

        root = next((r for r in runs if not r.parent_run_id), None)
        if not root:
            return None

        total_cost = sum(r.total_cost or 0 for r in runs)
        total_ms = 0
        if root.end_time and root.start_time:
            total_ms = int((root.end_time - root.start_time).total_seconds() * 1000)

        llm_count = sum(1 for r in runs if r.run_type == "llm")
        tool_count = sum(1 for r in runs if r.run_type == "tool")

        return {
            "status": root.status,
            "cost": total_cost,
            "latency_ms": total_ms,
            "llm_calls": llm_count,
            "tool_calls": tool_count,
            "total_runs": len(runs),
        }

    before = get_stats(trace_id_before)
    after = get_stats(trace_id_after)

    if not before or not after:
        print("Could not get stats for one or both traces")
        return

    print("\nCOMPARISON")
    print("=" * 50)
    print(f"{'':20} {'BEFORE':>12} {'AFTER':>12} {'DELTA':>12}")
    print("-" * 50)

    print(f"{'Outcome':20} {before['status']:>12} {after['status']:>12}")

    latency_delta = after["latency_ms"] - before["latency_ms"]
    latency_pct = (latency_delta / before["latency_ms"] * 100) if before["latency_ms"] else 0
    print(
        f"{'Latency':20} {before['latency_ms'] / 1000:>11.1f}s {after['latency_ms'] / 1000:>11.1f}s {latency_pct:>+11.0f}%"
    )

    cost_delta = after["cost"] - before["cost"]
    cost_pct = (cost_delta / before["cost"] * 100) if before["cost"] else 0
    print(f"{'Cost':20} ${before['cost']:>10.4f} ${after['cost']:>10.4f} {cost_pct:>+11.0f}%")

    print(f"{'LLM Calls':20} {before['llm_calls']:>12} {after['llm_calls']:>12}")
    print(f"{'Tool Calls':20} {before['tool_calls']:>12} {after['tool_calls']:>12}")

    # Verdict
    print("\nVERDICT:")
    if before["status"] != "success" and after["status"] == "success":
        print("  Fix SUCCESSFUL - failure resolved")
    elif before["status"] == "success" and after["status"] != "success":
        print("  REGRESSION - was working, now failing")
    elif before["status"] == after["status"]:
        if latency_pct < -10:
            print(f"  Performance improved by {-latency_pct:.0f}%")
        elif latency_pct > 10:
            print(f"  Performance degraded by {latency_pct:.0f}%")
        else:
            print("  No significant change")


# =============================================================================
# list_failures: Recent failed traces
# =============================================================================


def list_failures(hours: int = 24, limit: int = 10) -> None:
    """List recent failed traces.

    Args:
        hours: Look back this many hours
        limit: Max traces to show
    """
    client = _get_client()

    start_time = datetime.now() - timedelta(hours=hours)

    runs = list(
        client.list_runs(
            project_name="autifyme-dev",
            is_root=True,
            error=True,
            start_time=start_time,
            limit=limit,
        )
    )

    if not runs:
        print(f"No failures in last {hours} hours")
        return

    print(f"\nFAILURES (last {hours}h): {len(runs)} found")
    print("=" * 70)

    for r in runs:
        error_snippet = (r.error or "unknown")[:50]
        cost = r.total_cost or 0
        print(f"{str(r.id)[:12]} | ${cost:.4f} | {error_snippet}")


# =============================================================================
# list_recent: Recent traces (any status)
# =============================================================================


def list_recent(hours: int = 24, limit: int = 10) -> list[str]:
    """List recent traces in chronological order (oldest first).

    Returns trace IDs sorted oldest-to-newest so you can start evaluation
    from "the first one" and work forward.

    Args:
        hours: Look back this many hours
        limit: Max traces to show

    Returns:
        List of trace IDs in chronological order (oldest first)

    Example:
        >>> traces = list_recent(hours=24, limit=3)
        >>> # Start evaluation from first trace
        >>> show_tree(traces[0])
    """
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

    if not runs:
        print(f"No traces in last {hours} hours")
        return []

    # Sort chronologically (oldest first) for evaluation order
    runs.sort(key=lambda x: x.start_time or datetime.min)

    print(f"\nRECENT TRACES (last {hours}h): {len(runs)} found")
    print("Sorted: oldest first (start evaluation from #1)")
    print("=" * 90)

    trace_ids = []
    for i, r in enumerate(runs, 1):
        trace_id = str(r.id)
        trace_ids.append(trace_id)
        cost = r.total_cost or 0
        time_str = r.start_time.strftime("%H:%M:%S") if r.start_time else "??:??:??"
        user_preview = _extract_user_input(r)[:50]
        print(f"#{i} {trace_id[:12]} | {time_str} | {r.status:8} | ${cost:.4f} | {user_preview}")

    print("")
    print("Usage: show_tree(traces[0]) to start evaluation from first trace")

    return trace_ids


# =============================================================================
# show_node: Comprehensive single node analysis
# =============================================================================


def show_node(run_id: str) -> dict:
    """Show comprehensive analysis for a single node.

    Outputs the full INPUT/REASONING/OUTPUT template for evaluation.
    Returns structured data for programmatic use.

    Args:
        run_id: Full LangSmith run UUID

    Returns:
        Dict with parsed node data
    """
    client = _get_client()
    run = client.read_run(run_id)

    print(f"\n{'=' * 70}")
    print(f"NODE: [{str(run.id)[:8]}] {run.name}")
    print(f"Full ID: {run.id}")
    print(f"Type: {run.run_type} | Status: {run.status} | Tokens: {run.total_tokens or 0:,}")
    print(f"{'=' * 70}")

    result = {
        "id": str(run.id),
        "name": run.name,
        "type": run.run_type,
        "status": run.status,
        "tokens": run.total_tokens or 0,
        "inputs": {},
        "outputs": {},
        "tool_calls": [],
    }

    # === INPUT ANALYSIS ===
    print("\n--- INPUT (from trace) ---")

    if run.inputs:
        if "messages" in run.inputs:
            messages = parse_lc_messages(run.inputs["messages"])
            result["inputs"]["messages"] = messages

            print(f"Messages: {len(messages)}")
            for i, msg in enumerate(messages):
                content_preview = (
                    msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                )
                _safe_print(f"  [{i}] {msg['type']}: {content_preview}")

                # Show tool calls in AIMessage
                if msg["tool_calls"]:
                    print(f"      Tool calls: {len(msg['tool_calls'])}")
                    for tc in msg["tool_calls"]:
                        print(f"        -> {tc.get('name', '?')}")
        else:
            # Non-message inputs (tool inputs)
            print("Tool inputs:")
            for key, value in run.inputs.items():
                val_str = str(value)
                # Show full description for task tool (critical for evaluation)
                if key == "description" or (key == "input" and run.name == "task"):
                    _safe_print(f"  {key}: {val_str}")
                elif len(val_str) > 100:
                    _safe_print(f"  {key}: {val_str[:100]}...")
                else:
                    _safe_print(f"  {key}: {val_str}")
                result["inputs"][key] = value

    # === REASONING (for LLM nodes) ===
    if run.run_type == "llm":
        print("\n--- REASONING (LLM decision) ---")
        # Model info
        model = "unknown"
        if run.extra:
            model = run.extra.get("invocation_params", {}).get("model", "")
            if not model:
                model = run.extra.get("model", "unknown")
        print(f"Model: {model}")

    # === OUTPUT ANALYSIS ===
    print("\n--- OUTPUT ---")

    if run.outputs:
        if run.run_type == "tool":
            # Tool outputs - extract key fields for display
            result["outputs"] = run.outputs
            if isinstance(run.outputs, dict):
                for key, value in run.outputs.items():
                    val_str = str(value)
                    if len(val_str) > 200:
                        _safe_print(f"  {key}: {val_str[:200]}...")
                    else:
                        _safe_print(f"  {key}: {val_str}")
            else:
                _safe_print(f"  Result: {run.outputs}")
        else:
            # LLM outputs - parse using helper
            parsed_output = parse_lc_output(run.outputs)
            result["outputs"] = parsed_output

            if parsed_output["content"]:
                _safe_print(f"Content: {parsed_output['content']}")

            if parsed_output["tool_calls"]:
                print(f"\nTool Calls: {len(parsed_output['tool_calls'])}")
                result["tool_calls"] = parsed_output["tool_calls"]

                for tc in parsed_output["tool_calls"]:
                    name = tc.get("name", "unknown")
                    args = tc.get("args", {})
                    print(f"\n  -> {name}")

                    # Show all args - NO truncation
                    for k, v in args.items():
                        _safe_print(f"     {k}: {v}")

                    # Mark if this is a task delegation
                    if name == "task":
                        subagent = args.get("subagent_type", args.get("specialist", "unknown"))
                        print(f"     [HANDOFF CHECK REQUIRED -> {subagent}]")

    print(f"\n{'=' * 70}")

    return result


# =============================================================================
# show_handoff: Context handoff analysis between parent and child
# =============================================================================


def show_handoff(parent_run_id: str, child_run_id: str) -> dict:
    """Analyze context handoff between parent and child nodes.

    Critical for evaluating if parent passed necessary context to child.

    Args:
        parent_run_id: Full UUID of parent run
        child_run_id: Full UUID of child run

    Returns:
        Dict with handoff analysis
    """
    client = _get_client()
    parent = client.read_run(parent_run_id)
    child = client.read_run(child_run_id)

    print(f"\n{'=' * 70}")
    print("CONTEXT HANDOFF ANALYSIS")
    print(f"{'=' * 70}")
    print(f"Parent: [{str(parent.id)[:8]}] {parent.name}")
    print(f"Child:  [{str(child.id)[:8]}] {child.name}")
    print(f"{'=' * 70}")

    result = {
        "parent_id": str(parent.id),
        "child_id": str(child.id),
        "parent_had": {},
        "parent_passed": {},
        "child_received": {},
        "child_output": {},
        "issues": [],
    }

    # === WHAT PARENT HAD ===
    print("\n--- WHAT PARENT HAD AVAILABLE ---")

    parent_context = {}

    # Check parent's input messages for context
    if parent.inputs and "messages" in parent.inputs:
        messages = parse_lc_messages(parent.inputs["messages"])
        for msg in messages:
            # Look for image paths, URLs, etc.
            content = msg.get("content", "")
            if "inbox/" in content or "/tmp/" in content or "http" in content:
                parent_context["media_reference"] = content[:100]
            if msg["type"] == "HumanMessage":
                parent_context["user_message"] = content[:100]

    # Check parent's tool results from previous calls
    if parent.inputs and "messages" in parent.inputs:
        messages = parse_lc_messages(parent.inputs["messages"])
        for msg in messages:
            if msg["type"] == "ToolMessage":
                content = msg.get("content", "")
                # Look for file paths in tool results
                if "storage_path" in content or "inbox/" in content:
                    parent_context["file_from_tool"] = content[:150]

    for k, v in parent_context.items():
        _safe_print(f"  {k}: {v}")
        result["parent_had"][k] = v

    if not parent_context:
        print("  (No specific context detected)")

    # === WHAT PARENT PASSED ===
    print("\n--- WHAT PARENT PASSED IN TOOL CALL ---")

    passed_context = {}

    # Find the specific tool call that led to this child
    # by matching child's input subagent_type
    child_subagent = None
    if child.inputs:
        child_input = child.inputs.get("input", {})
        if isinstance(child_input, dict):
            child_subagent = child_input.get("subagent_type")
        # Also try direct subagent_type in inputs
        if not child_subagent:
            child_subagent = child.inputs.get("subagent_type")

    # Debug: show what we detected
    if child_subagent:
        print(f"  (Matched to: {child_subagent})")

    if parent.outputs:
        parsed = parse_lc_output(parent.outputs)
        for tc in parsed.get("tool_calls", []):
            args = tc.get("args", {})
            # Match the specific task call by subagent_type
            if tc.get("name") == "task":
                tc_subagent = args.get("subagent_type", "unknown")
                # If we know child's subagent, only show matching call
                if child_subagent and tc_subagent != child_subagent:
                    continue

                passed_context["subagent_type"] = tc_subagent
                passed_context["description"] = args.get("description", "")

                # Check for key context fields
                for key in ["image_path", "file_path", "url", "product_id", "context"]:
                    if key in args:
                        passed_context[key] = str(args[key])
                break  # Found the matching call

    # If couldn't get from parent LLM outputs, try extracting from child's inputs directly
    if not passed_context and child.inputs:
        import ast
        import json

        child_input = child.inputs.get("input", {})
        # Parse string input if needed
        if isinstance(child_input, str):
            try:
                child_input = ast.literal_eval(child_input)
            except (ValueError, SyntaxError):
                import contextlib

                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    child_input = json.loads(child_input)

        if isinstance(child_input, dict):
            passed_context["subagent_type"] = child_input.get("subagent_type", "unknown")
            passed_context["description"] = child_input.get("description", "")

    for k, v in passed_context.items():
        _safe_print(f"  {k}: {v}")
        result["parent_passed"][k] = v

    if not passed_context:
        print("  (Could not extract tool call args)")

    # === WHAT CHILD RECEIVED ===
    print("\n--- WHAT CHILD RECEIVED ---")

    child_received = {}

    if child.inputs:
        for k, v in child.inputs.items():
            if k != "messages":  # Skip raw messages
                val_str = str(v)
                # Show full content for key fields
                if k in ("input", "description"):
                    child_received[k] = val_str
                else:
                    child_received[k] = val_str[:100] if len(val_str) > 100 else val_str

        # Also check first message content
        if "messages" in child.inputs:
            messages = parse_lc_messages(child.inputs["messages"])
            if messages:
                first_human = next((m for m in messages if m["type"] == "HumanMessage"), None)
                if first_human:
                    child_received["first_message"] = first_human["content"][:150]

    for k, v in child_received.items():
        _safe_print(f"  {k}: {v}")
        result["child_received"][k] = v

    if not child_received:
        print("  (No inputs found)")

    # === WHAT CHILD OUTPUT (the result) ===
    print("\n--- WHAT CHILD OUTPUT ---")

    child_output = {}

    if child.outputs:
        # For task tools, output is usually in 'output' key
        if "output" in child.outputs:
            output_val = child.outputs["output"]
            if isinstance(output_val, dict):
                # Specialist returns structured output
                for k, v in output_val.items():
                    child_output[k] = str(v)
            else:
                child_output["output"] = str(output_val)
        else:
            # Raw outputs
            for k, v in child.outputs.items():
                child_output[k] = str(v)

    for k, v in child_output.items():
        _safe_print(f"  {k}: {v}")
        result["child_output"] = child_output

    if not child_output:
        print("  (No output found)")

    # === HANDOFF QUALITY ASSESSMENT ===
    print("\n--- HANDOFF QUALITY ---")

    issues = []

    # Check for image/file path passing
    if "media_reference" in parent_context or "file_from_tool" in parent_context:
        # Parent had file, check if child got it
        child_has_file = any(
            "inbox/" in str(v) or "/tmp/" in str(v) or "storage_path" in str(v)
            for v in child_received.values()
        )
        passed_has_file = any(
            "inbox/" in str(v) or "/tmp/" in str(v) for v in passed_context.values()
        )

        if not passed_has_file:
            issues.append("Image/file path NOT in tool args")
        if not child_has_file:
            issues.append("Image/file path NOT received by child")

    # Check description clarity
    if "description" in passed_context:
        desc = passed_context["description"]
        if len(desc) < 20:
            issues.append("Task description very short - may lack context")

    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  [!] {issue}")
        result["issues"] = issues
        print("\nHANDOFF QUALITY: PARTIAL/BROKEN")
    else:
        print("No obvious issues detected")
        print("\nHANDOFF QUALITY: OK (verify manually)")

    print(f"\n{'=' * 70}")

    return result


# =============================================================================
# show_orchestrator_flow: Show orchestrator's decisions chronologically
# =============================================================================


def show_orchestrator_flow(trace_id: str) -> list[dict]:
    """Show orchestrator's decisions in chronological order.

    Useful for understanding the orchestration flow in any multi-agent system.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        List of orchestrator decisions
    """
    client = _get_client()
    runs = list(client.list_runs(trace_id=trace_id))

    # Find root (orchestrator)
    root = next((r for r in runs if not r.parent_run_id), None)
    if not root:
        _safe_print("No root found")
        return []

    # Find LLM calls that are direct children of orchestrator's model chains
    orchestrator_llm_calls = []
    by_id = {str(r.id): r for r in runs}

    for r in runs:
        if r.run_type == "llm" and r.parent_run_id:
            parent = by_id.get(str(r.parent_run_id))
            if (
                parent
                and parent.name == "model"
                and parent.parent_run_id
                and str(parent.parent_run_id) == str(root.id)
            ):
                # Grandparent is root - this is an orchestrator LLM call
                orchestrator_llm_calls.append(r)

    orchestrator_llm_calls.sort(key=lambda x: x.start_time or datetime.min)

    _safe_print(f"\n{'=' * 70}")
    _safe_print("ORCHESTRATOR DECISION FLOW")
    _safe_print(f"Trace: {trace_id}")
    _safe_print(f"{'=' * 70}")

    decisions = []

    for i, run in enumerate(orchestrator_llm_calls, 1):
        _safe_print(f"\n[{i}] Decision - {str(run.id)[:8]}")
        _safe_print(f"    Full ID: {run.id}")
        _safe_print(f"    Tokens: {run.total_tokens or 0:,}")

        decision = {
            "index": i,
            "id": str(run.id),
            "tokens": run.total_tokens or 0,
            "tool_calls": [],
        }

        # Parse output for tool calls
        if run.outputs:
            parsed = parse_lc_output(run.outputs)
            for tc in parsed.get("tool_calls", []):
                name = tc.get("name", "unknown")
                args = tc.get("args", {})

                call_info = {"name": name, "args_summary": {}}

                if name == "task":
                    subagent = args.get("subagent_type", args.get("specialist", "?"))
                    desc = args.get("description", "")
                    _safe_print(f"    -> task({subagent})")
                    _safe_print(f"       desc: {desc}")
                    call_info["args_summary"]["subagent"] = subagent
                    call_info["args_summary"]["description"] = desc
                else:
                    _safe_print(f"    -> {name}")
                    # Show all args - NO truncation
                    for k, v in args.items():
                        _safe_print(f"       {k}: {v}")
                        call_info["args_summary"][k] = str(v)

                decision["tool_calls"].append(call_info)

        decisions.append(decision)

    _safe_print(f"\n{'=' * 70}")
    _safe_print(f"Total orchestrator decisions: {len(decisions)}")

    return decisions


# Backward compatibility alias
show_pm_flow = show_orchestrator_flow


# =============================================================================
# scan_all_handoffs: Auto-detect broken context handoffs
# =============================================================================


def scan_all_handoffs(trace_id: str) -> list[dict]:
    """Scan all task delegations and list them with context analysis.

    Finds every task(subagent) delegation and shows what was passed.
    Checks for common issues like missing file paths.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        List of handoff issues: [{child_id, subagent, issue, severity}]
    """
    client = _get_client()
    runs = list(client.list_runs(trace_id=trace_id))

    # Find all task tool calls
    task_runs = [r for r in runs if r.run_type == "tool" and r.name == "task"]

    print(f"\n{'=' * 70}")
    print(f"HANDOFF SCAN: {trace_id}")
    print(f"Found {len(task_runs)} task delegations")
    print(f"{'=' * 70}")

    issues = []

    for task_run in task_runs:
        # Extract subagent type and description from task input
        # LangSmith stores tool inputs in various formats - check multiple locations
        subagent = "unknown"
        task_description = ""
        if task_run.inputs:
            # Try 1: Direct keys in inputs (common for StructuredTool)
            subagent = task_run.inputs.get("subagent_type", "unknown")
            task_description = task_run.inputs.get("description", "")

            # Try 2: Nested under 'input' dict or string
            if subagent == "unknown":
                task_input = task_run.inputs.get("input", {})
                if isinstance(task_input, dict):
                    subagent = task_input.get("subagent_type", subagent)
                    task_description = task_input.get("description", task_description)
                elif isinstance(task_input, str):
                    # Try 3: Parse string input (Python repr or JSON)
                    import ast
                    import json

                    try:
                        # Try Python literal first (single quotes from LangSmith)
                        parsed = ast.literal_eval(task_input)
                        if isinstance(parsed, dict):
                            subagent = parsed.get("subagent_type", subagent)
                            task_description = parsed.get("description", task_description)
                    except (ValueError, SyntaxError):
                        # Fall back to JSON
                        try:
                            parsed = json.loads(task_input)
                            if isinstance(parsed, dict):
                                subagent = parsed.get("subagent_type", subagent)
                                task_description = parsed.get("description", task_description)
                        except (json.JSONDecodeError, TypeError):
                            pass

            # Try 4: Check prompt/description directly (some tools store differently)
            if subagent == "unknown":
                subagent = task_run.inputs.get(
                    "specialist", task_run.inputs.get("agent", "unknown")
                )
            if not task_description:
                task_description = task_run.inputs.get("prompt", task_run.inputs.get("task", ""))

        # Check if file path was passed in task description
        task_has_file = bool(
            "inbox/" in task_description
            or "pending/" in task_description
            or "products/" in task_description
            or "storage_path" in task_description
        )

        # Check child output for signs of missing context
        child_asked_for_context = False
        child_output_text = ""
        if task_run.outputs:
            output = task_run.outputs.get("output", {})
            if isinstance(output, dict):
                # Check nested messages for "provide" or "need" keywords
                messages = output.get("messages", [])
                for msg in messages:
                    if isinstance(msg, dict):
                        content = msg.get("content", "")
                        if isinstance(content, str):
                            child_output_text = content
                            if any(
                                kw in content.lower()
                                for kw in [
                                    "provide the",
                                    "need the",
                                    "please provide",
                                    "storage_path",
                                    "image path",
                                    "file path",
                                ]
                            ):
                                child_asked_for_context = True

        # Determine issue
        issue_found = None
        severity = "OK"

        if child_asked_for_context:
            issue_found = f"Child asked for missing context: '{child_output_text}'"
            severity = "HIGH"

        # Print result - always show what was delegated
        status_icon = "[X]" if issue_found else "[OK]"
        file_marker = " [+file]" if task_has_file else ""
        print(f"\n{status_icon} {subagent}{file_marker}")
        print(f"    Task ID: {task_run.id}")
        _safe_print(f"    Description: {task_description}")
        if issue_found:
            print(f"    ISSUE: {issue_found}")
            issues.append(
                {
                    "child_id": str(task_run.id),
                    "subagent": subagent,
                    "issue": issue_found,
                    "severity": severity,
                    "description": task_description,
                }
            )

    print(f"\n{'=' * 70}")
    if issues:
        print(f"FOUND {len(issues)} HANDOFF ISSUE(S)")
        for i in issues:
            print(f"  - [{i['severity']}] {i['subagent']}: {i['issue']}")
    else:
        print("No handoff issues detected")
    print(f"{'=' * 70}")

    return issues


# =============================================================================
# Workflow Window: Bounded trace retrieval for multi-turn evaluation
# =============================================================================


def get_workflow_window(
    trace_id: str,
    hours_before: float = 2.0,
    hours_after: float = 2.0,
    max_traces: int = 20,
    session_gap_minutes: int = 60,
) -> list[dict]:
    """Get traces in a bounded window around the given trace.

    This is the correct abstraction for multi-turn evaluation:
    - Given a starting trace, find related traces in a reasonable time window
    - Respects that threads/sessions can span lifetime of conversations
    - Returns bounded results for efficient processing
    - Optionally detects session boundaries via time gaps

    IMPORTANT: Thread/session IDs can represent lifetime conversations.
    This function provides bounded access instead of loading entire history.

    Args:
        trace_id: Starting LangSmith trace ID
        hours_before: Hours to look back (default: 2)
        hours_after: Hours to look forward (default: 2)
        max_traces: Maximum traces to return (default: 20)
        session_gap_minutes: Gap (in minutes) that indicates session boundary (default: 60)

    Returns:
        List of trace info dicts in chronological order, with session boundary markers:
        [
            {"trace_id": "...", "start_time": datetime, "is_starting_trace": bool, "session_break_before": bool},
            ...
        ]

    Example:
        >>> # Get workflow context around a trace
        >>> window = get_workflow_window('abc123')
        >>> for t in window:
        ...     marker = "*" if t['is_starting_trace'] else " "
        ...     break_marker = "---" if t.get('session_break_before') else ""
        ...     print(f"{break_marker}{marker} {t['trace_id'][:8]}: {t['start_time']}")

        >>> # Narrow window for recent workflow
        >>> window = get_workflow_window('abc123', hours_before=0.5, hours_after=0.5)
    """
    client = _get_client()
    run = client.read_run(trace_id)

    if not run.session_id:
        print(f"No session_id found for trace: {trace_id}")
        return []

    if not run.start_time:
        print(f"No start_time found for trace: {trace_id}")
        return []

    # Calculate time window centered on source trace
    source_time = run.start_time
    window_start = source_time - timedelta(hours=hours_before)
    window_end = source_time + timedelta(hours=hours_after)

    # Format times for LangSmith filter (ISO format)
    start_iso = window_start.isoformat()
    end_iso = window_end.isoformat()

    # Query with higher limit to ensure we capture traces around source
    # LangSmith returns arbitrary subset when limited, so we fetch more
    # and then trim to max_traces centered on source
    query_limit = max(max_traces * 3, 60)

    session_runs = list(
        client.list_runs(
            project_name="autifyme-dev",
            is_root=True,
            filter=f'and(eq(session_id, "{run.session_id}"), gte(start_time, "{start_iso}"), lte(start_time, "{end_iso}"))',
            limit=query_limit,
        )
    )

    if not session_runs:
        return []

    # Sort by start_time (ascending = chronological)
    session_runs.sort(key=lambda x: x.start_time or datetime.min)

    # Find source trace position and return window centered on it
    source_idx = None
    for i, r in enumerate(session_runs):
        if str(r.id) == trace_id or str(r.trace_id) == trace_id:
            source_idx = i
            break

    if source_idx is not None and len(session_runs) > max_traces:
        # Center window on source trace
        half_window = max_traces // 2
        start_idx = max(0, source_idx - half_window)
        end_idx = min(len(session_runs), start_idx + max_traces)

        # Adjust if we hit the end
        if end_idx - start_idx < max_traces:
            start_idx = max(0, end_idx - max_traces)

        session_runs = session_runs[start_idx:end_idx]

    # Build result with session boundary detection and HITL extraction
    # Import here to avoid circular imports
    from tests.tools.trace_analysis import _extract_hitl_decisions

    result = []
    prev_time = None
    gap_threshold = timedelta(minutes=session_gap_minutes)

    # First pass: build basic trace info and identify PM workflow traces
    trace_list = []
    for r in session_runs:
        is_starting = str(r.id) == trace_id or str(r.id).startswith(trace_id)

        # Detect session break (large gap from previous trace)
        session_break = False
        if prev_time and r.start_time:
            gap = r.start_time - prev_time
            if gap > gap_threshold:
                session_break = True

        # Classify trace type by checking for user input
        inputs = r.inputs or {}
        has_user_input = False
        user_message_preview = None

        if "messages" in inputs:
            msgs = inputs["messages"]
            if msgs and len(msgs) > 0:
                last = msgs[-1]
                if isinstance(last, dict):
                    content = last.get("content", "")
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("type") == "text":
                                text = c.get("text", "")
                                if text and not text.startswith("("):
                                    has_user_input = True
                                    user_message_preview = text[:100]
                                break
                    elif content and isinstance(content, str):
                        has_user_input = True
                        user_message_preview = content[:100]

        # Check if this is an approval analyzer trace (has BatchApprovalResponse output)
        is_approval_analyzer = False
        outputs = r.outputs or {}
        if isinstance(outputs, dict):
            if "responses" in outputs and "reasoning" in outputs:
                is_approval_analyzer = True
            elif "output" in outputs:
                inner = outputs.get("output", {})
                if isinstance(inner, dict) and "responses" in inner and "reasoning" in inner:
                    is_approval_analyzer = True

        trace_list.append(
            {
                "run": r,
                "trace_id": str(r.id),
                "start_time": r.start_time,
                "end_time": r.end_time,
                "is_starting_trace": is_starting,
                "session_break_before": session_break,
                "status": r.status,
                "error": r.error if r.error else None,
                "has_user_input": has_user_input,
                "user_message": user_message_preview,
                "is_approval_analyzer": is_approval_analyzer,
                "hitl_decisions": None,  # Will be populated below
            }
        )

        prev_time = r.end_time or r.start_time

    # Second pass: Extract HITL decisions for PM workflow traces
    # HITL decisions come from approval analyzer traces that follow an interrupt
    for i, t in enumerate(trace_list):
        if t["is_approval_analyzer"]:
            # This is an approval analyzer trace - extract the decisions
            # and attach them to the PREVIOUS workflow trace
            outputs = t["run"].outputs or {}
            approval_response = None
            if isinstance(outputs, dict):
                if "responses" in outputs and "reasoning" in outputs:
                    approval_response = outputs
                elif "output" in outputs:
                    inner = outputs.get("output", {})
                    if isinstance(inner, dict) and "responses" in inner:
                        approval_response = inner

            if approval_response:
                decisions = []
                responses = approval_response.get("responses", [])
                reasoning = approval_response.get("reasoning", "")

                for idx, resp in enumerate(responses):
                    if isinstance(resp, dict):
                        resp_type = resp.get("type", "")
                        user_message = resp.get("user_message")
                        action = "approved" if resp_type == "accept" else "rejected"
                        decisions.append(
                            {
                                "index": idx,
                                "action": action,
                                "user_message": user_message,
                            }
                        )

                # Attach to this approval analyzer trace for visibility
                t["hitl_decisions"] = decisions
                t["hitl_reasoning"] = reasoning

                # Also try to find and annotate the preceding workflow trace
                if i > 0:
                    for j in range(i - 1, -1, -1):
                        prev_t = trace_list[j]
                        if prev_t["has_user_input"] and not prev_t["is_approval_analyzer"]:
                            # This is the workflow trace that triggered the HITL
                            prev_t["hitl_response"] = {
                                "decisions": decisions,
                                "reasoning": reasoning,
                            }
                            break

    # Build final result (exclude internal 'run' object)
    for t in trace_list:
        del t["run"]
        result.append(t)

    print(f"Workflow window: {len(result)} traces in {hours_before}h before / {hours_after}h after")
    if any(t.get("session_break_before") for t in result):
        print(f"  (session breaks detected - gaps > {session_gap_minutes} min)")

    # Count HITL decisions found
    hitl_count = sum(1 for t in result if t.get("hitl_decisions"))
    if hitl_count:
        print(f"  (found {hitl_count} HITL approval responses)")

    return result


# =============================================================================
# prev_trace / next_trace: Efficient O(1) thread navigation
# =============================================================================


def prev_trace(trace_id: str, session_gap_minutes: int = 60) -> str | None:
    """Get previous trace in same session, or None if first.

    Uses time-bounded query for O(1) performance instead of loading entire session.
    Optionally respects session boundaries (large time gaps).

    Args:
        trace_id: LangSmith trace ID
        session_gap_minutes: Gap that indicates session boundary (skips across boundaries)

    Returns:
        Previous trace ID, or None if this is the first trace in session/window

    Example:
        >>> prev_id = prev_trace('a194cf05')
        >>> if prev_id:
        ...     show_orchestrator_flow(prev_id)
    """
    client = _get_client()
    run = client.read_run(trace_id)

    if not run.session_id:
        print(f"No session_id found for trace: {trace_id}")
        return None

    if not run.start_time:
        print(f"No start_time found for trace: {trace_id}")
        return None

    # Query for traces BEFORE current, ordered by time descending (most recent first)
    # Only look back a reasonable window (24 hours) to avoid scanning entire history
    window_start = run.start_time - timedelta(hours=24)
    start_iso = window_start.isoformat()
    current_iso = run.start_time.isoformat()

    # Get traces before current time, limit to small batch
    prev_runs = list(
        client.list_runs(
            project_name="autifyme-dev",
            is_root=True,
            filter=f'and(eq(session_id, "{run.session_id}"), gte(start_time, "{start_iso}"), lt(start_time, "{current_iso}"))',
            limit=10,
        )
    )

    if not prev_runs:
        print("This is the first trace in the session (within 24h window)")
        return None

    # Sort descending to get most recent first
    prev_runs.sort(key=lambda x: x.start_time or datetime.min, reverse=True)

    # Check for session boundary
    prev_run = prev_runs[0]
    if prev_run.end_time and run.start_time:
        gap = run.start_time - (prev_run.end_time or prev_run.start_time)
        if gap > timedelta(minutes=session_gap_minutes):
            print(
                f"Session boundary detected (gap: {gap}). Previous trace is from different session."
            )
            print(f"  Use prev_trace('{trace_id}', session_gap_minutes=0) to ignore boundaries.")
            return None

    print(f"Previous trace: {prev_run.id}")
    print(f"  Time: {prev_run.start_time}")
    return str(prev_run.id)


def next_trace(trace_id: str, session_gap_minutes: int = 60) -> str | None:
    """Get next trace in same session, or None if last.

    Uses time-bounded query for O(1) performance instead of loading entire session.
    Optionally respects session boundaries (large time gaps).

    Args:
        trace_id: LangSmith trace ID
        session_gap_minutes: Gap that indicates session boundary (skips across boundaries)

    Returns:
        Next trace ID, or None if this is the last trace in session/window

    Example:
        >>> next_id = next_trace('f264838e')
        >>> if next_id:
        ...     show_orchestrator_flow(next_id)
        ...     # See what user did after PM asked for direction
    """
    client = _get_client()
    run = client.read_run(trace_id)

    if not run.session_id:
        print(f"No session_id found for trace: {trace_id}")
        return None

    if not run.start_time:
        print(f"No start_time found for trace: {trace_id}")
        return None

    # Query for traces AFTER current, ordered by time ascending (earliest first)
    # Only look forward a reasonable window (24 hours)
    window_end = run.start_time + timedelta(hours=24)
    current_iso = run.start_time.isoformat()
    end_iso = window_end.isoformat()

    # Get traces after current time, limit to small batch
    next_runs = list(
        client.list_runs(
            project_name="autifyme-dev",
            is_root=True,
            filter=f'and(eq(session_id, "{run.session_id}"), gt(start_time, "{current_iso}"), lte(start_time, "{end_iso}"))',
            limit=10,
        )
    )

    if not next_runs:
        print("This is the last trace in the session (within 24h window)")
        return None

    # Sort ascending to get earliest first
    next_runs.sort(key=lambda x: x.start_time or datetime.min)

    # Check for session boundary
    next_run = next_runs[0]
    current_end = run.end_time or run.start_time
    if current_end and next_run.start_time:
        gap = next_run.start_time - current_end
        if gap > timedelta(minutes=session_gap_minutes):
            print(f"Session boundary detected (gap: {gap}). Next trace is from different session.")
            print(f"  Use next_trace('{trace_id}', session_gap_minutes=0) to ignore boundaries.")
            return None

    print(f"Next trace: {next_run.id}")
    print(f"  Time: {next_run.start_time}")
    return str(next_run.id)


# =============================================================================
# detect_issues: Auto-detect common trace problems
# =============================================================================


def detect_issues(trace_id: str) -> list[dict]:
    """Auto-detect common issues in a trace.

    Checks for:
    - Broken handoffs (file paths not passed)
    - Failed/errored runs
    - Tool loops (same tool called 3+ times in sequence)
    - High token usage (>50k tokens in single LLM call)
    - Child agents asking for missing context

    Args:
        trace_id: LangSmith trace ID

    Returns:
        List of issues: [{type, severity, node_id, description}]
    """
    client = _get_client()
    runs = list(client.list_runs(trace_id=trace_id))

    print(f"\n{'=' * 70}")
    print(f"ISSUE DETECTION: {trace_id}")
    print(f"Scanning {len(runs)} nodes...")
    print(f"{'=' * 70}")

    issues = []

    # 1. Check for failed/errored runs
    failed_runs = [r for r in runs if r.status == "error" or r.error]
    for r in failed_runs:
        issues.append(
            {
                "type": "ERROR",
                "severity": "HIGH",
                "node_id": str(r.id),
                "node_name": r.name,
                "description": f"Run failed: {r.error or 'unknown error'}",
            }
        )

    # 2. Check for high token usage
    high_token_runs = [r for r in runs if r.run_type == "llm" and (r.total_tokens or 0) > 50000]
    for r in high_token_runs:
        issues.append(
            {
                "type": "HIGH_TOKENS",
                "severity": "MEDIUM",
                "node_id": str(r.id),
                "node_name": r.name,
                "description": f"High token usage: {r.total_tokens:,} tokens",
            }
        )

    # 3. Check for tool loops (same tool called 3+ times by same agent)
    # Group runs by parent
    by_parent: dict[str, list] = {}
    for r in runs:
        if r.run_type == "tool" and r.parent_run_id:
            parent_key = str(r.parent_run_id)
            if parent_key not in by_parent:
                by_parent[parent_key] = []
            by_parent[parent_key].append(r)

    for parent_id, tool_runs in by_parent.items():
        tool_counts: dict[str, int] = {}
        for tr in tool_runs:
            tool_counts[tr.name] = tool_counts.get(tr.name, 0) + 1
        for tool_name, count in tool_counts.items():
            if count >= 3 and tool_name not in ("write_todos", "SummarizationMiddleware"):
                issues.append(
                    {
                        "type": "TOOL_LOOP",
                        "severity": "MEDIUM",
                        "node_id": parent_id,
                        "node_name": tool_name,
                        "description": f"Tool '{tool_name}' called {count} times - possible loop",
                    }
                )

    # 4. Scan handoffs (reuse scan_all_handoffs logic but quieter)
    task_runs = [r for r in runs if r.run_type == "tool" and r.name == "task"]

    for task_run in task_runs:
        # Check child output for signs of missing context
        if task_run.outputs:
            output = task_run.outputs.get("output", {})
            if isinstance(output, dict):
                messages = output.get("messages", [])
                for msg in messages:
                    if isinstance(msg, dict):
                        content = msg.get("content", "")
                        if isinstance(content, str) and any(
                            kw in content.lower()
                            for kw in [
                                "provide the",
                                "need the",
                                "please provide",
                                "storage_path",
                                "image path",
                                "file path",
                            ]
                        ):
                            subagent = "unknown"
                            if task_run.inputs:
                                # Try direct key first, then nested
                                subagent = task_run.inputs.get("subagent_type", "unknown")
                                if subagent == "unknown":
                                    task_input = task_run.inputs.get("input", {})
                                    if isinstance(task_input, dict):
                                        subagent = task_input.get("subagent_type", "unknown")

                            issues.append(
                                {
                                    "type": "MISSING_CONTEXT",
                                    "severity": "HIGH",
                                    "node_id": str(task_run.id),
                                    "node_name": f"task({subagent})",
                                    "description": f"Child asked for missing context: {content}",
                                }
                            )
                            break

    # Print summary
    print(f"\n--- ISSUES FOUND: {len(issues)} ---\n")

    if not issues:
        print("No issues detected. Trace looks healthy.")
    else:
        # Group by severity
        high = [i for i in issues if i["severity"] == "HIGH"]
        medium = [i for i in issues if i["severity"] == "MEDIUM"]

        if high:
            print("HIGH SEVERITY:")
            for i in high:
                print(f"  [{i['type']}] {i['node_name']}: {i['description']}")

        if medium:
            print("\nMEDIUM SEVERITY:")
            for i in medium:
                print(f"  [{i['type']}] {i['node_name']}: {i['description']}")

    print(f"\n{'=' * 70}")

    return issues
