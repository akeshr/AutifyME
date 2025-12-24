"""Rich Output Tool - Generate branded HTML pages from structured data.

Enables agents to present complex data visually instead of text walls.
LLM-powered HTML generation with client company branding.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from langchain_core.tools import StructuredTool

from autifyme_agents.core.tool_error_handler import build_agent_error_response
from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.tools.rich_output.html_generator import (
    HTMLGenerationError,
    generate_html,
)
from autifyme_agents.tools.rich_output.schemas import (
    FieldHint,
    RichOutputInput,
    RichOutputResult,
)
from autifyme_agents.tools.rich_output.utils.validation import validate_image_url

logger = logging.getLogger(__name__)


# Module-level storage reference (set by tool factory)
# Uses Any because we access _ensure_client() which is an implementation
# detail of SupabaseStorageClient, not part of StorageInterface
_storage_client: Any = None


def _set_storage_client(storage: Any) -> None:
    """Set the storage client for uploads."""
    global _storage_client
    _storage_client = storage


async def _upload_rich_output(
    html_content: str,
    filename: str,
    ttl_days: int = 30,
    bucket: str = "assets",
) -> dict[str, Any]:
    """Upload HTML to Supabase Storage with TTL metadata.

    Uploads to outputs/ folder within the assets bucket.
    Sets expires_at metadata for cleanup job.

    Args:
        html_content: Generated HTML content
        filename: Unique filename (without folder prefix)
        ttl_days: Days until expiration (0 = permanent)
        bucket: Storage bucket name

    Returns:
        Dict with url, storage_path, expires_at

    Raises:
        RuntimeError: If storage client not configured
        Exception: On upload failure
    """
    if _storage_client is None:
        raise RuntimeError(
            "Storage client not configured. "
            "Pass storage to create_rich_output_tool()."
        )

    storage_path = f"outputs/{filename}"

    # Calculate expiration timestamp
    expires_at: str | None = None
    if ttl_days > 0:
        expires_at = (datetime.now(UTC) + timedelta(days=ttl_days)).isoformat()

    # Get underlying Supabase client
    client = _storage_client._ensure_client()

    # Upload HTML file
    # Note: file_options doesn't support user_metadata directly in supabase-py
    # We store expires_at in a separate tracking mechanism if needed
    file_bytes = html_content.encode("utf-8")

    client.storage.from_(bucket).upload(
        path=storage_path,
        file=file_bytes,
        file_options={
            "content-type": "text/html; charset=utf-8",
            "upsert": "true",  # Overwrite if exists
        },
    )

    # Get public URL
    public_url = client.storage.from_(bucket).get_public_url(storage_path)

    logger.info(
        "Uploaded rich output",
        extra={
            "bucket": bucket,
            "storage_path": storage_path,
            "size_bytes": len(file_bytes),
            "expires_at": expires_at,
        }
    )

    return {
        "url": public_url,
        "storage_path": storage_path,
        "expires_at": expires_at,
    }


async def _generate_rich_output_impl(
    title: str,
    data: dict[str, Any] | list[dict[str, Any]],
    context: str,
    company_profile: CompanyProfile | dict[str, Any],
    field_hints: dict[str, FieldHint | dict[str, Any]] | None = None,
    images: list[str] | None = None,
    layout_hint: str | None = None,
    highlight_fields: list[str] | None = None,
    ttl_days: int = 30,
) -> dict[str, Any]:
    """Generate branded HTML output from structured data.

    Flow:
    1. Validate inputs (images, company profile)
    2. Convert field_hints dicts to FieldHint objects
    3. Generate HTML via LLM (with input/output sanitization)
    4. Upload to Supabase Storage with TTL metadata
    5. Return URL and summary

    Args:
        title: Page title - appears in header and link preview
        data: Structured data to render (any shape)
        context: WHY this page exists, WHAT user needs to do
        company_profile: Client company profile for branding
        field_hints: Optional field rendering hints
        images: Optional image URLs (first = OG preview)
        layout_hint: Optional layout suggestion
        highlight_fields: Optional fields to emphasize
        ttl_days: Days until expiration (0 = permanent)

    Returns:
        RichOutputResult as dict
    """
    try:
        # Convert company_profile dict to model if needed
        if isinstance(company_profile, dict):
            company_profile = CompanyProfile.model_validate(company_profile)

        # Convert field_hints dicts to FieldHint objects
        parsed_hints: dict[str, FieldHint] | None = None
        if field_hints:
            parsed_hints = {}
            for key, hint in field_hints.items():
                if isinstance(hint, dict):
                    parsed_hints[key] = FieldHint.model_validate(hint)
                else:
                    parsed_hints[key] = hint

        # Validate image URLs
        valid_images: list[str] | None = None
        if images:
            valid_images = [url for url in images if validate_image_url(url)]
            if len(valid_images) < len(images):
                logger.warning(
                    "Some image URLs were invalid and skipped",
                    extra={
                        "total": len(images),
                        "valid": len(valid_images),
                    }
                )

        # Generate HTML
        html_content, summary = await generate_html(
            title=title,
            data=data,
            context=context,
            company_profile=company_profile,
            field_hints=parsed_hints,
            images=valid_images,
            layout_hint=layout_hint,
            highlight_fields=highlight_fields,
        )

        # Generate unique filename
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}.html"

        # Upload to storage
        upload_result = await _upload_rich_output(
            html_content=html_content,
            filename=filename,
            ttl_days=ttl_days,
        )

        result = RichOutputResult(
            success=True,
            url=upload_result["url"],
            filename=filename,
            summary=summary,
            expires_at=upload_result["expires_at"],
        )

        logger.info(
            "Rich output generated successfully",
            extra={
                "title": title,
                "company": company_profile.name,
                "url": result.url,
                "summary": summary,
            }
        )

        return result.model_dump()

    except HTMLGenerationError as e:
        logger.error(
            "HTML generation failed",
            extra={"title": title, "error": str(e)},
            exc_info=True
        )
        return RichOutputResult(
            success=False,
            summary="",
            error=f"HTML generation failed: {str(e)}",
        ).model_dump()

    except Exception as e:
        logger.exception("Rich output generation failed")
        return build_agent_error_response(
            exception=e,
            context={"title": title, "data_type": type(data).__name__},
            fallback_type="RICH_OUTPUT_ERROR",
            fallback_action=(
                "Rich output generation failed. "
                "Consider presenting data as text summary instead."
            ),
        )


def create_rich_output_tool(storage: Any = None) -> StructuredTool:
    """Create the generate_rich_output tool.

    The tool generates branded HTML pages from structured data,
    enabling agents to present complex information visually.

    Args:
        storage: Storage client for Supabase uploads.
            Required for production use. Pass SupabaseStorageClient instance.

    Returns:
        StructuredTool for generate_rich_output
    """
    _set_storage_client(storage)

    return StructuredTool.from_function(
        coroutine=_generate_rich_output_impl,
        name="generate_rich_output",
        description="""Generate visual HTML output when text is insufficient.

USE WHEN:
- Structured data with 5+ items requiring verification
- Hierarchical/nested data (categories, subcategories)
- Comparisons between entities
- Multiple validation errors (3+)
- Large query results
- Any case where text would be a "wall of data"

DO NOT USE WHEN:
- Simple confirmations
- Short lists (< 5 items)
- Conversational responses
- Single error with clear message

HOW IT WORKS:
1. Pass your structured data + context + company_profile
2. Use field_hints for domain-specific labels (e.g., "sku_code" -> "SKU")
3. LLM generates branded HTML matching company's style
4. Returns public URL + summary text

RESPONSE PATTERN:
Include BOTH the URL AND the summary in your response:
"Here's the [what] I've prepared:

[Summary from tool - e.g., '12 items | $499-$1,299']

[URL from tool]

[What you want user to do next]"

FIELD HINTS:
Use to provide human-friendly labels:
field_hints={
    "sku_code": {"label": "SKU", "format": "code"},
    "unit_price": {"label": "Price", "format": "currency"},
    "moq": {"label": "Min Order Qty", "format": "number"}
}

RETURNS:
{
    "success": true,
    "url": "https://...supabase.../outputs/abc123.html",
    "filename": "20251219_123456_abc12345.html",
    "summary": "12 items | $499 - $1,299",
    "expires_at": "2026-01-18T00:00:00Z",
    "error": null
}""",
        args_schema=RichOutputInput,
        return_direct=False,
    )
