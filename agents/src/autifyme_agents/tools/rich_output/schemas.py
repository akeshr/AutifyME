"""Rich Output Engine schemas.

Defines input/output models for the generate_rich_output tool.
Domain-agnostic design - works for any structured data.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from autifyme_agents.schemas.models import CompanyProfile


class FieldHint(BaseModel):
    """Hint for how to render a specific field.

    Enables agents to provide human-friendly labels and formatting
    for domain-specific fields without hardcoding domain knowledge
    into the tool itself.
    """

    label: str = Field(
        description="Human-friendly label to display (e.g., 'SKU' instead of 'sku_code')"
    )
    format: Literal["text", "code", "currency", "number", "date", "url", "image"] = Field(
        default="text", description="How to format the value"
    )
    currency: str | None = Field(default="USD", description="Currency code if format=currency")


class RichOutputInput(BaseModel):
    """Input schema for rich output generation.

    Agents provide structured data and context; the rendering LLM
    analyzes data structure and company context to generate appropriate,
    branded visual output.
    """

    title: str = Field(description="Page title - appears in header and link preview (OG tags)")

    data: dict[str, Any] | list[dict[str, Any]] = Field(
        description="Structured data to render. Any shape - LLM adapts layout."
    )

    context: str = Field(description="WHY this page exists, WHAT user needs to understand/do")

    company_profile: CompanyProfile = Field(
        description="Client company profile for branding. Injected from agent context."
    )

    field_hints: dict[str, FieldHint] | None = Field(
        default=None,
        description=(
            "Hints for field rendering. Key=field_name, Value=display config. "
            "Use this to provide human-friendly labels and formatting for domain-specific fields."
        ),
    )

    images: list[str] | None = Field(
        default=None, description="Image URLs. First = primary (OG preview). Full https:// URLs."
    )

    layout_hint: Literal["grid", "table", "hierarchy", "comparison", "timeline"] | None = Field(
        default=None, description="Optional layout hint. LLM may override based on data structure."
    )

    highlight_fields: list[str] | None = Field(
        default=None, description="Field names to emphasize visually (e.g., ['price', 'status'])"
    )

    ttl_days: int = Field(
        default=30,
        ge=0,
        le=365,
        description="Days until this output expires and is deleted. Default 30. Set 0 for permanent.",
    )


class RichOutputResult(BaseModel):
    """Result from rich output generation."""

    success: bool = Field(description="Whether generation succeeded")
    url: str | None = Field(default=None, description="Public URL to branded page")
    filename: str | None = Field(default=None, description="Storage filename for reference")
    summary: str = Field(description="Text summary for chat context")
    expires_at: str | None = Field(
        default=None, description="ISO timestamp when output will be deleted"
    )
    error: str | None = Field(default=None, description="Error message if generation failed")
