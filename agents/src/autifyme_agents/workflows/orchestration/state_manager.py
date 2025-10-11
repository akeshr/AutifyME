"""State manager for approval persistence.

Provides a clean API for managing approval state during HITL workflows.
This is a thin wrapper around StorageInterface focusing on approval operations.

Design Principle: Single Responsibility - only handles approval state, not checkpoints.
"""

from __future__ import annotations

from typing import Any

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.models import Product


class StateManager:
    """Manages approval state persistence.

    Responsibilities:
    - Save/retrieve pending approvals
    - Check approval existence
    - Delete approvals after resolution

    NOT responsible for:
    - Checkpointer operations (delegates to caller)
    - Business logic (pure data operations)
    """

    def __init__(self, storage: StorageInterface):
        """Initialize state manager with storage adapter.

        Args:
            storage: Storage adapter implementing StorageInterface
        """
        self.storage = storage

    def save_pending_approval(
        self,
        thread_id: str,
        approval_data: Any,  # ApprovalRequest (avoid circular import)
        media_path: str | None = None,
        agent_source: str = "cataloging_department",
        checkpoint_ns: str | None = None,
    ) -> None:
        """Persist approval request for restart resilience.

        Args:
            thread_id: Conversation thread ID
            approval_data: Structured approval request with interrupt/tool/draft data
            media_path: Optional media file path to preserve until resolution
            agent_source: Agent source identifier for resumption
            checkpoint_ns: Checkpoint namespace for resumption
        """
        # Format draft for storage (human-readable summary)
        draft_summary = self._format_draft(approval_data.draft)

        # Delegate to storage
        self.storage.save_pending_approval(
            thread_id=thread_id,
            interrupt_id=approval_data.interrupt_id,
            checkpoint_id=approval_data.checkpoint_id,
            tool_call=approval_data.tool_call,
            draft_summary=draft_summary,
            ai_message=approval_data.ai_message,
            image_path=media_path,
            agent_source=agent_source,
            checkpoint_ns=checkpoint_ns,
        )

    def get_pending_approval(self, thread_id: str) -> dict[str, Any] | None:
        """Retrieve pending approval for thread.

        Args:
            thread_id: Conversation thread ID

        Returns:
            Approval data dict, or None if no pending approval
        """
        return self.storage.get_pending_approval(thread_id)

    def has_pending_approval(self, thread_id: str) -> bool:
        """Check if thread has pending approval.

        Args:
            thread_id: Conversation thread ID

        Returns:
            True if pending approval exists, False otherwise
        """
        return self.get_pending_approval(thread_id) is not None

    def delete_pending_approval(self, thread_id: str) -> None:
        """Clear pending approval after resolution.

        Args:
            thread_id: Conversation thread ID
        """
        self.storage.delete_pending_approval(thread_id)

    def _format_draft(self, draft: Product) -> str:
        """Format product draft as human-readable summary.

        Args:
            draft: Product draft to format

        Returns:
            Human-readable summary string
        """
        lines = [f"Product: {draft.name}"]

        if draft.price is not None:
            lines.append(f"Price: {draft.price}")
        else:
            lines.append("Price: n/a")

        if draft.sizes:
            sizes_text = ", ".join(str(s) for s in draft.sizes if s)
            lines.append(f"Sizes: {sizes_text}")
        else:
            lines.append("Sizes: n/a")

        if draft.description:
            lines.append(f"Description: {draft.description}")

        return "\n".join(lines)
