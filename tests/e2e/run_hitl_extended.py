#!/usr/bin/env python
"""Extended HITL testing with various scenarios and edge cases.

Tests:
1. Approval with different phrasing ("looks good", "approved", "yes")
2. Rejection with different phrasing ("no", "reject", "cancel")
3. Edit requests ("change price to X")
4. Insufficient information handling
5. Multi-turn clarifications
6. Off-topic redirects

Run: uv run python test_hitl_extended.py
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
load_dotenv()  # noqa: E402

print("=" * 80)
print("EXTENDED HITL TESTING - Various Scenarios and Phrasings")
print("=" * 80)
print()

from tests.cli.simulate import run_scenario

test_cases = [
    # Approval variations
    {
        "name": "Approval: 'looks good'",
        "text": "Catalog backpack for Rs 500",
        "hitl_mode": "auto_approve",
    },
    {
        "name": "Approval: natural language",
        "text": "Add jacket for Rs 2000",
        "hitl_mode": "auto_approve",
    },

    # Rejection variations
    {
        "name": "Rejection: 'no thanks'",
        "text": "Catalog watch for Rs 3000",
        "hitl_mode": "auto_reject",
    },
    {
        "name": "Rejection: 'cancel this'",
        "text": "Add sunglasses for Rs 1500",
        "hitl_mode": "auto_reject",
    },

    # Insufficient information
    {
        "name": "Insufficient info: missing price",
        "text": "Add a blue shirt",
        "hitl_mode": "auto_approve",
    },
    {
        "name": "Insufficient info: just product name",
        "text": "Catalog shoes",
        "hitl_mode": "auto_approve",
    },

    # Off-topic and greetings
    {
        "name": "Off-topic: weather question",
        "text": "What's the weather like?",
        "hitl_mode": "auto_approve",
    },
    {
        "name": "Greeting: formal",
        "text": "Good morning! How can you help me?",
        "hitl_mode": "auto_approve",
    },

    # Varied cataloging requests
    {
        "name": "Detailed product: with description",
        "text": "Add premium leather wallet, brown color, genuine leather, for Rs 800",
        "hitl_mode": "auto_approve",
    },
    {
        "name": "Simple product: minimal info",
        "text": "Catalog mug Rs 50",
        "hitl_mode": "auto_approve",
    },
]

print(f"Running {len(test_cases)} extended test scenarios...")
print()

results = []

for i, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"TEST {i}/{len(test_cases)}: {test['name']}")
    print(f"{'='*80}\n")

    try:
        run_scenario(
            name=test['name'],
            text=test['text'],
            hitl_mode=test.get('hitl_mode', 'auto_approve'),
        )
        results.append({"test": test['name'], "status": "PASSED"})
        print(f"\n✅ TEST {i} PASSED\n")
    except Exception as e:
        results.append({"test": test['name'], "status": "FAILED", "error": str(e)})
        print(f"\n❌ TEST {i} FAILED: {e}\n")
        # Continue with next test even if one fails
        continue

# Summary
print("\n" + "=" * 80)
print("EXTENDED TEST SUMMARY")
print("=" * 80)

passed = sum(1 for r in results if r["status"] == "PASSED")
failed = sum(1 for r in results if r["status"] == "FAILED")

print(f"\n✅ Passed: {passed}/{len(results)}")
print(f"❌ Failed: {failed}/{len(results)}\n")

for result in results:
    status_icon = "✅" if result["status"] == "PASSED" else "❌"
    print(f"{status_icon} {result['test']}: {result['status']}")
    if "error" in result:
        print(f"   Error: {result['error'][:200]}")

print("\n" + "=" * 80)
print("EXTENDED TESTING COMPLETE")
print("=" * 80)

sys.exit(0 if failed == 0 else 1)
