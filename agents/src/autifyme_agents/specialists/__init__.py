"""
Specialist SubAgents for AutifyME.

Architecture (Phase 3 - Consolidated Domain Specialists):
- PM -> Specialists -> Tools (2-level hierarchy)
- Domain-centric design: reusable specialists, not workflow-specific agents

Primary Specialist:
- catalog_specialist: Unified domain expert for product catalog operations
  - PIM: product_families, products, variants
  - DAM: assets, product_assets
  - Pricing: price_lists, product_prices
  - Manufacturing: bom, bom_lines

Future Specialists:
- operations_specialist: Suppliers, inventory, locations ("how we get/store/ship")
- marketing_specialist: Campaigns, ads, content

Pattern:
- SubAgent dict format for PM delegation
- Domain specialists handle HITL via write_data tool
- PM orchestrates, specialists execute
"""

from autifyme_agents.specialists.catalog_specialist import (
    create_catalog_specialist,
)

__all__ = [
    "create_catalog_specialist",
]
