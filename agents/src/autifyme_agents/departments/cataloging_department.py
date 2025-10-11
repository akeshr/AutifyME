"""Cataloging Department as DeepAgent with specialist tools.

Department coordinates specialists (as tools) to gather product information,
structure it into Product models, and persist to the database.

Architecture:
- Department: DeepAgent (coordinates workflow)
- Specialists: Tools that return structured data (ImageAnalysisResult, Product)
- Persistence: save_product tool writes to database
"""

from typing import Any

from deepagents import create_deep_agent  # type: ignore[import-untyped]
from langgraph.checkpoint.base import BaseCheckpointSaver

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.core.middleware import CompanyContextMiddleware
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.tools import create_save_product_tool
from autifyme_agents.tools.cataloging_tools import (
    create_cataloging_specialist_tool,
    create_image_analysis_tool,
)


def create_cataloging_department(
    checkpointer: BaseCheckpointSaver,
    storage: StorageInterface,
) -> Any:
    """Create cataloging department as DeepAgent with specialist tools.

    Args:
        checkpointer: LangGraph checkpoint saver for state persistence
        storage: Storage adapter for company profile and products

    Returns:
        DeepAgent that coordinates specialists and handles product cataloging
    """

    if storage is None:
        raise ValueError("storage adapter required")

    llm = get_llm()

    # Department's tools - all specialists are now regular tools that return structured data
    # This allows the LLM to access Product fields directly and call save_product properly
    tools = [
        create_image_analysis_tool(storage),  # Returns ImageAnalysisResult directly
        create_cataloging_specialist_tool(storage),  # Returns Product directly
        create_save_product_tool(storage),  # Accepts individual Product fields
    ]

    # Department's middleware stack
    # Note: create_deep_agent automatically adds caching and summarization
    # HITL approval happens at the draft stage via channel.send_approval_request()
    middleware: list[Any] = [
        CompanyContextMiddleware(storage),  # Inject company context
    ]

    # Load department instructions
    instructions = load_prompt("departments/cataloging_department.prompt")

    # Create DeepAgent department
    department = create_deep_agent(
        model=llm,
        instructions=instructions,
        tools=tools,  # All specialists are now tools, not subagents
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
