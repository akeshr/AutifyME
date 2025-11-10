"""Web Research Tools - Tavily API wrappers for product research and enrichment.

Provides two complementary research capabilities:
1. research_product_tool: Broad web search (multi-source aggregation)
2. extract_web_content_tool: Deep content extraction (single URL)

Architecture:
- Pattern B (Rich Schema): Structured outputs with comprehensive validation
- Intelligence-First: Returns LLM-optimized summaries, not raw HTML
- Type Safety: Pydantic models ensure data integrity
- Graceful Degradation: Continue workflow if research fails

Cost Optimization:
- Expected: ~150 searches/month (well within 1000 free tier)
- Caching: TODO - PostgreSQL cache with 24hr TTL
- Monitoring: LangSmith tracks usage and costs
"""

import logging
import math
from datetime import datetime
from typing import Annotated, Any, Literal

from langchain.tools import tool
from pydantic import Field

from autifyme_agents.core.config import settings
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)
from autifyme_agents.schemas.agent_outputs import (
    ProductResearchResult,
    ResearchSource,
    WebContentAnalysis,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================


def _calculate_research_confidence(sources: list[dict[str, Any]]) -> float:
    """Calculate research quality confidence score.

    Formula: avg_relevance * source_count_factor
    - avg_relevance: Mean of source relevance scores
    - source_count_factor: 1 - 1/sqrt(n) (diminishing returns)

    Examples:
    - 1 source @ 0.9 relevance = 0.9 * 0.0 = 0.0 (single source = low confidence)
    - 2 sources @ 0.9 avg = 0.9 * 0.29 = 0.26
    - 5 sources @ 0.9 avg = 0.9 * 0.55 = 0.50
    - 10 sources @ 0.9 avg = 0.9 * 0.68 = 0.61

    Args:
        sources: List of source dicts with 'score' field

    Returns:
        Confidence score (0.0-1.0)
    """
    if not sources:
        return 0.0

    # Average relevance
    scores = [s.get("score", 0.5) for s in sources]
    avg_relevance = sum(scores) / len(scores)

    # Source count factor (diminishing returns)
    n = len(sources)
    if n == 1:
        # Single source = low confidence regardless of score
        source_factor = 0.3
    else:
        # Multi-source: sqrt provides diminishing returns
        source_factor = 1 - (1 / math.sqrt(n))

    return min(avg_relevance * source_factor, 1.0)


def _extract_key_findings(sources: list[dict[str, Any]], max_findings: int = 5) -> list[str]:
    """Extract key findings from sources for quick consumption.

    Takes first sentence from top N sources as bullet points.

    Args:
        sources: List of source dicts with 'content' field
        max_findings: Maximum findings to extract

    Returns:
        List of key finding strings
    """
    findings = []

    for source in sources[:max_findings]:
        content = source.get("content", "")
        if not content:
            continue

        # Extract first sentence (simple heuristic: split on '. ')
        first_sentence = content.split(". ")[0].strip()
        if first_sentence and len(first_sentence) > 20:
            findings.append(first_sentence)

    return findings


# =============================================================================
# Research Tools
# =============================================================================


@tool
def research_product_tool(
    query: Annotated[
        str,
        Field(description=(
            "Natural language research query targeting product information. "
            "IMPORTANT: Be specific and targeted (not exploratory). "
            "Good: 'PET plastic bottles food grade specifications India' "
            "Bad: 'plastic bottles' (too broad, wastes API calls). "
            "Include: product type, material, specifications, location/market if relevant."
        ))
    ],
    max_results: Annotated[
        int,
        Field(
            default=5,
            ge=1,
            le=10,
            description="Max search results to return (1-10, default 5). More results = higher cost but better coverage."
        )
    ] = 5,
    include_answer: Annotated[
        bool,
        Field(
            default=True,
            description=(
                "Whether to include AI-generated answer summary from Tavily. "
                "True: Get concise answer + sources (recommended for most cases). "
                "False: Only get sources (use when you need raw data without synthesis)."
            )
        )
    ] = True,
) -> dict[str, Any]:
    """Research product information using web search (Tavily API).

    WHEN TO USE:
    - User provides minimal product data (enrich specifications, pricing, details)
    - Validating specifications (material safety, certifications, standards)
    - Competitive analysis (market pricing, alternatives, positioning)
    - Brand/manufacturer verification (confirm legitimacy, find contact info)
    - Technical documentation (safety data sheets, compliance, usage guidelines)

    COST AWARENESS:
    - Each call = 1 API credit (~$0.008 on paid tier, free tier: 1000/month)
    - Research efficiently: targeted queries, avoid exploratory searches
    - Expected usage: 2-3 searches per product, ~150/month = well within free tier

    QUALITY SIGNALS:
    - confidence: 0.7+ = good research, 0.5-0.7 = moderate, <0.5 = weak/insufficient
    - relevance_score per source: 0.8+ = highly relevant, 0.5-0.8 = relevant, <0.5 = tangential

    ERROR HANDLING:
    - If API fails: workflow continues WITHOUT research data (inform user)
    - If no results found: returns empty sources (inform user, consider follow-up query)
    - If network issues: returns error (retry once, then continue without research)

    Args:
        query: Targeted research query (specific product + context)
        max_results: Max sources to return (1-10, default 5)
        include_answer: Include AI summary (default True)

    Returns:
        Dict with research results or error:
        - On success: {"success": True, "query": str, "answer": str|None, "sources": [...], "confidence": float, ...}
        - On error: {"success": False, "error": str, "error_type": str, "query": str, "agent_action": str}

    Examples:
        >>> research_product_tool("PET bottles 500ml food grade India specifications")
        {"success": True, "answer": "PET bottles...", "sources": [...], "confidence": 0.72}

        >>> research_product_tool("Pavisha Packaging company details contact", max_results=3)
        {"success": True, "answer": "Pavisha is...", "sources": [...], "confidence": 0.65}
    """
    try:
        # Import here to avoid errors if langchain-tavily not installed
        try:
            from langchain_tavily import TavilySearch
        except ImportError as import_err:
            logger.error("langchain-tavily not installed", exc_info=True)
            return build_agent_error_response(
                exception=import_err,
                context={"query": query},
                fallback_type="IMPORT_ERROR",
                fallback_action=(
                    "langchain-tavily package not installed. "
                    "Install with: uv pip install langchain-tavily. "
                    "Continue workflow without research, inform user."
                ),
            )

        # Initialize Tavily search
        tavily = TavilySearch(
            api_key=settings.TAVILY_API_KEY,
            max_results=max_results,
        )

        logger.info(
            "Executing product research",
            extra={
                "query": query,
                "max_results": max_results,
                "include_answer": include_answer,
            }
        )

        # Execute search
        # Tavily returns: {"query": str, "answer": str, "results": [{"title": str, "url": str, "content": str, "score": float}]}
        raw_results = tavily.invoke({"query": query, "include_answer": include_answer})

        # Handle API returning dict with error
        if isinstance(raw_results, dict) and "error" in raw_results:
            logger.error(
                "Tavily API returned error",
                extra={
                    "query": query,
                    "error": raw_results.get("error"),
                }
            )
            return build_agent_error_response(
                exception=ValueError(f"Tavily API error: {raw_results['error']}"),
                context={"query": query},
                fallback_type="API_ERROR",
                fallback_action=(
                    "Tavily API returned error. Possible causes: invalid API key, rate limit, network issue. "
                    "Continue workflow without research, inform user."
                ),
            )

        # Parse results (Tavily can return dict or list depending on version)
        if isinstance(raw_results, dict):
            api_answer = raw_results.get("answer") if include_answer else None
            api_sources = raw_results.get("results", [])
            api_query = raw_results.get("query", query)
        elif isinstance(raw_results, list):
            # Older Tavily versions return list of dicts
            api_answer = None
            api_sources = raw_results
            api_query = query
        else:
            logger.error(
                "Unexpected Tavily response format",
                extra={
                    "query": query,
                    "response_type": type(raw_results).__name__,
                }
            )
            return build_agent_error_response(
                exception=ValueError(f"Unexpected Tavily response type: {type(raw_results)}"),
                context={"query": query},
                fallback_type="API_ERROR",
                fallback_action="Tavily API returned unexpected format. Continue without research, inform user.",
            )

        # Convert to structured schema
        sources = []
        for source in api_sources:
            sources.append(ResearchSource(
                title=source.get("title", "Untitled"),
                url=source.get("url", ""),
                content=source.get("content", ""),
                relevance_score=source.get("score", 0.5),
                published_date=source.get("published_date"),
            ))

        # Calculate quality metrics
        confidence = _calculate_research_confidence(api_sources)
        key_findings = _extract_key_findings(api_sources)

        # Build structured result
        result = ProductResearchResult(
            query=api_query,
            search_type="product_search",
            answer=api_answer,
            sources=sources,
            confidence=confidence,
            total_sources_found=len(sources),
            key_findings=key_findings,
            research_gaps=None,  # TODO: Implement gap detection
        )

        logger.info(
            "Product research completed",
            extra={
                "query": query,
                "sources_found": len(sources),
                "confidence": confidence,
                "has_answer": api_answer is not None,
            }
        )

        return build_success_response(result.model_dump())

    except ImportError as exc:
        # langchain-tavily not installed
        logger.error("Import error during research", exc_info=True)
        return build_agent_error_response(
            exception=exc,
            context={"query": query},
            fallback_type="IMPORT_ERROR",
            fallback_action="Research package not available. Continue workflow without research, inform user.",
        )

    except Exception as exc:
        # Catch-all for unexpected errors
        logger.error(
            "Unexpected error during product research",
            exc_info=True,
            extra={
                "query": query,
                "error_type": type(exc).__name__,
            }
        )
        return build_agent_error_response(
            exception=exc,
            context={"query": query},
            fallback_type="RESEARCH_ERROR",
            fallback_action=(
                "Unexpected research error. Retry once if transient (network, timeout). "
                "If persistent, continue workflow without research and inform user."
            ),
        )


@tool
def extract_web_content_tool(
    url: Annotated[
        str,
        Field(description=(
            "URL to extract content from (e.g., product page, spec sheet, documentation). "
            "IMPORTANT: Must be valid HTTP/HTTPS URL. "
            "Use after research_product_tool to deep-dive into specific sources."
        ))
    ],
    format: Annotated[
        Literal["markdown", "text"],
        Field(
            default="markdown",
            description=(
                "Output format for extracted content. "
                "markdown: Preserves structure (headers, lists, links) - best for LLM analysis. "
                "text: Plain text only - use for simple content or when markdown causes issues."
            )
        )
    ] = "markdown",
) -> dict[str, Any]:
    """Extract and parse web page content for LLM analysis (Tavily Extract API).

    WHEN TO USE:
    - Deep-dive into specific source from research_product_tool results
    - Extract detailed specifications from product pages
    - Parse technical documentation or safety data sheets
    - Get structured content from manufacturer websites

    COST AWARENESS:
    - Each call = 1 API credit (~$0.008, free tier: 1000/month)
    - Use selectively: only for high-value sources (not every link)
    - Prefer research_product_tool for broad searches (includes summaries)

    ERROR HANDLING:
    - Invalid URL: returns error (validate URL first, inform user)
    - Inaccessible page (404, timeout): returns error (try alternative sources)
    - Parsing failure: returns error (content may not be extractable)

    Args:
        url: Valid HTTP/HTTPS URL to extract
        format: Output format ("markdown" or "text", default "markdown")

    Returns:
        Dict with extracted content or error:
        - On success: {"success": True, "url": str, "title": str, "content": str, "format": str, ...}
        - On error: {"success": False, "error": str, "error_type": str, "url": str, "agent_action": str}

    Examples:
        >>> extract_web_content_tool("https://manufacturer.com/product-specs")
        {"success": True, "title": "Product Specs", "content": "# Specifications...", ...}

        >>> extract_web_content_tool("https://docs.example.com/safety", format="text")
        {"success": True, "content": "Safety guidelines...", "format": "text", ...}
    """
    try:
        # Import here to avoid errors if langchain-tavily not installed
        try:
            from langchain_tavily import TavilyExtract
        except ImportError as import_err:
            logger.error("langchain-tavily not installed", exc_info=True)
            return build_agent_error_response(
                exception=import_err,
                context={"url": url},
                fallback_type="IMPORT_ERROR",
                fallback_action=(
                    "langchain-tavily package not installed. "
                    "Skip content extraction, use summary from research_product_tool instead."
                ),
            )

        # Validate URL format (basic check)
        if not url.startswith(("http://", "https://")):
            return build_agent_error_response(
                exception=ValueError(f"Invalid URL format: {url}"),
                context={"url": url},
                fallback_type="VALIDATION_ERROR",
                fallback_action="URL must start with http:// or https://. Inform user, request valid URL.",
            )

        # Initialize Tavily extract
        tavily = TavilyExtract(api_key=settings.TAVILY_API_KEY)

        logger.info(
            "Extracting web content",
            extra={
                "url": url,
                "format": format,
            }
        )

        # Execute extraction
        # Tavily returns: {"url": str, "title": str, "content": str, "metadata": {...}}
        raw_result = tavily.invoke({"urls": [url], "format": format})

        # Handle API returning error
        if isinstance(raw_result, dict) and "error" in raw_result:
            logger.error(
                "Tavily Extract API returned error",
                extra={
                    "url": url,
                    "error": raw_result.get("error"),
                }
            )
            return build_agent_error_response(
                exception=ValueError(f"Tavily Extract error: {raw_result['error']}"),
                context={"url": url},
                fallback_type="API_ERROR",
                fallback_action=(
                    "Content extraction failed. Try alternative URL or use summary from research instead."
                ),
            )

        # Parse extraction (Tavily Extract returns list of results)
        if isinstance(raw_result, list) and raw_result:
            extraction = raw_result[0]  # Single URL = single result
        elif isinstance(raw_result, dict):
            extraction = raw_result
        else:
            logger.error(
                "Unexpected Tavily Extract response format",
                extra={
                    "url": url,
                    "response_type": type(raw_result).__name__,
                }
            )
            return build_agent_error_response(
                exception=ValueError(f"Unexpected Tavily Extract response: {type(raw_result)}"),
                context={"url": url},
                fallback_type="API_ERROR",
                fallback_action="Content extraction returned unexpected format. Try alternative source.",
            )

        # Extract fields
        content = extraction.get("content", "")
        if not content:
            return build_agent_error_response(
                exception=ValueError("No content extracted from URL"),
                context={"url": url},
                fallback_type="EXTRACTION_ERROR",
                fallback_action=(
                    "URL returned empty content. Possible causes: paywall, JavaScript-required, inaccessible. "
                    "Try alternative source or use summary from research instead."
                ),
            )

        # Build structured result
        word_count = len(content.split()) if content else 0

        result = WebContentAnalysis(
            url=url,
            title=extraction.get("title"),
            description=extraction.get("description"),
            content=content,
            content_format=format,
            structured_data=extraction.get("metadata"),
            publish_date=extraction.get("published_date"),
            author=extraction.get("author"),
            word_count=word_count,
        )

        logger.info(
            "Web content extraction completed",
            extra={
                "url": url,
                "word_count": word_count,
                "has_structured_data": result.structured_data is not None,
            }
        )

        return build_success_response(result.model_dump())

    except ImportError as exc:
        logger.error("Import error during content extraction", exc_info=True)
        return build_agent_error_response(
            exception=exc,
            context={"url": url},
            fallback_type="IMPORT_ERROR",
            fallback_action="Content extraction not available. Use summary from research instead.",
        )

    except Exception as exc:
        logger.error(
            "Unexpected error during content extraction",
            exc_info=True,
            extra={
                "url": url,
                "error_type": type(exc).__name__,
            }
        )
        return build_agent_error_response(
            exception=exc,
            context={"url": url},
            fallback_type="EXTRACTION_ERROR",
            fallback_action=(
                "Content extraction failed. Try alternative URL or use summary from research instead."
            ),
        )
