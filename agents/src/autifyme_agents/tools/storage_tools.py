from langchain_core.tools import tool
from typing import Dict, Any
from uuid import UUID

from ..schemas.models import Product
from ..integrations.storage.supabase_client import SupabaseStorageClient

# Initialize a single, shared instance of our storage client.
# This is a simple form of dependency injection. In a more complex system,
# we might use a proper DI framework, but for our single-tenant architecture,
# this singleton pattern is clean and sufficient.
_storage_client = SupabaseStorageClient()


@tool
def save_product(product: Product) -> Product:
    """
    Saves a product to the database.
    
    Use this tool when you need to persist a new product or update an existing one.
    
    Args:
        product: The Product object to save.
        
    Returns:
        The saved Product object with any updates from the database.
    """
    return _storage_client.save_product(product)


@tool
def get_company_profile() -> Dict[str, Any]:
    """
    Retrieves the company profile from the database.
    
    Use this tool when you need to understand the company's brand voice,
    target audience, or other contextual information to inform your work.
    
    Returns:
        A dictionary containing the company's profile information.
    """
    return _storage_client.get_company_profile()
