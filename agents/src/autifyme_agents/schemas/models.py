"""Domain models for core business entities."""

from uuid import UUID
from typing import Optional, List, Literal, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Product(BaseModel):
    """
    Represents a product in the catalog.

    Note: No company_id field - single-tenant architecture means each
    deployed instance serves exactly one company.

    The `id` field is None for drafts and populated by the database on INSERT.
    """
    id: Optional[UUID] = Field(
        default=None,
        description="The unique identifier for the product (database-generated)."
    )
    name: Optional[str] = Field(None, description="The name of the product.")
    description: Optional[str] = Field(None, description="A detailed description of the product.")
    price: Optional[float] = Field(None, description="The price of the product.")
    sizes: Optional[List[str]] = Field(default_factory=list, description="Available sizes.")
    colors: Optional[List[str]] = Field(default_factory=list, description="Available colors.")
    image_urls: Optional[List[str]] = Field(default_factory=list, description="Product image URLs.")

    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v: Any) -> Optional[UUID]:
        """
        Handle invalid UUID strings from LLM by treating them as None (draft).

        Valid UUIDs pass through, invalid strings become None (database will generate).
        """
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        if isinstance(v, str):
            try:
                return UUID(v)
            except (ValueError, AttributeError):
                # Invalid UUID string from LLM - treat as draft (no ID yet)
                return None
        return None

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


# --- Department Response Models ---
# These models define structured outputs that departments return to the Project Manager


class CatalogingResult(BaseModel):
    """
    Structured output from the Cataloging Department.
    
    Used by the Project Manager to track cataloging progress and approvals.
    """

    stage: Literal["draft", "awaiting_approval", "saved", "failed"] = Field(
        ..., description="Current lifecycle stage for the cataloging workflow."
    )
    success: bool = Field(..., description="Whether the cataloging operation succeeded for this stage.")
    product_id: Optional[UUID] = Field(None, description="The UUID of the cataloged product if available.")
    product_name: Optional[str] = Field(None, description="The name of the cataloged product.")
    message: str = Field(..., description="Human-readable summary of what happened.")
    data: Optional[dict] = Field(
        default=None,
        description="Structured payload associated with the stage (draft details or saved record).",
    )

    model_config = ConfigDict(from_attributes=True)