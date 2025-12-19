"""HTML Generator LLM integration for Rich Output Engine.

Uses Gemini 3 Flash for fast, cheap HTML generation from structured data.
"""

from __future__ import annotations

import contextlib
import json
import logging
from typing import Any

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.tools.rich_output.prompts.system_prompt import (
    build_html_generator_prompt,
)
from autifyme_agents.tools.rich_output.schemas import FieldHint
from autifyme_agents.tools.rich_output.utils.input_sanitization import (
    sanitize_input_data,
)
from autifyme_agents.tools.rich_output.utils.output_sanitization import (
    sanitize_llm_html_output,
)
from autifyme_agents.tools.rich_output.utils.validation import validate_html_structure

logger = logging.getLogger(__name__)

# Model configuration for HTML generation
# Gemini 3 Flash: Fast, cheap, excellent at HTML/CSS, 1M context
HTML_GENERATOR_MODEL = "gemini-3-flash-preview"
HTML_GENERATOR_PROVIDER = "google"
HTML_GENERATOR_TEMPERATURE = 1.0  # Gemini 3 default (below 1.0 may cause looping)
HTML_GENERATOR_MAX_TOKENS = 16000  # Sufficient for complex pages


class HTMLGenerationError(Exception):
    """Raised when HTML generation fails."""

    pass


def _build_user_prompt(
    title: str,
    data: dict[str, Any] | list[dict[str, Any]],
    context: str,
    field_hints: dict[str, FieldHint] | None = None,
    images: list[str] | None = None,
    layout_hint: str | None = None,
    highlight_fields: list[str] | None = None,
) -> str:
    """Build the user prompt with data and rendering instructions.

    Args:
        title: Page title
        data: Structured data to render (already sanitized)
        context: What user needs to understand/do
        field_hints: Optional field rendering hints
        images: Optional image URLs
        layout_hint: Optional layout suggestion
        highlight_fields: Optional fields to emphasize

    Returns:
        Formatted user prompt as JSON string
    """
    prompt_data: dict[str, Any] = {
        "title": title,
        "data": data,
        "context": context,
    }

    if field_hints:
        prompt_data["field_hints"] = {
            k: v.model_dump() for k, v in field_hints.items()
        }

    if images:
        prompt_data["images"] = images

    if layout_hint:
        prompt_data["layout_hint"] = layout_hint

    if highlight_fields:
        prompt_data["highlight_fields"] = highlight_fields

    return json.dumps(prompt_data, indent=2)


async def generate_html(
    title: str,
    data: dict[str, Any] | list[dict[str, Any]],
    context: str,
    company_profile: CompanyProfile,
    field_hints: dict[str, FieldHint] | None = None,
    images: list[str] | None = None,
    layout_hint: str | None = None,
    highlight_fields: list[str] | None = None,
    max_retries: int = 2,
) -> tuple[str, str]:
    """Generate HTML from structured data using LLM.

    Two-layer sanitization:
    1. INPUT: Escape HTML entities in data before sending to LLM
    2. OUTPUT: Strip scripts and event handlers from LLM response

    Args:
        title: Page title
        data: Structured data to render
        context: What user needs to understand/do
        company_profile: Client company profile for branding
        field_hints: Optional field rendering hints
        images: Optional image URLs
        layout_hint: Optional layout suggestion
        highlight_fields: Optional fields to emphasize
        max_retries: Maximum retry attempts for malformed HTML

    Returns:
        Tuple of (html_content, summary)

    Raises:
        HTMLGenerationError: If HTML generation fails after retries
    """
    # Layer 1: Sanitize INPUT data
    sanitized_data = sanitize_input_data(data)

    # Build prompts
    system_prompt = build_html_generator_prompt(
        company_name=company_profile.name,
        company_industry=company_profile.industry,
        company_brand_voice=company_profile.brand_voice,
        company_target_audience=company_profile.target_audience,
        company_style_preferences=company_profile.style_preferences,
    )

    user_prompt = _build_user_prompt(
        title=title,
        data=sanitized_data,
        context=context,
        field_hints=field_hints,
        images=images,
        layout_hint=layout_hint,
        highlight_fields=highlight_fields,
    )

    # Get LLM
    llm = get_llm(
        provider=HTML_GENERATOR_PROVIDER,
        model=HTML_GENERATOR_MODEL,
        temperature=HTML_GENERATOR_TEMPERATURE,
        max_output_tokens=HTML_GENERATOR_MAX_TOKENS,
        tags=["rich_output", "html_generator"],
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    last_error: str | None = None

    for attempt in range(max_retries + 1):
        try:
            logger.info(
                "Generating HTML",
                extra={
                    "attempt": attempt + 1,
                    "title": title,
                    "company": company_profile.name,
                    "data_type": type(data).__name__,
                    "item_count": len(data) if isinstance(data, list) else 1,
                }
            )

            # Invoke LLM
            response = await llm.ainvoke(messages)
            html_content = response.content

            # Handle AIMessage content types
            if isinstance(html_content, list):
                # Extract text from content blocks
                text_parts = [
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in html_content
                ]
                html_content = "".join(text_parts)

            if not isinstance(html_content, str):
                html_content = str(html_content)

            # Layer 2: Sanitize OUTPUT HTML
            html_content = sanitize_llm_html_output(html_content)

            # Validate structure
            is_valid, error_msg = validate_html_structure(html_content)
            if not is_valid:
                logger.warning(
                    "HTML validation failed",
                    extra={
                        "attempt": attempt + 1,
                        "error": error_msg,
                        "html_length": len(html_content),
                    }
                )
                last_error = error_msg

                # Add feedback for retry
                if attempt < max_retries:
                    messages.append({
                        "role": "assistant",
                        "content": html_content
                    })
                    messages.append({
                        "role": "user",
                        "content": f"Invalid HTML: {error_msg}. Please regenerate with proper structure."
                    })
                    continue

            # Generate summary
            summary = _generate_summary(data)

            logger.info(
                "HTML generated successfully",
                extra={
                    "attempt": attempt + 1,
                    "html_size_bytes": len(html_content.encode("utf-8")),
                    "summary": summary,
                }
            )

            return html_content, summary

        except Exception as e:
            logger.error(
                "HTML generation failed",
                extra={
                    "attempt": attempt + 1,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            last_error = str(e)

            if attempt >= max_retries:
                break

    raise HTMLGenerationError(
        f"HTML generation failed after {max_retries + 1} attempts. Last error: {last_error}"
    )


def _generate_summary(data: dict[str, Any] | list[dict[str, Any]]) -> str:
    """Generate a text summary for chat context.

    Creates a brief description of the data for inclusion in chat messages.

    Args:
        data: The structured data

    Returns:
        Brief summary string (e.g., "12 items | $499 - $1,299")
    """
    if isinstance(data, list):
        count = len(data)
        if count == 0:
            return "No items"

        # Try to extract price range if present
        prices = []
        for item in data:
            if isinstance(item, dict):
                for key in ["price", "unit_price", "amount", "cost"]:
                    if key in item and item[key] is not None:
                        with contextlib.suppress(ValueError, TypeError):
                            prices.append(float(item[key]))
                        break

        if prices:
            min_price = min(prices)
            max_price = max(prices)
            if min_price == max_price:
                return f"{count} items | ${min_price:,.2f}"
            return f"{count} items | ${min_price:,.2f} - ${max_price:,.2f}"

        return f"{count} items"

    elif isinstance(data, dict):
        # Single entity
        name = data.get("name") or data.get("title") or data.get("id")
        if name:
            return f"Details: {name}"
        return "Entity details"

    return "Data rendered"
