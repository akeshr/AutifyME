"""Project Manager agent built on deepagents.

This module adheres to our Architecture-First mandate by centralizing all
cross-workflow orchestration logic in a single Project Manager agent. The
implementation closely follows `docs/architecture/PROJECT_MANAGER_DESIGN.md`
and leverages deepagents for planning, sub-agent delegation, and HITL.

**HITL Strategy**: Uses LangGraph's native `interrupt_before=["tools"]` to pause
execution after the agent emits tool calls but before the tool node executes them.
This allows the runner to inspect tool calls (e.g., save_product) and request
human approval, then resume the graph to execute the tool naturally. No custom
post-model hooks are needed—LangGraph's tool node handles all ToolMessage synthesis.
"""

from __future__ import annotations

from typing import Any, Sequence

from deepagents import create_deep_agent, SubAgent
from langchain_core.language_models.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.schemas.state import ProjectManagerState
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.tools import registry as tools_registry


_DEFAULT_BUILTIN_TOOLS: list[str] = ["write_todos"]


def _resolve_model(model: BaseChatModel | None = None) -> BaseChatModel:
    """Return the configured chat model for the Project Manager.

    Follows the Architecture-First rule by centralizing model selection through
    our LLM factory. Default configuration favours GPT-4o with low temperature
    for deterministic planning.
    """

    if model is not None:
        return model
    return get_llm(model="gpt-4o", temperature=0.2)


def _load_prompt(company_profile: CompanyProfile) -> str:
    prompt_template = load_prompt("project_manager.prompt")
    return prompt_template.format(
        company_name=company_profile.name,
        brand_voice=company_profile.brand_voice,
        target_audience=company_profile.target_audience,
    )


def _build_subagents(company_profile: CompanyProfile, storage: StorageInterface) -> list[SubAgent]:
    """Return deepagents sub-agent specifications for all departments.

    Each sub-agent is a DeepAgents SubAgent dict that defines:
    - name: Sub-agent identifier
    - description: When PM should delegate to this sub-agent
    - prompt: System prompt for the sub-agent
    - tools: List of tool objects (not names) the sub-agent can use

    Note: These are NOT the same as department agents. DeepAgents sub-agents
    are lightweight delegates for the PM, while departments are full LangChain
    agents with middleware, HITL, and checkpointing.
    """

    cataloging_prompt = tools_registry.get_cataloging_instructions(company_profile)

    return [
        {
            "name": "cataloging_department",
            "description": "Manages product ingestion and catalog creation workflows. Delegate here for product cataloging requests with or without images.",
            "prompt": cataloging_prompt,
            "tools": tools_registry.get_cataloging_tool_objects(storage),
        }
    ]


def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any,
    storage: StorageInterface,
    tools: Sequence | None = None,
) -> Any:
    """Create the deepagents-powered Project Manager with native HITL via tool_configs.

    Args:
        company_profile: Single-tenant company context required for all workflows.
        model: Optional override for the LLM powering the manager.
        checkpointer: LangGraph checkpointer for durable state (required - provided by runner).
        storage: Storage adapter implementing StorageInterface (required).
        tools: Optional explicit tool list (otherwise retrieved from registry).

    Returns:
        Compiled deepagents agent with tool_configs for HITL interrupts.

    **Architecture Compliance**:
    - Uses DeepAgents `tool_configs` for HITL (native to deepagents 0.0.11rc1)
    - Tool configs specify which tools require approval (save_product)
    - Runner handles interrupt detection and resume via Command API
    - Sub-agents provide lightweight delegation without full agent overhead
    """

    llm = _resolve_model(model)
    instructions = _load_prompt(company_profile)

    cataloging_tools = list(tools) if tools is not None else tools_registry.get_cataloging_tool_objects(storage)

    subagents = _build_subagents(company_profile, storage)

    tool_configs = tools_registry.get_interrupt_config()

    project_manager = create_deep_agent(
        tools=cataloging_tools,
        instructions=instructions,
        model=llm,
        subagents=subagents,
        tool_configs=tool_configs,
        checkpointer=checkpointer,
    )

    initial_state = {
        "company_profile": company_profile.model_dump(),
        "status": "idle",
        "plan": [],
        "current_step": 0,
        "department_results": {},
        "todos": [],
        "remaining_steps": 8,
    }

    return project_manager.with_config(
        {
            "metadata": {
                "workflow": "cataloging",
            },
            "initial_state": initial_state,
        }
    )
 