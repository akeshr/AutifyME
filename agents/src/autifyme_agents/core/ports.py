from abc import ABC, abstractmethod

from ..schemas.models import Product, CompanyProfile

# Note for Abhi (from our discussion):
# This is the equivalent of a Java or TypeScript `interface`. It defines a
# contract that any storage provider we use *must* adhere to.
# The `@abstractmethod` decorator is like marking a method as abstract.


class StorageInterface(ABC):
    """
    Defines the abstract interface (the "Port") for all storage operations.

    Any concrete storage implementation (like Supabase, DynamoDB, etc.) must
    inherit from this class and implement all its abstract methods. This ensures
    that our application's core logic is decoupled from any specific
    database technology.
    """

    @abstractmethod
    def get_company_profile(self) -> CompanyProfile:
        """
        Retrieves the company profile from the storage layer.

        Since we operate in a single-tenant model, this fetches the one
        and only company profile for the instance.
        """
        pass

    @abstractmethod
    def save_product(self, product: Product) -> Product:
        """
        Saves a product to the storage layer.

        Args:
            product: The Product object to save.

        Returns:
            The saved Product object, potentially updated with new data
            from the database (like a creation timestamp).
        """
        pass
