"""Domain models for core business entities."""

from uuid import UUID, uuid4
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class Product(BaseModel):
    """
    Represents a product in the catalog.
    
    Note: No company_id field - single-tenant architecture means each
    deployed instance serves exactly one company.
    """
    id: UUID = Field(
        default_factory=uuid4,
        description="The unique identifier for the product."
    )
    name: Optional[str] = Field(None, description="The name of the product.")
    description: Optional[str] = Field(None, description="A detailed description of the product.")
    price: Optional[float] = Field(None, description="The price of the product.")
    sizes: Optional[List[str]] = Field(default_factory=list, description="Available sizes.")
    colors: Optional[List[str]] = Field(default_factory=list, description="Available colors.")
    image_urls: Optional[List[str]] = Field(default_factory=list, description="Product image URLs.")

    class Config:
        from_attributes = True


class CompanyProfile(BaseModel):
    """
    Represents a company's profile and brand guidelines.
    
    Used to provide context for product descriptions, image analysis,
    and content generation across all departments.
    """
    id: str = Field(..., description="Unique identifier for the company.")
    name: str = Field(..., description="The company's business name.")
    brand_voice: str = Field(..., description="Brand voice description.")
    target_audience: str = Field(..., description="Target customer demographic.")
    style_preferences: Optional[List[str]] = Field(default_factory=list, description="Style keywords.")
    industry: Optional[str] = Field(None, description="Company's industry vertical.")

    class Config:
        from_attributes = True


# --- Department Response Models ---
# These models define structured outputs that departments return to the Project Manager


class CatalogingResult(BaseModel):
    """
    Structured output from the Cataloging Department.
    
    This is what the Project Manager receives after a product is cataloged.
    Provides clean, typed interface for multi-department workflows.
    """
    success: bool = Field(..., description="Whether the cataloging operation succeeded.")
    product_id: Optional[UUID] = Field(None, description="The UUID of the cataloged product.")
    product_name: Optional[str] = Field(None, description="The name of the cataloged product.")
    message: str = Field(..., description="Human-readable summary of what happened.")
    
    class Config:
        from_attributes = True
