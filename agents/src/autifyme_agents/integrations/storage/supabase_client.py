"""Supabase storage adapter - implements StorageInterface for database operations."""

from supabase import create_client, Client
from typing import Dict, Any

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.config import settings
from autifyme_agents.schemas.models import Product, CompanyProfile


class SupabaseStorageClient(StorageInterface):
    """
    Concrete implementation of StorageInterface for Supabase.
    
    This adapter encapsulates all Supabase-specific logic, making it easy
    to swap databases without changing core application logic.
    """
    _client: Client
    
    def __init__(self):
        """Initialize Supabase client with credentials from environment."""
        self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    def get_company_profile(self) -> CompanyProfile:
        """
        Retrieves the single company profile from the 'companies' table.
        
        Assumes a single-tenant architecture where only one company profile exists.
        
        Returns:
            A CompanyProfile object containing the company's data.
        
        Raises:
            ValueError: If no company profile is found in the database.
        """
        response = self._client.table("companies").select("*").limit(1).single().execute()
        
        if not response.data:
            raise ValueError(
                "No company profile found in database. "
                "Please create one in the Supabase UI or run a setup script."
            )
        
        return CompanyProfile.model_validate(response.data)
    
    def save_product(self, product: Product) -> Product:
        """
        Saves a product to the 'products' table.
        
        Uses upsert for idempotency - if a product with the same primary key exists,
        it updates the record; otherwise, it inserts a new one.
        
        Args:
            product: The Product object to be saved.
        
        Returns:
            The saved Product object, including any database-generated fields.
        
        Raises:
            Exception: If the save operation fails.
        """
        product_dict = product.model_dump(mode='json')
        
        response = self._client.table("products").upsert(product_dict).execute()
        
        if not response.data:
            raise Exception(f"Failed to save product to Supabase: {response.error}")
        
        return Product.model_validate(response.data[0])
