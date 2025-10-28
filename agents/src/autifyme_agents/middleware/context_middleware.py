"""Context middleware for loading PM base context from database.

Provides lightweight catalog and taxonomy summaries for Intelligent PM paradigm.
Loaded once at PM startup, refreshed periodically (15 min TTL recommended).
"""

import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.context_models import (
    CatalogSummary,
    CategoryNode,
    PMBaseContext,
    TaxonomyTree,
)
from autifyme_agents.schemas.models import CompanyProfile

logger = logging.getLogger(__name__)


async def load_catalog_summary(storage: StorageInterface) -> CatalogSummary:
    """Query database for lightweight catalog summary.

    Queries:
    - Total product families count
    - Total SKUs count
    - Family names (for PM awareness)
    - Top categories (most common)

    Args:
        storage: Storage adapter with DB access

    Returns:
        CatalogSummary with stats and names (NOT full product data)

    Raises:
        Exception: If DB query fails (caller handles graceful degradation)
    """
    try:
        client = storage._ensure_client()

        # Query 1: Total families (include category_id for top categories)
        families_response = client.table("product_families").select("id, name, category_id").execute()
        families = families_response.data or []
        total_families = len(families)
        family_names = [f["name"] for f in families]

        # Query 2: Total SKUs
        skus_response = client.table("products").select("id", count="exact").execute()
        total_skus = skus_response.count or 0

        # Query 3: Top categories (from product families)
        # Get category_id from families, then lookup category names
        category_ids = [UUID(f["category_id"]) for f in families if f.get("category_id")]
        top_categories = []

        if category_ids:
            # Count category frequency
            category_counts: dict[Any, int] = defaultdict(int)
            for cat_id in category_ids:
                category_counts[cat_id] += 1

            # Get top 5 category names
            top_cat_ids = sorted(category_counts.keys(), key=lambda x: category_counts[x], reverse=True)[:5]

            if top_cat_ids:
                categories_response = (
                    client.table("categories")
                    .select("id, name")
                    .in_("id", [str(c) for c in top_cat_ids])
                    .execute()
                )
                categories = categories_response.data or []
                top_categories = [c["name"] for c in categories]

        logger.info(
            "Loaded catalog summary",
            extra={
                "total_families": total_families,
                "total_skus": total_skus,
                "top_categories_count": len(top_categories),
            }
        )

        return CatalogSummary(
            total_families=total_families,
            total_skus=total_skus,
            family_names=family_names,
            top_categories=top_categories,
            last_updated=datetime.now(UTC),
        )

    except Exception as e:
        logger.error(
            "Failed to load catalog summary from database",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_msg": str(e)}
        )
        # Re-raise for caller to handle graceful degradation
        raise


async def load_taxonomy_tree(storage: StorageInterface) -> TaxonomyTree:
    """Query database for hierarchical taxonomy tree.

    Builds category tree with parent-child relationships for PM understanding.
    Lightweight structure (IDs and names only, not full category data).

    Args:
        storage: Storage adapter with DB access

    Returns:
        TaxonomyTree with hierarchical category structure

    Raises:
        Exception: If DB query fails (caller handles graceful degradation)
    """
    try:
        client = storage._ensure_client()

        # Query all categories with parent_id
        categories_response = (
            client.table("categories")
            .select("id, name, parent_id")
            .execute()
        )
        categories_data = categories_response.data or []

        if not categories_data:
            logger.warning("No categories found in database - empty taxonomy tree")
            return TaxonomyTree(
                root_categories=[],
                total_categories=0,
                last_updated=datetime.now(UTC),
            )

        # Build lookup maps
        category_map: dict[UUID, CategoryNode] = {}
        children_map: dict[UUID | None, list[CategoryNode]] = defaultdict(list)

        # First pass: Create all category nodes
        for cat in categories_data:
            node = CategoryNode(
                id=UUID(cat["id"]),
                name=cat["name"],
                parent_id=UUID(cat["parent_id"]) if cat.get("parent_id") else None,
                children=[],
            )
            category_map[node.id] = node
            children_map[node.parent_id].append(node)

        # Second pass: Build hierarchy (assign children to parents)
        for node in category_map.values():
            if node.id in children_map:
                node.children = children_map[node.id]

        # Root categories have parent_id = None
        root_categories = children_map[None]

        logger.info(
            "Loaded taxonomy tree",
            extra={
                "total_categories": len(categories_data),
                "root_categories": len(root_categories),
            }
        )

        return TaxonomyTree(
            root_categories=root_categories,
            total_categories=len(categories_data),
            last_updated=datetime.now(UTC),
        )

    except Exception as e:
        logger.error(
            "Failed to load taxonomy tree from database",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_msg": str(e)}
        )
        # Re-raise for caller to handle graceful degradation
        raise


async def load_base_context(
    company_profile: CompanyProfile,
    storage: StorageInterface,
) -> PMBaseContext:
    """Load complete base context for Intelligent PM.

    Combines company profile with catalog summary and taxonomy tree into single
    context object. Handles DB failures gracefully (returns empty summaries with
    stale flag rather than crashing PM startup).

    This enables Intelligent PM paradigm:
    - PM knows company context from message 1
    - PM knows what products exist (summary level)
    - PM knows category structure
    - PM can have intelligent discussions before delegating

    Args:
        company_profile: Company profile (already loaded)
        storage: Storage adapter with DB access

    Returns:
        PMBaseContext with all base context loaded

    Notes:
        - DB unavailable → Returns empty summaries (graceful degradation)
        - Logs errors but doesn't crash PM startup
        - Caller should check last_updated timestamps for staleness
    """
    try:
        # Load catalog and taxonomy (may raise exceptions)
        catalog_summary = await load_catalog_summary(storage)
        taxonomy_tree = await load_taxonomy_tree(storage)

        logger.info(
            "Base context loaded successfully",
            extra={
                "catalog_families": catalog_summary.total_families,
                "taxonomy_categories": taxonomy_tree.total_categories,
            }
        )

        return PMBaseContext(
            company_profile=company_profile.model_dump(),
            catalog_summary=catalog_summary,
            taxonomy_tree=taxonomy_tree,
            recent_activity=[],  # FUTURE: Load from activity log
            loaded_at=datetime.now(UTC),
        )

    except Exception as e:
        logger.error(
            "Failed to load base context - using empty summaries (graceful degradation)",
            exc_info=True,
            extra={
                "error_type": type(e).__name__,
                "error_msg": str(e),
                "company_id": company_profile.id,
            }
        )

        # Graceful degradation: Return empty summaries instead of crashing
        # PM can still operate with limited context
        return PMBaseContext(
            company_profile=company_profile.model_dump(),
            catalog_summary=CatalogSummary(
                total_families=0,
                total_skus=0,
                family_names=[],
                top_categories=[],
                last_updated=datetime.now(UTC),
            ),
            taxonomy_tree=TaxonomyTree(
                root_categories=[],
                total_categories=0,
                last_updated=datetime.now(UTC),
            ),
            recent_activity=[],
            loaded_at=datetime.now(UTC),
        )
