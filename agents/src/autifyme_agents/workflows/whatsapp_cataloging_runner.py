"""Workflow runner coordinating WhatsApp cataloging conversations."""

from __future__ import annotations

import logging
from pathlib import Path

from langgraph.types import Interrupt
from langgraph.checkpoint.base import BaseCheckpointSaver

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.departments.cataloging_department import create_cataloging_department
from autifyme_agents.integrations.communication import WhatsAppClient, WhatsAppMediaClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

logger = logging.getLogger(__name__)


class WhatsAppCatalogingRunner:
    """Coordinates the end-to-end WhatsApp cataloging workflow."""

    def __init__(
        self,
        *,
        storage: StorageInterface | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
        whatsapp_client: WhatsAppClient | None = None,
        media_client: WhatsAppMediaClient | None = None,
    ) -> None:
        self.storage = storage or SupabaseStorageClient()
        self.checkpointer = checkpointer
        self.whatsapp_client = whatsapp_client or WhatsAppClient()
        self.media_client = media_client or WhatsAppMediaClient()

    def _get_checkpointer(self) -> BaseCheckpointSaver:
        if self.checkpointer:
            return self.checkpointer
        with get_checkpointer() as saver:
            return saver

    def _thread_id(self, sender: str) -> str:
        return f"whatsapp:{sender}"

    def handle_message(self, sender: str, text: str | None, media_id: str | None) -> None:
        image_path: Path | None = None
        try:
            if media_id:
                image_path = self.media_client.download_media(media_id)

            payload = {
                "messages": [
                    {
                        "type": "human",
                        "content": text or "Please catalog this product.",
                    }
                ]
            }

            config = {
                "configurable": {
                    "thread_id": self._thread_id(sender),
                    "company_id": "default",
                }
            }

            with get_checkpointer() as saver:
                department = create_cataloging_department(saver, self.storage)
                try:
                    result = department.invoke(payload, config=config)
                    structured = result.get("structured_response")
                    if structured:
                        self._send_completion(sender, structured)
                except Interrupt as interruption:
                    self._handle_interrupt(sender, interruption)
        finally:
            if image_path and image_path.exists():
                image_path.unlink()

    def handle_approval(self, sender: str, decision: str) -> None:
        action = decision.strip().lower()
        if action not in {"approve", "reject"}:
            self.whatsapp_client.send_text(sender, "Please reply with 'approve' or 'reject'.")
            return

        config = {
            "configurable": {
                "thread_id": self._thread_id(sender),
            },
            "interrupt": {
                "tool": "save_product",
                "decision": action,
            },
        }

        with get_checkpointer() as saver:
            department = create_cataloging_department(saver, self.storage)
            result = department.invoke({}, config=config)
            structured = result.get("structured_response")
            if structured:
                self._send_completion(sender, structured)

    def _handle_interrupt(self, sender: str, interruption: Interrupt) -> None:
        payload = interruption.value or {}
        tool_name = payload.get("tool")
        if tool_name == "save_product":
            message = payload.get("message", "Cataloging complete. Approve to save the product.")
            self.whatsapp_client.send_text(sender, f"Approval needed: {message}\nReply 'approve' or 'reject'.")
        else:
            logger.warning("Received unsupported interrupt from tool %s", tool_name)

    def _send_completion(self, sender: str, structured: dict) -> None:
        success = structured.get("success")
        name = structured.get("product_name")
        message = structured.get("message")
        status = "Success" if success else "Failed"
        body = f"Cataloging {status}: {name or 'Unnamed'}\n{message}"
        self.whatsapp_client.send_text(sender, body)
