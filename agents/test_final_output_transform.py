"""Test the output transformation - should return only final message."""

import uuid
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver

from autifyme_agents.departments.cataloging_department import create_cataloging_department
from autifyme_agents.tools.storage_tools import initialize_storage
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.core.config import settings


def main():
    with PostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
        storage_client = SupabaseStorageClient()
        initialize_storage(storage_client)
        
        department_agent = create_cataloging_department(checkpointer)
        
        task = "Catalog sneakers: price $79.99, sizes 7-11, image: https://i.imgur.com/325hRIH.jpeg"
        
        thread_id = str(uuid.uuid4())
        run_config = {
            "configurable": {
                "thread_id": thread_id,
                "company_id": "test_company_id_123"
            }
        }
        
        print("\n" + "="*80)
        print("TESTING OUTPUT TRANSFORMATION")
        print("="*80)
        print(f"\n🔍 THREAD ID: {thread_id}")
        print(f"   Search for this in LangSmith to verify output format")
        print("="*80)
        
        initial_input = {"messages": [HumanMessage(content=task)]}
        
        print("\n⏳ Running workflow...\n")
        
        # Invoke - should now return transformed output
        result = department_agent.invoke(initial_input, config=run_config)
        
        print("\n" + "="*80)
        print("RESULT STRUCTURE (After Transformation):")
        print("="*80)
        print(f"Result type: {type(result)}")
        print(f"Result keys: {list(result.keys())}")
        
        print("\n" + "="*80)
        print("VERIFICATION:")
        print("="*80)
        
        if "output" in result and "messages" not in result:
            print("✅ SUCCESS! Output is transformed correctly")
            print(f"\nOutput content:\n{result['output'][:200]}...\n")
            print("="*80)
            print("WHAT PROJECT MANAGER RECEIVES:")
            print("="*80)
            print(f"Clean output: {result['output'][:150]}...")
            print("\n✅ No conversation history - just the final result!")
        elif "messages" in result:
            print("❌ FAILED! Still returning full state with 'messages'")
            print(f"   Keys: {result.keys()}")
            print("\n   This means the transformation didn't work.")
        else:
            print("❓ UNEXPECTED structure")
            print(f"   Result: {result}")
        
        print("\n" + "="*80)
        print("LANGSMITH VERIFICATION:")
        print("="*80)
        print(f"1. Go to LangSmith: https://smith.langchain.com")
        print(f"2. Search for thread_id: {thread_id}")
        print(f"3. Check the Output tab - should show:")
        print(f"   {{\"output\": \"The sneakers have been successfully cataloged...\"}}")
        print(f"4. NOT: {{\"messages\": [...]}}")
        print("="*80)
        
        print(f"\n🔍 THREAD ID: {thread_id}\n")


if __name__ == "__main__":
    main()

