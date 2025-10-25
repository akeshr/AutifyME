"""Workflow factories exposed by autifyme_agents."""

from .basic_project_manager import create_project_manager as create_basic_project_manager
from .project_manager import create_project_manager

__all__ = [
    # Main PM (handles all workflows: cataloging, product onboarding, etc.)
    "create_project_manager",
    # Basic PM (legacy, simple cataloging only)
    "create_basic_project_manager",
]
