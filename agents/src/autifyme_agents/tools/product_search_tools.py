"""Product Family Search Tools - Intelligent catalog matching for autonomous decisions.

Architecture:
- Specialists use these tools to find existing product families
- Fuzzy matching on business_id, name, brand, material
- Returns confidence scores for autonomous decision-making
- PM uses results to decide: create new, update existing, or ask user

Design Philosophy:
- Autonomous: High-confidence matches enable auto-decisions
- Intelligent: Multi-factor matching with reasoning
- Self-improving: Confidence thresholds tunable over time
"""

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from autifyme_agents.core.exceptions import classify_api_error
from autifyme_agents.core.ports import StorageInterface

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class VariantAxisInfo(BaseModel):
    """Variant axis definition from an existing product family.

    Represents a dimension along which variants differ (e.g., capacity, color, neck_finish).
    Used when adding variants to existing families to maintain SKU pattern consistency.

    Examples:
        Capacity axis:
            VariantAxisInfo(
                axis_id="660e8400-e29b-41d4-a716-446655440000",
                name="capacity",
                display_label="Capacity",
                sort_order=1
            )

        Color axis:
            VariantAxisInfo(
                axis_id="660e8401-e29b-41d4-a716-446655440000",
                name="color",
                display_label="Color",
                sort_order=2
            )
    """
    axis_id: str = Field(
        ...,
        description=(
            "UUID of variant axis in database. "
            "Used to create new variant_values referencing this axis. "
            "Example: '660e8400-e29b-41d4-a716-446655440000'."
        )
    )
    name: str = Field(
        ...,
        description=(
            "Internal axis name (lowercase, underscored). "
            "Examples: 'capacity', 'color', 'neck_finish', 'material', 'closure_type'. "
            "Used in backend logic and SKU pattern generation."
        )
    )
    display_label: str = Field(
        ...,
        description=(
            "Human-readable label for UI display (title case). "
            "Examples: 'Capacity', 'Color', 'Neck Finish', 'Closure Type'. "
            "Shown to users in product catalogs and variant selectors."
        )
    )
    sort_order: int = Field(
        ...,
        description=(
            "Display order in UI and SKU pattern (1-indexed). "
            "Lower numbers appear first. "
            "Example: Capacity (sort_order=1) appears before Color (sort_order=2) in SKU: BOTTLE-PET-500ML-CLEAR. "
            "Determines variant value sequence in generated SKUs."
        )
    )


class VariantValueInfo(BaseModel):
    """Variant value from an existing product family.

    Represents a specific value for a variant axis (e.g., '500ml' for capacity, 'Clear' for color).
    Includes SKU code used in pattern generation.

    Examples:
        500ml capacity value:
            VariantValueInfo(
                value_id="770e8400-e29b-41d4-a716-446655440000",
                axis_id="660e8400-e29b-41d4-a716-446655440000",
                axis_name="capacity",
                value="500ml",
                display_label="500ml",
                sku_code="500ML",
                sort_order=1
            )

        Clear color value:
            VariantValueInfo(
                value_id="770e8401-e29b-41d4-a716-446655440000",
                axis_id="660e8401-e29b-41d4-a716-446655440000",
                axis_name="color",
                value="Clear",
                display_label="Clear",
                sku_code="CLR",
                sort_order=1
            )

        Amber color value:
            VariantValueInfo(
                value_id="770e8402-e29b-41d4-a716-446655440000",
                axis_id="660e8401-e29b-41d4-a716-446655440000",
                axis_name="color",
                value="Amber",
                display_label="Amber",
                sku_code="AMB",
                sort_order=2
            )
    """
    value_id: str = Field(
        ...,
        description=(
            "UUID of variant value in database. "
            "Referenced in product_variant_values join table for SKU composition. "
            "Example: '770e8400-e29b-41d4-a716-446655440000'."
        )
    )
    axis_id: str = Field(
        ...,
        description=(
            "Parent variant axis UUID this value belongs to. "
            "Groups values under axis (e.g., all capacity values share same axis_id). "
            "Example: '660e8400-e29b-41d4-a716-446655440000' for capacity axis."
        )
    )
    axis_name: str = Field(
        ...,
        description=(
            "Parent axis name for display grouping (lowercase, underscored). "
            "Examples: 'capacity', 'color', 'neck_finish'. "
            "Use to group variant values by axis in UI (Capacity: 500ml, 1L, 2L | Color: Clear, Amber)."
        )
    )
    value: str = Field(
        ...,
        description=(
            "Internal value identifier (mixed case, human-readable). "
            "Examples: '500ml', '1L', 'Clear', 'Amber', '28mm', '38mm Screw Cap'. "
            "Exact string stored in database and shown in catalogs."
        )
    )
    display_label: str | None = Field(
        None,
        description=(
            "Optional UI label (overrides value for display if provided). "
            "Use when value differs from display (e.g., value='PET', display_label='Polyethylene Terephthalate'). "
            "None means use value field for display. "
            "Examples: '500 milliliters', 'Crystal Clear', 'Amber Tint'."
        )
    )
    sku_code: str = Field(
        ...,
        description=(
            "SKU code segment for pattern generation (uppercase, concise). "
            "Examples: '500ML', '1L', '2L', 'CLR', 'AMB', '28MM', '38SC'. "
            "Combined with family sku_prefix and other axis codes to form complete SKU. "
            "Pattern: {family_prefix}-{axis1_code}-{axis2_code}-... → BOTTLE-PET-500ML-CLR."
        )
    )
    sort_order: int = Field(
        ...,
        description=(
            "Display order within parent axis (1-indexed). "
            "Lower numbers appear first in UI dropdowns and SKU listings. "
            "Example: 500ml (sort_order=1), 1L (sort_order=2), 2L (sort_order=3) shown in ascending capacity order."
        )
    )


class ProductFamilyMatch(BaseModel):
    """A single product family match result with confidence scoring.

    Returned by search_product_families tool for intelligent decision-making.
    Includes variant configuration to enable adding new variants to existing families.

    Examples:
        Exact match (business_id + high name similarity):
            ProductFamilyMatch(
                family_id="550e8400-e29b-41d4-a716-446655440000",
                product_group_id="PACK-PET-JAR",
                name="PET Jars",
                brand="Pavisha",
                material="PET",
                sku_prefix="JAR-PET",
                base_price=22.50,
                variant_axes=[
                    VariantAxisInfo(axis_id="...", name="capacity", display_label="Capacity", sort_order=1),
                    VariantAxisInfo(axis_id="...", name="color", display_label="Color", sort_order=2)
                ],
                variant_values=[
                    VariantValueInfo(value_id="...", axis_name="capacity", value="500ml", sku_code="500ML", ...),
                    VariantValueInfo(value_id="...", axis_name="capacity", value="1L", sku_code="1L", ...),
                    VariantValueInfo(value_id="...", axis_name="color", value="Clear", sku_code="CLR", ...)
                ],
                match_score=0.95,
                match_type="exact",
                match_factors={
                    "business_id_match": True,
                    "name_similarity": 0.85,
                    "brand_match": True,
                    "material_match": True
                },
                reasoning="Exact (95% confidence): Exact business ID match, High name similarity (85%), Same brand, Same material"
            )

        Variant candidate (high name similarity, same brand, no business_id):
            ProductFamilyMatch(
                family_id="550e8401-e29b-41d4-a716-446655440000",
                product_group_id="PACK-PET-BOTTLE",
                name="PET Bottles",
                brand="Pavisha",
                material="PET",
                sku_prefix="BOTTLE-PET",
                base_price=25.00,
                variant_axes=[VariantAxisInfo(...)],  # Full variant config included
                variant_values=[VariantValueInfo(...)],
                match_score=0.75,
                match_type="variant_candidate",
                match_factors={
                    "business_id_match": False,
                    "name_similarity": 0.80,
                    "brand_match": True,
                    "material_match": True
                },
                reasoning="Variant Candidate (75% confidence): High name similarity (80%), Same brand, Same material"
            )

        Similar (moderate name similarity, different brand):
            ProductFamilyMatch(
                family_id="550e8402-e29b-41d4-a716-446655440000",
                product_group_id="PACK-HDPE-BOTTLE",
                name="HDPE Bottles",
                brand="Generic",
                material="HDPE",
                sku_prefix="BOTTLE-HDPE",
                base_price=30.00,
                variant_axes=None,
                variant_values=None,
                match_score=0.50,
                match_type="similar",
                match_factors={
                    "business_id_match": False,
                    "name_similarity": 0.65,
                    "brand_match": False,
                    "material_match": False
                },
                reasoning="Similar (50% confidence): Moderate name similarity (65%)"
            )
    """

    family_id: str = Field(
        ...,
        description=(
            "UUID of matched product family in database. "
            "Use to reference this family in update/add_variant operations. "
            "Example: '550e8400-e29b-41d4-a716-446655440000'."
        )
    )
    product_group_id: str = Field(
        ...,
        description=(
            "Business identifier for this product family (unique, uppercase). "
            "Examples: 'PACK-PET-JAR', 'PACK-HDPE-BOTTLE', 'PACK-GLASS-JAR'. "
            "Strongest matching signal - exact business_id match indicates same product family."
        )
    )
    name: str = Field(
        ...,
        description=(
            "Product family name (human-readable). "
            "Examples: 'PET Jars', 'HDPE Bottles', 'Glass Jars 200ml-5L'. "
            "Used for fuzzy name matching and user presentation."
        )
    )
    brand: str = Field(
        ...,
        description=(
            "Brand name for this product family. "
            "Examples: 'Pavisha', 'Acme', 'Generic'. "
            "Brand match boosts confidence score - same brand suggests related products."
        )
    )
    material: str | None = Field(
        None,
        description=(
            "Primary material (uppercase). "
            "Examples: 'PET', 'HDPE', 'Glass', 'Aluminum'. "
            "None if material not specified in catalog. "
            "Material match contributes to overall confidence."
        )
    )
    sku_prefix: str = Field(
        ...,
        description=(
            "SKU prefix for all products in this family (uppercase with hyphens). "
            "Examples: 'JAR-PET', 'BOTTLE-HDPE', 'CONT-GLASS'. "
            "Combined with variant codes to form complete SKUs: JAR-PET-500ML-CLR."
        )
    )
    base_price: float = Field(
        ...,
        description=(
            "Base price for this family (currency units, typically INR). "
            "Example: 22.50 (₹22.50). "
            "Individual variants may adjust from base using price modifiers."
        )
    )

    # Variant configuration (for add_variant scenarios)
    variant_axes: list[VariantAxisInfo] | None = Field(
        None,
        description=(
            "Variant axes configured for this family (enables extending existing SKU patterns). "
            "None if no axes configured (simple product family). "
            "Present for variant_candidate and exact matches to support add_variant workflow. "
            "Example: [VariantAxisInfo(name='capacity', ...), VariantAxisInfo(name='color', ...)]."
        )
    )
    variant_values: list[VariantValueInfo] | None = Field(
        None,
        description=(
            "Existing variant values per axis (for SKU pattern consistency). "
            "None if no values exist or no axes configured. "
            "Use to understand current variant coverage and maintain naming consistency. "
            "Example: [VariantValueInfo(axis_name='capacity', value='500ml', sku_code='500ML', ...), ...]."
        )
    )

    # Match analysis
    match_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Overall confidence score (0.0-1.0). "
            "Calculated from: business_id_match (0.5 weight), name_similarity (0.3), brand_match (0.15), material_match (0.05). "
            "Thresholds: >=0.9 exact, >=0.7 variant_candidate, >=0.4 similar, <0.4 weak. "
            "Example: 0.95 (95% confidence) indicates very strong match."
        )
    )
    match_type: str = Field(
        ...,
        description=(
            "Type of match classification. Options: "
            "'exact' (>=0.9 score, likely same family - update/query), "
            "'variant_candidate' (>=0.7 score, likely new variant of existing family - add_variant), "
            "'similar' (>=0.4 score, related but distinct - show user for confirmation), "
            "'weak' (<0.4 score, low confidence - probably different family)."
        )
    )
    match_factors: dict[str, Any] = Field(
        ...,
        description=(
            "Breakdown of matching factors for transparency. "
            "Structure: {"
            "  'business_id_match': bool (True if exact business_id match), "
            "  'name_similarity': float (0.0-1.0 token-based Jaccard similarity), "
            "  'brand_match': bool (True if exact brand match), "
            "  'material_match': bool (True if exact material match)"
            "}. "
            "Example: {'business_id_match': True, 'name_similarity': 0.85, 'brand_match': True, 'material_match': False}."
        )
    )
    reasoning: str = Field(
        ...,
        description=(
            "Human-readable explanation of why this matched (for user transparency). "
            "Format: '{match_type} ({score}% confidence): {reasons}'. "
            "Examples: "
            "'Exact (95% confidence): Exact business ID match, High name similarity (85%), Same brand', "
            "'Variant Candidate (75% confidence): High name similarity (80%), Same brand, Same material', "
            "'Similar (50% confidence): Moderate name similarity (65%)', "
            "'Weak (25% confidence): Low similarity across all factors'."
        )
    )


class ProductFamilySearchResult(BaseModel):
    """Results from product family search with autonomous recommendation.

    Enables intelligent decision-making: create_new, update_existing, add_variant, or ask_user.
    Specialists use this to determine workflow path without PM intervention for high-confidence matches.

    Examples:
        No matches found → create_new:
            ProductFamilySearchResult(
                query_summary="Searched for: business_id=None, name=Glass Containers, brand=Pavisha, material=Glass",
                matches=[],
                total_found=0,
                recommendation="create_new",
                confidence=0.95
            )

        Exact match → update_existing:
            ProductFamilySearchResult(
                query_summary="Searched for: business_id=PACK-PET-JAR, name=PET Jars, brand=Pavisha, material=PET. Found 1 potential matches.",
                matches=[
                    ProductFamilyMatch(
                        family_id="550e8400-...",
                        name="PET Jars",
                        match_score=0.95,
                        match_type="exact",
                        reasoning="Exact (95% confidence): Exact business ID match, High name similarity (85%), Same brand, Same material"
                    )
                ],
                total_found=1,
                recommendation="update_existing",
                confidence=0.95
            )

        High similarity, same brand → add_variant:
            ProductFamilySearchResult(
                query_summary="Searched for: business_id=None, name=PET Bottles 500ml Clear, brand=Pavisha, material=PET. Found 1 potential matches.",
                matches=[
                    ProductFamilyMatch(
                        family_id="550e8401-...",
                        product_group_id="PACK-PET-BOTTLE",
                        name="PET Bottles",
                        brand="Pavisha",
                        material="PET",
                        variant_axes=[VariantAxisInfo(...)],  # Existing axes
                        variant_values=[VariantValueInfo(...)],  # Current values
                        match_score=0.75,
                        match_type="variant_candidate",
                        reasoning="Variant Candidate (75% confidence): High name similarity (80%), Same brand, Same material"
                    )
                ],
                total_found=1,
                recommendation="add_variant",
                confidence=0.75
            )

        Multiple similar matches → ask_user:
            ProductFamilySearchResult(
                query_summary="Searched for: business_id=None, name=Bottles, brand=None, material=None. Found 3 potential matches.",
                matches=[
                    ProductFamilyMatch(name="PET Bottles", match_score=0.55, match_type="similar", ...),
                    ProductFamilyMatch(name="HDPE Bottles", match_score=0.52, match_type="similar", ...),
                    ProductFamilyMatch(name="Glass Bottles", match_score=0.50, match_type="similar", ...)
                ],
                total_found=3,
                recommendation="ask_user",
                confidence=0.40
            )
    """

    query_summary: str = Field(
        ...,
        description=(
            "Summary of search criteria and results count. "
            "Format: 'Searched for: business_id={val}, name={val}, brand={val}, material={val}. Found {N} potential matches.' "
            "Example: 'Searched for: business_id=PACK-PET-JAR, name=PET Jars, brand=Pavisha, material=PET. Found 1 potential matches.'. "
            "Used for logging and specialist reasoning transparency."
        )
    )
    matches: list[ProductFamilyMatch] = Field(
        default_factory=list,
        description=(
            "Ranked matches sorted by match_score descending (best match first). "
            "Empty list if no matches found (score <= 0.2 threshold). "
            "Limited to top 5-10 matches to keep response concise. "
            "Each match includes full family details and variant configuration for decision-making."
        )
    )
    total_found: int = Field(
        ...,
        description=(
            "Total number of families found matching search criteria (before score threshold filtering). "
            "May be higher than len(matches) if weak matches were filtered out. "
            "Example: total_found=15 but matches=[top 5] after filtering score < 0.2. "
            "Used to inform user about breadth of search results."
        )
    )
    recommendation: str = Field(
        ...,
        description=(
            "Suggested autonomous action based on match analysis. Options: "
            "'create_new' (no matches or all weak, confidence ~0.80-0.95), "
            "'update_existing' (exact match found, confidence ~0.90-0.95), "
            "'add_variant' (variant_candidate match, confidence ~0.70-0.80), "
            "'ask_user' (multiple similar matches or ambiguous, confidence ~0.40-0.60). "
            "Specialist should execute recommendation if confidence >= 0.70, otherwise escalate to PM/user."
        )
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Confidence in recommendation (0.0-1.0). "
            "Derived from best match score and match count. "
            "Thresholds: "
            ">=0.90 (very high - auto-execute update_existing), "
            ">=0.70 (high - auto-execute add_variant), "
            ">=0.60 (moderate - show user for confirmation), "
            "<0.60 (low - ask user to clarify or verify). "
            "Example: 0.95 for exact business_id match, 0.40 for multiple ambiguous similar matches."
        )
    )


class SearchProductFamiliesInput(BaseModel):
    """Input schema for search_product_families tool (OpenAI-compatible)."""

    model_config = {"extra": "forbid"}  # Generates additionalProperties: false

    product_group_id: str | None = Field(
        default=None,
        description=(
            "Business identifier for exact match (e.g., 'PACK-PET-JAR'). "
            "Strongest signal - if provided, prioritizes exact business ID matches. "
            "Use when you have structured business identifier from user or PM."
        )
    )
    name: str | None = Field(
        default=None,
        description=(
            "Product family name to fuzzy match (e.g., 'PET Bottles', 'Glass Jars'). "
            "REQUIRED for meaningful search - uses token-based similarity scoring. "
            "Provide descriptive product name from user request."
        )
    )
    brand: str | None = Field(
        default=None,
        description=(
            "Brand name for filtering and similarity scoring (e.g., 'Acme', 'PavCorp'). "
            "Boosts match confidence when brand matches. Filters results if no business_id provided."
        )
    )
    material: str | None = Field(
        default=None,
        description=(
            "Material for additional match scoring (e.g., 'PET', 'Glass', 'Aluminum'). "
            "Contributes to overall match confidence. Use when material is known from request."
        )
    )
    limit: int = Field(
        default=5,
        description="Max results to return (default: 5, max: 10). Increase if expecting multiple similar families."
    )


# =============================================================================
# Matching Logic
# =============================================================================


def _calculate_match_score(
    query_business_id: str | None,
    query_name: str,
    query_brand: str,
    query_material: str | None,
    existing_family: dict[str, Any],
) -> tuple[float, dict[str, Any], str]:
    """Calculate match score between query and existing family.

    Returns:
        Tuple of (score, factors, match_type)
    """
    factors = {
        "business_id_match": False,
        "name_similarity": 0.0,
        "brand_match": False,
        "material_match": False,
    }

    score_components = []

    # Business ID match (strongest signal - 0.5 weight)
    if query_business_id and query_business_id.upper() == existing_family.get("product_group_id", "").upper():
        factors["business_id_match"] = True
        score_components.append(0.5)

    # Name similarity (0.3 weight)
    query_name_normalized = query_name.lower().strip()
    existing_name_normalized = existing_family.get("name", "").lower().strip()

    # Simple token-based similarity
    query_tokens = set(query_name_normalized.split())
    existing_tokens = set(existing_name_normalized.split())

    if query_tokens and existing_tokens:
        intersection = query_tokens & existing_tokens
        union = query_tokens | existing_tokens
        name_similarity = len(intersection) / len(union)
        factors["name_similarity"] = name_similarity
        score_components.append(name_similarity * 0.3)

    # Brand match (0.15 weight) - only apply if brand provided in query
    if query_brand and query_brand.lower().strip() and query_brand.lower().strip() == existing_family.get("brand", "").lower().strip():
        factors["brand_match"] = True
        score_components.append(0.15)

    # Material match (0.05 weight)
    if query_material and existing_family.get("material") and query_material.lower().strip() == existing_family.get("material", "").lower().strip():
        factors["material_match"] = True
        score_components.append(0.05)

    total_score = sum(score_components)

    # Determine match type
    if total_score >= 0.9:
        match_type = "exact"
    elif total_score >= 0.7:
        match_type = "variant_candidate"
    elif total_score >= 0.4:
        match_type = "similar"
    else:
        match_type = "weak"

    return total_score, factors, match_type


def _build_reasoning(factors: dict[str, Any], match_type: str, score: float) -> str:
    """Build human-readable reasoning for match."""
    reasons = []

    if factors["business_id_match"]:
        reasons.append("Exact business ID match")

    if factors["name_similarity"] > 0.7:
        reasons.append(f"High name similarity ({factors['name_similarity']:.0%})")
    elif factors["name_similarity"] > 0.4:
        reasons.append(f"Moderate name similarity ({factors['name_similarity']:.0%})")

    if factors["brand_match"]:
        reasons.append("Same brand")

    if factors["material_match"]:
        reasons.append("Same material")

    if not reasons:
        reasons.append("Low similarity across all factors")

    reasoning = f"{match_type.replace('_', ' ').title()} ({score:.0%} confidence): {', '.join(reasons)}"
    return reasoning


def _recommend_action(matches: list[ProductFamilyMatch]) -> tuple[str, float]:
    """Recommend action based on match results.

    Returns:
        Tuple of (action, confidence)
    """
    if not matches:
        return "create_new", 0.95

    best_match = matches[0]

    # Exact match - update existing
    if best_match.match_type == "exact":
        return "update_existing", best_match.match_score

    # Variant candidate - likely new variant of existing family
    if best_match.match_type == "variant_candidate":
        return "add_variant", best_match.match_score

    # Multiple similar matches - ambiguous
    if len(matches) > 1 and matches[1].match_score > 0.5:
        return "ask_user", 0.4

    # Single similar match - probably new family but show user the similar one
    if best_match.match_type == "similar":
        return "ask_user", 0.6

    # Weak or no matches - create new
    return "create_new", 0.8


# =============================================================================
# Search Tool
# =============================================================================


def create_search_product_families_tool(storage: StorageInterface) -> object:
    """Create tool for searching existing product families.

    Tool is given to specialists (Product Architecture) for intelligent matching.

    Args:
        storage: Storage adapter for database operations

    Returns:
        LangChain tool for product family search
    """

    async def _search_product_families_impl(
        product_group_id: str | None = None,
        name: str | None = None,
        brand: str | None = None,
        material: str | None = None,
        limit: int = 5,
    ) -> ProductFamilySearchResult:
        """Search for existing product families in catalog using fuzzy matching.

        Use this tool BEFORE creating a new product family to check if it already exists
        or if the incoming product is a new variant of an existing family.

        Matching logic:
        - Exact business_id match = highest confidence (exact match or update)
        - High name similarity + same brand = variant candidate
        - Moderate similarity = ask user to confirm
        - Low/no matches = create new family

        Args:
            product_group_id: Business identifier to search for (e.g., "PACK-PET-JAR")
            name: Product family name to match against
            brand: Brand name to filter by
            material: Material to match (e.g., "PET", "Glass")
            limit: Max number of results to return (default 5)

        Returns:
            ProductFamilySearchResult with ranked matches and recommendation
        """
        try:
            # Build query - join with variant axes and values for complete SKU config
            # Nested select: product_families → variant_axes → variant_values
            filters: dict[str, Any] = {"is_active": True}
            if product_group_id:
                # Exact match on business ID
                filters["product_group_id"] = product_group_id.upper()
            elif brand:
                # If no business_id, filter by brand at minimum
                filters["brand"] = brand

            # Execute query using port method (type-safe)
            response_data = await storage.query_entities(
                table="product_families",
                filters=filters,
                relations=["variant_axes(id,name,display_label,sort_order,variant_values(id,value,display_label,sku_code,sort_order))"],
                limit=50  # Get more for fuzzy matching
            )

            if not response_data:
                return ProductFamilySearchResult(
                    query_summary=f"Searched for: business_id={product_group_id}, name={name}, brand={brand}",
                    matches=[],
                    total_found=0,
                    recommendation="create_new",
                    confidence=0.95,
                )

            # Calculate match scores for all results
            all_matches = []

            for family in response_data:
                score, factors, match_type = _calculate_match_score(
                    query_business_id=product_group_id,
                    query_name=name or "",
                    query_brand=brand or "",
                    query_material=material,
                    existing_family=family,
                )

                # Only include if score > 0.2 (filter out very weak matches)
                # Lower threshold allows name + material matches even without brand
                if score > 0.2:
                    reasoning = _build_reasoning(factors, match_type, score)

                    # Parse variant configuration if available
                    variant_axes_list = None
                    variant_values_list = None

                    if family.get("variant_axes"):
                        variant_axes_list = []
                        variant_values_list = []

                        for axis in family["variant_axes"]:
                            # Add axis info
                            variant_axes_list.append(VariantAxisInfo(
                                axis_id=axis["id"],
                                name=axis["name"],
                                display_label=axis["display_label"],
                                sort_order=axis["sort_order"],
                            ))

                            # Add all values for this axis
                            if axis.get("variant_values"):
                                for value in axis["variant_values"]:
                                    variant_values_list.append(VariantValueInfo(
                                        value_id=value["id"],
                                        axis_id=axis["id"],
                                        axis_name=axis["name"],
                                        value=value["value"],
                                        display_label=value.get("display_label"),
                                        sku_code=value["sku_code"],
                                        sort_order=value["sort_order"],
                                    ))

                    match = ProductFamilyMatch(
                        family_id=family["id"],
                        product_group_id=family["product_group_id"],
                        name=family["name"],
                        brand=family["brand"],
                        material=family.get("material"),
                        sku_prefix=family["sku_prefix"],
                        base_price=family["base_price"],
                        variant_axes=variant_axes_list,
                        variant_values=variant_values_list,
                        match_score=score,
                        match_type=match_type,
                        match_factors=factors,
                        reasoning=reasoning,
                    )
                    all_matches.append(match)

            # Sort by score (highest first)
            all_matches.sort(key=lambda m: m.match_score, reverse=True)

            # Take top N matches
            top_matches = all_matches[:limit]

            # Recommend action
            action, confidence = _recommend_action(top_matches)

            query_summary = (
                f"Searched for: business_id={product_group_id}, name={name}, brand={brand}, material={material}. "
                f"Found {len(all_matches)} potential matches."
            )

            return ProductFamilySearchResult(
                query_summary=query_summary,
                matches=top_matches,
                total_found=len(all_matches),
                recommendation=action,
                confidence=confidence,
            )

        except Exception as e:
            logger.error(
                "Product family search failed",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_msg": str(e),
                    "query_params": {
                        "product_group_id": product_group_id,
                        "name": name,
                        "brand": brand,
                    }
                }
            )
            raise classify_api_error(e, "search_product_families", "Supabase") from e

    return StructuredTool.from_function(
        func=_search_product_families_impl,
        name="search_product_families",
        description=(
            "Search for existing product families using intelligent fuzzy matching. "
            "WHEN TO USE: BEFORE creating new product families - checks if product already exists or is variant of existing family. "
            "Returns confidence scores (exact/variant_candidate/similar/weak) and recommendations (create_new/update_existing/add_variant/ask_user). "
            "Includes full variant configuration (axes, values, SKU codes) for extending existing patterns. "
            "CRITICAL: Use this for finding matches before CREATE operations. For READ operations on known entities, use query_database with filters instead."
        ),
        args_schema=SearchProductFamiliesInput,
    )
