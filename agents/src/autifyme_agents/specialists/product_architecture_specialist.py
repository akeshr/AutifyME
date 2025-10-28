"""
Product Architecture Specialist - Analyzes product structure and variant composition.

Domain Expertise:
- Product structure analysis (family vs variants)
- Variant axis identification (dimensions that vary: size, color, material, etc.)
- SKU architecture design (naming conventions, combinations)
- Composition pattern understanding (how variants relate to family)
- **NEW: Intelligent catalog matching for autonomous create vs update decisions**

Responsibilities:
- **Search catalog FIRST** for existing product families (autonomous intelligence)
- Analyze multimodal input (user descriptions + images)
- Identify variant dimensions and values
- Calculate total SKU combinations
- Generate SKU naming patterns
- Recommend: create new, update existing, or add variant
- Return structured ProductArchitectureDraft with match analysis

Does NOT:
- Persist to database (PM handles persistence)
- Generate marketing content (Content Specialist handles this)
- Classify into taxonomy (Taxonomy Specialist handles this)

Architecture Pattern:
- SubAgent dict format (NOT create_agent)
- Returns structured Pydantic models with intelligent match recommendations
- PM orchestrates delegation and uses recommendations for autonomous decisions
"""

from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, Field

from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool
from autifyme_agents.tools.product_search_tools import ProductFamilySearchResult

# =============================================================================
# Data Models - Product Architecture Specialist Outputs
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


class ProductArchitectureDraft(BaseModel):
    """Complete product architecture analysis from Product Architecture Specialist."""

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

    # **NEW: Intelligent matching for autonomous decisions**
    catalog_match_analysis: ProductFamilySearchResult | None = Field(
        None,
        description="Results from catalog search - enables autonomous create vs update decisions"
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
# Tools - Product Architecture Analysis
# =============================================================================

# NOTE: calculate_sku_combinations and generate_sku_pattern tools removed.
# Modern LLMs can handle SKU calculations (basic multiplication) and pattern
# generation (string formatting) autonomously. Tools reserved for external
# system access only (database, APIs, vision).
#
# Specialist prompt includes instructions for:
# - SKU calculation: Multiply variant axis value counts
# - Pattern generation: Follow company conventions from state.company_profile
# - Existing family extension: Use patterns from search_product_families results


# =============================================================================
# Specialist Factory
# =============================================================================


def create_product_architecture_specialist(storage: StorageInterface | None = None) -> dict[str, Any]:
    """
    Create Product Architecture Specialist as SubAgent spec.

    Specialist Responsibilities:
    - **Search catalog FIRST** for existing product families (enables autonomous decisions)
    - Analyze product from multimodal input (images + user description)
    - Identify variant structure (axes and values)
    - Design SKU architecture (naming pattern, combinations)
    - Recommend action: create new / update existing / add variant
    - Return ProductArchitectureDraft with match analysis for PM

    Architecture:
    - SubAgent dict format (DeepAgents pattern)
    - Analysis + intelligent search tools
    - Returns structured Pydantic model with match recommendations
    - PM uses recommendations for autonomous create vs update decisions

    Args:
        storage: Storage interface for catalog search (required for intelligent matching)

    Returns:
        SubAgent spec with:
        - name: specialist identifier
        - description: delegation criteria
        - tools: analysis + search tools
        - system_prompt: domain expertise instructions
    """
    system_prompt = load_prompt("specialists/product_architecture_specialist.prompt")

    description = (
        "Analyzes product structure and designs variant architecture. "
        "Searches catalog for existing product families to determine if this is a new family, "
        "new variant of existing family, or update to existing product. "
        "Identifies variant dimensions (size, color, material, etc.), calculates SKU combinations, "
        "generates naming patterns, and recommends action. "
        "Returns ProductArchitectureDraft with catalog match analysis."
    )

    # Tools for intelligent product architecture analysis
    # Only 2 tools: image analysis (vision) + search (database access)
    # LLM handles SKU calculations and pattern generation autonomously
    tools = [
        image_analysis_tool,  # Multimodal product analysis
    ]

    # Add catalog search tool if storage provided (enables autonomous matching)
    if storage:
        from autifyme_agents.tools.product_search_tools import create_search_product_families_tool
        tools.append(create_search_product_families_tool(storage))

    return {
        "name": "product_architecture_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        "response_format": ProductArchitectureDraft,  # Enforce structured output
    }
