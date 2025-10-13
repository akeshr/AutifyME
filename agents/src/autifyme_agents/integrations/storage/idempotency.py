"""Database-backed idempotency checker for webhook deduplication."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

logger = logging.getLogger(__name__)


class IdempotencyChecker:
    """Persistent idempotency checks using PostgreSQL via Supabase.

    Prevents duplicate webhook processing by tracking message_id in database.
    Survives server restarts and works across distributed containers.
    """

    def __init__(self, storage: "SupabaseStorageClient"):
        """Initialize idempotency checker.

        Args:
            storage: Supabase storage client for database access
        """
        self.storage = storage
        self._client = storage.supabase

    def is_processed_and_mark(
        self,
        message_id: str,
        sender_id: str,
        thread_id: str,
        received_at: datetime,
    ) -> bool:
        """Atomically check if message is duplicate AND mark as processed.

        This is the core idempotency operation. Uses PostgreSQL stored procedure
        for atomic INSERT ON CONFLICT to prevent race conditions.

        Args:
            message_id: WhatsApp message ID (unique across retries)
            sender_id: Phone number
            thread_id: LangGraph thread ID
            received_at: When webhook was received

        Returns:
            True if duplicate (already processed), False if new (now marked as processed)
        """
        try:
            result = self._client.rpc("check_and_mark_processed", {
                "p_message_id": message_id,
                "p_sender_id": sender_id,
                "p_thread_id": thread_id,
                "p_received_at": received_at.isoformat(),
            }).execute()

            is_duplicate = result.data.get("is_duplicate", False)

            if is_duplicate:
                logger.info(
                    "Duplicate message detected (DB idempotency)",
                    extra={
                        "message_id": message_id,
                        "sender_id": sender_id,
                        "thread_id": thread_id,
                    },
                )
            else:
                logger.debug(
                    "New message marked as processed",
                    extra={"message_id": message_id},
                )

            return is_duplicate

        except Exception as exc:
            # If DB check fails, fail OPEN (allow processing) to prevent webhook blocking
            # Log error for monitoring/alerts
            logger.exception(
                "Idempotency check failed - allowing processing (fail open)",
                exc_info=exc,
                extra={
                    "message_id": message_id,
                    "error_type": type(exc).__name__,
                },
            )
            return False  # Process the message (risk: potential duplicate)
