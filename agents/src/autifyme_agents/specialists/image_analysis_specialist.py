"""Image analysis specialist for extracting visual product information."""

import base64
from pathlib import Path
from typing import Any, Dict

from langchain.messages import SystemMessage, HumanMessage
from langchain.tools import tool, ToolException

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.core.prompt_loader import load_prompt

# Load prompt from version-controlled file
IMAGE_ANALYSIS_SYSTEM_PROMPT = load_prompt("specialists/image_analysis_specialist.prompt")


def _image_to_data_url(image_path: str) -> str:
    """Convert a local image file to a base64 data URL for OpenAI's multimodal API.
    
    Args:
        image_path: Path to local image file (e.g., /tmp/xyz.jpg)
        
    Returns:
        Data URL string (e.g., data:image/jpeg;base64,...)
        
    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If image format is unsupported
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Infer MIME type from extension
    suffix = path.suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    
    mime_type = mime_types.get(suffix)
    if not mime_type:
        raise ValueError(f"Unsupported image format: {suffix}. Supported: {list(mime_types.keys())}")
    
    # Read and encode
    with open(path, "rb") as f:
        image_data = f.read()
    
    base64_data = base64.b64encode(image_data).decode("utf-8")
    return f"data:{mime_type};base64,{base64_data}"


def create_image_analysis_specialist():
    """
    Creates and returns a specialist function for extracting visual
    product information from an image URL.

    This specialist leverages a multimodal LLM and guarantees a structured,
    Pydantic-based output using LangChain v1's `.with_structured_output()`.

    Returns:
        A function that takes a dict `{"input": {"image_url": "...", "company_profile": ...}}` and returns an ImageAnalysisResult.
    """
    llm = get_llm(provider="openai", model="gpt-4o")
    structured_llm = llm.with_structured_output(ImageAnalysisResult)

    # For multimodal messages, we construct them dynamically using a RunnableLambda
    def format_messages(payload: dict) -> list:
        """Formats the multimodal input as a list of messages for the LLM.
        
        Handles both web URLs (https://...) and local file paths (/tmp/xyz.jpg)
        by converting local files to base64 data URLs as required by OpenAI's API.
        """
        inputs = payload["input"]
        company_profile = inputs.get('company_profile')
        if company_profile:
            context_text = f"Company Brand Voice: {company_profile.brand_voice}\nTarget Audience: {company_profile.target_audience}"
        else:
            context_text = "Company Brand Voice: N/A\nTarget Audience: N/A"
        
        # Handle both web URLs and local file paths
        image_url = inputs["image_url"]
        if image_url.startswith("http://") or image_url.startswith("https://"):
            # Web URL - pass directly
            image_url_formatted = image_url
        else:
            # Local file path - convert to base64 data URL
            image_url_formatted = _image_to_data_url(image_url)
        
        return [
            SystemMessage(content=IMAGE_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(
                content=[
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url_formatted},
                    },
                    {
                        "type": "text",
                        "text": context_text,
                    },
                ]
            ),
        ]
    
    # Create a simple function instead of Runnable chains
    def analyze_image(inputs: Dict[str, Any]) -> Any:
        """Simple function to analyze images without Runnable dependencies."""
        formatted_messages = format_messages(inputs)
        return structured_llm.invoke(formatted_messages)

    return analyze_image


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
    try:
        return chain.invoke(payload, config=config)
    except FileNotFoundError as exc:
        raise ToolException(
            f"Image could not be accessed at '{image_url}'. Please resend the media."
        ) from exc


def create_image_analysis_specialist_tool():
    return image_analysis_specialist_tool
