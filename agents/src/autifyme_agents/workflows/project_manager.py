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
from langchain.agents.middleware import ContextEditingMiddleware
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
from autifyme_agents.middleware import create_execution_limits
from autifyme_agents.middleware.context_management import HybridTruncateThenClearEdit
from autifyme_agents.middleware.context_middleware import load_base_context
from autifyme_agents.schemas.context import CompanyContext
from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.schemas.pm_output import PMOutput
from autifyme_agents.specialists.catalog_specialist import create_catalog_specialist
from autifyme_agents.specialists.creative_specialist import create_creative_specialist

# NOTE: PM has LIMITED content tools - view_image only for conversational context
# Detailed analysis still delegated to analysts per ARCHITECTURAL_VISION.md
# PM sees images for routing decisions, analysts do thorough domain analysis

if TYPE_CHECKING:
    from autifyme_agents.workflows.channels.protocol import MessagingChannel

logger = logging.getLogger(__name__)


def _resolve_model(model: BaseChatModel | None = None) -> BaseChatModel:
    """Return configured LLM for PM. Defaults to gemini-3-flash-preview.

    Configuration rationale:
    - thinking_level='low': Fast orchestration with Gemini 3.
    - max_retries=5: Production resilience against Gemini's occasional blank responses.
    - temperature=1.0: Gemini 3 default (below 1.0 may cause looping).
    """
    if model is not None:
        return model
    return get_llm(
        provider="google",
        model="gemini-3-flash-preview",
        thinking_level="low",  # Fast orchestration
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
        model: LLM for orchestration (defaults to gemini-3-flash-preview)
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

    # PM Tools - Protocol loading, media access, view_image for conversational context
    # PM can SEE images for routing decisions; detailed analysis delegated to analysts
    pm_tools: list[Any] = []

    # load_protocol for PM to load coordination protocols (domain_awareness, coordination_patterns)
    # PM uses this for: understanding domain boundaries, conflict resolution, multi-domain coordination
    from autifyme_agents.tools.protocol_loader import create_load_protocol_tool
    pm_tools.append(create_load_protocol_tool())

    # view_image for PM to see user images and understand conversational context
    # PM uses this for: initial understanding, conversational references ("the blue one")
    # PM does NOT use this for: detailed analysis (that's visual_analyst's job)
    from autifyme_agents.tools.view_image import create_view_image_tool
    pm_tools.append(create_view_image_tool())

    # list_storage for PM to discover files in storage folders
    # PM uses this for: session awareness (what's in inbox/pending), workflow planning
    if storage is not None:
        from autifyme_agents.tools.list_storage import create_list_storage_tool
        pm_tools.append(create_list_storage_tool(storage))

    # Platform media download (with storage for inbox persistence)
    if channel is not None:
        from autifyme_agents.tools.platform_tools import create_platform_media_tools
        pm_tools.extend(create_platform_media_tools(channel, storage=storage))

    # Specialist LLM configuration
    specialist_llm = get_llm(
        provider="google",
        model="gemini-3-flash-preview",
        thinking_level="high",  # Specialists need deeper reasoning
        max_retries=5,  # Match PM resilience for blank response handling
    )

    # Analysts (Research Layer) - Fast, read-only, cross-domain reusable
    # All agents receive company_profile for prompt formatting
    visual_analyst = create_visual_analyst(company_profile=company_profile)
    product_analyst = create_product_analyst(company_profile=company_profile)
    catalog_analyst = create_catalog_analyst(storage=storage, company_profile=company_profile)

    # Specialists (Execution Layer) - HITL-enabled, domain-specific
    creative_specialist = create_creative_specialist(
        company_profile=company_profile,
        storage=storage,
    )
    catalog_specialist = create_catalog_specialist(
        storage=storage,
        company_profile=company_profile,
        model=specialist_llm,
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

    # Aggressive context management: Truncate data tools at 30k tokens
    # Task tool (subagent calls) preserved - contains specialist decisions
    # Other tools (schema, read_data, etc.) truncated - raw data can be re-fetched
    pm_middleware = [
        *create_execution_limits(limit=60),
        ContextEditingMiddleware(
            edits=[
                HybridTruncateThenClearEdit(
                    trigger_truncate=50000,  # Start truncating at 30k tokens
                    trigger_clear=80000,  # Clear if still over 80k
                    max_truncate_length=1000,  # Keep first 500 chars of each result
                    keep_recent_truncate=5,  # Don't truncate last 3 results
                    keep_recent_clear=5,  # Don't clear last 5 results
                    exclude_tools=("task",),  # Preserve subagent results
                )
            ]
        ),
    ]

    project_manager = create_deep_agent(
        tools=pm_tools,
        system_prompt=instructions,
        model=llm,
        subagents=subagents,
        middleware=pm_middleware,
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
