"""Cataloging Department as DeepAgent with specialist subagents.

Department coordinates specialist subagents to gather product information,
structure it into Product models, and persist to the database.

Architecture (Correct Hierarchy):
- Department: DeepAgent (coordinates workflow)
- Specialists: SubAgents that perform focused transformations
  - image_analysis_specialist: Vision analysis → ImageAnalysisResult
  - cataloging_specialist: Product extraction → Product
- Tools: Utility functions only
  - save_product: Database persistence
  - write_todos: Planning
"""

from typing import Any

from deepagents import create_deep_agent  # type: ignore[import-untyped]
from deepagents.tools import write_todos  # type: ignore[import-untyped]
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain.agents.middleware.human_in_the_loop import ToolConfig

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.core.middleware import CompanyContextMiddleware
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.tools import create_save_product_tool
from autifyme_agents.specialists.image_analysis_specialist import create_image_analysis_specialist
from autifyme_agents.specialists.cataloging_specialist import create_cataloging_specialist
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.schemas.models import Product


def create_cataloging_department(
    checkpointer: BaseCheckpointSaver,
    storage: StorageInterface,
    channel: Any | None = None,
) -> Any:
    """Create cataloging department as DeepAgent with specialist subagents.

    Args:
        checkpointer: LangGraph checkpoint saver for state persistence
        storage: Storage adapter for company profile and products
        channel: Optional messaging channel for media download

    Returns:
        DeepAgent that coordinates specialist subagents and handles product cataloging
    """

    if storage is None:
        raise ValueError("storage adapter required")

    llm = get_llm()

    # TOOLS: Only utility functions, not specialists
    tools = [
        write_todos,  # Planning tool for multi-step coordination
        create_save_product_tool(storage),  # Database persistence
    ]

    # Add platform media download tools if channel provided
    if channel is not None:
        from autifyme_agents.tools.platform_tools import create_platform_media_tools
        platform_tools = create_platform_media_tools(channel)
        tools.extend(platform_tools)

    # SUBAGENTS: Specialists that perform focused transformations
    # Using DeepAgents SubAgent pattern (not CustomSubAgent)
    # IMPORTANT: Explicitly set tools=[] to prevent inheriting parent tools
    subagents = [
        {
            "name": "image_analysis_specialist",
            "description": (
                "Analyze product images to extract visual attributes including colors, "
                "materials, style, and features. Returns ImageAnalysisResult with "
                "visual_description, identified_colors, and style_tags."
            ),
            "response_format": ImageAnalysisResult,  # Structured output
            "prompt": load_prompt("specialists/image_analysis_specialist.prompt"),
            "tools": [],  # ✅ Explicitly no tools - pure vision analysis
        },
        {
            "name": "cataloging_specialist",
            "description": (
                "Transform user descriptions and optional image insights into complete "
                "Product models. Synthesizes information, fills reasonable gaps, ensures "
                "brand alignment. Returns Product with all catalog fields."
            ),
            "response_format": Product,  # Structured output
            "prompt": load_prompt("specialists/cataloging_specialist.prompt"),
            "tools": [],  # ✅ Explicitly no tools - pure synthesis
        },
    ]

    # Department's middleware stack
    middleware: list[Any] = [
        CompanyContextMiddleware(storage),  # Inject company context
    ]

    # Load department instructions
    instructions = load_prompt("departments/cataloging_department.prompt")

    # Configure HITL for save_product tool
    tool_configs = {
        "save_product": ToolConfig(
            allow_accept=True,
            allow_edit=True,
            allow_respond=True,
            description="Please review this product before saving to the catalog database."
        )
    }

    # Create DeepAgent department with proper hierarchy
    department = create_deep_agent(
        model=llm,
        instructions=instructions,
        tools=tools,  # ✅ Only utilities
        subagents=subagents,  # ✅ Specialists as subagents
        middleware=middleware,
        checkpointer=checkpointer,
        tool_configs=tool_configs,
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
