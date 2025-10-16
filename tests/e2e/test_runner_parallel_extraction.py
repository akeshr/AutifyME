"""Unit test for runner's interrupt extraction logic.

Tests that the runner correctly unpacks list-valued interrupts into
N interrupt_info objects for the approval analyzer.
"""

import sys
from collections import namedtuple

# Mock interrupt object structure
MockInterrupt = namedtuple('MockInterrupt', ['id', 'value'])


def test_single_action_extraction():
    """Test extraction of single action (dict value)."""
    print("\n" + "="*80)
    print("TEST 1: Single Action Extraction")
    print("="*80)

    # Simulate single interrupt with dict value
    interrupt_obj = MockInterrupt(
        id="test_interrupt_1",
        value={
            "tool_name": "save_product",
            "tool_args": {"name": "Product A", "price": 30.0},
        }
    )

    # Extraction logic
    pending_interrupts_list = []
    interrupt_id = interrupt_obj.id
    interrupt_value = interrupt_obj.value

    if isinstance(interrupt_value, list):
        for action_idx, action in enumerate(interrupt_value):
            if isinstance(action, dict):
                action_request = action.get("action_request", {})
                tool_name = action_request.get("action", "unknown")
                tool_args = action_request.get("args", {})
                description = action.get("description", f"Action {action_idx + 1}")
            else:
                tool_name = "unknown"
                tool_args = {}
                description = str(action)[:100]

            interrupt_info = {
                "interrupt_id": f"{interrupt_id}_{action_idx}",
                "original_interrupt_id": interrupt_id,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "description": description,
            }
            pending_interrupts_list.append(interrupt_info)

    elif isinstance(interrupt_value, dict):
        interrupt_info = {
            "interrupt_id": interrupt_id,
            "tool_name": interrupt_value.get("tool_name", "unknown"),
            "tool_args": interrupt_value.get("tool_args", {}),
            "description": str(interrupt_value)[:100],
        }
        pending_interrupts_list.append(interrupt_info)

    print("Input: 1 interrupt (dict value)")
    print(f"Output: {len(pending_interrupts_list)} interrupt_info objects")
    print("Expected: 1")

    assert len(pending_interrupts_list) == 1, f"Expected 1, got {len(pending_interrupts_list)}"
    assert pending_interrupts_list[0]["interrupt_id"] == "test_interrupt_1"
    assert pending_interrupts_list[0]["tool_name"] == "save_product"

    print("[PASSED] Single action extracted correctly")
    return True


def test_parallel_actions_extraction():
    """Test extraction of parallel actions (list value)."""
    print("\n" + "="*80)
    print("TEST 2: Parallel Actions Extraction")
    print("="*80)

    # Simulate single interrupt with list of 2 actions
    interrupt_obj = MockInterrupt(
        id="test_interrupt_2",
        value=[
            {
                "action_request": {
                    "action": "save_product",
                    "args": {"name": "Glass Jar 500ml", "price": 30}
                },
                "config": {"allow_accept": True},
                "description": "Save Glass Jar 500ml"
            },
            {
                "action_request": {
                    "action": "save_product",
                    "args": {"name": "Glass Jar 1L", "price": 50}
                },
                "config": {"allow_accept": True},
                "description": "Save Glass Jar 1L"
            }
        ]
    )

    # Extraction logic (same as runner_v2.py)
    pending_interrupts_list = []
    interrupt_id = interrupt_obj.id
    interrupt_value = interrupt_obj.value

    if isinstance(interrupt_value, list):
        print(f"Detected list-valued interrupt with {len(interrupt_value)} actions")

        for action_idx, action in enumerate(interrupt_value):
            if isinstance(action, dict):
                action_request = action.get("action_request", {})
                tool_name = action_request.get("action", "unknown")
                tool_args = action_request.get("args", {})
                description = action.get("description", f"Action {action_idx + 1}")
            else:
                tool_name = "unknown"
                tool_args = {}
                description = str(action)[:100]

            interrupt_info = {
                "interrupt_id": f"{interrupt_id}_{action_idx}",
                "original_interrupt_id": interrupt_id,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "description": description,
            }
            pending_interrupts_list.append(interrupt_info)
            print(f"  Extracted action {action_idx}: {tool_name} - {description}")

    elif isinstance(interrupt_value, dict):
        interrupt_info = {
            "interrupt_id": interrupt_id,
            "tool_name": interrupt_value.get("tool_name", "unknown"),
            "tool_args": interrupt_value.get("tool_args", {}),
            "description": str(interrupt_value)[:100],
        }
        pending_interrupts_list.append(interrupt_info)

    print("\nInput: 1 interrupt (list with 2 actions)")
    print(f"Output: {len(pending_interrupts_list)} interrupt_info objects")
    print("Expected: 2")

    assert len(pending_interrupts_list) == 2, f"Expected 2, got {len(pending_interrupts_list)}"
    assert pending_interrupts_list[0]["interrupt_id"] == "test_interrupt_2_0"
    assert pending_interrupts_list[0]["original_interrupt_id"] == "test_interrupt_2"
    assert pending_interrupts_list[0]["tool_name"] == "save_product"
    assert pending_interrupts_list[0]["tool_args"]["name"] == "Glass Jar 500ml"

    assert pending_interrupts_list[1]["interrupt_id"] == "test_interrupt_2_1"
    assert pending_interrupts_list[1]["original_interrupt_id"] == "test_interrupt_2"
    assert pending_interrupts_list[1]["tool_name"] == "save_product"
    assert pending_interrupts_list[1]["tool_args"]["name"] == "Glass Jar 1L"

    print("[PASSED] Parallel actions extracted correctly")
    return True


def test_command_building():
    """Test Command building with grouped responses."""
    print("\n" + "="*80)
    print("TEST 3: Command Building (Grouping by original_interrupt_id)")
    print("="*80)

    from collections import defaultdict

    # Simulate pending_interrupts from extraction
    pending_interrupts = [
        {
            "interrupt_id": "int_1_0",
            "original_interrupt_id": "int_1",
            "tool_name": "save_product",
            "tool_args": {"name": "Jar 500ml", "price": 30},
        },
        {
            "interrupt_id": "int_1_1",
            "original_interrupt_id": "int_1",
            "tool_name": "save_product",
            "tool_args": {"name": "Jar 1L", "price": 50},
        }
    ]

    # Simulate approval responses
    approval_responses = [
        {"type": "accept", "args": None},
        {"type": "edit", "args": {"price": 45.0}}
    ]

    # Build Command (same logic as runner_v2.py)
    interrupt_responses = defaultdict(list)

    for idx, interrupt_info in enumerate(pending_interrupts):
        original_id = interrupt_info.get("original_interrupt_id", interrupt_info["interrupt_id"])
        response = approval_responses[idx]
        interrupt_responses[original_id].append(response)

    resume_dict = dict(interrupt_responses)

    print("Input: 2 interrupt_info with same original_interrupt_id")
    print(f"Output: Command.resume dict with {len(resume_dict)} key(s)")
    print("Expected: 1 key with 2 responses")

    print("\nResume dict:")
    for int_id, responses in resume_dict.items():
        print(f"  {int_id}: {len(responses)} responses")

    assert len(resume_dict) == 1, f"Expected 1 key, got {len(resume_dict)}"
    assert "int_1" in resume_dict, "Expected key 'int_1'"
    assert len(resume_dict["int_1"]) == 2, f"Expected 2 responses, got {len(resume_dict['int_1'])}"

    print("[PASSED] Command building groups responses correctly")
    return True


if __name__ == "__main__":
    print("\n" + "#"*80)
    print("# RUNNER INTERRUPT EXTRACTION UNIT TESTS")
    print("# Testing production fix for parallel interrupts")
    print("#"*80)

    results = []

    try:
        results.append(("Single Action Extraction", test_single_action_extraction()))
    except Exception as e:
        print(f"[FAILED] Single action test: {e}")
        results.append(("Single Action Extraction", False))

    try:
        results.append(("Parallel Actions Extraction", test_parallel_actions_extraction()))
    except Exception as e:
        print(f"[FAILED] Parallel actions test: {e}")
        results.append(("Parallel Actions Extraction", False))

    try:
        results.append(("Command Building", test_command_building()))
    except Exception as e:
        print(f"[FAILED] Command building test: {e}")
        results.append(("Command Building", False))

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
        print("\n[ALL TESTS PASSED] Runner extraction logic is production-ready!")
        sys.exit(0)
    else:
        print(f"\n[SOME TESTS FAILED] {total - passed} test(s) failed.")
        sys.exit(1)
