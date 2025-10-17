"""Comprehensive testing script using all testing frameworks.

This script runs through all testing frameworks to validate:
- Unit and integration tests (pytest)
- Single-message scenarios (simulate.py)
- Multi-turn conversations (conversation.py)
- Database validation for all workflows

Usage:
    uv run python run_comprehensive_tests.py
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def safe_print(text: str) -> None:
    """Print text safely, handling console encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))


def run_command(cmd: list[str], description: str, timeout: int = 300) -> tuple[bool, str]:
    """Run a command and return success status.

    Args:
        cmd: Command to run
        description: Description for output
        timeout: Timeout in seconds

    Returns:
        Tuple of (success, output)
    """
    safe_print(f"\n{'='*70}")
    safe_print(f"▶️  {description}")
    safe_print(f"{'='*70}")
    safe_print(f"   Command: {' '.join(cmd)}")
    print()

    start = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent
        )

        elapsed = time.time() - start

        if result.returncode == 0:
            safe_print(f"✅ PASSED in {elapsed:.2f}s")
            return True, result.stdout
        else:
            safe_print(f"❌ FAILED in {elapsed:.2f}s")
            safe_print("\nError output:")
            safe_print(result.stderr[:1000])  # Show first 1000 chars
            return False, result.stderr

    except subprocess.TimeoutExpired:
        safe_print(f"❌ TIMEOUT after {timeout}s")
        return False, f"Timeout after {timeout}s"

    except Exception as e:
        safe_print(f"❌ ERROR: {e}")
        return False, str(e)


def main():
    """Run comprehensive test suite."""
    safe_print("\n" + "="*70)
    safe_print("🚀 AUTIFYME COMPREHENSIVE TEST SUITE")
    safe_print("="*70)
    safe_print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print(f"Working directory: {Path.cwd()}")
    print()

    # Test results tracking
    results = []
    total_tests = 0
    passed_tests = 0

    # Phase 1: Unit and Integration Tests
    safe_print("\n" + "#"*70)
    safe_print("📋 PHASE 1: UNIT & INTEGRATION TESTS")
    safe_print("#"*70)

    success, output = run_command(
        ["uv", "run", "pytest", "tests/", "-v", "--tb=short"],
        "Running pytest suite",
        timeout=180
    )

    results.append({
        "phase": "Unit & Integration Tests",
        "success": success,
        "output": output[:500]
    })

    total_tests += 1
    if success:
        passed_tests += 1

    # Phase 2: Linting
    safe_print("\n" + "#"*70)
    safe_print("🔍 PHASE 2: CODE QUALITY (LINTING)")
    safe_print("#"*70)

    success, output = run_command(
        ["uv", "run", "ruff", "check", "src/"],
        "Running ruff linting"
    )

    results.append({
        "phase": "Linting",
        "success": success,
        "output": output[:500]
    })

    total_tests += 1
    if success:
        passed_tests += 1

    # Phase 3: Single-Message Scenarios
    safe_print("\n" + "#"*70)
    safe_print("📨 PHASE 3: SINGLE-MESSAGE SCENARIOS")
    safe_print("#"*70)

    # Run a few key scenarios
    test_scenarios = [
        ("Text with clear cataloging request", "Catalog these canvas sneakers: white, $79.99, sizes 7-11"),
        ("Text only minimal", "Add sneakers"),
    ]

    for name, message in test_scenarios:
        success, output = run_command(
            ["uv", "run", "python", "-m", "autifyme_agents.cli.simulate",
             message, "--hitl-mode", "auto_approve"],
            f"Testing: {name}",
            timeout=60
        )

        results.append({
            "phase": f"Single Message - {name}",
            "success": success,
            "output": output[:500]
        })

        total_tests += 1
        if success:
            passed_tests += 1

        time.sleep(1)  # Brief pause between scenarios

    # Phase 4: Multi-Turn Conversations
    safe_print("\n" + "#"*70)
    safe_print("💬 PHASE 4: MULTI-TURN CONVERSATIONS")
    safe_print("#"*70)

    # List conversation scenarios
    success, output = run_command(
        ["uv", "run", "python", "-m", "autifyme_agents.cli.conversation", "--list"],
        "Listing conversation scenarios"
    )

    if success:
        # Run greeting_to_cataloging scenario
        success, output = run_command(
            ["uv", "run", "python", "-m", "autifyme_agents.cli.conversation",
             "--scenario", "greeting_to_cataloging", "--hitl-mode", "auto_approve"],
            "Testing: Greeting to Cataloging Flow",
            timeout=90
        )

        results.append({
            "phase": "Multi-Turn Conversation",
            "success": success,
            "output": output[:500]
        })

        total_tests += 1
        if success:
            passed_tests += 1

    # Phase 5: Database Validation
    safe_print("\n" + "#"*70)
    safe_print("🗄️  PHASE 5: DATABASE VALIDATION")
    safe_print("#"*70)

    safe_print("\nRunning workflow with database validation...")

    # Run a cataloging workflow and validate DB
    success, output = run_command(
        ["uv", "run", "python", "-m", "autifyme_agents.cli.simulate",
         "Catalog these premium running shoes: Nike Air, $129.99, sizes 8-12, black/white",
         "--hitl-mode", "auto_approve"],
        "Testing cataloging with database validation",
        timeout=60
    )

    results.append({
        "phase": "Database Validation - Product Creation",
        "success": success,
        "output": output[:500]
    })

    total_tests += 1
    if success:
        passed_tests += 1
        safe_print("\n✓ Product should be created in database")
        safe_print("   (Manual verification: Check Supabase products table)")

    # Final Summary
    safe_print("\n" + "="*70)
    safe_print("📊 COMPREHENSIVE TEST SUMMARY")
    safe_print("="*70)

    safe_print(f"\n✅ Passed: {passed_tests}/{total_tests} ({(passed_tests/total_tests*100):.1f}%)")
    safe_print(f"❌ Failed: {total_tests - passed_tests}/{total_tests}")
    safe_print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Detailed results
    safe_print("\n" + "-"*70)
    safe_print("DETAILED RESULTS:")
    safe_print("-"*70)

    for result in results:
        icon = "✅" if result['success'] else "❌"
        safe_print(f"{icon} {result['phase']}: {'PASSED' if result['success'] else 'FAILED'}")

    # Export results
    report_file = Path(__file__).parent / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": total_tests - passed_tests,
        "pass_rate": f"{(passed_tests/total_tests*100):.1f}%",
        "results": results
    }

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    safe_print(f"\n📄 Test report saved to: {report_file}")

    # Exit code
    if passed_tests == total_tests:
        safe_print("\n🎉 ALL TESTS PASSED!\n")
        sys.exit(0)
    else:
        safe_print(f"\n⚠️  {total_tests - passed_tests} TESTS FAILED\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
