"""Storage URL utilities for Supabase integration.

Builds URLs from storage paths, handling both user paths (LLM-visible)
and storage paths (internal). User paths are automatically expanded
using thread_id from execution context.

Path Formats:
- User Path: "inbox/photo.jpg" (LLM sees this)
- Storage Path: "inbox/{thread_id}/photo.jpg" (internal)
- URL: Full Supabase public URL

Usage:
    # From user path (auto-expands thread_id)
    url = build_storage_url("inbox/photo.jpg")

    # From storage path (direct)
    url = build_storage_url("inbox/thread_123/photo.jpg")
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Storage zones that use thread_id subfolder
THREADED_ZONES = ("inbox", "pending")
STORAGE_PREFIXES = ("inbox/", "pending/", "products/", "brands/", "assets/", "outputs/")


def build_storage_url(path: str, bucket: str = "assets") -> str:
    """Build Supabase storage URL from path.

    Accepts both user paths and storage paths. User paths for threaded
    zones are automatically expanded using thread_id from execution context.

    Args:
        path: User path ("inbox/photo.jpg") or storage path ("inbox/thread/photo.jpg")
        bucket: Storage bucket name

    Returns:
        Full public URL

    Raises:
        ValueError: If SUPABASE_URL not configured
    """
    # Passthrough URLs
    if path.startswith(("http://", "https://")):
        return path

    # Import here to avoid circular dependency
    from autifyme_agents.core.execution_context import is_user_path, to_storage_path

    # Normalize
    path = path.lstrip("/\\")

    # Expand user path to storage path if needed
    if is_user_path(path):
        try:
            path = to_storage_path(path)
        except ValueError:
            # No thread_id in context - path might already be complete or non-threaded
            pass

    # Strip bucket prefix if accidentally included
    if path.startswith(f"{bucket}/"):
        path = path[len(bucket) + 1:]

    # Build URL
    base_url = os.getenv("SUPABASE_URL")
    if not base_url:
        raise ValueError("SUPABASE_URL not configured")

    base_url = base_url.rstrip("/")
    return f"{base_url}/storage/v1/object/public/{bucket}/{path}"


def is_storage_path(path: str) -> bool:
    """Check if path is a relative storage path (not URL or local).

    Recognizes both user paths and storage paths.
    """
    if path.startswith(("http://", "https://")):
        return False

    normalized = path.lstrip("/\\")

    # Windows absolute paths
    if len(normalized) > 1 and normalized[1] == ":":
        return False

    return normalized.startswith(STORAGE_PREFIXES)
