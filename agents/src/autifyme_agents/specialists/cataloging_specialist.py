from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.schemas.models import Product
from autifyme_agents.core.prompt_loader import load_prompt

# The prompt is now loaded from a version-controlled file,
# adhering to our architecture.
CATALOGING_SPECIALIST_SYSTEM_PROMPT = load_prompt("specialists/cataloging_specialist.prompt")

def create_cataloging_specialist() -> Runnable:
    """
    Creates and returns a specialist agent focused on extracting product
    information from unstructured text and formatting it as a Product object.

    This specialist is a simple, non-cyclical chain (not a ReAct agent) because
    its task is a one-shot extraction, not a multi-step process involving tools.
    It leverages LangChain v1's `.with_structured_output()` to guarantee
    type-safe, Pydantic-based output.

    Returns:
        A Runnable chain that takes a user message and returns a Product object.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CATALOGING_SPECIALIST_SYSTEM_PROMPT),
        ]
    )

    # Use our centralized LLM factory to get a consistent, cached model
    llm = get_llm(provider="openai", model="gpt-4o")

    # The core of our type-safe extraction. This method ensures the LLM's
    # output is a valid instance of the Product Pydantic model.
    structured_llm = llm.with_structured_output(Product)

    # Create the final chain
    chain = prompt | structured_llm

    return chain
