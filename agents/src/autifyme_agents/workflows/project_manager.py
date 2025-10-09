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
from langchain_core.language_models.chat_models import BaseChatModel

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


def _create_department_tools(
    company_profile: CompanyProfile,
    storage: StorageInterface,
    checkpointer: Any,
) -> list:
    """Create tools that wrap full department agents.

    Each department is a complete LangChain agent with middleware, HITL, and
    checkpointing. We wrap these agents as tools so the PM can invoke them via
    standard tool calling, preserving all department capabilities.

    This is the correct architecture: PM calls department tools, departments execute
    their workflows with full middleware stack, and return structured results to PM.
    """

    from langchain_core.tools import tool
    from autifyme_agents.departments.cataloging_department import create_cataloging_department

    # Create FULL department agent with middleware, HITL, checkpointing
    cataloging_dept_agent = create_cataloging_department(
        checkpointer=checkpointer,
        storage=storage,
        enable_hitl=True,
    )

    @tool("cataloging_department")
    def invoke_cataloging_department(task_description: str) -> dict:
        """Handle product cataloging workflows.

        Use this tool when user provides product information (text, images, videos, or
        combinations). Supports single products, batch cataloging, and product updates.

        Args:
            task_description: Semantic description of what user wants (include text,
                mention media attachments, relevant context like prices/sizes)

        Returns:
            Structured cataloging result with product details
        """
        from langchain_core.messages import HumanMessage

        # Invoke department agent with task description
        result = cataloging_dept_agent.invoke(
            {"messages": [HumanMessage(content=task_description)]},
            config={"configurable": {"thread_id": f"dept_{hash(task_description) % 100000}"}},
        )

        # Extract structured result or summary
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            content = getattr(last_message, "content", str(last_message))
            return {"success": True, "result": content}

        return {"success": False, "error": "Department returned no result"}

    return [invoke_cataloging_department]


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

    llm = _resolve_model(model)
    instructions = _load_prompt(company_profile)

    # PM gets department tools (which wrap full agents) + any additional orchestration tools
    pm_tools = list(tools) if tools is not None else []
    pm_tools.extend(_create_department_tools(company_profile, storage, checkpointer))

    # No subagents - departments are invoked as tools
    subagents = []

    # No tool_configs needed - departments handle their own HITL via middleware
    tool_configs = {}

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
 