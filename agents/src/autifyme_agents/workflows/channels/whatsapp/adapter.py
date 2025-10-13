"""WhatsApp channel adapter implementation.

WhatsApp-specific implementation of the MessagingChannel protocol.
Wraps WhatsAppClient and WhatsAppMediaClient with channel-specific formatting.

Design Pattern: Adapter - adapts WhatsApp API to generic MessagingChannel interface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from autifyme_agents.core.logging_config import get_logger
from autifyme_agents.integrations.communication import WhatsAppClient, WhatsAppMediaClient
from autifyme_agents.workflows.channels.protocol import ChannelError
from autifyme_agents.schemas.models import Product, CatalogingResult

logger = get_logger(__name__)


class WhatsAppChannel:
    """WhatsApp implementation of MessagingChannel protocol.

    Responsibilities:
    - Wrap WhatsAppClient and WhatsAppMediaClient
    - Format messages with WhatsApp markdown
    - Handle WhatsApp-specific errors
    - Download media via WhatsApp Graph API

    NOT responsible for:
    - Workflow orchestration
    - Approval logic
    - State management
    """

    def __init__(
        self,
        whatsapp_client: WhatsAppClient | None = None,
        media_client: WhatsAppMediaClient | None = None,
    ):
        """Initialize WhatsApp channel adapter.

        Args:
            whatsapp_client: WhatsApp client instance (creates default if None)
            media_client: WhatsApp media client instance (creates default if None)
        """
        self.client = whatsapp_client or WhatsAppClient()
        self.media = media_client or WhatsAppMediaClient()

    def send_text(
        self,
        recipient: str,
        message: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send plain text message via WhatsApp.

        Args:
            recipient: WhatsApp phone number (e.g., "919876543210")
            message: Message content
            metadata: Optional dict with "preview_url" boolean

        Returns:
            WhatsApp API response dict

        Raises:
            ChannelError: If message sending fails
        """
        try:
            preview_url = (metadata or {}).get("preview_url", False)

            logger.debug(
                "Sending WhatsApp text message",
                extra={
                    "recipient": recipient,
                    "message_length": len(message),
                    "preview_url": preview_url,
                },
            )

            result = self.client.send_text(recipient, message, preview_url=preview_url)

            logger.info(
                "WhatsApp message sent successfully",
                extra={"recipient": recipient, "message_id": result.get("message_id")},
            )

            return result

        except Exception as exc:
            logger.exception("Failed to send WhatsApp message", exc_info=exc)
            raise ChannelError(
                f"Failed to send WhatsApp message: {str(exc)}",
                channel="whatsapp",
                recipient=recipient,
                original_error=exc,
            ) from exc

    def send_approval_request(
        self,
        recipient: str,
        draft: Product,
    ) -> dict[str, Any]:
        """Send HITL approval request formatted for WhatsApp.

        Uses WhatsApp markdown for formatting:
        - *bold* for labels
        - Plain text for values
        - Newlines for structure

        Args:
            recipient: WhatsApp phone number
            draft: Product draft requiring approval

        Returns:
            WhatsApp API response dict

        Raises:
            ChannelError: If message sending fails
        """
        # Format draft with WhatsApp markdown
        message = self._format_approval_message(draft)

        logger.info(
            "Sending WhatsApp approval request",
            extra={"recipient": recipient, "product_name": draft.name},
        )

        return self.send_text(recipient, message)

    def send_completion(
        self,
        recipient: str,
        result: CatalogingResult,
    ) -> dict[str, Any]:
        """Send workflow completion message.

        Args:
            recipient: WhatsApp phone number
            result: Cataloging result to communicate

        Returns:
            WhatsApp API response dict

        Raises:
            ChannelError: If message sending fails
        """
        if result.success:
            message = f"✅ *Cataloging Complete*\n\n{result.product_name or 'Product'} has been added to your catalog!\n\n{result.message}"
        else:
            message = f"❌ *Cataloging Failed*\n\n{result.message}"

        logger.info(
            "Sending WhatsApp completion message",
            extra={
                "recipient": recipient,
                "success": result.success,
                "product_name": result.product_name,
            },
        )

        return self.send_text(recipient, message)

    def send_error(
        self,
        recipient: str,
        error_type: Literal["media_download", "processing", "recursion"],
        message: str | None = None,
    ) -> dict[str, Any]:
        """Send user-friendly error message.

        Args:
            recipient: WhatsApp phone number
            error_type: Category of error (determines default message)
            message: Optional custom error message (overrides default)

        Returns:
            WhatsApp API response dict

        Raises:
            ChannelError: If message sending fails (critical)
        """
        if message:
            error_message = message
        else:
            error_message = self._get_default_error_message(error_type)

        logger.warning(
            "Sending WhatsApp error message",
            extra={"recipient": recipient, "error_type": error_type},
        )

        return self.send_text(recipient, error_message)

    def download_media(self, media_id: str) -> Path:
        """Download media file via WhatsApp Graph API.

        Returns only the file path. The file is saved to disk and can be read
        by downstream tools when needed. This prevents token explosion from
        passing binary data through LangChain message history.

        Args:
            media_id: WhatsApp media ID from message

        Returns:
            Path to downloaded media file

        Raises:
            ChannelError: If download fails
        """
        try:
            logger.debug("Downloading WhatsApp media", extra={"media_id": media_id})

            media_path, media_bytes, mime_type = self.media.download_media(media_id)

            logger.info(
                "WhatsApp media downloaded successfully",
                extra={
                    "media_id": media_id,
                    "path": str(media_path),
                    "size_bytes": len(media_bytes),
                    "mime_type": mime_type,
                },
            )

            # Only return path - never return binary data to avoid token explosion
            return media_path

        except Exception as exc:
            logger.exception("Failed to download WhatsApp media", exc_info=exc)
            raise ChannelError(
                f"Failed to download media: {str(exc)}",
                channel="whatsapp",
                original_error=exc,
            ) from exc

    def format_thread_id(self, sender: str) -> str:
        """Generate WhatsApp-specific thread ID for checkpointing.

        WhatsApp uses "whatsapp:" prefix to distinguish from other channels.

        Args:
            sender: WhatsApp phone number

        Returns:
            Thread ID for LangGraph checkpointer (e.g., "whatsapp:919876543210")
        """
        return f"whatsapp:{sender}"

    def _format_approval_message(self, draft: Product) -> str:
        """Format product draft as WhatsApp approval request.

        Args:
            draft: Product draft to format

        Returns:
            Formatted message string with WhatsApp markdown
        """
        lines = ["*Approval Needed*\n"]

        lines.append(f"*Product:* {draft.name}")

        if draft.price is not None:
            lines.append(f"*Price:* {draft.price}")

        if draft.sizes:
            sizes_text = ", ".join(str(s) for s in draft.sizes if s)
            lines.append(f"*Sizes:* {sizes_text}")

        if draft.colors:
            colors_text = ", ".join(str(c) for c in draft.colors if c)
            lines.append(f"*Colors:* {colors_text}")

        if draft.description:
            lines.append(f"*Description:* {draft.description}")

        lines.append("\nReply *approve* or *reject*.")

        return "\n".join(lines)

    def _get_default_error_message(
        self,
        error_type: Literal["media_download", "processing", "recursion"],
    ) -> str:
        """Get default user-friendly error message by type.

        Args:
            error_type: Category of error

        Returns:
            User-friendly error message
        """
        messages = {
            "media_download": (
                "❌ I couldn't download your image. "
                "Please try resending it or check your connection."
            ),
            "processing": (
                "❌ I hit a processing error. "
                "Please try resending the details or wait for support."
            ),
            "recursion": (
                "❌ I'm having trouble finishing this task. "
                "A specialist will review and follow up."
            ),
        }
        return messages.get(error_type, "❌ Something went wrong. Please try again.")
