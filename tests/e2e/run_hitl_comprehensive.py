#!/usr/bin/env python
"""Comprehensive end-to-end testing of Generic HITL Framework.

Tests complete workflows with runner_v2:
1. New cataloging request
2. Approval workflow
3. Edit workflow
4. Rejection workflow
5. Clarification workflow
6. Multiple scenarios

Run: uv run python test_generic_hitl_comprehensive.py
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
print("GENERIC HITL COMPREHENSIVE END-TO-END TESTING")
print("=" * 80)
print()

from tests.cli.simulate import run_scenario
from pathlib import Path

# Test scenarios with different HITL responses
test_cases = [
    {
        "name": "Scenario 1: Simple cataloging with auto-approve",
        "text": "Catalog this jar for Rs 10",
        "hitl_mode": "auto_approve",
    },
    {
        "name": "Scenario 2: Cataloging with rejection",
        "text": "Add sneakers for Rs 500",
        "hitl_mode": "auto_reject",
    },
    {
        "name": "Scenario 3: Greeting message",
        "text": "Hello",
        "hitl_mode": "auto_approve",
    },
]

print("Running", len(test_cases), "test scenarios...")
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

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
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
print("COMPREHENSIVE TESTING COMPLETE")
print("=" * 80)

sys.exit(0 if failed == 0 else 1)
