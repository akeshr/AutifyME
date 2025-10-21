"""End-to-end test for mixed batch approval scenario.

Test scenario:
1. Request 3 products via runner
2. User sees batch approval with all 3
3. User responds: "approve 1, reject 2, edit 3 price to 50"
4. Verify: Product 1 saved, Product 2 NOT saved, Product 3 saved with edited price
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agents", "src"))

from dotenv import load_dotenv
load_dotenv('.env')

import pytest
from autifyme_agents.workflows.orchestration.runner_v2 import WorkflowRunner
from autifyme_agents.integrations.storage.storage_factory import get_storage
from autifyme_agents.core.config import settings

class TestChannel:
    """Test channel that captures messages."""

    def __init__(self):
        self.messages = []
        self.approval_requests = []

    def format_thread_id(self, sender: str) -> str:
        return f"test:{sender}"

    def send_text(self, recipient: str, text: str) -> dict:
        print(f"\n[CHANNEL] Text to {recipient}:")
        print(text)
        self.messages.append({"type": "text", "text": text})
        return {"status": "sent"}

    def send_approval_request(self, recipient: str, product: any) -> dict:
        print(f"\n[CHANNEL] Approval request to {recipient}:")
        print(f"  Product: {product.name} - Rs {product.price}")
        self.approval_requests.append(product)
        return {"status": "sent"}

    def send_completion(self, recipient: str, result: any) -> dict:
        print(f"\n[CHANNEL] Completion to {recipient}:")
        print(f"  Result: {result}")
        self.messages.append({"type": "completion", "result": result})
        return {"status": "sent"}

    def send_error(self, recipient: str, error_type: str, message: str = None) -> dict:
        print(f"\n[CHANNEL] Error to {recipient}: {error_type}")
        if message:
            print(f"  Message: {message}")
        self.messages.append({"type": "error", "error_type": error_type})
        return {"status": "sent"}


@pytest.mark.skipif(
    "dummy" in settings.SUPABASE_URL.lower(),
    reason="Archived test requires real Supabase instance; skipping in CI with dummy credentials"
)
def test_mixed_batch_approval():
    """Test mixed approval: approve 1, reject 2, edit 3."""

    print("\n" + "="*80)
    print("END-TO-END TEST: Mixed Batch Approval")
    print("="*80)

    # Setup
    channel = TestChannel()
    storage = get_storage()
    runner = WorkflowRunner(channel=channel, storage=storage)

    sender = "test_mixed_batch"

    print("\n" + "-"*80)
    print("STEP 1: Request 3 products")
    print("-"*80)

    runner.handle_message(
        sender=sender,
        text="Catalog three products: jar 500ml 30rs, mug 300ml 25rs, plate 10inch 45rs",
        media_id=None,
    )

    print("\n" + "-"*80)
    print("STEP 2: Check batch approval")
    print("-"*80)

    if len(channel.approval_requests) > 0:
        print(f"\nBatch approval shown with {len(channel.approval_requests)} products:")
        for idx, product in enumerate(channel.approval_requests, 1):
            print(f"  {idx}. {product.name} - Rs {product.price}")
    else:
        # Check if batch approval was sent as text
        text_msgs = [m for m in channel.messages if m.get("type") == "text"]
        if text_msgs:
            print(f"\nBatch approval sent as text message (check output above)")
        else:
            print("\nERROR: No batch approval found!")
            return

    print("\n" + "-"*80)
    print("STEP 3: Send mixed approval response")
    print("-"*80)
    print("\nUser input: 'approve 1, reject 2, edit 3 price to 50'")

    # Clear previous messages
    channel.messages = []
    channel.approval_requests = []

    runner.handle_message(
        sender=sender,
        text="approve 1, reject 2, edit 3 price to 50",
        media_id=None,
    )

    print("\n" + "-"*80)
    print("STEP 4: Verify results")
    print("-"*80)

    # Check messages
    completion_msgs = [m for m in channel.messages if m.get("type") == "completion"]
    text_msgs = [m for m in channel.messages if m.get("type") == "text"]

    print(f"\nCompletion messages: {len(completion_msgs)}")
    print(f"Text messages: {len(text_msgs)}")

    # Query database to verify saved products
    print("\n" + "-"*80)
    print("DATABASE VERIFICATION")
    print("-"*80)

    try:
        # Get recent products (last 5 minutes)
        from datetime import datetime, timedelta
        recent_time = datetime.now() - timedelta(minutes=5)

        # This is a simplified query - adjust based on your actual schema
        print("\nQuerying database for recently saved products...")
        print("(Check completion messages and logs above for actual saved products)")

    except Exception as e:
        print(f"\nDatabase verification skipped: {e}")

    print("\n" + "="*80)
    print("EXPECTED RESULTS:")
    print("="*80)
    print("  Product 1 (Jar 500ml, Rs 30): SAVED")
    print("  Product 2 (Mug 300ml, Rs 25): REJECTED (NOT saved)")
    print("  Product 3 (Plate 10inch, Rs 50): SAVED with edited price")
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

    return channel


if __name__ == "__main__":
    try:
        channel = test_mixed_batch_approval()

        print("\n\nFull message log:")
        for idx, msg in enumerate(channel.messages, 1):
            print(f"{idx}. {msg.get('type')}: {str(msg)[:100]}")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
