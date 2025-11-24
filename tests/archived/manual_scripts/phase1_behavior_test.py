"""Phase 1 Behavior Validation (Automated).

Tests PM's actual conversational behavior without manual input.
Validates intelligent prompt is working correctly.
"""

import asyncio
import uuid

from autifyme_agents.integrations.storage.postgres_saver_factory import (
    get_checkpointer,
)
from autifyme_agents.integrations.storage.storage_factory import get_storage
from autifyme_agents.workflows.project_manager import create_project_manager


def print_scenario(num: int, title: str, message: str):
    """Print scenario header."""
    print("\n" + "=" * 80)
    print(f"SCENARIO {num}: {title}")
    print("=" * 80)
    print(f"USER: {message}")
    print("\nPM RESPONSE:")
    print("-" * 80)


def invoke_pm_and_print(pm, message: str, thread_id: str):
    """Invoke PM and print full response with analysis."""
    try:
        result = pm.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": thread_id}},
        )

        # Extract response
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            content = last_message.content if hasattr(last_message, "content") else str(last_message)
            print(content)

            # Check for tool calls
            tool_calls = getattr(last_message, "tool_calls", []) if hasattr(last_message, "tool_calls") else []
            if tool_calls:
                print("\n" + "-" * 80)
                print(f"TOOL CALLS MADE: {len(tool_calls)}")
                for tc in tool_calls:
                    print(f"  - {tc.get('name', 'unknown')}: {tc.get('args', {})}")

        return result

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run all behavior tests automatically."""
    print("\n" + "=" * 80)
    print("         PHASE 1 BEHAVIOR VALIDATION (AUTOMATED)")
    print("=" * 80)

    storage = get_storage()
    company_profile = storage.get_company_profile()
    pm_checkpointer = get_checkpointer()
    specialist_checkpointer = get_checkpointer()

    # Create PM once for all tests
    print("\nInitializing PM...")
    pm = await create_project_manager(
        company_profile=company_profile,
        checkpointer=pm_checkpointer,
        specialist_checkpointer=specialist_checkpointer,
        storage=storage,
    )
    print("PM initialized successfully!")

    # Scenario 1: User asks about catalog
    print_scenario(
        1,
        "User Catalog Question",
        "What products do we currently make?"
    )
    invoke_pm_and_print(
        pm,
        "What products do we currently make?",
        f"test-1-{uuid.uuid4()}"
    )
    print("\nEXPECTED: Should list family names from base_context")

    # Scenario 2: Check if product exists
    print_scenario(
        2,
        "Product Existence Check",
        "Do we have PET jars?"
    )
    invoke_pm_and_print(
        pm,
        "Do we have PET jars?",
        f"test-2-{uuid.uuid4()}"
    )
    print("\nEXPECTED: Should check base_context, then query to confirm")

    # Scenario 3: Vague request
    print_scenario(
        3,
        "Vague Product Request",
        "I want to add a new product"
    )
    invoke_pm_and_print(
        pm,
        "I want to add a new product",
        f"test-3-{uuid.uuid4()}"
    )
    print("\nEXPECTED: Should ask clarifying questions (price, type, specs)")

    # Scenario 4: Complete request
    print_scenario(
        4,
        "Complete Product Request",
        "Add 500ml PET jar at Rs 30 for food packaging"
    )
    invoke_pm_and_print(
        pm,
        "Add 500ml PET jar at Rs 30 for food packaging",
        f"test-4-{uuid.uuid4()}"
    )
    print("\nEXPECTED: Should check catalog, identify as new family, prepare enriched context")

    # Scenario 5: Ambiguous match
    print_scenario(
        5,
        "Ambiguous Match",
        "Add blue bottles 1 liter"
    )
    invoke_pm_and_print(
        pm,
        "Add blue bottles 1 liter",
        f"test-5-{uuid.uuid4()}"
    )
    print("\nEXPECTED: Should query bottles, find multiple, ask which family")

    # Summary
    print("\n" + "=" * 80)
    print("BEHAVIOR VALIDATION COMPLETE")
    print("=" * 80)
    print("\nReview PM responses above to validate:")
    print("  1. Uses base_context appropriately (Scenario 1)")
    print("  2. Calls query tools when needed (Scenario 2, 5)")
    print("  3. Asks intelligent questions (Scenario 3)")
    print("  4. Shows domain knowledge (Scenario 4)")
    print("  5. Prepares enriched context (Scenario 4)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
