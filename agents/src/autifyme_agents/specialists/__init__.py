"""
Specialist SubAgents for AutifyME.

Architecture Evolution (Phase 3):
- Consolidated from 7 narrow specialists to 2 domain specialists
- Catalog Specialist: PIM, DAM, Pricing, BOM ("what we sell")
- Operations Specialist (future): Suppliers, Inventory, Locations ("how we get/store/ship")

Primary Specialist:
- catalog_specialist: Unified domain expert for product catalog operations

Legacy Specialists (deprecated, kept for backward compatibility):
- product_architecture_specialist: Now alias for catalog_specialist
- cataloging_specialist, taxonomy_specialist, etc.: Superseded by catalog_specialist

Pattern:
- SubAgent dict format (NOT create_agent objects)
- Domain specialists handle HITL via write_data tool
- PM orchestrates delegation
"""

# =============================================================================
# Primary Domain Specialist (Phase 3)
# =============================================================================

from autifyme_agents.specialists.catalog_specialist import (
    create_catalog_specialist,
)

# =============================================================================
# Backward Compatibility Aliases
# =============================================================================
# Alias: product_architecture_specialist -> catalog_specialist
from autifyme_agents.specialists.catalog_specialist import (
    create_catalog_specialist as create_product_architecture_specialist,
)

# =============================================================================
# Legacy Specialists (Deprecated - kept for compatibility)
# =============================================================================
from autifyme_agents.specialists.cataloging_specialist import (
    create_cataloging_specialist,
)
from autifyme_agents.specialists.content_seo_specialist import (
    create_content_seo_specialist,
)
from autifyme_agents.specialists.market_intelligence_specialist import (
    create_market_intelligence_specialist,
)
from autifyme_agents.specialists.taxonomy_specialist import create_taxonomy_specialist
from autifyme_agents.specialists.visual_assets_specialist import (
    create_visual_assets_specialist,
)

__all__ = [
    # Primary domain specialist (recommended)
    "create_catalog_specialist",

    # Backward compatibility alias
    "create_product_architecture_specialist",

    # Legacy specialists (deprecated - use catalog_specialist instead)
    "create_cataloging_specialist",
    "create_taxonomy_specialist",
    "create_market_intelligence_specialist",
    "create_visual_assets_specialist",
    "create_content_seo_specialist",
]
