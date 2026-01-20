"""Structured output schemas for agent responses."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AgentOutput(BaseModel):
    """Base model for all agent outputs with consistent success flag."""

    success: bool = Field(..., description="Indicates whether the operation was successful.")
    message: str | None = Field(None, description="Details about the outcome.")


class ProductCatalogedOutput(AgentOutput):
    """Output schema for successful product cataloging."""

    success: Literal[True] = Field(True, description="Always True for successful cataloging.")
    product_id: UUID = Field(..., description="The unique identifier of the saved product.")
    message: str = Field("Product has been successfully saved to the catalog.")
    product: dict[str, Any] = Field(
        ..., description="The full product record saved to the catalog."
    )


class ErrorOutput(AgentOutput):
    """Output schema for reporting errors."""

    success: Literal[False] = Field(False, description="Always False for errors.")
    error_type: str = Field(
        ..., description="The type of error (e.g., 'Validation Error', 'API Failure')."
    )
    message: str = Field(..., description="Detailed error message.")


class ImageAnalysisResult(BaseModel):
    """
    Structured output for image analysis specialist.

    Used with .with_structured_output() to ensure LLM returns valid data.
    Schema aligned with vision API prompt - all requested fields present.
    """

    visual_description: str = Field(
        ...,
        description="Detailed, objective product description suitable for e-commerce.",
        min_length=20,
    )
    identified_colors: list[str] = Field(
        default_factory=list,
        description="Dominant colors visible in the product (e.g., 'Clear', 'Blue', 'Amber').",
    )
    identified_materials: list[str] = Field(
        default_factory=list,
        description="Materials identified in the product (e.g., 'PET', 'Glass', 'Aluminum', 'Cardboard').",
    )
    style_tags: list[str] = Field(
        default_factory=list,
        description="Style keywords (e.g., 'modern', 'industrial', 'minimalist', 'vintage').",
    )
    dimensions_indicators: str | None = Field(
        None,
        description="Estimated dimensions or size indicators visible in image (e.g., '500ml capacity', 'approx 20cm height').",
    )
    condition_assessment: str | None = Field(
        None,
        description="Product condition and quality indicators (e.g., 'new/unused', 'excellent condition', 'minor wear').",
    )
    brand_elements: list[str] = Field(
        default_factory=list,
        description="Visible brand elements, logos, or manufacturer markings (e.g., 'Pavisha logo on cap', 'FDA marking').",
    )


# =============================================================================
# Research Tool Schemas (Web Search & Content Extraction)
# =============================================================================


class ResearchSource(BaseModel):
    """Single search result source from web research.

    Represents one source returned by Tavily search API with relevance scoring.
    """

    title: str = Field(..., description="Page title or heading from source")
    url: str = Field(..., description="Source URL for citation and verification")
    content: str = Field(
        ..., description="LLM-optimized content summary from Tavily (not raw HTML)"
    )
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Tavily relevance score (0.0-1.0, higher = more relevant)"
    )
    published_date: str | None = Field(
        None, description="Publication date if available (ISO 8601 format)"
    )


class ProductResearchResult(BaseModel):
    """Structured research findings for product enrichment.

    Used by research_product_tool to return web search results.
    Comprehensive schema ensures all API data captured without loss.
    """

    # Query metadata
    query: str = Field(..., description="Original search query executed")
    search_type: Literal["product_search", "content_extract"] = Field(
        ..., description="Type of research performed"
    )

    # Primary findings
    answer: str | None = Field(
        None, description="AI-generated answer summary from Tavily (when include_answer=True)"
    )
    sources: list[ResearchSource] = Field(
        default_factory=list,
        description="Ranked sources (highest relevance first), max based on max_results parameter",
    )

    # Quality signals
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Research quality score: avg(source relevance scores) * (1 - 1/sqrt(source_count))",
    )
    total_sources_found: int = Field(
        ..., description="Number of sources returned by API (same as len(sources))"
    )

    # Agent guidance (derived fields for quick consumption)
    key_findings: list[str] = Field(
        default_factory=list,
        description="Bullet-point takeaways extracted from sources for quick reference",
    )
    research_gaps: list[str] | None = Field(
        None, description="What couldn't be found or remains unclear (informs follow-up research)"
    )


class WebContentAnalysis(BaseModel):
    """Parsed web content for LLM analysis.

    Used by extract_web_content_tool to return extracted page content.
    """

    url: str = Field(..., description="Source URL that was extracted")
    title: str | None = Field(None, description="Page title from HTML <title> or Open Graph")
    description: str | None = Field(
        None, description="Page description from meta tags or Open Graph"
    )
    content: str = Field(
        ..., description="Extracted content in markdown or text format (LLM-ready)"
    )
    content_format: Literal["markdown", "text"] = Field(
        ..., description="Format of extracted content"
    )
    structured_data: dict[str, Any] | None = Field(
        None, description="Structured data extracted from JSON-LD, microdata, or Open Graph"
    )
    publish_date: str | None = Field(
        None, description="Publication date if available (ISO 8601 format)"
    )
    author: str | None = Field(None, description="Content author if available")
    word_count: int | None = Field(None, description="Word count of extracted content")
