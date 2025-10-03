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

from deepagents import create_deep_agent
from deepagents.builder import SerializableSubAgent
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


def _build_subagents(company_profile: CompanyProfile) -> list[SerializableSubAgent]:
    """Return deepagents sub-agent specifications for all departments."""

    cataloging_prompt = tools_registry.get_cataloging_instructions(company_profile)

    return [
        {
            "name": "cataloging_department",
            "description": "Manages product ingestion and catalog creation workflows.",
            "prompt": cataloging_prompt,
            "tools": tools_registry.get_cataloging_tool_names(),
        }
    ]


def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer=None,
    builtin_tools: Sequence[str] | None = None,
    tools: Sequence | None = None,
    storage: StorageInterface | None = None,
) -> Any:
    """Create the deepagents-powered Project Manager with native LangGraph HITL.

    Args:
        company_profile: Single-tenant company context required for all workflows.
        model: Optional override for the LLM powering the manager.
        checkpointer: Optional LangGraph checkpointer for durable state. If not
            provided, the function will create a Postgres-backed saver.
        builtin_tools: Optional subset of deepagents built-ins to enable.
        tools: Optional explicit tool list (otherwise retrieved from registry).
        storage: Storage adapter implementing StorageInterface (required).

    Returns:
        Compiled deepagents agent with interrupt_before=["tools"] for HITL.

    **Architecture Compliance**:
    - Uses native LangGraph `interrupt_before` for HITL (per LANGCHAIN_V1_FEATURES.md).
    - No custom post-model hooks—tool node synthesizes ToolMessages naturally.
    - Interrupts pause execution after agent emits tool calls, before execution.
    - Runner inspects tool calls (e.g., save_product), requests approval, resumes.
    """

    llm = _resolve_model(model)
    instructions = _load_prompt(company_profile)

    if storage is None:
        raise ValueError("storage adapter implementing StorageInterface is required")

    cataloging_tools = list(tools) if tools is not None else tools_registry.get_cataloging_tool_objects(storage)

    subagents = _build_subagents(company_profile)

    if checkpointer is None:
        with get_checkpointer() as saver:
            checkpointer = saver

    enabled_builtins = list(builtin_tools) if builtin_tools is not None else _DEFAULT_BUILTIN_TOOLS

    # DeepAgents uses interrupt_config to map tool names to HITL behavior.
    # Under the hood, this leverages LangGraph's interrupt mechanism to pause
    # execution after the agent emits tool calls but before the tool node runs.
    # Setting a tool to `True` in interrupt_config triggers HITL for that tool.
    interrupt_config = tools_registry.get_interrupt_config()

    project_manager = create_deep_agent(
        tools=cataloging_tools,
        instructions=instructions,
        model=llm,
        subagents=subagents,
        builtin_tools=enabled_builtins,
        interrupt_config=interrupt_config,  # HITL for save_product, etc.
        checkpointer=checkpointer,
        state_schema=ProjectManagerState,
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
 