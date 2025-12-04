"""
Specialist SubAgents for AutifyME.

Architecture (2-Level Domain Specialists):
- PM -> Specialists -> Tools
- Domain-centric design: reusable specialists, not workflow-specific agents

Active Specialists:
- creative_specialist: Media and visual operations ("how we present")
  - image_studio: analyze, edit, generate (Gemini 3 Pro Image)
  - Multi-product detection, extraction, enhancement
  - Returns processed image paths

- catalog_specialist: Product catalog operations ("what we sell")
  - PIM: product_families, products, variants
  - DAM: assets, product_assets (records only)
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

from autifyme_agents.specialists.catalog_specialist import create_catalog_specialist
from autifyme_agents.specialists.creative_specialist import create_creative_specialist

__all__ = [
    "create_catalog_specialist",
    "create_creative_specialist",
]
