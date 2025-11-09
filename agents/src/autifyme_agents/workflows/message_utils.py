"""Message content extraction utilities.

Handles both OpenAI (string) and Gemini (list) content formats.
"""

from typing import Any


def extract_text_content(content: str | list[dict[str, Any]] | Any) -> str | None:
    """Extract text from message content (handles both string and list formats).

    Args:
        content: Message content (string for OpenAI, list for Gemini multimodal)

    Returns:
        Extracted text string, or None if no text found

    Examples:
        >>> extract_text_content("Hello")
        "Hello"
        >>> extract_text_content([{"type": "text", "text": "Hello"}])
        "Hello"
        >>> extract_text_content([])
        None
    """
    # Handle string content (OpenAI format)
    if isinstance(content, str) and content.strip():
        return content

    # Handle list content (Gemini multimodal format)
    # Gemini returns: [{"type": "text", "text": "actual message"}]
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text: str = block.get("text", "")
                if text.strip():
                    return text

    return None
