"""Core middleware for AutifyME agents."""

from autifyme_agents.core.middleware.approval_context import ApprovalContextMiddleware

# Import from the legacy middleware.py file for backwards compatibility
# The old middleware.py is at agents/src/autifyme_agents/core/middleware.py (sibling to this package)
from autifyme_agents.core.middleware import (
    CompanyContextMiddleware,
    create_company_context_middleware,
)

__all__ = [
    "ApprovalContextMiddleware",
    "CompanyContextMiddleware",
    "create_company_context_middleware",
]
