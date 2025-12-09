"""Project Manager - Central orchestrator for AutifyME workflows.

Orchestrates domain specialists via SubAgent pattern. Detects intent, delegates
to appropriate specialists, and communicates outcomes.

Architecture:
- PM is orchestrator (read-only tools)
- Specialists are domain experts (creative + catalog)
- DeepAgents handles specialist compilation and state
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from deepagents import create_deep_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import BaseChatModel

from autifyme_agents.analysts import (
    create_catalog_analyst,
    create_product_analyst,
    create_visual_analyst,
)
from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.integrations.storage import get_store
from autifyme_agents.middleware.context_middleware import load_base_context
from autifyme_agents.schemas.context import CompanyContext
from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.schemas.pm_output import PMOutput
from autifyme_agents.specialists.catalog_specialist import create_catalog_specialist
from autifyme_agents.specialists.creative_specialist import create_creative_specialist
from autifyme_agents.tools import create_view_image_tool
from autifyme_agents.tools.data_engine import (
    create_inspect_schema_tool,
    create_read_data_tool,
)

if TYPE_CHECKING:
    from autifyme_agents.workflows.channels.protocol import MessagingChannel

logger = logging.getLogger(__name__)


def _resolve_model(model: BaseChatModel | None = None) -> BaseChatModel:
    """Return configured LLM for PM. Defaults to gemini-2.5-pro.

    Configuration rationale:
    - thinking_budget=128: Minimum for Pro models (cannot disable like Flash).
      PM is orchestrator so minimal thinking suffices.
    - max_retries=5: Production resilience against Gemini's occasional blank responses.
    - temperature=0.7: Balanced creativity for user communication.
    """
    if model is not None:
        return model
    return get_llm(
        provider="google",
        model="gemini-2.5-flash",
        temperature=0.7,  # PM orchestrates, specialists reason
        max_retries=5,  # Increase resilience against blank responses
    )


def _load_prompt(
    company_profile: CompanyProfile,
    base_context: Any,
    channel: MessagingChannel | None = None,
) -> str:
    """Load and format PM prompt with company context."""
    prompt_template = load_prompt("project_manager.prompt")

    platform_name = "unknown"
    if channel is not None:
        platform_name = channel.__class__.__name__.replace("Channel", "").lower()

    catalog_summary_text = f"""
**Your Catalog Summary (Loaded at Startup):**
- Total Product Families: {base_context.catalog_summary.total_families}
- Total SKUs: {base_context.catalog_summary.total_skus}
- Family Names: {', '.join(base_context.catalog_summary.family_names)}
- Top Categories: {', '.join(base_context.catalog_summary.top_categories)}
"""

    root_categories = [cat.name for cat in base_context.taxonomy_tree.root_categories]
    taxonomy_text = f"""
**Your Taxonomy Tree (Loaded at Startup):**
- Total Categories: {base_context.taxonomy_tree.total_categories}
- Root Categories: {', '.join(root_categories)}
"""

    # Company patterns for cold-start handling
    patterns = base_context.company_patterns
    price_min, price_max = patterns.typical_price_range
    patterns_text = f"""
**Company Patterns (For Cold-Start Handling):**
- Primary Workflow: {patterns.primary_workflow}
- Price Range: Rs {price_min:.0f} - Rs {price_max:.0f}
- Common Product Types: {', '.join(patterns.common_product_types) if patterns.common_product_types else 'N/A'}
- SKU Pattern: {patterns.naming_conventions.get('sku_pattern', 'FAMILY-SIZE-VARIANT')}
"""

    return prompt_template.format(
        company_name=company_profile.name,
        brand_voice=company_profile.brand_voice,
        target_audience=company_profile.target_audience,
        platform=platform_name,
    ) + "\n\n" + catalog_summary_text + "\n" + taxonomy_text + "\n" + patterns_text


async def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any,
    storage: StorageInterface,
    channel: MessagingChannel | None = None,
) -> Any:
    """Create Project Manager agent.

    Args:
        company_profile: Company context for brand voice and positioning
        model: LLM for orchestration (defaults to gemini-2.5-flash)
        checkpointer: LangGraph checkpointer for state persistence
        storage: Storage adapter for database operations
        channel: Messaging channel for platform-specific operations

    Returns:
        Compiled DeepAgent
    """
    if checkpointer is None:
        raise ValueError("checkpointer is required for Project Manager")

    if storage is None:
        raise ValueError("storage is required for Project Manager")

    llm = _resolve_model(model)
    store = get_store()

    # Load base context (catalog summary + taxonomy tree)
    logger.info("Loading base context for PM")
    base_context = await load_base_context(company_profile, storage)
    logger.info(
        "Base context loaded",
        extra={
            "catalog_families": base_context.catalog_summary.total_families,
            "taxonomy_categories": base_context.taxonomy_tree.total_categories,
        }
    )

    instructions = _load_prompt(company_profile, base_context, channel)

    # PM Tools - Read-only, orchestration-focused
    pm_tools: list[Any] = []

    # Platform media download (with storage for inbox persistence)
    if channel is not None:
        from autifyme_agents.tools.platform_tools import create_platform_media_tools
        pm_tools.extend(create_platform_media_tools(channel, storage=storage))

    # Schema inspection and read operations
    pm_tools.append(create_inspect_schema_tool(storage, tables=None))
    pm_tools.append(create_read_data_tool(storage))

    # Image viewing - PM uses intelligently based on context/need
    # For deep analysis, delegates to visual_analyst; for quick checks, uses directly
    pm_tools.append(create_view_image_tool())

    # Specialist LLM configuration
    specialist_llm = get_llm(
        provider="google",
        model="gemini-2.5-flash",
        temperature=0.7,
        max_retries=5,  # Match PM resilience for blank response handling
    )

    # Analysts (Research Layer) - Fast, read-only, cross-domain reusable
    visual_analyst = create_visual_analyst()
    product_analyst = create_product_analyst()
    catalog_analyst = create_catalog_analyst(storage=storage)

    # Specialists (Execution Layer) - HITL-enabled, domain-specific
    creative_specialist = create_creative_specialist(
        model=None,
        storage=storage,
    )
    catalog_specialist = create_catalog_specialist(
        model=specialist_llm,
        storage=storage,
    )

    subagents: list[Any] = [
        # Analysts first (research layer)
        visual_analyst,
        product_analyst,
        catalog_analyst,
        # Specialists second (execution layer)
        creative_specialist,
        catalog_specialist,
    ]

    # Structured output for multimodal responses (text + images)
    response_format = ToolStrategy(
        schema=PMOutput,
        handle_errors=True,  # Retry on parse errors
    )

    project_manager = create_deep_agent(
        tools=pm_tools,
        system_prompt=instructions,
        model=llm,
        subagents=subagents,
        response_format=response_format,
        interrupt_on={},
        checkpointer=checkpointer,
        store=store,
        context_schema=CompanyContext,
    )

    initial_state = {
        "company_profile": company_profile.model_dump(),
        "base_context": base_context.model_dump(),
        "status": "ready",
        "current_workflow": None,
        "specialist_results": {},
    }

    return project_manager.with_config(
        {
            "metadata": {"version": "1.0.0"},
            "initial_state": initial_state,
        }
    )
