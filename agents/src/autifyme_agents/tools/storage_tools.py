"""
Storage tools for database operations.

Following LangChain v1 patterns:
- Tools raise custom exceptions on failure (not generic ValueError)
- Retry logic with tenacity for transient failures
- Errors are caught by ToolNode's handle_tool_errors mechanism
"""

from langchain_core.tools import tool
from typing import List, Optional
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

from autifyme_agents.schemas.models import Product, CompanyProfile
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.core.exceptions import (
    StorageError,
    ConfigurationError,
    DataNotFoundError,
    ExternalAPIError
)

logger = logging.getLogger(__name__)


_storage_client: SupabaseStorageClient | None = None


def initialize_storage(storage_client: SupabaseStorageClient):
    """Initialize the storage client for all storage tools."""
    global _storage_client
    _storage_client = storage_client


class SaveProductArgs(BaseModel):
    """Input schema for the save_product tool."""
    name: str = Field(..., description="The name of the product.")
    description: str = Field(..., description="A detailed description of the product.")
    price: float = Field(..., description="The price of the product.")
    sizes: Optional[List[str]] = Field(None, description="A list of available sizes for the product.")
    colors: Optional[List[str]] = Field(None, description="A list of available colors for the product.")
    image_urls: Optional[List[str]] = Field(None, description="A list of URLs for the product images.")


@tool(args_schema=SaveProductArgs)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(ExternalAPIError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def save_product(**kwargs) -> Product:
    """
    Saves a product to the company's catalog database.
    
    This is a generic storage operation that can be used across all workflows
    (cataloging, marketing, inventory management, etc.).
    
    Retry Strategy:
        - Retries up to 3 times on transient API errors
        - Exponential backoff: 2s, 4s, 8s
        - Only retries ExternalAPIError (network/timeout issues)
        - Other errors (validation, not found) fail immediately
    
    Args:
        **kwargs: Product fields validated against SaveProductArgs schema.
    
    Returns:
        The saved Product object with database-generated ID.
    
    Raises:
        ConfigurationError: If storage client not initialized
        StorageError: If save operation fails
        ExternalAPIError: If Supabase API is unreachable (after retries)
    """
    if _storage_client is None:
        raise ConfigurationError(
            "Storage client not initialized. Call initialize_storage() first.",
            config_key="storage_client"
        )
    
    try:
        product = Product(**kwargs)
        return _storage_client.save_product(product)
    except Exception as e:
        # Check if it's a transient network/API error (retryable)
        if "timeout" in str(e).lower() or "connection" in str(e).lower():
            raise ExternalAPIError(
                message=str(e),
                tool_name="save_product",
                api_name="Supabase",
                is_retryable=True,
                original_error=e
            )
        
        # Otherwise, it's a permanent error (don't retry)
        raise StorageError(
            message=f"Failed to save product: {str(e)}",
            operation="save_product",
            original_error=e
        )


@tool
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(ExternalAPIError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def get_company_profile(**kwargs) -> CompanyProfile:
    """
    Retrieves the company's profile, including brand voice and target audience.
    
    This is a generic read operation used across all departments to access
    brand guidelines and company context.
    
    Retry Strategy:
        - Retries up to 3 times on transient API errors
        - Exponential backoff: 2s, 4s, 8s
        - Only retries ExternalAPIError (network/timeout issues)
    
    Returns:
        CompanyProfile with brand voice, target audience, and preferences.
    
    Raises:
        ConfigurationError: If storage client not initialized
        DataNotFoundError: If company profile doesn't exist
        ExternalAPIError: If Supabase API is unreachable (after retries)
    """
    if _storage_client is None:
        raise ConfigurationError(
            "Storage client not initialized. Call initialize_storage() first.",
            config_key="storage_client"
        )

    try:
        profile = _storage_client.get_company_profile()
        if profile is None:
            raise DataNotFoundError(
                resource_type="CompanyProfile",
                identifier="default"  # We're using a single profile for now
            )
        return profile
    except DataNotFoundError:
        # Re-raise DataNotFoundError as-is (don't wrap it)
        raise
    except Exception as e:
        # Check if it's a transient network/API error (retryable)
        if "timeout" in str(e).lower() or "connection" in str(e).lower():
            raise ExternalAPIError(
                message=str(e),
                tool_name="get_company_profile",
                api_name="Supabase",
                is_retryable=True,
                original_error=e
            )
        
        # Otherwise, it's a permanent error (don't retry)
        raise StorageError(
            message=f"Failed to retrieve company profile: {str(e)}",
            operation="get_company_profile",
            original_error=e
        )
