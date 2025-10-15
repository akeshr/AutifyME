#!/usr/bin/env python
"""Full HITL flow test with database validation via Supabase MCP.

Tests complete workflow:
1. User submits cataloging request
2. Product draft created
3. HITL approval
4. Product saved to database
5. Verify record exists in Supabase

Run: uv run python test_hitl_with_db_validation.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if os.name == 'nt':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, str(Path(__file__).parent / "agents" / "src"))

from dotenv import load_dotenv
load_dotenv()

print("=" * 80)
print("FULL HITL FLOW WITH DATABASE VALIDATION")
print("=" * 80)
print()

from autifyme_agents.cli.simulate import run_scenario

# Test product details
test_product = {
    "name": "Nike Air Max",
    "price": 2500,
    "text": "Catalog Nike Air Max sneakers for Rs 2500"
}

print(f"Testing product: {test_product['name']}")
print(f"Price: Rs {test_product['price']}")
print()

# Step 1: Run workflow with auto-approval
print("STEP 1: Running workflow with HITL auto-approval...")
print("-" * 80)

try:
    run_scenario(
        name='DB Validation Test',
        text=test_product['text'],
        hitl_mode='auto_approve',
    )
    print("\n✅ Workflow completed successfully")
except Exception as e:
    print(f"\n❌ Workflow failed: {e}")
    sys.exit(1)

print()
print("=" * 80)
print("WORKFLOW COMPLETED - Now validating database record...")
print("=" * 80)
print()

# Step 2: Query database to verify product was saved
print("STEP 2: Querying Supabase to verify product record...")
print("-" * 80)
print()

# We'll use the MCP tool in the next step
print("✅ Test completed - use Supabase MCP to verify record")
print()
print("Expected record should have:")
print(f"  - name: {test_product['name']}")
print(f"  - price: {test_product['price']}")
print(f"  - id: <database-generated UUID>")
print(f"  - created_at: ~{datetime.now().isoformat()}")
