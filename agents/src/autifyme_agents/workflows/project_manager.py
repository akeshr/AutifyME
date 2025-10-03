"""Project Manager agent built on deepagents.

This module adheres to our Architecture-First mandate by centralizing all
cross-workflow orchestration logic in a single Project Manager agent. The
implementation closely follows `docs/architecture/PROJECT_MANAGER_DESIGN.md`
and leverages deepagents for planning, sub-agent delegation, and HITL.
"""

from __future__ import annotations

from typing import Any, Sequence

from deepagents import create_deep_agent
from deepagents.builder import SerializableSubAgent
from deepagents.graph import create_interrupt_hook
from deepagents.tools import write_todos
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import ToolMessage

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.schemas.state import ProjectManagerState
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.tools import registry as tools_registry


_DEFAULT_BUILTIN_TOOLS: list[str] = ["write_todos"]


def _extract_messages(state: Any) -> list[Any]:
    if state is None:
        return []
    if hasattr(state, "messages"):
        return getattr(state, "messages") or []
    return state.get("messages", []) if isinstance(state, dict) else []


def _has_tool_response(messages: list[Any], tool_call_id: str) -> bool:
    for message in messages:
        message_type = getattr(message, "type", None)
        if not message_type and hasattr(message, "__class__"):
            message_type = message.__class__.__name__.replace("Message", "").lower()
        if message_type != "tool":
            continue
        if getattr(message, "tool_call_id", None) == tool_call_id:
            return True
    return False


def _build_post_model_hook(interrupt_config: dict[str, Any] | None):
    interrupt_hook = create_interrupt_hook(interrupt_config or {}) if interrupt_config else None

    def post_model_hook(state: Any) -> dict[str, Any] | None:
        messages = _extract_messages(state)
        if not messages:
            return interrupt_hook(state) if interrupt_hook else None

        updates: dict[str, Any] = {}
        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", None) or []
        auto_messages: list[ToolMessage] = []
        todos_update = None

        for call in tool_calls:
            tool_name = call.get("name") if isinstance(call, dict) else None
            if tool_name != "write_todos":
                continue
            tool_call_id = call.get("id")
            if not tool_call_id or _has_tool_response(messages, tool_call_id):
                continue
            todos_arg = (call.get("args") or {}).get("todos")
            if todos_arg is None:
                continue
            command = write_todos.func(todos=todos_arg, tool_call_id=tool_call_id)
            command_update = getattr(command, "update", {}) or {}
            command_messages = command_update.get("messages") or []
            auto_messages.extend(command_messages)
            if "todos" in command_update:
                todos_update = command_update["todos"]

        if auto_messages:
            updates.setdefault("messages", []).extend(auto_messages)
        if todos_update is not None:
            updates["todos"] = todos_update

        if interrupt_hook is not None:
            interrupt_updates = interrupt_hook(state)
            if interrupt_updates:
                if "messages" in interrupt_updates:
                    updates.setdefault("messages", []).extend(interrupt_updates["messages"])
                for key, value in interrupt_updates.items():
                    if key == "messages":
                        continue
                    updates[key] = value

        return updates or None

    return post_model_hook


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
    """Create the deepagents-powered Project Manager.

    Args:
        company_profile: Single-tenant company context required for all workflows.
        model: Optional override for the LLM powering the manager.
        checkpointer: Optional LangGraph checkpointer for durable state. If not
            provided, the function will create a Postgres-backed saver.
        builtin_tools: Optional subset of deepagents built-ins to enable.

    Returns:
        Compiled deepagents agent ready for invocation.
    """

    llm = _resolve_model(model)
    instructions = _load_prompt(company_profile)

    if storage is None:
        raise ValueError("storage adapter implementing StorageInterface is required")

    cataloging_tools = list(tools) if tools is not None else tools_registry.get_cataloging_tool_objects(storage)

    subagents = _build_subagents(company_profile)

    interrupt_config = tools_registry.get_interrupt_config()

    if checkpointer is None:
        with get_checkpointer() as saver:
            checkpointer = saver

    enabled_builtins = list(builtin_tools) if builtin_tools is not None else _DEFAULT_BUILTIN_TOOLS

    post_model_hook = _build_post_model_hook(interrupt_config)

    project_manager = create_deep_agent(
        tools=cataloging_tools,
        instructions=instructions,
        model=llm,
        subagents=subagents,
        builtin_tools=enabled_builtins,
        interrupt_config=None,
        checkpointer=checkpointer,
        state_schema=ProjectManagerState,
        post_model_hook=post_model_hook,
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
 