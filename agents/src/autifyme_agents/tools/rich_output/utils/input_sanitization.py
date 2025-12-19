"""Input sanitization for Rich Output Engine.

Escapes HTML entities in input data before sending to LLM.
Prevents injection via data values.
"""

from __future__ import annotations

import html
from typing import Any


def sanitize_input_data(data: Any) -> Any:
    """Sanitize INPUT data before sending to LLM.

    Recursively escapes HTML entities to prevent injection via data values.
    Handles nested dicts, lists, and string values.

    Args:
        data: Any data structure (dict, list, str, or primitive)

    Returns:
        Same structure with string values HTML-escaped

    Example:
        >>> sanitize_input_data({"name": "<script>alert('xss')</script>"})
        {'name': '&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;'}
    """
    if isinstance(data, str):
        return html.escape(data)
    elif isinstance(data, dict):
        return {k: sanitize_input_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input_data(item) for item in data]
    # Preserve other types (int, float, bool, None) as-is
    return data
