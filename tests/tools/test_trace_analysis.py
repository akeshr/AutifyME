"""Test script for trace analysis tools.

Tests all 3 levels of hierarchical trace analysis with a real execution.
"""
import sys
from pathlib import Path

# Add tests to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.execution import execute_scenario
from tools.trace_analysis import get_trace_overview, get_run_details, get_run_messages


def print_run_tree(node, indent=0):
    """Recursively print run tree structure."""
    prefix = "  " * indent
    status_symbol = "[OK]" if node.status == "success" else "[FAIL]"
    print(f"{prefix}{status_symbol} {node.name} ({node.run_type}) - {node.duration_ms}ms")
    if node.error:
        print(f"{prefix}  Error: {node.error[:100]}...")
    for child in node.children:
        print_run_tree(child, indent + 1)


def main():
    print("=" * 80)
    print("TRACE ANALYSIS TOOL TEST")
    print("=" * 80)

    # Step 1: Execute a simple scenario
    print("\n[1/4] Executing test scenario...")
    result = execute_scenario(
        scenario_id="Hello, I want to catalog a product",
        hitl_mode="auto_approve",
    )

    print(f"  [OK] Execution {'succeeded' if result.success else 'failed'}")
    print(f"  Trace ID: {result.trace_id}")
    print(f"  Thread ID: {result.thread_id}")
    print(f"  Execution time: {result.execution_time_seconds}s")

    if result.errors:
        print(f"  Errors:")
        for error in result.errors:
            print(f"    - {error}")

    if result.trace_id == "unknown":
        print("\n[WARN] No trace captured - cannot test trace analysis")
        return

    # Step 2: Test Level 0 - Overview
    print("\n[2/4] Testing get_trace_overview() - Level 0 (metadata only)...")
    overview = get_trace_overview(result.trace_id)

    print(f"  Total runs: {overview.total_runs}")
    print(f"  Total cost: ${overview.total_cost}")
    print(f"  Total latency: {overview.total_latency_ms}ms")
    print(f"\n  Run tree structure:")
    for root in overview.run_tree:
        print_run_tree(root, indent=2)

    # Step 3: Test Level 1 - Run Details
    print("\n[3/4] Testing get_run_details() - Level 1 (inputs/outputs)...")

    # Find an interesting run to drill into (prefer errors or LLM runs)
    target_run_id = None
    target_run_name = None

    def find_target(node):
        nonlocal target_run_id, target_run_name
        # Prioritize errors
        if node.status == "error" and not target_run_id:
            target_run_id = node.run_id
            target_run_name = node.name
            return
        # Otherwise take first LLM run
        if node.run_type == "llm" and not target_run_id:
            target_run_id = node.run_id
            target_run_name = node.name
        for child in node.children:
            find_target(child)

    for root in overview.run_tree:
        find_target(root)

    if target_run_id:
        print(f"  Drilling into run: {target_run_name}")
        details = get_run_details(target_run_id)

        print(f"  Run type: {details.run_type}")
        print(f"  Inputs keys: {list(details.inputs.keys())}")
        print(f"  Outputs: {details.outputs is not None}")
        if details.error:
            print(f"  Error: {details.error[:200]}...")
        if details.metadata.model:
            print(f"  Model: {details.metadata.model}")
        if details.metadata.total_tokens:
            print(f"  Tokens: {details.metadata.total_tokens}")
    else:
        print("  [WARN] No suitable run found to drill into")

    # Step 4: Test Level 2 - Messages (only if LLM run)
    print("\n[4/4] Testing get_run_messages() - Level 2 (full conversation)...")

    if target_run_id and details.run_type == "llm":
        messages = get_run_messages(target_run_id)
        print(f"  Message count: {len(messages.messages)}")
        for i, msg in enumerate(messages.messages[:3]):  # Show first 3
            content_preview = msg.content[:100] if msg.content else ""
            print(f"  [{i}] {msg.role}: {content_preview}...")
            if msg.tool_calls:
                print(f"      Tool calls: {len(msg.tool_calls)}")
    else:
        print("  [WARN] Skipping - target run is not LLM type")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
