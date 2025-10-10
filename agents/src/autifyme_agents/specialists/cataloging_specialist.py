"""Cataloging specialist for extracting product details from text."""

from typing import Dict, Any

from langchain.messages import SystemMessage, HumanMessage
from langchain.tools import tool, BaseTool

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.schemas.models import Product
from autifyme_agents.core.prompt_loader import load_prompt


# Alternative to ChatPromptTemplate to avoid langchain_core
def create_chat_prompt(system_content: str, human_template: str):
    """Alternative to ChatPromptTemplate.from_messages"""
    def format_prompt(**kwargs):
        return [
            SystemMessage(content=system_content),
            HumanMessage(content=human_template.format(**kwargs))
        ]
    return format_prompt

# Load prompt from version-controlled file
CATALOGING_SPECIALIST_SYSTEM_PROMPT = load_prompt("specialists/cataloging_specialist.prompt")


def create_cataloging_specialist():
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

    # Use alternative prompt creation instead of ChatPromptTemplate
    prompt = create_chat_prompt(
        CATALOGING_SPECIALIST_SYSTEM_PROMPT,
        """
User request:
{user_message}

Image insights (may be empty):
{image_analysis}

Produce a complete product record with all available fields populated.
"""
    )
    
    # Use centralized LLM factory with prompt caching
    llm = get_llm(provider="openai", model="gpt-4o")
    
    # Force structured output (LangChain v1 feature)
    structured_llm = llm.with_structured_output(Product)
    
    # Create a simple Runnable-like class instead of plain function
    class CatalogingChain:
        """A simple chain class that mimics Runnable behavior."""
        def __init__(self, prepare_func, prompt_func, llm):
            self.prepare_func = prepare_func
            self.prompt_func = prompt_func
            self.llm = llm

        def __call__(self, inputs: Dict[str, Any], config=None) -> Any:
            """Make the chain callable."""
            return self.invoke(inputs, config)

        def invoke(self, inputs: Dict[str, Any], config=None) -> Any:
            """Invoke the chain with inputs."""
            prepared = self.prepare_func(inputs)
            messages = self.prompt_func(**prepared)
            return self.llm.invoke(messages)

    return CatalogingChain(prepare_inputs, prompt, structured_llm)


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


def create_cataloging_specialist_tool() -> BaseTool:
    return cataloging_specialist_tool
