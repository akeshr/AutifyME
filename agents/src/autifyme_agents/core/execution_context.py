"""Execution Context - Infrastructure concerns invisible to LLMs.

Provides thread-local storage for infrastructure data (thread_id, company_id)
and path conversion utilities that hide thread_id from LLM-visible paths.

Architecture:
- Runner sets context once before workflow execution
- Tools read context silently - no parameters needed
- Paths are converted between user format (LLM) and storage format (internal)

Path Formats:
- User Path (LLM sees): "inbox/photo.jpg", "pending/output.png"
- Storage Path (internal): "inbox/{thread_id}/photo.jpg", "pending/{thread_id}/output.png"

Usage:
    # Runner sets context:
    with execution_context(thread_id="whatsapp_123"):
        result = await pm.invoke(...)

    # Tools convert paths silently:
    storage_path = to_storage_path("inbox/photo.jpg")  # inbox/whatsapp_123/photo.jpg
    user_path = to_user_path(storage_path)              # inbox/photo.jpg
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

from autifyme_agents.core.storage_utils import sanitize_for_path

logger = logging.getLogger(__name__)

# Context variables - invisible to LLMs
_current_thread_id: ContextVar[str | None] = ContextVar("thread_id", default=None)
_current_company_id: ContextVar[str | None] = ContextVar("company_id", default=None)

# Storage zones that use thread_id subfolder
THREADED_ZONES = ("inbox", "pending")


def get_thread_id() -> str | None:
    """Get current thread_id from execution context."""
    return _current_thread_id.get()


def get_company_id() -> str | None:
    """Get current company_id from execution context."""
    return _current_company_id.get()


@contextmanager
def execution_context(
    thread_id: str | None = None,
    company_id: str | None = None,
) -> Generator[None, None, None]:
    """Context manager for setting execution context.

    Args:
        thread_id: Conversation thread identifier
        company_id: Company/tenant identifier
    """
    thread_token = _current_thread_id.set(thread_id)
    company_token = _current_company_id.set(company_id)

    logger.debug("Execution context set", extra={"thread_id": thread_id})

    try:
        yield
    finally:
        _current_thread_id.reset(thread_token)
        _current_company_id.reset(company_token)


def to_user_path(storage_path: str) -> str:
    """Convert storage path to user path by stripping thread_id.

    Storage: "inbox/{thread_id}/photo.jpg" -> User: "inbox/photo.jpg"
    Storage: "pending/{thread_id}/out.png" -> User: "pending/out.png"
    Storage: "products/img.jpg" -> User: "products/img.jpg" (no thread_id)

    Args:
        storage_path: Full storage path with thread_id

    Returns:
        User-friendly path without thread_id
    """
    # Skip URLs
    if storage_path.startswith(("http://", "https://")):
        return storage_path

    # Normalize
    path = storage_path.lstrip("/\\")
    parts = path.split("/")

    if len(parts) < 3:
        return path  # Already short or not threaded

    zone = parts[0]
    if zone not in THREADED_ZONES:
        return path  # Non-threaded zone (products, brands, etc.)

    # Pattern: zone/thread_id/filename... -> zone/filename...
    # parts[0] = zone, parts[1] = thread_id, parts[2:] = filename/subpath
    return f"{zone}/{'/'.join(parts[2:])}"


def to_storage_path(user_path: str) -> str:
    """Convert user path to storage path by injecting thread_id.

    User: "inbox/photo.jpg" -> Storage: "inbox/{thread_id}/photo.jpg"
    User: "pending/out.png" -> Storage: "pending/{thread_id}/out.png"
    User: "products/img.jpg" -> Storage: "products/img.jpg" (no thread_id needed)

    Args:
        user_path: User-friendly path without thread_id

    Returns:
        Full storage path with thread_id injected

    Raises:
        ValueError: If thread_id required but not available in context
    """
    # Skip URLs
    if user_path.startswith(("http://", "https://")):
        return user_path

    # Normalize
    path = user_path.lstrip("/\\")
    parts = path.split("/")

    if len(parts) < 2:
        return path  # Invalid path

    zone = parts[0]
    if zone not in THREADED_ZONES:
        return path  # Non-threaded zone

    # Check if thread_id already present (idempotent)
    thread_id = get_thread_id()
    if not thread_id:
        logger.warning(f"No thread_id in context for path: {user_path}")
        raise ValueError(f"thread_id required for {zone}/ paths but not in context")

    # Sanitize for storage path (replace invalid chars like colons)
    safe_thread_id = sanitize_for_path(thread_id)

    if len(parts) >= 3 and parts[1] == safe_thread_id:
        return path  # Already has thread_id

    # Pattern: zone/filename... -> zone/thread_id/filename...
    filename_parts = parts[1:]  # Everything after zone
    return f"{zone}/{safe_thread_id}/{'/'.join(filename_parts)}"


def is_user_path(path: str) -> bool:
    """Check if path is in user format (no thread_id).

    User paths: "inbox/photo.jpg", "pending/out.png"
    Storage paths: "inbox/thread_123/photo.jpg" (has extra segment)
    """
    if path.startswith(("http://", "https://")):
        return False

    path = path.lstrip("/\\")
    parts = path.split("/")

    if len(parts) < 2:
        return False

    zone = parts[0]
    if zone not in THREADED_ZONES:
        return True  # Non-threaded zones don't need conversion

    # User path has exactly 2 parts for simple files: zone/filename
    # Or zone/subdir/filename but NO thread_id pattern
    # Storage path has: zone/thread_id/filename (thread_id is long)
    # Heuristic: thread_id contains underscore and is long
    if len(parts) >= 3:
        potential_thread_id = parts[1]
        # Thread IDs look like: whatsapp_default_919876543210
        if "_" in potential_thread_id and len(potential_thread_id) > 15:
            return False  # Likely storage path

    return True
