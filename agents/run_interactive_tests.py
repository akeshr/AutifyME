"""Interactive test runner - runs scenarios and pauses for your approval.

This script runs through test scenarios but DOES NOT capture output,
allowing you to provide input at HITL approval prompts. After each test,
it validates the database to confirm product creation.

Usage:
    uv run python run_interactive_tests.py

Features:
- Runs scenarios sequentially
- Pauses for your approval at HITL prompts
- Validates database after each test
- Generates comprehensive report
"""

import sys
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv


def safe_print(text: str) -> None:
    """Print text safely, handling console encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))


def run_interactive_command(
    cmd: list[str],
    description: str,
    timeout: int = 300
) -> tuple[bool, str]:
    """Run a command interactively (NO output capture - you can provide input).

    Args:
        cmd: Command to run
        description: Description for output
        timeout: Timeout in seconds

    Returns:
        Tuple of (success, empty_string)
    """
    safe_print(f"\n{'='*70}")
    safe_print(f"▶️  {description}")
    safe_print(f"{'='*70}")
    safe_print(f"   Command: {' '.join(cmd)}")
    safe_print("\n⏸️  This test will pause for your input at HITL prompts")
    safe_print(f"{'='*70}\n")

    start = time.time()

    try:
        # NO capture_output - this allows interactive input!
        result = subprocess.run(
            cmd,
            timeout=timeout,
            cwd=Path(__file__).parent
        )

        elapsed = time.time() - start

        if result.returncode == 0:
            safe_print(f"\n{'='*70}")
            safe_print(f"✅ COMPLETED in {elapsed:.2f}s")
            safe_print(f"{'='*70}\n")
            return True, ""
        else:
            safe_print(f"\n{'='*70}")
            safe_print(f"❌ FAILED in {elapsed:.2f}s")
            safe_print(f"{'='*70}\n")
            return False, ""

    except subprocess.TimeoutExpired:
        safe_print(f"\n❌ TIMEOUT after {timeout}s")
        return False, f"Timeout after {timeout}s"

    except Exception as e:
        safe_print(f"\n❌ ERROR: {e}")
        return False, str(e)


def validate_database() -> dict:
    """Validate database after test completion.

    Returns:
        Validation result dictionary
    """
    try:
        from autifyme_agents.adapters.supabase_storage import SupabaseStorage

        storage = SupabaseStorage()
        company_profile = storage.get_company_profile()

        if company_profile:
            products_count = len(company_profile.products)
            return {
                "success": True,
                "message": f"✅ Database validated: {products_count} products in catalog",
                "products_count": products_count
            }
        else:
            return {
                "success": False,
                "message": "⚠️  No company profile found in database",
                "products_count": 0
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Database validation error: {e}",
            "products_count": 0
        }


def main():
    """Run interactive test suite."""
    # Load environment
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        env_path = Path.cwd().parent / ".env"

    if env_path.exists():
        load_dotenv(env_path)
    else:
        print("Warning: .env file not found")

    safe_print("\n" + "="*70)
    safe_print("🎮 AUTIFYME INTERACTIVE TEST SUITE")
    safe_print("="*70)
    safe_print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print(f"Working directory: {Path.cwd()}")
    safe_print(f"\n{'='*70}")
    safe_print("📋 TEST MODE: INTERACTIVE")
    safe_print("   • Tests will pause for your input")
    safe_print("   • Provide approvals/edits at HITL prompts")
    safe_print("   • Database validated after each test")
    safe_print(f"{'='*70}\n")

    input("Press Enter to start interactive testing...")

    # Test results tracking
    results = []
    total_tests = 0
    passed_tests = 0

    # Define test scenarios
    test_scenarios = [
        {
            "name": "Text-only cataloging (clear details)",
            "cmd": [
                "uv", "run", "python", "-m", "autifyme_agents.cli.simulate",
                "Catalog these canvas sneakers: white, $79.99, sizes 7-11",
                "--hitl-mode", "interactive"
            ],
            "timeout": 120
        },
        {
            "name": "Text-only cataloging (minimal details)",
            "cmd": [
                "uv", "run", "python", "-m", "autifyme_agents.cli.simulate",
                "Add sneakers",
                "--hitl-mode", "interactive"
            ],
            "timeout": 120
        },
        {
            "name": "Image with caption cataloging",
            "cmd": [
                "uv", "run", "python", "-m", "autifyme_agents.cli.simulate",
                "--image", "test_images/sneaker.jpg",
                "--hitl-mode", "interactive",
                "Catalog these premium running shoes - Nike Air Max, $129.99"
            ],
            "timeout": 180
        },
        {
            "name": "Multi-turn: Greeting to Cataloging",
            "cmd": [
                "uv", "run", "python", "-m", "autifyme_agents.cli.conversation",
                "--scenario", "greeting_to_cataloging",
                "--hitl-mode", "interactive"
            ],
            "timeout": 180
        }
    ]

    # Run each scenario
    for i, scenario in enumerate(test_scenarios, 1):
        safe_print(f"\n{'#'*70}")
        safe_print(f"📨 TEST {i}/{len(test_scenarios)}: {scenario['name']}")
        safe_print(f"{'#'*70}")

        success, output = run_interactive_command(
            scenario["cmd"],
            scenario["name"],
            timeout=scenario["timeout"]
        )

        # Validate database
        db_validation = validate_database()
        safe_print(f"\n🗄️  {db_validation['message']}")

        results.append({
            "test": scenario["name"],
            "success": success,
            "db_validation": db_validation,
            "timestamp": datetime.now().isoformat()
        })

        total_tests += 1
        if success:
            passed_tests += 1

        # Pause between tests
        if i < len(test_scenarios):
            safe_print(f"\n{'-'*70}")
            input(f"Test {i} complete. Press Enter to continue to next test...")

    # Final Summary
    safe_print("\n" + "="*70)
    safe_print("📊 INTERACTIVE TEST SUMMARY")
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
        safe_print(f"{icon} {result['test']}: {'PASSED' if result['success'] else 'FAILED'}")
        if result['db_validation']['success']:
            safe_print(f"   📦 Products in DB: {result['db_validation']['products_count']}")

    # Export results
    report_file = Path(__file__).parent / f"interactive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report_data = {
        "test_mode": "interactive",
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
        safe_print("\n🎉 ALL INTERACTIVE TESTS PASSED!\n")
        sys.exit(0)
    else:
        safe_print(f"\n⚠️  {total_tests - passed_tests} TESTS FAILED\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
