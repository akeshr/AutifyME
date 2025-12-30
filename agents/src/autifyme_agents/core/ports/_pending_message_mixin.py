"""Pending message mixin for batching rapid-fire WhatsApp messages."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class PendingMessageMixin(ABC):
    """Operations for buffering and batching messages before PM processing.

    Supports Smart Skip logic:
    - Media messages always debounce (users often send multiple images)
    - Text messages debounce only if recent activity from sender exists
    - Batch processing reduces PM invocations and provides unified context
    """

    @abstractmethod
    async def queue_pending_message(
        self,
        message_id: str,
        sender_id: str,
        thread_id: str,
        message_type: str,
        text_content: str | None,
        media_id: str | None,
        caption: str | None,
        sender_name: str | None,
        received_at: datetime,
    ) -> dict[str, Any]:
        """Queue a message for batch processing.

        Args:
            message_id: WhatsApp message ID (unique)
            sender_id: Phone number
            thread_id: LangGraph thread ID
            message_type: text, image, video, document, audio, voice
            text_content: Message text (if any)
            media_id: WhatsApp media ID (if any)
            caption: Media caption (if any)
            sender_name: User display name (if available)
            received_at: When webhook was received

        Returns:
            Inserted record with id and batch_key
        """
        pass

    @abstractmethod
    async def fetch_and_clear_batch(self, batch_key: str) -> list[dict[str, Any]]:
        """Atomically fetch and delete all pending messages for a sender.

        This is the core batching operation - retrieves all queued messages
        and removes them from the buffer in a single atomic operation.

        Args:
            batch_key: Sender ID (grouping key)

        Returns:
            List of pending message records, ordered by created_at ASC
        """
        pass

    @abstractmethod
    async def has_recent_activity(
        self, sender_id: str, window_seconds: int | float = 5
    ) -> bool:
        """Check if sender has recent activity within time window.

        Used for Smart Skip logic: text messages only debounce if
        there's recent activity (indicating a burst of messages).

        Args:
            sender_id: Phone number
            window_seconds: Lookback window (default 5s)

        Returns:
            True if sender has pending messages created within window
        """
        pass

    @abstractmethod
    async def has_pending_messages(self, sender_id: str) -> bool:
        """Check if sender has any messages in the buffer.

        Args:
            sender_id: Phone number

        Returns:
            True if sender has at least one pending message
        """
        pass

    @abstractmethod
    async def get_orphaned_batches(
        self, age_seconds: int = 33
    ) -> list[dict[str, Any]]:
        """Get pending messages older than expected processing time.

        Used for server restart recovery - these messages were queued
        but never processed (server crashed before timer fired).

        Args:
            age_seconds: Age threshold (default 33s = 3s debounce + 30s buffer)

        Returns:
            List of orphaned message records grouped by batch_key
        """
        pass
