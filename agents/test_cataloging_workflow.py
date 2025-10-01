"""End-to-end test for Cataloging Department workflow."""

import asyncio
from pprint import pprint
import uuid

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver

from autifyme_agents.departments.cataloging_department import create_cataloging_department
from autifyme_agents.tools.storage_tools import initialize_storage
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.core.config import settings


def main():
    """
    Tests the full stateful workflow for the Cataloging Department.
    """
    print("=" * 60)
    print("🚀 CATALOGING DEPARTMENT - STATE PERSISTENCE TEST")
    print("=" * 60)
    
    # Use a `with` block to correctly manage the PostgresSaver connection
    # NOTE: Run `python agents/setup_checkpointer_once.py` first to create tables
    with PostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
        # Initialize storage adapter (dependency injection)
        print("\n[1/4] Initializing storage adapter...")
        storage_client = SupabaseStorageClient()
        initialize_storage(storage_client)
        print("✓ Storage initialized")
        
        # Create Department Head agent, passing the checkpointer
        print("\n[2/4] Creating Cataloging Department agent...")
        department_agent = create_cataloging_department(checkpointer)
        print("✓ Agent ready")
        
        print("\n[3/4] Defining cataloging task...")
        # NOTE: Using a consistent test - the image shows sneakers, so we catalog sneakers
        task = """
        Please catalog a new product.
        It's a pair of high-top canvas sneakers with a classic design. The price is 79.99.
        They come in sizes 7, 8, 9, 10, 11.
        Here is the image for it: https://i.imgur.com/325hRIH.jpeg
        """
        print(f"Task:\n{task.strip()}")
        
        thread_id = str(uuid.uuid4())
        print(f"\nGenerated Thread ID for this conversation: {thread_id}")

        run_config = {
            "configurable": {
                "thread_id": thread_id,
                "company_id": "test_company_id_123"
            }
        }
        print(f"\n[4/4] Invoking agent with thread_id: {thread_id}...")
        print("-" * 60)
        
        try:
            initial_input = {"messages": [HumanMessage(content=task)]}
            
            # Using synchronous `stream` as PostgresSaver doesn't fully support async
            for event in department_agent.stream(initial_input, config=run_config):
                print("---")
                pprint(event)

            print("\n" + "=" * 60)
            print("✅ TEST PASSED")
            print(f"State persisted for thread_id='{thread_id}'")
            print("=" * 60)
            
        except Exception as e:
            print("-" * 60)
            print("\n❌ TEST FAILED")
            print("=" * 60)
            print(f"\nError: {str(e)}")
            raise

if __name__ == "__main__":
    main()
