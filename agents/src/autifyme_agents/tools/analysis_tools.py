"""
Analysis tools for product intelligence.

Following LangChain v1 patterns:
- Tools raise custom exceptions on failure
- Retry logic with tenacity for transient failures
- Errors are caught by agent for self-correction
"""

from typing import Callable
import logging

from langchain_core.tools import tool
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from autifyme_agents.specialists.image_analysis_specialist import create_image_analysis_specialist
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.core.middleware import create_company_context_middleware
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.exceptions import (
    ImageAnalysisError,
    ExternalAPIError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def create_analyze_product_image_tool(storage: StorageInterface) -> Callable:
    company_context_middleware = create_company_context_middleware(storage)

    @tool
    @company_context_middleware
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ExternalAPIError),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def analyze_product_image(image_url: str, **kwargs) -> ImageAnalysisResult:
        """Analyze a product image and return structured visual insights."""
        company_profile = kwargs.get("company_profile")

        if not company_profile:
            raise ValidationError(
                "Company profile not available. Ensure middleware is properly configured.",
                field="company_profile",
                value=None,
            )
        if not image_url or not image_url.startswith(("http://", "https://")):
            raise ValidationError(
                "Image URL must be a valid HTTP/HTTPS URL",
                field="image_url",
                value=image_url,
            )

        try:
            specialist = create_image_analysis_specialist()

            invoke_config = kwargs.get("config", {})
            result = specialist.invoke(
                {
                    "input": {
                        "image_url": image_url,
                        "company_profile": company_profile,
                    }
                },
                config=invoke_config,
            )
            return result

        except ValidationError:
            raise

        except Exception as e:
            error_str = str(e).lower()

            if any(term in error_str for term in ["timeout", "rate limit", "429", "503"]):
                raise ExternalAPIError(
                    message=str(e),
                    tool_name="analyze_product_image",
                    api_name="Vision API",
                    status_code=getattr(e, "status_code", None),
                    is_retryable=True,
                    original_error=e,
                )

            if any(term in error_str for term in ["404", "not found", "access denied", "forbidden"]):
                raise ValidationError(
                    f"Cannot access image at URL: {image_url}. Error: {str(e)}",
                    field="image_url",
                    value=image_url,
                )

            raise ImageAnalysisError(
                message=f"Failed to analyze image: {str(e)}",
                image_url=image_url,
                original_error=e,
            )

    return analyze_product_image
