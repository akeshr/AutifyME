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

from deepagents import create_deep_agent
from langchain.agents.middleware.human_in_the_loop import InterruptOnConfig
from langchain.agents.structured_output import ToolStrategy
from langgraph.checkpoint.base import BaseCheckpointSaver

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.middleware import CompanyContextMiddleware
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.integrations.storage import get_store
from autifyme_agents.schemas.context import CompanyContext
from autifyme_agents.schemas.models import Product
from autifyme_agents.specialists.image_analysis_specialist import (
    create_image_analysis_specialist_graph,
)
from autifyme_agents.tools import create_save_product_tool


def create_cataloging_department(
    checkpointer: BaseCheckpointSaver[Any],
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

    # Get store for long-term memory
    store = get_store()

    # Get company profile for brand-aware specialist configuration
    company_profile = storage.get_company_profile()

    # TOOLS: Only utility functions, not specialists
    # Note: write_todos now provided by TodoListMiddleware in v1.0
    tools = [
        create_save_product_tool(storage),  # Database persistence
    ]

    # Add platform media download tools if channel provided
    if channel is not None:
        from autifyme_agents.tools.platform_tools import create_platform_media_tools
        platform_tools = create_platform_media_tools(channel)
        tools.extend(platform_tools)

    # SUBAGENTS: Specialists that perform focused transformations
    # ARCHITECTURE: Using CompiledSubAgent for image specialist to bypass virtual filesystem
    # DeepAgents SubAgent pattern injects default filesystem tools that conflict with real OS files
    subagents = [
        # CompiledSubAgent: Pre-built graph with full control (no tool injection)
        # v1.0: renamed 'graph' to 'runnable'
        {
            "name": "image_analysis_specialist",
            "description": (
                "Analyze product images to extract visual attributes including colors, "
                "materials, style, and features. Provide the file path in your delegation "
                "message (e.g., 'Analyze /tmp/media_downloads/xyz.jpg'). Returns "
                "ImageAnalysisResult with visual_description, identified_colors, and style_tags."
            ),
            "runnable": create_image_analysis_specialist_graph(company_profile),  # v1.0: renamed from graph
        },
        # SubAgent: Simple spec-based (no file access needed)
        {
            "name": "cataloging_specialist",
            "description": (
                "Transform user descriptions and optional image insights into complete "
                "Product models. Synthesizes information, fills reasonable gaps, ensures "
                "brand alignment. Returns Product with all catalog fields."
            ),
            "response_format": ToolStrategy(
                schema=Product,
                handle_errors=True  # v1.0: Self-healing structured outputs
            ),
            "system_prompt": load_prompt("specialists/cataloging_specialist.prompt"),  # v1.0: renamed from prompt
            "tools": [],  # ✅ No tools - pure synthesis
            "middleware": [],  # ✅ Disable default middleware (filesystem, write_todos)
        },
    ]

    # Department's middleware stack
    # Note: TodoListMiddleware is added by default in create_deep_agent (v1.0)
    middleware: list[Any] = [
        CompanyContextMiddleware(storage),  # Inject company context
    ]

    # Load department instructions
    instructions = load_prompt("departments/cataloging_department.prompt")

    # Configure HITL for save_product tool (v1.0 uses interrupt_on parameter)
    interrupt_config = {
        "save_product": InterruptOnConfig(
            allowed_decisions=["approve", "edit", "reject"],
            description="Please review this product before saving to the catalog database."
        )
    }

    # Create DeepAgent department with proper hierarchy
    department = create_deep_agent(
        model=llm,
        system_prompt=instructions,  # v1.0: renamed from instructions
        tools=tools,  # ✅ Only utilities
        subagents=subagents,  # ✅ Specialists as subagents
        middleware=middleware,
        checkpointer=checkpointer,
        store=store,  # v1.0: Long-term memory store
        use_longterm_memory=True,  # v1.0: Enable persistent cross-session memory
        context_schema=CompanyContext,  # v1.0: Type-safe company context injection
        interrupt_on=interrupt_config,  # v1.0: renamed from tool_configs
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
