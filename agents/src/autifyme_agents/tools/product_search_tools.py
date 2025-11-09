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
    """
    axis_id: str = Field(..., description="UUID of variant axis")
    name: str = Field(..., description="Internal axis name (e.g., 'capacity', 'color')")
    display_label: str = Field(..., description="Human-readable label (e.g., 'Capacity', 'Color')")
    sort_order: int = Field(..., description="Display order in UI")


class VariantValueInfo(BaseModel):
    """Variant value from an existing product family.

    Represents a specific value for a variant axis (e.g., '500ml' for capacity, 'Clear' for color).
    Includes SKU code used in pattern generation.
    """
    value_id: str = Field(..., description="UUID of variant value")
    axis_id: str = Field(..., description="Parent variant axis UUID")
    axis_name: str = Field(..., description="Parent axis name for grouping")
    value: str = Field(..., description="Internal value (e.g., '500ml', 'Clear')")
    display_label: str | None = Field(None, description="Optional UI label")
    sku_code: str = Field(..., description="SKU code (e.g., '500ML', 'CLR')")
    sort_order: int = Field(..., description="Display order within axis")


class ProductFamilyMatch(BaseModel):
    """A single product family match result."""

    family_id: str = Field(..., description="UUID of matched product family")
    product_group_id: str = Field(..., description="Business identifier (e.g., 'PACK-PET-JAR')")
    name: str = Field(..., description="Product family name")
    brand: str = Field(..., description="Brand name")
    material: str | None = Field(None, description="Primary material")
    sku_prefix: str = Field(..., description="SKU prefix")
    base_price: float = Field(..., description="Base price")

    # Variant configuration (for add_variant scenarios)
    variant_axes: list[VariantAxisInfo] | None = Field(
        None,
        description="Variant axes configured for this family (enables extending existing SKU patterns)"
    )
    variant_values: list[VariantValueInfo] | None = Field(
        None,
        description="Existing variant values per axis (for SKU pattern consistency)"
    )

    # Match analysis
    match_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall confidence score"
    )
    match_type: str = Field(
        ...,
        description="Type of match: 'exact', 'variant_candidate', 'similar', 'weak'"
    )
    match_factors: dict[str, Any] = Field(
        ...,
        description="Breakdown of what matched: business_id, name, brand, material"
    )
    reasoning: str = Field(
        ..., description="Human-readable explanation of why this matched"
    )


class ProductFamilySearchResult(BaseModel):
    """Results from product family search."""

    query_summary: str = Field(..., description="Summary of search criteria")
    matches: list[ProductFamilyMatch] = Field(
        default_factory=list, description="Ranked matches (best first)"
    )
    total_found: int = Field(..., description="Total families found in search")
    recommendation: str = Field(
        ...,
        description="Suggested action: 'create_new', 'update_existing', 'add_variant', 'ask_user'"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in recommendation"
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
            filters = {"is_active": True}
            if product_group_id:
                # Exact match on business ID
                filters["product_group_id"] = product_group_id.upper()
            elif brand:
                # If no business_id, filter by brand at minimum
                filters["brand"] = brand

            # Execute query using port method
            response_data = await storage.query_advanced(
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
