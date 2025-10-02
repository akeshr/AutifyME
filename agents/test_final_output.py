"""Test what the graph returns as final output for LangSmith."""

import uuid
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver

from autifyme_agents.departments.cataloging_department import create_cataloging_department
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.core.config import settings


def main():
    with PostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
        storage_client = SupabaseStorageClient()

        department_agent = create_cataloging_department(checkpointer)
        
        task = "Catalog sneakers: price $79.99, sizes 7-11, image: https://i.imgur.com/325hRIH.jpeg"
        
        thread_id = str(uuid.uuid4())
        run_config = {
            "configurable": {
                "thread_id": thread_id,
                "company_id": "test_company_id_123"
            },
            "storage_client": storage_client,
        }
        
        initial_input = {"messages": [HumanMessage(content=task)]}
        
        print("="*80)
        print("CHECKING FINAL OUTPUT FOR LANGSMITH")
        print("="*80)
        
        # Use invoke (what LangSmith sees)
        final_state = department_agent.invoke(initial_input, config=run_config)
        
        print(f"\nFinal state type: {type(final_state)}")
        print(f"Final state keys: {final_state.keys()}")
        
        messages = final_state['messages']
        print(f"\nTotal messages: {len(messages)}")
        
        print("\n" + "="*80)
        print("MESSAGE BREAKDOWN:")
        print("="*80)
        
        for i, msg in enumerate(messages, 1):
            msg_type = type(msg).__name__
            print(f"\n{i}. {msg_type}")
            if hasattr(msg, 'content'):
                content = str(msg.content)[:100]
                print(f"   Content: {content}...")
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print(f"   Tool calls: {len(msg.tool_calls)}")
            if hasattr(msg, 'name'):
                print(f"   Tool name: {msg.name}")
        
        print("\n" + "="*80)
        print("WHAT LANGSMITH SHOULD SEE:")
        print("="*80)
        print(f"Input (first message): {messages[0].content[:80]}...")
        print(f"Output (last message): {messages[-1].content[:80] if hasattr(messages[-1], 'content') else 'NO CONTENT'}...")
        
        print("\n" + "="*80)
        print("ISSUE DIAGNOSIS:")
        print("="*80)
        
        # Check if last message is the final response
        last = messages[-1]
        if hasattr(last, 'tool_calls') and last.tool_calls:
            print("❌ PROBLEM: Last message has tool_calls - graph didn't reach END properly!")
            print("   The workflow might not be completing the final agent response.")
        elif not hasattr(last, 'content') or not last.content:
            print("❌ PROBLEM: Last message has no content!")
        else:
            print("✅ Last message looks correct - it's a final response")
            print(f"   Content: {last.content[:150]}...")


if __name__ == "__main__":
    main()

