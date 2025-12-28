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

from typing import TYPE_CHECKING, Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.middleware import (
    MultimodalInjectionMiddleware,
    create_execution_limits,
)
from autifyme_agents.tools import create_view_image_tool
from autifyme_agents.tools.protocol_loader import create_load_protocol_tool

if TYPE_CHECKING:
    from autifyme_agents.schemas.models import CompanyProfile

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
    company_profile: "CompanyProfile",
    model: str | BaseChatModel | None = None,
) -> dict[str, Any]:
    """Create Catalog Specialist SubAgent spec.

    Args:
        storage: Storage interface for catalog operations
        company_profile: Company context for prompt formatting (currency, SKU naming, etc.)
        model: Optional LLM (string or instance). None uses PM's default.

    Returns:
        SubAgent spec dict: {name, description, tools, system_prompt, interrupt_on, model}
    """
    if storage is None:
        raise ValueError("storage is required for Catalog Specialist")
    if company_profile is None:
        raise ValueError("company_profile is required for Catalog Specialist (single-tenant)")

    # Load and format prompt with company context
    prompt_template = load_prompt("specialists/catalog_specialist.prompt")
    sku_conv = company_profile.sku_naming_convention

    system_prompt = prompt_template.format(
        company_name=company_profile.name,
        currency_symbol=company_profile.currency_symbol,
        default_currency=company_profile.default_currency,
        price_positioning=company_profile.price_positioning,
        business_models=", ".join(company_profile.business_models) if company_profile.business_models else "B2B",
        target_markets=", ".join(company_profile.target_markets) if company_profile.target_markets else "India",
        sku_prefix=sku_conv.prefix if sku_conv else "SKU",
        sku_separator=sku_conv.separator if sku_conv else "-",
        sku_uppercase=str(sku_conv.uppercase) if sku_conv else "True",
        sku_examples=", ".join(sku_conv.examples[:3]) if sku_conv and sku_conv.examples else "SKU-001",
        default_price_list_id=company_profile.default_price_list_id or "Query from price_lists",
    )

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
        *create_execution_limits(limit=60),
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
