"""Cataloging specialist for extracting product details from text."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import tool

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.schemas.models import Product
from autifyme_agents.core.prompt_loader import load_prompt

# Load prompt from version-controlled file
CATALOGING_SPECIALIST_SYSTEM_PROMPT = load_prompt("specialists/cataloging_specialist.prompt")


def create_cataloging_specialist() -> Runnable:
    """
    Creates a specialist agent for extracting product info from unstructured text.
    
    This is a simple chain (not a ReAct agent) that:
    1. Takes text as input
    2. Extracts product details using an LLM
    3. Returns structured Product model via .with_structured_output()
    
    Returns:
        A Runnable chain that takes {"input": {"user_message": str, "image_analysis": dict | None}} and returns Product.
    """
    def prepare_inputs(payload: dict) -> dict:
        inputs = payload.get("input", {})
        return {
            "user_message": inputs.get("user_message", ""),
            "image_analysis": inputs.get("image_analysis") or "No image insights provided.",
        }

    prompt = ChatPromptTemplate.from_messages([
        ("system", CATALOGING_SPECIALIST_SYSTEM_PROMPT),
        ("human", """
User request:
{user_message}

Image insights (may be empty):
{image_analysis}

Produce a complete product record with all available fields populated.
"""),
    ])
    
    # Use centralized LLM factory with prompt caching
    llm = get_llm(provider="openai", model="gpt-4o")
    
    # Force structured output (LangChain v1 feature)
    structured_llm = llm.with_structured_output(Product)
    
    # Compose chain using LCEL
    return RunnableLambda(prepare_inputs) | prompt | structured_llm


@tool("cataloging_specialist")
def cataloging_specialist_tool(
    user_message: str,
    image_analysis: dict | None = None,
    *,
    config=None,
) -> Product:
    """Combine user text and optional image insights into a structured Product."""
    chain = create_cataloging_specialist()
    payload = {
        "input": {
            "user_message": user_message,
            "image_analysis": image_analysis,
        }
    }
    return chain.invoke(payload, config=config)


def create_cataloging_specialist_tool() -> tool:
    return cataloging_specialist_tool
