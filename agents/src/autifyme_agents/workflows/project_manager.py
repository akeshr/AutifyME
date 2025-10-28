"""Project Manager - Central orchestrator for AutifyME workflows.

Orchestrates domain specialists via SubAgent pattern. Detects intent, delegates
to appropriate specialists, synthesizes results, and persists via HITL-enabled tools.
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
from autifyme_agents.tools.campaign_persistence_tools import (
    create_save_campaign_tool,
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
    # Using minimal prompt during specialist integration
    prompt_template = load_prompt("project_manager_minimal.prompt")
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
    """Create Project Manager agent.

    PM orchestrates domain specialists for business workflows. Uses SubAgent pattern
    for specialist delegation and HITL-enabled persistence tools.

    Args:
        company_profile: Company context for brand voice and positioning
        model: LLM for orchestration (defaults to gpt-4.1-mini)
        checkpointer: LangGraph checkpointer for state persistence
        storage: Storage adapter for database operations
        channel: Messaging channel for platform-specific operations

    Returns:
        Compiled DeepAgent
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

    # PM Tools
    pm_tools: list[Any] = []

    if channel is not None:
        from autifyme_agents.tools.platform_tools import create_platform_media_tools
        pm_tools.extend(create_platform_media_tools(channel))

    # HITL persistence tools
    pm_tools.append(create_save_product_family_tool(storage))
    pm_tools.append(create_save_campaign_tool(storage))

    # Specialists (SubAgent pattern)
    subagents: list[Any] = []

    # HITL configuration
    interrupt_configs: dict[str, bool] = {
        "save_product_family": True,
        "save_campaign": True,
    }
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

    initial_state = {
        "company_profile": company_profile.model_dump(),
        "status": "idle",
        "current_workflow": None,
        "specialist_results": {},
    }

    return project_manager.with_config(
        {
            "metadata": {"version": "1.0.0"},
            "initial_state": initial_state,
        }
    )
