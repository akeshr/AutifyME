"""Recovery strategy for workflow error handling.

Handles abandonment detection and auto-recovery from orphaned state.

Design Principle: Single Responsibility - only handles recovery logic, not workflow execution.
"""

from __future__ import annotations

from typing import Callable
from langgraph.checkpoint.base import BaseCheckpointSaver

from autifyme_agents.core.logging_config import get_logger
from autifyme_agents.workflows.orchestration.state_manager import StateManager

logger = get_logger(__name__)


class RecoveryStrategy:
    """Handles workflow error recovery and abandonment detection.

    Responsibilities:
    - Detect abandonment scenarios (user starts new request before approving)
    - Clear orphaned state (approval + checkpoint)
    - Auto-recover from INVALID_CHAT_HISTORY errors

    NOT responsible for:
    - Workflow execution
    - Decision logic beyond abandonment detection
    """

    def __init__(
        self,
        state_manager: StateManager,
        checkpointer_factory: Callable[[], BaseCheckpointSaver],
    ):
        """Initialize recovery strategy.

        Args:
            state_manager: State manager for approval operations
            checkpointer_factory: Factory function returning checkpointer instance
        """
        self.state = state_manager
        self.get_checkpointer = checkpointer_factory

    def should_clear_state(
        self,
        thread_id: str,
        new_message_has_media: bool,
    ) -> bool:
        """Determine if state should be cleared (abandonment detection).

        Abandonment occurs when user sends a NEW product request (with media)
        while an approval is still pending. This indicates they've moved on to
        a different product and we should clear the old workflow state.

        Args:
            thread_id: Conversation thread ID
            new_message_has_media: Whether new message includes media attachment

        Returns:
            True if state should be cleared (abandonment detected), False otherwise

        Design Note:
            - Text-only messages during approval are treated as conversation
              continuation (clarifications, edits), NOT abandonment
            - Only media-bearing messages trigger abandonment detection
            - This is proactive recovery - catches known scenarios before errors occur
        """
        pending = self.state.get_pending_approval(thread_id)

        if not pending:
            # No pending approval - nothing to abandon
            return False

        # User sent NEW product (with media) while approval pending
        # This is abandonment - clear state for fresh start
        if new_message_has_media:
            logger.info(
                "Abandonment detected: user sent new media while approval pending",
                extra={
                    "thread_id": thread_id,
                    "pending_interrupt_id": pending.get("interrupt_id"),
                },
            )
            return True

        # Text-only message - treat as conversation continuation
        logger.debug(
            "Text-only message during approval - treating as continuation",
            extra={"thread_id": thread_id},
        )
        return False

    def clear_orphaned_state(self, thread_id: str) -> None:
        """Clear both approval and checkpoint for clean restart.

        This is called when abandonment is detected or when auto-recovery
        needs to clean up orphaned state.

        Args:
            thread_id: Conversation thread ID
        """
        logger.info(
            "Clearing orphaned state",
            extra={"thread_id": thread_id},
        )

        # Clear approval record
        self.state.delete_pending_approval(thread_id)

        # Clear checkpoint
        try:
            checkpointer = self.get_checkpointer()
            with checkpointer as saver:
                saver.delete_thread(thread_id)
                logger.info(
                    "Cleared checkpoint for clean restart",
                    extra={"thread_id": thread_id},
                )
        except Exception as exc:
            logger.exception(
                "Failed to clear checkpoint during recovery",
                exc_info=exc,
                extra={"thread_id": thread_id},
            )
            # Don't re-raise - approval is already cleared, checkpoint cleanup is best-effort

    def auto_recover(self, thread_id: str) -> None:
        """Auto-recover from INVALID_CHAT_HISTORY error.

        This is reactive recovery for unexpected edge cases that slip through
        proactive abandonment detection:
        - Server crashes during interrupt handling
        - Race conditions in concurrent requests
        - Future bugs in workflow logic

        This is "defense in depth" - proactive detection handles known scenarios,
        this catches everything else.

        Args:
            thread_id: Conversation thread ID
        """
        logger.warning(
            "Auto-recovery triggered for orphaned state (reactive recovery)",
            extra={"thread_id": thread_id},
        )
        self.clear_orphaned_state(thread_id)
