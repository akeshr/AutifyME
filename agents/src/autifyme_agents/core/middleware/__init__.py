"""Core middleware for AutifyME agents."""

from autifyme_agents.core.middleware.approval_context import ApprovalContextMiddleware

# Import from legacy middleware file for backwards compatibility
from autifyme_agents.core.legacy_middleware import (
    CompanyContextMiddleware,
    create_company_context_middleware,
)

__all__ = [
    "ApprovalContextMiddleware",
    "CompanyContextMiddleware",
    "create_company_context_middleware",
]
