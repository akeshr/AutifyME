"""Utilities for inspecting WhatsApp webhook payloads and media.

This script gives developers running inside constrained environments (e.g.,
Codespaces) an easy way to inspect inbound webhook payloads captured by
`whatsapp_webhook` and, when desired, fetch the referenced media using the
same `WhatsAppMediaClient` employed in production. This honors our
Architecture-First policy: we validate adapters in isolation before invoking
agent workflows.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autifyme_agents.integrations.communication.whatsapp_media_client import (
    WhatsAppMediaClient,
)

LOG = logging.getLogger(__name__)
EVENT_DIR = Path("tmp/whatsapp_events")


@dataclass
class EventSummary:
    path: Path
    sender: str | None
    message_type: str | None
    text: str | None
    media_id: str | None


def _load_event(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - operational error
        raise SystemExit(f"Event file not found: {path}") from exc


def _extract_summary(data: dict[str, Any], path: Path) -> EventSummary:
    sender: str | None = None
    message_type: str | None = None
    text: str | None = None
    media_id: str | None = None

    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change.get("value", {})
        messages = value.get("messages", [])
        if messages:
            message = messages[0]
            sender = message.get("from")
            message_type = message.get("type")
            text = message.get("text", {}).get("body")
            if message_type == "image":
                media = message.get("image", {})
                media_id = media.get("id")
    except (KeyError, IndexError) as exc:  # noqa: PERF203 - nested spec lookups
        LOG.warning("Failed to parse event structure %s: %s", path, exc)

    return EventSummary(
        path=path,
        sender=sender,
        message_type=message_type,
        text=text,
        media_id=media_id,
    )


def _find_latest_event() -> Path:
    if not EVENT_DIR.exists():
        raise SystemExit(
            "Event directory not found. Ensure the webhook server is running and receiving events first."
        )
    event_files = sorted(EVENT_DIR.glob("event_*.json"))
    if not event_files:
        raise SystemExit("No events captured yet in tmp/whatsapp_events.")
    return event_files[-1]


def _download_media(media_id: str, destination: Path | None, client: WhatsAppMediaClient) -> Path:
    LOG.info("Requesting media metadata", extra={"media_id": media_id})
    temp_path = client.download_media(media_id)
    if destination:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_path.replace(destination)
        LOG.info("Media saved to %s", destination)
        return destination
    LOG.info("Media downloaded to %s", temp_path)
    return temp_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect WhatsApp webhook payloads and media downloads."
    )
    parser.add_argument(
        "--event",
        type=Path,
        help="Path to a saved event JSON. Defaults to the most recent file in tmp/whatsapp_events.",
    )
    parser.add_argument(
        "--media-id",
        help="Override media id. Useful if you only need to test the download step.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the media referenced by the event/media id using WhatsAppMediaClient.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional destination path for the downloaded media. Defaults to a temp file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging for deeper inspection.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    event_path = args.event or _find_latest_event()
    LOG.info("Loading event %s", event_path)
    data = _load_event(event_path)
    summary = _extract_summary(data, event_path)

    print("Event summary:")
    print(f"  Path:        {summary.path}")
    print(f"  Sender:      {summary.sender}")
    print(f"  MessageType: {summary.message_type}")
    print(f"  Text:        {summary.text!r}")
    print(f"  Media ID:    {summary.media_id}")

    media_id = args.media_id or summary.media_id
    if not media_id:
        if args.download:
            LOG.warning("No media id available; skipping download.")
        return

    if not args.download:
        LOG.info("Media id available (use --download to fetch)", extra={"media_id": media_id})
        return

    client = WhatsAppMediaClient()
    final_path = _download_media(media_id, args.output, client)
    print(f"Downloaded media to: {final_path}")


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    main()
