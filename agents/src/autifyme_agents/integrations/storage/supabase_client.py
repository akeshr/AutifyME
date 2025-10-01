from supabase import create_client, Client
from typing import Dict, Any

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.config import settings
from autifyme_agents.schemas.models import Product

# Note for Abhi (from our discussion):
# This is our concrete "Adapter". It implements the StorageInterface and
# encapsulates all the Supabase-specific logic. If we ever switch databases,
# we would simply write a new class like this one that implements the same
# interface, and the rest of the app wouldn't need to change.

class SupabaseStorageClient(StorageInterface):
    """
    The concrete implementation of the StorageInterface for Supabase.
    """
    _client: Client

    def __init__(self):
        """
        Initializes the Supabase client using credentials from our settings.
        """
        self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

    def get_company_profile(self) -> Dict[str, Any]:
        """
        Retrieves the single company profile from the 'companies' table in Supabase.
        """
        response = self._client.table("companies").select("*").limit(1).single().execute()
        if not response.data:
            # In a real product, we might have better error handling or setup checks.
            # For now, we'll raise an error if the profile isn't manually created.
            raise ValueError("No company profile found in the database. Please create one in the Supabase UI.")
        return response.data

    def save_product(self, product: Product) -> Product:
        """
        Saves a product to the 'products' table in Supabase.
        """
        # Pydantic's model_dump() is like Java's .toString() or .toJSON() but for creating
        # a dictionary representation of the model, which the Supabase client needs.
        product_dict = product.model_dump(mode='json')

        response = self._client.table("products").upsert(product_dict).execute()
        
        if not response.data:
            raise Exception(f"Failed to save product to Supabase: {response.error}")

        # The response data is a list containing the saved record. We return the first one.
        # We then use Pydantic's model_validate to parse the raw dict back into a clean
        # Product object, ensuring our data remains validated.
        return Product.model_validate(response.data[0])
