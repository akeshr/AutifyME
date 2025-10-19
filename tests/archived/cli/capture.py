"""Webhook event capture tool for recording real WhatsApp flows.

This tool captures webhook events, media downloads, and state snapshots during
real WhatsApp interactions. Captured scenarios can be replayed locally for
regression testing and debugging.

Features:
- Webhook event recording (JSON format)
- Media file capture and storage
- State snapshot at key points
- Automatic scenario naming and organization
- Metadata tracking (timestamp, user, intent)

Usage:
    # Start capture mode (records to scenarios/recorded/)
    uv run python -m autifyme_agents.cli.capture --start

    # Capture specific webhook payload
    uv run python -m autifyme_agents.cli.capture --event webhook_payload.json

    # List captured scenarios
    uv run python -m autifyme_agents.cli.capture --list

    # Export scenario for sharing
    uv run python -m autifyme_agents.cli.capture --export scenario_001 --output scenario.json

Captured Scenario Format:
    {
        "id": "scenario_001_20251011_123456",
        "name": "Product cataloging with image",
        "captured_at": "2025-10-11T12:34:56Z",
        "sender": "whatsapp:1234567890",
        "events": [
            {
                "type": "webhook",
                "timestamp": "2025-10-11T12:34:56Z",
                "payload": {...},
                "media_files": ["media_001.jpg"]
            }
        ],
        "state_snapshots": [...],
        "metadata": {
            "intent": "cataloging",
            "approval_count": 1,
            "duration": 5.23
        }
    }
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def safe_print(text: str) -> None:
    """Print text safely, handling console encoding issues on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))


class ScenarioCapture:
    """Captures webhook events and creates replayable scenarios."""

    def __init__(self, scenarios_dir: Path | None = None):
        """Initialize scenario capture.

        Args:
            scenarios_dir: Directory to store captured scenarios
        """
        if scenarios_dir:
            self.scenarios_dir = scenarios_dir
        else:
            self.scenarios_dir = Path(__file__).parent / "scenarios_recorded"

        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir = self.scenarios_dir / "media"
        self.media_dir.mkdir(exist_ok=True)

    def generate_scenario_id(self) -> str:
        """Generate unique scenario ID with timestamp.

        Returns:
            Scenario ID string
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Count existing scenarios to get next number
        existing = list(self.scenarios_dir.glob("scenario_*.json"))
        next_num = len(existing) + 1

        return f"scenario_{next_num:03d}_{timestamp}"

    def capture_event(
        self,
        webhook_payload: dict[str, Any],
        scenario_id: str | None = None,
        media_files: list[Path] | None = None
    ) -> str:
        """Capture a webhook event and create scenario.

        Args:
            webhook_payload: WhatsApp webhook payload
            scenario_id: Optional scenario ID (generated if not provided)
            media_files: Optional list of media file paths to copy

        Returns:
            Scenario ID
        """
        if not scenario_id:
            scenario_id = self.generate_scenario_id()

        # Extract key information
        sender = self._extract_sender(webhook_payload)
        text = self._extract_text(webhook_payload)
        media_id = self._extract_media_id(webhook_payload)
        media_type = self._extract_media_type(webhook_payload)

        # Generate scenario name
        if text and len(text) > 50:
            name = f"{text[:50]}..."
        elif text:
            name = text
        elif media_type:
            name = f"{media_type} message"
        else:
            name = "Captured scenario"

        # Copy media files if provided
        captured_media: list[str] = []
        if media_files:
            for media_path in media_files:
                if media_path.exists():
                    dest_name = f"{scenario_id}_{media_path.name}"
                    dest_path = self.media_dir / dest_name
                    shutil.copy(media_path, dest_path)
                    captured_media.append(dest_name)
                    safe_print(f"   📎 Captured media: {dest_name}")

        # Create scenario structure
        scenario = {
            "id": scenario_id,
            "name": name,
            "captured_at": datetime.now().isoformat(),
            "sender": sender,
            "events": [
                {
                    "type": "webhook",
                    "timestamp": datetime.now().isoformat(),
                    "payload": webhook_payload,
                    "media_files": captured_media,
                }
            ],
            "metadata": {
                "text": text,
                "media_id": media_id,
                "media_type": media_type,
                "has_media": bool(media_id),
            }
        }

        # Save scenario
        scenario_path = self.scenarios_dir / f"{scenario_id}.json"
        with open(scenario_path, 'w', encoding='utf-8') as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)

        safe_print(f"\n✅ Scenario captured: {scenario_id}")
        safe_print(f"   Name: {name}")
        safe_print(f"   Path: {scenario_path}")
        if captured_media:
            safe_print(f"   Media files: {len(captured_media)}")

        return scenario_id

    def _extract_sender(self, payload: dict[str, Any]) -> str:
        """Extract sender from webhook payload."""
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [{}])
            if messages:
                return f"whatsapp:{messages[0].get('from', 'unknown')}"
        except (IndexError, KeyError, TypeError):
            pass
        return "unknown"

    def _extract_text(self, payload: dict[str, Any]) -> str | None:
        """Extract text message from webhook payload."""
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [{}])
            if messages:
                message = messages[0]

                # Check text field
                if "text" in message:
                    return message["text"].get("body")

                # Check caption fields for media messages
                for media_type in ["image", "video", "document", "audio"]:
                    if media_type in message:
                        caption = message[media_type].get("caption")
                        if caption:
                            return caption
        except (IndexError, KeyError, TypeError):
            pass
        return None

    def _extract_media_id(self, payload: dict[str, Any]) -> str | None:
        """Extract media ID from webhook payload."""
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [{}])
            if messages:
                message = messages[0]

                # Check for media types
                for media_type in ["image", "video", "document", "audio", "voice"]:
                    if media_type in message:
                        return message[media_type].get("id")
        except (IndexError, KeyError, TypeError):
            pass
        return None

    def _extract_media_type(self, payload: dict[str, Any]) -> str | None:
        """Extract media type from webhook payload."""
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [{}])
            if messages:
                return messages[0].get("type")
        except (IndexError, KeyError, TypeError):
            pass
        return None

    def list_scenarios(self) -> list[dict[str, Any]]:
        """List all captured scenarios.

        Returns:
            List of scenario summaries
        """
        scenarios = []

        for scenario_file in sorted(self.scenarios_dir.glob("scenario_*.json")):
            try:
                with open(scenario_file, encoding='utf-8') as f:
                    scenario = json.load(f)

                    summary = {
                        "id": scenario["id"],
                        "name": scenario["name"],
                        "captured_at": scenario["captured_at"],
                        "sender": scenario["sender"],
                        "events": len(scenario.get("events", [])),
                        "has_media": scenario.get("metadata", {}).get("has_media", False),
                        "file": str(scenario_file),
                    }
                    scenarios.append(summary)
            except Exception as e:
                safe_print(f"Error loading {scenario_file}: {e}")

        return scenarios

    def export_scenario(self, scenario_id: str, output_path: Path) -> None:
        """Export scenario to standalone file.

        Args:
            scenario_id: Scenario ID to export
            output_path: Output file path
        """
        scenario_path = self.scenarios_dir / f"{scenario_id}.json"

        if not scenario_path.exists():
            raise FileNotFoundError(f"Scenario not found: {scenario_id}")

        with open(scenario_path, encoding='utf-8') as f:
            scenario = json.load(f)

        # Copy media files to output directory if specified
        if output_path.parent != self.scenarios_dir:
            media_dir = output_path.parent / "media"
            media_dir.mkdir(exist_ok=True)

            for event in scenario.get("events", []):
                for media_file in event.get("media_files", []):
                    src = self.media_dir / media_file
                    dest = media_dir / media_file
                    if src.exists():
                        shutil.copy(src, dest)

        # Save scenario
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)

        safe_print(f"\n✅ Scenario exported to: {output_path}")


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
        print("  # Capture from webhook payload file")
        print("  uv run python -m autifyme_agents.cli.capture --event webhook.json")
        print()
        print("  # List captured scenarios")
        print("  uv run python -m autifyme_agents.cli.capture --list")
        print()
        print("  # Export scenario")
        print("  uv run python -m autifyme_agents.cli.capture --export scenario_001_20251011_123456 --output exported.json")
        print()
        sys.exit(1)

    capture = ScenarioCapture()

    # Parse arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg in ["--help", "-h"]:
            print(__doc__)
            return

        elif arg == "--list":
            scenarios = capture.list_scenarios()

            if not scenarios:
                print("\nNo captured scenarios found.")
                print(f"Scenarios directory: {capture.scenarios_dir}")
                return

            print(f"\n{'='*70}")
            safe_print(f"📹 CAPTURED SCENARIOS ({len(scenarios)})")
            print(f"{'='*70}\n")

            for scenario in scenarios:
                safe_print(f"🎬 {scenario['id']}")
                safe_print(f"   Name: {scenario['name']}")
                safe_print(f"   Captured: {scenario['captured_at']}")
                safe_print(f"   Sender: {scenario['sender']}")
                safe_print(f"   Events: {scenario['events']}")
                if scenario['has_media']:
                    safe_print("   📎 Has media")
                safe_print(f"   File: {scenario['file']}")
                print()

            return

        elif arg == "--event":
            if i + 1 >= len(sys.argv):
                print("Error: --event requires a file path")
                sys.exit(1)

            event_file = Path(sys.argv[i + 1])
            if not event_file.exists():
                print(f"Error: File not found: {event_file}")
                sys.exit(1)

            with open(event_file, encoding='utf-8') as f:
                webhook_payload = json.load(f)

            scenario_id = capture.capture_event(webhook_payload)
            print(f"\n✅ Captured as: {scenario_id}")
            return

        elif arg == "--export":
            if i + 1 >= len(sys.argv):
                print("Error: --export requires a scenario ID")
                sys.exit(1)

            scenario_id = sys.argv[i + 1]

            # Check for --output flag
            output_path = Path(f"{scenario_id}_exported.json")
            if i + 2 < len(sys.argv) and sys.argv[i + 2] == "--output":
                if i + 3 < len(sys.argv):
                    output_path = Path(sys.argv[i + 3])
                    i += 2

            capture.export_scenario(scenario_id, output_path)
            return

        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)

        i += 1


if __name__ == "__main__":
    main()
