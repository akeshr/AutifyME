"""Full workflow simulator with comprehensive HITL testing support.

This tool simulates the complete workflow including Runner, PM, Departments,
and HITL approvals - but all locally without WhatsApp.

✨ NEW: Comprehensive Testing Features
- Media + caption support (test WhatsApp caption extraction fix)
- Multiple HITL modes (approve/reject/edit/question/defer)
- Interactive field editing during approval
- All media types (image/video/audio/voice/document)
- Extensive predefined scenarios covering all permutations

Usage:
    # Run single scenario
    uv run python -m autifyme_agents.cli.simulate "Catalog these sneakers, price $79"

    # With media + caption (tests caption extraction)
    uv run python -m autifyme_agents.cli.simulate "Catalog this, price $79" --media test_images/sneaker.jpg

    # Media types (images, videos, voice, documents)
    uv run python -m autifyme_agents.cli.simulate "Catalog this" --media test_images/sneaker.jpg
    uv run python -m autifyme_agents.cli.simulate "Product demo" --media test_media/demo.mp4
    uv run python -m autifyme_agents.cli.simulate "Transcribe this" --media test_audio/voice_note.ogg
    uv run python -m autifyme_agents.cli.simulate "Review specs" --media test_docs/specs.pdf

    # HITL Testing Modes
    uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" --hitl-mode auto_approve
    uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" --hitl-mode auto_reject
    uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" --hitl-mode auto_edit
    uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" --hitl-mode question
    uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" --hitl-mode interactive (default)

    # Interactive mode supports:
    #   - approve/yes: Approve as-is
    #   - reject/no: Reject and cancel
    #   - edit <field> <value>: Edit field and approve (e.g., "edit price 99.99")
    #   - question: Ask clarifying question
    #   - defer: Postpone decision

    # Run predefined scenario
    uv run python -m autifyme_agents.cli.simulate --scenario image_with_clear_caption

    # Run all scenarios (comprehensive test suite)
    uv run python -m autifyme_agents.cli.simulate --all --hitl-mode auto_approve

    # List available scenarios
    uv run python -m autifyme_agents.cli.simulate --scenario

    # Legacy shortcuts
    uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" --auto-approve (same as --hitl-mode auto_approve)
    uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" -y (shorthand for auto-approve)

Available Scenarios:
    Text Messages:
    - text_clear: Clear cataloging request
    - text_ambiguous: Ambiguous intent
    - text_minimal: Minimal information

    Image + Caption:
    - image_with_clear_caption: Image + clear caption (tests caption extraction)
    - image_with_ambiguous_caption: Image + ambiguous caption
    - image_with_minimal_caption: Image + minimal caption
    - image_no_caption: Image only (no caption)

    Video + Caption:
    - video_with_caption: Video + caption
    - video_no_caption: Video only

    Document + Caption:
    - document_with_caption: Document + caption
    - document_no_caption: Document only

    Audio/Voice:
    - voice_message: Voice message (no caption support)

    Other:
    - conversational_greeting: Conversational greeting
    - inquiry_product: Product inquiry
"""

import sys
import json
import time
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.schemas.models import Product, CatalogingResult
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.workflows.orchestration.runner_v2 import WorkflowRunner
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

    def __init__(self, auto_approve: bool = False, hitl_mode: str = "interactive"):
        """Initialize console channel.

        Args:
            auto_approve: If True, automatically approve all HITL requests
            hitl_mode: HITL testing mode:
                - "interactive": Prompt user for approval/edits/questions
                - "auto_approve": Auto-approve all (same as auto_approve=True)
                - "auto_reject": Auto-reject all
                - "auto_edit": Auto-approve with predefined edits
                - "question": Simulate asking clarifying questions
        """
        self.auto_approve = auto_approve
        self.hitl_mode = "auto_approve" if auto_approve else hitl_mode
        self.messages_sent: list[dict[str, Any]] = []
        self.predefined_edits: dict[str, Any] = {}

    def format_thread_id(self, sender: str) -> str:
        return f"console:{sender}"

    def send_text(self, recipient: str, message: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        print(f"\n{'='*60}")
        safe_print(f"📤 MESSAGE TO {recipient}:")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")

        self.messages_sent.append({"type": "text", "message": message})
        return {"status": "sent"}

    def send_hitl_request(self, recipient: str, interrupt_value: Any) -> dict[str, Any]:
        """Generic HITL request handler - works for ANY interrupt type."""
        print(f"\n{'='*60}")
        safe_print(f"⏸️  HITL REQUEST TO {recipient}:")
        print(f"{'='*60}")

        # Handle different interrupt value types
        if hasattr(interrupt_value, 'model_dump'):
            # Pydantic model (Product, etc.)
            draft_dict = interrupt_value.model_dump()
        elif isinstance(interrupt_value, dict):
            draft_dict = interrupt_value
        else:
            draft_dict = {"value": str(interrupt_value)}

        # Custom JSON encoder to handle UUID objects
        def json_encoder(obj):
            if hasattr(obj, '__str__'):
                return str(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        print(json.dumps(draft_dict, indent=2, ensure_ascii=False, default=json_encoder))
        print(f"{'='*60}")

        # Handle different HITL modes
        if self.hitl_mode == "auto_approve":
            print("\n[AUTO-APPROVE MODE: Approving automatically]\n")
            time.sleep(0.5)
            return {"status": "approved", "value": interrupt_value}

        elif self.hitl_mode == "auto_reject":
            print("\n[AUTO-REJECT MODE: Rejecting automatically]\n")
            time.sleep(0.5)
            return {"status": "rejected"}

        elif self.hitl_mode == "auto_edit":
            print("\n[AUTO-EDIT MODE: Approving with edits]\n")
            # Apply predefined edits
            if self.predefined_edits and hasattr(interrupt_value, '__dict__'):
                for field, value in self.predefined_edits.items():
                    if hasattr(interrupt_value, field):
                        setattr(interrupt_value, field, value)
                        safe_print(f"  ✏️  Edited {field}: {value}")
            time.sleep(0.5)
            return {"status": "approved", "value": interrupt_value}

        elif self.hitl_mode == "question":
            print("\n[QUESTION MODE: Simulating clarification question]\n")
            print("User: What's the SKU for this product?")
            time.sleep(0.5)
            return {"status": "question", "question": "What's the SKU for this product?"}

        # Interactive approval (default)
        while True:
            print("\nOptions:")
            print("  1. approve / yes - Approve as-is")
            print("  2. reject / no - Reject and cancel")
            print("  3. edit <field> <value> - Approve with edits (e.g., 'edit price 99.99')")
            print("  4. question - Ask a clarifying question")
            print("  5. defer - Postpone decision")

            decision = input("\nYour decision: ").strip().lower()

            # Parse decision
            if decision in ["yes", "y", "approve", "1"]:
                print("\n[APPROVED]\n")
                return {"status": "approved", "value": interrupt_value}

            elif decision in ["no", "n", "reject", "2"]:
                print("\n[REJECTED]\n")
                return {"status": "rejected"}

            elif decision.startswith("edit") or decision.startswith("3"):
                # Parse edit command: "edit price 99.99" or "edit name New Name"
                parts = decision.split(maxsplit=2)
                if len(parts) >= 3:
                    field = parts[1]
                    value = parts[2]

                    # Try to set the field
                    if hasattr(interrupt_value, field):
                        # Type conversion based on field type
                        field_value = getattr(interrupt_value, field)
                        try:
                            if isinstance(field_value, float):
                                value = float(value)
                            elif isinstance(field_value, int):
                                value = int(value)
                            setattr(interrupt_value, field, value)
                            safe_print(f"\n✏️  Edited {field}: {value}")
                            print("[APPROVED WITH EDITS]\n")
                            return {"status": "approved", "value": interrupt_value}
                        except ValueError:
                            print(f"Error: Invalid value type for {field}")
                    else:
                        print(f"Error: Field '{field}' not found in interrupt value")
                else:
                    print("Usage: edit <field> <value>")

            elif decision in ["question", "4"]:
                question = input("Your question: ").strip()
                print(f"\n[QUESTION: {question}]\n")
                return {"status": "question", "question": question}

            elif decision in ["defer", "5"]:
                print("\n[DEFERRED]\n")
                return {"status": "deferred"}

            else:
                print("Invalid option. Try again.")

    def send_completion(self, recipient: str, result: CatalogingResult) -> dict[str, Any]:
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
    hitl_mode: str = "interactive",
    predefined_edits: dict[str, Any] | None = None,
    media_type: str = "image",
):
    """Run a test scenario through full workflow.

    Args:
        name: Scenario name for display
        text: User's text message (can be caption if media present)
        image_path: Optional path to media file
        auto_approve: If True, auto-approve HITL requests
        hitl_mode: HITL testing mode (interactive/auto_approve/auto_reject/auto_edit/question)
        predefined_edits: Edits to apply in auto_edit mode
        media_type: Type of media (image/video/audio/voice/document)
    """
    print(f"\n{'#'*60}")
    safe_print(f"🎬 SCENARIO: {name}")
    print(f"{'#'*60}\n")

    start_time = time.time()

    # Setup
    storage = SupabaseStorageClient()
    channel = ConsoleChannel(auto_approve=auto_approve, hitl_mode=hitl_mode)
    if predefined_edits:
        channel.predefined_edits = predefined_edits
    checkpointer = get_checkpointer()

    # Create runner
    runner = WorkflowRunner(
        channel=channel,
        storage=storage,
        checkpointer=checkpointer,
    )

    # Display inputs
    safe_print("📝 User Input:")
    if text and image_path:
        safe_print(f"   Caption: {text}")
        safe_print(f"   Media ({media_type}): {image_path}")
    elif text:
        print(f"   Text: {text}")
    elif image_path:
        safe_print(f"   Media ({media_type}): {image_path} (no caption)")

    if image_path and not image_path.exists():
        safe_print("   ⚠️  Warning: Media file not found")
    print()

    # Run scenario with unique sender to avoid checkpoint pollution
    import uuid
    unique_sender = f"local_test_{uuid.uuid4().hex[:8]}"

    try:
        runner.handle_message(
            sender=unique_sender,
            text=text,
            media_id=str(image_path) if image_path else None,
        )

        # If auto-approve/reject/edit mode, send follow-up approval message
        # This simulates user responding to HITL interrupt
        if hitl_mode in ["auto_approve", "auto_reject", "auto_edit"]:
            time.sleep(0.5)  # Brief pause to simulate user thinking
            print(f"\n{'='*60}")
            print(f"📨 AUTO-MODE: Sending follow-up {'approval' if hitl_mode != 'auto_reject' else 'rejection'} message")
            print(f"{'='*60}\n")

            # Send appropriate follow-up message
            if hitl_mode == "auto_approve":
                follow_up_text = "approve"
            elif hitl_mode == "auto_reject":
                follow_up_text = "reject"
            elif hitl_mode == "auto_edit":
                # Apply predefined edits in the follow-up
                if predefined_edits:
                    edits = ", ".join(f"{k}={v}" for k, v in predefined_edits.items())
                    follow_up_text = f"approve with edits: {edits}"
                else:
                    follow_up_text = "approve"

            runner.handle_message(
                sender=unique_sender,
                text=follow_up_text,
                media_id=None,
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
    """Return predefined test scenarios covering all permutations."""
    return {
        # === PART 1: Message Type Permutations (Text Messages) ===
        "text_clear": {
            "name": "Text - Clear cataloging request",
            "text": "Catalog these sneakers: Canvas material, price $79.99, sizes 7-11, color white",
            "image": None,
            "media_type": None,
        },
        "text_ambiguous": {
            "name": "Text - Ambiguous intent",
            "text": "Can you help with this product?",
            "image": None,
            "media_type": None,
        },
        "text_minimal": {
            "name": "Text - Minimal information",
            "text": "Add sneakers",
            "image": None,
            "media_type": None,
        },

        # === PART 2: Image + Caption Permutations ===
        "image_with_clear_caption": {
            "name": "Image + Clear Caption",
            "text": "Catalog these canvas sneakers. Price $79.99, sizes 7-11.",
            "image": "test_images/sneaker.jpg",
            "media_type": "image",
        },
        "image_with_ambiguous_caption": {
            "name": "Image + Ambiguous Caption",
            "text": "What do you think?",
            "image": "test_images/sneaker.jpg",
            "media_type": "image",
        },
        "image_with_minimal_caption": {
            "name": "Image + Minimal Caption",
            "text": "Catalog this",
            "image": "test_images/sneaker.jpg",
            "media_type": "image",
        },
        "image_no_caption": {
            "name": "Image Only (no caption)",
            "text": None,
            "image": "test_images/sneaker.jpg",
            "media_type": "image",
        },

        # === PART 3: Video + Caption Permutations ===
        "video_with_caption": {
            "name": "Video + Caption",
            "text": "Product demo - price $49.99",
            "image": "test_media/product_demo.mp4",
            "media_type": "video",
        },
        "video_no_caption": {
            "name": "Video Only (no caption)",
            "text": None,
            "image": "test_media/product_demo.mp4",
            "media_type": "video",
        },

        # === PART 4: Document + Caption Permutations ===
        "document_with_caption": {
            "name": "Document + Caption",
            "text": "Product spec sheet - catalog all items",
            "image": "test_media/product_specs.pdf",
            "media_type": "document",
        },
        "document_no_caption": {
            "name": "Document Only (no caption)",
            "text": None,
            "image": "test_media/product_specs.pdf",
            "media_type": "document",
        },

        # === PART 5: Audio/Voice Messages (no captions) ===
        "voice_message": {
            "name": "Voice Message",
            "text": None,
            "image": "test_media/voice_note.ogg",
            "media_type": "voice",
        },

        # === PART 6: Conversational & Inquiry ===
        "conversational_greeting": {
            "name": "Conversational - Greeting",
            "text": "Hi, how are you?",
            "image": None,
            "media_type": None,
        },
        "inquiry_product": {
            "name": "Product Inquiry",
            "text": "What colors do we have for SKU-456?",
            "image": None,
            "media_type": None,
        },

        # === Legacy scenarios for backward compatibility ===
        "cataloging_with_image": {
            "name": "Legacy - Cataloging with Text + Image",
            "text": "Catalog these canvas sneakers. Price $79.99, sizes 7-11.",
            "image": "test_images/sneaker.jpg",
            "media_type": "image",
        },
        "cataloging_text_only": {
            "name": "Legacy - Cataloging with Text Only",
            "text": "Add a new product: Blue Cotton T-Shirt, price $29.99, sizes S-XL",
            "image": None,
            "media_type": None,
        },
    }


def run_all_scenarios(auto_approve: bool = False, hitl_mode: str = "interactive"):
    """Run all predefined scenarios."""
    scenarios = get_predefined_scenarios()

    print(f"\n{'*'*60}")
    safe_print(f"🚀 RUNNING ALL SCENARIOS ({len(scenarios)} total)")
    print(f"{'*'*60}\n")

    results = []

    for scenario_id, scenario in scenarios.items():
        try:
            image_path = Path(scenario["image"]) if scenario.get("image") else None
            media_type = scenario.get("media_type", "image")
            run_scenario(
                name=scenario["name"],
                text=scenario.get("text"),
                image_path=image_path,
                auto_approve=auto_approve,
                hitl_mode=hitl_mode,
                media_type=media_type,
            )
            results.append({"scenario": scenario["name"], "status": "PASSED"})

        except Exception as e:
            results.append({
                "scenario": scenario["name"],
                "status": "FAILED",
                "error": str(e),
            })

        if hitl_mode == "interactive":
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

    return results


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

    # Parse HITL mode
    hitl_mode = "interactive"
    if "--hitl-mode" in sys.argv:
        idx = sys.argv.index("--hitl-mode")
        if idx + 1 < len(sys.argv):
            hitl_mode = sys.argv[idx + 1]
    elif auto_approve:
        hitl_mode = "auto_approve"

    if len(sys.argv) > 1:
        if sys.argv[1] in ["--help", "-h"]:
            print(__doc__)
            return

        if sys.argv[1] in ["--all", "-a"]:
            run_all_scenarios(auto_approve=auto_approve, hitl_mode=hitl_mode)
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
            image_path = Path(scenario["image"]) if scenario.get("image") else None
            media_type = scenario.get("media_type", "image")
            run_scenario(
                name=scenario["name"],
                text=scenario.get("text"),
                image_path=image_path,
                auto_approve=auto_approve,
                hitl_mode=hitl_mode,
                media_type=media_type,
            )
            return

        if sys.argv[1] in ["--media", "--image", "-img"]:
            if len(sys.argv) < 4:
                print("Usage: simulate --media <path> 'Your message'")
                sys.exit(1)
            media_path = Path(sys.argv[2])
            message = " ".join(sys.argv[3:])
            run_scenario("Custom", message, media_path, auto_approve, hitl_mode)
            return

        # Default: treat as message
        if sys.argv[1].startswith("-"):
            # Skip argument parsing flags
            if sys.argv[1] not in ["--hitl-mode"]:
                print("Unknown option:", sys.argv[1])
                print("Use --help for usage information")
                sys.exit(1)

        message = " ".join(arg for arg in sys.argv[1:] if not arg.startswith("-") and arg not in ["interactive", "auto_approve", "auto_reject", "auto_edit", "question"])
        if message:
            run_scenario("Custom", message, auto_approve=auto_approve, hitl_mode=hitl_mode)
    else:
        print(__doc__)
        print("\nNo scenario provided. Use --all to run all scenarios.\n")


if __name__ == "__main__":
    main()
