"""Phase 2C Intelligent Testing Suite.

Tests Phase 2C schema-driven CRUD architecture using AI-powered testing framework.
AI acts as real user, detecting PM architectural violations in real-time.

Test Scenarios:
1. CREATE: New product family with multiple variants
2. ADD: New variant value to existing family
3. UPDATE: Modify family or product fields
4. DELETE: Remove entities with cascade impact
5. AMBIGUOUS: Handle vague requests requiring clarification
6. BUSINESS RULES: SKU uniqueness validation
7. ERROR HANDLING: Rollback on failures
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
from tests.tools.trace_analysis import get_trace_overview, get_llm_trace_tree


# =============================================================================
# Test Scenario Definitions
# =============================================================================

PHASE2C_SCENARIOS = {
    "create_family_happy_path": """
**Scenario:** CREATE new product family (happy path)

**User Profile:** Packaging company owner onboarding new product line

**Initial Request:** "I want to add glass bottles to my catalog. We make 250ml, 500ml, and 1L sizes. Base price is Rs 15 per bottle. All are transparent, food-grade quality."

**Expected PM Behavior:**
1. PM analyzes request (complete information provided)
2. PM delegates to Product Architecture Specialist
3. Specialist generates OperationIntent with:
   - product_families INSERT (Glass Bottles)
   - variant_axes INSERT (Capacity)
   - variant_values INSERT (250ml, 500ml, 1L)
   - products INSERT (3 products for each capacity)
4. PM presents impact analysis for approval
5. User approves
6. PM executes via execute_database_operation
7. PM confirms completion

**Success Criteria:**
- PM uses execute_database_operation tool (NOT old phase 2B tools)
- Specialist returns OperationIntent (NOT ProductArchitectureDraft)
- PM presents clear impact analysis
- Database operations succeed
- No architectural violations
""",

    "add_variant_granular": """
**Scenario:** ADD new variant value (granular operation)

**User Profile:** Existing customer adding capacity to product line

**Context:** Water Bottles family already exists with 500ml, 1L capacities

**Initial Request:** "Add 2L capacity to our Water Bottles family"

**Expected PM Behavior:**
1. PM searches catalog, finds Water Bottles family
2. PM delegates to Product Architecture Specialist
3. Specialist generates granular OperationIntent:
   - variant_values INSERT (2L only)
   - products INSERT (only for 2L capacity)
   - NOT rebuilding entire family
4. PM shows impact (adding X new SKUs)
5. User approves
6. PM executes operation
7. Completion confirmed

**Success Criteria:**
- Granular operation (not full family rebuild)
- OperationIntent contains minimal operations
- Existing products untouched
- New SKUs follow family convention
""",

    "update_field_targeted": """
**Scenario:** UPDATE specific field (targeted operation)

**User Profile:** Manager updating product pricing

**Context:** PET Jars family exists with base_price = 25.00

**Initial Request:** "Update base price for PET Jars to Rs 30"

**Expected PM Behavior:**
1. PM searches catalog, finds PET Jars family
2. PM delegates to Product Architecture Specialist
3. Specialist generates UPDATE OperationIntent:
   - product_families UPDATE (base_price only)
   - target_filter: {product_family_id: ...}
4. PM shows impact (1 family record updated)
5. User approves
6. PM executes UPDATE operation
7. Confirmation with updated price

**Success Criteria:**
- Targeted UPDATE (not DELETE + CREATE)
- Only base_price field modified
- Single SQL UPDATE statement
- Other fields unchanged
""",

    "delete_with_cascade": """
**Scenario:** DELETE with cascade impact analysis

**User Profile:** Manager discontinuing product variant

**Context:** Water Bottles family has Red, Blue, Green colors

**Initial Request:** "Remove Green color from Water Bottles"

**Initial Request:** "Delete the Green color option from our Water Bottles"

**Expected PM Behavior:**
1. PM searches catalog, finds Water Bottles + Green variant
2. PM delegates to Product Architecture Specialist
3. Specialist generates DELETE OperationIntent with:
   - variant_values DELETE (Green)
   - CASCADE impact calculation (products affected)
4. PM presents impact:
   - "Will delete Green variant value"
   - "CASCADE: Will delete X products with Green color"
5. User confirms understanding of impact
6. PM executes DELETE
7. Confirmation

**Success Criteria:**
- Accurate cascade impact calculation
- Clear warning about affected products
- Cascade DELETE executes correctly
- No orphaned records
""",

    "ambiguous_request": """
**Scenario:** Ambiguous request requiring clarification

**User Profile:** User providing vague product details

**Initial Request:** "Add some containers"

**Expected PM Behavior:**
1. PM analyzes request (too vague)
2. PM asks clarifying questions:
   - "What type of containers?"
   - "What sizes/capacities?"
   - "Material? (plastic, glass, metal)"
   - "Price range?"
3. User provides details: "PET bottles, 500ml, Rs 10"
4. PM now has complete info
5. PM delegates to specialist
6. Normal CREATE workflow continues

**Success Criteria:**
- PM asks intelligent questions
- PM doesn't delegate with incomplete data
- Specialist receives complete information
- Workflow succeeds after clarification
""",

    "business_rule_duplicate_sku": """
**Scenario:** Business rule validation - duplicate SKU

**User Profile:** User attempting to add product with existing SKU

**Context:** Product with SKU "BOTTLE-500ML-CLR" already exists

**Initial Request:** "Add PET bottle, 500ml, clear, SKU code BOTTLE-500ML-CLR"

**Expected PM Behavior:**
1. PM delegates to Product Architecture Specialist
2. Specialist generates OperationIntent
3. PM presents for approval
4. User approves
5. PM executes via execute_database_operation
6. **Business rule triggers:** validate_sku_uniqueness
7. **Validation fails:** Duplicate SKU detected
8. PM reports error clearly:
   - "Operation failed: SKU 'BOTTLE-500ML-CLR' already exists"
   - "Please use different SKU code"
9. User understands and can retry with different SKU

**Success Criteria:**
- Business rule executes before database insert
- Duplicate detected and prevented
- Clear error message to user
- Database unchanged (no partial insert)
- User can retry with corrected data
""",

    "error_rollback": """
**Scenario:** Error handling with rollback

**User Profile:** User with request that causes mid-execution failure

**Initial Request:** "Add Ceramic Jars family with capacities 100ml, 200ml, invalid_size_format"

**Expected PM Behavior:**
1. PM delegates to Product Architecture Specialist
2. Specialist generates multi-step OperationIntent:
   - Step 1: INSERT product_families (succeeds)
   - Step 2: INSERT variant_axes (succeeds)
   - Step 3: INSERT variant_values (fails due to invalid data)
3. PM executes steps sequentially
4. **Step 3 fails**
5. **Rollback triggers:** Steps 1-2 reversed
6. PM reports:
   - "Operation failed at step 3"
   - "Rolled back 2 completed steps"
   - "Database unchanged"
7. User understands failure, no partial data

**Success Criteria:**
- Multi-step execution detected
- Failure at step N
- Steps 1 to N-1 rolled back
- Database in consistent state
- Clear error reporting
"""
}


# =============================================================================
# Test Execution Functions
# =============================================================================


async def run_scenario_test(scenario_name: str, scenario_desc: str):
    """
    Run single intelligent test scenario.

    Args:
        scenario_name: Scenario identifier
        scenario_desc: Full scenario description for AI context

    Returns:
        ExecutionResult with success/failure and trace info
    """
    print(f"\n{'='*80}")
    print(f"TEST: {scenario_name}")
    print(f"{'='*80}\n")

    result = await intelligent_execute_scenario(
        scenario_id=scenario_desc,
        media_path=None,
        max_turns=15,  # Allow more turns for complex scenarios
    )

    # Print result summary
    print(f"\n[RESULT]: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"[Time]:  Duration: {result.execution_time_ms}ms")
    print(f"[Turns]: {result.conversation_turns}")

    if result.trace_url:
        print(f"[Trace]: {result.trace_url}")

    if not result.success:
        print(f"\n[Warning]:  FAILURE REASON:")
        print(f"   {result.debug_reason or result.errors}")

        if result.trace_id:
            print(f"\n[Analyzing]: trace...")
            try:
                # Get trace overview
                overview = get_trace_overview(result.trace_id)
                print(f"\n   Trace Overview:")
                print(f"   - Total runs: {overview.get('total_runs', 'N/A')}")
                print(f"   - Errors: {overview.get('error_count', 0)}")

                # Get LLM call tree
                tree = get_llm_trace_tree(result.trace_id)
                if tree:
                    print(f"\n   LLM Call Tree:")
                    for call in tree[:5]:  # Show first 5 calls
                        print(f"   - {call.get('name', 'Unknown')}: {call.get('status', 'N/A')}")

            except Exception as e:
                print(f"   (Could not analyze trace: {e})")

    return result


async def run_all_phase2c_tests():
    """
    Run all Phase 2C intelligent test scenarios.

    Returns:
        Dict of scenario results
    """
    print("\n" + "="*80)
    print("PHASE 2C INTELLIGENT TESTING SUITE")
    print("="*80)
    print("\nAI (gpt-4.1-nano) acts as real user, detecting architectural violations.\n")

    results = {}

    for scenario_name, scenario_desc in PHASE2C_SCENARIOS.items():
        try:
            result = await run_scenario_test(scenario_name, scenario_desc)
            results[scenario_name] = {
                "success": result.success,
                "execution_time_ms": result.execution_time_ms,
                "conversation_turns": result.conversation_turns,
                "trace_url": result.trace_url,
                "debug_reason": result.debug_reason,
                "errors": result.errors,
            }

            # Pause between scenarios to avoid rate limits
            print("\nWaiting 3 seconds before next scenario...")
            await asyncio.sleep(3)

        except Exception as e:
            print(f"\n[EXCEPTION]: {e}")
            results[scenario_name] = {
                "success": False,
                "error": str(e),
            }

    # Print summary
    print("\n" + "="*80)
    print("TEST SUITE SUMMARY")
    print("="*80 + "\n")

    success_count = sum(1 for r in results.values() if r.get("success", False))
    total_count = len(results)

    print(f"[PASSED]: {success_count}/{total_count}")
    print(f"[FAILED]: {total_count - success_count}/{total_count}")

    print(f"\n{'Scenario':<35} {'Result':<10} {'Turns':<8} {'Time (ms)'}")
    print("-" * 80)

    for name, result in results.items():
        status = "PASS" if result.get("success", False) else "FAIL"
        turns = result.get("conversation_turns", "N/A")
        time_ms = result.get("execution_time_ms", "N/A")
        print(f"{name:<35} {status:<10} {turns!s:<8} {time_ms}")

    print("\n" + "="*80)

    return results


# =============================================================================
# Main Entry Point
# =============================================================================


if __name__ == "__main__":
    # Run all Phase 2C tests
    results = asyncio.run(run_all_phase2c_tests())

    # Exit with error code if any tests failed
    failed = sum(1 for r in results.values() if not r.get("success", False))
    sys.exit(1 if failed > 0 else 0)
