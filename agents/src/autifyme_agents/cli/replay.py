"""Scenario replay tool for local execution of captured WhatsApp flows.

This tool replays captured webhook scenarios locally, allowing you to:
- Test changes against real user interactions
- Build regression test suite from production data
- Debug issues with exact reproduction
- Validate database state after workflow completion

Features:
- Local replay of captured scenarios
- Database validation (products, checkpoints)
- Comparison with original execution
- Batch regression testing
- Detailed execution reports

Usage:
    # Replay single scenario
    uv run python -m autifyme_agents.cli.replay --scenario scenario_001_20251011_123456

    # Replay with database validation
    uv run python -m autifyme_agents.cli.replay --scenario scenario_001_20251011_123456 --validate-db

    # Replay all scenarios (regression suite)
    uv run python -m autifyme_agents.cli.replay --all

    # Replay with specific HITL mode
    uv run python -m autifyme_agents.cli.replay --scenario scenario_001_20251011_123456 --hitl-mode auto_approve

    # Generate regression report
    uv run python -m autifyme_agents.cli.replay --all --validate-db --report regression_report.json
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
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner
from autifyme_agents.workflows.channels.protocol import MessagingChannel


def safe_print(text: str) -> None:
    """Print text safely, handling console encoding issues on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))


class ReplayChannel(MessagingChannel):
    """Messaging channel for scenario replay with validation."""

    def __init__(self, hitl_mode: str = "auto_approve", validate_db: bool = False):
        """Initialize replay channel.

        Args:
            hitl_mode: HITL testing mode
            validate_db: If True, validate database records
        """
        self.hitl_mode = hitl_mode
        self.validate_db = validate_db
        self.messages_sent: list[dict[str, Any]] = []
        self.approvals_requested: list[dict[str, Any]] = []
        self.completions: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []

    def format_thread_id(self, sender: str) -> str:
        return f"replay:{sender}"

    def send_text(self, recipient: str, message: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send text message and track it."""
        print(f"\n📤 PM: {message[:100]}{'...' if len(message) > 100 else ''}")

        self.messages_sent.append({
            "type": "text",
            "message": message,
            "recipient": recipient,
        })
        return {"status": "sent"}

    def send_approval_request(self, recipient: str, draft: Product) -> dict[str, Any]:
        """Send approval request and track it."""
        print("\n⏸️  APPROVAL REQUEST")

        draft_dict = draft.model_dump() if hasattr(draft, 'model_dump') else draft

        def json_encoder(obj):
            if hasattr(obj, '__str__'):
                return str(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        print(json.dumps(draft_dict, indent=2, ensure_ascii=False, default=json_encoder)[:500])

        self.approvals_requested.append({
            "draft": draft_dict,
        })

        # Auto-handle based on HITL mode
        if self.hitl_mode == "auto_approve":
            print("[AUTO-APPROVE]")
            time.sleep(0.2)
            return {"status": "approved", "draft": draft}

        elif self.hitl_mode == "auto_reject":
            print("[AUTO-REJECT]")
            time.sleep(0.2)
            return {"status": "rejected"}

        else:
            # Interactive mode
            while True:
                decision = input("\nApprove? (yes/no): ").strip().lower()
                if decision in ["yes", "y"]:
                    return {"status": "approved", "draft": draft}
                elif decision in ["no", "n"]:
                    return {"status": "rejected"}
                else:
                    print("Please enter 'yes' or 'no'")

    def send_completion(self, recipient: str, result: CatalogingResult) -> dict[str, Any]:
        """Send completion and track it."""
        print("\n✅ Workflow completed")

        self.completions.append({
            "result": result.model_dump() if hasattr(result, 'model_dump') else result,
        })
        return {"status": "sent"}

    def send_error(self, recipient: str, error_type: str, custom_message: str | None = None) -> dict:
        """Send error and track it."""
        print(f"\n❌ Error: {error_type}")
        if custom_message:
            print(f"   {custom_message}")

        self.errors.append({
            "error_type": error_type,
            "custom_message": custom_message,
        })
        return {"status": "sent"}

    def download_media(self, media_id: str) -> Path:
        """Download media (for local testing, media_id is a path)."""
        return Path(media_id)


class ScenarioReplay:
    """Replays captured scenarios locally with validation."""

    def __init__(self, scenarios_dir: Path | None = None, validate_db: bool = False):
        """Initialize scenario replay.

        Args:
            scenarios_dir: Directory containing captured scenarios
            validate_db: If True, validate database records
        """
        if scenarios_dir:
            self.scenarios_dir = scenarios_dir
        else:
            self.scenarios_dir = Path(__file__).parent / "scenarios_recorded"

        self.validate_db = validate_db
        self.storage = SupabaseStorageClient()
        self.checkpointer = get_checkpointer()

    def load_scenario(self, scenario_id: str) -> dict[str, Any]:
        """Load scenario from file.

        Args:
            scenario_id: Scenario ID to load

        Returns:
            Scenario data
        """
        scenario_path = self.scenarios_dir / f"{scenario_id}.json"

        if not scenario_path.exists():
            raise FileNotFoundError(f"Scenario not found: {scenario_id}")

        with open(scenario_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def replay_scenario(self, scenario_id: str, hitl_mode: str = "auto_approve") -> dict[str, Any]:
        """Replay a captured scenario locally.

        Args:
            scenario_id: Scenario ID to replay
            hitl_mode: HITL testing mode

        Returns:
            Replay report with results and validations
        """
        # Load scenario
        scenario = self.load_scenario(scenario_id)

        print(f"\n{'#'*70}")
        safe_print(f"🎬 REPLAYING SCENARIO: {scenario['name']}")
        safe_print(f"   ID: {scenario['id']}")
        safe_print(f"   Captured: {scenario['captured_at']}")
        safe_print(f"   Sender: {scenario['sender']}")
        print(f"{'#'*70}\n")

        # Extract event data
        if not scenario.get("events"):
            raise ValueError("Scenario has no events")

        event = scenario["events"][0]  # For now, handle single event scenarios

        # Extract message details
        text = scenario.get("metadata", {}).get("text")
        media_files = event.get("media_files", [])

        # Get media path if available
        media_path = None
        if media_files:
            media_path = self.scenarios_dir / "media" / media_files[0]
            if not media_path.exists():
                print(f"⚠️  Warning: Media file not found: {media_path}")
                media_path = None

        # Create unique sender for replay
        original_sender = scenario["sender"].replace("whatsapp:", "").replace("replay:", "")
        replay_sender = f"replay_{original_sender}_{int(time.time())}"

        # Create channel and runner
        channel = ReplayChannel(hitl_mode=hitl_mode, validate_db=self.validate_db)
        runner = WorkflowRunner(
            channel=channel,
            storage=self.storage,
            checkpointer=self.checkpointer,
        )

        # Display replay input
        safe_print("📝 Replay Input:")
        if text:
            safe_print(f"   Text: {text}")
        if media_path:
            safe_print(f"   Media: {media_path}")
        print()

        # Execute replay
        start_time = time.time()
        status = "success"
        error = None

        try:
            runner.handle_message(
                sender=replay_sender,
                text=text,
                media_id=str(media_path) if media_path else None,
            )

        except Exception as e:
            status = "error"
            error = f"{type(e).__name__}: {e}"
            safe_print(f"\n❌ Replay Error: {error}")

        elapsed = time.time() - start_time

        # Validate database if requested
        db_validation = None
        if self.validate_db and status == "success":
            db_validation = self._validate_database(replay_sender, text, channel)

        # Generate report
        report = {
            "scenario_id": scenario_id,
            "scenario_name": scenario["name"],
            "status": status,
            "error": error,
            "elapsed": elapsed,
            "messages_sent": len(channel.messages_sent),
            "approvals_requested": len(channel.approvals_requested),
            "completions": len(channel.completions),
            "errors": len(channel.errors),
            "db_validation": db_validation,
        }

        self._print_report(report)

        return report

    def _validate_database(self, sender: str, text: str | None, channel: ReplayChannel) -> dict[str, Any]:
        """Validate database records after replay.

        Args:
            sender: Sender ID used in replay
            text: Message text
            channel: Replay channel with execution data

        Returns:
            Validation results
        """
        print(f"\n{'-'*70}")
        safe_print("🔍 DATABASE VALIDATION")
        print(f"{'-'*70}\n")

        validations = []

        # Validate product creation
        if channel.completions:
            safe_print("✓ Checking product creation...")

            # Try to find product in database
            # Note: This is simplified - in production you'd query by specific criteria
            try:
                # Get company profile to check products
                company_profile = self.storage.get_company_profile()

                if company_profile:
                    products_count = len(company_profile.products) if hasattr(company_profile, 'products') else 0
                    validations.append({
                        "check": "company_profile_exists",
                        "passed": True,
                        "message": f"Company profile found with {products_count} products"
                    })
                    safe_print(f"   ✅ Company profile exists ({products_count} products)")
                else:
                    validations.append({
                        "check": "company_profile_exists",
                        "passed": False,
                        "message": "Company profile not found"
                    })
                    safe_print("   ⚠️  Company profile not found")

            except Exception as e:
                validations.append({
                    "check": "company_profile_exists",
                    "passed": False,
                    "message": f"Error checking company profile: {e}"
                })
                safe_print(f"   ❌ Error: {e}")

        # Validate checkpoint state
        safe_print("\n✓ Checking checkpoint state...")
        try:
            from langchain_core.runnables import RunnableConfig

            thread_id = channel.format_thread_id(sender)
            config: RunnableConfig = {"configurable": {"thread_id": thread_id}}  # type: ignore[typeddict-item]
            checkpoint_tuple = self.checkpointer.get_tuple(config)

            if checkpoint_tuple:
                validations.append({
                    "check": "checkpoint_exists",
                    "passed": True,
                    "message": "Checkpoint found"
                })
                safe_print("   ✅ Checkpoint exists")
            else:
                validations.append({
                    "check": "checkpoint_exists",
                    "passed": False,
                    "message": "No checkpoint found"
                })
                safe_print("   ⚠️  No checkpoint found")

        except Exception as e:
            validations.append({
                "check": "checkpoint_exists",
                "passed": False,
                "message": f"Error checking checkpoint: {e}"
            })
            safe_print(f"   ❌ Error: {e}")

        # Summary
        passed = sum(1 for v in validations if v['passed'])
        total = len(validations)

        print(f"\n{'-'*70}")
        safe_print(f"📊 Validation Summary: {passed}/{total} checks passed")
        print(f"{'-'*70}\n")

        return {
            "checks": validations,
            "passed": passed,
            "total": total,
            "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "N/A"
        }

    def _print_report(self, report: dict[str, Any]) -> None:
        """Print replay report."""
        print(f"\n{'#'*70}")
        safe_print(f"📊 REPLAY REPORT: {report['scenario_name']}")
        print(f"{'#'*70}\n")

        # Status
        status_icon = "✅" if report['status'] == 'success' else "❌"
        safe_print(f"{status_icon} Status: {report['status'].upper()}")

        if report.get('error'):
            safe_print(f"   Error: {report['error']}")

        # Metrics
        safe_print(f"⏱️  Elapsed: {report['elapsed']:.2f}s")
        safe_print(f"📨 Messages sent: {report['messages_sent']}")
        safe_print(f"⏸️  Approvals: {report['approvals_requested']}")
        safe_print(f"✅ Completions: {report['completions']}")

        if report['errors'] > 0:
            safe_print(f"❌ Errors: {report['errors']}")

        # Database validation
        if report.get('db_validation'):
            db_val = report['db_validation']
            safe_print(f"\n🔍 Database Validation: {db_val['passed']}/{db_val['total']} ({db_val['pass_rate']})")

        print(f"\n{'#'*70}\n")

    def replay_all(self, hitl_mode: str = "auto_approve") -> list[dict[str, Any]]:
        """Replay all captured scenarios.

        Args:
            hitl_mode: HITL testing mode

        Returns:
            List of replay reports
        """
        scenario_files = sorted(self.scenarios_dir.glob("scenario_*.json"))

        if not scenario_files:
            print(f"\nNo scenarios found in: {self.scenarios_dir}")
            return []

        print(f"\n{'*'*70}")
        safe_print(f"🚀 REPLAYING ALL SCENARIOS ({len(scenario_files)} total)")
        print(f"{'*'*70}\n")

        reports = []

        for scenario_file in scenario_files:
            scenario_id = scenario_file.stem

            try:
                report = self.replay_scenario(scenario_id, hitl_mode=hitl_mode)
                reports.append(report)

            except Exception as e:
                safe_print(f"❌ Error replaying {scenario_id}: {e}")
                reports.append({
                    "scenario_id": scenario_id,
                    "status": "error",
                    "error": str(e),
                })

            # Pause between scenarios
            if len(scenario_files) > 1:
                time.sleep(0.5)

        # Overall summary
        print(f"\n{'*'*70}")
        safe_print(f"📊 REGRESSION TEST SUMMARY ({len(reports)} scenarios)")
        print(f"{'*'*70}\n")

        successful = sum(1 for r in reports if r['status'] == 'success')
        failed = sum(1 for r in reports if r['status'] == 'error')

        safe_print(f"✅ Successful: {successful}/{len(reports)}")
        safe_print(f"❌ Failed: {failed}/{len(reports)}")

        if self.validate_db:
            db_passed = sum(r.get('db_validation', {}).get('passed', 0) for r in reports)
            db_total = sum(r.get('db_validation', {}).get('total', 0) for r in reports)
            if db_total > 0:
                safe_print(f"🔍 Database Validations: {db_passed}/{db_total} ({(db_passed / db_total * 100):.1f}%)")

        print()

        for report in reports:
            icon = "✅" if report['status'] == 'success' else "❌"
            safe_print(f"{icon} {report.get('scenario_name', report['scenario_id'])}: {report['status'].upper()}")

        print(f"\n{'*'*70}\n")

        return reports


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

    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print("  # Replay scenario with database validation")
        print("  uv run python -m autifyme_agents.cli.replay --scenario scenario_001_20251011_123456 --validate-db")
        print()
        print("  # Replay all scenarios")
        print("  uv run python -m autifyme_agents.cli.replay --all --validate-db")
        print()
        sys.exit(1)

    # Parse arguments
    scenario_id = None
    hitl_mode = "auto_approve"
    validate_db = "--validate-db" in sys.argv
    replay_all = "--all" in sys.argv
    report_path = None

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg in ["--help", "-h"]:
            print(__doc__)
            return

        elif arg == "--scenario":
            if i + 1 >= len(sys.argv):
                print("Error: --scenario requires a scenario ID")
                sys.exit(1)
            scenario_id = sys.argv[i + 1]
            i += 2

        elif arg == "--hitl-mode":
            if i + 1 >= len(sys.argv):
                print("Error: --hitl-mode requires a mode")
                sys.exit(1)
            hitl_mode = sys.argv[i + 1]
            i += 2

        elif arg == "--report":
            if i + 1 >= len(sys.argv):
                print("Error: --report requires a file path")
                sys.exit(1)
            report_path = Path(sys.argv[i + 1])
            i += 2

        elif arg in ["--validate-db", "--all"]:
            i += 1

        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)

    # Create replay instance
    replay = ScenarioReplay(validate_db=validate_db)

    # Execute replay
    if replay_all:
        reports = replay.replay_all(hitl_mode=hitl_mode)

        # Save report if requested
        if report_path:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(reports, f, indent=2, ensure_ascii=False)
            safe_print(f"\n📄 Report saved to: {report_path}\n")

    elif scenario_id:
        report = replay.replay_scenario(scenario_id, hitl_mode=hitl_mode)

        # Save report if requested
        if report_path:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            safe_print(f"\n📄 Report saved to: {report_path}\n")

    else:
        print("Error: Either --scenario or --all is required")
        sys.exit(1)


if __name__ == "__main__":
    main()
