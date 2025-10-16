"""Pydantic schemas for HITL approval responses.

These schemas ensure type-safe communication between the approval analyzer
and runner when handling batch HITL interrupts.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class HumanInTheLoopResponse(BaseModel):
    """Single response for one HITL interrupt.

    This schema matches langchain.agents.middleware.human_in_the_loop expectations
    for resuming interrupted workflows.

    Attributes:
        type: Response type - accept (approve as-is), edit (approve with changes),
              or response (reject/clarify)
        args: Additional data based on type:
              - accept: None
              - edit: dict with field → value mappings (e.g., {"price": 45.0})
              - response: string message explaining rejection/clarification
    """

    type: Literal["accept", "edit", "response"] = Field(
        description="Response type: accept, edit, or response"
    )
    args: dict[str, Any] | str | None = Field(
        default=None,
        description="Arguments: None for accept, dict for edit, string for response",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"type": "accept", "args": None},
                {"type": "edit", "args": {"price": 45.0, "name": "Updated Name"}},
                {"type": "response", "args": "User rejected this item"},
            ]
        }
    )


class InterruptContext(BaseModel):
    """Context about a pending HITL interrupt.

    This is passed to the approval analyzer to provide context about what the user
    is approving/rejecting.

    Attributes:
        interrupt_id: Unique identifier for this interrupt
        tool_name: Name of the tool that triggered the interrupt (e.g., "save_product")
        tool_args: Arguments that were passed to the tool
        description: Human-readable description of what's being interrupted
    """

    interrupt_id: str = Field(description="Unique interrupt identifier")
    tool_name: str = Field(description="Tool that triggered interrupt")
    tool_args: dict[str, Any] = Field(description="Tool arguments")
    description: str = Field(
        default="",
        description="Human-readable description of pending action",
    )


class BatchApprovalResponse(BaseModel):
    """Structured response for batch HITL approval.

    The approval analyzer returns this model, ensuring type-safe communication
    with the runner and proper validation of response count.

    Attributes:
        responses: List of responses, one per pending interrupt.
                   CRITICAL: len(responses) MUST equal len(pending_interrupts)
        reasoning: Brief explanation of how user input was interpreted.
                   Useful for debugging and logging.
    """

    responses: list[HumanInTheLoopResponse] = Field(
        description="List of responses matching pending interrupts by index"
    )
    reasoning: str = Field(
        description="Explanation of how user input was interpreted"
    )

    def validate_count(self, expected: int) -> None:
        """Validate that response count matches expected interrupt count.

        Args:
            expected: Expected number of pending interrupts

        Raises:
            ValueError: If response count doesn't match expected count
        """
        if len(self.responses) != expected:
            raise ValueError(
                f"Response count mismatch: got {len(self.responses)} responses, "
                f"expected {expected} (one per pending interrupt). "
                f"This is a critical error - approval analyzer must return "
                f"exactly one response per interrupt."
            )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "responses": [
                        {"type": "accept", "args": None},
                        {"type": "accept", "args": None},
                    ],
                    "reasoning": "User approved both pending items",
                },
                {
                    "responses": [
                        {"type": "accept", "args": None},
                        {"type": "edit", "args": {"price": 45.0}},
                    ],
                    "reasoning": "User approved first item as-is, requested price edit for second",
                },
                {
                    "responses": [
                        {"type": "response", "args": "User rejected"},
                        {"type": "response", "args": "User rejected"},
                    ],
                    "reasoning": "User rejected all pending items",
                },
            ]
        }
    )
