"""PM approval decision tools for HITL workflows.

These tools enable the PM to reason about and decide on pending approvals.
The Runner intercepts tool output and converts decisions to LangGraph Command objects.

Architecture:
- PM calls tools to express approval decisions
- Tools return structured output (APPROVAL_DECISION marker)
- Runner intercepts output and builds Command(resume={...})
- Workflow resumes based on PM's decision

Design principle: Keep tools simple, Runner handles Command construction.
"""

from __future__ import annotations

import logging
from typing import Literal

from langchain_core.tools import tool, ToolException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ApprovalDecision(BaseModel):
    """Structured approval decision from PM.

    This Pydantic model ensures type-safe communication between PM and Runner.
    """

    interrupt_id: str = Field(
        description="Unique identifier for the interrupt to resume"
    )
    decision_type: Literal["accept", "reject", "edit"] = Field(
        description="Type of decision: accept (proceed), reject (abort), edit (modify)"
    )
    edited_args: dict = Field(
        default_factory=dict,
        description="Modified arguments if decision is 'edit'",
    )
    reasoning: str = Field(
        default="",
        description="Brief reasoning for the decision",
    )


@tool
def propose_workflow_resumption(
    interrupt_ids: list[str],
    decisions: list[Literal["accept", "reject", "edit"]],
    edited_args_list: list[dict] | None = None,
    reasoning: str | None = None,
) -> str:
    """Propose how to resume paused approval workflows.

    This tool allows the PM to reason about and decide on pending approvals.
    The Runner intercepts this tool call and converts it to LangGraph Commands
    to resume the workflows.

    Supports batch decisions (multiple interrupts at once).

    Args:
        interrupt_ids: List of interrupt IDs to resume (from approval_context)
        decisions: List of decisions (one per interrupt_id)
        edited_args_list: List of modified args (optional, for 'edit' decisions)
        reasoning: Brief explanation of decisions

    Returns:
        Confirmation message (Runner intercepts and builds Command)

    Example:
        PM sees: "Pending approvals: int_1 (product $120), int_2 (product $30)"
        PM decides: Both prices reasonable
        PM calls: propose_workflow_resumption(
            interrupt_ids=["int_1", "int_2"],
            decisions=["accept", "accept"],
            reasoning="Prices within acceptable range"
        )
        Tool returns: "APPROVAL_DECISION: int_1:accept|int_2:accept"
        Runner intercepts: Builds Command(resume={"int_1": [...], "int_2": [...]})
    """
    edited_args_list = edited_args_list or [{}] * len(interrupt_ids)
    reasoning = reasoning or ""

    try:
        # Validate input consistency
        if len(interrupt_ids) != len(decisions):
            raise ValueError(
                f"Mismatch: {len(interrupt_ids)} interrupt_ids but {len(decisions)} decisions"
            )

        if len(edited_args_list) != len(interrupt_ids):
            raise ValueError(
                f"Mismatch: {len(interrupt_ids)} interrupt_ids but {len(edited_args_list)} edited_args"
            )

        # Validate each decision
        validated_decisions = []
        for i, (interrupt_id, decision, edited_args) in enumerate(
            zip(interrupt_ids, decisions, edited_args_list)
        ):
            decision_obj = ApprovalDecision(
                interrupt_id=interrupt_id,
                decision_type=decision,
                edited_args=edited_args,
                reasoning=reasoning,
            )
            validated_decisions.append(decision_obj)

        logger.info(
            "PM proposed workflow resumption",
            extra={
                "interrupt_count": len(interrupt_ids),
                "decisions": decisions,
                "has_edits": any(len(args) > 0 for args in edited_args_list),
            },
        )

        # Build output format that Runner can intercept
        # Format: "APPROVAL_DECISION: int_1:accept|int_2:edit|int_3:reject"
        decision_parts = [
            f"{dec.interrupt_id}:{dec.decision_type}"
            for dec in validated_decisions
        ]
        output = f"APPROVAL_DECISION: {' | '.join(decision_parts)}"

        logger.debug(
            "Built approval decision output",
            extra={"output": output, "reasoning": reasoning[:100]},
        )

        return output

    except ValueError as e:
        logger.warning(
            "Invalid approval decision",
            extra={"error": str(e), "interrupt_ids": interrupt_ids},
        )
        raise ToolException(f"Invalid approval decision: {str(e)}")
    except Exception as e:
        logger.exception(
            "Unexpected error in approval decision",
            extra={"interrupt_ids": interrupt_ids},
        )
        raise ToolException(f"Approval decision failed: {str(e)}")


@tool
def reject_workflow_approval(
    interrupt_ids: list[str], reason: str
) -> str:
    """Explicitly reject approval requests.

    Shorthand for propose_workflow_resumption with all decisions='reject'.
    Use this when PM determines the actions should not proceed.

    Args:
        interrupt_ids: List of interrupt IDs to reject
        reason: Explanation for rejection

    Returns:
        Confirmation message (Runner intercepts)

    Example:
        PM sees: "Pending approval: int_1 (product with missing description)"
        PM decides: Cannot approve without description
        PM calls: reject_workflow_approval(
            interrupt_ids=["int_1"],
            reason="Product description required"
        )
        Tool returns: "APPROVAL_DECISION: int_1:reject"
        Runner intercepts: Builds Command + sends error to user
    """
    try:
        logger.info(
            "PM rejected workflow approvals",
            extra={"interrupt_count": len(interrupt_ids), "reason": reason[:100]},
        )

        # Build rejection output
        decision_parts = [f"{interrupt_id}:reject" for interrupt_id in interrupt_ids]
        output = f"APPROVAL_DECISION: {' | '.join(decision_parts)}"

        logger.debug(
            "Built rejection output", extra={"output": output, "reason": reason[:100]}
        )

        return output

    except Exception as e:
        logger.exception(
            "Unexpected error in rejection", extra={"interrupt_ids": interrupt_ids}
        )
        raise ToolException(f"Rejection failed: {str(e)}")
