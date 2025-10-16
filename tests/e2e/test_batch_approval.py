"""Simple batch approval test.

Tests the critical batch approval scenario:
1. User requests multiple products
2. Multiple HITL interrupts occur
3. User approves all
4. System should handle N responses for N interrupts correctly
"""

import sys
from pathlib import Path

# Add agents to path
sys.path.insert(0, str(Path(__file__).parent / "agents" / "src"))

from dotenv import load_dotenv
load_dotenv()  # noqa: E402

from autifyme_agents.schemas.approval import BatchApprovalResponse
from autifyme_agents.workflows.approval_analyzer import analyze_approval


def test_batch_approval_simple():
    """Test approval analyzer with 2 interrupts - 'approve both'."""
    print("\n" + "="*80)
    print("TEST 1: Batch Approval - 'approve both'")
    print("="*80)

    pending_interrupts = [
        {
            "interrupt_id": "int_1",
            "tool_name": "save_product",
            "tool_args": {"name": "Jar 500ml", "price": 30.0},
            "description": "Save Jar 500ml @ 30 Rs"
        },
        {
            "interrupt_id": "int_2",
            "tool_name": "save_product",
            "tool_args": {"name": "Jar 1L", "price": 50.0},
            "description": "Save Jar 1L @ 50 Rs"
        },
    ]

    user_message = "approve both"

    print(f"\nPending Interrupts: {len(pending_interrupts)}")
    for idx, interrupt in enumerate(pending_interrupts, 1):
        print(f"  {idx}. {interrupt['tool_name']}: {interrupt['tool_args']}")

    print(f"\nUser Message: '{user_message}'")
    print("\nInvoking approval analyzer...")

    try:
        result: BatchApprovalResponse = analyze_approval(
            pending_interrupts=pending_interrupts,
            user_message=user_message,
        )

        print("\n[SUCCESS]")
        print(f"\nResponse Count: {len(result.responses)}")
        print(f"Expected Count: {len(pending_interrupts)}")
        print(f"Match: {len(result.responses) == len(pending_interrupts)}")

        print(f"\nReasoning: {result.reasoning}")

        print("\nResponses:")
        for idx, response in enumerate(result.responses, 1):
            print(f"  {idx}. type={response.type}, args={response.args}")

        # Validate
        assert len(result.responses) == len(pending_interrupts), \
            f"Response count mismatch: {len(result.responses)} != {len(pending_interrupts)}"

        assert all(r.type == "accept" for r in result.responses), \
            "Expected all responses to be 'accept'"

        print("\n[ALL ASSERTIONS PASSED]")
        return True

    except Exception as e:
        print(f"\n[FAILED]: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_selective_approval():
    """Test approval analyzer with selective approval - 'approve first, change second to 45'."""
    print("\n" + "="*80)
    print("TEST 2: Selective Approval - 'approve first, change second to 45'")
    print("="*80)

    pending_interrupts = [
        {
            "interrupt_id": "int_1",
            "tool_name": "save_product",
            "tool_args": {"name": "Jar 500ml", "price": 30.0},
            "description": "Save Jar 500ml @ 30 Rs"
        },
        {
            "interrupt_id": "int_2",
            "tool_name": "save_product",
            "tool_args": {"name": "Jar 1L", "price": 50.0},
            "description": "Save Jar 1L @ 50 Rs"
        },
    ]

    user_message = "approve first, change second to 45 Rs"

    print(f"\nPending Interrupts: {len(pending_interrupts)}")
    for idx, interrupt in enumerate(pending_interrupts, 1):
        print(f"  {idx}. {interrupt['tool_name']}: {interrupt['tool_args']}")

    print(f"\nUser Message: '{user_message}'")
    print("\nInvoking approval analyzer...")

    try:
        result: BatchApprovalResponse = analyze_approval(
            pending_interrupts=pending_interrupts,
            user_message=user_message,
        )

        print("\n[SUCCESS]")
        print(f"\nResponse Count: {len(result.responses)}")
        print(f"Expected Count: {len(pending_interrupts)}")
        print(f"Match: {len(result.responses) == len(pending_interrupts)}")

        print(f"\nReasoning: {result.reasoning}")

        print("\nResponses:")
        for idx, response in enumerate(result.responses, 1):
            print(f"  {idx}. type={response.type}, args={response.args}")

        # Validate
        assert len(result.responses) == len(pending_interrupts), \
            f"Response count mismatch: {len(result.responses)} != {len(pending_interrupts)}"

        assert result.responses[0].type == "accept", \
            f"Expected first response to be 'accept', got {result.responses[0].type}"

        assert result.responses[1].type == "edit", \
            f"Expected second response to be 'edit', got {result.responses[1].type}"

        assert result.responses[1].args.get("price") == 45.0, \
            f"Expected price edit to 45.0, got {result.responses[1].args}"

        print("\n[ALL ASSERTIONS PASSED]")
        return True

    except Exception as e:
        print(f"\n[FAILED]: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reject_all():
    """Test approval analyzer with rejection - 'no, reject'."""
    print("\n" + "="*80)
    print("TEST 3: Reject All - 'no, reject'")
    print("="*80)

    pending_interrupts = [
        {
            "interrupt_id": "int_1",
            "tool_name": "save_product",
            "tool_args": {"name": "Jar 500ml", "price": 30.0},
            "description": "Save Jar 500ml @ 30 Rs"
        },
        {
            "interrupt_id": "int_2",
            "tool_name": "save_product",
            "tool_args": {"name": "Jar 1L", "price": 50.0},
            "description": "Save Jar 1L @ 50 Rs"
        },
    ]

    user_message = "no, reject"

    print(f"\nPending Interrupts: {len(pending_interrupts)}")
    for idx, interrupt in enumerate(pending_interrupts, 1):
        print(f"  {idx}. {interrupt['tool_name']}: {interrupt['tool_args']}")

    print(f"\nUser Message: '{user_message}'")
    print("\nInvoking approval analyzer...")

    try:
        result: BatchApprovalResponse = analyze_approval(
            pending_interrupts=pending_interrupts,
            user_message=user_message,
        )

        print("\n[SUCCESS]")
        print(f"\nResponse Count: {len(result.responses)}")
        print(f"Expected Count: {len(pending_interrupts)}")
        print(f"Match: {len(result.responses) == len(pending_interrupts)}")

        print(f"\nReasoning: {result.reasoning}")

        print("\nResponses:")
        for idx, response in enumerate(result.responses, 1):
            print(f"  {idx}. type={response.type}, args={response.args}")

        # Validate
        assert len(result.responses) == len(pending_interrupts), \
            f"Response count mismatch: {len(result.responses)} != {len(pending_interrupts)}"

        assert all(r.type == "response" for r in result.responses), \
            "Expected all responses to be 'response' (rejection)"

        print("\n[ALL ASSERTIONS PASSED]")
        return True

    except Exception as e:
        print(f"\n[FAILED]: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "#"*80)
    print("# BATCH APPROVAL TEST SUITE")
    print("#"*80)

    results = []

    # Run tests
    results.append(("Batch Approval (approve both)", test_batch_approval_simple()))
    results.append(("Selective Approval (edit)", test_selective_approval()))
    results.append(("Reject All", test_reject_all()))

    # Summary
    print("\n" + "#"*80)
    print("# SUMMARY")
    print("#"*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASSED]" if result else "[FAILED]"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[ALL TESTS PASSED] Batch approval is working correctly!")
        sys.exit(0)
    else:
        print(f"\n[FAILED] {total - passed} test(s) failed.")
        sys.exit(1)
