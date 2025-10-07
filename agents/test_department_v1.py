"""Test cataloging department with v1 features."""

from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from autifyme_agents.departments.cataloging_department import create_cataloging_department
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.schemas.context import AgentContext

load_dotenv(Path.cwd() / ".env")

print("=" * 60)
print("CATALOGING DEPARTMENT V1 TEST")
print("=" * 60)

storage = SupabaseStorageClient()
checkpointer = get_checkpointer()

print("Creating cataloging department...")
department = create_cataloging_department(
    checkpointer=checkpointer,
    storage=storage,
    enable_hitl=False  # Skip HITL for simple test
)

print("Invoking department...")
context = AgentContext(
    thread_id="test-v1",
    company_id="default",
    storage=storage
)

result = department.invoke(
    {"messages": [HumanMessage(content="Catalog: Red cotton t-shirt, size M, price $29.99")]},
    config={"configurable": {"thread_id": "test-v1"}},
    context=context
)

print("\nResult:")
print(f"Type: {type(result)}")
print(f"Keys: {result.keys() if hasattr(result, 'keys') else 'N/A'}")
if 'messages' in result:
    print(f"Message count: {len(result['messages'])}")
    last_msg = result['messages'][-1]
    print(f"Last message type: {type(last_msg).__name__}")
    print(f"Content preview: {str(last_msg.content)[:200]}")

print("\n" + "=" * 60)
print("V1 FEATURES TEST COMPLETE")
print("=" * 60)
