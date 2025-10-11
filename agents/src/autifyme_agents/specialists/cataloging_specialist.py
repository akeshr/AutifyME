"""Cataloging specialist using create_agent for consistency.

Replaces simple chain with full agent for observability and middleware support.
"""

from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.schemas.models import Product


def create_cataloging_specialist(
    model: BaseChatModel | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Create cataloging specialist as full agent with structured output.

    Uses create_agent instead of simple chain for:
    - LangSmith observability (traced as agent)
    - Middleware support (caching, summarization)
    - Future extensibility (can add tools)
    - Architectural consistency (agents all the way down)

    Args:
        model: Optional LLM override
        checkpointer: Optional checkpointer for stateful specialist

    Returns:
        Agent that takes input and returns Product model
    """

    llm = model or get_llm(provider="openai", model="gpt-4o")
    system_prompt = load_prompt("specialists/cataloging_specialist.prompt")

    # ✅ Use create_agent with response_format for structured output
    agent = create_agent(
        model=llm,
        tools=[],  # No tools needed - pure extraction
        system_prompt=system_prompt,
        response_format=Product,  # ✅ Structured output (replaces with_structured_output)
        checkpointer=checkpointer,  # Optional: stateful if needed
        name="CatalogingSpecialist",
    )

    return agent


# Adapter for backward compatibility with tool invocation
def cataloging_specialist_invoke(
    user_message: str,
    image_analysis: dict | None = None,
    config: dict | None = None,
) -> Product:
    """Invoke cataloging specialist with simplified interface.

    This maintains compatibility with existing tool wrappers while
    using the new agent-based implementation underneath.
    """

    agent = create_cataloging_specialist()

    # Build input message
    content_parts = [f"User request:\n{user_message}"]

    if image_analysis:
        content_parts.append(f"\nImage insights:\n{image_analysis}")
    else:
        content_parts.append("\nNo image insights provided.")

    content_parts.append("\nProduce a complete product record with all available fields populated.")

    messages = [{"role": "human", "content": "\n".join(content_parts)}]

    # Invoke agent
    result = agent.invoke({"messages": messages}, config=config or {})

    # Extract structured response (Product model)
    return result["response"]  # create_agent with response_format returns {"response": Product}
