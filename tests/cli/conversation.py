"""Multi-turn conversation testing framework.

This tool tests conversation continuity and context preservation across multiple
message exchanges, simulating realistic WhatsApp conversation flows.

Features:
- YAML-based conversation scripts (declarative, reusable)
- Multi-turn conversation execution with timing controls
- Context validation (state preservation, message history tracking)
- Support for all message types (text, media, voice, documents)
- HITL testing modes (approve/reject/edit/question)
- State inspection at each turn
- Conversation flow visualization

Usage:
    # Run single conversation scenario
    uv run python -m autifyme_agents.cli.conversation --scenario greeting_to_cataloging

    # Run with specific HITL mode
    uv run python -m autifyme_agents.cli.conversation --scenario clarification_flow --hitl-mode auto_approve

    # Run all conversation scenarios
    uv run python -m autifyme_agents.cli.conversation --all

    # List available scenarios
    uv run python -m autifyme_agents.cli.conversation --list

    # Debug mode (verbose state inspection)
    uv run python -m autifyme_agents.cli.conversation --scenario greeting_to_cataloging --debug

Conversation Script Format (YAML):
    name: "Greeting to Cataloging Flow"
    description: "User greets, then catalogs a product"
    sender: "test_user_123"
    hitl_mode: "auto_approve"  # optional, defaults to interactive

    turns:
      - turn: 1
        text: "Hi, how are you?"
        wait: 0.5  # seconds to wait before next turn
        expected_intent: "conversational"
        validate_context:
          - conversation_history_length: 2  # user message + PM response
          - no_pending_approval: true

      - turn: 2
        text: "Catalog these sneakers"
        media: "test_images/sneaker.jpg"
        media_type: "image"
        wait: 1.0
        expected_intent: "cataloging"
        validate_context:
          - conversation_history_length: 4
          - pending_approval: true
          - approval_has_image_data: true

Available Scenarios:
    greeting_to_cataloging - Greeting followed by product cataloging
    clarification_flow - Ambiguous request → clarification → answer
    approval_followup - Catalog → approve → ask follow-up question
    multi_product - Catalog multiple products in sequence
    conversation_mixed - Mix of greetings, questions, and cataloging
"""

import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from dotenv import load_dotenv

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.integrations.storage.storage_factory import get_storage
from autifyme_agents.schemas.models import CatalogingResult, Product
from autifyme_agents.workflows.channels.protocol import MessagingChannel
from autifyme_agents.workflows.orchestration.runner_v2 import WorkflowRunner


def safe_print(text: str) -> None:
    """Print text safely, handling console encoding issues on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback: encode to ASCII, replacing unencodable chars
        print(text.encode('ascii', errors='replace').decode('ascii'))


class ConversationChannel(MessagingChannel):
    """Console-based messaging channel for conversation testing with state tracking."""

    def __init__(self, hitl_mode: str = "interactive", debug: bool = False):
        """Initialize conversation channel.

        Args:
            hitl_mode: HITL testing mode (interactive/auto_approve/auto_reject/auto_edit/question)
            debug: If True, enable verbose state inspection
        """
        self.hitl_mode = hitl_mode
        self.debug = debug
        self.messages_sent: list[dict[str, Any]] = []
        self.approvals_requested: list[dict[str, Any]] = []
        self.turn_number = 0

    def format_thread_id(self, sender: str) -> str:
        return f"conversation:{sender}"

    def send_text(self, recipient: str, message: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send text message and track it."""
        self.turn_number += 1

        if self.debug:
            print(f"\n{'='*60}")
            safe_print(f"📤 [TURN {self.turn_number}] MESSAGE TO {recipient}:")
            print(f"{'='*60}")
            print(message)
            print(f"{'='*60}\n")
        else:
            print(f"\n📤 PM: {message[:100]}{'...' if len(message) > 100 else ''}")

        self.messages_sent.append({
            "turn": self.turn_number,
            "type": "text",
            "message": message,
            "recipient": recipient,
        })
        return {"status": "sent"}

    def send_approval_request(self, recipient: str, draft: Product) -> dict[str, Any]:
        """Send approval request and track it."""
        self.turn_number += 1

        print(f"\n{'='*60}")
        safe_print(f"⏸️  [TURN {self.turn_number}] APPROVAL REQUEST TO {recipient}:")
        print(f"{'='*60}")

        # Convert Pydantic model to dict for JSON serialization
        draft_dict = draft.model_dump() if hasattr(draft, 'model_dump') else draft

        # Custom JSON encoder to handle UUID objects
        def json_encoder(obj):
            if hasattr(obj, '__str__'):
                return str(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        print(json.dumps(draft_dict, indent=2, ensure_ascii=False, default=json_encoder))
        print(f"{'='*60}")

        # Track approval
        self.approvals_requested.append({
            "turn": self.turn_number,
            "draft": draft_dict,
        })

        # Handle HITL modes
        if self.hitl_mode == "auto_approve":
            print("\n[AUTO-APPROVE MODE: Approving automatically]\n")
            time.sleep(0.3)
            return {"status": "approved", "draft": draft}

        elif self.hitl_mode == "auto_reject":
            print("\n[AUTO-REJECT MODE: Rejecting automatically]\n")
            time.sleep(0.3)
            return {"status": "rejected"}

        elif self.hitl_mode == "auto_edit":
            print("\n[AUTO-EDIT MODE: Approving with minor edit]\n")
            # Apply minor edit for testing
            if hasattr(draft, 'price') and draft.price:
                draft.price = draft.price + 0.01
                safe_print(f"  ✏️  Edited price: {draft.price}")
            time.sleep(0.3)
            return {"status": "approved", "draft": draft}

        elif self.hitl_mode == "question":
            print("\n[QUESTION MODE: Simulating clarification question]\n")
            print("User: What's the SKU for this product?")
            time.sleep(0.3)
            return {"status": "question", "question": "What's the SKU for this product?"}

        # Interactive approval
        while True:
            print("\nOptions: approve / reject / edit <field> <value> / question / defer")
            decision = input("Your decision: ").strip().lower()

            if decision in ["approve", "yes", "y"]:
                print("\n[APPROVED]\n")
                return {"status": "approved", "draft": draft}

            elif decision in ["reject", "no", "n"]:
                print("\n[REJECTED]\n")
                return {"status": "rejected"}

            elif decision.startswith("edit"):
                parts = decision.split(maxsplit=2)
                if len(parts) >= 3:
                    field = parts[1]
                    value_str = parts[2]
                    if hasattr(draft, field):
                        try:
                            field_value = getattr(draft, field)
                            typed_value: int | float | str
                            if isinstance(field_value, float):
                                typed_value = float(value_str)
                            elif isinstance(field_value, int):
                                typed_value = int(value_str)
                            else:
                                typed_value = value_str
                            setattr(draft, field, typed_value)
                            safe_print(f"\n✏️  Edited {field}: {typed_value}")
                            print("[APPROVED WITH EDITS]\n")
                            return {"status": "approved", "draft": draft}
                        except ValueError:
                            print(f"Error: Invalid value type for {field}")
                    else:
                        print(f"Error: Field '{field}' not found")
                else:
                    print("Usage: edit <field> <value>")

            elif decision == "question":
                question = input("Your question: ").strip()
                print(f"\n[QUESTION: {question}]\n")
                return {"status": "question", "question": question}

            elif decision == "defer":
                print("\n[DEFERRED]\n")
                return {"status": "deferred"}

            else:
                print("Invalid option. Try again.")

    def send_completion(self, recipient: str, result: CatalogingResult) -> dict[str, Any]:
        """Send completion message and track it."""
        self.turn_number += 1

        if self.debug:
            print(f"\n{'='*60}")
            safe_print(f"✅ [TURN {self.turn_number}] COMPLETION MESSAGE TO {recipient}:")
            print(f"{'='*60}")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print(f"{'='*60}\n")
        else:
            print("\n✅ Workflow complete")

        self.messages_sent.append({
            "turn": self.turn_number,
            "type": "completion",
            "result": result,
        })
        return {"status": "sent"}

    def send_error(self, recipient: str, error_type: str, custom_message: str | None = None) -> dict:
        """Send error message and track it."""
        self.turn_number += 1

        print(f"\n{'='*60}")
        safe_print(f"❌ [TURN {self.turn_number}] ERROR MESSAGE TO {recipient}:")
        print(f"{'='*60}")
        print(f"Error Type: {error_type}")
        if custom_message:
            print(f"Message: {custom_message}")
        print(f"{'='*60}\n")

        self.messages_sent.append({
            "turn": self.turn_number,
            "type": "error",
            "error_type": error_type,
            "custom_message": custom_message,
        })
        return {"status": "sent"}

    def download_media(self, media_id: str) -> Path:
        """Download media (for local testing, media_id is already a path)."""
        return Path(media_id)


class ConversationPlayer:
    """Executes multi-turn conversation scenarios with state validation."""

    def __init__(self, debug: bool = False):
        """Initialize conversation player.

        Args:
            debug: If True, enable verbose state inspection
        """
        self.debug = debug
        self.storage: StorageInterface = get_storage()
        self.checkpointer = get_checkpointer()

    def play_conversation(self, scenario_path: Path, hitl_mode: str = "interactive") -> dict[str, Any]:
        """Play a conversation scenario from YAML file.

        Args:
            scenario_path: Path to YAML conversation scenario file
            hitl_mode: HITL testing mode

        Returns:
            Conversation report with turns, validations, and summary
        """
        # Load scenario
        with open(scenario_path, encoding='utf-8') as f:
            scenario = yaml.safe_load(f)

        name = scenario.get('name', scenario_path.stem)
        description = scenario.get('description', '')
        sender = scenario.get('sender', f"conv_test_{int(time.time())}")
        turns = scenario.get('turns', [])
        scenario_hitl_mode = scenario.get('hitl_mode', hitl_mode)

        print(f"\n{'#'*70}")
        safe_print(f"🎭 CONVERSATION: {name}")
        if description:
            safe_print(f"📝 {description}")
        safe_print(f"👤 Sender: {sender}")
        safe_print(f"🔧 HITL Mode: {scenario_hitl_mode}")
        safe_print(f"🔄 Turns: {len(turns)}")
        print(f"{'#'*70}\n")

        # Create channel and runner
        channel = ConversationChannel(hitl_mode=scenario_hitl_mode, debug=self.debug)
        runner = WorkflowRunner(
            channel=channel,
            storage=self.storage,
            checkpointer=self.checkpointer,
        )

        # Execute turns
        start_time = time.time()
        turn_results = []

        for i, turn_config in enumerate(turns, 1):
            turn_result = self._execute_turn(
                runner=runner,
                channel=channel,
                sender=sender,
                turn_number=i,
                turn_config=turn_config,
            )
            turn_results.append(turn_result)

            # Wait before next turn
            wait_time = turn_config.get('wait', 0.5)
            if i < len(turns):
                if self.debug:
                    safe_print(f"⏳ Waiting {wait_time}s before next turn...")
                time.sleep(wait_time)

        elapsed = time.time() - start_time

        # Generate report
        report = {
            "scenario": name,
            "description": description,
            "sender": sender,
            "hitl_mode": scenario_hitl_mode,
            "total_turns": len(turns),
            "elapsed_time": elapsed,
            "turns": turn_results,
            "summary": self._generate_summary(turn_results),
        }

        self._print_report(report)

        return report

    def _execute_turn(
        self,
        runner: WorkflowRunner,
        channel: ConversationChannel,
        sender: str,
        turn_number: int,
        turn_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a single conversation turn.

        Args:
            runner: WorkflowRunner instance
            channel: ConversationChannel instance
            sender: Sender ID
            turn_number: Turn number (1-indexed)
            turn_config: Turn configuration from YAML

        Returns:
            Turn result with validations
        """
        print(f"\n{'-'*70}")
        safe_print(f"🔵 TURN {turn_number}")
        print(f"{'-'*70}")

        text = turn_config.get('text')
        media = turn_config.get('media')
        media_type = turn_config.get('media_type', 'image')
        expected_intent = turn_config.get('expected_intent')
        validate_context = turn_config.get('validate_context', [])

        # Display turn input
        safe_print(f"👤 User: {text}" if text else "👤 User: [media only]")
        if media:
            safe_print(f"📎 Media ({media_type}): {media}")
        if expected_intent:
            safe_print(f"🎯 Expected Intent: {expected_intent}")
        print()

        # Track state before turn
        messages_before = len(channel.messages_sent)
        approvals_before = len(channel.approvals_requested)

        # Execute turn
        turn_start = time.time()
        try:
            media_path = Path(media) if media else None

            runner.handle_message(
                sender=sender,
                text=text,
                media_id=str(media_path) if media_path else None,
            )

            turn_elapsed = time.time() - turn_start
            status = "success"
            error = None

        except Exception as e:
            turn_elapsed = time.time() - turn_start
            status = "error"
            error = f"{type(e).__name__}: {e}"
            safe_print(f"❌ Error: {error}")

        # Track state after turn
        messages_after = len(channel.messages_sent)
        approvals_after = len(channel.approvals_requested)

        # Validate context if specified
        validation_results = []
        if validate_context:
            validation_results = self._validate_context(
                channel=channel,
                validations=validate_context,
                turn_number=turn_number,
            )

        turn_result = {
            "turn": turn_number,
            "text": text,
            "media": media,
            "media_type": media_type if media else None,
            "expected_intent": expected_intent,
            "status": status,
            "error": error,
            "elapsed": turn_elapsed,
            "messages_sent": messages_after - messages_before,
            "approvals_requested": approvals_after - approvals_before,
            "validations": validation_results,
        }

        # Print turn summary
        if self.debug:
            safe_print(f"✅ Turn {turn_number} complete in {turn_elapsed:.2f}s")
            safe_print(f"   Messages sent: {turn_result['messages_sent']}")
            safe_print(f"   Approvals requested: {turn_result['approvals_requested']}")
            if validation_results:
                passed = sum(1 for v in validation_results if v['passed'])
                safe_print(f"   Validations: {passed}/{len(validation_results)} passed")

        return turn_result

    def _validate_context(
        self,
        channel: ConversationChannel,
        validations: list[dict[str, Any]],
        turn_number: int,
    ) -> list[dict[str, Any]]:
        """Validate context preservation after a turn.

        Args:
            channel: ConversationChannel instance
            validations: List of validation rules from YAML
            turn_number: Current turn number

        Returns:
            List of validation results
        """
        if self.debug:
            print(f"\n🔍 Validating context (turn {turn_number}):")

        results = []

        for validation in validations:
            for rule, expected_value in validation.items():
                passed = False
                actual_value = None
                message = ""

                try:
                    # Conversation history length
                    if rule == "conversation_history_length":
                        actual_value = len(channel.messages_sent)
                        passed = actual_value == expected_value
                        message = f"Message count: {actual_value} (expected {expected_value})"

                    # Pending approval check
                    elif rule == "pending_approval":
                        actual_value = len(channel.approvals_requested) > 0
                        passed = actual_value == expected_value
                        message = f"Has pending approval: {actual_value} (expected {expected_value})"

                    # No pending approval check
                    elif rule == "no_pending_approval":
                        actual_value = len(channel.approvals_requested) == 0
                        passed = actual_value == expected_value
                        message = f"No pending approval: {actual_value} (expected {expected_value})"

                    # Approval has image data
                    elif rule == "approval_has_image_data":
                        if channel.approvals_requested:
                            last_approval = channel.approvals_requested[-1]
                            actual_value = 'image_path' in last_approval['draft'] or 'media_path' in last_approval['draft']
                            passed = actual_value == expected_value
                            message = f"Approval has image: {actual_value} (expected {expected_value})"
                        else:
                            passed = False
                            message = "No approvals to check"

                    else:
                        message = f"Unknown validation rule: {rule}"

                except Exception as e:
                    message = f"Validation error: {e}"

                result = {
                    "rule": rule,
                    "expected": expected_value,
                    "actual": actual_value,
                    "passed": passed,
                    "message": message,
                }
                results.append(result)

                if self.debug:
                    icon = "✅" if passed else "❌"
                    safe_print(f"   {icon} {message}")

        return results

    def _generate_summary(self, turn_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate conversation summary from turn results."""
        total_turns = len(turn_results)
        successful_turns = sum(1 for t in turn_results if t['status'] == 'success')
        failed_turns = sum(1 for t in turn_results if t['status'] == 'error')
        total_messages = sum(t['messages_sent'] for t in turn_results)
        total_approvals = sum(t['approvals_requested'] for t in turn_results)

        # Validation summary
        all_validations = [v for t in turn_results for v in t.get('validations', [])]
        total_validations = len(all_validations)
        passed_validations = sum(1 for v in all_validations if v['passed'])

        return {
            "total_turns": total_turns,
            "successful_turns": successful_turns,
            "failed_turns": failed_turns,
            "total_messages": total_messages,
            "total_approvals": total_approvals,
            "total_validations": total_validations,
            "passed_validations": passed_validations,
            "validation_pass_rate": f"{(passed_validations / total_validations * 100):.1f}%" if total_validations > 0 else "N/A",
        }

    def _print_report(self, report: dict[str, Any]) -> None:
        """Print conversation report."""
        print(f"\n{'#'*70}")
        safe_print(f"📊 CONVERSATION REPORT: {report['scenario']}")
        print(f"{'#'*70}\n")

        summary = report['summary']
        safe_print(f"✅ Successful turns: {summary['successful_turns']}/{summary['total_turns']}")
        if summary['failed_turns'] > 0:
            safe_print(f"❌ Failed turns: {summary['failed_turns']}")
        safe_print(f"📨 Total messages: {summary['total_messages']}")
        safe_print(f"⏸️  Total approvals: {summary['total_approvals']}")

        if summary['total_validations'] > 0:
            safe_print(f"🔍 Validations: {summary['passed_validations']}/{summary['total_validations']} passed ({summary['validation_pass_rate']})")

        safe_print(f"⏱️  Total time: {report['elapsed_time']:.2f}s")

        print(f"\n{'-'*70}")
        safe_print("📋 Turn-by-Turn Breakdown:")
        print(f"{'-'*70}\n")

        for turn in report['turns']:
            icon = "✅" if turn['status'] == 'success' else "❌"
            safe_print(f"{icon} Turn {turn['turn']}: {turn['status'].upper()} ({turn['elapsed']:.2f}s)")
            if turn.get('error'):
                print(f"     Error: {turn['error']}")
            if turn['validations']:
                passed = sum(1 for v in turn['validations'] if v['passed'])
                safe_print(f"     Validations: {passed}/{len(turn['validations'])} passed")

        print(f"\n{'#'*70}\n")


def get_scenario_files() -> dict[str, Path]:
    """Get all conversation scenario files.

    Returns:
        Dictionary mapping scenario ID to file path
    """
    scenarios_dir = Path(__file__).parent / "conversation_scenarios"

    if not scenarios_dir.exists():
        return {}

    scenario_files = {}
    for yaml_file in scenarios_dir.glob("*.yaml"):
        scenario_id = yaml_file.stem
        scenario_files[scenario_id] = yaml_file

    for yml_file in scenarios_dir.glob("*.yml"):
        scenario_id = yml_file.stem
        scenario_files[scenario_id] = yml_file

    return scenario_files


def list_scenarios() -> None:
    """List all available conversation scenarios."""
    scenarios = get_scenario_files()

    if not scenarios:
        print("No conversation scenarios found.")
        print("Create YAML files in: agents/src/autifyme_agents/cli/conversation_scenarios/")
        return

    print(f"\nAvailable Conversation Scenarios ({len(scenarios)}):\n")

    for scenario_id, scenario_path in sorted(scenarios.items()):
        # Load scenario to get name/description
        try:
            with open(scenario_path, encoding='utf-8') as f:
                scenario = yaml.safe_load(f)
                name = scenario.get('name', scenario_id)
                description = scenario.get('description', 'No description')
                turns = len(scenario.get('turns', []))
                safe_print(f"  {scenario_id}:")
                safe_print(f"    Name: {name}")
                safe_print(f"    Description: {description}")
                safe_print(f"    Turns: {turns}")
                print()
        except Exception as e:
            print(f"  {scenario_id}: Error loading ({e})")


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
    debug = "--debug" in sys.argv or "-d" in sys.argv
    hitl_mode = "interactive"

    if "--hitl-mode" in sys.argv:
        idx = sys.argv.index("--hitl-mode")
        if idx + 1 < len(sys.argv):
            hitl_mode = sys.argv[idx + 1]

    # Create player
    player = ConversationPlayer(debug=debug)

    if len(sys.argv) > 1:
        if sys.argv[1] in ["--help", "-h"]:
            print(__doc__)
            return

        if sys.argv[1] in ["--list", "-l"]:
            list_scenarios()
            return

        if sys.argv[1] in ["--all", "-a"]:
            scenarios = get_scenario_files()
            if not scenarios:
                print("No conversation scenarios found.")
                return

            print(f"\n{'*'*70}")
            safe_print(f"🚀 RUNNING ALL CONVERSATION SCENARIOS ({len(scenarios)} total)")
            print(f"{'*'*70}\n")

            reports = []
            for scenario_id, scenario_path in sorted(scenarios.items()):
                try:
                    report = player.play_conversation(scenario_path, hitl_mode=hitl_mode)
                    reports.append(report)
                except Exception as e:
                    print(f"❌ Error running {scenario_id}: {e}")

                if len(scenarios) > 1:
                    input("\nPress Enter to continue to next scenario...")

            # Overall summary
            print(f"\n{'*'*70}")
            safe_print(f"📊 OVERALL SUMMARY ({len(reports)} scenarios)")
            print(f"{'*'*70}\n")

            for report in reports:
                summary = report['summary']
                icon = "✅" if summary['failed_turns'] == 0 else "❌"
                safe_print(f"{icon} {report['scenario']}: {summary['successful_turns']}/{summary['total_turns']} turns")

            return

        if sys.argv[1] in ["--scenario", "-s"]:
            if len(sys.argv) < 3:
                print("Usage: conversation --scenario <scenario_id>")
                list_scenarios()
                sys.exit(1)

            scenario_id = sys.argv[2]
            scenarios = get_scenario_files()

            if scenario_id not in scenarios:
                print(f"Unknown scenario: {scenario_id}")
                list_scenarios()
                sys.exit(1)

            scenario_path = scenarios[scenario_id]
            player.play_conversation(scenario_path, hitl_mode=hitl_mode)
            return

    print(__doc__)
    print("\nNo scenario provided. Use --list to see available scenarios.\n")


if __name__ == "__main__":
    main()
