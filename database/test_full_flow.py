"""Comprehensive Phase 1 testing - all permutation combinations.

Tests all workflow scenarios with database verification.

Usage:
    uv run python database/test_full_flow.py
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load environment
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")


def print_header(title: str) -> None:
    """Print test case header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def verify_outcome_in_db(test_name: str, expected_sender: str = "local_test_user") -> dict | None:
    """Verify outcome was tracked in database.

    Args:
        test_name: Name of test for verification
        expected_sender: Expected sender ID

    Returns:
        Latest outcome dict or None if not found
    """
    print(f"\n[DB VERIFICATION] Checking database for: {test_name}")

    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg not installed")
        return None

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not found")
        return None

    try:
        with psycopg.connect(db_url, connect_timeout=5) as conn, conn.cursor() as cur:
            # Get latest outcome for this sender
            cur.execute("""
                    SELECT
                        tracking_id,
                        message_text,
                        success,
                        error_type,
                        duration_seconds,
                        created_at
                    FROM workflow_outcomes
                    WHERE sender_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (expected_sender,))

            result = cur.fetchone()
            if result:
                print("  [OK] Found outcome in database:")
                print(f"    Tracking ID: {result[0]}")
                print(f"    Message: {result[1][:50] if result[1] else 'None'}...")
                print(f"    Success: {result[2]}")
                print(f"    Error: {result[3] or 'None'}")
                print(f"    Duration: {result[4]:.2f}s" if result[4] else "    Duration: None")
                print(f"    Tracked At: {result[5]}")
                return {
                    "tracking_id": result[0],
                    "message": result[1],
                    "success": result[2],
                    "error": result[3],
                    "duration": result[4],
                    "created_at": result[5],
                }
            else:
                print(f"  [FAIL] No outcome found for sender: {expected_sender}")
                return None

    except Exception as e:
        print(f"  [ERROR] Database verification failed: {e}")
        return None


def get_workflow_count() -> int:
    """Get total count of tracked workflows."""
    try:
        import psycopg
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            return -1
        with psycopg.connect(db_url, connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM workflow_outcomes")
            result = cur.fetchone()
            if result:
                return result[0]
            return -1
    except Exception:
        return -1


def run_test_case(case_number: int, description: str, command: str) -> bool:
    """Run a test case and verify results.

    Args:
        case_number: Test case number
        description: Test description
        command: Shell command to execute

    Returns:
        True if test passed, False otherwise
    """
    print_header(f"TEST CASE {case_number}: {description}")

    # Get count before test
    count_before = get_workflow_count()
    print(f"[PRE-TEST] Workflow count: {count_before}")

    # Run test
    print(f"\n[EXECUTING] {command}\n")
    os.system(command)

    # Wait a moment for database write
    time.sleep(2)

    # Get count after test
    count_after = get_workflow_count()
    print(f"\n[POST-TEST] Workflow count: {count_after}")

    if count_after > count_before:
        print(f"[OK] New outcome tracked (delta: {count_after - count_before})")
        # Verify the outcome
        outcome = verify_outcome_in_db(description)
        if outcome:
            print(f"\n[RESULT] Test Case {case_number}: PASSED ✓")
            return True
        else:
            print(f"\n[RESULT] Test Case {case_number}: FAILED (outcome not verified)")
            return False
    else:
        print("[FAIL] No new outcome tracked")
        print(f"\n[RESULT] Test Case {case_number}: FAILED ✗")
        return False


def main():
    """Run comprehensive test suite."""
    print("\n" + "="*70)
    print("  COMPREHENSIVE PHASE 1 TESTING")
    print("  All Permutation Combinations + Database Verification")
    print("="*70)

    results = []

    # Test Case 1: Text only (auto-approve)
    success = run_test_case(
        1,
        "Text Only (Auto-Approve)",
        'cd agents && uv run python -m autifyme_agents.cli.simulate "Catalog a blue cotton t-shirt, price $29.99, sizes S-XL" --auto-approve'
    )
    results.append(("Text Only (Auto-Approve)", success))

    # Test Case 2: Image only (auto-approve)
    success = run_test_case(
        2,
        "Image Only (Auto-Approve)",
        'cd agents && uv run python -m autifyme_agents.cli.simulate "" --media test_images/WhatsApp.jpeg --auto-approve'
    )
    results.append(("Image Only (Auto-Approve)", success))

    # Test Case 3: Text + Image (auto-approve)
    success = run_test_case(
        3,
        "Text + Image (Auto-Approve)",
        'cd agents && uv run python -m autifyme_agents.cli.simulate "Catalog this product, price $79.99" --media test_images/WhatsApp.jpeg --auto-approve'
    )
    results.append(("Text + Image (Auto-Approve)", success))

    # Test Case 4: Text + Image with HITL (manual - will prompt user)
    print_header("TEST CASE 4: Text + Image with HITL Approval")
    print("NOTE: This test requires manual approval")
    print("When prompted, please type 'yes' to approve\n")
    input("Press Enter to continue...")

    count_before = get_workflow_count()
    print(f"\n[PRE-TEST] Workflow count: {count_before}")
    print("\n[EXECUTING] Workflow with HITL (awaiting your approval)...\n")

    # Run without auto-approve
    os.system('cd agents && uv run python -m autifyme_agents.cli.simulate "HITL Test: Catalog premium sneakers, price $149.99" --media test_images/WhatsApp.jpeg')

    time.sleep(2)
    count_after = get_workflow_count()
    print(f"\n[POST-TEST] Workflow count: {count_after}")

    if count_after > count_before:
        print(f"[OK] New outcome tracked (delta: {count_after - count_before})")
        outcome = verify_outcome_in_db("HITL Approval Test")
        hitl_approval_success = outcome is not None
        print(f"\n[RESULT] Test Case 4: {'PASSED ✓' if hitl_approval_success else 'FAILED'}")
    else:
        hitl_approval_success = False
        print("\n[RESULT] Test Case 4: FAILED ✗")

    results.append(("HITL Approval", hitl_approval_success))

    # Test Case 5: Text + Image with HITL Rejection (manual)
    print_header("TEST CASE 5: Text + Image with HITL Rejection")
    print("NOTE: This test requires manual rejection")
    print("When prompted, please type 'no' to reject\n")
    input("Press Enter to continue...")

    count_before = get_workflow_count()
    print(f"\n[PRE-TEST] Workflow count: {count_before}")
    print("\n[EXECUTING] Workflow with HITL (awaiting your rejection)...\n")

    os.system('cd agents && uv run python -m autifyme_agents.cli.simulate "HITL Rejection Test: Catalog rejected product" --media test_images/WhatsApp.jpeg')

    time.sleep(2)
    count_after = get_workflow_count()
    print(f"\n[POST-TEST] Workflow count: {count_after}")

    if count_after > count_before:
        print(f"[OK] New outcome tracked (delta: {count_after - count_before})")
        outcome = verify_outcome_in_db("HITL Rejection Test")
        hitl_rejection_success = outcome is not None
        print(f"\n[RESULT] Test Case 5: {'PASSED ✓' if hitl_rejection_success else 'FAILED'}")
    else:
        hitl_rejection_success = False
        print("\n[RESULT] Test Case 5: FAILED ✗")

    results.append(("HITL Rejection", hitl_rejection_success))

    # Summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%\n")

    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"  {status}  {test_name}")

    # Final database verification
    print("\n" + "="*70)
    print("  FINAL DATABASE VERIFICATION")
    print("="*70)

    try:
        import psycopg
        db_url = os.getenv("DATABASE_URL")
        with psycopg.connect(db_url, connect_timeout=5) as conn, conn.cursor() as cur:
            # Total count
            cur.execute("SELECT COUNT(*) FROM workflow_outcomes")
            total_count = cur.fetchone()[0]
            print(f"\n  Total Workflows Tracked: {total_count}")

            # Success vs failure
            cur.execute("SELECT success, COUNT(*) FROM workflow_outcomes GROUP BY success")
            success_breakdown = dict(cur.fetchall())
            print(f"  Successful: {success_breakdown.get(True, 0)}")
            print(f"  Failed: {success_breakdown.get(False, 0)}")

            # Recent workflows
            cur.execute("""
                    SELECT message_text, success, duration_seconds, created_at
                    FROM workflow_outcomes
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
            print("\n  Latest 5 Workflows:")
            for i, row in enumerate(cur.fetchall(), 1):
                msg = row[0][:40] if row[0] else "No message"
                success = "✓" if row[1] else "✗"
                duration = f"{row[2]:.1f}s" if row[2] else "N/A"
                print(f"    {i}. [{success}] {msg}... ({duration})")

    except Exception as e:
        print(f"\n  ERROR: Database verification failed: {e}")

    print("\n" + "="*70)
    print("  COMPREHENSIVE TESTING COMPLETE")
    print("="*70 + "\n")

    return all(success for _, success in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
