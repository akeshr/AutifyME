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

from deepagents.middleware.filesystem import TOOL_GENERATORS as FILESYSTEM_TOOLS
from langchain.agents import create_agent
from langchain.agents.middleware.todo import write_todos
from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt

# Import generic operation intent (replaces all hard-coded draft types)
from autifyme_agents.schemas.operation_intent import OperationIntent
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool

# =============================================================================
# Helper Functions
# =============================================================================


def _get_standard_tools(long_term_memory: bool = False) -> list[Any]:
    """
    Get all standard tools that DeepAgents adds to SubAgents.

    These tools enable agents to manage complex tasks and work with ephemeral
    filesystem storage during analysis.

    Args:
        long_term_memory: Whether to enable long-term memory for filesystem tools
                         (persists files across conversations). Default: False.

    Returns:
        List of standard tools: [ls, read_file, write_file, edit_file, write_todos]
    """
    # Generate filesystem tools (ls, read_file, write_file, edit_file)
    filesystem_tools = [
        generator(custom_description=None, long_term_memory=long_term_memory)
        for generator in FILESYSTEM_TOOLS.values()
    ]

    # Add todo tool (write_todos)
    return filesystem_tools + [write_todos]


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
    - StructuredSubAgent pattern (DeepAgents SubAgent + response_format)
    - OperationIntent response (single generic model)
    - Schema-driven planning (no hard-coded operation types)
    - Dynamic execution plan generation
    - Includes standard tools (write_todos, file operations)

    Provider Compatibility:
        Works across all LLM providers (OpenAI, Gemini, Claude) via LangChain's
        create_agent response_format parameter:
        - OpenAI: Uses native json_schema mode (strict=True)
        - Anthropic: Uses function calling / tool-based approach
        - Google Gemini: Uses function calling or responseSchema

    Args:
        storage: Storage interface for catalog search + schema query
        model: LLM for specialist. If None, defaults to gpt-4.1-mini (fast, cost-effective
            for structured output tasks). Override to use different model per specialist.

    Model Selection Guide:
        - gpt-4.1-mini: Fast, cheap, excellent for structured output (DEFAULT)
        - gemini-2.5-flash: Fast, good reasoning, works well with tools
        - claude-3-5-sonnet: Best reasoning, highest quality, more expensive
        - gpt-4o: Strong reasoning, reliable tool calling

    Example - Using different models for different specialists:
        ```python
        # PM uses Gemini for orchestration
        pm_model = get_llm(provider="google", model="gemini-2.5-flash")

        # Product Specialist uses GPT-4.1-mini for structured output
        product_spec = create_product_architecture_specialist(
            storage=storage,
            model=None,  # Uses default: gpt-4.1-mini
        )

        # Marketing Specialist could use Claude for creative work
        marketing_spec = create_marketing_specialist(
            storage=storage,
            model=get_llm(provider="anthropic", model="claude-3-5-sonnet"),
        )
        ```

    Returns:
        StructuredSubAgent spec with:
        - name: specialist identifier
        - description: delegation criteria
        - system_prompt: loaded from prompts/specialists/
        - tools: schema tools + storage tools + standard tools
        - response_format: OperationIntent Pydantic model
    """
    system_prompt = load_prompt("specialists/product_architecture_specialist.prompt")

    description = (
        "Product architecture specialist with schema-driven CRUD. "
        "Queries schema dynamically, searches catalog, classifies intent, "
        "and generates OperationIntent with execution plan. "
        "Handles any operation on any table through schema-driven planning."
    )

    # Start with standard tools (write_todos, filesystem operations)
    tools = _get_standard_tools(long_term_memory=False)

    # Add domain-specific tools
    tools.append(image_analysis_tool)

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

    # Return StructuredSubAgent specification (used by StructuredSubAgentMiddleware)
    # The middleware will create the agent with response_format support
    return {
        "name": "product_architecture_specialist",
        "description": description,
        "system_prompt": system_prompt,
        "tools": tools,
        "model": model,  # Pass model through (middleware uses it)
        "response_format": OperationIntent,  # Pydantic model for structured output
    }
