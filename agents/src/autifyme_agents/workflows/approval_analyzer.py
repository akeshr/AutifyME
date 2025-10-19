"""Approval analyzer for HITL batch approval interpretation.

This module provides a lightweight LLM chain that interprets user approval
responses and returns structured BatchApprovalResponse objects. It is NOT
a full agent - just a prompt + LLM + structured output.

Architecture:
- Input: pending_interrupts + user_message
- Processing: LLM analyzes intent with structured output schema
- Output: BatchApprovalResponse (Pydantic model)

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

logger = logging.getLogger(__name__)


def create_approval_analyzer(llm: BaseChatModel | None = None) -> Any:
    """Create approval analyzer chain with structured output.

    This creates a lightweight LLM chain (NOT a full agent) that:
    1. Takes pending interrupts + user message as input
    2. Interprets user intent using LLM reasoning
    3. Returns BatchApprovalResponse (structured Pydantic model)

    No state, no tools, no delegation - pure analysis function.

    Args:
        llm: Optional LLM override. If None, uses default gpt-4.1-mini with low temperature
             for deterministic approval interpretation.

    Returns:
        LangChain chain configured for structured output:
        Input: {"pending_interrupts": list[InterruptContext], "user_message": str}
        Output: BatchApprovalResponse

    Example:
        >>> analyzer = create_approval_analyzer()
        >>> result = analyzer.invoke({
        ...     "pending_interrupts": [
        ...         {"interrupt_id": "1", "tool_name": "save_product", "tool_args": {...}},
        ...         {"interrupt_id": "2", "tool_name": "save_product", "tool_args": {...}},
        ...     ],
        ...     "user_message": "approve both"
        ... })
        >>> assert isinstance(result, BatchApprovalResponse)
        >>> assert len(result.responses) == 2
    """
    if llm is None:
        # Use gpt-4.1-mini with low temperature for deterministic approval interpretation
        llm = get_llm(model="gpt-4.1-mini-2025-04-14", temperature=0.2)

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
    # Input variables: pending_interrupts, user_message, conversation_history
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", prompt_text),
        ("human", """**Conversation History:**
{conversation_history_formatted}

**Pending Interrupts:**
{pending_interrupts_formatted}

**Current User Message:**
{user_message}

Use the conversation history to understand context and resolve references (e.g., "the cheaper one", "same description", "make it 25").
Analyze the user's response and return BatchApprovalResponse with exactly {interrupt_count} responses (one per interrupt)."""),
    ])

    # Build chain with preprocessing
    def format_input(inputs: dict[str, Any]) -> dict[str, Any]:
        """Format inputs for prompt template."""
        pending_interrupts = inputs["pending_interrupts"]
        user_message = inputs.get("user_message", "")
        conversation_history = inputs.get("conversation_history", [])

        # Format interrupts for display
        interrupt_lines = []
        for idx, interrupt in enumerate(pending_interrupts, 1):
            interrupt_lines.append(
                f"{idx}. Tool: {interrupt.get('tool_name', 'unknown')}, "
                f"Args: {interrupt.get('tool_args', {})}"
            )

        # Format conversation history for context
        history_lines = []
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                msg_type = getattr(msg, 'type', None)
                if not msg_type and hasattr(msg, '__class__'):
                    msg_type = msg.__class__.__name__.replace('Message', '').lower()

                # Ensure msg_type is not None
                if msg_type is None:
                    msg_type = 'unknown'

                content = getattr(msg, 'content', str(msg))
                if isinstance(content, str) and len(content) > 0:
                    # Truncate long messages
                    preview = content[:200] + "..." if len(content) > 200 else content
                    history_lines.append(f"[{msg_type.upper()}]: {preview}")

        formatted = {
            "conversation_history_formatted": (
                "\n".join(history_lines) if history_lines
                else "(No prior conversation)"
            ),
            "pending_interrupts_formatted": "\n".join(interrupt_lines),
            "user_message": user_message,
            "interrupt_count": len(pending_interrupts),
        }

        return formatted

    # Chain: input → format → prompt → structured LLM → BatchApprovalResponse
    chain = format_input | prompt_template | structured_llm

    logger.info("Approval analyzer created with structured output")

    return chain


def analyze_approval(
    pending_interrupts: list[dict[str, Any]],
    user_message: str,
    conversation_history: list[Any] | None = None,
    llm: BaseChatModel | None = None,
    run_id: str | None = None,
) -> BatchApprovalResponse:
    """Convenience function to analyze approval with validation.

    Args:
        pending_interrupts: List of interrupt context dicts
        user_message: User's approval/rejection message
        conversation_history: Full conversation history for context (NEW)
        llm: Optional LLM override
        run_id: Optional run_id to use as trace_id in LangSmith

    Returns:
        BatchApprovalResponse with validated count

    Raises:
        ValueError: If response count doesn't match interrupt count
    """
    analyzer = create_approval_analyzer(llm)

    # Build config with run_id if provided
    config = {}
    if run_id:
        from uuid import UUID
        config["run_id"] = UUID(run_id) if isinstance(run_id, str) else run_id

    # Invoke analyzer with conversation history
    result: BatchApprovalResponse = analyzer.invoke(
        {
            "pending_interrupts": pending_interrupts,
            "user_message": user_message,
            "conversation_history": conversation_history or [],
        },
        config=config if config else None,
    )

    # Validate count
    result.validate_count(len(pending_interrupts))

    logger.info(
        "Approval analysis complete",
        extra={
            "interrupt_count": len(pending_interrupts),
            "response_count": len(result.responses),
            "has_conversation_history": len(conversation_history or []) > 0,
            "reasoning": result.reasoning,
        }
    )

    return result
