"""Image analysis specialist using create_agent for consistency.

Replaces simple chain with full agent for observability and middleware support.
"""

from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult


def create_image_analysis_specialist(
    model: BaseChatModel | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Create image analysis specialist as full agent with structured output.

    Uses create_agent for architectural consistency and observability.

    Args:
        model: Optional LLM override (defaults to vision model)
        checkpointer: Optional checkpointer for stateful specialist

    Returns:
        Agent that analyzes images and returns ImageAnalysisResult
    """

    # Use vision-capable model
    llm = model or get_llm(provider="openai", model="gpt-4o")
    system_prompt = load_prompt("specialists/image_analysis_specialist.prompt")

    # ✅ Use create_agent with response_format
    agent = create_agent(
        model=llm,
        tools=[],  # Pure vision extraction, no tools
        system_prompt=system_prompt,
        response_format=ImageAnalysisResult,  # Structured output
        checkpointer=checkpointer,
        name="ImageAnalysisSpecialist",
    )

    return agent


def image_analysis_specialist_invoke(
    image_url: str,
    company_profile: dict | None = None,
    config: dict | None = None,
) -> ImageAnalysisResult:
    """Invoke image analysis specialist with simplified interface."""

    agent = create_image_analysis_specialist()

    # Build vision input
    brand_voice = company_profile.get("brand_voice") if company_profile else "professional"
    target_audience = company_profile.get("target_audience") if company_profile else "general"

    content = f"""Analyze this product image in the context of our brand.

Brand Voice: {brand_voice}
Target Audience: {target_audience}

Image URL: {image_url}

Extract all visual product attributes including colors, materials, sizes, style, and features."""

    messages = [
        {
            "role": "human",
            "content": [
                {"type": "text", "text": content},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]

    # Invoke agent
    result = agent.invoke({"messages": messages}, config=config or {})

    return result["response"]  # ImageAnalysisResult model
