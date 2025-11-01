"""
Custom SubAgentMiddleware with response_format support.

Extends DeepAgents' SubAgentMiddleware to support structured outputs via
response_format parameter. Works across all LLM providers (OpenAI, Gemini, Claude).

Architecture:
- Extends SubAgent TypedDict with optional response_format field
- Overrides _get_subagents() to forward response_format to create_agent()
- Maintains full DeepAgents compatibility (middleware, interrupt_on, etc.)

Usage:
    from autifyme_agents.core.structured_subagent_middleware import (
        StructuredSubAgentMiddleware,
        StructuredSubAgent,
    )

    specialist: StructuredSubAgent = {
        "name": "product_specialist",
        "description": "Product architecture expert",
        "system_prompt": load_prompt("specialists/product_specialist.prompt"),
        "tools": tools,
        "response_format": OperationIntent,  # Pydantic model
    }

    middleware = StructuredSubAgentMiddleware(
        default_model=model,
        subagents=[specialist],
    )
"""

from collections.abc import Callable, Sequence
from typing import Any, TypedDict

from deepagents.middleware.subagents import (
    CompiledSubAgent,
    SubAgentMiddleware,
    TASK_SYSTEM_PROMPT,
    _create_task_tool,
)
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, InterruptOnConfig
from langchain.agents.middleware.types import AgentMiddleware
from langchain.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel
from typing_extensions import NotRequired


# =============================================================================
# Extended SubAgent TypedDict with response_format Support
# =============================================================================


class StructuredSubAgent(TypedDict):
    """
    Extended SubAgent specification with structured output support.

    Adds optional response_format field to DeepAgents' standard SubAgent TypedDict.
    All other fields maintain compatibility with DeepAgents architecture.

    Fields:
        name: Unique identifier for the subagent
        description: Delegation criteria (used in task tool docs)
        system_prompt: Agent's system instructions
        tools: Available tools for this subagent
        model: (Optional) Model override (defaults to default_model)
        middleware: (Optional) Additional middleware after default_middleware
        interrupt_on: (Optional) HITL tool configuration
        response_format: (Optional) Pydantic model for structured output

    Provider Compatibility:
        - OpenAI: Uses native json_schema mode (strict=True)
        - Anthropic: Uses function calling / tool-based approach
        - Google Gemini: Uses function calling or responseSchema

    Example:
        specialist: StructuredSubAgent = {
            "name": "data_analyzer",
            "description": "Analyzes data and returns structured results",
            "system_prompt": "You are a data analysis specialist...",
            "tools": [query_db, calculate],
            "response_format": AnalysisReport,  # Pydantic BaseModel
        }
    """

    name: str
    """The name of the agent."""

    description: str
    """The description of the agent (delegation criteria)."""

    system_prompt: str
    """The system prompt to use for the agent."""

    tools: Sequence[BaseTool | Callable | dict[str, Any]]
    """The tools to use for the agent."""

    model: NotRequired[str | BaseChatModel]
    """The model for the agent. Defaults to default_model."""

    middleware: NotRequired[list[AgentMiddleware]]
    """Additional middleware to append after default_middleware."""

    interrupt_on: NotRequired[dict[str, bool | InterruptOnConfig]]
    """The tool configs to use for the agent (HITL configuration)."""

    response_format: NotRequired[type[BaseModel]]
    """
    Pydantic model for structured output (NEW FIELD).

    When provided, the subagent will return responses matching this Pydantic schema
    instead of free-form text. Uses LangChain's create_agent response_format parameter,
    which works across all major providers.

    Example:
        class Report(BaseModel):
            summary: str
            findings: list[str]
            confidence: float

        specialist["response_format"] = Report
    """


# =============================================================================
# Structured SubAgent Creation Logic
# =============================================================================


def _get_structured_subagents(
    *,
    default_model: str | BaseChatModel,
    default_tools: Sequence[BaseTool | Callable | dict[str, Any]],
    default_middleware: list[AgentMiddleware] | None,
    default_interrupt_on: dict[str, bool | InterruptOnConfig] | None,
    subagents: list[StructuredSubAgent | CompiledSubAgent],
    general_purpose_agent: bool,
    default_general_purpose_description: str,
) -> tuple[dict[str, Any], list[str]]:
    """
    Create subagent instances from StructuredSubAgent specifications.

    Enhanced version of DeepAgents' _get_subagents() that forwards response_format
    parameter to create_agent(). Maintains full DeepAgents compatibility.

    Args:
        default_model: Default model for subagents that don't specify one.
        default_tools: Default tools for subagents that don't specify tools.
        default_middleware: Middleware to apply to all subagents. If None,
            no default middleware is applied.
        default_interrupt_on: The tool configs to use for the default general-purpose
            subagent. These are also the fallback for any subagents that don't
            specify their own tool configs.
        subagents: List of StructuredSubAgent specifications or pre-compiled agents.
        general_purpose_agent: Whether to include a general-purpose subagent.
        default_general_purpose_description: Description for general-purpose agent.

    Returns:
        Tuple of (agent_dict, description_list) where agent_dict maps agent names
        to runnable instances and description_list contains formatted descriptions.
    """
    # Use empty list if None (no default middleware)
    default_subagent_middleware = default_middleware or []

    agents: dict[str, Any] = {}
    subagent_descriptions = []

    # Create general-purpose agent if enabled (no structured output by default)
    if general_purpose_agent:
        from deepagents.middleware.subagents import DEFAULT_SUBAGENT_PROMPT

        general_purpose_middleware = [*default_subagent_middleware]
        if default_interrupt_on:
            general_purpose_middleware.append(
                HumanInTheLoopMiddleware(interrupt_on=default_interrupt_on)
            )
        general_purpose_subagent = create_agent(
            default_model,
            system_prompt=DEFAULT_SUBAGENT_PROMPT,
            tools=default_tools,
            middleware=general_purpose_middleware,
        )
        agents["general-purpose"] = general_purpose_subagent
        subagent_descriptions.append(f"- general-purpose: {default_general_purpose_description}")

    # Process custom subagents (with response_format support)
    for agent_ in subagents:
        subagent_descriptions.append(f"- {agent_['name']}: {agent_['description']}")

        # CompiledSubAgent path (pre-compiled runnable)
        if "runnable" in agent_:
            from typing import cast
            custom_agent = cast(CompiledSubAgent, agent_)
            agents[custom_agent["name"]] = custom_agent["runnable"]
            continue

        # StructuredSubAgent path (build with response_format)
        _tools = agent_.get("tools", list(default_tools))
        subagent_model = agent_.get("model", default_model)

        # Compose middleware (default + custom)
        _middleware = (
            [*default_subagent_middleware, *agent_["middleware"]]
            if "middleware" in agent_
            else [*default_subagent_middleware]
        )

        # Add HITL middleware if configured
        interrupt_on = agent_.get("interrupt_on", default_interrupt_on)
        if interrupt_on:
            _middleware.append(HumanInTheLoopMiddleware(interrupt_on=interrupt_on))

        # [CRITICAL] Forward response_format if provided
        response_format = agent_.get("response_format", None)

        agents[agent_["name"]] = create_agent(
            subagent_model,
            system_prompt=agent_["system_prompt"],
            tools=_tools,
            middleware=_middleware,
            response_format=response_format,  # NEW: Forward to create_agent
            checkpointer=False,
        )

    return agents, subagent_descriptions


# =============================================================================
# Structured SubAgent Middleware
# =============================================================================


class StructuredSubAgentMiddleware(SubAgentMiddleware):
    """
    SubAgentMiddleware with response_format support for structured outputs.

    Drop-in replacement for DeepAgents' SubAgentMiddleware that adds support for
    Pydantic-based structured outputs via response_format parameter. Works across
    all LLM providers (OpenAI, Anthropic, Google Gemini).

    Key Enhancement:
        - Accepts StructuredSubAgent specifications with optional response_format field
        - Forwards response_format to LangChain's create_agent()
        - Maintains full DeepAgents compatibility (middleware, tools, HITL, etc.)

    Provider Implementation:
        - OpenAI: Uses native json_schema with strict=True (most reliable)
        - Anthropic Claude: Uses tool calling / function calling approach
        - Google Gemini: Uses function calling or responseSchema
        - LangChain handles provider-specific differences automatically

    Args:
        default_model: The model to use for subagents.
            Can be a LanguageModelLike or a dict for init_chat_model.
        default_tools: The tools to use for the default general-purpose subagent.
        default_middleware: Default middleware to apply to all subagents. If None (default),
            no default middleware is applied. Pass a list to specify custom middleware.
        default_interrupt_on: The tool configs to use for the default general-purpose subagent.
            These are also the fallback for any subagents that don't specify their own tool configs.
        subagents: A list of StructuredSubAgent specifications (with optional response_format).
        system_prompt: Full system prompt override. When provided, completely replaces
            the agent's system prompt. Defaults to TASK_SYSTEM_PROMPT.
        general_purpose_agent: Whether to include the general-purpose agent. Defaults to True.
        task_description: Custom description for the task tool. If None, uses the
            default description template.

    Example:
        ```python
        from pydantic import BaseModel, Field
        from autifyme_agents.core.structured_subagent_middleware import (
            StructuredSubAgentMiddleware,
            StructuredSubAgent,
        )

        class AnalysisReport(BaseModel):
            summary: str = Field(description="Brief summary")
            findings: list[str] = Field(description="Key findings")
            confidence: float = Field(description="Confidence score 0-1")

        specialist: StructuredSubAgent = {
            "name": "data_analyst",
            "description": "Analyzes data and returns structured reports",
            "system_prompt": "You are a data analysis expert...",
            "tools": [query_tool, calculate_tool],
            "response_format": AnalysisReport,  # Pydantic model
        }

        middleware = StructuredSubAgentMiddleware(
            default_model="openai:gpt-4o",
            subagents=[specialist],
        )

        # Use in agent
        agent = create_deep_agent(
            model="openai:gpt-4o",
            middleware=[middleware],
        )
        ```

    Cross-Provider Compatibility:
        This middleware works with any LLM provider supported by LangChain.
        The underlying implementation (json_schema, function calling, etc.) is
        automatically selected by LangChain based on provider capabilities.
    """

    def __init__(
        self,
        *,
        default_model: str | BaseChatModel,
        default_tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
        default_middleware: list[AgentMiddleware] | None = None,
        default_interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
        subagents: list[StructuredSubAgent | CompiledSubAgent] | None = None,
        system_prompt: str | None = TASK_SYSTEM_PROMPT,
        general_purpose_agent: bool = True,
        task_description: str | None = None,
    ) -> None:
        """Initialize the StructuredSubAgentMiddleware."""
        # Store configuration (same as parent)
        self.system_prompt = system_prompt

        # Import here to avoid circular dependency
        from deepagents.middleware.subagents import DEFAULT_GENERAL_PURPOSE_DESCRIPTION

        # Create task tool with our enhanced _get_structured_subagents
        task_tool = _create_task_tool(
            default_model=default_model,
            default_tools=default_tools or [],
            default_middleware=default_middleware,
            default_interrupt_on=default_interrupt_on,
            subagents=subagents or [],
            general_purpose_agent=general_purpose_agent,
            task_description=task_description,
        )

        # PATCH: Replace task tool's subagent creation logic
        # We need to recreate task tool with our _get_structured_subagents
        # This is a workaround since _create_task_tool calls the original _get_subagents

        # Get subagent graphs using our enhanced function
        subagent_graphs, subagent_descriptions = _get_structured_subagents(
            default_model=default_model,
            default_tools=default_tools or [],
            default_middleware=default_middleware,
            default_interrupt_on=default_interrupt_on,
            subagents=subagents or [],
            general_purpose_agent=general_purpose_agent,
            default_general_purpose_description=DEFAULT_GENERAL_PURPOSE_DESCRIPTION,
        )

        # Recreate task tool with our subagent graphs
        # Import the task creation logic
        from deepagents.middleware.subagents import (
            TASK_TOOL_DESCRIPTION,
            _EXCLUDED_STATE_KEYS,
        )
        from langchain.tools import ToolRuntime
        from langchain_core.messages import HumanMessage, ToolMessage
        from langchain_core.tools import StructuredTool
        from langgraph.types import Command

        subagent_description_str = "\n".join(subagent_descriptions)

        # Use custom description if provided, otherwise use default template
        if task_description is None:
            task_description_final = TASK_TOOL_DESCRIPTION.format(
                available_agents=subagent_description_str
            )
        elif "{available_agents}" in task_description:
            task_description_final = task_description.format(
                available_agents=subagent_description_str
            )
        else:
            task_description_final = task_description

        def _return_command_with_state_update(result: dict, tool_call_id: str) -> Command:
            state_update = {k: v for k, v in result.items() if k not in _EXCLUDED_STATE_KEYS}
            return Command(
                update={
                    **state_update,
                    "messages": [ToolMessage(result["messages"][-1].content, tool_call_id=tool_call_id)],
                }
            )

        def _validate_and_prepare_state(subagent_type: str, description: str, runtime: ToolRuntime):
            """Validate subagent type and prepare state for invocation."""
            if subagent_type not in subagent_graphs:
                allowed_types = [f'`{k}`' for k in subagent_graphs]
                msg = f"Error: invoked agent of type {subagent_type}, the only allowed types are {allowed_types}"
                raise ValueError(msg)
            subagent = subagent_graphs[subagent_type]
            # Create a new state dict to avoid mutating the original
            subagent_state = {k: v for k, v in runtime.state.items() if k not in _EXCLUDED_STATE_KEYS}
            subagent_state["messages"] = [HumanMessage(content=description)]
            return subagent, subagent_state

        def task(
            description: str,
            subagent_type: str,
            runtime: ToolRuntime,
        ) -> str | Command:
            subagent, subagent_state = _validate_and_prepare_state(subagent_type, description, runtime)
            result = subagent.invoke(subagent_state)
            if not runtime.tool_call_id:
                value_error_msg = "Tool call ID is required for subagent invocation"
                raise ValueError(value_error_msg)
            return _return_command_with_state_update(result, runtime.tool_call_id)

        async def atask(
            description: str,
            subagent_type: str,
            runtime: ToolRuntime,
        ) -> str | Command:
            subagent, subagent_state = _validate_and_prepare_state(subagent_type, description, runtime)
            result = await subagent.ainvoke(subagent_state)
            if not runtime.tool_call_id:
                value_error_msg = "Tool call ID is required for subagent invocation"
                raise ValueError(value_error_msg)
            return _return_command_with_state_update(result, runtime.tool_call_id)

        self.tools = [
            StructuredTool.from_function(
                name="task",
                func=task,
                coroutine=atask,
                description=task_description_final,
            )
        ]
