"""Catalog Analyst - Internal catalog data research specialist.

Read-only analyst that queries the product catalog for patterns and similar items.
Answers "What do we HAVE?" - existing products, pricing patterns, family structures.

Cross-domain reuse:
- Catalog: Duplicate detection, pricing alignment, family selection
- Marketing: Product availability, variant options
- Operations: Inventory context, product relationships

Protocol Integration (v2):
- Loads business_context, family_fit, and tool_mastery protocols at task start
- Protocol grounds analysis in domain expertise and tool patterns
"""

from typing import TYPE_CHECKING, Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.middleware import MultimodalInjectionMiddleware, create_execution_limits
from autifyme_agents.tools import create_view_image_tool
from autifyme_agents.tools.protocol_loader import create_load_protocol_tool

if TYPE_CHECKING:
    from autifyme_agents.schemas.models import CompanyProfile

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
    """Get LLM for analyst tasks with balanced reasoning.

    Uses Gemini 3 Flash with 'medium' thinking - enough for behavioral discipline
    (think-before-acting, stop conditions) without excessive latency.
    """
    return get_llm(
        provider="google",
        model="gemini-3-flash-preview",
        thinking_level="medium",  # Balanced: discipline without latency penalty
        max_retries=5,
    )


def create_catalog_analyst(
    storage: StorageInterface,
    company_profile: "CompanyProfile",
    model: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Create Catalog Analyst SubAgent spec.

    Args:
        storage: Storage interface for catalog queries (read-only)
        company_profile: Company context for prompt formatting.
        model: Optional LLM override. Defaults to Gemini 3 Flash.

    Returns:
        SubAgent spec dict for PM's subagents list.

    Example:
        >>> analyst = create_catalog_analyst(storage, company_profile)
        >>> # Add to PM subagents
        >>> subagents = [visual_analyst, product_analyst, analyst, ...]
    """
    if storage is None:
        raise ValueError("storage is required for Catalog Analyst")
    if company_profile is None:
        raise ValueError("company_profile is required for Catalog Analyst (single-tenant)")

    prompt_template = load_prompt("analysts/catalog_analyst.prompt")

    system_prompt = prompt_template.format(
        company_name=company_profile.name,
        currency_symbol=company_profile.currency_symbol,
        default_currency=company_profile.default_currency,
        price_positioning=company_profile.price_positioning,
        business_models=", ".join(company_profile.business_models) if company_profile.business_models else "B2B",
        target_markets=", ".join(company_profile.target_markets) if company_profile.target_markets else "India",
    )

    description = (
        "ROLE: Analyst (read-only, protocol-integrated)\n"
        "MISSION: UNLIMITED internal exploration - answer ANY question about our catalog.\n\n"
        "OWNERSHIP:\n"
        "- Full catalog intelligence - any question about internal data\n"
        "- Adapts analysis by task (family fit, duplicates, pricing, gaps, etc.)\n"
        "- Protocol-grounded decisions (business_context, family_fit, etc.)\n\n"
        "INPUTS I NEED:\n"
        "- The question to answer about our catalog\n"
        "- Optional: keywords/attributes to search, candidate IDs, image paths\n\n"
        "OUTPUTS I PRODUCE:\n"
        "- Complete findings with evidence (IDs, fields, aggregates)\n"
        "- Protocol-grounded recommendations when applicable\n"
        "- Write catalog_analysis_[item].md to thread directory\n\n"
        "TOOLS I USE:\n"
        "- load_protocol (business_context, family_fit, and others as needed)\n"
        "- inspect_schema, read_data, aggregate_data, view_image\n\n"
        "GUARDRAILS:\n"
        "- No write_data; no external web research; no image editing"
    )

    # Import here to avoid circular imports
    from autifyme_agents.tools.data_engine import (
        create_aggregate_data_tool,
        create_inspect_schema_tool,
        create_read_data_tool,
    )

    tools: list[Any] = [
        create_load_protocol_tool(),
        create_inspect_schema_tool(storage, tables=CATALOG_ANALYST_TABLES),
        create_read_data_tool(storage, tables=CATALOG_ANALYST_TABLES),
        create_aggregate_data_tool(storage, tables=CATALOG_ANALYST_TABLES),
        create_view_image_tool(),  # View images for catalog matching
    ]

    # Multimodal middleware injects images from paths in delegation message
    # Execution limits: read-only analyst with catalog query limits
    middleware = [
        *create_execution_limits(limit=60),
        MultimodalInjectionMiddleware(),
    ]

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
