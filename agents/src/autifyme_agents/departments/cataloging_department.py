"""Cataloging Department agent.

The department adheres to the architecture mandate of delegating to Specialist
agents which in turn rely on deterministic tools. This module wires together
the specialists, wraps them as LangChain tools, and exposes a Department Head
agent with structured outputs for upstream orchestration.
"""

from typing import Annotated, Sequence, TypedDict
import operator

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langgraph.checkpoint.base import BaseCheckpointSaver

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.specialists.cataloging_specialist import create_cataloging_specialist
from autifyme_agents.specialists.image_analysis_specialist import create_image_analysis_specialist
from autifyme_agents.tools import create_save_product_tool
from autifyme_agents.core.middleware import create_company_context_middleware
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.schemas.models import CatalogingResult, Product


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


def create_cataloging_department(
    checkpointer: BaseCheckpointSaver,
    storage: StorageInterface,
) -> Runnable:
    """Build the cataloging department head agent with specialist delegation.

    Args:
        checkpointer: LangGraph checkpoint saver for state persistence.
        storage: Concrete implementation of the storage port.

    Returns:
        A runnable department agent that produces a `CatalogingResult`.
    """
    if storage is None:
        raise ValueError("storage adapter must be provided and implement StorageInterface")

    company_context = create_company_context_middleware(storage)

    image_specialist = create_image_analysis_specialist()
    cataloging_specialist = create_cataloging_specialist()

    @tool("image_analysis_specialist")
    @company_context
    def image_analysis_tool(image_url: str, *, company_profile, config=None) -> ImageAnalysisResult:
        """Analyze an image to produce structured product insights."""

        payload = {
            "input": {
                "image_url": image_url,
                "company_profile": company_profile,
            }
        }
        return image_specialist.invoke(payload, config=config)

    @tool("cataloging_specialist")
    @company_context
    def cataloging_tool(
        user_message: str,
        image_analysis: dict | None = None,
        *,
        company_profile,
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

    custom_instructions = load_prompt("departments/cataloging_department.prompt")

    prompt = ChatPromptTemplate.from_messages([
        ("system", custom_instructions),
        ("placeholder", "{messages}"),
    ])

    llm = get_llm()

    agent_graph = create_agent(
        llm,
        tools,
        prompt=prompt,
        checkpointer=checkpointer,
        name="CatalogingDepartmentAgent",
        response_format=CatalogingResult,
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
