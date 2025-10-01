"""End-to-end test for Cataloging Department workflow."""

import asyncio
from pprint import pprint
import uuid

from autifyme_agents.departments.cataloging_department import create_cataloging_department
from autifyme_agents.tools.storage_tools import initialize_storage
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient


async def main():
    """
    Tests the full hierarchical agent flow: Department → Specialists → Tools.
    
    This validates:
    - Department Head reasoning and tool selection
    - Image Analysis Specialist extracts visual information
    - Storage tools save data to Supabase
    - LangSmith captures all traces
    """
    print("=" * 60)
    print("🚀 CATALOGING DEPARTMENT - END-TO-END TEST")
    print("=" * 60)
    
    # Initialize storage adapter (dependency injection)
    print("\n[1/5] Initializing storage adapter...")
    storage_client = SupabaseStorageClient()
    initialize_storage(storage_client)
    print("✓ Storage initialized")
    
    # Create Department Head agent
    print("\n[2/5] Creating Cataloging Department agent...")
    department_agent = create_cataloging_department()
    print("✓ Agent ready")
    
    # Define test task (simulates WhatsApp message)
    print("\n[3/5] Defining cataloging task...")
    task = """
    Please catalog a new product.
    It's a vintage-style blue denim jacket. The price is 89.99.
    It comes in sizes S, M, and L.
    Here is the image for it: https://i.imgur.com/325hRIH.jpeg
    """
    print(f"Task:\n{task.strip()}")
    
    # Configure LangSmith tracing
    print("\n[4/5] Configuring LangSmith tracing...")
    # It's critical for tracing a request through the entire system.
    # The 'company_id' here will be picked up by our middleware (Rule 05).
    run_config = {
        "metadata": {
            "conversation_id": str(uuid.uuid4()),
            "user_id": "user_123_test",
        },
        "configurable": {
            "company_id": "test_company_id_123" # This will be used by company_context_middleware
        }
    }
    print(f"✓ Trace ID: {run_config['metadata']['conversation_id']}")
    
    # Invoke agent
    print("\n[5/5] Invoking agent...")
    print("-" * 60)
    
    try:
        # We pass both the input and the config to the `ainvoke` method.
        # The key is "messages" and the value is a list containing the task.
        # This matches the new input schema for agents created with `create_agent`.
        result = await department_agent.ainvoke(
            {"messages": [("human", task)]},
            config=run_config
        )

        print("\n--- Department Finished ---")
        pprint(result)
        
        print("-" * 60)
        print("\n✅ TEST PASSED")
        print("=" * 60)
        print("\nAgent Result:")
        pprint(result, indent=2)
        
        print("\n" + "=" * 60)
        print("🎉 Check LangSmith for full trace:")
        print("   https://smith.langchain.com")
        print("=" * 60)
        
    except Exception as e:
        print("-" * 60)
        print("\n❌ TEST FAILED")
        print("=" * 60)
        print(f"\nError: {str(e)}")
        print("\nDebugging tips:")
        print("1. Check LangSmith for error traces")
        print("2. Verify .env has all required keys")
        print("3. Confirm Supabase schema exists")
        print("=" * 60)
        raise


if __name__ == "__main__":
    asyncio.run(main())
