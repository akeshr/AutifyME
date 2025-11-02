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
- CompiledSubAgent: Specialist compiled with create_agent()
- Returns CompiledStateGraph from create_agent
- Structured output via response_format=OperationIntent
- Schema-driven planning (no hard-coded operation types)
- Domain specialist pattern (no orchestration capabilities)
"""

from typing import Any

from langchain.agents import create_agent
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
    provider: str = "google",
    model_name: str = "gemini-2.5-pro",
    temperature: float = 0.3,
) -> CompiledStateGraph:
    """
    Create Product Architecture Specialist with schema-driven CRUD.

    CompiledSubAgent Pattern: Domain specialist compiled with create_agent().

    Specialist Responsibilities:
    - Query product catalog schema dynamically
    - Search catalog for existing product families
    - Classify user intent (create/read/update/delete)
    - Generate OperationIntent with execution plan
    - Calculate impact analysis from schema + data
    - Maintain conversation history across PM delegations

    Architecture:
    - Specialist Agent (create_agent) with structured output
    - response_format: OperationIntent (Pydantic model)
    - Checkpointer: Uses separate specialist checkpointer for context isolation
    - Thread isolation: LangGraph automatically namespaces thread_id for nested agent
    - Schema-driven planning (no hard-coded operation types)
    - Domain specialist (no orchestration features like subagents, file tools)

    Args:
        storage: Storage interface for catalog search + schema query (REQUIRED)
        checkpointer: Checkpointer instance for specialist state persistence (REQUIRED)
        provider: LLM provider ("openai", "anthropic", "google") - default: "google"
        model_name: Model identifier - default: "gemini-2.5-pro"
        temperature: Sampling temperature (0.0-1.0) - default: 0.3

    Returns:
        CompiledStateGraph: Stateful specialist agent wrapped as CompiledSubAgent in PM

    Notes:
        - Follows CLAUDE.md: "Use create_agent for specialists" (line 68)
        - Specialist maintains domain knowledge across delegations
        - LangGraph handles thread_id namespacing automatically
        - OpenAI requires StrictChatOpenAI wrapper when using response_format
        - Other providers work with their native chat model classes
        - Separate checkpointer provides context isolation from PM
        - No orchestration overhead (no subagents, file tools, todo tools)
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

    # Model configuration - provider-agnostic with OpenAI special handling
    # OpenAI requires StrictChatOpenAI wrapper when using response_format (structured outputs)
    # because it enforces strict schema validation globally and requires additionalProperties: false
    # Other providers (Anthropic, Google) work natively with structured outputs
    from autifyme_agents.core.llm_factory import get_llm

    if provider == "openai":
        # OpenAI with response_format requires strict mode + additionalProperties injection
        from autifyme_agents.core.strict_openai_model import StrictChatOpenAI
        model = StrictChatOpenAI(
            model=model_name,
            temperature=temperature,
        )
    else:
        # Other providers work natively
        model = get_llm(
            provider=provider,
            model=model_name,
            temperature=temperature,
        )

    # Create specialist as Agent (CompiledSubAgent pattern)
    # - Uses create_agent (not create_deep_agent) per CLAUDE.md architecture
    # - Domain specialist without orchestration capabilities
    # - OpenAI: StrictChatOpenAI wrapper ensures tools have correct strict schemas
    # - Other providers: Native tool use with structured outputs
    specialist = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        response_format=OperationIntent,  # Structured output (Pydantic model)
        checkpointer=checkpointer,  # State persistence
        # No interrupt_before/after - PM handles approvals via HITL tools
    )

    return specialist
