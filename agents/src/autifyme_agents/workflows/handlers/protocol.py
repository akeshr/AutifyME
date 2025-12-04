"""Protocol for workflow-specific handlers."""

from __future__ import annotations

from typing import Any, Protocol


class WorkflowHandler(Protocol):
    """Protocol for workflow-specific message extraction and interrupt handling.

    Implementations handle domain-specific logic for different workflow types
    (cataloging, customer service, etc.).
    """

    def extract_summary(self, messages: list[Any]) -> str | None:
        """Extract AI summary for conversational responses.

        Args:
            messages: PM output messages

        Returns:
            Summary string if found, None otherwise
        """
        ...

    def handle_interrupt(
        self,
        sender: str,
        thread_id: str,
        interrupt_value: Any,
    ) -> None:
        """Send workflow-specific interrupt to user via channel.

        Args:
            sender: Channel-specific sender ID
            thread_id: Conversation thread ID
            interrupt_value: Interrupt value from LangGraph (may be wrapped)
        """
        ...
