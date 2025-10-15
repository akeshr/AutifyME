#!/usr/bin/env python
"""Simple HITL test - direct cataloging without message intent parsing.

This test bypasses the message intent specialist to test HITL flow directly.
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if os.name == 'nt':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, str(Path(__file__).parent / "agents" / "src"))

from dotenv import load_dotenv
load_dotenv()

print("=" * 80)
print("SIMPLE HITL FLOW TEST")
print("=" * 80)
print()

# Direct cataloging department invocation
from autifyme_agents.departments.cataloging_department import create_cataloging_department
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from langgraph.types import Command

storage = SupabaseStorageClient()
checkpointer = get_checkpointer()

# Create cataloging department
dept = create_cataloging_department(checkpointer=checkpointer, storage=storage)

# Test message - simple cataloging request
from langchain.messages import HumanMessage
import json
import uuid

thread_id = f"test_{uuid.uuid4().hex[:8]}"
config = {
    "configurable": {"thread_id": thread_id},
    "recursion_limit": 50,
}

# Initial message - cataloging request
message = HumanMessage(content="Catalog Nike Air Max sneakers for Rs 2500")
input_data = {"messages": [message]}

print("STEP 1: Sending initial cataloging request...")
print(f"Thread ID: {thread_id}")
print()

# Stream department execution
interrupt_detected = False
interrupt_value = None
last_state = None

try:
    for event in dept.stream(input_data, config=config, stream_mode="values"):
        last_state = event
        print(f"Event: {list(event.keys())}")

        # Check for interrupt
        if "__interrupt__" in event:
            interrupts = event.get("__interrupt__") or []
            if interrupts:
                interrupt_detected = True
                interrupt_value = interrupts[0].value
                print(f"\n⏸️  INTERRUPT DETECTED!")
                print(f"Interrupt value: {interrupt_value}")
                print()
                break

except Exception as e:
    print(f"Error during initial request: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if not interrupt_detected:
    print("❌ No interrupt detected - expected HITL interrupt!")
    sys.exit(1)

print("✅ Interrupt detected successfully")
print()

# STEP 2: Get current state and check for pending interrupt
print("STEP 2: Checking state for pending interrupt...")
state_snapshot = dept.get_state(config)
print(f"Interrupts in state: {len(state_snapshot.interrupts)}")

if not state_snapshot.interrupts:
    print("❌ No pending interrupts in state!")
    sys.exit(1)

pending_interrupt = state_snapshot.interrupts[0]
print(f"✅ Found pending interrupt with ID: {pending_interrupt.id}")
print()

# STEP 3: Resume with approval
print("STEP 3: Resuming with approval...")
# HITL middleware expects a LIST of responses!
resume_value = [{"type": "accept"}]
command = Command(resume={pending_interrupt.id: resume_value})

print(f"Sending Command(resume={{{pending_interrupt.id}: {resume_value}}})")
print()

try:
    final_state = None
    for event in dept.stream(command, config=config, stream_mode="values"):
        final_state = event
        print(f"Event: {list(event.keys())}")

    print()
    print("✅ Command resume completed successfully!")
    print(f"Final state keys: {list(final_state.keys()) if final_state else 'None'}")

    # Check if product was saved
    if "messages" in final_state:
        messages = final_state["messages"]
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'tool':
                content = getattr(msg, 'content', None)
                if isinstance(content, dict) and content.get('tool_name') == 'save_product':
                    print()
                    print("=" * 80)
                    print("✅ SUCCESS: Product saved to database!")
                    print("=" * 80)
                    sys.exit(0)

    print()
    print("=" * 80)
    print("⚠️  WARNING: No save_product confirmation found in messages")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error during resume: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
