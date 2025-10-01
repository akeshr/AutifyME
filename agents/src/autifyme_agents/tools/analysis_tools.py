"""Analysis tools for product intelligence."""

from langchain_core.tools import tool

from autifyme_agents.specialists.image_analysis_specialist import create_image_analysis_specialist
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.core.middleware import company_context_middleware
from autifyme_agents.schemas.models import CompanyProfile


@tool
@company_context_middleware
async def analyze_product_image(image_url: str, company_profile: CompanyProfile, _langchain_config: dict = None) -> ImageAnalysisResult:
    """
    Analyzes a product image and returns structured visual information.
    
    This is a generic vision analysis tool that can be used across all workflows
    requiring product image understanding (cataloging, quality control, style matching, etc.).

    Args:
        image_url: The public URL of the product image to analyze.
        company_profile: The company's profile, injected by middleware.
        _langchain_config: Internal LangChain config for tracing (auto-injected by middleware).

    Returns:
        An ImageAnalysisResult object containing visual description, colors, and style tags.
    """
    specialist = create_image_analysis_specialist()
    
    # Pass config to specialist invocation for proper tracing
    invoke_config = _langchain_config or {}
    result = await specialist.ainvoke(
        {"image_url": image_url, "company_profile": company_profile},
        config=invoke_config
    )
    return result
