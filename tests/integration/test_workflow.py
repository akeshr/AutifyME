"""End-to-end smoke test for the WhatsApp Project Manager orchestration."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from autifyme_agents.integrations.communication.whatsapp_media_client import (
    WhatsAppMediaClient,
)
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.workflows.channels.whatsapp.adapter import WhatsAppChannel
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner


class RecordingWhatsAppClient:
    """Test double that records outbound WhatsApp messages instead of sending them."""

    def __init__(self) -> None:
        self.sent_messages: list[dict[str, Any]] = []

    def send_text(self, recipient: str, message: str, *, preview_url: bool = False) -> dict[str, Any]:
        payload = {
            "recipient": recipient,
            "message": message,
            "preview_url": preview_url,
        }
        self.sent_messages.append(payload)
        print("[WhatsAppClient] Would send:", json.dumps(payload, ensure_ascii=False))
        return {"status": "mocked"}


class NoopWhatsAppMediaClient(WhatsAppMediaClient):
    """Stub media client that forbids downloads in this smoke test."""

    def __init__(self) -> None:  # pragma: no cover - simple override
        pass

    def download_media(self, media_id: str) -> Path:  # pragma: no cover - defensive guard
        raise RuntimeError(
            "Media downloads are not exercised in this smoke test. Provide a media_id to extend the script."
        )


def _load_env() -> None:
    load_dotenv(Path.cwd() / ".env")


def main() -> None:
    print("=" * 60)
    print("WHATSAPP PROJECT MANAGER - STATEFUL SMOKE TEST")
    print("=" * 60)

    _load_env()

    storage = SupabaseStorageClient()
    whatsapp_client = RecordingWhatsAppClient()
    media_client = NoopWhatsAppMediaClient()
    checkpointer = get_checkpointer()

    # Create WhatsApp channel with test doubles
    whatsapp_channel = WhatsAppChannel(
        whatsapp_client=whatsapp_client,
        media_client=media_client,
    )

    # Create workflow runner with WhatsApp channel
    runner = WorkflowRunner(
        channel=whatsapp_channel,
        storage=storage,
        checkpointer=checkpointer,
    )
    print(" Runner ready (Project Manager orchestrated with refactored architecture)")

    sender = f"test-user-{uuid.uuid4()}"
    payload = {
        "text": "Please catalog a new pair of canvas sneakers. Price 79.99, sizes 7-11.",
        "media_id": None,
    }

    print("\n[1/2] Sending synthetic WhatsApp payload:")
    print(json.dumps(payload, indent=2))

    runner.handle_message(
        sender=sender,
        text=payload["text"],
        media_id=payload["media_id"],
    )

    print("\n[2/2] Invocation completed. Recorded outbound messages:")
    if whatsapp_client.sent_messages:
        for idx, message in enumerate(whatsapp_client.sent_messages, start=1):
            print(f"  [{idx}] -> {json.dumps(message, ensure_ascii=False)}")
    else:
        print("  (No messages were sent)")
    print("=" * 60)


if __name__ == "__main__":
    main()
