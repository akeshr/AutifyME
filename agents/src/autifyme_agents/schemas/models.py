from uuid import UUID, uuid4
from typing import Optional, List
from pydantic import BaseModel, Field

class Product(BaseModel):
    """
    Represents a single product in the company's catalog.
    
    This schema is the canonical representation of a product throughout the system.
    In our single-tenant architecture, a product is implicitly tied to the
    deployment instance.
    """
    id: UUID = Field(default_factory=uuid4, description="The unique identifier for the product.")
    
    name: Optional[str] = Field(None, description="The name of the product.")
    description: Optional[str] = Field(None, description="A detailed description of the product.")
    price: Optional[float] = Field(None, description="The price of the product.")
    
    sizes: Optional[List[str]] = Field(default_factory=list, description="A list of available sizes for the product.")
    colors: Optional[List[str]] = Field(default_factory=list, description="A list of available colors for the product.")
    
    image_urls: Optional[List[str]] = Field(default_factory=list, description="A list of URLs for the product images.")

    class Config:
        """
        Pydantic model configuration.
        """
        # This allows the model to be created from database records (which are not dicts)
        orm_mode = True
