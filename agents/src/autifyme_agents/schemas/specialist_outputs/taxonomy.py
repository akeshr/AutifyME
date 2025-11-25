"""Taxonomy Specialist output models.

Defines structured outputs for multi-system product classification:
internal categories, Google Product Category, and NAICS industries.
"""

from pydantic import BaseModel, Field


class CategoryMatch(BaseModel):
    """Match to internal category hierarchy."""

    category_id: str = Field(..., description="Category UUID")
    name: str = Field(..., description="Category name")
    slug: str = Field(..., description="Category slug")
    parent_name: str | None = Field(None, description="Parent category if hierarchical")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence")
    reasoning: str = Field(..., description="Why this category was selected")


class GoogleCategoryMatch(BaseModel):
    """Match to Google Product Category taxonomy."""

    category_path: str = Field(
        ..., description="Full category path (e.g., 'Apparel & Accessories > Clothing > Shirts')"
    )
    category_id: str | None = Field(None, description="Google category ID if available")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence")
    reasoning: str = Field(..., description="Why this Google category was selected")


class IndustryMatch(BaseModel):
    """Match to NAICS industry."""

    naics_code: str = Field(..., description="NAICS 2022 code")
    label: str = Field(..., description="Industry label")
    description: str | None = Field(None, description="Industry description")
    level: int = Field(..., description="NAICS hierarchy level (1-6)")
    is_primary_industry: bool = Field(
        ..., description="Primary target industry for this product"
    )
    use_case: str = Field(
        ..., description="How this product serves this industry"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence")


class TaxonomyClassificationDraft(BaseModel):
    """Complete taxonomy classification from Taxonomy Specialist."""

    # Internal category
    internal_category: CategoryMatch | None = Field(
        None, description="Best match from internal category hierarchy"
    )
    alternative_categories: list[CategoryMatch] = Field(
        default_factory=list, description="Alternative category suggestions"
    )

    # Google Product Category
    google_product_category: GoogleCategoryMatch = Field(
        ..., description="Google Product Category for platform compliance"
    )

    # NAICS industries (B2B multi-industry targeting)
    industries: list[IndustryMatch] = Field(
        ..., description="Relevant NAICS industries (ordered by relevance)"
    )

    # Analysis metadata
    classification_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall classification confidence"
    )
    classification_notes: str = Field(
        ..., description="Additional observations and edge cases"
    )
