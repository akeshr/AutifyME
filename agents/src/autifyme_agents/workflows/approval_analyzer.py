"""Approval analyzer for HITL batch approval interpretation.

This module provides a lightweight LLM chain that interprets user approval
responses and returns structured BatchApprovalResponse objects. It is NOT
a full agent - just a prompt + LLM + structured output.

Architecture:
- Input: pending_interrupts + user_message + conversation_history
- Processing: LLM analyzes intent with structured output schema
- Output: BatchApprovalResponse (Pydantic model)

Key Design:
- Uses conversation history to understand context and resolve ambiguous references
- Full tool_args provided for complete context
- LLM interprets approval intent based on full context

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
from autifyme_agents.workflows.message_utils import extract_text_content

logger = logging.getLogger(__name__)


def create_approval_analyzer(llm: BaseChatModel | None = None) -> Any:
    """Create approval analyzer chain with structured output.

    This creates a lightweight LLM chain (NOT a full agent) that:
    1. Takes pending interrupts + user message + conversation history as input
    2. Interprets user intent using LLM reasoning with full context
    3. Returns BatchApprovalResponse (structured Pydantic model)

    No state, no tools, no delegation - pure analysis function with conversation context.

    Args:
        llm: Optional LLM override. If None, uses default gemini-2.5-flash-lite with low temperature
             for deterministic approval interpretation.

    Returns:
        LangChain chain configured for structured output:
        Input: {"pending_interrupts": list[dict], "user_message": str, "conversation_history": list}
        Output: BatchApprovalResponse

    Example:
        >>> analyzer = create_approval_analyzer()
        >>> result = analyzer.invoke({
        ...     "pending_interrupts": [
        ...         {"interrupt_id": "1", "tool_name": "execute_database_operation", "tool_args": {...}},
        ...     ],
        ...     "user_message": "approve",
        ...     "conversation_history": [...]
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
        method="function_calling",  # More flexible than strict JSON schema
    )

    # Load prompt template
    prompt_text = load_prompt("approval_analyzer.prompt")

    # Build prompt template
    # Input variables: pending_interrupts, user_message, has_media, conversation_history
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_text),
            (
                "human",
                """**Conversation History:**
{conversation_history_formatted}

**Pending Interrupts:**
{pending_interrupts_formatted}

**Has Media Attachment:** {has_media}

**Current User Message:**
{user_message}

Use the conversation history to understand context and resolve references (e.g., "the cheaper one", "same description", "make it 25").
If has_media is True and user message contains product details (not explicit approval), treat as NEW INFORMATION (reject to pass to specialist).
Analyze the user's response and return BatchApprovalResponse with exactly {interrupt_count} responses (one per interrupt).""",
            ),
        ]
    )

    # Build chain with preprocessing
    def format_input(inputs: dict[str, Any]) -> dict[str, Any]:
        """Format inputs for prompt template."""
        pending_interrupts = inputs["pending_interrupts"]
        user_message = inputs.get("user_message", "")
        has_media = inputs.get("has_media", False)
        conversation_history = inputs.get("conversation_history", [])

        # Format interrupts for display - show only high-level summary
        # Approval analyzer should see what user saw, not backend OperationIntent details
        interrupt_lines = []
        for idx, interrupt in enumerate(pending_interrupts, 1):
            tool_name = interrupt.get("tool_name", "unknown")
            tool_args = interrupt.get("tool_args", {})

            # Extract human-readable summary (what user actually saw in approval message)
            if tool_name == "execute_database_operation":
                # Show operation type + summary (matches approval message format)
                intent_type = tool_args.get("intent_type", "unknown").upper()
                summary = tool_args.get("user_request_summary", "Database operation")
                interrupt_lines.append(f"{idx}. {intent_type}: {summary}")
            else:
                # For other tools, show formatted tool name
                formatted_name = tool_name.replace("_", " ").title()
                interrupt_lines.append(f"{idx}. {formatted_name}")

        # Result: "1. CREATE: Add 500ml PET jar" instead of "1. Tool: execute_database_operation, Args: {change_spec: {...}, entity_references: {...}}"

        # Format conversation history for context
        # LIMIT to recent messages to prevent context bleeding (applying old edits)
        history_lines = []
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                msg_type = getattr(msg, "type", None)
                if not msg_type and hasattr(msg, "__class__"):
                    msg_type = msg.__class__.__name__.replace("Message", "").lower()

                # Ensure msg_type is not None
                if msg_type is None:
                    msg_type = "unknown"

                # Extract text content (handles both OpenAI string and Gemini list formats)
                raw_content = getattr(msg, "content", None)
                text_content = extract_text_content(raw_content) if raw_content else None

                if text_content and len(text_content) > 0:
                    # Truncate long messages (500 chars to preserve context for references)
                    preview = (
                        text_content[:500] + "..." if len(text_content) > 500 else text_content
                    )
                    history_lines.append(f"[{msg_type.upper()}]: {preview}")

        formatted = {
            "conversation_history_formatted": (
                "\n".join(history_lines) if history_lines else "(No prior conversation)"
            ),
            "pending_interrupts_formatted": "\n".join(interrupt_lines),
            "has_media": "True" if has_media else "False",
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
    conversation_history: list[Any] | None = None,
    has_media: bool = False,
    llm: BaseChatModel | None = None,
    run_id: str | None = None,
) -> BatchApprovalResponse:
    """Convenience function to analyze approval with validation.

    Args:
        pending_interrupts: List of InterruptInfo objects
        user_message: User's approval/rejection message
        conversation_history: Full conversation history for context (helps resolve ambiguous references)
        has_media: Whether user attached media (image) with their response
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

    # Invoke analyzer with conversation history for context
    try:
        result: BatchApprovalResponse = analyzer.invoke(
            {
                "pending_interrupts": interrupts_as_dicts,
                "user_message": user_message,
                "has_media": has_media,
                "conversation_history": conversation_history or [],
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
            },
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
            },
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
            "has_conversation_history": len(conversation_history or []) > 0,
            "reasoning": result.reasoning,
        },
    )

    return result
