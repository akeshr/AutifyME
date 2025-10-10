"""Messaging channel protocol definition.

Defines the abstract interface that all messaging channel implementations
must satisfy. This enables channel-agnostic workflow orchestration.

Design Pattern: Strategy Pattern + Protocol (structural subtyping)
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Literal, Any

from autifyme_agents.schemas.models import Product, CatalogingResult


class MessagingChannel(Protocol):
    """Abstract protocol for messaging channel implementations.

    All messaging platforms (WhatsApp, SMS, Telegram, etc.) must implement
    this interface to be compatible with the generic WorkflowRunner.

    Design Notes:
    - Uses Protocol for structural subtyping (no inheritance required)
    - Each method has clear input/output contract
    - Channel-specific formatting is encapsulated in implementations
    - Return types are simple dicts (keep it flexible)
    """

    def send_text(
        self,
        recipient: str,
        message: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a plain text message.

        Args:
            recipient: Channel-specific recipient ID (e.g., phone number for WhatsApp)
            message: Message content (plain text or channel-specific format)
            metadata: Optional channel-specific metadata (e.g., preview_url for WhatsApp)

        Returns:
            Channel-specific response dict (e.g., {"message_id": "..."})

        Raises:
            ChannelError: If message sending fails
        """
        ...

    def send_approval_request(
        self,
        recipient: str,
        draft: Product,
    ) -> dict[str, Any]:
        """Send HITL approval request formatted for this channel.

        Args:
            recipient: Channel-specific recipient ID
            draft: Product draft requiring approval

        Returns:
            Channel-specific response dict

        Raises:
            ChannelError: If message sending fails

        Notes:
            - Formatting is channel-specific (e.g., WhatsApp markdown, SMS plain text)
            - Should include all relevant product details
            - Should prompt for approve/reject response
        """
        ...

    def send_completion(
        self,
        recipient: str,
        result: CatalogingResult,
    ) -> dict[str, Any]:
        """Send workflow completion message.

        Args:
            recipient: Channel-specific recipient ID
            result: Cataloging result to communicate

        Returns:
            Channel-specific response dict

        Raises:
            ChannelError: If message sending fails

        Notes:
            - Message should be success-focused and user-friendly
            - Include product name and confirmation
        """
        ...

    def send_error(
        self,
        recipient: str,
        error_type: Literal["media_download", "processing", "recursion"],
        message: str | None = None,
    ) -> dict[str, Any]:
        """Send user-friendly error message.

        Args:
            recipient: Channel-specific recipient ID
            error_type: Category of error (for choosing appropriate message)
            message: Optional custom error message (overrides default)

        Returns:
            Channel-specific response dict

        Raises:
            ChannelError: If message sending fails (critical)

        Notes:
            - Should be user-friendly (no technical jargon)
            - Should suggest recovery action when possible
        """
        ...

    def download_media(self, media_id: str) -> Path | None:
        """Download media file to temporary location.

        Args:
            media_id: Channel-specific media identifier

        Returns:
            Path to downloaded file, or None if media not found/not applicable

        Raises:
            ChannelError: If download fails

        Notes:
            - File should be temporary (caller is responsible for cleanup)
            - Should handle authentication/authorization internally
            - None return indicates graceful failure (not an error)
        """
        ...

    def format_thread_id(self, sender: str) -> str:
        """Generate channel-specific thread ID for checkpointing.

        Args:
            sender: Channel-specific sender identifier

        Returns:
            Thread ID for LangGraph checkpointer (unique per conversation)

        Notes:
            - Used to maintain conversation state across messages
            - Should be deterministic (same sender → same thread_id)
            - Example: WhatsApp uses "whatsapp:{phone_number}"
        """
        ...


class ChannelError(Exception):
    """Base exception for all channel adapter errors.

    Raised when channel-specific operations fail (API errors, network issues, etc.).
    The workflow runner should catch and handle these gracefully.
    """

    def __init__(
        self,
        message: str,
        *,
        channel: str | None = None,
        recipient: str | None = None,
        original_error: Exception | None = None,
    ):
        """Initialize channel error.

        Args:
            message: Human-readable error description
            channel: Channel name (e.g., "whatsapp", "sms")
            recipient: Recipient ID where error occurred
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.channel = channel
        self.recipient = recipient
        self.original_error = original_error
