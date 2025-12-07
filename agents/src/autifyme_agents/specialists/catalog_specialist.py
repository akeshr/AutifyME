"""
Catalog Specialist - Domain expert for product catalog operations.

Domain Ownership ("What We Sell"):
- PIM: product families, variants, SKUs
- DAM: assets (metadata/records), product-asset links
- Pricing: price lists, product prices
- Manufacturing: BOM, component lines
- Master Data: UOM (read-only)

Architecture:
- SubAgent spec dict for PM delegation
- Schema-driven CRUD with HITL approval
- Autonomous research and enrichment
- Does NOT process images (Creative Specialist does that)
"""

from typing import Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools import create_view_image_tool
from autifyme_agents.tools.research_tools import (
    extract_web_content_tool,
    research_product_tool,
)

# =============================================================================
# Domain Table Configuration
# =============================================================================

CATALOG_TABLES_CRUD = [
    # PIM (Product Information Management)
    "product_families",
    "products",
    "variant_axes",
    "variant_values",
    "product_variant_values",
    "product_family_industries",
    "customer_segments",
    # DAM (Digital Asset Management)
    "assets",
    "product_assets",
    "asset_composition_rules",
    "product_images",
    # Pricing
    "price_lists",
    "product_prices",
    # Manufacturing (BOM)
    "bom",
    "bom_lines",
    # Product UOM
    "product_uom_conversion",
]

CATALOG_TABLES_READ_ONLY = [
    "uom",
    "uom_conversion",
]

CATALOG_TABLES_ALL = CATALOG_TABLES_CRUD + CATALOG_TABLES_READ_ONLY


# =============================================================================
# Specialist Factory
# =============================================================================


def create_catalog_specialist(
    storage: StorageInterface,
    model: str | BaseChatModel | None = None,
) -> dict[str, Any]:
    """Create Catalog Specialist SubAgent spec.

    Args:
        storage: Storage interface for catalog operations
        model: Optional LLM (string or instance). None uses PM's default.

    Returns:
        SubAgent spec dict: {name, description, tools, system_prompt, interrupt_on, model}
    """
    if storage is None:
        raise ValueError("storage is required for Catalog Specialist")

    system_prompt = load_prompt("specialists/catalog_specialist.prompt")

    # Tools
    tools: list[Any] = [
        research_product_tool,
        extract_web_content_tool,
    ]

    from autifyme_agents.tools.data_engine import (
        create_aggregate_data_tool,
        create_inspect_schema_tool,
        create_read_data_tool,
        create_write_data_tool,
    )

    tools.append(create_inspect_schema_tool(storage, tables=CATALOG_TABLES_ALL))
    tools.append(create_read_data_tool(storage, tables=CATALOG_TABLES_ALL))
    tools.append(create_aggregate_data_tool(storage, tables=CATALOG_TABLES_ALL))
    tools.append(create_write_data_tool(storage, tables=CATALOG_TABLES_CRUD))

    # Image viewing - verify processed images before creating asset records
    tools.append(create_view_image_tool())

    description = (
        "Catalog Specialist - domain expert for product catalog operations. "
        "Handles: products, families, variants, pricing, asset records, BOM. "
        "Capabilities: schema-driven CRUD, web research, duplicate detection, "
        "multi-table atomic transactions. Receives processed images from "
        "Creative Specialist. Does NOT process images directly."
    )

    spec: dict[str, Any] = {
        "name": "catalog_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        # FilesystemMiddleware (read_file for workspace) is provided by default via DeepAgents
        "interrupt_on": {"write_data": True},
    }

    if model is not None:
        spec["model"] = model

    return spec
