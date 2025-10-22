"""Interrupt data models for type-safe interrupt handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InterruptInfo:
    """Normalized interrupt information for approval processing.

    This dataclass provides type safety and immutability for interrupt data
    flowing between InterruptUnpacker and ApprovalCoordinator.

    Attributes:
        interrupt_id: Unique identifier (may have suffix like "id_0", "id_1")
        tool_name: Name of the tool being called
        tool_args: Arguments for the tool call
        description: Human-readable description of the action
        original_interrupt_id: Optional original ID without suffix (for Command building)
    """

    interrupt_id: str
    tool_name: str
    tool_args: dict[str, Any]
    description: str
    original_interrupt_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict format for backward compatibility.

        Returns:
            Dict representation with all fields
        """
        return {
            "interrupt_id": self.interrupt_id,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "description": self.description,
            "original_interrupt_id": self.original_interrupt_id or self.interrupt_id,
        }
