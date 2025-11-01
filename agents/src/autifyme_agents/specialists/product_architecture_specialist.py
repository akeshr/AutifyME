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
    provider: str = "google",
    model_name: str = "gemini-2.5-flash",
    temperature: float = 0.2,
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
        provider: LLM provider ("openai", "anthropic", "google") - default: "openai"
        model_name: Model identifier - default: "gpt-4.1-mini"
        temperature: Sampling temperature (0.0-1.0) - default: 0.2

    Returns:
        CompiledStateGraph: Stateful specialist agent that can be nested as subagent in PM

    Notes:
        - Pattern 3 test: Stateful specialist with shared checkpointer
        - Specialist maintains domain knowledge across delegations
        - LangGraph handles thread_id namespacing automatically
        - OpenAI requires StrictChatOpenAI wrapper when using response_format
        - Other providers work with their native chat model classes
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

    # Create specialist as DeepAgent (Pattern 3)
    # - OpenAI: StrictChatOpenAI wrapper ensures tools have correct strict schemas
    # - Other providers: Native tool use with structured outputs
    specialist = create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        response_format=OperationIntent,  # Structured output (Pydantic model)
        subagents=[],  # No nested sub-specialists
        checkpointer=checkpointer,  # State persistence
        interrupt_on={},  # No HITL for specialist (PM handles approvals)
    )

    return specialist
