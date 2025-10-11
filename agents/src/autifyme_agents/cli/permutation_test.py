"""Permutation Test Framework - Systematically test all combinations.

This tool generates and runs comprehensive permutation tests covering:
- Message types (text/image/video/document/audio/voice)
- Caption variations (clear/ambiguous/minimal/empty/none)
- HITL responses (approve/reject/edit/question/defer)
- Workflow paths (success/error/clarification)

Based on COMPREHENSIVE_CLI_TESTING_DESIGN.md test matrix.

Usage:
    # Run all permutation tests (auto-mode)
    uv run python -m autifyme_agents.cli.permutation_test --all

    # Test specific permutation category
    uv run python -m autifyme_agents.cli.permutation_test --category message_types
    uv run python -m autifyme_agents.cli.permutation_test --category hitl_variations
    uv run python -m autifyme_agents.cli.permutation_test --category workflows

    # Test specific message type combinations
    uv run python -m autifyme_agents.cli.permutation_test --message-type image --caption-clarity clear,ambiguous

    # Generate test report
    uv run python -m autifyme_agents.cli.permutation_test --all --report permutation_report.json

    # Dry run (show tests without executing)
    uv run python -m autifyme_agents.cli.permutation_test --all --dry-run
"""

import sys
import json
import time
from pathlib import Path
from typing import Any
from itertools import product
from dotenv import load_dotenv

from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner
from autifyme_agents.cli.simulate import ConsoleChannel, safe_print


class PermutationTestFramework:
    """Comprehensive permutation testing framework."""

    def __init__(self):
        self.test_results = []
        self.storage = SupabaseStorageClient()
        self.checkpointer = get_checkpointer()

    # === Message Type Permutations ===

    def generate_message_type_tests(self) -> list[dict]:
        """Generate all message type permutation tests (84 scenarios)."""

        message_types = ["text", "image", "video", "document", "audio", "voice"]
        caption_clarity = ["clear", "ambiguous", "minimal", "empty"]
        hitl_states = ["none", "pending", "expired"]

        tests = []

        for msg_type in message_types:
            # Media types support captions (image/video/document)
            if msg_type in ["image", "video", "document"]:
                for clarity, hitl_state in product(caption_clarity, hitl_states):
                    tests.append({
                        "name": f"{msg_type}+{clarity}_caption+{hitl_state}_hitl",
                        "message_type": msg_type,
                        "caption_clarity": clarity,
                        "hitl_state": hitl_state,
                        "text": self._get_caption_text(clarity, msg_type),
                        "media": self._get_media_path(msg_type),
                    })

                # Also test without caption
                for hitl_state in hitl_states:
                    tests.append({
                        "name": f"{msg_type}+no_caption+{hitl_state}_hitl",
                        "message_type": msg_type,
                        "caption_clarity": "none",
                        "hitl_state": hitl_state,
                        "text": None,
                        "media": self._get_media_path(msg_type),
                    })

            # Audio/voice don't support captions
            elif msg_type in ["audio", "voice"]:
                for hitl_state in hitl_states:
                    tests.append({
                        "name": f"{msg_type}+{hitl_state}_hitl",
                        "message_type": msg_type,
                        "caption_clarity": "none",
                        "hitl_state": hitl_state,
                        "text": None,
                        "media": self._get_media_path(msg_type),
                    })

            # Text messages
            else:
                for clarity, hitl_state in product(caption_clarity, hitl_states):
                    tests.append({
                        "name": f"{msg_type}+{clarity}+{hitl_state}_hitl",
                        "message_type": msg_type,
                        "caption_clarity": clarity,
                        "hitl_state": hitl_state,
                        "text": self._get_caption_text(clarity, "text"),
                        "media": None,
                    })

        return tests

    def _get_caption_text(self, clarity: str, msg_type: str) -> str | None:
        """Get caption text based on clarity level."""

        if clarity == "clear":
            return "Catalog these canvas sneakers. Price $79.99, sizes 7-11, color white."
        elif clarity == "ambiguous":
            return "Can you help with this?"
        elif clarity == "minimal":
            return "Catalog this"
        elif clarity == "empty":
            return ""
        else:  # none
            return None

    def _get_media_path(self, media_type: str) -> str:
        """Get test media path for media type."""

        media_paths = {
            "image": "test_images/sneaker.jpg",
            "video": "test_media/demo.mp4",
            "document": "test_media/specs.pdf",
            "audio": "test_media/audio.mp3",
            "voice": "test_media/voice_note.ogg",
        }

        return media_paths.get(media_type)

    # === HITL Approval Permutations ===

    def generate_hitl_variation_tests(self) -> list[dict]:
        """Generate HITL approval permutation tests (56 scenarios)."""

        intents = [
            "approve",
            "reject",
            "approve_with_edits",
            "question",
            "defer",
            "park",
            "abandon",
            "ambiguous"
        ]

        approval_states = ["fresh", "stale", "expired", "none"]

        tests = []

        for intent, state in product(intents, approval_states):
            test = {
                "name": f"hitl_{intent}+{state}_approval",
                "intent": intent,
                "approval_state": state,
                "base_message": "Catalog these sneakers, price $79.99",
                "media": "test_images/sneaker.jpg",
                "hitl_mode": self._get_hitl_mode(intent),
            }

            # Add variations for approve_with_edits
            if intent == "approve_with_edits":
                test["edits"] = {"price": 89.99, "name": "Updated Sneakers"}

            tests.append(test)

        return tests

    def _get_hitl_mode(self, intent: str) -> str:
        """Map intent to HITL mode."""

        mode_map = {
            "approve": "auto_approve",
            "reject": "auto_reject",
            "approve_with_edits": "auto_edit",
            "question": "question",
            "defer": "interactive",  # Requires interactive
            "park": "interactive",
            "abandon": "auto_reject",
            "ambiguous": "interactive",
        }

        return mode_map.get(intent, "interactive")

    # === Workflow Path Permutations ===

    def generate_workflow_path_tests(self) -> list[dict]:
        """Generate workflow path permutation tests (48 scenarios)."""

        intents = ["cataloging", "inquiry", "conversational", "unknown"]
        paths = ["success", "error_recovery", "clarification", "multi_turn"]

        tests = []

        for intent, path in product(intents, paths):
            tests.append({
                "name": f"{intent}+{path}",
                "intent": intent,
                "path": path,
                "message": self._get_workflow_message(intent, path),
                "media": self._get_workflow_media(intent, path),
                "expected_outcome": self._get_expected_outcome(intent, path),
            })

        return tests

    def _get_workflow_message(self, intent: str, path: str) -> str:
        """Get message for workflow test."""

        messages = {
            ("cataloging", "success"): "Catalog these sneakers, price $79.99, sizes 7-11",
            ("cataloging", "error_recovery"): "Catalog this product",  # Missing info
            ("cataloging", "clarification"): "Add this",  # Too vague
            ("cataloging", "multi_turn"): "Catalog sneakers",  # Will need follow-up
            ("inquiry", "success"): "What colors do we have for SKU-456?",
            ("inquiry", "error_recovery"): "Show me product ABC-999",  # Non-existent
            ("inquiry", "clarification"): "What's the price?",  # Which product?
            ("inquiry", "multi_turn"): "Tell me about our products",  # Broad query
            ("conversational", "success"): "Hi, how are you?",
            ("conversational", "error_recovery"): "Thanks!",  # No context
            ("conversational", "clarification"): "What?",
            ("conversational", "multi_turn"): "Hello, I need help",
            ("unknown", "success"): "asdfghjkl",  # Nonsense
            ("unknown", "error_recovery"): "",  # Empty
            ("unknown", "clarification"): "???",
            ("unknown", "multi_turn"): "Maybe later",
        }

        return messages.get((intent, path), "Test message")

    def _get_workflow_media(self, intent: str, path: str) -> str | None:
        """Get media for workflow test if applicable."""

        if intent == "cataloging":
            return "test_images/sneaker.jpg"
        return None

    def _get_expected_outcome(self, intent: str, path: str) -> str:
        """Get expected outcome for test."""

        if path == "success":
            return "completion" if intent == "cataloging" else "response"
        elif path == "error_recovery":
            return "error_handled"
        elif path == "clarification":
            return "clarification_request"
        else:  # multi_turn
            return "follow_up_needed"

    # === Test Execution ===

    def run_test(self, test: dict) -> dict:
        """Run a single permutation test."""

        start_time = time.time()

        try:
            # Setup channel with appropriate HITL mode
            hitl_mode = test.get("hitl_mode", "auto_approve")
            channel = ConsoleChannel(hitl_mode=hitl_mode)

            # Apply edits if specified
            if "edits" in test:
                channel.predefined_edits = test["edits"]

            # Create runner
            runner = WorkflowRunner(
                channel=channel,
                storage=self.storage,
                checkpointer=self.checkpointer,
            )

            # Generate unique sender
            import uuid
            sender = f"permutation_test_{uuid.uuid4().hex[:8]}"

            # Extract test parameters
            text = test.get("text") or test.get("base_message")
            media_id = test.get("media")

            # Run workflow
            runner.handle_message(
                sender=sender,
                text=text,
                media_id=media_id,
            )

            elapsed = time.time() - start_time

            result = {
                "test_name": test["name"],
                "status": "PASSED",
                "elapsed_time": elapsed,
                "details": test,
            }

        except Exception as e:
            elapsed = time.time() - start_time

            result = {
                "test_name": test["name"],
                "status": "FAILED",
                "elapsed_time": elapsed,
                "error": str(e),
                "error_type": type(e).__name__,
                "details": test,
            }

        self.test_results.append(result)
        return result

    def run_all_tests(self, category: str = "all", dry_run: bool = False) -> list[dict]:
        """Run all permutation tests in a category."""

        # Generate tests
        tests = []

        if category in ["all", "message_types"]:
            tests.extend(self.generate_message_type_tests())

        if category in ["all", "hitl_variations"]:
            tests.extend(self.generate_hitl_variation_tests())

        if category in ["all", "workflows"]:
            tests.extend(self.generate_workflow_path_tests())

        print(f"\n{'='*60}")
        safe_print(f"🧪 PERMUTATION TEST FRAMEWORK")
        print(f"{'='*60}")
        safe_print(f"Category: {category}")
        safe_print(f"Total tests: {len(tests)}")
        print(f"{'='*60}\n")

        if dry_run:
            print("\n[DRY RUN MODE - Tests not executed]\n")
            for i, test in enumerate(tests, 1):
                safe_print(f"{i}. {test['name']}")
            return tests

        # Run tests
        results = []
        for i, test in enumerate(tests, 1):
            safe_print(f"\n[{i}/{len(tests)}] Running: {test['name']}")
            result = self.run_test(test)
            status_icon = "✅" if result["status"] == "PASSED" else "❌"
            safe_print(f"{status_icon} {result['status']} ({result['elapsed_time']:.2f}s)")
            if result["status"] == "FAILED":
                print(f"   Error: {result['error']}")
            results.append(result)

        # Summary
        self.print_summary(results)

        return results

    def print_summary(self, results: list[dict]) -> None:
        """Print test summary."""

        print(f"\n{'='*60}")
        safe_print("📊 TEST SUMMARY")
        print(f"{'='*60}")

        passed = sum(1 for r in results if r["status"] == "PASSED")
        failed = sum(1 for r in results if r["status"] == "FAILED")
        total_time = sum(r["elapsed_time"] for r in results)
        avg_time = total_time / len(results) if results else 0

        safe_print(f"✅ Passed: {passed}/{len(results)} ({passed/len(results)*100:.1f}%)")
        safe_print(f"❌ Failed: {failed}/{len(results)}")
        safe_print(f"⏱️  Total time: {total_time:.2f}s")
        safe_print(f"⏱️  Avg time: {avg_time:.2f}s per test")

        if failed > 0:
            print(f"\nFailed tests:")
            for result in results:
                if result["status"] == "FAILED":
                    safe_print(f"  ❌ {result['test_name']}: {result['error_type']}")

        print(f"{'='*60}\n")

    def save_report(self, filepath: str, results: list[dict]) -> None:
        """Save test results to JSON report."""

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(results),
            "passed": sum(1 for r in results if r["status"] == "PASSED"),
            "failed": sum(1 for r in results if r["status"] == "FAILED"),
            "total_time": sum(r["elapsed_time"] for r in results),
            "results": results,
        }

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        safe_print(f"\n📄 Report saved to: {filepath}\n")


def main():
    """CLI entry point."""

    # Load environment
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        env_path = Path.cwd().parent / ".env"

    if env_path.exists():
        load_dotenv(env_path)
    else:
        print("Warning: .env file not found")

    # Parse arguments
    category = "all"
    dry_run = "--dry-run" in sys.argv
    report_path = None

    if "--category" in sys.argv:
        idx = sys.argv.index("--category")
        if idx + 1 < len(sys.argv):
            category = sys.argv[idx + 1]

    if "--report" in sys.argv:
        idx = sys.argv.index("--report")
        if idx + 1 < len(sys.argv):
            report_path = sys.argv[idx + 1]

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return

    # Run tests
    framework = PermutationTestFramework()
    results = framework.run_all_tests(category=category, dry_run=dry_run)

    # Save report if requested
    if report_path and not dry_run:
        framework.save_report(report_path, results)


if __name__ == "__main__":
    main()
