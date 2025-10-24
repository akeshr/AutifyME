"""
Project Manager - Main orchestrator for all AutifyME workflows.

Architecture:
- PM orchestrates domain specialists via DeepAgents SubAgent pattern
- Specialists analyze and generate (no persistence)
- PM owns HITL persistence tools
- PM detects workflow intent, delegates to specialists, synthesizes results, persists

Current Workflow Implementation:
- Product Onboarding: 5 domain specialists for enterprise-grade product families

Domain Specialists (5):
1. Product Architecture - Variant structure and SKU design
2. Taxonomy - Multi-system classification (internal, Google, NAICS)
3. Market Intelligence - Positioning, segments, industry use cases
4. Visual Assets - Image organization and quality
5. Content & SEO - Descriptions, meta tags, platform content

Future Workflows:
- Marketing campaigns
- Inventory management
- CRM operations
- Competitive analysis

HITL Strategy:
- PM level only (interrupt_on for persistence tools)
- User sees complete data before persistence
- Single approval point with full context
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deepagents import create_deep_agent
from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.integrations.storage import get_store
from autifyme_agents.schemas.context import CompanyContext
from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.specialists.content_seo_specialist import (
    create_content_seo_specialist,
)
from autifyme_agents.specialists.market_intelligence_specialist import (
    create_market_intelligence_specialist,
)
from autifyme_agents.specialists.product_architecture_specialist import (
    create_product_architecture_specialist,
)
from autifyme_agents.specialists.taxonomy_specialist import create_taxonomy_specialist
from autifyme_agents.specialists.visual_assets_specialist import (
    create_visual_assets_specialist,
)
from autifyme_agents.tools.product_persistence_tools import (
    create_save_product_family_tool,
)

if TYPE_CHECKING:
    from autifyme_agents.workflows.channels.protocol import MessagingChannel


def _resolve_model(model: BaseChatModel | None = None) -> BaseChatModel:
    """Return configured LLM for PM. Defaults to gpt-4.1-mini for orchestration."""
    if model is not None:
        return model
    return get_llm(model="gpt-4.1-mini", temperature=0.2)


def _load_prompt(company_profile: CompanyProfile) -> str:
    """Load and format PM prompt with company context."""
    prompt_template = load_prompt("project_manager.prompt")
    return prompt_template.format(
        company_name=company_profile.name,
        brand_voice=company_profile.brand_voice,
        target_audience=company_profile.target_audience,
    )


def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any,
    storage: StorageInterface,
    channel: MessagingChannel | None = None,
) -> Any:
    """
    Create Project Manager - main orchestrator for all AutifyME workflows.

    Current Implementation:
    Orchestrates 5 domain specialists for product onboarding workflow:
    - Product Architecture Specialist (variant structure)
    - Taxonomy Specialist (multi-system classification)
    - Market Intelligence Specialist (positioning & segments)
    - Visual Assets Specialist (image organization)
    - Content & SEO Specialist (content generation)

    Architecture:
    - PM = DeepAgent with SubAgents
    - Specialists = SubAgent dicts (analysis only)
    - PM owns HITL persistence tools
    - PM orchestrates workflow: delegate → synthesize → present → persist

    Extensibility:
    Designed to support future workflows (marketing, inventory, CRM)
    by adding new specialists and persistence tools as needed.

    Args:
        company_profile: Company context for brand voice and positioning
        model: Optional LLM override (defaults to gpt-4.1-mini)
        checkpointer: LangGraph checkpointer for state persistence (required)
        storage: Storage adapter for database operations (required)
        channel: Messaging channel for platform-specific operations (optional)

    Returns:
        Compiled DeepAgent ready for workflow orchestration
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
    instructions = _load_prompt(company_profile)
    store = get_store()

    # ==========================================================================
    # PM Tools - HITL Persistence ONLY
    # ==========================================================================
    # PM owns persistence tools for implemented workflows
    # Currently: save_product_family (product onboarding)
    # Platform media tools if channel provided
    pm_tools: list[Any] = []

    if channel is not None:
        from autifyme_agents.tools.platform_tools import create_platform_media_tools

        pm_tools.extend(create_platform_media_tools(channel))

    # HITL persistence tools - PM level only
    pm_tools.append(create_save_product_family_tool(storage))

    # ==========================================================================
    # Specialists - Domain Experts (Analysis Only, No Persistence)
    # ==========================================================================
    # 5 domain specialists for product onboarding workflow
    # New workflows will add additional specialists here
    subagents: list[Any] = [
        create_product_architecture_specialist(),
        create_taxonomy_specialist(storage),
        create_market_intelligence_specialist(),
        create_visual_assets_specialist(),
        create_content_seo_specialist(),
    ]

    # ==========================================================================
    # HITL Configuration - PM Level Only
    # ==========================================================================
    # Persistence tools trigger HITL interrupts
    # PM presents data to user, gets approval, persists atomically
    interrupt_configs: dict[str, bool] = {
        "save_product_family": True,
    }

    # ==========================================================================
    # Create DeepAgent
    # ==========================================================================
    project_manager = create_deep_agent(
        tools=pm_tools,
        system_prompt=instructions,
        model=llm,
        subagents=subagents,
        interrupt_on=interrupt_configs,
        checkpointer=checkpointer,
        store=store,
        use_longterm_memory=True,
        context_schema=CompanyContext,
    )

    # ==========================================================================
    # Initial State
    # ==========================================================================
    initial_state = {
        "company_profile": company_profile.model_dump(),
        "status": "idle",
        "current_workflow": None,  # product_onboarding, marketing, inventory, etc.
        "specialist_results": {},  # Track specialist outputs
    }

    return project_manager.with_config(
        {
            "metadata": {
                "version": "1.0.0",
            },
            "initial_state": initial_state,
        }
    )
