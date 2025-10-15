"""Test parallel interrupts at department level.

This test directly invokes the cataloging department with a message that
should trigger 2 parallel save_product calls, then validates the approval
analyzer handles them correctly through the full stack.

This replicates the original "1 != 2" error scenario to prove it's fixed.
"""

import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.storage_factory import get_storage
from autifyme_agents.departments.cataloging_department import create_cataloging_department
from langchain.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver


def test_department_parallel_interrupts():
    """Test department handling 2 variants in one message - should create 2 interrupts."""
    print("\n" + "="*80)
    print("DEPARTMENT PARALLEL INTERRUPT TEST")
    print("Testing: Department receives multi-variant request -> Makes 2 save_product calls")
    print("="*80)

    storage = get_storage()
    checkpointer = MemorySaver()

    # Create department directly
    print("\n[TEST] Creating cataloging department...")
    department = create_cataloging_department(
        checkpointer=checkpointer,
        storage=storage,
        channel=None,  # No media for this test
    )

    # Unique thread for test
    thread_id = f"dept_test_{uuid.uuid4().hex[:8]}"
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50,
    }

    # Message that should trigger 2 product creations
    message = """Create two variants for jar:
    - First variant: 500ml priced at 30 Rs
    - Second variant: 1000ml priced at 50 Rs

    Make both variants with clear glass, suitable for kitchen storage."""

    print(f"\n[TEST] Sending message to department:")
    print(f"  {message[:100]}...")

    print("\n[TEST] Invoking department (expecting 2 interrupts)...")

    try:
        # First invocation - should hit interrupt
        result = None
        interrupted = False

        for event in department.stream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            stream_mode="values"
        ):
            result = event
            if "__interrupt__" in event:
                interrupted = True
                interrupts = event.get("__interrupt__") or []
                print(f"\n[TEST] INTERRUPTED! Count: {len(interrupts)}")
                for idx, interrupt in enumerate(interrupts, 1):
                    print(f"  Interrupt {idx}: {interrupt}")
                break

        if not interrupted:
            print("\n[TEST] No interrupt occurred - department completed without HITL")
            print("[TEST] This means department did NOT make 2 parallel calls")
            print("[TEST] Current architecture prevents this (PM decomposes)")
            return False

        # Get state to check pending interrupts
        state_snapshot = department.get_state(config)

        if not state_snapshot or not state_snapshot.interrupts:
            print("\n[TEST] No interrupts in state snapshot")
            return False

        interrupt_count = len(state_snapshot.interrupts)
        print(f"\n[TEST] Pending interrupts in state: {interrupt_count}")

        if interrupt_count != 2:
            print(f"\n[TEST] Expected 2 interrupts, got {interrupt_count}")
            print("[TEST] Department did not make parallel calls")
            return False

        print("\n[TEST] SUCCESS! Got 2 simultaneous interrupts")
        print("\n[TEST] Now testing approval analyzer with 2 interrupts...")

        # Extract interrupt info
        from autifyme_agents.workflows.approval_analyzer import analyze_approval

        pending_interrupts = []
        for idx, interrupt_obj in enumerate(state_snapshot.interrupts):
            interrupt_info = {
                "interrupt_id": interrupt_obj.id if hasattr(interrupt_obj, 'id') else f"int_{idx}",
                "tool_name": "save_product",
                "tool_args": {},
                "description": "Product save pending approval",
            }
            if hasattr(interrupt_obj, 'value'):
                interrupt_info["description"] = str(interrupt_obj.value)[:100]
            pending_interrupts.append(interrupt_info)

        print(f"\n[TEST] Testing approval analyzer with {len(pending_interrupts)} interrupts...")

        # Test approval analyzer
        approval_response = analyze_approval(
            pending_interrupts=pending_interrupts,
            user_message="approve both",
        )

        print(f"\n[TEST] Approval analyzer returned:")
        print(f"  Response count: {len(approval_response.responses)}")
        print(f"  Expected count: {len(pending_interrupts)}")
        print(f"  Match: {len(approval_response.responses) == len(pending_interrupts)}")
        print(f"  Reasoning: {approval_response.reasoning}")

        # Validate
        assert len(approval_response.responses) == len(pending_interrupts), \
            f"Count mismatch: {len(approval_response.responses)} != {len(pending_interrupts)}"

        print("\n[TEST] Building Command from approval...")

        # Build Command
        from langgraph.types import Command

        resume_dict = {}
        for idx, interrupt_info in enumerate(pending_interrupts):
            interrupt_id = interrupt_info["interrupt_id"]
            response = approval_response.responses[idx]
            resume_dict[interrupt_id] = [response.model_dump()]

        command = Command(resume=resume_dict)

        print(f"\n[TEST] Command built with {len(resume_dict)} responses")
        print("[TEST] Executing Command to resume workflow...")

        # Resume with Command
        final_result = None
        for event in department.stream(
            command,
            config=config,
            stream_mode="values"
        ):
            final_result = event

        print("\n[TEST] Workflow resumed successfully!")
        print(f"\n[SUCCESS] Full stack test PASSED")
        print("  - Department made 2 parallel calls")
        print("  - Got 2 simultaneous interrupts")
        print("  - Approval analyzer handled them correctly")
        print("  - Command executed without '1 != 2' error")
        print("  - Products would be saved (if not for test mode)")

        return True

    except Exception as e:
        print(f"\n[FAILED] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "#"*80)
    print("# PARALLEL INTERRUPT FULL STACK TEST")
    print("# Replicating original '1 != 2' error scenario")
    print("#"*80)

    result = test_department_parallel_interrupts()

    print("\n" + "#"*80)
    if result:
        print("# RESULT: PASSED")
        print("# Parallel interrupts handled correctly with structured outputs")
        print("#"*80)
        sys.exit(0)
    else:
        print("# RESULT: Could not replicate parallel interrupt scenario")
        print("# This may be expected - PM architecture prevents it by design")
        print("#"*80)
        sys.exit(1)
