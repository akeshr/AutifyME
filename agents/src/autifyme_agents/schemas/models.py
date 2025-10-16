"""Domain models for core business entities."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Product(BaseModel):
    """
    Represents a product in the catalog.

    Note: No company_id field - single-tenant architecture means each
    deployed instance serves exactly one company.

    The `id` field is None for drafts and populated by the database on INSERT.
    """
    id: UUID | None = Field(
        default=None,
        description="The unique identifier for the product (database-generated)."
    )
    name: str | None = Field(None, description="The name of the product.")
    description: str | None = Field(None, description="A detailed description of the product.")
    price: float | None = Field(None, description="The price of the product.")
    sizes: list[str] | None = Field(default_factory=list, description="Available sizes.")
    colors: list[str] | None = Field(default_factory=list, description="Available colors.")
    image_urls: list[str] | None = Field(default_factory=list, description="Product image URLs.")

    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v: Any) -> UUID | None:
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
    style_preferences: list[str] | None = Field(default_factory=list, description="Style keywords.")
    industry: str | None = Field(None, description="Company's industry vertical.")

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
    product_id: UUID | None = Field(None, description="The UUID of the cataloged product if available.")
    product_name: str | None = Field(None, description="The name of the cataloged product.")
    message: str = Field(..., description="Human-readable summary of what happened.")
    data: dict | None = Field(
        default=None,
        description="Structured payload associated with the stage (draft details or saved record).",
    )

    model_config = ConfigDict(from_attributes=True)
