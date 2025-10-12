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
    llm = model or get_llm(model="gpt-4o-mini", temperature=0.1)
    system_prompt = load_prompt("specialists/message_intent_specialist.prompt")

    # ✅ Use create_agent with response_format for structured output + tools
    agent = create_agent(
        model=llm,
        tools=platform_tools,  # Platform-specific media download tools
        system_prompt=system_prompt,
        response_format=MessageInterpretation,  # ✅ Structured output
        name="MessageIntentSpecialist",
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
    user_input = f"""Raw Platform Message:
Platform: {parsed_message.platform}
Sender: {parsed_message.sender}
Text: {parsed_message.text or "[no text]"}
Media ID: {parsed_message.media_id or "[no media]"}
Timestamp: {parsed_message.timestamp}

Instructions:
1. Review the conversation history above to understand current context
2. Check if there's a pending approval request (look for product drafts awaiting user confirmation)
3. If media_id is present, call download_{parsed_message.platform}_media to get the local path
4. Interpret the user's intent based on their message + conversation context
5. Return structured MessageInterpretation with your reasoning

Remember:
- If you see a recent approval request and user responds with affirmation → approval_response
- If user sends new media during pending approval → workflow_abandonment
- If user asks about pending draft details → clarification_request
- If no context and user provides product info → new_cataloging_request
"""

    messages = [{"role": "human", "content": user_input}]

    # Invoke agent with conversation history from PM
    result = agent.invoke({"messages": messages}, config=config or {})

    # Extract structured response (MessageInterpretation model)
    interpretation = result["response"]  # create_agent with response_format returns {"response": MessageInterpretation}

    logger.info(
        "Message intent interpreted",
        extra={
            "intent": interpretation.intent,
            "has_media": interpretation.has_media,
            "reasoning": interpretation.reasoning[:100],
        }
    )

    return interpretation
