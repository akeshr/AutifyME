"""Input validation and sanitization utilities for cross-cutting validation rules.

Provides helpers for:
- HTML/XSS sanitization
- PII detection and redaction
- Length validation
- Content filtering

These utilities are used by InputValidationMiddleware to apply consistent
validation rules across all tools.
"""

from __future__ import annotations

import html
import re
from typing import Any

# PII patterns (phone numbers, emails, credit cards)
PHONE_PATTERN = re.compile(
    r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US/International phones
)

EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
)

# Credit card pattern (basic, captures common formats)
CREDIT_CARD_PATTERN = re.compile(
    r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
)

# SSN pattern (US)
SSN_PATTERN = re.compile(
    r'\b\d{3}-\d{2}-\d{4}\b',
)


def sanitize_html(text: Any) -> Any:
    """Remove HTML tags and escape special characters to prevent XSS.

    Args:
        text: Input string potentially containing HTML (or any type, returns unchanged if not str)

    Returns:
        Sanitized string with HTML tags removed and entities escaped, or original value if not string

    Examples:
        >>> sanitize_html("<script>alert('xss')</script>Hello")
        "alert('xss')Hello"
        >>> sanitize_html("Hello <b>world</b>!")
        "Hello world!"
    """
    if not isinstance(text, str):
        return text

    # Remove HTML tags
    sanitized = re.sub(r'<[^>]+>', '', text)

    # Escape remaining HTML entities for safety
    sanitized = html.escape(sanitized, quote=False)

    return sanitized


def detect_pii(text: Any) -> bool:
    """Detect potential PII in text (phone, email, SSN, credit card).

    Args:
        text: Input value to check (only strings are checked, others return False)

    Returns:
        True if PII patterns detected, False otherwise

    Examples:
        >>> detect_pii("Call me at 555-123-4567")
        True
        >>> detect_pii("Email: user@example.com")
        True
        >>> detect_pii("No sensitive data here")
        False
    """
    if not isinstance(text, str):
        return False

    return bool(
        PHONE_PATTERN.search(text)
        or EMAIL_PATTERN.search(text)
        or CREDIT_CARD_PATTERN.search(text)
        or SSN_PATTERN.search(text)
    )


def redact_pii(text: Any, placeholder: str = "[REDACTED]") -> Any:
    """Redact PII patterns from text for safe logging.

    Args:
        text: Input value potentially containing PII (non-strings returned unchanged)
        placeholder: Replacement text for detected PII

    Returns:
        Text with PII patterns replaced, or original value if not string

    Examples:
        >>> redact_pii("Call 555-123-4567 or email test@example.com")
        "Call [REDACTED] or email [REDACTED]"
        >>> redact_pii("SSN: 123-45-6789")
        "SSN: [REDACTED]"
    """
    if not isinstance(text, str):
        return text

    # Redact in order of specificity (more specific first)
    redacted = SSN_PATTERN.sub(placeholder, text)
    redacted = CREDIT_CARD_PATTERN.sub(placeholder, redacted)
    redacted = EMAIL_PATTERN.sub(placeholder, redacted)
    redacted = PHONE_PATTERN.sub(placeholder, redacted)

    return redacted


def validate_length(
    text: Any,
    max_length: int,
    field_name: str = "field",
) -> None:
    """Validate text length doesn't exceed maximum.

    Args:
        text: Input value to validate (only strings are validated, others ignored)
        max_length: Maximum allowed length
        field_name: Field name for error message

    Raises:
        ValueError: If text exceeds max_length

    Examples:
        >>> validate_length("short", 100)  # OK
        >>> validate_length("x" * 101, 100, "description")
        Traceback (most recent call last):
        ValueError: Field 'description' exceeds maximum length (100 characters)
    """
    if not isinstance(text, str):
        return  # Only validate strings

    if len(text) > max_length:
        raise ValueError(
            f"Field '{field_name}' exceeds maximum length ({max_length} characters). "
            f"Got {len(text)} characters."
        )


def validate_dict_lengths(
    data: dict[str, Any],
    max_str_length: int = 10000,
) -> None:
    """Recursively validate all string values in dict don't exceed max length.

    Args:
        data: Dictionary to validate
        max_str_length: Maximum allowed string length

    Raises:
        ValueError: If any string value exceeds max_str_length

    Examples:
        >>> validate_dict_lengths({"name": "Product", "desc": "x" * 50}, max_str_length=100)
        >>> validate_dict_lengths({"name": "x" * 101}, max_str_length=100)
        Traceback (most recent call last):
        ValueError: Field 'name' exceeds maximum length (100 characters). Got 101 characters.
    """
    for key, value in data.items():
        if isinstance(value, str):
            validate_length(value, max_str_length, field_name=key)
        elif isinstance(value, dict):
            validate_dict_lengths(value, max_str_length)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, str):
                    validate_length(item, max_str_length, field_name=f"{key}[{i}]")
                elif isinstance(item, dict):
                    validate_dict_lengths(item, max_str_length)


def sanitize_dict_strings(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize all string values in dict (remove HTML, escape entities).

    Args:
        data: Dictionary with potentially unsafe strings

    Returns:
        New dictionary with sanitized strings

    Examples:
        >>> sanitize_dict_strings({"name": "<script>alert('xss')</script>Product"})
        {'name': "alert('xss')Product"}
        >>> sanitize_dict_strings({"items": [{"name": "<b>Bold</b>"}]})
        {'items': [{'name': 'Bold'}]}
    """
    sanitized = {}

    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_html(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict_strings(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_html(item) if isinstance(item, str)
                else sanitize_dict_strings(item) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized
