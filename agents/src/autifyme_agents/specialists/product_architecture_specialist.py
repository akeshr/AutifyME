"""
Product Architecture Specialist - Complete CRUD operations for product architecture.

Domain Expertise:
- Product structure analysis (family vs variants)
- Variant axis identification (dimensions that vary: size, color, material, etc.)
- SKU architecture design (naming conventions, combinations)
- Intelligent catalog matching for autonomous create vs update decisions
- Complete CRUD operations (Create, Read, Update, Delete)

Responsibilities:
- Search catalog for existing product families (autonomous intelligence)
- Classify user intent into CRUD operations
- Return appropriate draft type based on intent:
  * CREATE: ProductArchitectureDraft, VariantAdditionDraft, AxisAdditionDraft
  * READ: ProductQueryDraft
  * UPDATE: FamilyUpdateDraft
  * DELETE: ProductDeletionDraft (with impact analysis)
  * CLARIFY: AmbiguousDraft

Does NOT:
- Persist to database (PM handles persistence)
- Generate marketing content (Content Specialist handles this)
- Classify into taxonomy (Taxonomy Specialist handles this)

Architecture Pattern:
- SubAgent dict format with Union response type
- Autonomous intent classification
- Discriminated union with 7 draft types
- PM routes based on draft_type discriminator
"""

from typing import Any

from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool

# Import all draft types from centralized schema
from autifyme_agents.schemas.product_drafts import ProductArchitectureResponse


# =============================================================================
# Specialist Factory
# =============================================================================


def create_product_architecture_specialist(
    storage: StorageInterface | None = None,
) -> dict[str, Any]:
    """
    Create Product Architecture Specialist with complete CRUD capabilities.

    Specialist Responsibilities:
    - Search catalog for existing product families (enables autonomous decisions)
    - Classify user intent into CRUD operations
    - Return appropriate draft type:
      * CREATE: full_family, variant_addition, axis_addition
      * READ: query
      * UPDATE: family_update
      * DELETE: deletion (with impact analysis)
      * CLARIFY: ambiguous

    Architecture:
    - SubAgent dict format (DeepAgents pattern)
    - Union response type (7 draft types)
    - Discriminated union via draft_type field
    - PM routes based on draft_type

    Args:
        storage: Storage interface for catalog search (required for intelligent matching)

    Returns:
        SubAgent spec with:
        - name: specialist identifier
        - description: delegation criteria
        - tools: analysis and search tools
        - system_prompt: domain expertise instructions
        - response_format: Union of all draft types
    """
    system_prompt = load_prompt("specialists/product_architecture_specialist.prompt")

    description = (
        "Product architecture specialist with complete CRUD capabilities. "
        "Searches catalog to determine operation type (create/read/update/delete), "
        "analyzes product structure, designs variant architecture, "
        "and returns appropriate draft type based on user intent. "
        "Returns one of 7 draft types: full_family, variant_addition, axis_addition, "
        "family_update, query, deletion, or ambiguous."
    )

    tools = [
        image_analysis_tool,
    ]

    if storage:
        from autifyme_agents.tools.product_search_tools import (
            create_search_product_families_tool,
        )

        tools.append(create_search_product_families_tool(storage))

    return {
        "name": "product_architecture_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        "response_format": ProductArchitectureResponse,  # Union type
    }
