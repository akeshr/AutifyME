"""
Storage tools for database operations.

Following LangChain v1 patterns:
- Tools raise custom exceptions on failure (not generic ValueError)
- Retry logic with tenacity for transient failures
- Errors are caught by ToolNode's handle_tool_errors mechanism
"""

import logging
from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, Field
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from autifyme_agents.core.exceptions import (
    ConfigurationError,
    DataNotFoundError,
    ExternalAPIError,
    classify_api_error,
)
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.models import CatalogingResult, CompanyProfile, Product

logger = logging.getLogger(__name__)


class SaveProductArgs(BaseModel):
    """Input schema for the save_product tool."""
    name: str = Field(..., description="The name of the product.")
    description: str = Field(..., description="A detailed description of the product.")
    price: float = Field(..., description="The price of the product.")
    sizes: list[str] | None = Field(None, description="A list of available sizes for the product.")
    colors: list[str] | None = Field(None, description="A list of available colors for the product.")
    image_urls: list[str] | None = Field(None, description="A list of URLs for the product images.")
    id: str | None = Field(
        None,
        description="Product ID for updates. If provided, updates existing product (upsert). If None, creates new product.",
    )


def _save_product(storage: StorageInterface, **kwargs: Any) -> Product:
    if storage is None:
        raise ConfigurationError(
            "Storage client not provided via config.",
            config_key="storage_client",
        )

    try:
        product = Product(**kwargs)
        return storage.save_product(product)
    except Exception as e:
        # Use centralized error classifier for consistent error handling
        raise classify_api_error(e, "save_product", "Supabase") from e


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
        # Use centralized error classifier for consistent error handling
        raise classify_api_error(e, "get_company_profile", "Supabase") from e


def create_save_product_tool(storage: StorageInterface) -> object:
    """Create a tool that saves products to the catalog database.

    Factory function that creates a LangChain tool with retry logic and proper error handling.
    The returned tool persists products to storage with automatic retry on transient failures.

    Args:
        storage: Storage adapter for persisting products

    Returns:
        LangChain tool function that accepts product fields and returns CatalogingResult
    """
    @tool(
        "save_product",
        args_schema=SaveProductArgs,
        return_direct=False,
    )
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ExternalAPIError),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def save_product(**kwargs: Any) -> CatalogingResult:
        """Save or update a product in the catalog database (CREATE or UPDATE via upsert).

        CREATE: Omit 'id' to create new product. Returns product_id - store this for updates.
        UPDATE: Include 'id' from previous save to update existing product (no duplicate created).

        Always returns full product with id in the response for future updates.
        """
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


def create_get_company_profile_tool(storage: StorageInterface) -> object:
    """Create a tool that retrieves the company profile from storage.

    Factory function that creates a LangChain tool with retry logic and proper error handling.
    The returned tool fetches company context including brand voice and target audience.

    Args:
        storage: Storage adapter for retrieving company profile

    Returns:
        LangChain tool function that returns CompanyProfile
    """
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
