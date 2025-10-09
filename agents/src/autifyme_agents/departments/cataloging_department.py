"""Cataloging Department agent.

The department adheres to the architecture mandate of delegating to Specialist
agents which in turn rely on deterministic tools. This module wires together
the specialists, wraps them as LangChain tools, and exposes a Department Head
agent with structured outputs for upstream orchestration.
"""

from typing import Annotated, Sequence, TypedDict, Union, Any
import operator

from langchain.agents import create_agent

from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    SummarizationMiddleware,
    AnthropicPromptCachingMiddleware,
)
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langchain.tools import tool
from langgraph.checkpoint.base import BaseCheckpointSaver

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.specialists.cataloging_specialist import create_cataloging_specialist
from autifyme_agents.specialists.image_analysis_specialist import create_image_analysis_specialist
from autifyme_agents.tools import create_save_product_tool
from autifyme_agents.core.middleware import CompanyContextMiddleware
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.schemas.models import CatalogingResult, Product
from autifyme_agents.schemas.context import AgentContext

# Use Union instead of BaseMessage to avoid langchain_core where possible
MessageType = Union[HumanMessage, SystemMessage, AIMessage]


class AgentState(TypedDict):
    messages: Annotated[Sequence[MessageType], operator.add]


def create_cataloging_department(
    checkpointer: BaseCheckpointSaver,
    storage: StorageInterface,
    *,
    enable_hitl: bool = True,
) -> Any:
    """Build the cataloging department head agent with specialist delegation.

    Args:
        checkpointer: LangGraph checkpoint saver for state persistence.
        storage: Concrete implementation of the storage port.
        enable_hitl: When False, skip human approval middleware (used in fast tests).

    Returns:
        A runnable department agent that produces a `CatalogingResult`.
    """
    if storage is None:
        raise ValueError("storage adapter must be provided and implement StorageInterface")

    image_specialist = create_image_analysis_specialist()
    cataloging_specialist = create_cataloging_specialist()

    # Get company profile once for all tools
    company_profile = storage.get_company_profile()

    @tool("image_analysis_specialist")
    def image_analysis_tool(image_url: str, *, config=None) -> ImageAnalysisResult:
        """Analyze an image to produce structured product insights."""
        payload = {
            "input": {
                "image_url": image_url,
                "company_profile": company_profile,
            }
        }
        return image_specialist.invoke(payload, config=config)

    @tool("cataloging_specialist")
    def cataloging_tool(
        user_message: str,
        image_analysis: dict | None = None,
        *,
        config=None,
    ) -> Product:
        """Combine user instructions and optional image analysis into a Product."""
        parsed_insights = None
        if image_analysis is not None:
            parsed_insights = ImageAnalysisResult.model_validate(image_analysis)

        payload = {
            "input": {
                "user_message": user_message,
                "image_analysis": parsed_insights.model_dump(mode="json") if parsed_insights else None,
            }
        }
        return cataloging_specialist.invoke(payload, config=config)

    tools = [
        image_analysis_tool,
        cataloging_tool,
        create_save_product_tool(storage),
    ]

    prompt = load_prompt("departments/cataloging_department.prompt")

    llm = get_llm()

    # Middleware stack (applied in order):
    # 1. Company Context - inject company profile into tool calls
    # 2. HITL - interrupt on save_product for approval (optional)
    # 3. Prompt Caching - reduce API costs for repeated calls
    # 4. Summarization - handle long conversations gracefully
    middleware: list[Any] = [CompanyContextMiddleware(storage)]

    if enable_hitl:
        middleware.append(
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "save_product": {
                        "allow_accept": True,
                        "allow_edit": True,
                        "allow_respond": True,
                        "description": "Approve or modify the product before it is persisted to storage.",
                    }
                },
                description_prefix="Department HITL",
            )
        )

    # Anthropic prompt caching - 5min TTL, cache after 2 messages
    middleware.append(
        AnthropicPromptCachingMiddleware(
            ttl="5m",
            min_messages_to_cache=2,
            unsupported_model_behavior="ignore",
        )
    )

    # Summarization - trigger after 4k tokens, keep last 5 messages
    middleware.append(
        SummarizationMiddleware(
            model=llm,
            max_tokens_before_summary=4000,
            messages_to_keep=5,
        )
    )

    agent_graph = create_agent(  # type: ignore[type-arg]
        llm,
        tools,
        system_prompt=prompt,
        checkpointer=checkpointer,
        context_schema=AgentContext,
        name="CatalogingDepartmentAgent",
        response_format=CatalogingResult,
        middleware=tuple(middleware),
    )

    return agent_graph.with_config({
        "run_name": "CatalogingDepartment",
        "tags": ["department:cataloging", "workflow:Cataloging"],
        "metadata": {
            "department": "cataloging",
            "workflow": "Cataloging",
            "agent_type": "department_head",
        },
    })
