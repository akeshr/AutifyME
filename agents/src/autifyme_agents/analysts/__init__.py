"""Analyst agents for research and information gathering.

Analysts are read-only SubAgents that gather information for PM decision-making.
Unlike Specialists who execute actions, Analysts:
- Focus on understanding and pattern detection
- Have no write capabilities
- Return detailed findings to PM
- Are reusable across multiple domains

Architecture:
    PM -> Analysts (research) -> PM synthesizes -> Specialists (execution)
"""

from autifyme_agents.analysts.catalog_analyst import create_catalog_analyst
from autifyme_agents.analysts.product_analyst import create_product_analyst
from autifyme_agents.analysts.visual_analyst import create_visual_analyst

__all__ = [
    "create_visual_analyst",
    "create_product_analyst",
    "create_catalog_analyst",
]
