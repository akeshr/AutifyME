"""
Storage tools for database operations.

Following LangChain v1 patterns:
- Tools raise custom exceptions on failure (not generic ValueError)
- Retry logic with tenacity for transient failures
- Errors are caught by ToolNode's handle_tool_errors mechanism
"""

from typing import List, Optional
import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from autifyme_agents.schemas.models import Product, CompanyProfile, CatalogingResult
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.exceptions import (
    StorageError,
    ConfigurationError,
    DataNotFoundError,
    ExternalAPIError,
)

logger = logging.getLogger(__name__)


class SaveProductArgs(BaseModel):
    """Input schema for the save_product tool."""
    name: str = Field(..., description="The name of the product.")
    description: str = Field(..., description="A detailed description of the product.")
    price: float = Field(..., description="The price of the product.")
    sizes: Optional[List[str]] = Field(None, description="A list of available sizes for the product.")
    colors: Optional[List[str]] = Field(None, description="A list of available colors for the product.")
    image_urls: Optional[List[str]] = Field(None, description="A list of URLs for the product images.")


def _save_product(storage: StorageInterface, **kwargs) -> Product:
    if storage is None:
        raise ConfigurationError(
            "Storage client not provided via config.",
            config_key="storage_client",
        )

    try:
        product = Product(**kwargs)
        return storage.save_product(product)
    except Exception as e:
        if "timeout" in str(e).lower() or "connection" in str(e).lower():
            raise ExternalAPIError(
                message=str(e),
                tool_name="save_product",
                api_name="Supabase",
                is_retryable=True,
                original_error=e,
            )

        raise StorageError(
            message=f"Failed to save product: {str(e)}",
            operation="save_product",
            original_error=e,
        )


def _get_company_profile(storage: StorageInterface) -> CompanyProfile:
    if storage is None:
        raise ConfigurationError(
            "Storage client not provided via config.",
            config_key="storage_client",
        )

    try:
        profile = storage.get_company_profile()
        if profile is None:
            raise DataNotFoundError(
                resource_type="CompanyProfile",
                identifier="default",
            )
        return profile
    except DataNotFoundError:
        raise
    except Exception as e:
        if "timeout" in str(e).lower() or "connection" in str(e).lower():
            raise ExternalAPIError(
                message=str(e),
                tool_name="get_company_profile",
                api_name="Supabase",
                is_retryable=True,
                original_error=e,
            )

        raise StorageError(
            message=f"Failed to retrieve company profile: {str(e)}",
            operation="get_company_profile",
            original_error=e,
        )


def create_save_product_tool(storage: StorageInterface):
    @tool(args_schema=SaveProductArgs)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ExternalAPIError),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def save_product(**kwargs) -> CatalogingResult:
        """Persist a product to the catalog database."""
        product = _save_product(storage, **kwargs)
        return CatalogingResult(
            stage="saved",
            success=True,
            product_id=product.id,
            product_name=product.name,
            message="Product persisted to catalog",
            data={"product": product.model_dump()},
        )

    return save_product


def create_get_company_profile_tool(storage: StorageInterface):
    @tool
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ExternalAPIError),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def get_company_profile() -> CompanyProfile:
        """Retrieve the company's profile, including brand voice and target audience."""
        return _get_company_profile(storage)

    return get_company_profile
