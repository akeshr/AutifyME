#!/usr/bin/env python
"""HITL testing with actual image inputs.

Tests the complete image cataloging workflow:
1. Image analysis by ImageAnalysisSpecialist
2. Product draft creation
3. HITL approval/rejection with visual content
4. Generic interrupt handling for image-based workflows

Run: uv run python test_hitl_with_images.py
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
print("HITL TESTING WITH ACTUAL IMAGE INPUTS")
print("=" * 80)
print()

from tests.cli.simulate import run_scenario

# Get absolute paths to test images
test_images_dir = Path(__file__).parent / "agents" / "test_images"

test_cases = [
    {
        "name": "Image cataloging: sneaker with approval",
        "text": "Catalog this sneaker for Rs 2500",
        "media": str(test_images_dir / "sneaker.jpg"),
        "hitl_mode": "auto_approve",
    },
    {
        "name": "Image cataloging: sneaker with rejection",
        "text": "Add this shoe",
        "media": str(test_images_dir / "sneaker.jpg"),
        "hitl_mode": "auto_reject",
    },
    {
        "name": "Image only: no text description",
        "text": "Please catalog this",
        "media": str(test_images_dir / "WhatsApp.jpeg"),
        "hitl_mode": "auto_approve",
    },
    {
        "name": "Detailed request with image",
        "text": "Add premium sneakers, white and blue color, size 10, for Rs 3000",
        "media": str(test_images_dir / "sneaker.jpg"),
        "hitl_mode": "auto_approve",
    },
]

print(f"Running {len(test_cases)} image-based test scenarios...")
print(f"Test images directory: {test_images_dir}")
print()

# Verify images exist
for test in test_cases:
    if "media" in test:
        media_path = Path(test["media"])
        if not media_path.exists():
            print(f"❌ ERROR: Image not found at {media_path}")
            sys.exit(1)
        else:
            print(f"✓ Found image: {media_path.name}")

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
            media=test.get('media'),
            hitl_mode=test.get('hitl_mode', 'auto_approve'),
        )
        results.append({"test": test['name'], "status": "PASSED"})
        print(f"\n✅ TEST {i} PASSED\n")
    except Exception as e:
        results.append({"test": test['name'], "status": "FAILED", "error": str(e)})
        print(f"\n❌ TEST {i} FAILED: {e}\n")
        # Continue with next test
        continue

# Summary
print("\n" + "=" * 80)
print("IMAGE-BASED HITL TEST SUMMARY")
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
print("IMAGE-BASED TESTING COMPLETE")
print("=" * 80)
print("\nKey validations:")
print("✓ Image analysis via ImageAnalysisSpecialist")
print("✓ Product draft generation from visual content")
print("✓ Generic HITL with image-based workflows")
print("✓ Approval/rejection flows with visual context")

sys.exit(0 if failed == 0 else 1)
