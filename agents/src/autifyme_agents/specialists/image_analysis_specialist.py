"""Image analysis specialist for extracting visual product information."""

from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.core.prompt_loader import load_prompt

# Load prompt from version-controlled file
IMAGE_ANALYSIS_SYSTEM_PROMPT = load_prompt("specialists/image_analysis_specialist.prompt")


def create_image_analysis_specialist() -> Runnable:
    """
    Creates and returns a specialist agent focused on extracting visual
    product information from an image URL.

    This specialist leverages a multimodal LLM and guarantees a structured,
    Pydantic-based output using LangChain v1's `.with_structured_output()`.

    Returns:
        A Runnable chain that takes a dict `{"input": {"image_url": "...", "company_profile": ...}}` and returns an ImageAnalysisResult.
    """
    llm = get_llm(provider="openai", model="gpt-4o")
    structured_llm = llm.with_structured_output(ImageAnalysisResult)

    # For multimodal messages, we construct them dynamically using a RunnableLambda
    def format_messages(payload: dict) -> list:
        """Formats the multimodal input as a list of messages for the LLM."""
        inputs = payload["input"]
        company_profile = inputs.get('company_profile')
        if company_profile:
            context_text = f"Company Brand Voice: {company_profile.brand_voice}\nTarget Audience: {company_profile.target_audience}"
        else:
            context_text = "Company Brand Voice: N/A\nTarget Audience: N/A"
        
        return [
            SystemMessage(content=IMAGE_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(
                content=[
                    {
                        "type": "image_url",
                        "image_url": {"url": inputs["image_url"]},
                    },
                    {
                        "type": "text",
                        "text": context_text,
                    },
                ]
            ),
        ]
    
    # Chain: format inputs → invoke LLM with structured output
    chain = RunnableLambda(format_messages) | structured_llm

    return chain


@tool("image_analysis_specialist")
def image_analysis_specialist_tool(
    image_url: str,
    *,
    company_profile: dict | None = None,
    config=None,
) -> ImageAnalysisResult:
    """Analyze a product image and return structured visual insights."""
    chain = create_image_analysis_specialist()
    payload = {
        "input": {
            "image_url": image_url,
            "company_profile": company_profile,
        }
    }
    return chain.invoke(payload, config=config)


def create_image_analysis_specialist_tool():
    return image_analysis_specialist_tool
