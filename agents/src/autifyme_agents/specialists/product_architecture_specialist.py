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
- Generate OperationIntent with execution plan
- Calculate impact analysis from schema + current data

Does NOT:
- Persist to database (PM handles persistence via universal tool)
- Generate marketing content (Content Specialist handles this)
- Classify into taxonomy (Taxonomy Specialist handles this)

Architecture Pattern:
- CompiledSubAgent pattern with OperationIntent response
- Schema-driven planning (no hard-coded operation types)
- Single generic model (replaces 7 hard-coded draft types)
- Dynamic execution plan generation
"""

from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt

# Import generic operation intent (replaces all hard-coded draft types)
from autifyme_agents.schemas.operation_intent import OperationIntent
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool

# =============================================================================
# Specialist Factory
# =============================================================================


def create_product_architecture_specialist(
    storage: StorageInterface | None = None,
    model: BaseChatModel | None = None,
) -> dict[str, Any]:
    """
    Create Product Architecture Specialist with schema-driven CRUD.

    Specialist Responsibilities:
    - Query product catalog schema dynamically
    - Search catalog for existing product families
    - Classify user intent (create/read/update/delete)
    - Generate OperationIntent with execution plan
    - Calculate impact analysis from schema + data

    Architecture:
    - CompiledSubAgent pattern (manually compiled agent with response_format)
    - OperationIntent response (single generic model)
    - Schema-driven planning (no hard-coded operation types)
    - Dynamic execution plan generation

    Args:
        storage: Storage interface for catalog search + schema query
        model: LLM for specialist (defaults to gemini-2.5-flash-lite)

    Returns:
        CompiledSubAgent spec with:
        - name: specialist identifier
        - description: delegation criteria
        - runnable: Pre-compiled agent with response_format configured
    """
    system_prompt = load_prompt("specialists/product_architecture_specialist.prompt")

    description = (
        "Product architecture specialist with schema-driven CRUD. "
        "Queries schema dynamically, searches catalog, classifies intent, "
        "and generates OperationIntent with execution plan. "
        "Handles any operation on any table through schema-driven planning."
    )

    # Core tools
    tools = [
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
    if storage:
        from autifyme_agents.tools.product_search_tools import (
            create_search_product_families_tool,
        )
        from autifyme_agents.tools.query_database_tool import (
            create_query_database_tool,
        )
        tools.append(create_search_product_families_tool(storage))
        tools.append(create_query_database_tool(storage))

    # Resolve model (default to gemini-2.5-flash-lite for specialist work)
    if model is None:
        model = get_llm(provider="google", model="gemini-2.5-flash-lite", temperature=0.1)

    # [CRITICAL] Manually compile agent with response_format
    # DeepAgents SubAgent dict does NOT support response_format field
    # Must use create_agent directly to configure structured output
    runnable = create_agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools,
        response_format=OperationIntent,  # Configures with_structured_output()
        checkpointer=False,  # Specialists are stateless
    )

    # Return CompiledSubAgent format (uses runnable instead of individual fields)
    return {
        "name": "product_architecture_specialist",
        "description": description,
        "runnable": runnable,
    }
