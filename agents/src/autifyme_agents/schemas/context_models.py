"""Context models for PM base context (catalog summary, taxonomy tree)."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from autifyme_agents.schemas.models import CompanyProfile


class CategoryNode(BaseModel):
    """Hierarchical category node for taxonomy tree.

    Recursive structure representing product categories with parent-child relationships.
    Used in PM base context for taxonomy awareness without loading full catalog.
    """

    id: UUID = Field(
        ...,
        description="Unique identifier for this category"
    )
    name: str = Field(
        ...,
        description="Category name (e.g., 'Food & Beverage', 'Personal Care')"
    )
    parent_id: UUID | None = Field(
        None,
        description="Parent category ID (None for root categories)"
    )
    children: list["CategoryNode"] = Field(
        default_factory=list,
        description="Child categories (empty for leaf nodes)"
    )

    model_config = ConfigDict(from_attributes=True)


class TaxonomyTree(BaseModel):
    """Hierarchical taxonomy structure for PM understanding.

    Lightweight representation of product categorization system loaded at PM startup.
    Enables PM to understand category structure without querying DB for each request.
    """

    root_categories: list[CategoryNode] = Field(
        ...,
        description="Top-level categories (e.g., Food & Beverage, Personal Care)"
    )
    total_categories: int = Field(
        ...,
        description="Total number of categories in tree (for context)"
    )
    last_updated: datetime = Field(
        ...,
        description="When taxonomy tree was last loaded from DB"
    )

    model_config = ConfigDict(from_attributes=True)


class CatalogSummary(BaseModel):
    """Lightweight catalog summary for PM base context.

    High-level statistics and family names loaded at PM startup (refreshed every 15min).
    Enables PM to:
    - Know what product families exist without full catalog load
    - Answer basic questions ("What products do we make?")
    - Decide whether to query details ("Do we have X?" → query if not in summary)

    Token cost: ~500-1000 tokens for 100 product families
    """

    total_families: int = Field(
        ...,
        description="Total number of product families in catalog"
    )
    total_skus: int = Field(
        ...,
        description="Total number of individual product SKUs"
    )
    family_names: list[str] = Field(
        ...,
        description="List of product family names (just names, not full data)"
    )
    top_categories: list[str] = Field(
        default_factory=list,
        description="Most common product categories in catalog"
    )
    last_updated: datetime = Field(
        ...,
        description="When catalog summary was last refreshed from DB"
    )

    model_config = ConfigDict(from_attributes=True)


class PMBaseContext(BaseModel):
    """Complete base context injected into PM at startup.

    Combines company profile, catalog summary, and taxonomy tree into single
    context object loaded once and refreshed periodically (every 15 minutes).

    This enables Intelligent PM paradigm:
    - PM knows company context from message 1
    - PM knows what products exist (summary level)
    - PM knows category structure
    - PM can have intelligent discussions before delegating
    - PM queries details only when needed (not every message)

    Token cost target: <2K tokens total
    - Company profile: ~200-500 tokens
    - Catalog summary: ~500-1000 tokens
    - Taxonomy tree: ~500-1000 tokens
    """

    company_profile: CompanyProfile = Field(
        ...,
        description="Company profile with brand voice, target audience, capabilities, and SKU naming conventions"
    )
    catalog_summary: CatalogSummary = Field(
        ...,
        description="Lightweight catalog statistics and family names"
    )
    taxonomy_tree: TaxonomyTree = Field(
        ...,
        description="Hierarchical category structure"
    )
    recent_activity: list[str] = Field(
        default_factory=list,
        description="Recent user activities for context (FUTURE - not implemented yet)"
    )
    loaded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this context object was created"
    )

    model_config = ConfigDict(from_attributes=True)


# Enable forward references for recursive CategoryNode model
CategoryNode.model_rebuild()
