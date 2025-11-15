"""
Taxonomy Specialist - Multi-system product classification expert.

Domain Expertise:
- Internal category hierarchy management
- Google Product Category taxonomy (for Google Shopping, Facebook Catalog)
- NAICS 2022 industry classification (for B2B multi-industry targeting)
- Cross-taxonomy mapping and alignment

Responsibilities:
- Classify products into internal category hierarchy
- Map to Google Product Category for platform compliance
- Identify relevant NAICS industries for B2B products
- Return TaxonomyClassificationDraft for PM review

Does NOT:
- Persist classifications (PM handles after approval)
- Generate marketing content (Content Specialist handles this)
- Determine pricing/positioning (Market Intelligence Specialist handles this)

Architecture Pattern:
- SubAgent dict format
- Returns structured Pydantic models
- PM orchestrates and approves
"""

import logging
from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, Field

from autifyme_agents.core.config import settings
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

# =============================================================================
# Data Models - Taxonomy Specialist Outputs
# =============================================================================


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


# =============================================================================
# Tool Factories - Taxonomy Classification
# =============================================================================


def create_find_relevant_categories_tool(storage: StorageInterface) -> object:
    """Factory: Create tool that searches internal category hierarchy."""

    @tool
    async def find_relevant_categories(
        product_name: str, product_description: str
    ) -> list[dict[str, Any]]:
        """
        Search internal category hierarchy for best matches.

        Args:
            product_name: Product name
            product_description: Product description

        Returns:
            List of matching categories with confidence scores
        """
        try:
            # Search categories by name/description similarity
            if settings.ENABLE_SEMANTIC_SEARCH:
                # TODO: Implement semantic search via embeddings when enabled
                raise NotImplementedError("Semantic search not yet implemented")

            # Fallback: Simple keyword-based search
            logger.warning(
                "Using keyword-based category search fallback. "
                "Enable ENABLE_SEMANTIC_SEARCH for improved accuracy via embeddings."
            )

            search_terms = (product_name + " " + product_description).lower().split()
            search_terms = [term for term in search_terms if len(term) > 3][:5]  # Top 5 keywords

            if not search_terms:
                return []

            # Query categories table using port method
            categories = await storage.query_entities(
                table="categories",
                filters={"is_active": True},
                columns=["id", "name", "slug", "description", "parent_id"]
            )

            if not categories:
                return []

            # Simple keyword matching
            matches = []
            for category in categories:
                cat_text = f"{category['name']} {category.get('description', '')}".lower()
                match_count = sum(1 for term in search_terms if term in cat_text)

                if match_count > 0:
                    # Calculate simple confidence
                    confidence = min(match_count / len(search_terms), 1.0)

                    matches.append({
                        "category_id": category["id"],
                        "name": category["name"],
                        "slug": category["slug"],
                        "parent_id": category.get("parent_id"),
                        "confidence": confidence,
                        "match_count": match_count,
                    })

            # Sort by confidence (match count)
            matches.sort(key=lambda x: (x["confidence"], x["match_count"]), reverse=True)

            return matches[:5]  # Top 5 matches

        except Exception as e:
            logger.error(
                "Failed to find relevant categories for product '%s': %s",
                product_name,
                e,
                exc_info=True
            )
            # Return empty list - specialist will note manual classification needed
            # This is acceptable degradation (manual fallback exists)
            return []

    return find_relevant_categories


@tool
def find_google_product_category(
    product_type: str, product_keywords: list[str]
) -> dict[str, Any]:
    """
    Find best Google Product Category match.

    Google Product Category is required for:
    - Google Shopping
    - Facebook Product Catalog
    - Instagram Shopping

    Args:
        product_type: General product type (e.g., "apparel", "packaging", "footwear")
        product_keywords: Specific keywords (e.g., ["t-shirt", "cotton", "casual"])

    Returns:
        Best Google category match with confidence

    Note: Phase 1 uses rule-based mapping. Phase 2 will add Google Taxonomy API integration.
    """
    # Check feature flag for Google Taxonomy API
    if settings.ENABLE_GOOGLE_TAXONOMY_API:
        # TODO: Implement Google Product Taxonomy API integration when enabled
        raise NotImplementedError("Google Product Taxonomy API not yet implemented")

    # Fallback: Simplified category mapping
    logger.warning(
        "Using rule-based Google category mapping fallback. "
        "Enable ENABLE_GOOGLE_TAXONOMY_API for official Google Taxonomy API integration."
    )

    category_map = {
        # Apparel
        "apparel": "Apparel & Accessories > Clothing",
        "clothing": "Apparel & Accessories > Clothing",
        "shirt": "Apparel & Accessories > Clothing > Shirts & Tops",
        "tshirt": "Apparel & Accessories > Clothing > Shirts & Tops",
        "t-shirt": "Apparel & Accessories > Clothing > Shirts & Tops",
        "pants": "Apparel & Accessories > Clothing > Pants",
        "dress": "Apparel & Accessories > Clothing > Dresses",
        # Footwear
        "footwear": "Apparel & Accessories > Shoes",
        "shoes": "Apparel & Accessories > Shoes",
        "sneakers": "Apparel & Accessories > Shoes > Athletic Shoes",
        "boots": "Apparel & Accessories > Shoes > Boots",
        # Accessories
        "bag": "Apparel & Accessories > Handbags, Wallets & Cases",
        "handbag": "Apparel & Accessories > Handbags, Wallets & Cases > Handbags",
        "wallet": "Apparel & Accessories > Handbags, Wallets & Cases > Wallets",
        # Packaging (B2B)
        "packaging": "Business & Industrial > Material Handling > Packaging & Shipping Supplies",
        "bottle": "Business & Industrial > Material Handling > Packaging & Shipping Supplies > Bottles",
        "container": "Business & Industrial > Material Handling > Packaging & Shipping Supplies > Containers",
        "box": "Business & Industrial > Material Handling > Packaging & Shipping Supplies > Boxes",
        # Default
        "": "Business & Industrial",
    }

    # Find best match
    best_match = None
    best_confidence = 0.0

    for keyword in [product_type] + product_keywords:
        keyword_lower = keyword.lower().strip()
        if keyword_lower in category_map:
            confidence = 0.9 if keyword == product_type else 0.7
            if confidence > best_confidence:
                best_match = category_map[keyword_lower]
                best_confidence = confidence

    # Fallback
    if not best_match:
        best_match = category_map[""]
        best_confidence = 0.3

    return {
        "category_path": best_match,
        "category_id": None,  # Phase 2: Get actual Google category ID
        "confidence": best_confidence,
        "reasoning": (
            f"Matched based on product type '{product_type}' and keywords {product_keywords[:3]}. "
            f"Phase 1 uses rule-based mapping; Phase 2 will integrate Google Taxonomy API for precision."
        ),
    }


def create_classify_into_industries_tool(storage: StorageInterface) -> object:
    """Factory: Create tool that classifies into NAICS industries."""

    @tool
    async def classify_into_industries(
        product_type: str,
        business_model: str,
        product_description: str,
    ) -> list[dict[str, Any]]:
        """
        Classify product into relevant NAICS 2022 industries.

        NAICS classification enables:
        - B2B multi-industry targeting
        - Industry-specific messaging
        - Compliance and certification tracking

        Args:
            product_type: Product type (e.g., "packaging", "apparel")
            business_model: B2B, B2C, or D2C
            product_description: Full product description

        Returns:
            List of relevant NAICS industries with use cases
        """
        try:
            # Query NAICS industries table using port method
            industries = await storage.query_entities(
                table="industries",
                filters={"is_active": True},
                columns=["naics_code", "label", "description", "level"]
            )

            if not industries:
                return []

            # Check feature flag for LLM-based classification
            if settings.ENABLE_LLM_INDUSTRY_CLASSIFICATION:
                # TODO: Implement LLM-based industry classification when enabled
                raise NotImplementedError("LLM-based industry classification not yet implemented")

            # Fallback: Simple keyword-based matching
            logger.warning(
                "Using keyword-based NAICS industry matching fallback. "
                "Enable ENABLE_LLM_INDUSTRY_CLASSIFICATION for LLM-powered precision."
            )

            search_terms = (product_type + " " + product_description).lower().split()
            search_terms = [term for term in search_terms if len(term) > 3][:10]

            matches = []
            for industry in industries:
                industry_text = (
                    f"{industry['label']} {industry.get('description', '')}"
                ).lower()

                match_count = sum(1 for term in search_terms if term in industry_text)

                if match_count > 0:
                    confidence = min(match_count / max(len(search_terms), 1), 1.0)

                    # B2B products more likely to match multiple industries
                    if business_model == "B2B":
                        confidence *= 1.2  # Boost B2B relevance
                        confidence = min(confidence, 1.0)

                    matches.append({
                        "naics_code": industry["naics_code"],
                        "label": industry["label"],
                        "description": industry.get("description"),
                        "level": industry["level"],
                        "confidence": confidence,
                        "match_count": match_count,
                    })

            # Sort by confidence
            matches.sort(key=lambda x: (x["confidence"], x["level"]), reverse=True)

            # Return top 5 matches
            return matches[:5]

        except Exception as e:
            logger.error(
                "Failed to classify product '%s' into industries: %s",
                product_type,
                e,
                exc_info=True
            )
            # Return empty list - specialist will note manual classification needed
            # This is acceptable degradation (manual fallback exists)
            return []

    return classify_into_industries


# =============================================================================
# Specialist Factory
# =============================================================================


def create_taxonomy_specialist(storage: StorageInterface) -> dict[str, Any]:
    """
    Create Taxonomy Specialist as SubAgent spec.

    Specialist Responsibilities:
    - Classify product into internal category hierarchy
    - Map to Google Product Category for platform compliance
    - Identify relevant NAICS industries for B2B targeting
    - Return TaxonomyClassificationDraft for PM review

    Architecture:
    - SubAgent dict format
    - Classification tools only (no persistence)
    - Returns structured Pydantic model
    - PM handles HITL and persistence

    Args:
        storage: Storage interface for database access (category/industry tables)

    Returns:
        SubAgent spec with classification tools
    """
    system_prompt = load_prompt("specialists/taxonomy_specialist.prompt")

    description = (
        "Classifies products into multiple taxonomy systems. "
        "Maps to internal categories, Google Product Category, and NAICS industries. "
        "Enables platform compliance (Google Shopping, Facebook) and B2B multi-industry targeting. "
        "Returns TaxonomyClassificationDraft for PM review."
    )

    # Tools for multi-taxonomy classification
    tools = [
        find_google_product_category,  # Rule-based Google category mapping
        create_find_relevant_categories_tool(storage),  # Internal category search
        create_classify_into_industries_tool(storage),  # NAICS classification
    ]

    return {
        "name": "taxonomy_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        "response_format": TaxonomyClassificationDraft,  # Enforce structured output
    }
