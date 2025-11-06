"""Pydantic schemas for HITL approval responses.

These schemas ensure type-safe communication between the approval analyzer
and runner when handling batch HITL interrupts.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HumanInTheLoopResponse(BaseModel):
    """Single response for one HITL interrupt.

    Simplified to binary approval model - approval analyzer does NOT modify domain data.

    Attributes:
        type: Response type - accept (approve operation) or reject (user rejected or wants changes)
        user_message: For reject, the exact user message explaining what they want changed.
                     For accept, this is empty/None.

    Design Philosophy:
        - Approval analyzer: Simple binary decision (accept/reject)
        - Specialist: Handles all domain work including regenerating operations based on feedback
        - PM: Receives rejection with user message, delegates back to specialist
    """

    type: Literal["accept", "reject"] = Field(
        description="Response type: accept (approve) or reject (user wants changes or rejects)"
    )
    user_message: str | None = Field(
        default=None,
        description="For reject: exact user message explaining rejection/changes. For accept: None.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"type": "accept", "user_message": None},
                {"type": "reject", "user_message": "change price to 25"},
                {"type": "reject", "user_message": "no, I want it cheaper"},
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
                        {"type": "accept", "user_message": None},
                        {"type": "accept", "user_message": None},
                    ],
                    "reasoning": "User approved both pending operations",
                },
                {
                    "responses": [
                        {"type": "accept", "user_message": None},
                        {"type": "reject", "user_message": "make the price 45 instead"},
                    ],
                    "reasoning": "User approved first operation, wants changes to second",
                },
                {
                    "responses": [
                        {"type": "reject", "user_message": "no, I don't want this"},
                        {"type": "reject", "user_message": "no, I don't want this"},
                    ],
                    "reasoning": "User rejected all pending operations",
                },
            ]
        }
    )
