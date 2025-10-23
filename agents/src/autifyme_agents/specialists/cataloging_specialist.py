"""Cataloging specialist - synthesizes product information into catalog entries.

Factory function returns SubAgent spec for PM's subagents list.
"""

from typing import Any

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool
from autifyme_agents.tools.storage_tools import create_save_product_tool


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

    # CRITICAL: NO interrupt_on at specialist level
    # HITL must be configured at PM level for proper Command.resume routing
    # When interrupt_on is at specialist level, PM can't route resume correctly
    return {
        "name": "cataloging_specialist",
        "description": description,
        "tools": [image_analysis_tool, save_product],
        "system_prompt": system_prompt,
        # NO interrupt_on here - PM handles HITL for all subagent tools
    }
