"""Message Intent Specialist - Interprets raw platform messages in context.

This specialist enables truly agentic message interpretation by understanding
user intent based on conversation history, pending workflows, and platform context.

Architecture:
- PM calls this specialist with raw platform messages
- Specialist analyzes conversation history for context (pending approvals, etc.)
- Can download media via platform-specific tools
- Returns structured MessageInterpretation for PM to route appropriately
"""

from __future__ import annotations

import json
import logging
from typing import Any, TYPE_CHECKING

from langchain.agents import create_agent
from langgraph.errors import GraphRecursionError

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.schemas.message_intent import MessageInterpretation, RawPlatformMessage

if TYPE_CHECKING:
    from langchain.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


def create_message_intent_specialist(
    *,
    platform_tools: list,
    model: BaseChatModel | None = None,
) -> Any:
    """Create message intent specialist with platform tools using create_agent.

    Uses create_agent for:
    - LangSmith observability (traced as agent)
    - Structured outputs (response_format)
    - Tool calling (platform media download)
    - Architectural consistency (agents all the way down)

    Args:
        platform_tools: Platform-specific tools (e.g., download_whatsapp_media)
        model: Optional LLM override (defaults to fast model for efficiency)

    Returns:
        Agent that interprets raw messages into structured MessageInterpretation
    """
    # Use OpenAI native structured outputs (response_format with Pydantic model)
    # This enforces the schema at API level - LLM MUST return exact structure
    # Works alongside regular tools (no ToolStrategy workaround needed)
    llm = model or get_llm(model="gpt-4.1-mini-2025-04-14", temperature=0.1)
    system_prompt = load_prompt("specialists/message_intent_specialist.prompt")

    # ✅ Native structured outputs: LLM forced to return MessageInterpretation schema
    agent = create_agent(
        model=llm,
        tools=platform_tools,  # Platform-specific media download tools
        system_prompt=system_prompt,
        name="MessageIntentSpecialist",
        response_format=MessageInterpretation,  # Direct Pydantic model - OpenAI native structured outputs
    )

    return agent


def message_intent_specialist_invoke(
    raw_message: str | dict,
    agent: Any,
    config: dict[str, Any] | None = None,
) -> MessageInterpretation:
    """Invoke message intent specialist agent with raw platform message.

    This maintains compatibility with tool wrapper while using agent-based
    implementation underneath.

    Args:
        raw_message: JSON string or dict of RawPlatformMessage
        agent: Pre-created agent from create_message_intent_specialist
        config: Runnable config (provides conversation history via PM context)

    Returns:
        Structured interpretation of user intent
    """
    # Parse raw message
    if isinstance(raw_message, str):
        try:
            message_data = json.loads(raw_message)
        except json.JSONDecodeError:
            # Treat as plain text if not JSON
            message_data = {"text": raw_message, "platform": "unknown"}
    else:
        message_data = raw_message

    # Validate with Pydantic
    try:
        parsed_message = RawPlatformMessage.model_validate(message_data)
    except Exception as e:
        logger.warning(
            "Failed to parse raw message, using fallback",
            extra={"error": str(e), "raw": message_data}
        )
        # Fallback for malformed messages
        return MessageInterpretation(
            intent="off_topic",
            reasoning=f"Could not parse message format: {e}",
            platform=message_data.get("platform", "unknown"),
            raw_text=message_data.get("text"),
            has_media=False,
        )

    # Build input for specialist
    user_input = f"""**Raw Platform Message**:
- Platform: {parsed_message.platform}
- Sender: {parsed_message.sender}
- Text: {parsed_message.text or "[no text]"}
- Media ID: {parsed_message.media_id or "[no media]"}
- Timestamp: {parsed_message.timestamp}

**Your Task**:
1. **Review conversation history above** - Look for pending interrupts, previous AI responses, workflow context
2. **Download media if present**: If media_id provided, call `download_{parsed_message.platform}_media(media_id)` to get local path
3. **Interpret user intent** based on message + full conversation context
4. **Construct Commands if resuming** - Build exact resume_value structure for pending interrupts
5. **Return structured interpretation** with clear reasoning

**Key Reminders**:
- If there's a pending interrupt and user wants to proceed → intent="resume_workflow" with command field
- Extract interrupt_id from conversation context (NOT from user message)
- Construct resume_value based on interrupt structure and user response
- For clarifications, compose response in clarification_response field
- Always explain your reasoning for observability
"""

    messages = [{"role": "human", "content": user_input}]

    try:
        # Invoke agent with conversation history from PM (via config)
        # Set reasonable recursion limit for specialist:
        # - Download media (if present): 1 step
        # - Generate structured output: 1-2 steps
        # - With explicit schema in prompt, should not loop on validation
        specialist_config = (config or {}).copy()
        specialist_config["recursion_limit"] = 5  # Reasonable limit with explicit schema guidance

        result = agent.invoke({"messages": messages}, config=specialist_config)

        # Extract structured response
        interpretation = result["structured_response"]

    except GraphRecursionError as e:
        logger.warning(
            "Message intent specialist hit recursion limit - likely looping. Using fallback interpretation.",
            extra={"error": str(e), "raw_message": str(message_data)[:200]}
        )
        # Fallback: Assume new cataloging request if message has content
        text = parsed_message.text or ""
        has_catalog_keywords = any(word in text.lower() for word in ["catalog", "add", "new", "product", "item", "price"])

        if has_catalog_keywords or parsed_message.media_id:
            return MessageInterpretation(
                intent="new_request",
                reasoning="Specialist recursion limit reached. Defaulting to cataloging request based on keywords/media presence.",
                request_data={"product_text": text} if text else {},
                platform=parsed_message.platform,
                raw_text=parsed_message.text,
                has_media=parsed_message.media_id is not None,
            )
        else:
            return MessageInterpretation(
                intent="clarification",
                reasoning="Specialist recursion limit reached. Asking for clarification.",
                clarification_response="I'm having trouble processing your message. Could you please provide more details about what you'd like to catalog?",
                platform=parsed_message.platform,
                raw_text=parsed_message.text,
                has_media=False,
            )

    except Exception as e:
        logger.exception(
            "Specialist invocation failed",
            extra={"error": str(e), "raw_message": str(message_data)[:200]}
        )
        # Robust fallback
        return MessageInterpretation(
            intent="error",
            reasoning=f"Specialist failed to interpret message: {str(e)}. Asking user for clarification.",
            clarification_response="I'm having trouble understanding. Could you please rephrase?",
            platform=parsed_message.platform,
            raw_text=parsed_message.text,
            has_media=parsed_message.media_id is not None,
        )

    logger.info(
        "Message intent interpreted",
        extra={
            "intent": interpretation.intent,
            "has_media": interpretation.has_media,
            "reasoning": interpretation.reasoning[:100],
        }
    )

    return interpretation
