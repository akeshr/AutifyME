"""Catalog Analyst - Internal catalog data research specialist.

Read-only analyst that queries the product catalog for patterns and similar items.
Answers "What do we HAVE?" - existing products, pricing patterns, family structures.

Cross-domain reuse:
- Catalog: Duplicate detection, pricing alignment, family selection
- Marketing: Product availability, variant options
- Operations: Inventory context, product relationships
"""

from typing import Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.middleware import MultimodalInjectionMiddleware
from autifyme_agents.tools import create_view_image_tool

# Tables catalog_analyst can read (no write access)
CATALOG_ANALYST_TABLES = [
    # PIM (Product Information Management)
    "product_families",
    "products",
    "variant_axes",
    "variant_values",
    "product_variant_values",
    "product_family_industries",
    "categories",  # Product taxonomy
    # Pricing
    "price_lists",
    "product_prices",
    "customer_prices",  # Customer-specific pricing
    # DAM (Digital Asset Management) - read only
    "assets",
    "product_assets",
    # Master Data
    "uom",
    "industries",  # NAICS classification
    # Marketing (read for context)
    "campaigns",
    "campaign_products",
    "marketing_content",
    "customer_segments",
    # Company Context
    "companies",
    "company_intelligence",
]


def _get_analyst_llm() -> BaseChatModel:
    """Get fast, cheap LLM for analyst tasks.

    Uses Gemini 2.5 Flash with minimal thinking for speed.
    Analysts are latency-sensitive (target <200ms for DB queries).
    """
    return get_llm(
        provider="google",
        model="gemini-2.5-flash",
        temperature=0.3,  # Lower temperature for consistent analysis
        max_retries=5,
        thinking_budget=1024,
    )


def create_catalog_analyst(
    storage: StorageInterface,
    model: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Create Catalog Analyst SubAgent spec.

    Args:
        storage: Storage interface for catalog queries (read-only)
        model: Optional LLM override. Defaults to Gemini 2.5 Flash.

    Returns:
        SubAgent spec dict for PM's subagents list.

    Example:
        >>> analyst = create_catalog_analyst(storage)
        >>> # Add to PM subagents
        >>> subagents = [visual_analyst, product_analyst, analyst, ...]
    """
    if storage is None:
        raise ValueError("storage is required for Catalog Analyst")

    system_prompt = load_prompt("analysts/catalog_analyst.prompt")

    description = (
        "Catalog Analyst - catalog data retrieval and analysis.\n\n"
        "DELEGATE WHEN:\n"
        "- 'Get me X' / 'Show me Y' catalog queries\n"
        "- Duplicate/similarity checks needed\n"
        "- Pricing analysis, gap analysis required\n"
        "- Company context or details needed\n\n"
        "DOES NOT: Create/modify records, process images, research external sources."
    )

    # Import here to avoid circular imports
    from autifyme_agents.tools.data_engine import (
        create_aggregate_data_tool,
        create_inspect_schema_tool,
        create_read_data_tool,
    )

    tools: list[Any] = [
        create_inspect_schema_tool(storage, tables=CATALOG_ANALYST_TABLES),
        create_read_data_tool(storage, tables=CATALOG_ANALYST_TABLES),
        create_aggregate_data_tool(storage, tables=CATALOG_ANALYST_TABLES),
        create_view_image_tool(),  # View images for catalog matching
    ]

    # Multimodal middleware injects images from paths in delegation message
    middleware = [MultimodalInjectionMiddleware()]

    spec: dict[str, Any] = {
        "name": "catalog_analyst",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        "middleware": middleware,
        # FilesystemMiddleware (write_file, read_file) is provided by default via DeepAgents
        # No interrupt_on - analysts are read-only
    }

    if model is not None:
        spec["model"] = model
    else:
        spec["model"] = _get_analyst_llm()

    return spec
