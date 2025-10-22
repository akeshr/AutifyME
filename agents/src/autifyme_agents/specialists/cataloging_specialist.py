"""Cataloging specialist - synthesizes product information into catalog entries.

Factory function returns SubAgent spec for PM's subagents list.
"""

from typing import Any

from langchain.agents.middleware import before_agent

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool
from autifyme_agents.tools.storage_tools import create_save_product_tool


@before_agent
def _limit_message_history(state: dict[str, Any]) -> dict[str, Any]:
    """Limit message history to prevent token bloat from PM conversation.

    Cataloging specialist only needs immediate task context (last 3-5 messages),
    not entire PM conversation history. This prevents 300K+ token costs.
    """
    messages = state.get("messages", [])
    if len(messages) > 5:
        # Keep only last 5 messages (task context)
        state["messages"] = messages[-5:]
    return state


def create_cataloging_specialist(storage: StorageInterface) -> dict[str, Any]:
    """Create cataloging specialist SubAgent spec.

    Args:
        storage: Storage adapter for database operations

    Returns:
        SubAgent spec with tools, HITL configuration, and message limiting middleware
    """
    save_product = create_save_product_tool(storage)
    system_prompt = load_prompt("specialists/cataloging_specialist.prompt")

    description = (
        "Synthesizes product information from user descriptions and image analysis. "
        "Analyzes product images, infers missing details, creates complete catalog entries "
        "with human approval before saving to database."
    )

    return {
        "name": "cataloging_specialist",
        "description": description,
        "tools": [image_analysis_tool, save_product],
        "system_prompt": system_prompt,
        "middleware": [_limit_message_history],  # Ultra-thin context
        "interrupt_on": {"save_product": True},
    }
