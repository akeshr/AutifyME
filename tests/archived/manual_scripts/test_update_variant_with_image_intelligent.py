"""
Intelligent test for updating variant capacity with image attachment.
Tests Phase 2C UPDATE operation with media handling.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Windows-specific fix for psycopg async
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from tests.tools.intelligent_execution import intelligent_execute_scenario

# Test scenario definition
UPDATE_WITH_IMAGE_SCENARIO = """
**Scenario:** UPDATE variant capacity from 500ml to 1L with product image

**User Profile:** Product manager updating existing product specification with new image

**Context:** Glass Bottles family exists with 250ml, 500ml, and 1L capacities

**Initial Request:** "I want to change the 500ml Glass Bottle variant to 1 liter capacity. I'm attaching the product image."

**Expected PM Behavior:**
1. PM downloads and analyzes the attached image
2. PM searches catalog, finds Glass Bottles family
3. PM identifies 500ml variant to update
4. PM delegates to Product Architecture Specialist with:
   - Image analysis context
   - Update request details
5. Specialist generates OperationIntent:
   - variant_values UPDATE (change 500ml to 1L)
   - products UPDATE (update display name, variant references)
   - Preserve existing SKUs and relationships
6. PM presents HITL approval with:
   - **Operation type:** UPDATE
   - **Summary:** What will be changed
   - **Impact analysis:** Affected entities count
   - **Example SKUs:** Preview of changes
   - **Image confirmation:** PM should mention image was analyzed
7. User approves
8. PM executes via execute_database_operation
9. PM confirms completion with updated details

**Success Criteria:**
- PM downloads and references the image in analysis
- PM uses execute_database_operation with complete OperationIntent
- HITL approval message shows formatted operation details (NOT blank)
- approval message includes: operation type, summary, impact, examples
- Specialist returns OperationIntent with ALL 8 fields (including impact_analysis, execution_plan)
- UPDATE operation targets specific variant (not full family rebuild)
- Database update succeeds with correct capacity change
- No architectural violations (Phase 2C patterns followed)

**Architecture Validation:**
- NO Phase 2B tools used (approve_product_draft, etc.)
- NO ProductArchitectureDraft returned
- YES execute_database_operation called with all parameters
- YES OperationIntent with impact_analysis and execution_plan
- YES formatted HITL approval message displayed
"""


async def run_update_with_image_test():
    """
    Run intelligent test for updating variant with image.
    """
    def safe_print(text):
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode('ascii', 'replace').decode('ascii'))

    safe_print("\n" + "="*80)
    safe_print("INTELLIGENT TEST: Update 500ml to 1L with Image")
    safe_print("="*80)
    safe_print("\nAI (Gemini 2.5 Flash) acts as real user with image attachment.\n")

    # Get image path
    fixture_image = Path(__file__).parent / "fixtures" / "images" / "PET_CAN_JAR_500ml.jpeg"

    if not fixture_image.exists():
        safe_print(f"[ERROR] Image not found: {fixture_image}")
        safe_print("Please ensure fixture image exists at tests/fixtures/images/PET_CAN_JAR_500ml.jpeg")
        return False

    safe_print(f"[IMAGE] Using fixture: {fixture_image.name}")
    safe_print("")

    # Run intelligent test with image
    result = await intelligent_execute_scenario(
        scenario_id=UPDATE_WITH_IMAGE_SCENARIO,
        media_path=str(fixture_image.absolute()),  # Pass image to PM
        max_turns=10,  # Allow more turns for image processing + update flow
    )

    # Print detailed result
    safe_print(f"\n{'='*80}")
    safe_print(f"RESULT: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
    safe_print(f"{'='*80}\n")

    safe_print(f"Execution Time: {result.execution_time_seconds}s")
    safe_print(f"HITL Triggered: {'Yes' if result.hitl_triggered else 'No'}")

    if result.trace_url:
        safe_print(f"Trace URL: {result.trace_url}")

    if not result.success:
        safe_print("\nFailure Reason:")
        for error in result.errors:
            safe_print(f"  - {error}")

    safe_print(f"\n{'='*80}\n")

    return result.success


if __name__ == "__main__":
    success = asyncio.run(run_update_with_image_test())
    sys.exit(0 if success else 1)
