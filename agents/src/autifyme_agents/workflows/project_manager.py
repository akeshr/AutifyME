"""Project Manager agent built on deepagents.

This module adheres to our Architecture-First mandate by centralizing all
cross-workflow orchestration logic in a single Project Manager agent. The
implementation closely follows `docs/architecture/PROJECT_MANAGER_DESIGN.md`
and leverages deepagents for planning, sub-agent delegation, and HITL.

**HITL Strategy (Approval Analyzer)**:
- Runner detects interrupts from department workflows
- Runner invokes approval_analyzer (separate agent) for HITL decisions
- approval_analyzer returns structured BatchApprovalResponse
- Runner builds Command objects and resumes workflow
- PM remains focused on orchestration, not approval logic

This maintains clean separation: PM orchestrates, approval_analyzer decides.
"""

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
    """Return the configured chat model for the Project Manager.

    Follows the Architecture-First rule by centralizing model selection through
    our LLM factory. Default configuration favours gpt-4.1-mini-2025-04-14 with low temperature
    for deterministic planning.
    """

    if model is not None:
        return model
    return get_llm(model="gpt-4.1-mini-2025-04-14", temperature=0.2)


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
    channel: MessagingChannel | None = None,
) -> dict[str, Any]:
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
        channel=channel,  # Pass channel for media download tools
    )

    # Return CompiledSubAgent spec for DeepAgents (v1.0: renamed graph to runnable)
    return {
        "name": "cataloging_department",
        "description": (
            "Handles product cataloging workflows including adding new products, "
            "updating existing products, and batch cataloging. Supports text, images, "
            "videos, and combinations. Returns structured CatalogingResult."
        ),
        "runnable": cataloging_dept_graph,  # v1.0: renamed from graph
    }


def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any,
    storage: StorageInterface,
    channel: MessagingChannel | None = None,
    tools: Sequence[Any] | None = None,
) -> Any:
    """Create the deepagents-powered Project Manager with proper delegation hierarchy.

    Args:
        company_profile: Single-tenant company context required for all workflows.
        model: Optional override for the LLM powering the manager.
        checkpointer: LangGraph checkpointer for durable state (required - provided by runner).
        storage: Storage adapter implementing StorageInterface (required).
        channel: Optional messaging channel for MessageIntentTool (enables agentic message interpretation).
        tools: Optional explicit tool list for PM orchestration only (NOT domain tools).

    Returns:
        Compiled deepagents agent with proper delegation to departments.

    **Architecture**:
    - PM handles intent detection directly (no specialist)
    - PM delegates with media_id (no download tools - keeps PM simple)
    - Departments download media when needed (lazy loading)
    - Departments have domain tools (analyze_image, save_product, download_media)
    - Enforces PM → Department → Specialist → Tools hierarchy
    """

    if checkpointer is None:
        raise ValueError("checkpointer is required for Project Manager (DeepAgents requirement)")

    llm = _resolve_model(model)
    instructions = _load_prompt(company_profile)

    # Get store for long-term memory
    store = get_store()

    # Note: Media download tools NOT included in PM
    # PM delegates media_id to departments, departments download when needed
    # This keeps PM focused on orchestration, not domain operations
    # TodoListMiddleware provides write_todos tool automatically (v1.0)

    # Departments are subagents (proper delegation hierarchy)
    subagents: list[Any] = [
        _create_cataloging_subagent(storage, checkpointer, channel),
    ]

    # Middleware for PM
    # Note: TodoListMiddleware is added by default in create_deep_agent (v1.0)
    # No custom middleware needed for PM currently

    # No interrupt_on needed - departments handle their own HITL
    project_manager = create_deep_agent(
        tools=[],  # PM has orchestration tools (middleware provides write_todos)
        system_prompt=instructions,  # v1.0: renamed from instructions
        model=llm,
        subagents=subagents,
        checkpointer=checkpointer,
        store=store,  # v1.0: Long-term memory store
        use_longterm_memory=True,  # v1.0: Enable persistent cross-session memory
        context_schema=CompanyContext,  # v1.0: Type-safe company context injection
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
