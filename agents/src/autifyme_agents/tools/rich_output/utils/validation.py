"""Validation utilities for Rich Output Engine.

HTML structure validation and image URL validation.
"""

from __future__ import annotations

from urllib.parse import urlparse


def validate_html_structure(content: str) -> tuple[bool, str | None]:
    """Validate HTML has required structure.

    Checks for essential elements that indicate valid HTML output.

    Args:
        content: HTML content from LLM

    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid.

    Example:
        >>> validate_html_structure("<!DOCTYPE html><html>...</html>")
        (True, None)
        >>> validate_html_structure("<div>incomplete</div>")
        (False, "Missing DOCTYPE")
    """
    content = content.strip()

    if not content.lower().startswith("<!doctype html>"):
        return False, "Missing DOCTYPE"

    if not content.lower().endswith("</html>"):
        return False, "Missing closing </html>"

    if "<head>" not in content.lower():
        return False, "Missing <head>"

    if "<body>" not in content.lower():
        return False, "Missing <body>"

    if "<title>" not in content.lower():
        return False, "Missing <title>"

    return True, None


def validate_image_url(url: str) -> bool:
    """Validate image URL is safe to include.

    Ensures URL is HTTPS and doesn't contain JavaScript.

    Args:
        url: Image URL to validate

    Returns:
        True if URL is safe, False otherwise

    Example:
        >>> validate_image_url("https://example.com/image.jpg")
        True
        >>> validate_image_url("javascript:alert('xss')")
        False
    """
    # Block javascript: URLs
    if "javascript:" in url.lower():
        return False

    parsed = urlparse(url)

    # Must be HTTPS
    if parsed.scheme != "https":
        return False

    # Must have a host
    return bool(parsed.netloc)
