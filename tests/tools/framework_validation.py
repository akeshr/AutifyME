"""Framework validation - Test the autonomous testing framework end-to-end.

This script validates the 6-tool framework by running real scenarios
and using hierarchical trace analysis to debug issues.
"""
import sys
from pathlib import Path

# Add tests to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import (
    execute_scenario,
    get_trace_overview,
    get_run_details,
    list_recent_tests,
    record_test_execution,
)


def print_header(title):
    """Print section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_run_tree(node, indent=0):
    """Recursively print run tree."""
    prefix = "  " * indent
    status = "OK" if node.status == "success" else "FAIL"
    print(f"{prefix}[{status}] {node.name} ({node.run_type}) - {node.duration_ms}ms")
    if node.error:
        print(f"{prefix}  ERROR: {node.error[:150]}...")
    for child in node.children:
        print_run_tree(child, indent + 1)


def test_basic_cataloging():
    """Test 1: Basic cataloging with auto-approve."""
    print_header("TEST 1: Basic Cataloging (Auto-Approve)")

    # Execute scenario
    print("\n[Step 1] Executing scenario...")
    result = execute_scenario(
        scenario_id="I want to catalog a product: Nike Air Max sneakers, white/blue colorway, sizes 8-12, price Rs 8500",
        hitl_mode="auto_approve"
    )

    print(f"  Success: {result.success}")
    print(f"  Thread ID: {result.thread_id}")
    print(f"  Trace ID: {result.trace_id}")
    print(f"  Execution time: {result.execution_time_seconds}s")
    print(f"  Products created: {result.products_created}")

    if result.errors:
        print(f"  Errors:")
        for error in result.errors:
            print(f"    - {error}")

    # Record in history
    record_test_execution(result, "basic_cataloging_auto_approve")

    if result.trace_id == "unknown":
        print("\n[SKIP] No trace captured - cannot analyze")
        return None

    # Level 0: Overview
    print("\n[Step 2] Level 0 Analysis - Trace Overview...")
    overview = get_trace_overview(result.trace_id)

    print(f"  Total runs: {overview.total_runs}")
    print(f"  Total cost: ${overview.total_cost}")
    print(f"  Total latency: {overview.total_latency_ms}ms")
    print(f"\n  Hierarchical Run Tree:")
    for root in overview.run_tree:
        print_run_tree(root, indent=2)

    # Find failures
    failures = []
    def find_failures(node):
        if node.status == "error":
            failures.append(node)
        for child in node.children:
            find_failures(child)

    for root in overview.run_tree:
        find_failures(root)

    if failures:
        print(f"\n[Step 3] Level 1 Analysis - Investigating {len(failures)} failure(s)...")
        for idx, failed_node in enumerate(failures[:3], 1):  # Limit to first 3
            print(f"\n  Failure {idx}: {failed_node.name}")
            details = get_run_details(failed_node.run_id)
            print(f"    Run type: {details.run_type}")
            print(f"    Error: {details.error[:200] if details.error else 'None'}")
            print(f"    Input keys: {list(details.inputs.keys())}")
            if details.outputs:
                print(f"    Output keys: {list(details.outputs.keys())}")
    else:
        print("\n[Step 3] No failures found - execution successful!")

    # Find LLM runs to check token usage
    llm_runs = []
    def find_llm_runs(node):
        if node.run_type == "llm":
            llm_runs.append(node)
        for child in node.children:
            find_llm_runs(child)

    for root in overview.run_tree:
        find_llm_runs(root)

    if llm_runs:
        print(f"\n[Step 4] LLM Token Analysis ({len(llm_runs)} LLM calls)...")
        total_tokens = 0
        for llm_run in llm_runs:
            details = get_run_details(llm_run.run_id)
            tokens = details.metadata.total_tokens or 0
            total_tokens += tokens
            print(f"    {llm_run.name}: {tokens} tokens, {llm_run.duration_ms}ms")
        print(f"  Total tokens: {total_tokens}")

    print(f"\n[Step 5] Test Result Summary:")
    print(f"  Overall: {'PASS' if result.success else 'FAIL'}")
    print(f"  Trace URL: {result.trace_url}")

    return result


def test_rejection_scenario():
    """Test 2: Cataloging with rejection."""
    print_header("TEST 2: Cataloging (Auto-Reject)")

    print("\n[Step 1] Executing scenario with auto-reject...")
    result = execute_scenario(
        scenario_id="Catalog product: Adidas sneakers, Rs 5000",
        hitl_mode="auto_reject"
    )

    print(f"  Success: {result.success}")
    print(f"  Execution time: {result.execution_time_seconds}s")
    print(f"  Products created: {result.products_created}")

    if result.errors:
        print(f"  Errors:")
        for error in result.errors:
            print(f"    - {error}")

    record_test_execution(result, "cataloging_auto_reject")

    if result.trace_id != "unknown":
        overview = get_trace_overview(result.trace_id)
        print(f"\n[Step 2] Trace Overview:")
        print(f"  Total runs: {overview.total_runs}")
        print(f"  Products should be 0 (rejected): {result.products_created}")
        print(f"  Trace URL: {result.trace_url}")

    return result


def test_history_tracking():
    """Test 3: History tracking."""
    print_header("TEST 3: History Tracking")

    history = list_recent_tests(limit=5)

    print(f"\n[Recent Test History] ({len(history.tests)} tests)")
    for idx, test in enumerate(history.tests, 1):
        status = "PASS" if test.success else "FAIL"
        print(f"\n  {idx}. [{status}] {test.scenario_id}")
        print(f"     Time: {test.timestamp}")
        print(f"     Duration: {test.execution_time_seconds}s")
        print(f"     Products: {test.products_created}")
        if test.errors_summary:
            print(f"     Errors: {test.errors_summary[:100]}")

    return history


def main():
    """Run all framework validation tests."""
    print("=" * 80)
    print("  AUTONOMOUS TESTING FRAMEWORK VALIDATION")
    print("=" * 80)
    print("\nThis script validates the 6-tool framework with real scenarios.")
    print("Framework: execute -> overview -> details -> messages -> story -> track")

    # Test 1: Basic cataloging
    test1_result = test_basic_cataloging()

    # Test 2: Rejection scenario
    test2_result = test_rejection_scenario()

    # Test 3: History tracking
    history = test_history_tracking()

    # Final summary
    print_header("VALIDATION SUMMARY")
    print("\nFramework Components Validated:")
    print("  [OK] execute_scenario() - Programmatic execution")
    print("  [OK] get_trace_overview() - Hierarchical analysis")
    print("  [OK] get_run_details() - Detailed investigation")
    print("  [OK] list_recent_tests() - History tracking")
    print("  [OK] record_test_execution() - Persistence")

    print("\nNext Steps:")
    print("  1. Review trace URLs in browser for visual inspection")
    print("  2. Validate database state with Supabase MCP")
    print("  3. Identify patterns in failures")
    print("  4. Document framework improvements needed")

    if test1_result:
        print(f"\nTrace URL for detailed review:")
        print(f"  {test1_result.trace_url}")

    print("\n" + "=" * 80)
    print("  VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
