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
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

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
) -> callable:
    """Create message intent specialist with platform tools.

    Args:
        platform_tools: Platform-specific tools (e.g., download_whatsapp_media)
        model: Optional LLM override (defaults to fast model for efficiency)

    Returns:
        Callable that interprets raw messages into structured MessageInterpretation
    """
    llm = model or get_llm(model="gpt-4o-mini", temperature=0.1)

    # Bind structured output for type-safe responses
    llm_with_structure = llm.with_structured_output(MessageInterpretation)

    # Bind platform tools for media downloading
    llm_with_tools = llm_with_structure.bind_tools(platform_tools)

    def interpret_message(
        raw_message: str | dict,
        config: RunnableConfig | None = None,
    ) -> MessageInterpretation:
        """Interpret raw platform message in conversational context.

        Args:
            raw_message: JSON string or dict of RawPlatformMessage
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

        # Load specialist prompt
        system_prompt = load_prompt("specialists/message_intent_specialist.prompt")

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

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        # Invoke with conversation history from PM
        # PM passes history via config, specialist has full context
        result = llm_with_tools.invoke(messages, config=config)

        logger.info(
            "Message intent interpreted",
            extra={
                "intent": result.intent,
                "has_media": result.has_media,
                "reasoning": result.reasoning[:100],
            }
        )

        return result

    return interpret_message
