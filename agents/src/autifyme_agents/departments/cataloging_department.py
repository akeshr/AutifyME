"""Cataloging Department as DeepAgent with specialist subagents.

Department coordinates specialists via task delegation and handles
final product persistence with HITL approval.

Architecture:
- Department: DeepAgent (can plan specialist coordination)
- Specialists: CustomSubAgents (pre-built create_agent graphs)
- HITL: Department-level middleware for save_product approval
"""

from typing import Any

from deepagents import create_deep_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
)
from langgraph.checkpoint.base import BaseCheckpointSaver

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.core.middleware import CompanyContextMiddleware
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.specialists.cataloging_specialist import create_cataloging_specialist
from autifyme_agents.specialists.image_analysis_specialist import create_image_analysis_specialist
from autifyme_agents.tools import create_save_product_tool


def create_cataloging_department(
    checkpointer: BaseCheckpointSaver,
    storage: StorageInterface,
    *,
    enable_hitl: bool = True,
) -> Any:
    """Create cataloging department as DeepAgent with specialist subagents.

    Args:
        checkpointer: LangGraph checkpoint saver for state persistence
        storage: Storage adapter for company profile and products
        enable_hitl: Enable human-in-the-loop approval for save_product

    Returns:
        DeepAgent that coordinates specialists and handles product cataloging
    """

    if storage is None:
        raise ValueError("storage adapter required")

    llm = get_llm()

    # Specialists as CustomSubAgents (pre-built create_agent graphs)
    # These are stateless - no checkpointing needed at specialist level
    subagents = [
        {
            "name": "image_analysis_specialist",
            "description": "Analyzes product images to extract visual attributes like colors, materials, style, and features",
            "graph": create_image_analysis_specialist(),  # create_agent with response_format
        },
        {
            "name": "cataloging_specialist",
            "description": "Combines user input and image analysis into structured product draft",
            "graph": create_cataloging_specialist(),  # create_agent with response_format
        },
    ]

    # Department's direct tools (not delegated to specialists)
    tools = [
        create_save_product_tool(storage),
    ]

    # Department's middleware stack
    # Note: create_deep_agent automatically adds caching and summarization
    # We only need to add custom middleware here
    middleware: list[Any] = [
        CompanyContextMiddleware(storage),  # Inject company context
    ]

    if enable_hitl:
        middleware.append(
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "save_product": {
                        "allow_accept": True,
                        "allow_edit": True,
                        "allow_respond": True,
                        "description": "Approve product before persisting to catalog",
                    }
                },
                description_prefix="Department HITL",
            )
        )

    # Load department instructions
    instructions = load_prompt("departments/cataloging_department.prompt")

    # Create DeepAgent department
    department = create_deep_agent(
        model=llm,
        instructions=instructions,
        tools=tools,
        subagents=subagents,
        middleware=middleware,
        checkpointer=checkpointer,  # Department-level checkpointing for HITL
    )

    return department.with_config({
        "run_name": "CatalogingDepartment",
        "tags": ["department:cataloging", "workflow:Cataloging"],
        "metadata": {
            "department": "cataloging",
            "workflow": "Cataloging",
            "agent_type": "department_head",
        },
    })
