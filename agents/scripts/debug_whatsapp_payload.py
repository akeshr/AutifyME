"""Utilities for inspecting WhatsApp webhook payloads without invoking agents."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

LOG = logging.getLogger(__name__)
EVENT_DIR = Path("tmp/whatsapp_events")


def list_events(limit: int | None = None) -> list[Path]:
    if not EVENT_DIR.exists():
        raise SystemExit("No events captured yet. Run the webhook server and send messages first.")
    all_events = sorted(EVENT_DIR.glob("event_*.json"))
    if limit is not None:
        all_events = all_events[-limit:]
    return all_events


def show_event(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(data, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect saved WhatsApp webhook payloads.")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List captured events instead of printing a specific one.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional limit when listing events (most recent first).",
    )
    parser.add_argument(
        "--event",
        type=Path,
        help="Specific event file to show. Defaults to newest captured event.",
    )
    parser.add_argument(
        "--save",
        type=Path,
        help="Optional path to copy the selected event for offline analysis.",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.list:
        for path in list_events(limit=args.limit):
            print(path)
        return

    event_path = args.event
    if event_path is None:
        events = list_events(limit=1)
        event_path = events[-1]

    LOG.info("Showing event %s", event_path)
    show_event(event_path)

    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(Path(event_path).read_text(encoding="utf-8"), encoding="utf-8")
        LOG.info("Copied event to %s", args.save)


if __name__ == "__main__":
    main()
