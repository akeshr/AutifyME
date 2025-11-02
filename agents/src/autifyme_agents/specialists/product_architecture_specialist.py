"""
Product Architecture Specialist - Dynamic schema-driven CRUD operations.

Domain Expertise:
- Product structure analysis (family vs variants)
- Variant axis identification (dimensions that vary: size, color, material, etc.)
- SKU architecture design (naming conventions, combinations)
- Intelligent catalog matching for autonomous create vs update decisions
- Schema-driven operation planning (queries schema, generates execution plans)

Responsibilities:
- Query product catalog schema dynamically
- Search catalog for existing product families
- Classify user intent into CRUD operations
- Generate operation specifications with execution plans
- Calculate impact analysis from schema + current data

Does NOT:
- Persist to database (PM handles persistence via universal tool)
- Generate marketing content (Content Specialist handles this)
- Classify into taxonomy (Taxonomy Specialist handles this)

Architecture Pattern:
- SubAgent spec: Standard dict format for PM delegation
- Returns dict with {name, description, tools, system_prompt}
- DeepAgents compiles specialist automatically in PM
- Schema-driven planning (no hard-coded operation types)
"""

from typing import Any

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool

# =============================================================================
# Specialist Factory
# =============================================================================


def create_product_architecture_specialist(storage: StorageInterface) -> dict[str, Any]:
    """
    Create Product Architecture Specialist SubAgent spec.

    Standard SubAgent Pattern: Returns dict for PM's subagents list.

    Specialist Responsibilities:
    - Query product catalog schema dynamically
    - Search catalog for existing product families
    - Classify user intent (create/read/update/delete)
    - Generate operation specifications with execution plans
    - Calculate impact analysis from schema + data
    - Maintain conversation history across PM delegations

    Architecture:
    - SubAgent dict: {name, description, tools, system_prompt}
    - DeepAgents compiles specialist with default_model from PM
    - Schema-driven planning (no hard-coded operation types)
    - PM handles persistence via execute_database_operation tool

    Args:
        storage: Storage interface for catalog search + schema query (REQUIRED)

    Returns:
        SubAgent spec dict for PM's subagents list

    Notes:
        - Standard SubAgent pattern (like cataloging_specialist)
        - DeepAgents handles model, checkpointer, middleware
        - Specialist focused on analysis and planning only
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

    # Description for PM delegation
    description = (
        "Product architecture specialist with schema-driven CRUD capabilities. "
        "Analyzes product structure, queries schemas dynamically, "
        "searches catalog for existing products, and generates "
        "operation specifications with execution plans and impact analysis. "
        "Handles any CRUD operation on any table through schema-driven planning. "
        "Returns detailed operation plans for PM to execute via execute_database_operation tool."
    )

    # Return SubAgent spec
    return {
        "name": "product_architecture_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        # No interrupt_on - specialist has no HITL tools
        # DeepAgents handles model and checkpointer configuration
    }
