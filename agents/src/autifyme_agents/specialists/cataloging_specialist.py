"""Cataloging specialist - synthesizes product information into catalog entries.

Factory function returns SubAgent spec for PM's subagents list.
"""

from typing import Any

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.data_engine_tools import (
    create_inspect_schema_tool,
    create_read_data_tool,
)
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool


def create_cataloging_specialist(storage: StorageInterface) -> dict[str, Any]:
    """Create cataloging specialist SubAgent spec.

    Args:
        storage: Storage adapter for database operations

    Returns:
        SubAgent spec with image analysis + schema inspection + read access.
        Specialist can check for duplicates and understand product structure.
        PM handles write operations with approval.
    """
    system_prompt = load_prompt("specialists/cataloging_specialist.prompt")

    description = (
        "Analyzes product images, checks for existing products, and synthesizes catalog data. "
        "Has read access to product tables for duplicate detection and schema understanding. "
        "Returns structured product data to PM for saving with user approval."
    )

    # Product-related tables only (scoped access)
    product_tables = [
        "product_families",
        "products",
        "product_variant_values",
        "variant_axes",
        "variant_values",
        "categories",
    ]

    return {
        "name": "cataloging_specialist",
        "description": description,
        "tools": [
            image_analysis_tool,
            create_inspect_schema_tool(storage, tables=product_tables),
            create_read_data_tool(storage, tables=product_tables),
        ],
        "system_prompt": system_prompt,
        # No interrupt_on - specialist has no HITL tools (read-only)
    }
