"""Full workflow simulator with HITL support.

This tool simulates the complete workflow including Runner, PM, Departments,
and HITL approvals - but all locally without WhatsApp.

Usage:
    # Run single scenario
    uv run python -m autifyme_agents.cli.simulate "Catalog these sneakers, price $79"

    # With media (images, videos, voice, documents)
    uv run python -m autifyme_agents.cli.simulate "Catalog this" --media test_images/sneaker.jpg
    uv run python -m autifyme_agents.cli.simulate "Transcribe this" --media test_audio/voice_note.ogg

    # Legacy --image flag (still supported)
    uv run python -m autifyme_agents.cli.simulate "Catalog this" --image test_images/product.jpg

    # Run predefined scenario
    uv run python -m autifyme_agents.cli.simulate --scenario cataloging_with_image

    # Run all scenarios
    uv run python -m autifyme_agents.cli.simulate --all

    # Auto-approve (skip HITL prompts)
    uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" --auto-approve
"""

import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner
from autifyme_agents.workflows.channels.protocol import MessagingChannel


def safe_print(text: str) -> None:
    """Print text safely, handling console encoding issues on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback: encode to ASCII, replacing unencodable chars
        print(text.encode('ascii', errors='replace').decode('ascii'))


class ConsoleChannel(MessagingChannel):
    """Console-based messaging channel for local testing."""

    def __init__(self, auto_approve: bool = False):
        self.auto_approve = auto_approve
        self.messages_sent = []

    def format_thread_id(self, sender: str) -> str:
        return f"console:{sender}"

    def send_text(self, recipient: str, message: str, *, preview_url: bool = False) -> dict:
        print(f"\n{'='*60}")
        safe_print(f"📤 MESSAGE TO {recipient}:")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")

        self.messages_sent.append({"type": "text", "message": message})
        return {"status": "sent"}

    def send_approval_request(self, recipient: str, draft: dict) -> dict:
        print(f"\n{'='*60}")
        safe_print(f"⏸️  APPROVAL REQUEST TO {recipient}:")
        print(f"{'='*60}")
        print(json.dumps(draft, indent=2, ensure_ascii=False))
        print(f"{'='*60}")

        if self.auto_approve:
            print("\n[AUTO-APPROVE MODE: Approving automatically]\n")
            time.sleep(1)
            return {"status": "approved", "draft": draft}

        # Interactive approval
        while True:
            decision = input("\nApprove / Reject? (yes/no): ").strip().lower()
            if decision in ["yes", "y", "approve"]:
                print("\n[APPROVED]\n")
                return {"status": "approved", "draft": draft}
            elif decision in ["no", "n", "reject"]:
                print("\n[REJECTED]\n")
                return {"status": "rejected"}
            else:
                print("Please answer 'yes' or 'no'")

    def send_completion(self, recipient: str, result: dict) -> dict:
        print(f"\n{'='*60}")
        safe_print(f"✅ COMPLETION MESSAGE TO {recipient}:")
        print(f"{'='*60}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"{'='*60}\n")

        self.messages_sent.append({"type": "completion", "result": result})
        return {"status": "sent"}

    def send_error(self, recipient: str, error_type: str, custom_message: str | None = None) -> dict:
        print(f"\n{'='*60}")
        safe_print(f"❌ ERROR MESSAGE TO {recipient}:")
        print(f"{'='*60}")
        print(f"Error Type: {error_type}")
        if custom_message:
            print(f"Message: {custom_message}")
        print(f"{'='*60}\n")

        self.messages_sent.append({"type": "error", "error_type": error_type})
        return {"status": "sent"}

    def download_media(self, media_id: str) -> Path:
        # For local testing, media_id is already a path
        return Path(media_id)


def run_scenario(
    name: str,
    text: str | None,
    image_path: Path | None = None,
    auto_approve: bool = False,
):
    """Run a test scenario through full workflow.

    Args:
        name: Scenario name for display
        text: User's text message
        image_path: Optional path to image
        auto_approve: If True, auto-approve HITL requests
    """
    print(f"\n{'#'*60}")
    safe_print(f"🎬 SCENARIO: {name}")
    print(f"{'#'*60}\n")

    start_time = time.time()

    # Setup
    storage = SupabaseStorageClient()
    channel = ConsoleChannel(auto_approve=auto_approve)
    checkpointer = get_checkpointer()

    # Create runner
    runner = WorkflowRunner(
        channel=channel,
        storage=storage,
        checkpointer=checkpointer,
    )

    # Display inputs
    safe_print("📝 User Input:")
    if text:
        print(f"   Text: {text}")
    if image_path:
        if image_path.exists():
            safe_print(f"   Image: {image_path} ✓")
        else:
            safe_print(f"   Image: {image_path} ⚠️ (not found)")
    print()

    # Run scenario
    try:
        runner.handle_message(
            sender="local_test_user",
            text=text,
            media_id=str(image_path) if image_path else None,
        )

        elapsed = time.time() - start_time
        print(f"\n{'#'*60}")
        safe_print(f"✅ SCENARIO COMPLETE: {name}")
        safe_print(f"⏱️  Elapsed time: {elapsed:.2f}s")
        print(f"{'#'*60}\n")

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n{'#'*60}")
        safe_print(f"❌ SCENARIO FAILED: {name}")
        safe_print(f"⏱️  Elapsed time: {elapsed:.2f}s")
        print(f"Error: {type(e).__name__}: {e}")
        print(f"{'#'*60}\n")
        raise


def get_predefined_scenarios():
    """Return predefined test scenarios."""
    return {
        "cataloging_with_image": {
            "name": "Cataloging with Text + Image",
            "text": "Catalog these canvas sneakers. Price $79.99, sizes 7-11.",
            "image": "test_images/sneaker.jpg",
        },
        "cataloging_text_only": {
            "name": "Cataloging with Text Only",
            "text": "Add a new product: Blue Cotton T-Shirt, price $29.99, sizes S-XL",
            "image": None,
        },
        "ambiguous_image": {
            "name": "Ambiguous - Image Only",
            "text": None,
            "image": "test_images/product.jpg",
        },
        "conversational": {
            "name": "Conversational - Greeting",
            "text": "Hi, how are you?",
            "image": None,
        },
        "inquiry": {
            "name": "Product Inquiry",
            "text": "What colors do we have for SKU-456?",
            "image": None,
        },
    }


def run_all_scenarios(auto_approve: bool = False):
    """Run all predefined scenarios."""
    scenarios = get_predefined_scenarios()

    print(f"\n{'*'*60}")
    safe_print(f"🚀 RUNNING ALL SCENARIOS ({len(scenarios)} total)")
    print(f"{'*'*60}\n")

    results = []

    for scenario_id, scenario in scenarios.items():
        try:
            image_path = Path(scenario["image"]) if scenario["image"] else None
            run_scenario(
                name=scenario["name"],
                text=scenario["text"],
                image_path=image_path,
                auto_approve=auto_approve,
            )
            results.append({"scenario": scenario["name"], "status": "PASSED"})

        except Exception as e:
            results.append({
                "scenario": scenario["name"],
                "status": "FAILED",
                "error": str(e),
            })

        if not auto_approve:
            input("\nPress Enter to continue to next scenario...")

    # Summary
    print(f"\n{'*'*60}")
    safe_print("📊 SUMMARY:")
    print(f"{'*'*60}")
    passed = sum(1 for r in results if r["status"] == "PASSED")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    safe_print(f"✅ Passed: {passed}")
    safe_print(f"❌ Failed: {failed}")
    print()
    for result in results:
        status_icon = "✅" if result["status"] == "PASSED" else "❌"
        safe_print(f"{status_icon} {result['scenario']}: {result['status']}")
        if "error" in result:
            print(f"   Error: {result['error']}")
    print(f"{'*'*60}\n")


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
    auto_approve = "--auto-approve" in sys.argv or "-y" in sys.argv

    if len(sys.argv) > 1:
        if sys.argv[1] in ["--help", "-h"]:
            print(__doc__)
            return

        if sys.argv[1] in ["--all", "-a"]:
            run_all_scenarios(auto_approve=auto_approve)
            return

        if sys.argv[1] in ["--scenario", "-s"]:
            if len(sys.argv) < 3:
                print("Available scenarios:")
                for scenario_id, scenario in get_predefined_scenarios().items():
                    print(f"  {scenario_id}: {scenario['name']}")
                return

            scenario_id = sys.argv[2]
            scenarios = get_predefined_scenarios()

            if scenario_id not in scenarios:
                print(f"Unknown scenario: {scenario_id}")
                print("\nAvailable scenarios:")
                for sid, scenario in scenarios.items():
                    print(f"  {sid}: {scenario['name']}")
                sys.exit(1)

            scenario = scenarios[scenario_id]
            image_path = Path(scenario["image"]) if scenario["image"] else None
            run_scenario(
                name=scenario["name"],
                text=scenario["text"],
                image_path=image_path,
                auto_approve=auto_approve,
            )
            return

        if sys.argv[1] in ["--media", "--image", "-img"]:
            if len(sys.argv) < 4:
                print("Usage: simulate --media <path> 'Your message'")
                sys.exit(1)
            media_path = Path(sys.argv[2])
            message = " ".join(sys.argv[3:])
            run_scenario("Custom", message, media_path, auto_approve)
            return

        # Default: treat as message
        if sys.argv[1].startswith("-"):
            print("Unknown option:", sys.argv[1])
            print("Use --help for usage information")
            sys.exit(1)

        message = " ".join(arg for arg in sys.argv[1:] if not arg.startswith("-"))
        run_scenario("Custom", message, auto_approve=auto_approve)
    else:
        print(__doc__)
        print("\nNo scenario provided. Use --all to run all scenarios.\n")


if __name__ == "__main__":
    main()
