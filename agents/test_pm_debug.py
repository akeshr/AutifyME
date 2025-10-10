"""Debug script to test PM delegation to department subagent."""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
env_path = Path.cwd() / ".env"
if not env_path.exists():
    env_path = Path.cwd().parent / ".env"
load_dotenv(env_path)

from langchain.messages import HumanMessage
from autifyme_agents.workflows.project_manager import create_project_manager
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer

# Create PM
storage = SupabaseStorageClient()
checkpointer = get_checkpointer()
company_profile = storage.get_company_profile()

pm = create_project_manager(
    company_profile=company_profile,
    checkpointer=checkpointer,
    storage=storage,
)

# Test simple invocation
print("Testing PM invocation with simple text...")
try:
    result = pm.invoke(
        {"messages": [HumanMessage(content="Catalog a blue t-shirt, price $29")]},
        config={"configurable": {"thread_id": "test_debug_123"}},
    )
    print("[SUCCESS] PM invoked successfully")
    print(f"Result type: {type(result)}")
    print(f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")

    if "messages" in result:
        print(f"Messages count: {len(result['messages'])}")
        for i, msg in enumerate(result['messages']):
            msg_type = type(msg).__name__
            content = str(msg.content)[:100] if hasattr(msg, 'content') else str(msg)[:100]
            print(f"  Message {i}: {msg_type} - {content}")
except Exception as e:
    print(f"[FAIL] PM invocation failed: {type(e).__name__}")
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
