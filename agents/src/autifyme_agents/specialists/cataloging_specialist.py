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

    # HITL is configured at PM level, not specialist level
    # PM's HITL middleware will intercept save_product calls from this specialist
    return {
        "name": "cataloging_specialist",
        "description": description,
        "tools": [image_analysis_tool, save_product],
        "system_prompt": system_prompt,
    }
