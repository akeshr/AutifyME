"""Message Intent Tool for PM to interpret raw platform messages.

This tool wraps the MessageIntentSpecialist as a PM tool, enabling the PM
to understand user intent based on conversation history and platform context.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from langchain_core.tools import tool

from autifyme_agents.specialists.message_intent_specialist import create_message_intent_specialist
from autifyme_agents.schemas.message_intent import MessageInterpretation

if TYPE_CHECKING:
    from autifyme_agents.workflows.channels.protocol import MessagingChannel

logger = logging.getLogger(__name__)


def create_message_intent_tool(
    channel: MessagingChannel,
    platform_tools: list,
) -> callable:
    """Create message intent interpretation tool for PM.

    Args:
        channel: Messaging channel for context
        platform_tools: Platform-specific tools (media download, etc.)

    Returns:
        LangChain tool that PM can invoke to interpret raw messages
    """
    # Create the specialist with platform tools
    specialist = create_message_intent_specialist(platform_tools=platform_tools)

    @tool
    def interpret_incoming_message(raw_message: str) -> dict[str, Any]:
        """Interpret raw platform message in conversational context.

        Use this tool FIRST when receiving a new message from the user.
        It analyzes the message content, conversation history, and current
        workflow state to determine user intent.

        Args:
            raw_message: JSON string containing platform message with fields:
                - platform: Source platform (whatsapp, telegram, etc.)
                - sender: User identifier
                - text: Message text (optional)
                - media_id: Media attachment ID (optional)
                - timestamp: ISO timestamp

        Returns:
            Structured interpretation with fields:
                - intent: User's intent (new_cataloging_request, approval_response, etc.)
                - reasoning: Explanation of the interpretation
                - Additional fields based on intent (approval_decision, media, etc.)

        Examples:
            >>> interpret_incoming_message('{"platform": "whatsapp", "text": "approved", ...}')
            {"intent": "approval_response", "approval_decision": "approve", ...}

            >>> interpret_incoming_message('{"text": "catalog this jar", "media_id": "xyz", ...}')
            {"intent": "new_cataloging_request", "media": [...], ...}
        """
        try:
            logger.info("PM invoking MessageIntentSpecialist", extra={"raw_message": raw_message[:100]})

            # Specialist has access to conversation history via config
            interpretation = specialist(raw_message)

            # Convert Pydantic model to dict for tool output
            result = interpretation.model_dump(mode="json")

            logger.info(
                "Message interpretation complete",
                extra={
                    "intent": result["intent"],
                    "has_media": result.get("has_media", False),
                }
            )

            return result

        except Exception as e:
            logger.exception("Failed to interpret message", extra={"error": str(e)})
            # Return safe fallback
            return {
                "intent": "off_topic",
                "reasoning": f"Failed to interpret message: {e}",
                "platform": "unknown",
                "raw_text": raw_message,
                "has_media": False,
            }

    return interpret_incoming_message
