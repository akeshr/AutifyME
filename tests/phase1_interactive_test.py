"""Phase 1 Interactive Behavior Tests.

Tests PM's actual conversational behavior to validate:
- Uses base context correctly
- Asks intelligent questions
- Uses query tools appropriately
- Follows intelligent prompt guidance
"""

import uuid

from autifyme_agents.integrations.storage.postgres_saver_factory import (
    get_checkpointer,
)
from autifyme_agents.integrations.storage.storage_factory import get_storage
from autifyme_agents.workflows.project_manager import create_project_manager


def print_separator():
    """Print visual separator."""
    print("\n" + "=" * 80 + "\n")


def print_scenario(title: str, description: str):
    """Print scenario header."""
    print_separator()
    print(f"SCENARIO: {title}")
    print(f"Testing: {description}")
    print_separator()


def invoke_pm(pm, message: str, thread_id: str):
    """Invoke PM with a message and print response."""
    print(f"\nUSER: {message}")
    print("\nPM Response:")
    print("-" * 80)

    try:
        result = pm.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": thread_id}},
        )

        # Extract PM's response
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            content = last_message.content if hasattr(last_message, "content") else str(last_message)
            print(content)
        else:
            print("[No response from PM]")

        return result
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_scenario_1_user_question():
    """Scenario 1: User asks about catalog (should use base context)."""
    print_scenario(
        "User Catalog Question",
        "PM should answer from base_context without querying"
    )

    storage = get_storage()
    company_profile = storage.get_company_profile()
    checkpointer = get_checkpointer()

    pm = create_project_manager(
        company_profile=company_profile,
        checkpointer=checkpointer,
        storage=storage,
    )

    thread_id = f"test-scenario-1-{uuid.uuid4()}"

    # Test: Ask what products we make
    invoke_pm(pm, "What products do we currently make?", thread_id)

    print("\n" + "-" * 80)
    print("EXPECTED BEHAVIOR:")
    print("- PM should list family names from base_context")
    print("- Should mention total families/SKUs")
    print("- Should NOT query database (base context has this)")
    print("- Response should be quick and accurate")

    input("\nPress Enter to continue to next scenario...")


def test_scenario_2_catalog_check():
    """Scenario 2: User asks if specific product exists (should query)."""
    print_scenario(
        "Product Existence Check",
        "PM should check base_context first, then query for confirmation"
    )

    storage = get_storage()
    company_profile = storage.get_company_profile()
    checkpointer = get_checkpointer()

    pm = create_project_manager(
        company_profile=company_profile,
        checkpointer=checkpointer,
        storage=storage,
    )

    thread_id = f"test-scenario-2-{uuid.uuid4()}"

    # Test: Ask about specific product
    invoke_pm(pm, "Do we have PET jars in our catalog?", thread_id)

    print("\n" + "-" * 80)
    print("EXPECTED BEHAVIOR:")
    print("- PM should scan base_context.family_names first")
    print("- Should notice we have 'PET Bottles' but not 'PET Jars'")
    print("- Should call search_catalog_summary('PET jar') to confirm")
    print("- Should clearly state we DON'T have PET jars (only PET Bottles)")

    input("\nPress Enter to continue to next scenario...")


def test_scenario_3_vague_request():
    """Scenario 3: Vague product request (should ask clarifying questions)."""
    print_scenario(
        "Vague Product Request",
        "PM should ask intelligent clarifying questions"
    )

    storage = get_storage()
    company_profile = storage.get_company_profile()
    checkpointer = get_checkpointer()

    pm = create_project_manager(
        company_profile=company_profile,
        checkpointer=checkpointer,
        storage=storage,
    )

    thread_id = f"test-scenario-3-{uuid.uuid4()}"

    # Test: Vague request
    invoke_pm(pm, "I want to add a new product", thread_id)

    print("\n" + "-" * 80)
    print("EXPECTED BEHAVIOR:")
    print("- PM should ask what type of product")
    print("- Should ask for price, target market, specifications")
    print("- Should show domain knowledge (B2B packaging context)")
    print("- Should NOT just say 'specialists coming soon'")
    print("- Should guide user to provide complete information")

    input("\nPress Enter to continue to next scenario...")


def test_scenario_4_complete_request():
    """Scenario 4: Complete product request (should prepare enriched context)."""
    print_scenario(
        "Complete Product Request",
        "PM should prepare enriched context for future specialists"
    )

    storage = get_storage()
    company_profile = storage.get_company_profile()
    checkpointer = get_checkpointer()

    pm = create_project_manager(
        company_profile=company_profile,
        checkpointer=checkpointer,
        storage=storage,
    )

    thread_id = f"test-scenario-4-{uuid.uuid4()}"

    # Test: Complete request
    invoke_pm(
        pm,
        "Add 500ml PET jar at Rs 30 for food packaging. Transparent with 63mm neck. B2B bulk orders.",
        thread_id
    )

    print("\n" + "-" * 80)
    print("EXPECTED BEHAVIOR:")
    print("- PM should check catalog (search for PET jars)")
    print("- Should identify this as NEW product family")
    print("- Should show domain knowledge (variant patterns, typical sizes)")
    print("- Should ask about multiple sizes (250ml, 1L, 2L?)")
    print("- Should prepare enriched context summary")
    print("- Should acknowledge specialists needed for execution")

    input("\nPress Enter to continue to next scenario...")


def test_scenario_5_ambiguous_match():
    """Scenario 5: Ambiguous product match (should clarify)."""
    print_scenario(
        "Ambiguous Product Match",
        "PM should query and ask for clarification"
    )

    storage = get_storage()
    company_profile = storage.get_company_profile()
    checkpointer = get_checkpointer()

    pm = create_project_manager(
        company_profile=company_profile,
        checkpointer=checkpointer,
        storage=storage,
    )

    thread_id = f"test-scenario-5-{uuid.uuid4()}"

    # Test: Ambiguous request
    invoke_pm(pm, "Add blue bottles 1 liter", thread_id)

    print("\n" + "-" * 80)
    print("EXPECTED BEHAVIOR:")
    print("- PM should search for 'bottles' in catalog")
    print("- Should find multiple bottle families (PET Bottles, Fridge Bottles, Kids Bottles)")
    print("- Should list options and ask which family")
    print("- Should ask if new variant or new family")
    print("- Should ask for specifications (neck type, shape, etc.)")

    input("\nPress Enter to finish...")


def main():
    """Run all interactive behavior tests."""
    print("\n")
    print("=" * 80)
    print("         PHASE 1 INTERACTIVE BEHAVIOR VALIDATION")
    print("      Testing PM's actual conversational intelligence")
    print("=" * 80)
    print("\nThis will test PM with real messages to validate:")
    print("  1. Uses base context correctly")
    print("  2. Calls query tools when appropriate")
    print("  3. Asks intelligent clarifying questions")
    print("  4. Shows domain knowledge")
    print("  5. Prepares enriched context for specialists")
    print("\nEach scenario will show PM's response and expected behavior.")
    print("=" * 80)

    input("\nPress Enter to start tests...")

    try:
        test_scenario_1_user_question()
        test_scenario_2_catalog_check()
        test_scenario_3_vague_request()
        test_scenario_4_complete_request()
        test_scenario_5_ambiguous_match()

        print_separator()
        print("INTERACTIVE BEHAVIOR TESTS COMPLETE")
        print_separator()
        print("\nReview PM responses above to validate:")
        print("  - Uses base context appropriately")
        print("  - Asks intelligent questions")
        print("  - Shows domain knowledge")
        print("  - Calls tools when needed")
        print("  - Acknowledges limitations honestly")
        print_separator()

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
    except Exception as e:
        print(f"\n\nTests failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
