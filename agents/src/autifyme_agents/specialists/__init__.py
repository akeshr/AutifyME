"""
Specialist SubAgents for AutifyME.

Architecture Evolution:
- Phase 3A: Catalog Specialist (domain owner for products + assets)
- Legacy: 7 narrow specialists (to be consolidated in Phase 3B)

All specialists follow the same pattern:
- SubAgent dict format (NOT create_agent objects)
- Domain-specific CRUD operations with HITL
- PM orchestrates delegation
"""

# Phase 3A: Domain-owning Catalog Specialist
from autifyme_agents.specialists.catalog_specialist import (
    create_catalog_specialist,
)

# Legacy specialists (to be consolidated in Phase 3B)
from autifyme_agents.specialists.cataloging_specialist import (
    create_cataloging_specialist,
)
from autifyme_agents.specialists.content_seo_specialist import (
    create_content_seo_specialist,
)
from autifyme_agents.specialists.market_intelligence_specialist import (
    create_market_intelligence_specialist,
)
from autifyme_agents.specialists.product_architecture_specialist import (
    create_product_architecture_specialist,
)
from autifyme_agents.specialists.taxonomy_specialist import create_taxonomy_specialist
from autifyme_agents.specialists.visual_assets_specialist import (
    create_visual_assets_specialist,
)

__all__ = [
    # Phase 3A: Domain-owning specialist
    "create_catalog_specialist",
    # Legacy (Phase 3B consolidation)
    "create_cataloging_specialist",
    "create_product_architecture_specialist",
    "create_taxonomy_specialist",
    "create_market_intelligence_specialist",
    "create_visual_assets_specialist",
    "create_content_seo_specialist",
]
