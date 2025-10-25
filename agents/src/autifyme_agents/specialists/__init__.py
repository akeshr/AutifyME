"""
Specialist SubAgents for AutifyME Product Onboarding.

All specialists follow the same pattern:
- SubAgent dict format (NOT create_agent objects)
- Domain-specific analysis only (NO persistence)
- Return structured Pydantic models
- PM orchestrates delegation and HITL approval

Architecture:
- Product onboarding uses 5 domain specialists
- Each specialist is independent and reusable
- PM synthesizes specialist outputs into unified ProductFamilyInput
- PM owns HITL persistence tools (specialists have none)
"""

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
    # Cataloging workflow (existing)
    "create_cataloging_specialist",
    # Product onboarding workflow (new)
    "create_product_architecture_specialist",
    "create_taxonomy_specialist",
    "create_market_intelligence_specialist",
    "create_visual_assets_specialist",
    "create_content_seo_specialist",
]
