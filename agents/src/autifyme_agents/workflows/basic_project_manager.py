"""Project Manager - orchestrates specialists to handle business workflows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from deepagents import create_deep_agent
from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.integrations.storage import get_store
from autifyme_agents.schemas.context import CompanyContext
from autifyme_agents.schemas.models import CompanyProfile

if TYPE_CHECKING:
    from autifyme_agents.workflows.channels.protocol import MessagingChannel


def _resolve_model(model: BaseChatModel | None = None) -> BaseChatModel:
    """Return configured LLM for PM. Defaults to gpt-4.1-mini."""
    if model is not None:
        return model
    return get_llm(model="gpt-4.1-mini", temperature=0.2)


def _load_prompt(company_profile: CompanyProfile) -> str:
    prompt_template = load_prompt("basic_project_manager.prompt")
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
    tools: Sequence[Any] | None = None,
) -> Any:
    """Create Project Manager that orchestrates specialists.

    Args:
        company_profile: Company context for brand voice and target audience
        model: Optional LLM override
        checkpointer: LangGraph checkpointer for state persistence (required)
        storage: Storage adapter for database operations (required)
        channel: Messaging channel for platform-specific media download tools
        tools: Ignored - tools auto-configured from channel

    Returns:
        Compiled DeepAgent with specialist delegation
    """

    if checkpointer is None:
        raise ValueError("checkpointer is required for Project Manager (DeepAgents requirement)")

    if storage is None:
        raise ValueError("storage is required for Project Manager (tools dependency)")

    llm = _resolve_model(model)
    instructions = _load_prompt(company_profile)

    store = get_store()

    # Platform tools (media download based on channel)
    pm_tools: list[Any] = []
    if channel is not None:
        from autifyme_agents.tools.platform_tools import create_platform_media_tools
        pm_tools.extend(create_platform_media_tools(channel))

    # Cataloging tools - save_product on PM for HITL (avoids subagent re-invocation issue)
    from autifyme_agents.tools.storage_tools import create_save_product_tool
    pm_tools.append(create_save_product_tool(storage))

    # Specialist for image analysis (no HITL, returns data to PM)
    from autifyme_agents.specialists.cataloging_specialist import create_cataloging_specialist

    subagents: list[Any] = [
        create_cataloging_specialist(storage),  # Has image_analysis_tool only
    ]

    # HITL only at PM level for save_product
    # Specialist analyzes images and returns data; PM saves with approval
    interrupt_configs: dict[str, bool] = {"save_product": True}

    # NOTE: DeepAgents automatically adds HumanInTheLoopMiddleware when interrupt_on is provided
    # Hybrid architecture: specialist for analysis, PM for HITL-required saves
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
        "plan": [],
        "current_step": 0,
        "department_results": {},
        "todos": [],
        "remaining_steps": 8,
        "pending_interrupts": [],  # Interrupt tracking (handled by runner + approval_analyzer)
    }

    return project_manager.with_config(
        {
            "metadata": {
                "workflow": "cataloging",
            },
            "initial_state": initial_state,
        }
    )
