"""
Analysis tools for product intelligence.

Following LangChain v1 patterns:
- Tools raise custom exceptions on failure
- Retry logic with tenacity for transient failures
- Errors are caught by agent for self-correction
"""

from langchain_core.tools import tool
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

from autifyme_agents.specialists.image_analysis_specialist import create_image_analysis_specialist
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.core.middleware import company_context_middleware
from autifyme_agents.core.exceptions import (
    ImageAnalysisError,
    ExternalAPIError,
    ValidationError
)

logger = logging.getLogger(__name__)


@tool
@company_context_middleware
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(ExternalAPIError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def analyze_product_image(image_url: str, **kwargs) -> ImageAnalysisResult:
    """
    Analyzes a product image using Vision AI and returns structured visual information.
    
    This is a generic vision analysis tool that can be used across all workflows
    requiring product image understanding (cataloging, quality control, style matching, etc.).
    
    IMPORTANT: company_profile is automatically injected by @company_context_middleware.
    DO NOT pass it as an argument - the agent should only provide image_url.
    
    Retry Strategy:
        - Retries up to 3 times on transient API errors
        - Exponential backoff: 2s, 4s, 8s
        - Only retries ExternalAPIError (Vision API timeouts, rate limits)
        - Validation errors (invalid URL) fail immediately

    Args:
        image_url: The public URL of the product image to analyze.
        **kwargs: Contains 'company_profile' (injected by middleware) and 'config' (for tracing).

    Returns:
        An ImageAnalysisResult object containing visual description, colors, and style tags.
    
    Raises:
        ValidationError: If image URL is invalid or inaccessible
        ImageAnalysisError: If image analysis fails
        ExternalAPIError: If Vision API is unreachable (after retries)
    """
    # Extract company_profile from kwargs (injected by middleware)
    company_profile = kwargs.get('company_profile')
    
    if not company_profile:
        raise ValidationError(
            "Company profile not available. Ensure middleware is properly configured.",
            field="company_profile",
            value=None
        )
    # Validate image URL
    if not image_url or not image_url.startswith(('http://', 'https://')):
        raise ValidationError(
            "Image URL must be a valid HTTP/HTTPS URL",
            field="image_url",
            value=image_url
        )
    
    try:
        specialist = create_image_analysis_specialist()
        
        # Pass config to specialist invocation for proper tracing
        invoke_config = kwargs.get("config", {})
        result = specialist.invoke(
            {"input": {"image_url": image_url, "company_profile": company_profile}},
            config=invoke_config
        )
        return result
    
    except ValidationError:
        # Re-raise validation errors as-is (don't wrap)
        raise
    
    except Exception as e:
        error_str = str(e).lower()
        
        # Check if it's a transient API error (retryable)
        if any(term in error_str for term in ["timeout", "rate limit", "429", "503"]):
            raise ExternalAPIError(
                message=str(e),
                tool_name="analyze_product_image",
                api_name="Vision API",
                status_code=getattr(e, 'status_code', None),
                is_retryable=True,
                original_error=e
            )
        
        # Check if it's an image access error
        if any(term in error_str for term in ["404", "not found", "access denied", "forbidden"]):
            raise ValidationError(
                f"Cannot access image at URL: {image_url}. Error: {str(e)}",
                field="image_url",
                value=image_url
            )
        
        # Otherwise, it's a permanent image analysis error
        raise ImageAnalysisError(
            message=f"Failed to analyze image: {str(e)}",
            image_url=image_url,
            original_error=e
        )
