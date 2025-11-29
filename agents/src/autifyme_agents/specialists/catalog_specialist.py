"""
Catalog Specialist - Domain expert for product catalog and digital assets.

Domain Ownership:
- Product catalog: products, product_families [CRUD]
- Digital assets: assets, product_assets [CRUD]
- Reference data: uom [READ]

Responsibilities:
- Product lifecycle management (create, update, discontinue)
- Digital asset management (upload, link, organize)
- Image processing ownership (preparation for image_studio tool)
- Schema-driven operation planning
- Intelligent duplicate detection

Architecture:
- SubAgent spec: Standard dict format for PM delegation
- Returns dict with {name, description, tools, system_prompt, model}
- DeepAgents compiles specialist automatically in PM
- HITL enabled on write_data for mutation approval

Phase: 3A (Minimal Catalog Specialist)
- Focused on products + assets domain
- BOM/pricing deferred to Phase 3B
"""

from typing import Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool
from autifyme_agents.tools.research_tools import (
    extract_web_content_tool,
    research_product_tool,
)


def create_catalog_specialist(
    storage: StorageInterface,
    model: str | BaseChatModel | None = None,
) -> dict[str, Any]:
    """
    Create Catalog Specialist SubAgent spec.

    Standard SubAgent Pattern: Returns dict for PM's subagents list.

    Domain Ownership:
    - products [CRUD] - Individual SKUs
    - product_families [CRUD] - Product groupings
    - assets [CRUD] - Digital asset master
    - product_assets [CRUD] - Product-asset links
    - uom [READ] - Unit of measure reference

    Responsibilities:
    - Product lifecycle management
    - Digital asset organization
    - Image processing ownership (future: image_studio)
    - Duplicate detection and catalog intelligence
    - Schema-driven operation planning

    Args:
        storage: Storage interface for database operations (REQUIRED)
        model: Optional model (string or LLM instance).
               - String: "google:gemini-2.5-pro", "openai:gpt-4o"
               - LLM instance: Pre-configured BaseChatModel
               - None: Uses PM's default_model from SubAgentMiddleware

    Returns:
        SubAgent spec dict for PM's subagents list

    Notes:
        - Phase 3A: Minimal scope (products + assets)
        - Phase 3B will add: BOM, pricing, deprecate narrow specialists
        - HITL on write_data for all mutations
    """
    if storage is None:
        raise ValueError(
            "storage is required for Catalog Specialist (tools dependency)"
        )

    # Load specialist prompt
    system_prompt = load_prompt("specialists/catalog_specialist.prompt")

    # Phase 3A: Catalog domain tables (minimal scope)
    # Products + Assets for catalog operations
    catalog_tables_crud = [
        "products",           # Individual SKUs
        "product_families",   # Product groupings
        "assets",             # Digital asset master
        "product_assets",     # Product-asset junction
    ]

    # Read-only reference tables
    catalog_tables_read = [
        "uom",                # Unit of measure reference
    ]

    # All tables this specialist can access
    all_tables = catalog_tables_crud + catalog_tables_read

    # Core tools - Domain expertise
    tools: list[Any] = [
        image_analysis_tool,         # Visual attribute extraction
        research_product_tool,       # Web research for product enrichment
        extract_web_content_tool,    # Deep content extraction from URLs
    ]

    # Universal Data Engine tools - Domain-restricted
    from autifyme_agents.tools.data_engine import (
        create_inspect_schema_tool,
        create_read_data_tool,
        create_write_data_tool,
    )

    # Schema inspection (all domain tables)
    tools.append(
        create_inspect_schema_tool(
            storage,
            tables=all_tables,
        )
    )

    # Read operations (all domain tables)
    tools.append(
        create_read_data_tool(
            storage,
            tables=all_tables,
        )
    )

    # Write operations (CRUD tables only, excludes read-only reference tables)
    # Specialist owns domain mutations - HITL approval for all writes
    tools.append(
        create_write_data_tool(
            storage,
            tables=catalog_tables_crud,
        )
    )

    # Description for PM delegation (routing decisions)
    description = (
        "Catalog specialist with domain ownership of products and digital assets. "
        "Core capabilities: product lifecycle management (create, update, discontinue), "
        "digital asset management (upload, link, organize), duplicate detection. "
        "Tables owned: products, product_families, assets, product_assets [CRUD], uom [READ]. "
        "Image processing owner: analyzes product images, manages asset relationships, "
        "prepares for image_studio integration. "
        "Research capabilities: web search for product specs, content extraction. "
        "Returns operation plans with HITL approval for all mutations."
    )

    # Return SubAgent spec
    spec: dict[str, Any] = {
        "name": "catalog_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        "interrupt_on": {
            "write_data": True,  # HITL for domain mutations
        },
    }

    # Add model if specified (otherwise uses PM's default_model)
    if model is not None:
        spec["model"] = model

    return spec
