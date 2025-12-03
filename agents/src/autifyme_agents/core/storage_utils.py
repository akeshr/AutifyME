"""Storage URL utilities for Supabase integration.

Centralized URL building for all components that need to fetch images
from Supabase storage. Ensures consistent URL construction and allows
components to work with storage_path (relative path) everywhere.

Architecture:
- All tools return storage_path (relative path within bucket)
- URL is derived on-demand where HTTP fetching is needed
- Single source of truth: storage_path is canonical
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def normalize_storage_path(path: str) -> str:
    """Normalize storage path by removing leading slashes.

    LLMs sometimes add leading slashes to storage paths. This ensures
    consistency before URL construction or path validation.

    Args:
        path: Storage path that may have leading slashes

    Returns:
        Normalized path without leading slashes

    Examples:
        >>> normalize_storage_path("/inbox/thread/img.png")
        "inbox/thread/img.png"
        >>> normalize_storage_path("inbox/thread/img.png")
        "inbox/thread/img.png"
    """
    # Don't touch URLs
    if path.startswith(("http://", "https://")):
        return path

    # Strip leading slashes/backslashes
    return path.lstrip("/\\")


def build_storage_url(
    path: str,
    bucket: str = "assets",
    supabase_url: str | None = None,
) -> str:
    """Build full Supabase storage URL from relative path.

    If the path is already a URL (starts with http:// or https://),
    returns it unchanged. Otherwise, constructs the full public URL.

    Handles and normalizes leading slashes that LLMs sometimes add.

    Args:
        path: Relative path within bucket (e.g., "pending/thread_id/image.png")
              OR already a full URL (passthrough)
        bucket: Storage bucket name (default: "assets")
        supabase_url: Optional Supabase project URL. Falls back to SUPABASE_URL env.

    Returns:
        Full public URL for the storage object

    Raises:
        ValueError: If path is relative but SUPABASE_URL is not configured

    Examples:
        >>> build_storage_url("pending/whatsapp_123/img.png")
        "https://xxx.supabase.co/storage/v1/object/public/assets/pending/whatsapp_123/img.png"

        >>> build_storage_url("/inbox/whatsapp_123/img.png")  # Leading slash normalized
        "https://xxx.supabase.co/storage/v1/object/public/assets/inbox/whatsapp_123/img.png"

        >>> build_storage_url("https://already-a-url.com/image.png")
        "https://already-a-url.com/image.png"
    """
    # Passthrough if already a URL
    if path.startswith(("http://", "https://")):
        return path

    # Normalize: remove leading slashes (LLMs sometimes add them)
    path = normalize_storage_path(path)

    # Get Supabase URL from param or env
    base_url = supabase_url or os.getenv("SUPABASE_URL")
    if not base_url:
        logger.warning(
            "Cannot build storage URL: SUPABASE_URL not configured",
            extra={"path": path, "bucket": bucket}
        )
        raise ValueError(
            "SUPABASE_URL not configured. Set environment variable or pass supabase_url."
        )

    # Build URL: https://{project}.supabase.co/storage/v1/object/public/{bucket}/{path}
    base_url = base_url.rstrip("/")
    return f"{base_url}/storage/v1/object/public/{bucket}/{path}"


def is_storage_path(path: str) -> bool:
    """Check if a path is a relative storage path (not a URL or local path).

    Handles leading slashes that LLMs sometimes add.

    Args:
        path: Path to check

    Returns:
        True if this looks like a relative Supabase storage path

    Examples:
        >>> is_storage_path("inbox/thread/img.png")
        True
        >>> is_storage_path("/inbox/thread/img.png")  # Leading slash OK
        True
        >>> is_storage_path("https://example.com/img.png")
        False
        >>> is_storage_path("/tmp/local/file.png")
        False
    """
    # URLs are not storage paths
    if path.startswith(("http://", "https://")):
        return False

    # Normalize: remove leading slashes before checking
    normalized = path.lstrip("/\\")

    # Windows absolute paths are not storage paths (e.g., "C:\...")
    if len(normalized) > 1 and normalized[1] == ":":
        return False

    # Relative paths starting with known folders are storage paths
    storage_prefixes = ("pending/", "inbox/", "products/")
    return normalized.startswith(storage_prefixes)
