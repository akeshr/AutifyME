"""Workflow factories exposed by autifyme_agents."""

from .project_manager import create_project_manager

__all__ = [
    # Main PM (handles all workflows: cataloging, product onboarding, etc.)
    "create_project_manager",
]
