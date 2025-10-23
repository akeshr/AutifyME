"""Cataloging specialist - synthesizes product information into catalog entries.

Factory function returns SubAgent spec for PM's subagents list.
"""

from typing import Any

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool


def create_cataloging_specialist(storage: StorageInterface) -> dict[str, Any]:
    """Create cataloging specialist SubAgent spec.

    Args:
        storage: Storage adapter for database operations (not used - kept for interface compatibility)

    Returns:
        SubAgent spec with image analysis tool only.
        save_product moved to PM level to avoid HITL re-invocation issues.
    """
    system_prompt = load_prompt("specialists/cataloging_specialist.prompt")

    description = (
        "Analyzes product images and synthesizes product information. "
        "Extracts visual details (colors, materials, style, quality) and returns "
        "structured product data. PM handles saving to database with approval."
    )

    return {
        "name": "cataloging_specialist",
        "description": description,
        "tools": [image_analysis_tool],  # Only analysis tool, no save_product
        "system_prompt": system_prompt,
        # No interrupt_on - specialist has no HITL tools
    }
