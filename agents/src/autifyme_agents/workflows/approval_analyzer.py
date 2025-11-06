"""Approval analyzer for HITL batch approval interpretation.

This module provides a lightweight LLM chain that interprets user approval
responses and returns structured BatchApprovalResponse objects. It is NOT
a full agent - just a prompt + LLM + structured output.

Architecture:
- Input: OperationIntent (extracted from pending_interrupts) + user_message (exact)
- Processing: LLM analyzes intent with structured output schema
- Output: BatchApprovalResponse (Pydantic model)

Key Design:
- No conversation history - clean approval analysis based solely on intent + user response
- Extracts only OperationIntent from tool_args (for execute_database_operation)
- Passes user message exactly as provided

This is separate from PM because:
1. PM handles orchestration (task delegation)
2. Approval analyzer handles HITL interpretation only
3. Clean separation of concerns
4. Type-safe communication via Pydantic
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.schemas.approval import BatchApprovalResponse
from autifyme_agents.schemas.interrupt import InterruptInfo

logger = logging.getLogger(__name__)


def create_approval_analyzer(llm: BaseChatModel | None = None) -> Any:
    """Create approval analyzer chain with structured output.

    This creates a lightweight LLM chain (NOT a full agent) that:
    1. Takes pending interrupts (OperationIntent only) + user message as input
    2. Interprets user intent using LLM reasoning
    3. Returns BatchApprovalResponse (structured Pydantic model)

    No state, no tools, no delegation, no conversation history - pure analysis function.
    Only receives the OperationIntent structure and exact user message.

    Args:
        llm: Optional LLM override. If None, uses default gemini-2.5-flash-lite with low temperature
             for deterministic approval interpretation.

    Returns:
        LangChain chain configured for structured output:
        Input: {"pending_interrupts": list[dict], "user_message": str}
        Output: BatchApprovalResponse

    Example:
        >>> analyzer = create_approval_analyzer()
        >>> result = analyzer.invoke({
        ...     "pending_interrupts": [
        ...         {"interrupt_id": "1", "tool_name": "execute_database_operation", "tool_args": {...}},
        ...     ],
        ...     "user_message": "approve"
        ... })
        >>> assert isinstance(result, BatchApprovalResponse)
        >>> assert len(result.responses) == 1
    """
    if llm is None:
        # Use gemini-2.5-flash for fast, deterministic approval interpretation
        llm = get_llm(provider="google", model="gemini-2.5-flash-lite", temperature=0.2)

    # Configure LLM for structured output
    # Use function_calling method to avoid OpenAI schema validation issues
    # This still returns BatchApprovalResponse Pydantic model
    structured_llm = llm.with_structured_output(
        BatchApprovalResponse,
        method="function_calling"  # More flexible than strict JSON schema
    )

    # Load prompt template
    prompt_text = load_prompt("approval_analyzer.prompt")

    # Build prompt template
    # Input variables: pending_interrupts, user_message
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", prompt_text),
        ("human", """**Pending Operations:**
{pending_operations_formatted}

**User Message:**
{user_message}

Analyze the user's response and return BatchApprovalResponse with exactly {interrupt_count} responses (one per operation)."""),
    ])

    # Build chain with preprocessing
    def format_input(inputs: dict[str, Any]) -> dict[str, Any]:
        """Format inputs for prompt template - extract OperationIntent only."""
        pending_interrupts = inputs["pending_interrupts"]
        user_message = inputs.get("user_message", "")

        # Format operations - extract only the OperationIntent from tool_args
        # For execute_database_operation, tool_args contains the full OperationIntent
        import json
        operation_lines = []
        for idx, interrupt in enumerate(pending_interrupts, 1):
            tool_name = interrupt.get('tool_name', 'unknown')
            tool_args = interrupt.get('tool_args', {})

            # Extract just the intent structure
            # For execute_database_operation, this is the OperationIntent
            # For other tools, just show the relevant args
            if tool_name == "execute_database_operation":
                # Extract the OperationIntent fields we care about
                intent = {
                    "intent_type": tool_args.get("intent_type"),
                    "user_request_summary": tool_args.get("user_request_summary"),
                    "change_spec": tool_args.get("change_spec"),
                    "impact_analysis": tool_args.get("impact_analysis"),
                }
            else:
                # For other tools, show all args
                intent = tool_args

            # Use json.dumps for safe formatting (escapes braces)
            intent_str = json.dumps(intent, ensure_ascii=False, indent=2)
            operation_lines.append(
                f"{idx}. {tool_name}:\n{intent_str}"
            )

        formatted = {
            "pending_operations_formatted": "\n\n".join(operation_lines),
            "user_message": user_message,
            "interrupt_count": len(pending_interrupts),
        }

        return formatted

    # Chain: input → format → prompt → structured LLM → BatchApprovalResponse
    chain = format_input | prompt_template | structured_llm

    logger.info("Approval analyzer created with structured output")

    return chain


def analyze_approval(
    pending_interrupts: list[InterruptInfo],
    user_message: str,
    conversation_history: list[Any] | None = None,  # Deprecated, kept for backwards compatibility
    llm: BaseChatModel | None = None,
    run_id: str | None = None,
) -> BatchApprovalResponse:
    """Convenience function to analyze approval with validation.

    Extracts only the OperationIntent from interrupts and passes user message exactly.
    No conversation history used - clean approval analysis based solely on intent + user response.

    Args:
        pending_interrupts: List of InterruptInfo objects (OperationIntent extracted from tool_args)
        user_message: User's exact approval/rejection message
        conversation_history: DEPRECATED - No longer used, kept for backwards compatibility
        llm: Optional LLM override
        run_id: Optional run_id to use as trace_id in LangSmith

    Returns:
        BatchApprovalResponse with validated count

    Raises:
        ValueError: If response count doesn't match interrupt count
    """
    # Convert InterruptInfo objects to dicts for LLM prompt
    interrupts_as_dicts = [interrupt.to_dict() for interrupt in pending_interrupts]

    analyzer = create_approval_analyzer(llm)

    # Build config with run_id if provided
    config = {}
    if run_id:
        from uuid import UUID
        config["run_id"] = UUID(run_id) if isinstance(run_id, str) else run_id

    # Invoke analyzer with OperationIntent + user message only
    try:
        result: BatchApprovalResponse = analyzer.invoke(
            {
                "pending_interrupts": interrupts_as_dicts,
                "user_message": user_message,
            },
            config=config if config else None,
        )
    except Exception as e:
        logger.error(
            "Approval analyzer returned malformed output",
            extra={
                "error": str(e),
                "interrupt_count": len(pending_interrupts),
                "user_message": user_message[:100],
            }
        )
        raise ValueError(
            f"Approval analyzer failed to return valid BatchApprovalResponse: {e}"
        ) from e

    # Validate count
    try:
        result.validate_count(len(pending_interrupts))
    except ValueError as e:
        logger.error(
            "Approval response count mismatch",
            extra={
                "expected_count": len(pending_interrupts),
                "actual_count": len(result.responses),
                "reasoning": result.reasoning,
            }
        )
        raise ValueError(
            f"Approval analyzer returned wrong number of responses: "
            f"expected {len(pending_interrupts)}, got {len(result.responses)}"
        ) from e

    logger.info(
        "Approval analysis complete",
        extra={
            "interrupt_count": len(pending_interrupts),
            "response_count": len(result.responses),
            "reasoning": result.reasoning,
        }
    )

    return result
