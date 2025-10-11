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

from deepagents import create_deep_agent  # type: ignore[import-untyped]
from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.core.ports import StorageInterface


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


def _create_cataloging_subagent(
    storage: StorageInterface,
    checkpointer: Any,
) -> dict:
    """Create cataloging department as a CustomSubAgent.

    DeepAgents supports two subagent patterns:
    1. SubAgent: Declare specs, DeepAgents builds agent
    2. CustomSubAgent: Pass pre-built agent graph

    Our department has complex middleware (HITL, caching, summarization) and
    response_format, so we use CustomSubAgent to preserve all that logic.

    This is the correct architecture: PM delegates to department subagent,
    department executes workflow with full middleware stack.
    """
    from autifyme_agents.departments.cataloging_department import create_cataloging_department

    # Create FULL department agent with middleware, HITL, checkpointing
    cataloging_dept_graph = create_cataloging_department(
        checkpointer=checkpointer,
        storage=storage,
    )

    # Return CustomSubAgent spec for DeepAgents
    return {
        "name": "cataloging_department",
        "description": (
            "Handles product cataloging workflows including adding new products, "
            "updating existing products, and batch cataloging. Supports text, images, "
            "videos, and combinations. Returns structured CatalogingResult."
        ),
        "graph": cataloging_dept_graph,
    }


def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any,
    storage: StorageInterface,
    tools: Sequence | None = None,
) -> Any:
    """Create the deepagents-powered Project Manager with proper delegation hierarchy.

    Args:
        company_profile: Single-tenant company context required for all workflows.
        model: Optional override for the LLM powering the manager.
        checkpointer: LangGraph checkpointer for durable state (required - provided by runner).
        storage: Storage adapter implementing StorageInterface (required).
        tools: Optional explicit tool list for PM orchestration only (NOT domain tools).

    Returns:
        Compiled deepagents agent with proper delegation to departments.

    **Architecture**:
    - PM has NO direct access to domain tools (analyze_image, save_product, etc.)
    - PM MUST delegate to departments via 'task' tool
    - Subagents (departments) have domain tools
    - Enforces PM → Department → Specialist → Tools hierarchy
    """

    if checkpointer is None:
        raise ValueError("checkpointer is required for Project Manager (DeepAgents requirement)")

    llm = _resolve_model(model)
    instructions = _load_prompt(company_profile)

    # PM has NO domain tools - only orchestration tools if provided
    pm_tools = list(tools) if tools is not None else []

    # Departments are subagents (proper delegation hierarchy)
    subagents: list[Any] = [
        _create_cataloging_subagent(storage, checkpointer),
    ]

    # No tool_configs needed - departments handle their own HITL via middleware
    tool_configs: dict[str, Any] = {}

    project_manager = create_deep_agent(
        tools=pm_tools,  # PM has NO direct domain tools
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
 