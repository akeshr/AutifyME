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
    CompanyPatterns,
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
        # Query 1: Total families (include category_id for top categories)
        families = await storage.query_entities(
            table="product_families",
            columns=["id", "name", "category_id"]
        )
        total_families = len(families)
        family_names = [f["name"] for f in families]

        # Query 2: Total SKUs (count only)
        total_skus = await storage.count_entities(table="products")

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
                # Query categories for top IDs
                # Use direct list for IN operator (documented interface)
                categories = await storage.query_entities(
                    table="categories",
                    filters={"id": [str(c) for c in top_cat_ids]},
                    columns=["id", "name"]
                )
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
        # Query all categories with parent_id
        categories_data = await storage.query_entities(
            table="categories",
            columns=["id", "name", "parent_id"]
        )

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


async def load_company_patterns(storage: StorageInterface) -> CompanyPatterns:
    """Derive company patterns from catalog analysis.

    Analyzes existing catalog to extract patterns useful for cold-start handling:
    - Primary workflow type (based on product distribution)
    - Typical price range (min/max from existing prices)
    - Common product types
    - Naming conventions (SKU patterns)

    Args:
        storage: Storage adapter with DB access

    Returns:
        CompanyPatterns derived from catalog analysis

    Raises:
        Exception: If DB query fails (caller handles graceful degradation)
    """
    try:
        # Query 1: Product type distribution
        products = await storage.query_entities(
            table="products",
            columns=["product_type", "sku", "status"]
        )

        # Count product types
        type_counts: dict[str, int] = defaultdict(int)
        for p in products:
            if p.get("status") == "ACTIVE":
                type_counts[p.get("product_type", "UNKNOWN")] += 1

        # Sort by count and get top types
        common_product_types = sorted(
            type_counts.keys(),
            key=lambda x: type_counts[x],
            reverse=True
        )[:5]

        # Determine primary workflow based on product mix
        if type_counts.get("FINISHED_GOOD", 0) > type_counts.get("RAW_MATERIAL", 0):
            primary_workflow = "catalog"
        else:
            primary_workflow = "operations"

        # Query 2: Price range
        prices = await storage.query_entities(
            table="product_prices",
            columns=["price"]
        )

        if prices:
            price_values = [float(p["price"]) for p in prices if p.get("price")]
            if price_values:
                typical_price_range = (min(price_values), max(price_values))
            else:
                typical_price_range = (0.0, 1000.0)
        else:
            typical_price_range = (0.0, 1000.0)

        # Query 3: SKU patterns (derive from existing SKUs)
        naming_conventions: dict[str, str] = {}
        if products:
            # Analyze SKU patterns
            skus = [p.get("sku", "") for p in products if p.get("sku")]
            if skus:
                # Check for common pattern: FAMILY-SIZE or FAMILY-SIZE-VARIANT
                sample_sku = skus[0] if skus else ""
                parts = sample_sku.split("-")
                if len(parts) >= 2:
                    naming_conventions["sku_pattern"] = "-".join(
                        ["FAMILY"] + ["PART"] * (len(parts) - 1)
                    )

        logger.info(
            "Loaded company patterns",
            extra={
                "primary_workflow": primary_workflow,
                "price_range": typical_price_range,
                "common_types_count": len(common_product_types),
            }
        )

        return CompanyPatterns(
            primary_workflow=primary_workflow,
            typical_price_range=typical_price_range,
            common_product_types=common_product_types,
            naming_conventions=naming_conventions,
            recent_actions=[],  # FUTURE: Load from activity log
            last_analyzed=datetime.now(UTC),
        )

    except Exception as e:
        logger.error(
            "Failed to load company patterns from database",
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
        # Load catalog, taxonomy, and patterns (may raise exceptions)
        catalog_summary = await load_catalog_summary(storage)
        taxonomy_tree = await load_taxonomy_tree(storage)
        company_patterns = await load_company_patterns(storage)

        logger.info(
            "Base context loaded successfully",
            extra={
                "catalog_families": catalog_summary.total_families,
                "taxonomy_categories": taxonomy_tree.total_categories,
                "primary_workflow": company_patterns.primary_workflow,
            }
        )

        return PMBaseContext(
            company_profile=company_profile,
            catalog_summary=catalog_summary,
            taxonomy_tree=taxonomy_tree,
            company_patterns=company_patterns,
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
            company_profile=company_profile,
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
            company_patterns=CompanyPatterns(
                primary_workflow="catalog",
                typical_price_range=(0.0, 1000.0),
                common_product_types=[],
                naming_conventions={},
                recent_actions=[],
                last_analyzed=datetime.now(UTC),
            ),
            recent_activity=[],
            loaded_at=datetime.now(UTC),
        )
