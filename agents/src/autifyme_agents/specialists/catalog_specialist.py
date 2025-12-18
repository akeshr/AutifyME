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

Protocol Integration (v2):
- Loads domain protocols at task start (business_context, family_fit, pricing, etc.)
- Protocol-driven decision making with structured reasoning
- Protocols ground specialist in validated domain patterns
"""

from typing import Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.middleware import (
    MultimodalInjectionMiddleware,
    create_execution_limits,
)
from autifyme_agents.tools import create_view_image_tool
from autifyme_agents.tools.protocol_loader import create_load_protocol_tool

# NOTE: Research tools removed - product_analyst handles all external research
# catalog_specialist focuses on catalog CRUD operations only

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
    "categories",  # Product taxonomy hierarchy
    # DAM (Digital Asset Management)
    "assets",
    "product_assets",
    "asset_composition_rules",
    "product_images",
    # Pricing
    "price_lists",
    "product_prices",
    "customer_prices",  # Customer-specific pricing
    # Manufacturing (BOM)
    "bom",
    "bom_lines",
    # Product UOM
    "product_uom_conversion",
]

CATALOG_TABLES_READ_ONLY = [
    "uom",
    "uom_conversion",
    "industries",  # NAICS classification (read-only reference)
    "companies",  # Single-tenant company info
    "company_intelligence",  # Auto-discovered brand intel
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

    system_prompt = load_prompt("specialists/catalog_specialist_v2.prompt")

    # Tools - load_protocol first for protocol-driven reasoning
    # NOTE: No research tools - product_analyst handles external research
    tools: list[Any] = [
        create_load_protocol_tool(),
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
        "ROLE: Specialist (execution, protocol-integrated)\n"
        "MISSION: Safely mutate the product catalog with protocol-driven CRUD and HITL approval.\n\n"
        "OWNERSHIP:\n"
        "- Product families, products/SKUs, variants, taxonomy links, pricing, BOM\n"
        "- Asset metadata + links between assets and products (not image editing)\n"
        "- Protocol-driven decisions (family_fit, pricing, duplicate_prevention)\n\n"
        "INPUTS I NEED:\n"
        "- Target intent (create/update/delete) and business goal\n"
        "- IDs when possible (or enough attributes to look them up)\n"
        "- Any processed image storage_path(s) in pending/... when linking assets\n"
        "- External research findings from product_analyst (if needed)\n\n"
        "OUTPUTS I PRODUCE:\n"
        "- Protocol-grounded write plan with structured reasoning\n"
        "- After approval: executed write_data results + created/updated IDs\n"
        "- On rejection: revised write_data intent based on user feedback\n\n"
        "TOOLS I USE:\n"
        "- load_protocol (FIRST - loads business_context, family_fit, pricing, etc.)\n"
        "- inspect_schema, read_data, aggregate_data, write_data (HITL), view_image\n"
        "- NO research tools - product_analyst handles external research\n\n"
        "GUARDRAILS:\n"
        "- Protocol steps are MANDATORY (e.g., family_fit requires customer_segments query)\n"
        "- No image processing (delegate to creative_specialist); no ad-hoc SQL; always read-before-write"
    )

    # Multimodal middleware injects images from paths in delegation message
    # When PM includes image paths in the task description, the middleware
    # loads and injects the images so the specialist's LLM can see them
    middleware = [
        *create_execution_limits(
            model_call_limit=15,
            tool_limits={
                "load_protocol": 10,
                "write_data": 10,
                "read_data": 10,
                "aggregate_data": 10,
                "inspect_schema": 10,
                "view_image": 10,
            },
        ),
        MultimodalInjectionMiddleware(),
    ]

    spec: dict[str, Any] = {
        "name": "catalog_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        "middleware": middleware,
        # FilesystemMiddleware (read_file for workspace) is provided by default via DeepAgents
        "interrupt_on": {"write_data": True},
    }

    if model is not None:
        spec["model"] = model

    return spec
