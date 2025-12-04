"""Domain models for core business entities."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Product(BaseModel):
    """
    Represents a product in the catalog (LEGACY - simplified flat model).

    **DEPRECATION NOTICE:** This model is kept for backward compatibility with
    existing tools and workflows. For new product onboarding workflows, use:
    - ProductFamily: Parent product concept
    - ProductVariant: Individual SKUs with variant linkages

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


class SKUNamingConvention(BaseModel):
    """
    Company-specific SKU naming rules for autonomous pattern generation.

    Used by Product Architecture Specialist to generate consistent SKUs
    that match company branding and naming patterns.
    """
    prefix_format: str = Field(
        ...,
        description="Format for SKU prefix (e.g., 'BRAND-CATEGORY', 'CATEGORY-PRODUCT')"
    )
    separator: str = Field(
        default="-",
        description="Character used to separate SKU components"
    )
    variant_code_length: str = Field(
        ...,
        description="Length range for variant codes (e.g., '3-5', '4', '2-6')"
    )
    uppercase: bool = Field(
        default=True,
        description="Whether SKUs should be uppercase"
    )
    examples: list[str] = Field(
        ...,
        description="Example SKUs following this convention (e.g., ['PAV-BTL-500ML-CLR', 'PAV-JAR-1L-AMB'])"
    )

    model_config = ConfigDict(from_attributes=True)


class WorkflowOutcome(BaseModel):
    """
    Represents the outcome of a completed workflow for analytics and learning.

    Schema matches database: database/migrations/001_workflow_outcomes.sql
    Used by outcome tracking middleware to record workflow execution results.
    """
    # Required identifiers (NOT NULL in DB)
    tracking_id: str = Field(..., description="Unique identifier for this outcome")
    thread_id: str = Field(..., description="LangGraph thread ID")
    sender_id: str = Field(..., description="User identifier (phone number, email, etc.)")
    message_hash: str = Field(..., description="Content hash for similarity matching")
    received_at: datetime = Field(..., description="When message was received")
    started_at: datetime = Field(..., description="When workflow execution started")
    success: bool = Field(..., description="Whether workflow completed successfully")

    # Message info (optional)
    message_text: str | None = Field(None, description="User's original message")
    media_id: str | None = Field(None, description="Media identifier if present")
    media_type: str | None = Field(None, description="Media type (image, video, document)")
    platform: str | None = Field(None, description="Originating platform (whatsapp, web, etc.)")

    # Routing decision
    intent: str | None = Field(None, description="Detected user intent")
    department: str | None = Field(None, description="Routed to department/workflow")
    routing_reasoning: str | None = Field(None, description="PM's routing reasoning")
    routing_confidence: float | None = Field(None, description="Confidence score 0-1")
    alternative_departments: list[str] | None = Field(None, description="Fallback options")
    routed_at: datetime | None = Field(None, description="When routing decision was made")

    # Execution outcome
    error_type: str | None = Field(None, description="Error class if failed")
    error_message: str | None = Field(None, description="Error details if failed")
    resolution_strategy: str | None = Field(None, description="How error was resolved")
    result_data: dict[str, Any] | None = Field(None, description="Structured result (JSONB)")

    # Timing
    duration_seconds: float | None = Field(None, description="Total execution time")
    ended_at: datetime | None = Field(None, description="When workflow completed")

    # Learning metadata (Phase 2)
    learned_patterns: list[dict[str, Any]] | None = Field(None, description="Success patterns")
    failure_warnings: list[dict[str, Any]] | None = Field(None, description="Failure cases")
    applied_strategies: list[str] | None = Field(None, description="Strategies applied")

    # LangSmith correlation
    trace_id: str | None = Field(None, description="LangSmith trace ID")

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

    # SKU Naming Conventions (for Product Architecture Specialist)
    sku_naming_convention: SKUNamingConvention | None = Field(
        None,
        description="Company-specific SKU naming rules for autonomous pattern generation"
    )

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
    data: dict[str, Any] | None = Field(
        default=None,
        description="Structured payload associated with the stage (draft details or saved record).",
    )

    model_config = ConfigDict(from_attributes=True)


# --- Normalized Product Models (Database-Aligned) ---
# These models match the normalized database schema for product families and variants


class ProductFamily(BaseModel):
    """
    Parent product concept representing a group of related variants.

    Example: "Nike Air Max" is a product family that has variants like:
    - Nike Air Max - Red, Size 10
    - Nike Air Max - Blue, Size 9

    Maps to: product_families table in database.
    """

    id: UUID | None = Field(
        default=None,
        description="The unique identifier (database-generated)."
    )
    company_id: str | None = Field(
        default=None,
        description="Company identifier (optional for single-tenant, required in database)."
    )
    category_id: UUID | None = Field(
        default=None,
        description="Category this product family belongs to."
    )

    # Core identifiers
    product_group_id: str = Field(
        ...,
        description="Unique identifier for schema.org ProductGroup (e.g., 'PAV-BTL-500')."
    )
    sku_prefix: str = Field(
        ...,
        description="Prefix for variant SKUs (e.g., 'PAV-BTL' generates 'PAV-BTL-500ML-CLR')."
    )

    # Basic info
    name: str = Field(..., description="Product family name (e.g., '500ml PET Bottle').")
    description: str = Field(..., description="Detailed description of the product family.")
    brand: str = Field(..., description="Brand name (e.g., 'PAVISHA').")

    # Tags and categorization
    tags: list[str] = Field(
        default_factory=list,
        description="Search tags for discovery (e.g., ['food-grade', 'BPA-free'])."
    )
    google_product_category: str | None = Field(
        default=None,
        description="Google Product Category taxonomy ID for Google Shopping feeds."
    )

    # Pricing (base price for all variants, can be overridden per variant)
    base_price: Decimal = Field(
        ...,
        description="Base price in price_currency (variants may add price_adjustment)."
    )
    price_currency: str = Field(
        default="INR",
        description="ISO 4217 currency code (e.g., 'INR', 'USD')."
    )

    # Shared attributes across all variants
    material: str | None = Field(
        default=None,
        description="Primary material (e.g., 'Virgin PET Resin', 'Cotton')."
    )
    condition: Literal["new", "refurbished", "used"] = Field(
        default="new",
        description="Product condition."
    )

    # Extensible attributes (JSONB in database)
    custom_attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible key-value attributes (e.g., {'weight_g': 22, 'certifications': ['IS:12252', 'FSSAI']})."
    )

    # Lifecycle management
    lifecycle_stage: Literal["new_arrival", "regular", "clearance", "discontinued"] = Field(
        default="regular",
        description="Product lifecycle stage for marketing and inventory."
    )

    # Metadata
    is_active: bool = Field(
        default=True,
        description="Whether this product family is active and available."
    )
    created_at: datetime | None = Field(
        default=None,
        description="Creation timestamp (database-generated)."
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp (database-generated)."
    )
    created_by: str | None = Field(
        default=None,
        description="User who created this record (for audit trail)."
    )
    updated_by: str | None = Field(
        default=None,
        description="User who last updated this record (for audit trail)."
    )

    model_config = ConfigDict(from_attributes=True)


class VariantAxis(BaseModel):
    """
    A dimension along which product variants differ.

    Example: For "Nike Air Max" product family:
    - Axis 1: "size" (values: 8, 9, 10, 11)
    - Axis 2: "color" (values: Red, Blue, Black)

    Each product variant is a combination of values from all axes.

    Maps to: variant_axes table in database.
    """

    id: UUID | None = Field(
        default=None,
        description="The unique identifier (database-generated)."
    )
    product_family_id: UUID = Field(
        ...,
        description="The product family this axis belongs to."
    )

    name: str = Field(
        ...,
        description="Internal axis name (lowercase, underscores: 'size', 'color', 'neck_finish')."
    )
    display_label: str = Field(
        ...,
        description="Human-readable label for UI (e.g., 'Size', 'Color', 'Neck Finish')."
    )
    sort_order: int = Field(
        default=0,
        description="Display order in UI (lower numbers appear first)."
    )

    # Schema.org mapping (optional)
    schema_property: str | None = Field(
        default=None,
        description="Schema.org property URL (e.g., 'https://schema.org/color')."
    )

    model_config = ConfigDict(from_attributes=True)


class VariantValue(BaseModel):
    """
    A specific value for a variant axis.

    Example: For axis "color":
    - Value 1: "Red" (display_label: "Red", sku_code: "RED", color_hex: "#FF0000")
    - Value 2: "Blue" (display_label: "Blue", sku_code: "BLU", color_hex: "#0000FF")

    Maps to: variant_values table in database.
    """

    id: UUID | None = Field(
        default=None,
        description="The unique identifier (database-generated)."
    )
    variant_axis_id: UUID = Field(
        ...,
        description="The variant axis this value belongs to."
    )

    value: str = Field(
        ...,
        description="Internal value (e.g., 'S', 'Red', '500ml', '99%')."
    )
    display_label: str | None = Field(
        default=None,
        description="Optional pretty label for UI (e.g., 'Small', 'Extra Large')."
    )

    # SKU generation
    sku_code: str = Field(
        ...,
        description="Code used in SKU generation (uppercase, alphanumeric, hyphens: 'S', 'RED', '500ML')."
    )

    # Visual representation (for color/pattern swatches)
    color_hex: str | None = Field(
        default=None,
        description="Hex color code for color swatches (e.g., '#FF0000')."
    )
    image_url: str | None = Field(
        default=None,
        description="URL to swatch or pattern image."
    )

    # Pricing modifier (optional)
    price_adjustment: Decimal = Field(
        default=Decimal("0"),
        description="Price adjustment vs base_price (+/- amount, e.g., Decimal('5.00') adds ₹5)."
    )

    # Display order
    sort_order: int = Field(
        default=0,
        description="Display order within axis (lower numbers appear first)."
    )

    # Metadata
    is_active: bool = Field(
        default=True,
        description="Whether this value is active and available."
    )

    model_config = ConfigDict(from_attributes=True)


class ProductVariant(BaseModel):
    """
    An individual SKU representing a specific combination of variant values.

    Example: "Nike Air Max - Red, Size 10" (SKU: NKE-AIR-MAX-RED-10)
    - Linked to product_family "Nike Air Max"
    - Linked to variant_value "Red" (axis: color)
    - Linked to variant_value "10" (axis: size)

    This is the NEW model aligned with normalized database schema.
    Use this instead of legacy `Product` model for new workflows.

    Maps to: products table in database.
    """

    id: UUID | None = Field(
        default=None,
        description="The unique identifier (database-generated)."
    )
    company_id: str | None = Field(
        default=None,
        description="Company identifier (optional for single-tenant, required in database)."
    )
    product_family_id: UUID = Field(
        ...,
        description="The product family this variant belongs to."
    )

    # SKU (unique identifier)
    sku: str = Field(
        ...,
        description="Unique SKU code (e.g., 'PAV-BTL-500ML-28PCO-CLR' from family + variant values)."
    )

    # Name (optional - can be auto-generated from family + variants)
    name: str | None = Field(
        default=None,
        description="Variant name (e.g., '500ml PET Bottle - Clear - 28mm PCO'). NULL = auto-generate."
    )

    # Pricing (overrides base_price if set)
    price: Decimal | None = Field(
        default=None,
        description="Variant-specific price (overrides product_family.base_price if set)."
    )
    sale_price: Decimal | None = Field(
        default=None,
        description="Sale price (must be < price if set)."
    )
    sale_price_start: date | None = Field(
        default=None,
        description="Sale period start date."
    )
    sale_price_end: date | None = Field(
        default=None,
        description="Sale period end date."
    )

    # Inventory
    availability: Literal["in_stock", "out_of_stock", "preorder", "available_for_order", "discontinued"] = Field(
        default="in_stock",
        description="Stock availability status."
    )
    stock_quantity: int | None = Field(
        default=None,
        description="Current stock quantity (NULL = not tracked)."
    )
    low_stock_threshold: int = Field(
        default=5,
        description="Alert threshold for low stock."
    )

    # Preorder
    preorder_date: date | None = Field(
        default=None,
        description="Expected shipping date for preorder items."
    )

    # Product page URL
    link: str | None = Field(
        default=None,
        description="URL to product page (e.g., 'https://pavisha.com/products/bottle-500ml-clear')."
    )

    # Extensible attributes (variant-specific overrides)
    custom_attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Variant-specific attributes (overrides product_family.custom_attributes)."
    )

    # Metadata
    is_primary_variant: bool = Field(
        default=False,
        description="Whether this is the featured/default variant for the family."
    )
    is_active: bool = Field(
        default=True,
        description="Whether this variant is active and available."
    )
    created_at: datetime | None = Field(
        default=None,
        description="Creation timestamp (database-generated)."
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp (database-generated)."
    )

    model_config = ConfigDict(from_attributes=True)


class ProductVariantValue(BaseModel):
    """
    Junction table linking a product variant to its specific variant values.

    Example: Product "PAV-BTL-500ML-CLR-28PCO" links to:
    - variant_value "500ML" (axis: capacity)
    - variant_value "CLR" (axis: color)
    - variant_value "28PCO" (axis: neck_finish)

    Maps to: product_variant_values table in database.
    """

    product_id: UUID = Field(
        ...,
        description="The product variant ID."
    )
    variant_value_id: UUID = Field(
        ...,
        description="The variant value ID."
    )

    model_config = ConfigDict(from_attributes=True)


class CustomerSegment(BaseModel):
    """
    Defines a customer segment and its messaging strategy for a product family.

    Example: For "PET Bottles" product family:
    - Segment 1: B2B (target: beverage manufacturers, tone: professional)
    - Segment 2: B2C (target: households, tone: casual)

    Maps to: customer_segments table in database.
    """

    id: UUID | None = Field(
        default=None,
        description="The unique identifier (database-generated)."
    )
    company_id: str | None = Field(
        default=None,
        description="Company identifier (optional for single-tenant, required in database)."
    )
    product_family_id: UUID = Field(
        ...,
        description="The product family this segment applies to."
    )

    # Segment definition
    segment_type: Literal["B2B", "B2C", "D2C"] = Field(
        ...,
        description="Type of customer segment."
    )

    # Audience definition
    target_audience: str = Field(
        ...,
        description="Description of target audience (e.g., 'Food processing manufacturers', 'Health-conscious families')."
    )
    use_cases: list[str] = Field(
        default_factory=list,
        description="Primary use cases for this segment (e.g., ['Beverage bottling', 'Bulk packaging'])."
    )

    # Messaging strategy
    benefits_focus: list[str] = Field(
        default_factory=list,
        description="Key benefits to emphasize (e.g., ['Cost efficiency', 'Bulk discounts', 'Reliable supply'])."
    )
    content_tone: Literal["professional", "casual", "luxury", "playful", "traditional"] = Field(
        ...,
        description="Content tone for marketing materials."
    )
    marketing_channels: list[str] = Field(
        default_factory=list,
        description="Preferred marketing channels (e.g., ['LinkedIn', 'Trade shows', 'Email'])."
    )

    # Pricing strategy (text description, not actual prices)
    pricing_strategy: str | None = Field(
        default=None,
        description="Pricing approach description (e.g., 'Bulk discounts with MOQ 1000 units')."
    )

    # Metadata
    created_at: datetime | None = Field(
        default=None,
        description="Creation timestamp (database-generated)."
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp (database-generated)."
    )

    model_config = ConfigDict(from_attributes=True)


class ProductFamilyIndustry(BaseModel):
    """
    Links a product family to target industries with industry-specific messaging.

    Example: For "PET Bottles" product family:
    - Industry 1: NAICS 311 (Food Manufacturing) - use_cases: ['Juice bottling', 'Sauce packaging']
    - Industry 2: NAICS 3121 (Beverage Manufacturing) - use_cases: ['Soda bottling', 'Water packaging']

    Maps to: product_family_industries table in database.
    """

    id: UUID | None = Field(
        default=None,
        description="The unique identifier (database-generated)."
    )
    company_id: str | None = Field(
        default=None,
        description="Company identifier (optional for single-tenant, required in database)."
    )
    product_family_id: UUID = Field(
        ...,
        description="The product family this industry link applies to."
    )
    naics_code: str = Field(
        ...,
        description="NAICS 2022 industry code (e.g., '311', '3121')."
    )

    # Industry-specific messaging
    use_cases: list[str] = Field(
        default_factory=list,
        description="Industry-specific use cases (e.g., ['Juice bottling', 'Beverage packaging'])."
    )
    messaging_angle: str | None = Field(
        default=None,
        description="Industry-specific messaging angle (e.g., 'Food-grade certification for regulatory compliance')."
    )

    # Priority
    is_primary: bool = Field(
        default=False,
        description="Whether this is the primary industry for the product family."
    )

    created_at: datetime | None = Field(
        default=None,
        description="Creation timestamp (database-generated)."
    )

    model_config = ConfigDict(from_attributes=True)
