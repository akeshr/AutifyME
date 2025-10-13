"""Mock channel adapter for testing and development.

This adapter provides a no-op implementation of the MessagingChannel protocol
for testing when external messaging services (WhatsApp, Telegram, etc.) are not available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from autifyme_agents.core.logging_config import get_logger
from autifyme_agents.workflows.channels.protocol import ChannelError
from autifyme_agents.schemas.models import Product, CatalogingResult

logger = get_logger(__name__)


class MockChannel:
    """Mock implementation of MessagingChannel protocol for testing.

    This channel logs all operations but doesn't actually send messages.
    Useful for development and testing when external services are unavailable.
    """

    def __init__(self, channel_name: str = "mock"):
        """Initialize mock channel.

        Args:
            channel_name: Name of the channel for logging purposes
        """
        self.channel_name = channel_name
        logger.info(f"Mock {channel_name} channel initialized")

    def send_text(
        self,
        recipient: str,
        message: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Mock send text message.

        Args:
            recipient: Recipient identifier
            message: Message content
            metadata: Optional metadata

        Returns:
            Mock response dict
        """
        logger.info(
            f"[MOCK {self.channel_name.upper()}] Sending text to {recipient}",
            extra={
                "recipient": recipient,
                "message_length": len(message),
                "message_preview": message[:100] + "..." if len(message) > 100 else message,
            },
        )
        return {"status": "sent", "channel": self.channel_name, "recipient": recipient}

    def send_approval_request(
        self,
        recipient: str,
        draft: Product,
    ) -> dict[str, Any]:
        """Mock send approval request.

        Args:
            recipient: Recipient identifier
            draft: Product draft requiring approval

        Returns:
            Mock response dict
        """
        logger.info(
            f"[MOCK {self.channel_name.upper()}] Sending approval request to {recipient}",
            extra={
                "recipient": recipient,
                "product_name": draft.name,
                "product_id": getattr(draft, 'id', 'unknown'),
            },
        )
        return {"status": "approval_sent", "channel": self.channel_name, "recipient": recipient}

    def send_completion(
        self,
        recipient: str,
        result: CatalogingResult,
    ) -> dict[str, Any]:
        """Mock send completion message.

        Args:
            recipient: Recipient identifier
            result: Cataloging result to communicate

        Returns:
            Mock response dict
        """
        logger.info(
            f"[MOCK {self.channel_name.upper()}] Sending completion to {recipient}",
            extra={
                "recipient": recipient,
                "success": result.success,
                "product_name": result.product_name,
            },
        )
        return {"status": "completion_sent", "channel": self.channel_name, "recipient": recipient}

    def send_error(
        self,
        recipient: str,
        error_type: Literal["media_download", "processing", "recursion"],
        message: str | None = None,
    ) -> dict[str, Any]:
        """Mock send error message.

        Args:
            recipient: Recipient identifier
            error_type: Category of error
            message: Optional custom error message

        Returns:
            Mock response dict
        """
        logger.warning(
            f"[MOCK {self.channel_name.upper()}] Sending error to {recipient}",
            extra={
                "recipient": recipient,
                "error_type": error_type,
                "custom_message": message is not None,
            },
        )
        return {"status": "error_sent", "channel": self.channel_name, "recipient": recipient}

    def download_media(self, media_id: str) -> Path:
        """Mock download media.

        Args:
            media_id: Media identifier

        Returns:
            Mock file path

        Raises:
            ChannelError: Always raises error as mock doesn't support media
        """
        logger.warning(
            f"[MOCK {self.channel_name.upper()}] Media download requested but not supported",
            extra={"media_id": media_id},
        )
        raise ChannelError(
            f"Mock {self.channel_name} channel does not support media download",
            channel=self.channel_name,
            original_error=NotImplementedError("Media download not supported in mock channel"),
        )

    def format_thread_id(self, sender: str) -> str:
        """Generate mock thread ID for checkpointing.

        Args:
            sender: Sender identifier

        Returns:
            Thread ID for LangGraph checkpointer
        """
        return f"{self.channel_name}:{sender}"

    def handle_approval(self, sender: str, text: str) -> None:
        """Mock handle approval message.

        Args:
            sender: Sender identifier
            text: Approval message text
        """
        logger.info(
            f"[MOCK {self.channel_name.upper()}] Handling approval from {sender}",
            extra={"sender": sender, "text": text},
        )
        # Mock implementation - in real channels this would resume the workflow