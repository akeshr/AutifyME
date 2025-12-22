"""Output sanitization for Rich Output Engine.

Defense in depth: sanitize LLM-generated HTML to remove any
potentially dangerous content even if LLM doesn't follow instructions.
"""

from __future__ import annotations

import re


def sanitize_llm_html_output(html_content: str) -> str:
    """Sanitize LLM-generated HTML output.

    DO NOT trust LLM to follow instructions perfectly.
    Strip any potentially dangerous content.

    Removes:
    - <script> tags and content
    - on* event handlers (onclick, onerror, onload, etc.)
    - javascript: URLs
    - data: URLs with text/html (XSS vector)

    Args:
        html_content: Raw HTML from LLM

    Returns:
        Sanitized HTML with dangerous content removed

    Example:
        >>> sanitize_llm_html_output('<div onclick="alert()">Hi</div>')
        '<div >Hi</div>'
    """
    # Remove <script> tags and content
    html_content = re.sub(
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
        '',
        html_content,
        flags=re.IGNORECASE
    )

    # Remove on* event handlers (onclick, onerror, onload, etc.)
    # Matches: onclick="...", onclick='...', onclick=...
    html_content = re.sub(
        r'\bon\w+\s*=\s*["\'][^"\']*["\']',
        '',
        html_content,
        flags=re.IGNORECASE
    )

    # Also handle unquoted event handlers
    html_content = re.sub(
        r'\bon\w+\s*=\s*[^\s>]+',
        '',
        html_content,
        flags=re.IGNORECASE
    )

    # Remove javascript: URLs
    html_content = re.sub(
        r'javascript\s*:',
        '',
        html_content,
        flags=re.IGNORECASE
    )

    # Remove data: URLs that could contain HTML (XSS vector)
    html_content = re.sub(
        r'data\s*:\s*text/html',
        '',
        html_content,
        flags=re.IGNORECASE
    )

    return html_content
