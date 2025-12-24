"""Message batcher for Smart Skip debouncing of rapid-fire WhatsApp messages.

Handles multi-image scenarios where users send multiple images in quick succession.
Uses database-backed buffering with in-memory timer management for reliability.

Key Design Decisions:
- DB-backed buffer: Survives server restarts, enables orphan recovery
- In-memory timers: Fast, no DB polling overhead
- Smart Skip: Only debounces media or when recent activity detected
- Fail-open: If DB check fails, process immediately (safe default)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from autifyme_agents.core.config import settings
from autifyme_agents.core.ports import StorageInterface

if TYPE_CHECKING:
    from autifyme_agents.workflows.orchestration.runner import WorkflowRunner

logger = logging.getLogger(__name__)

# Message types that always trigger debouncing
MEDIA_TYPES = frozenset({"image", "video", "document", "audio", "voice"})


class MessageBatcher:
    """Batches rapid-fire WhatsApp messages before PM processing.

    Smart Skip Logic:
    - Media messages (image/video/document/audio) always debounce
    - Text messages only debounce if recent activity or pending messages exist
    - Single text with no activity processes immediately (zero latency)

    Flow:
    1. should_debounce() determines if message needs batching
    2. If yes: queue_message() stores in DB and starts timer (if not running)
    3. Timer fires after debounce window: fetch_and_process_batch()
    4. All pending messages for sender processed as unified batch
    """

    def __init__(
        self,
        storage: StorageInterface,
        debounce_seconds: float | None = None,
        recent_window_seconds: int | None = None,
        max_batch_size: int | None = None,
    ):
        """Initialize MessageBatcher.

        Args:
            storage: Storage interface for DB operations
            debounce_seconds: Debounce window (default from settings)
            recent_window_seconds: Recent activity window (default from settings)
            max_batch_size: Max messages per batch (default from settings)
        """
        self._storage = storage
        self._debounce_seconds = (
            debounce_seconds
            if debounce_seconds is not None
            else settings.MESSAGE_BATCH_DEBOUNCE_SECONDS
        )
        self._recent_window_seconds = (
            recent_window_seconds
            if recent_window_seconds is not None
            else settings.MESSAGE_BATCH_RECENT_WINDOW_SECONDS
        )
        self._max_batch_size = (
            max_batch_size
            if max_batch_size is not None
            else settings.MESSAGE_BATCH_MAX_SIZE
        )

        # In-memory timer registry: sender_id -> (timer_task, runner)
        self._active_timers: dict[str, tuple[asyncio.Task[None], WorkflowRunner]] = {}
        self._lock = asyncio.Lock()

        logger.info(
            "MessageBatcher initialized",
            extra={
                "debounce_seconds": self._debounce_seconds,
                "recent_window_seconds": self._recent_window_seconds,
                "max_batch_size": self._max_batch_size,
            },
        )

    async def should_debounce(self, sender_id: str, message_type: str) -> bool:
        """Determine if message should be debounced (Smart Skip logic).

        Returns True if:
        - Message is media (image/video/document/audio/voice), OR
        - Sender has recent activity in buffer, OR
        - Sender has any pending messages in buffer

        Text-only messages with no recent activity process immediately.

        Args:
            sender_id: Phone number
            message_type: WhatsApp message type

        Returns:
            True if message should be debounced, False for immediate processing
        """
        # Media messages always debounce (common multi-image scenario)
        if message_type in MEDIA_TYPES:
            logger.debug(
                "Debouncing media message",
                extra={"sender_id": sender_id, "message_type": message_type},
            )
            return True

        # Text messages: check for recent activity or pending messages
        # These checks are fail-open (return False on error = process immediately)
        try:
            has_recent = await self._storage.has_recent_activity(
                sender_id, self._recent_window_seconds
            )
            if has_recent:
                logger.debug(
                    "Debouncing text message (recent activity detected)",
                    extra={"sender_id": sender_id},
                )
                return True

            has_pending = await self._storage.has_pending_messages(sender_id)
            if has_pending:
                logger.debug(
                    "Debouncing text message (pending messages exist)",
                    extra={"sender_id": sender_id},
                )
                return True

        except Exception:
            # Fail open: process immediately if DB check fails
            logger.warning(
                "Smart Skip check failed, processing immediately",
                exc_info=True,
                extra={"sender_id": sender_id},
            )
            return False

        # Text message with no recent activity: process immediately
        logger.debug(
            "No debounce needed (text with no recent activity)",
            extra={"sender_id": sender_id},
        )
        return False

    async def queue_message(
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
        runner: WorkflowRunner,
    ) -> bool:
        """Queue message for batch processing and start timer if needed.

        Args:
            message_id: WhatsApp message ID
            sender_id: Phone number
            thread_id: LangGraph thread ID
            message_type: text, image, video, document, audio, voice
            text_content: Message text (if any)
            media_id: WhatsApp media ID (if any)
            caption: Media caption (if any)
            sender_name: User display name
            received_at: When webhook was received
            runner: WorkflowRunner for batch processing

        Returns:
            True if new timer was started, False if timer already running
        """
        # Store message in DB buffer
        await self._storage.queue_pending_message(
            message_id=message_id,
            sender_id=sender_id,
            thread_id=thread_id,
            message_type=message_type,
            text_content=text_content,
            media_id=media_id,
            caption=caption,
            sender_name=sender_name,
            received_at=received_at,
        )

        # Check if timer already running for this sender
        async with self._lock:
            if sender_id in self._active_timers:
                logger.debug(
                    "Timer already running, message added to batch",
                    extra={"sender_id": sender_id, "message_id": message_id},
                )
                return False

            # Start new debounce timer
            timer_task = asyncio.create_task(
                self._debounce_and_process(sender_id, runner),
                name=f"debounce_{sender_id}",
            )
            self._active_timers[sender_id] = (timer_task, runner)

            logger.info(
                "Started debounce timer for sender",
                extra={
                    "sender_id": sender_id,
                    "debounce_seconds": self._debounce_seconds,
                },
            )
            return True

    async def _debounce_and_process(
        self, sender_id: str, runner: WorkflowRunner
    ) -> None:
        """Wait for debounce window, then process batch.

        Args:
            sender_id: Phone number (batch key)
            runner: WorkflowRunner for batch processing
        """
        try:
            # Wait for debounce window
            await asyncio.sleep(self._debounce_seconds)

            # Remove timer from registry
            async with self._lock:
                self._active_timers.pop(sender_id, None)

            # Fetch and process batch
            await self._fetch_and_process_batch(sender_id, runner)

        except asyncio.CancelledError:
            # Task cancelled (e.g., shutdown) - messages stay in DB for recovery
            logger.info(
                "Debounce timer cancelled, messages preserved for recovery",
                extra={"sender_id": sender_id},
            )
            async with self._lock:
                self._active_timers.pop(sender_id, None)
            raise

        except Exception:
            logger.error(
                "Debounce timer error",
                exc_info=True,
                extra={"sender_id": sender_id},
            )
            async with self._lock:
                self._active_timers.pop(sender_id, None)

    async def _fetch_and_process_batch(
        self, sender_id: str, runner: WorkflowRunner
    ) -> None:
        """Atomically fetch pending messages and process as batch.

        Args:
            sender_id: Phone number (batch key)
            runner: WorkflowRunner for batch processing
        """
        # Atomic fetch-and-delete from DB
        batch = await self._storage.fetch_and_clear_batch(sender_id)

        if not batch:
            logger.warning(
                "Batch empty after debounce (messages expired or processed elsewhere)",
                extra={"sender_id": sender_id},
            )
            return

        # Safety limit: process max_batch_size messages
        if len(batch) > self._max_batch_size:
            logger.warning(
                "Batch exceeds max size, truncating",
                extra={
                    "sender_id": sender_id,
                    "batch_size": len(batch),
                    "max_size": self._max_batch_size,
                },
            )
            batch = batch[: self._max_batch_size]

        logger.info(
            "Processing message batch",
            extra={
                "sender_id": sender_id,
                "batch_size": len(batch),
                "message_types": [m.get("message_type") for m in batch],
            },
        )

        # Delegate to runner for PM processing
        await runner.handle_message_batch(sender_id, batch)

    async def recover_orphaned_batches(self, runner: WorkflowRunner) -> int:
        """Recover and process orphaned messages from previous server instance.

        Called on startup to handle messages that were queued but never
        processed (server crashed before timer fired).

        Args:
            runner: WorkflowRunner for batch processing

        Returns:
            Number of orphaned messages recovered
        """
        orphaned = await self._storage.get_orphaned_batches()

        if not orphaned:
            logger.debug("No orphaned batches found")
            return 0

        # Group by sender
        batches_by_sender: dict[str, list[dict[str, Any]]] = {}
        for msg in orphaned:
            sender_id = msg.get("sender_id", msg.get("batch_key"))
            if sender_id:
                batches_by_sender.setdefault(sender_id, []).append(msg)

        recovered_count = 0
        for sender_id, batch in batches_by_sender.items():
            try:
                logger.info(
                    "Recovering orphaned batch",
                    extra={"sender_id": sender_id, "message_count": len(batch)},
                )
                # Clear from DB and process
                await self._storage.fetch_and_clear_batch(sender_id)
                await runner.handle_message_batch(sender_id, batch)
                recovered_count += len(batch)
            except Exception:
                logger.error(
                    "Failed to recover orphaned batch",
                    exc_info=True,
                    extra={"sender_id": sender_id},
                )

        logger.info(
            "Orphaned batch recovery complete",
            extra={"recovered_count": recovered_count},
        )
        return recovered_count

    async def shutdown(self) -> None:
        """Cancel all active timers gracefully.

        Called during application shutdown. Messages remain in DB
        for recovery on next startup.
        """
        async with self._lock:
            for sender_id, (task, _) in self._active_timers.items():
                logger.debug("Cancelling timer for sender", extra={"sender_id": sender_id})
                task.cancel()

            # Wait for all tasks to complete cancellation
            if self._active_timers:
                tasks = [t for t, _ in self._active_timers.values()]
                await asyncio.gather(*tasks, return_exceptions=True)

            self._active_timers.clear()

        logger.info("MessageBatcher shutdown complete")
