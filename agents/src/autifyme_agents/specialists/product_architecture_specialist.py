"""
Product Architecture Specialist - Schema-driven CRUD with autonomous research.

Domain Expertise:
- Product structure analysis (family vs variants)
- Variant axis identification (dimensions that vary: size, color, material, etc.)
- SKU architecture design (naming conventions, combinations)
- Intelligent catalog matching for autonomous create vs update decisions
- Schema-driven operation planning (queries schema, generates execution plans)
- Web research for product enrichment (specs, pricing, competitive analysis)
- Visual attribute extraction from product images
- Autonomous data enrichment (handles minimal user input intelligently)

Responsibilities:
- Query product catalog schema dynamically
- Search catalog for existing product families
- Classify user intent into CRUD operations
- Generate operation specifications with execution plans
- Calculate impact analysis from schema + current data
- Research product information via web search (Tavily API)
- Extract content from specific URLs (manufacturer sites, spec sheets)
- Analyze product images for visual attributes (materials, colors, dimensions)
- Enrich minimal user data autonomously (no hand-holding needed)

Does NOT:
- Persist to database (PM handles persistence via universal tool)
- Generate marketing content (Content Specialist handles this)
- Classify into taxonomy (Taxonomy Specialist handles this)

Architecture Pattern:
- SubAgent spec: Standard dict format for PM delegation
- Returns dict with {name, description, tools, system_prompt}
- DeepAgents compiles specialist automatically in PM
- Schema-driven planning (no hard-coded operation types)
- Intelligence-first: trusts specialist to research and enrich autonomously
"""

from typing import Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool
from autifyme_agents.tools.research_tools import (
    extract_web_content_tool,
    research_product_tool,
)

# =============================================================================
# Specialist Factory
# =============================================================================


def create_product_architecture_specialist(
    storage: StorageInterface,
    model: str | BaseChatModel | None = None,
) -> dict[str, Any]:
    """
    Create Product Architecture Specialist SubAgent spec.

    Standard SubAgent Pattern: Returns dict for PM's subagents list.

    Specialist Responsibilities:
    - Query product catalog schema dynamically
    - Search catalog for existing product families
    - Classify user intent (create/read/update/delete)
    - Generate operation specifications with execution plans
    - Calculate impact analysis from schema + data
    - Research product information via web (Tavily API)
    - Extract content from URLs (manufacturer sites, spec sheets)
    - Analyze product images for visual attributes
    - Enrich minimal user data autonomously
    - Maintain conversation history across PM delegations

    Architecture:
    - SubAgent dict: {name, description, tools, system_prompt, model (optional)}
    - DeepAgents compiles specialist with specified model or default_model from PM
    - Schema-driven planning (no hard-coded operation types)
    - Intelligence-first: autonomous research and enrichment
    - PM handles persistence via execute_database_operation tool

    Args:
        storage: Storage interface for catalog search + schema query (REQUIRED)
        model: Optional model (string or LLM instance).
               - String: "google:gemini-2.5-pro", "openai:gpt-4o"
               - LLM instance: Pre-configured BaseChatModel with custom temperature/thinking_budget
               - None: Uses PM's default_model from SubAgentMiddleware

    Returns:
        SubAgent spec dict for PM's subagents list

    Notes:
        - Standard SubAgent pattern (like cataloging_specialist)
        - DeepAgents handles model compilation, checkpointer, middleware
        - Specialist focused on analysis, research, and planning
        - PM delegates execution and approval
    """
    if storage is None:
        raise ValueError(
            "storage is required for Product Architecture Specialist (tools dependency)"
        )

    # Load specialist prompt
    system_prompt = load_prompt("specialists/product_architecture_specialist.prompt")

    # Core tools
    tools: list[Any] = [
        image_analysis_tool,
        research_product_tool,       # Web research for product enrichment
        extract_web_content_tool,    # Deep content extraction from URLs
    ]

    # Schema query tools (for dynamic planning)
    from autifyme_agents.tools.schema_tools import (
        get_product_schema,
        get_table_schema,
        list_available_tables,
    )

    tools.extend([get_product_schema, get_table_schema, list_available_tables])

    # Storage-dependent tools
    from autifyme_agents.tools.product_search_tools import (
        create_search_product_families_tool,
    )
    from autifyme_agents.tools.query_database_tool import (
        create_query_database_tool,
    )

    tools.append(create_search_product_families_tool(storage))
    tools.append(create_query_database_tool(storage))

    # Description for PM delegation (routing decisions)
    description = (
        "Product architecture specialist with schema-driven CRUD and autonomous research. "
        "Core capabilities: analyzes product structure, queries schemas dynamically, "
        "searches catalog for existing products, generates operation specifications with execution plans. "
        "Research capabilities: web search for product specs/pricing/competitive analysis (Tavily), "
        "extracts content from URLs (manufacturer sites, spec sheets), "
        "analyzes product images for visual attributes (materials, colors, dimensions, condition). "
        "Intelligence: handles minimal user data autonomously (researches to fill gaps), "
        "enriches product information without hand-holding. "
        "Returns detailed operation plans for PM to execute via execute_database_operation tool."
    )

    # Return SubAgent spec
    spec: dict[str, Any] = {
        "name": "product_architecture_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        # No interrupt_on - specialist has no HITL tools
    }

    # Add model if specified (otherwise uses PM's default_model)
    if model is not None:
        spec["model"] = model

    return spec
