"""Project Manager - Central orchestrator for AutifyME workflows.

Orchestrates domain specialists via SubAgent pattern. Detects intent, delegates
to appropriate specialists, synthesizes results, and persists via HITL-enabled tools.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from deepagents import create_deep_agent
from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.integrations.storage import get_store
from autifyme_agents.middleware.context_middleware import load_base_context
from autifyme_agents.schemas.context import CompanyContext
from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.specialists.product_architecture_specialist import (
    create_product_architecture_specialist,
)
from autifyme_agents.tools.campaign_persistence_tools import (
    create_save_campaign_tool,
)
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool
from autifyme_agents.tools.pm_context_tools import (
    create_get_category_info_tool,
    create_search_catalog_summary_tool,
)
from autifyme_agents.tools.schema_tools import get_product_schema
from autifyme_agents.tools.universal_crud_tool import create_database_tool

if TYPE_CHECKING:
    from autifyme_agents.workflows.channels.protocol import MessagingChannel

logger = logging.getLogger(__name__)


def _resolve_model(model: BaseChatModel | None = None) -> BaseChatModel:
    """Return configured LLM for PM. Defaults to gemini-2.5-flash for orchestration."""
    if model is not None:
        return model
    return get_llm(provider="google", model="gemini-2.5-flash", temperature=0.5)


def _load_prompt(
    company_profile: CompanyProfile,
    base_context: Any,
    channel: MessagingChannel | None = None,
) -> str:
    """Load and format PM prompt with company context and base context.

    Base context is formatted into system prompt so LLM can see the actual data.
    """
    prompt_template = load_prompt("project_manager_intelligent.prompt")

    # Extract platform name from channel (same logic as platform_tools.py)
    platform_name = "unknown"
    if channel is not None:
        platform_name = channel.__class__.__name__.replace("Channel", "").lower()

    # Format catalog summary for prompt
    catalog_summary_text = f"""
**Your Catalog Summary (Loaded at Startup):**
- Total Product Families: {base_context.catalog_summary.total_families}
- Total SKUs: {base_context.catalog_summary.total_skus}
- Family Names: {', '.join(base_context.catalog_summary.family_names)}
- Top Categories: {', '.join(base_context.catalog_summary.top_categories)}
"""

    # Format taxonomy tree (just root categories for now)
    root_categories = [cat.name for cat in base_context.taxonomy_tree.root_categories]
    taxonomy_text = f"""
**Your Taxonomy Tree (Loaded at Startup):**
- Total Categories: {base_context.taxonomy_tree.total_categories}
- Root Categories: {', '.join(root_categories)}
"""

    return prompt_template.format(
        company_name=company_profile.name,
        brand_voice=company_profile.brand_voice,
        target_audience=company_profile.target_audience,
        platform=platform_name,
    ) + "\n\n" + catalog_summary_text + "\n" + taxonomy_text


async def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any,
    storage: StorageInterface,
    channel: MessagingChannel | None = None,
) -> Any:
    """Create Project Manager agent.

    PM orchestrates domain specialists for business workflows. Uses SubAgent pattern
    for specialist delegation and HITL-enabled persistence tools.

    Args:
        company_profile: Company context for brand voice and positioning
        model: LLM for orchestration (defaults to gemini-2.5-flash-lite)
        checkpointer: LangGraph checkpointer for PM state persistence
        storage: Storage adapter for database operations
        channel: Messaging channel for platform-specific operations

    Returns:
        Compiled DeepAgent

    Notes:
        - DeepAgents SubAgentMiddleware handles specialist compilation
        - Specialists use default_model and default_middleware from SubAgentMiddleware
        - PM's checkpointer is passed to create_deep_agent
        - Specialist state managed by DeepAgents internally
    """
    if checkpointer is None:
        raise ValueError(
            "checkpointer is required for Project Manager (DeepAgents requirement)"
        )

    if storage is None:
        raise ValueError(
            "storage is required for Project Manager (tools dependency)"
        )

    llm = _resolve_model(model)
    store = get_store()

    # Load base context (catalog summary + taxonomy tree)
    # Uses await since we're in async context
    # Gracefully degrades to empty summaries if DB unavailable
    logger.info("Loading base context for PM (catalog summary + taxonomy tree)")
    base_context = await load_base_context(company_profile, storage)
    logger.info(
        "Base context loaded",
        extra={
            "catalog_families": base_context.catalog_summary.total_families,
            "taxonomy_categories": base_context.taxonomy_tree.total_categories,
        }
    )

    # Load intelligent prompt with company context
    # base_context is available to PM via initial_state
    instructions = _load_prompt(company_profile, base_context, channel)

    # PM Tools
    pm_tools: list[Any] = []

    # Platform-specific tools (media download)
    if channel is not None:
        from autifyme_agents.tools.platform_tools import create_platform_media_tools
        pm_tools.extend(create_platform_media_tools(channel))

    # Context query tools (on-demand detail lookups)
    pm_tools.append(create_search_catalog_summary_tool(storage))
    pm_tools.append(create_get_category_info_tool(storage))

    # Schema query tool (for dynamic operation planning)
    pm_tools.append(get_product_schema)

    # Image analysis tool (multimodal analysis before delegation)
    pm_tools.append(image_analysis_tool)

    # Universal CRUD tool (schema-driven database operations with HITL)
    pm_tools.append(
        create_database_tool(
            storage=storage,
            allowed_operations=["create", "read", "update", "delete"],  # Full CRUD access
        )
    )

    # Campaign persistence tool (HITL-enabled for marketing campaigns)
    pm_tools.append(create_save_campaign_tool(storage))

    # Product Architecture Specialist (SubAgent spec pattern)
    # Returns dict spec that DeepAgents compiles automatically
    # Standard pattern used by all specialists
    #
    # CRITICAL: Specialist needs deterministic model for structured OperationIntent
    # - temperature=0.3: More deterministic for schema-driven operations
    # - thinking_budget=0: No extended reasoning needed for structured outputs
    # PM uses temperature=0.5 for orchestration; specialist needs more precision
    specialist_llm = get_llm(
        provider="google",
        model="gemini-2.5-flash",
        temperature=0.3,
        thinking_budget=0,
    )
    product_architecture_specialist = create_product_architecture_specialist(
        storage=storage,
        model=specialist_llm  # Pass configured LLM instance
    )

    # Add SubAgent spec to subagents list
    # DeepAgents SubAgentMiddleware compiles specialist with default_model
    subagents: list[Any] = [
        product_architecture_specialist,  # SubAgent dict spec
    ]

    # HITL configuration
    interrupt_configs: dict[str, bool] = {
        "execute_database_operation": True,
        "save_campaign": True,
    }

    # Note: create_deep_agent adds SummarizationMiddleware by default
    # No need to pass custom middleware - use default configuration
    # Default: triggers at ~170K tokens, keeps last 6 messages

    project_manager = create_deep_agent(
        tools=pm_tools,
        system_prompt=instructions,
        model=llm,
        subagents=subagents,
        interrupt_on=interrupt_configs,
        checkpointer=checkpointer,
        store=store,
        context_schema=CompanyContext,
    )

    initial_state = {
        "company_profile": company_profile.model_dump(),
        "base_context": base_context.model_dump(),
        "status": "product_architecture_integrated",
        "current_workflow": None,
        "specialist_results": {},
    }

    return project_manager.with_config(
        {
            "metadata": {"version": "1.0.0"},
            "initial_state": initial_state,
        }
    )
