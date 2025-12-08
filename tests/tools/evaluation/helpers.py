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

# Initialize client lazily
_client: Client | None = None


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
    by_id = {str(r.id): r for r in runs}
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

    # Header
    print(f"\nTRACE: {trace_id}")
    print(f"Status: {root.status} | Cost: ${total_cost:.4f} | Time: {total_ms/1000:.1f}s | Tokens: {total_tokens:,}")
    print(f"LLM calls: {llm_count} | Tool calls: {tool_count} | Total nodes: {len(runs)}")
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
            duration = f"{ms/1000:.1f}s"

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
                content = kwargs.get("content", "")
                if content:
                    snippet = content[:100].replace("\n", " ")
                    print(f"    Output: {snippet}...")
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
        if current.parent_run_id:
            current = by_id.get(str(current.parent_run_id))
        else:
            current = None

    path.reverse()

    # Show context at each step
    for i, run in enumerate(path):
        full_run = client.read_run(run.id)

        print(f"\n[{i+1}] {run.name}")

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

    print(f"\nCOMPARISON")
    print("=" * 50)
    print(f"{'':20} {'BEFORE':>12} {'AFTER':>12} {'DELTA':>12}")
    print("-" * 50)

    print(f"{'Outcome':20} {before['status']:>12} {after['status']:>12}")

    latency_delta = after["latency_ms"] - before["latency_ms"]
    latency_pct = (latency_delta / before["latency_ms"] * 100) if before["latency_ms"] else 0
    print(f"{'Latency':20} {before['latency_ms']/1000:>11.1f}s {after['latency_ms']/1000:>11.1f}s {latency_pct:>+11.0f}%")

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

    runs = list(client.list_runs(
        project_name="autifyme-dev",
        is_root=True,
        error=True,
        start_time=start_time,
        limit=limit,
    ))

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


def list_recent(hours: int = 24, limit: int = 10) -> None:
    """List recent traces.

    Args:
        hours: Look back this many hours
        limit: Max traces to show
    """
    client = _get_client()

    start_time = datetime.now() - timedelta(hours=hours)

    runs = list(client.list_runs(
        project_name="autifyme-dev",
        is_root=True,
        start_time=start_time,
        limit=limit,
    ))

    if not runs:
        print(f"No traces in last {hours} hours")
        return

    print(f"\nRECENT TRACES (last {hours}h): {len(runs)} found")
    print("=" * 70)

    for r in runs:
        cost = r.total_cost or 0
        print(f"{str(r.id)[:12]} | {r.status:8} | ${cost:.4f} | {r.name[:30]}")


# =============================================================================
# parse_lc_messages: Parse LangChain serialization format
# =============================================================================


def parse_lc_messages(messages: list) -> list[dict]:
    """Parse LangChain message serialization format into clean dicts.

    LangChain serializes messages as: {lc: 1, type: "constructor", id: [...], kwargs: {...}}
    This function extracts the useful parts.

    Args:
        messages: Raw messages from run.inputs['messages']

    Returns:
        List of dicts with keys: type, content, tool_calls
    """
    # Handle nested list (common in LangSmith)
    if messages and isinstance(messages[0], list):
        messages = messages[0]

    parsed = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue

        # Extract message type from id field
        msg_id = msg.get("id", [])
        msg_type = "unknown"
        if isinstance(msg_id, list) and msg_id:
            # id is like ["langchain_core", "messages", "HumanMessage"]
            msg_type = msg_id[-1] if msg_id else "unknown"

        # Extract content and tool_calls from kwargs
        kwargs = msg.get("kwargs", {})
        content = kwargs.get("content", "")
        tool_calls = kwargs.get("tool_calls", [])

        # Handle multimodal content (list of parts)
        if isinstance(content, list):
            text_parts = []
            has_image = False
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        has_image = True
            content = " ".join(text_parts)
            if has_image:
                content = f"[IMAGE] {content}" if content else "[IMAGE]"

        parsed.append({
            "type": msg_type,
            "content": content,
            "tool_calls": tool_calls,
        })

    return parsed


def parse_lc_output(outputs: dict) -> dict:
    """Parse LangChain LLM output format.

    Args:
        outputs: Raw outputs from run.outputs

    Returns:
        Dict with keys: content, tool_calls, raw
    """
    result = {"content": "", "tool_calls": [], "raw": outputs}

    if not outputs:
        return result

    try:
        generations = outputs.get("generations", [[]])
        if generations and generations[0]:
            gen = generations[0][0] if isinstance(generations[0], list) else generations[0]
            if isinstance(gen, dict):
                msg = gen.get("message", {})
                kwargs = msg.get("kwargs", {})

                result["content"] = kwargs.get("content", "")
                result["tool_calls"] = kwargs.get("tool_calls", [])
    except Exception:
        pass

    return result


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

    print(f"\n{'='*70}")
    print(f"NODE: [{str(run.id)[:8]}] {run.name}")
    print(f"Full ID: {run.id}")
    print(f"Type: {run.run_type} | Status: {run.status} | Tokens: {run.total_tokens or 0:,}")
    print(f"{'='*70}")

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
                content_preview = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                print(f"  [{i}] {msg['type']}: {content_preview}")

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
                if len(val_str) > 100:
                    val_str = val_str[:100] + "..."
                print(f"  {key}: {val_str}")
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
        parsed_output = parse_lc_output(run.outputs)
        result["outputs"] = parsed_output

        if parsed_output["content"]:
            content = parsed_output["content"]
            if len(content) > 300:
                print(f"Content: {content[:300]}...")
            else:
                print(f"Content: {content}")

        if parsed_output["tool_calls"]:
            print(f"\nTool Calls: {len(parsed_output['tool_calls'])}")
            result["tool_calls"] = parsed_output["tool_calls"]

            for tc in parsed_output["tool_calls"]:
                name = tc.get("name", "unknown")
                args = tc.get("args", {})
                print(f"\n  -> {name}")

                # Show all args - NO truncation for 'description' (critical for handoff)
                for k, v in args.items():
                    v_str = str(v)
                    # Don't truncate description - it's the handoff contract
                    if k != "description" and len(v_str) > 80:
                        v_str = v_str[:80] + "..."
                    print(f"     {k}: {v_str}")

                # Mark if this is a task delegation
                if name == "task":
                    subagent = args.get("subagent_type", args.get("specialist", "unknown"))
                    print(f"     [HANDOFF CHECK REQUIRED -> {subagent}]")

    elif run.run_type == "tool":
        # Tool outputs are usually in outputs directly
        print(f"Tool result: {str(run.outputs)[:200]}...")

    print(f"\n{'='*70}")

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

    print(f"\n{'='*70}")
    print(f"CONTEXT HANDOFF ANALYSIS")
    print(f"{'='*70}")
    print(f"Parent: [{str(parent.id)[:8]}] {parent.name}")
    print(f"Child:  [{str(child.id)[:8]}] {child.name}")
    print(f"{'='*70}")

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
        print(f"  {k}: {v}")
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
                passed_context["description"] = args.get("description", "")[:200]

                # Check for key context fields
                for key in ["image_path", "file_path", "url", "product_id", "context"]:
                    if key in args:
                        passed_context[key] = str(args[key])[:100]
                break  # Found the matching call

    for k, v in passed_context.items():
        print(f"  {k}: {v}")
        result["parent_passed"][k] = v

    if not passed_context:
        print("  (Could not extract tool call args)")

    # === WHAT CHILD RECEIVED ===
    print("\n--- WHAT CHILD RECEIVED ---")

    child_received = {}

    if child.inputs:
        for k, v in child.inputs.items():
            if k != "messages":  # Skip raw messages
                child_received[k] = str(v)[:100]

        # Also check first message content
        if "messages" in child.inputs:
            messages = parse_lc_messages(child.inputs["messages"])
            if messages:
                first_human = next((m for m in messages if m["type"] == "HumanMessage"), None)
                if first_human:
                    child_received["first_message"] = first_human["content"][:150]

    for k, v in child_received.items():
        print(f"  {k}: {v}")
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
                    v_str = str(v)
                    if len(v_str) > 200:
                        v_str = v_str[:200] + "..."
                    child_output[k] = v_str
            else:
                child_output["output"] = str(output_val)[:300]
        else:
            # Raw outputs
            for k, v in child.outputs.items():
                v_str = str(v)
                if len(v_str) > 200:
                    v_str = v_str[:200] + "..."
                child_output[k] = v_str

    for k, v in child_output.items():
        print(f"  {k}: {v}")
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
            "inbox/" in str(v) or "/tmp/" in str(v)
            for v in passed_context.values()
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

    print(f"\n{'='*70}")

    return result


# =============================================================================
# show_pm_flow: Show PM's decisions chronologically
# =============================================================================


def show_pm_flow(trace_id: str) -> list[dict]:
    """Show PM's decisions in chronological order.

    Useful for understanding the orchestration flow.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        List of PM decisions
    """
    client = _get_client()
    runs = list(client.list_runs(trace_id=trace_id))

    # Find root (PM)
    root = next((r for r in runs if not r.parent_run_id), None)
    if not root:
        print("No root found")
        return []

    # Find LLM calls that are direct children of PM's model chains
    pm_llm_calls = []
    by_id = {str(r.id): r for r in runs}

    for r in runs:
        if r.run_type == "llm" and r.parent_run_id:
            parent = by_id.get(str(r.parent_run_id))
            if parent and parent.name == "model":
                # Check if grandparent is root
                if parent.parent_run_id and str(parent.parent_run_id) == str(root.id):
                    pm_llm_calls.append(r)

    pm_llm_calls.sort(key=lambda x: x.start_time or datetime.min)

    print(f"\n{'='*70}")
    print(f"PM DECISION FLOW")
    print(f"Trace: {trace_id}")
    print(f"{'='*70}")

    decisions = []

    for i, run in enumerate(pm_llm_calls, 1):
        print(f"\n[{i}] PM Decision - {str(run.id)[:8]}")
        print(f"    Full ID: {run.id}")
        print(f"    Tokens: {run.total_tokens or 0:,}")

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
                    desc = args.get("description", "")[:60]
                    print(f"    -> task({subagent})")
                    print(f"       desc: {desc}...")
                    call_info["args_summary"]["subagent"] = subagent
                    call_info["args_summary"]["description"] = desc
                else:
                    print(f"    -> {name}")
                    # Show first 2 args
                    for k, v in list(args.items())[:2]:
                        v_str = str(v)[:50]
                        print(f"       {k}: {v_str}")
                        call_info["args_summary"][k] = v_str

                decision["tool_calls"].append(call_info)

        decisions.append(decision)

    print(f"\n{'='*70}")
    print(f"Total PM decisions: {len(decisions)}")

    return decisions
