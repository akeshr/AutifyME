"""Storage tools for database operations."""

from langchain_core.tools import tool
from typing import List, Optional
from pydantic import BaseModel, Field

from autifyme_agents.schemas.models import Product, CompanyProfile
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient


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
def save_product(**kwargs) -> Product:
    """
    Saves a product to the company's catalog database.
    
    This is a generic storage operation that can be used across all workflows
    (cataloging, marketing, inventory management, etc.).
    
    Args:
        **kwargs: Product fields validated against SaveProductArgs schema.
    
    Returns:
        The saved Product object with database-generated ID.
    """
    if _storage_client is None:
        raise ValueError("Storage client not initialized. Call initialize_storage() first.")
    
    product = Product(**kwargs)
    return _storage_client.save_product(product)


@tool
def get_company_profile() -> CompanyProfile:
    """
    Retrieves the company's profile, including brand voice and target audience.
    
    This is a generic read operation used across all departments to access
    brand guidelines and company context.
    """
    if _storage_client is None:
        raise ValueError("Storage client not initialized. Call initialize_storage() first.")

    return _storage_client.get_company_profile()
