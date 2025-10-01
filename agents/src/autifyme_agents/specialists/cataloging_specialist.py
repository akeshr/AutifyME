"""Cataloging specialist for extracting product details from text."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

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
        A Runnable chain that takes {"input": {"user_message": str}} and returns Product.
    """
    # Build prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", CATALOGING_SPECIALIST_SYSTEM_PROMPT),
        ("human", "{input[user_message]}"),
    ])
    
    # Use centralized LLM factory with prompt caching
    llm = get_llm(provider="openai", model="gpt-4o")
    
    # Force structured output (LangChain v1 feature)
    structured_llm = llm.with_structured_output(Product)
    
    # Compose chain using LCEL
    return prompt | structured_llm
