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
from autifyme_agents.schemas.models import CatalogingResult

logger = logging.getLogger(__name__)


CATALOGING_PROMPT = "Please share the product details and photo so I can catalog it."  # Minimal triage response


class WhatsAppCatalogingRunner:
    """Coordinates the end-to-end WhatsApp cataloging workflow."""

    def __init__(
        self,
        *,
        storage: StorageInterface | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
        whatsapp_client: WhatsAppClient | None = None,
        media_client: WhatsAppMediaClient | None = None,
        enable_agent: bool = True,
    ) -> None:
        self.storage = storage or SupabaseStorageClient()
        self.checkpointer = checkpointer
        self.whatsapp_client = whatsapp_client or WhatsAppClient()
        self.media_client = media_client or WhatsAppMediaClient()
        self.enable_agent = enable_agent

    def _get_checkpointer(self) -> BaseCheckpointSaver:
        if self.checkpointer:
            return self.checkpointer
        with get_checkpointer() as saver:
            return saver

    def _thread_id(self, sender: str) -> str:
        return f"whatsapp:{sender}"

    def handle_message(self, sender: str, text: str | None, media_id: str | None) -> None:
        normalized_text = (text or "").strip()
        if not normalized_text and not media_id:
            logger.info("Ignoring empty message from %s", sender)
            self.whatsapp_client.send_text(sender, CATALOGING_PROMPT)
            return

        image_path: Path | None = None
        try:
            if media_id:
                image_path = self.media_client.download_media(media_id)
                logger.info("Media download succeeded", extra={"sender": sender, "media_id": media_id, "path": str(image_path)})

            if not self.enable_agent:
                self.whatsapp_client.send_text(
                    sender,
                    "Received your message. The cataloging agent is temporarily paused while we validate media handling.",
                )
                return

            payload = {
                "messages": [
                    {
                        "type": "human",
                        "content": normalized_text or "Please catalog this product.",
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
                    self._handle_completion(sender, result)
                except Interrupt as interruption:
                    self._handle_interrupt(sender, interruption)
        finally:
            if image_path and image_path.exists():
                image_path.unlink(missing_ok=True)

    def handle_approval(self, sender: str, decision: str) -> None:
        if not self.enable_agent:
            self.whatsapp_client.send_text(sender, "Agent approval flow is temporarily disabled while we run diagnostics.")
            return
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
            self._handle_completion(sender, result)

    def _handle_completion(self, sender: str, result: dict) -> None:
        if not result:
            logger.warning("Department returned empty result for %s", sender)
            return
        try:
            structured = CatalogingResult.model_validate(result)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to validate cataloging result: %s", exc)
            self.whatsapp_client.send_text(sender, "Cataloging finished, but the output was invalid.")
            return

        status = "Success" if structured.success else "Failed"
        name = structured.product_name or "Unnamed product"
        body = f"Cataloging {status}: {name}\n{structured.message}"
        self.whatsapp_client.send_text(sender, body)

    def _handle_interrupt(self, sender: str, interruption: Interrupt) -> None:
        payload = interruption.value or {}
        tool_name = payload.get("tool")
        if tool_name == "save_product":
            message = payload.get("message", "Cataloging complete. Approve to save the product.")
            self.whatsapp_client.send_text(sender, f"Approval needed: {message}\nReply 'approve' or 'reject'.")
        else:
            logger.warning("Received unsupported interrupt from tool %s", tool_name)
