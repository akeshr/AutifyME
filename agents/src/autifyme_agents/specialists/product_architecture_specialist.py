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
- Pattern 3: DeepAgent as subagent (testing nested DeepAgent behavior)
- Returns CompiledStateGraph from create_deep_agent
- Structured output via response_format=OperationIntent
- Schema-driven planning (no hard-coded operation types)
- No nested sub-specialists (clean test of DeepAgent capabilities)
"""

from typing import Any

from deepagents import create_deep_agent
from langgraph.graph.state import CompiledStateGraph

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
    storage: StorageInterface,
    checkpointer: Any,
) -> CompiledStateGraph:
    """
    Create Product Architecture Specialist with schema-driven CRUD.

    Pattern 3: DeepAgent as subagent with shared checkpointer for state persistence.

    Specialist Responsibilities:
    - Query product catalog schema dynamically
    - Search catalog for existing product families
    - Classify user intent (create/read/update/delete)
    - Generate OperationIntent with execution plan
    - Calculate impact analysis from schema + data
    - Maintain conversation history across PM delegations

    Architecture:
    - DeepAgent (create_deep_agent) with structured output
    - response_format: OperationIntent (Pydantic model)
    - Shared checkpointer: Uses PM's checkpointer for state persistence
    - Thread isolation: LangGraph automatically namespaces thread_id for nested agent
    - Schema-driven planning (no hard-coded operation types)
    - No nested sub-specialists (clean Pattern 3 test)

    Args:
        storage: Storage interface for catalog search + schema query (REQUIRED)
        checkpointer: Checkpointer instance from PM (REQUIRED for state persistence)

    Returns:
        CompiledStateGraph: Stateful specialist agent that can be nested as subagent in PM

    Notes:
        - Pattern 3 test: Stateful specialist with shared checkpointer
        - Specialist maintains domain knowledge across delegations
        - LangGraph handles thread_id namespacing automatically
        - Single checkpointer simplifies state management
        - Includes default file tools + todo tool (DeepAgent behavior)
        - SubAgentMiddleware excluded (cannot spawn dynamic subagents)
    """
    if storage is None:
        raise ValueError(
            "storage is required for Product Architecture Specialist (tools dependency)"
        )

    if checkpointer is None:
        raise ValueError(
            "checkpointer is required for Product Architecture Specialist (state persistence)"
        )

    # Load specialist prompt
    system_prompt = load_prompt("specialists/product_architecture_specialist.prompt")

    # Model configuration - use Gemini for specialist-level reasoning
    model = get_llm(
        provider="google",
        model="gemini-2.5-flash-preview-09-2025",
        temperature=0.2,  # Slight creativity for analysis
    )

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

    # Create specialist as DeepAgent (Pattern 3)
    # No nested subagents for clean test
    specialist = create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        response_format=OperationIntent,  # Structured output
        subagents=[],  # No nested sub-specialists
        checkpointer=checkpointer,  # Optional state persistence
        interrupt_on={},  # No HITL for specialist (PM handles approvals)
    )

    return specialist
