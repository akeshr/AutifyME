"""
Product Architecture Specialist - Analyzes product structure and variant composition.

Domain Expertise:
- Product structure analysis (family vs variants)
- Variant axis identification (dimensions that vary: size, color, material, etc.)
- SKU architecture design (naming conventions, combinations)
- Composition pattern understanding (how variants relate to family)

Responsibilities:
- Analyze multimodal input (user descriptions + images)
- Identify variant dimensions and values
- Calculate total SKU combinations
- Generate SKU naming patterns
- Return structured ProductArchitectureDraft

Does NOT:
- Persist to database (PM handles persistence with HITL)
- Generate marketing content (Content Specialist handles this)
- Classify into taxonomy (Taxonomy Specialist handles this)

Architecture Pattern:
- SubAgent dict format (NOT create_agent)
- Returns structured Pydantic models
- PM orchestrates delegation and approval
"""

from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, Field

from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool

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


@tool
def calculate_sku_combinations(variant_axes: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calculate total SKU combinations from variant axes.

    Args:
        variant_axes: List of variant axes with inferred_values
            Example: [
                {"name": "size", "inferred_values": ["S", "M", "L"]},
                {"name": "color", "inferred_values": ["Red", "Blue"]}
            ]

    Returns:
        Dict with:
        - total_combinations: int (total SKUs)
        - breakdown: str (human-readable explanation)
        - is_manageable: bool (< 100 SKUs is manageable)
    """
    if not variant_axes:
        return {
            "total_combinations": 1,
            "breakdown": "No variants - single standalone product",
            "is_manageable": True,
        }

    total = 1
    breakdown_parts = []

    for axis in variant_axes:
        values = axis.get("inferred_values", [])
        count = len(values)
        total *= count
        breakdown_parts.append(f"{count} {axis['name']} options")

    breakdown = " × ".join(breakdown_parts) + f" = {total} total SKUs"

    return {
        "total_combinations": total,
        "breakdown": breakdown,
        "is_manageable": total < 100,
        "warning": (
            f"Large SKU count ({total}) - consider reducing variant options"
            if total >= 100
            else None
        ),
    }


@tool
def generate_sku_pattern(
    product_category: str, variant_axes: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Generate SKU naming pattern based on product category and variants.

    Args:
        product_category: Product category (e.g., "footwear", "apparel", "accessories")
        variant_axes: List of variant axes
            Example: [
                {"name": "size", "inferred_values": ["S", "M", "L"]},
                {"name": "color", "inferred_values": ["Red", "Blue"]}
            ]

    Returns:
        Dict with:
        - prefix: str (SKU prefix)
        - pattern: str (full pattern with placeholders)
        - example_skus: list[str] (sample SKUs)
        - reasoning: str (explanation)
    """
    # Generate prefix from category (first 3-4 uppercase letters)
    prefix = product_category.upper()[:4].ljust(3, "X")

    if not variant_axes:
        return {
            "prefix": prefix,
            "pattern": f"{prefix}-001",
            "example_skus": [f"{prefix}-001"],
            "reasoning": "Standalone product with no variants - simple sequential numbering",
        }

    # Build pattern with variant placeholders
    pattern_parts = [prefix]
    example_values = []

    for axis in variant_axes:
        axis_name = axis["name"].upper()
        pattern_parts.append(f"{{{axis_name}}}")

        # Get first value for example
        values = axis.get("inferred_values", [])
        if values:
            # Convert to SKU code (uppercase, limit to 3-5 chars)
            example_code = values[0].upper().replace(" ", "")[:5]
            example_values.append(example_code)

    pattern = "-".join(pattern_parts)

    # Generate example SKUs
    example_skus = []
    if len(variant_axes) >= 2:
        # Generate a few combinations
        axis1_values = variant_axes[0].get("inferred_values", [])[:3]
        axis2_values = variant_axes[1].get("inferred_values", [])[:2]

        for v1 in axis1_values:
            for v2 in axis2_values:
                code1 = v1.upper().replace(" ", "")[:5]
                code2 = v2.upper().replace(" ", "")[:5]
                parts = [prefix, code1, code2]
                # Add remaining axes if exist
                for axis in variant_axes[2:]:
                    first_val = axis.get("inferred_values", [""])[0]
                    parts.append(first_val.upper().replace(" ", "")[:5])
                example_skus.append("-".join(parts))
                if len(example_skus) >= 5:
                    break
            if len(example_skus) >= 5:
                break
    else:
        # Single variant axis
        for value in variant_axes[0].get("inferred_values", [])[:5]:
            code = value.upper().replace(" ", "")[:5]
            example_skus.append(f"{prefix}-{code}")

    reasoning = (
        f"Pattern uses {len(variant_axes)} variant dimensions. "
        f"Each SKU uniquely identifies a product by {', '.join([a['name'] for a in variant_axes])}. "
        f"Format is hierarchical: PREFIX-{'-'.join([a['name'].upper() for a in variant_axes])}"
    )

    return {
        "prefix": prefix,
        "pattern": pattern,
        "example_skus": example_skus[:5],
        "reasoning": reasoning,
    }


# =============================================================================
# Specialist Factory
# =============================================================================


def create_product_architecture_specialist() -> dict[str, Any]:
    """
    Create Product Architecture Specialist as SubAgent spec.

    Specialist Responsibilities:
    - Analyze product from multimodal input (images + user description)
    - Identify variant structure (axes and values)
    - Design SKU architecture (naming pattern, combinations)
    - Return ProductArchitectureDraft for PM review

    Architecture:
    - SubAgent dict format (DeepAgents pattern)
    - Analysis tools only (no persistence)
    - Returns structured Pydantic model
    - PM handles HITL and persistence

    Returns:
        SubAgent spec with:
        - name: specialist identifier
        - description: delegation criteria
        - tools: analysis tools
        - system_prompt: domain expertise instructions
    """
    system_prompt = load_prompt("specialists/product_architecture_specialist.prompt")

    description = (
        "Analyzes product structure and designs variant architecture. "
        "Identifies variant dimensions (size, color, material, etc.), "
        "calculates SKU combinations, and generates naming patterns. "
        "Returns ProductArchitectureDraft with complete variant structure for PM review."
    )

    # Tools for variant architecture analysis
    tools = [
        image_analysis_tool,  # Multimodal product analysis
        calculate_sku_combinations,  # SKU count calculation
        generate_sku_pattern,  # SKU naming design
    ]

    return {
        "name": "product_architecture_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        # No response_format - specialist should return conversational analysis
        # PM will extract ProductArchitectureDraft from specialist's messages
    }
