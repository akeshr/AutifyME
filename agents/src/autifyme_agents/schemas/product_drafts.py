"""Product Architecture Specialist - Complete CRUD Draft Types.

Architecture:
- Discriminated union with 7 draft types covering all CRUD operations
- Each draft type has only relevant fields (focused models)
- Type-safe routing via draft_type discriminator
- Specialist autonomously chooses appropriate draft type based on intent classification

Design Philosophy:
- Granular operations: Return only what changed (not full specifications)
- Impact transparency: Deletions include preview of affected data
- Type safety: PM knows exactly what it received
- Extensibility: Easy to add new draft types
"""

from typing import Any, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field

# Import existing nested models
from autifyme_agents.tools.product_persistence_tools import (
    VariantValueInput,
    ProductSKUInput,
)
from autifyme_agents.tools.product_search_tools import ProductFamilySearchResult


# =============================================================================
# Nested Models for Drafts
# =============================================================================


class VariantAxisDraft(BaseModel):
    """Draft of a single variant dimension."""

    name: str = Field(..., description="Snake_case axis name (e.g., 'size', 'color')")
    display_label: str = Field(..., description="Human-readable label")
    inferred_values: list[str] = Field(
        ..., description="Detected variant values for this axis"
    )
    reasoning: str = Field(
        ..., description="Why this axis was identified and how values were detected"
    )
    schema_property: str | None = Field(
        None, description="Schema.org property if applicable (e.g., 'size', 'color')"
    )
    sort_order: int = Field(default=0, description="Display order in UI")


class SKUPatternDraft(BaseModel):
    """Draft SKU naming pattern."""

    prefix: str = Field(..., description="SKU prefix (e.g., 'SHOE', 'BAG')")
    pattern: str = Field(
        ..., description="Full pattern with placeholders (e.g., 'SHOE-{SIZE}-{COLOR}')"
    )
    example_skus: list[str] = Field(
        ..., description="3-5 example SKUs generated from pattern"
    )
    total_combinations: int = Field(
        ..., description="Total number of SKUs that will be generated"
    )
    reasoning: str = Field(..., description="Explanation of naming logic")


# =============================================================================
# UPDATE Operation - Nested Update Models
# =============================================================================


class VariantAxisUpdate(BaseModel):
    """Update metadata for existing variant axis."""

    axis_name: str = Field(..., description="Which axis to update")
    field_updates: dict[str, Any] = Field(
        ...,
        description="Fields to update: display_label, sort_order, schema_property",
    )


class VariantValueUpdate(BaseModel):
    """Update attributes for existing variant value."""

    sku_code: str = Field(..., description="Which value to update (by SKU code)")
    field_updates: dict[str, Any] = Field(
        ...,
        description=(
            "Fields: value, display_label, price_adjustment, "
            "color_hex, image_url, sort_order"
        ),
    )


class IndustryTargetUpdate(BaseModel):
    """Add or update industry target."""

    industry_naics_code: str
    operation: Literal["add", "update", "remove"]
    field_updates: dict[str, Any] | None = Field(
        None,
        description=(
            "For add/update: industry_use_case, industry_benefits, "
            "compliance_notes, is_primary_industry"
        ),
    )


class CustomerSegmentUpdate(BaseModel):
    """Add or update customer segment."""

    segment_type: str = Field(..., description="b2b, b2c, d2c, wholesale, etc.")
    operation: Literal["add", "update", "remove"]
    field_updates: dict[str, Any] | None = Field(
        None,
        description=(
            "For add/update: segment_label, tone, key_benefits, "
            "pain_points, primary_channels, etc."
        ),
    )


class ImageUpdate(BaseModel):
    """Add or update product image."""

    image_url: str = Field(..., description="Image identifier")
    operation: Literal["add", "update", "remove", "reorder"]
    field_updates: dict[str, Any] | None = Field(
        None,
        description="For add/update: alt_text, image_type, display_order, is_primary, for_sku",
    )
    new_display_order: int | None = Field(None, description="For reorder operation")


class MarketingContentUpdate(BaseModel):
    """Add or update marketing content."""

    content_id: str | None = Field(None, description="Existing content ID for update")
    platform: str = Field(..., description="instagram, facebook, catalog, etc.")
    content_type: str = Field(..., description="post, story, ad, description, etc.")
    operation: Literal["add", "update", "remove"]
    field_updates: dict[str, Any] | None = Field(
        None,
        description=(
            "For add/update: content_text, hashtags, keywords, "
            "meta_title, meta_description, etc."
        ),
    )


# =============================================================================
# DELETE Operation - Impact Analysis
# =============================================================================


class DeletionImpactAnalysis(BaseModel):
    """Analysis of what will be deleted (preview before execution)."""

    affected_skus: list[str] = Field(
        default_factory=list, description="SKUs that will be deleted"
    )
    affected_images: int = Field(default=0, description="Count of images to be deleted")
    affected_content: int = Field(
        default=0, description="Count of marketing content to be deleted"
    )
    cascade_deletions: dict[str, int] = Field(
        default_factory=dict,
        description="Cascading deletions by table: {table_name: count}",
    )
    total_records: int = Field(..., description="Total database records affected")
    reversible: bool = Field(..., description="Can this deletion be undone?")
    warning_message: str | None = Field(
        None, description="Critical warnings (e.g., order history exists)"
    )


# =============================================================================
# Draft Type 1: CREATE - Full Product Family
# =============================================================================


class ProductArchitectureDraft(BaseModel):
    """Complete product architecture analysis for new product family.

    Use when: User wants to create entirely new product family.
    Trigger: search recommendation = "create_new", no catalog matches found.
    """

    draft_type: Literal["full_family"] = "full_family"

    # Core identification
    product_family_name: str = Field(..., description="Product family name")
    product_group_id: str = Field(
        ..., description="Business identifier (e.g., 'SHOE-AIR-MAX')"
    )
    brand: str = Field(..., description="Brand name")
    description: str = Field(..., description="Family-level description")

    # Variant structure
    variant_axes: list[VariantAxisDraft] = Field(
        ..., description="Identified variant dimensions"
    )

    # SKU architecture
    sku_pattern: SKUPatternDraft = Field(..., description="SKU naming design")

    # Material and condition
    material: str | None = Field(None, description="Primary material")
    condition: str = Field(default="new", description="new, refurbished, or used")

    # Intelligent matching for autonomous decisions
    catalog_match_analysis: ProductFamilySearchResult = Field(
        ..., description="Search results confirming no match found"
    )

    # Analysis metadata
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in architecture design"
    )
    analysis_notes: str = Field(
        ..., description="Additional observations and recommendations"
    )

    # Reusability validation
    is_standalone_product: bool = Field(
        default=False,
        description="True if no variants detected (single product, not a family)",
    )


# =============================================================================
# Draft Type 2: CREATE - Add Variant Value
# =============================================================================


class VariantAdditionDraft(BaseModel):
    """Adding variant value(s) to existing family (GRANULAR CREATE).

    Use when: User wants to add new value to existing variant dimension.
    Trigger: search recommendation = "add_variant", value doesn't exist.
    Example: "Add 2L capacity" where capacity axis already exists.
    """

    draft_type: Literal["variant_addition"] = "variant_addition"

    # Context (from search)
    existing_family_id: UUID = Field(..., description="Family being extended")
    existing_family_name: str
    existing_sku_prefix: str

    # What's NEW (not full spec)
    target_axis_name: str = Field(
        ..., description="Axis being extended (e.g., 'capacity')"
    )
    new_variant_values: list[VariantValueInput] = Field(
        ..., description="ONLY new values, not existing ones"
    )

    # Generated SKUs from new values
    new_skus: list[ProductSKUInput] = Field(
        ..., description="New product SKUs generated from new values"
    )

    # Match analysis & confidence
    catalog_match_analysis: ProductFamilySearchResult
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    analysis_notes: str


# =============================================================================
# Draft Type 3: CREATE - Add Variant Axis
# =============================================================================


class AxisAdditionDraft(BaseModel):
    """Adding entirely new variant axis (STRUCTURAL CREATE).

    Use when: User wants to add new dimension that doesn't exist.
    Trigger: User mentions axis that doesn't exist in search results.
    Example: "Add material options" where material axis doesn't exist.
    """

    draft_type: Literal["axis_addition"] = "axis_addition"

    # Context
    existing_family_id: UUID
    existing_family_name: str
    existing_sku_prefix: str
    existing_variant_count: int = Field(..., description="SKU count before expansion")

    # What's NEW
    new_axis: VariantAxisDraft = Field(..., description="New dimension being added")
    new_axis_values: list[VariantValueInput] = Field(
        ..., description="Values for new axis"
    )

    # Impact assessment
    new_sku_count: int = Field(..., description="Total SKUs after expansion")
    sku_pattern_update: str = Field(
        ..., description="Updated SKU pattern with new axis placeholder"
    )
    warning: str | None = Field(
        None, description="Warning if SKU count explodes (e.g., > 100)"
    )

    # Match analysis & confidence
    catalog_match_analysis: ProductFamilySearchResult
    confidence_score: float
    analysis_notes: str


# =============================================================================
# Draft Type 4: UPDATE - Field Updates
# =============================================================================


class FamilyUpdateDraft(BaseModel):
    """Update ANY field(s) on ANY table(s) for existing family (COMPREHENSIVE UPDATE).

    Use when: User wants to change specific fields without structural changes.
    Trigger: search recommendation = "update_existing", user mentions field changes.
    Example: "Change base price to Rs 35", "Update Instagram caption", "Add B2B segment".

    ALL nested update lists are optional - include only what user wants to change.
    Supports updates across all 9 tables in database.
    """

    draft_type: Literal["family_update"] = "family_update"

    # Context
    existing_family_id: UUID
    existing_family_name: str

    # ===== Table 1: product_families =====
    family_field_updates: dict[str, Any] | None = Field(
        None,
        description="Family fields: name, description, base_price, material, condition, "
        "lifecycle_stage, tags, google_product_category, custom_attributes",
    )

    # ===== Table 2: products (SKUs) =====
    sku_field_updates: dict[str, dict[str, Any]] | None = Field(
        None,
        description="SKU-specific changes: {sku: {price, stock_quantity, availability, "
        "is_primary_variant, sale_price, link}}",
    )

    # ===== Table 3: variant_axes =====
    variant_axis_updates: list[VariantAxisUpdate] | None = Field(
        None, description="Update axis metadata (display_label, sort_order)"
    )

    # ===== Table 4: variant_values =====
    variant_value_updates: list[VariantValueUpdate] | None = Field(
        None,
        description=(
            "Update value attributes (price_adjustment, color_hex, "
            "display_label, sort_order)"
        ),
    )

    # ===== Table 6: product_family_industries =====
    industry_target_updates: list[IndustryTargetUpdate] | None = Field(
        None, description="Add/update/remove industry targets"
    )

    # ===== Table 7: customer_segments =====
    customer_segment_updates: list[CustomerSegmentUpdate] | None = Field(
        None, description="Add/update/remove customer segments"
    )

    # ===== Table 8: product_images =====
    image_updates: list[ImageUpdate] | None = Field(
        None, description="Add/update/remove/reorder product images"
    )

    # ===== Table 9: marketing_content =====
    marketing_content_updates: list[MarketingContentUpdate] | None = Field(
        None, description="Add/update/remove platform-specific marketing content"
    )

    # Match analysis & confidence
    catalog_match_analysis: ProductFamilySearchResult
    confidence_score: float
    analysis_notes: str

    # Summary for HITL
    update_summary: str = Field(
        ..., description="Human-readable summary of all changes for user approval"
    )


# =============================================================================
# Draft Type 5: READ - Query Data
# =============================================================================


class ProductQueryDraft(BaseModel):
    """Retrieve product data (READ operations).

    Use when: User wants to view/inspect existing data.
    Trigger: User asks questions or requests data (keywords: show, list, what, which, get, view).
    Example: "Show me all SKUs for PET Bottles", "What industries are we targeting?".
    """

    draft_type: Literal["query"] = "query"

    # Which family (required)
    family_id: UUID
    family_name: str

    # What to retrieve (at least one must be True)
    retrieve_family_details: bool = Field(
        default=False, description="Get complete family metadata"
    )
    retrieve_all_skus: bool = Field(
        default=False, description="Get all product variants with details"
    )
    retrieve_specific_skus: list[str] | None = Field(
        None, description="Get specific SKUs by code"
    )
    retrieve_variant_structure: bool = Field(
        default=False, description="Get axes + values configuration"
    )
    retrieve_industry_targets: bool = Field(
        default=False, description="Get industry targeting data"
    )
    retrieve_customer_segments: bool = Field(
        default=False, description="Get customer segment data"
    )
    retrieve_images: bool = Field(default=False, description="Get all product images")
    retrieve_marketing_content: bool = Field(
        default=False, description="Get all marketing content"
    )
    retrieve_marketing_by_platform: str | None = Field(
        None, description="Get content for specific platform (instagram, facebook, etc.)"
    )

    # Match context
    catalog_match_analysis: ProductFamilySearchResult
    confidence_score: float
    analysis_notes: str


# =============================================================================
# Draft Type 6: DELETE - Remove Data
# =============================================================================


class ProductDeletionDraft(BaseModel):
    """Delete product data (DELETE operations with impact analysis).

    Use when: User wants to remove products/variants/data.
    Trigger: User wants to delete (keywords: delete, remove, discontinue, archive).
    Example: "Remove Amber color option", "Delete PET Bottles family".

    CRITICAL: Always includes impact analysis for user confirmation before execution.
    """

    draft_type: Literal["deletion"] = "deletion"

    # Deletion scope
    deletion_scope: Literal[
        "entire_family",
        "specific_skus",
        "variant_axis",
        "variant_value",
        "industry_target",
        "customer_segment",
        "images",
        "marketing_content",
    ]

    # Context
    family_id: UUID
    family_name: str

    # What to delete (based on scope)
    target_skus: list[str] | None = Field(None, description="For specific_skus scope")
    target_axis_name: str | None = Field(
        None,
        description="For variant_axis scope (deletes axis + all its values + affected SKUs)",
    )
    target_value_sku_code: str | None = Field(
        None, description="For variant_value scope (deletes value + affected SKUs)"
    )
    target_industry_naics: str | None = Field(
        None, description="For industry_target scope"
    )
    target_segment_type: str | None = Field(
        None, description="For customer_segment scope"
    )
    target_image_urls: list[str] | None = Field(None, description="For images scope")
    target_content_ids: list[str] | None = Field(
        None, description="For marketing_content scope"
    )

    # Deletion mode
    soft_delete: bool = Field(
        default=True,
        description="If True, mark as inactive/discontinued. If False, hard delete from DB.",
    )

    # Impact analysis (REQUIRED before deletion)
    impact_analysis: DeletionImpactAnalysis = Field(
        ...,
        description="Preview of what will be deleted - shown to user for confirmation",
    )

    # Reasoning
    catalog_match_analysis: ProductFamilySearchResult
    confidence_score: float
    analysis_notes: str

    # Safety check
    requires_explicit_confirmation: bool = Field(
        default=True,
        description="Always True for deletions - PM must get explicit user approval",
    )


# =============================================================================
# Draft Type 7: CLARIFY - Ambiguous Intent
# =============================================================================


class AmbiguousDraft(BaseModel):
    """Cannot determine operation autonomously (CLARIFICATION NEEDED).

    Use when: Multiple matches, unclear intent, or missing critical data.
    Trigger: search recommendation = "ask_user", OR confidence < 0.7.
    Example: "Catalog this jar" with multiple similar products in catalog.
    """

    draft_type: Literal["ambiguous"] = "ambiguous"

    # What specialist found
    catalog_match_analysis: ProductFamilySearchResult = Field(
        ..., description="Multiple matches or low-confidence results"
    )

    # What specialist needs
    clarification_needed: list[str] = Field(
        ..., description="Questions PM should ask user"
    )
    suggestions: list[str] = Field(
        ..., description="Possible interpretations or options"
    )

    # Confidence (always low for ambiguous)
    confidence_score: float = Field(..., le=0.7, description="Low confidence")
    analysis_notes: str


# =============================================================================
# Union Type for Specialist Response
# =============================================================================

ProductArchitectureResponse = Union[
    ProductArchitectureDraft,  # CREATE: New family
    VariantAdditionDraft,  # CREATE: Add variant value
    AxisAdditionDraft,  # CREATE: Add variant axis
    FamilyUpdateDraft,  # UPDATE: Any field, any table
    ProductQueryDraft,  # READ: Retrieve data
    ProductDeletionDraft,  # DELETE: Remove data
    AmbiguousDraft,  # CLARIFY: Need user input
]
