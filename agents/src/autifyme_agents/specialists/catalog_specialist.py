"""
Catalog Specialist - Unified domain expert for product catalog operations.

Domain Ownership ("What We Sell"):
- Product Information Management (PIM): families, variants, SKUs
- Digital Asset Management (DAM): assets, product-asset links, composition rules
- Pricing: price lists, product prices, tiered pricing
- Manufacturing: BOM, component lines
- Master Data: UOM (read-only), variant axes/values

Consolidated from 7 narrow specialists:
- Product Architecture -> product structure, families, variants
- Visual Assets -> asset management, image metadata
- Content SEO -> product descriptions (embedded in product data)
- Taxonomy -> category/industry classification (via product_family_industries)
- Pricing Logic -> price lists, tiered pricing

Responsibilities:
- Query catalog schema dynamically (inspect_schema)
- Search catalog for duplicates (read_data with search_patterns)
- Research product specs via web (research_product_tool)
- Process product images (image_studio: analyze, edit, generate via Gemini 3 Pro Image)
- Generate complete operation plans (WriteIntent)
- Execute mutations with HITL approval (write_data)
- Self-review for completeness before submission

Does NOT:
- Handle supply chain (Operations Specialist domain)
- Manage inventory/locations (Operations Specialist domain)
- Create marketing campaigns (future Marketing Specialist)

Architecture Pattern:
- SubAgent spec: Standard dict format for PM delegation
- Returns dict with {name, description, tools, system_prompt, interrupt_on, model}
- DeepAgents compiles specialist automatically in PM
- Schema-driven planning (no hard-coded operation types)
- Intelligence-first: autonomous research and enrichment
- Single HITL approval point for atomic multi-table transactions
"""

from typing import Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.image_studio import create_image_studio_tool
from autifyme_agents.tools.research_tools import (
    extract_web_content_tool,
    research_product_tool,
)

# =============================================================================
# Domain Table Configuration
# =============================================================================

# Catalog Domain Tables - Complete ownership
# Organized by sub-domain for clarity

CATALOG_TABLES_CRUD = [
    # Product Information Management (PIM)
    "product_families",           # Product family definitions
    "products",                   # Product variants (SKUs)
    "variant_axes",               # Variant dimensions (Size, Color, Material)
    "variant_values",             # Values for variant axes (500ml, 1L, Red, Blue)
    "product_variant_values",     # Junction: products <-> variant_values (M:N)
    "product_family_industries",  # Junction: product_families <-> industries
    "customer_segments",          # Target customer segments

    # Digital Asset Management (DAM)
    "assets",                     # Master asset repository
    "product_assets",             # Junction: products <-> assets
    "asset_composition_rules",    # Rules for composite assets
    "product_images",             # Legacy - kept for backward compatibility

    # Pricing
    "price_lists",                # Named price lists (MRP, Wholesale, Dealer)
    "product_prices",             # Product-specific pricing entries

    # Manufacturing (BOM)
    "bom",                        # Bill of materials headers
    "bom_lines",                  # BOM component line items

    # Product UOM (domain-specific conversions)
    "product_uom_conversion",     # Product-specific unit conversions
]

CATALOG_TABLES_READ_ONLY = [
    # Master Data (owned by Operations, read by Catalog)
    "uom",                        # Master unit of measure
    "uom_conversion",             # Master UOM conversions
]

# Combined list for tool initialization
CATALOG_TABLES_ALL = CATALOG_TABLES_CRUD + CATALOG_TABLES_READ_ONLY


# =============================================================================
# Specialist Factory
# =============================================================================


def create_catalog_specialist(
    storage: StorageInterface,
    model: str | BaseChatModel | None = None,
) -> dict[str, Any]:
    """
    Create Catalog Specialist SubAgent spec.

    Unified domain expert for all product catalog operations. Consolidates
    capabilities from 7 narrow specialists into single domain authority.

    Domain Ownership:
    - PIM: product_families, products, variants, SKUs
    - DAM: assets, product_assets, asset_composition_rules
    - Pricing: price_lists, product_prices
    - Manufacturing: bom, bom_lines
    - Master Data: uom (READ), variant axes/values

    Capabilities:
    - Schema-driven CRUD with HITL approval
    - Autonomous web research for product enrichment
    - Image Studio for visual processing (analyze, edit, generate)
    - Duplicate detection via catalog search
    - Multi-table atomic transactions
    - Self-review pattern before HITL submission

    Architecture:
    - SubAgent dict: {name, description, tools, system_prompt, interrupt_on, model}
    - DeepAgents compiles specialist with specified model or PM's default_model
    - Single HITL approval point for atomic operations
    - PM handles orchestration, specialist handles domain execution

    Args:
        storage: Storage interface for catalog operations (REQUIRED)
        model: Optional model (string or LLM instance).
               - String: "google:gemini-2.5-flash", "openai:gpt-4o"
               - LLM instance: Pre-configured BaseChatModel
               - None: Uses PM's default_model from SubAgentMiddleware

    Returns:
        SubAgent spec dict for PM's subagents list

    Example:
        ```python
        catalog_specialist = create_catalog_specialist(
            storage=storage,
            model=get_llm(provider="google", model="gemini-2.5-flash", temperature=0.3)
        )
        pm = create_deep_agent(
            subagents=[catalog_specialist],
            ...
        )
        ```
    """
    if storage is None:
        raise ValueError(
            "storage is required for Catalog Specialist (tools dependency)"
        )

    # Load specialist prompt
    system_prompt = load_prompt("specialists/catalog_specialist.prompt")

    # ==========================================================================
    # Tool Configuration
    # ==========================================================================

    # Core research tools
    tools: list[Any] = [
        research_product_tool,     # Web research for product enrichment
        extract_web_content_tool,  # Deep content extraction from URLs
    ]

    # Universal Data Engine tools - Domain-scoped
    from autifyme_agents.tools.data_engine import (
        create_aggregate_data_tool,
        create_inspect_schema_tool,
        create_read_data_tool,
        create_write_data_tool,
    )

    # Schema inspection (all catalog tables)
    tools.append(
        create_inspect_schema_tool(
            storage,
            tables=CATALOG_TABLES_ALL,
        )
    )

    # Read operations (all catalog tables)
    tools.append(
        create_read_data_tool(
            storage,
            tables=CATALOG_TABLES_ALL,
        )
    )

    # Aggregate operations (analytics, reporting)
    tools.append(
        create_aggregate_data_tool(
            storage,
            tables=CATALOG_TABLES_ALL,
        )
    )

    # Write operations (CRUD tables only, triggers HITL)
    tools.append(
        create_write_data_tool(
            storage,
            tables=CATALOG_TABLES_CRUD,  # Exclude read-only tables
        )
    )

    # Image Studio - Gemini 3 Pro Image (Nano Banana Pro)
    # Unified image processing: analyze, edit, generate
    tools.append(create_image_studio_tool())

    # ==========================================================================
    # SubAgent Specification
    # ==========================================================================

    # Description for PM delegation (routing decisions)
    description = (
        "Catalog Specialist - unified domain expert for product catalog operations. "
        "Handles all 'what we sell' operations: products, families, variants, "
        "pricing, assets, and BOM. "
        "Capabilities: schema-driven CRUD, autonomous web research for specs/pricing, "
        "image processing (analyze, edit, generate via Gemini 3 Pro Image), "
        "duplicate detection, multi-table atomic transactions with HITL approval. "
        "Owns: PIM (products, families, variants), DAM (assets, product_assets), "
        "Pricing (price_lists, product_prices), Manufacturing (bom, bom_lines). "
        "Does NOT handle: suppliers, inventory, locations (Operations Specialist domain)."
    )

    # Return SubAgent spec
    spec: dict[str, Any] = {
        "name": "catalog_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        "interrupt_on": {
            "write_data": True,  # HITL for all catalog mutations
        },
    }

    # Add model if specified (otherwise uses PM's default_model)
    if model is not None:
        spec["model"] = model

    return spec


