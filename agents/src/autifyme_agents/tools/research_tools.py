"""Web Research Tools - Tavily API wrappers for product research and enrichment.

Factory functions following database tools pattern:
- create_research_product_tool(settings): Web search with dependency injection
- create_extract_web_content_tool(settings): Content extraction with DI

Architecture:
- Factory Pattern: Dependency injection for settings (Tavily API key)
- Rich Schema: Structured outputs with comprehensive validation
- Intelligence-First: Returns LLM-optimized summaries, not raw HTML
- Type Safety: Pydantic models ensure data integrity
- Graceful Degradation: Continue workflow if research fails
- Consistent Pattern: Matches database tools (StructuredTool.from_function)

Cost Optimization:
- Expected: ~150 searches/month (well within 1000 free tier)
- Caching: TODO - PostgreSQL cache with 24hr TTL
- Monitoring: LangSmith tracks usage and costs
"""

import logging
import math
from typing import Any, Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from autifyme_agents.core.config import Settings
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
# Input Schemas (Explicit Pydantic models for tool parameters)
# =============================================================================


class ResearchProductInput(BaseModel):
    """Input schema for research_product_tool."""

    query: str = Field(
        ...,
        description=(
            "Natural language research query targeting product information. "
            "IMPORTANT: Be specific and targeted (not exploratory). "
            "Good: 'PET plastic bottles food grade specifications India' "
            "Bad: 'plastic bottles' (too broad, wastes API calls). "
            "Include: product type, material, specifications, location/market if relevant."
        ),
        min_length=3,
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Max search results to return (1-10, default 5). More results = higher cost but better coverage.",
    )
    include_answer: bool = Field(
        default=True,
        description=(
            "Whether to include AI-generated answer summary from Tavily. "
            "True: Get concise answer + sources (recommended for most cases). "
            "False: Only get sources (use when you need raw data without synthesis)."
        ),
    )


class ExtractWebContentInput(BaseModel):
    """Input schema for extract_web_content_tool."""

    url: str = Field(
        ...,
        description=(
            "URL to extract content from (e.g., product page, spec sheet, documentation). "
            "IMPORTANT: Must be valid HTTP/HTTPS URL. "
            "Use after research_product_tool to deep-dive into specific sources."
        ),
        min_length=10,
    )
    format: Literal["markdown", "text"] = Field(
        default="markdown",
        description=(
            "Output format for extracted content. "
            "markdown: Preserves structure (headers, lists, links) - best for LLM analysis. "
            "text: Plain text only - use for simple content or when markdown causes issues."
        ),
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _calculate_research_confidence(sources: list[dict[str, Any]]) -> float:
    """Calculate research quality confidence score.

    Formula: avg_relevance * source_count_factor
    - avg_relevance: Mean of source relevance scores
    - source_count_factor: 1 - 1/sqrt(n) (diminishing returns)

    Examples:
    - 1 source @ 0.9 relevance = 0.9 * 0.3 = 0.27 (single source = low confidence)
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
    scores: list[float] = [float(s.get("score", 0.5)) for s in sources]
    avg_relevance: float = sum(scores) / len(scores)

    # Source count factor (diminishing returns)
    n = len(sources)
    # Single source = moderate confidence (not zero); multi-source uses sqrt for diminishing returns
    source_factor = 0.3 if n == 1 else 1 - (1 / math.sqrt(n))

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
# Tool Factory Functions (Dependency Injection Pattern)
# =============================================================================


def create_research_product_tool(settings: Settings) -> StructuredTool:
    """Create web research tool with dependency injection.

    Factory function following database tools pattern for consistency.

    Args:
        settings: Application settings (contains TAVILY_API_KEY)

    Returns:
        LangChain StructuredTool for product research
    """

    async def _research_product_impl(
        query: str,
        max_results: int = 5,
        include_answer: bool = True,
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

            # Initialize Tavily search with injected API key
            tavily = TavilySearch(
                api_key=settings.TAVILY_API_KEY,
                max_results=max_results,
                include_answer=include_answer,  # Constructor parameter, not invoke parameter
            )

            logger.info(
                "Executing product research",
                extra={
                    "query": query,
                    "max_results": max_results,
                    "include_answer": include_answer,
                }
            )

            # Execute search (only query in invoke dict)
            raw_results = tavily.invoke({"query": query})

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
            logger.error("Import error during research", exc_info=True)
            return build_agent_error_response(
                exception=exc,
                context={"query": query},
                fallback_type="IMPORT_ERROR",
                fallback_action="Research package not available. Continue workflow without research, inform user.",
            )

        except Exception as exc:
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

    # Return StructuredTool with explicit schema
    return StructuredTool.from_function(
        coroutine=_research_product_impl,
        name="research_product_tool",
        description=(
            "PURPOSE: Web search for product info (Tavily API) - enrich minimal user data with specs, pricing, certifications, compliance, market context. Fill knowledge gaps that visual analysis and catalog cannot answer.\n\n"
            "USE WHEN:\n"
            "- User provides minimal data: Need material grade, capacity, typical pricing\n"
            "- Validating specifications: User says 500ml but looks 750ml\n"
            "- Unknown products: Identify product type, common specs from image\n"
            "- Pricing research: Need market baseline for catalog entry\n"
            "- Compliance gaps: HSN code, food-grade certification, material safety\n"
            "- Brand verification: Manufacturer legitimacy, contact details\n"
            "- Technical docs: Safety specs, usage guidelines, handling requirements\n\n"
            "DON'T USE:\n"
            "- For catalog data (use read_data - research is external knowledge)\n"
            "- Exploratory searches without focus (wastes API credits)\n"
            "- When visual analysis sufficient\n"
            "- Generic queries like 'plastic bottles' (be specific with material, size, market)\n"
            "- When user provided complete specifications\n\n"
            "CRITICAL:\n"
            "- query: Be SPECIFIC - include product type, material, size, market\n"
            "  Good: 'PET plastic jars 500ml food grade specifications India', 'HSN code glass jars food packaging'\n"
            "  Bad: 'plastic bottles' (too broad, generic results)\n"
            "- max_results (1-10, default 5): 5 usually sufficient, 8-10 for complex products, 1-3 for quick checks\n"
            "- include_answer (default True): AI summary + sources (recommended)\n"
            "- Quality signals:\n"
            "  * confidence >=0.7: Good research, trust findings\n"
            "  * confidence 0.5-0.7: Moderate, proceed with caution\n"
            "  * confidence <0.5: Weak, verify or continue without\n"
            "  * relevance_score >=0.8: Highly relevant source\n"
            "- Cost: ~$0.008/search, 1000/month free tier, 2-3 searches per product typical\n"
            "- Graceful failures: Research errors never block workflow - inform user, continue without\n\n"
            "EXAMPLES:\n"
            "# Enrich minimal input\n"
            "research_product_tool(query='PET plastic jars 500ml food grade specifications BPA free India', max_results=5)\n"
            "Returns: AI summary + 5 sources - material safety, specs, pricing, manufacturers\n\n"
            "# Compliance research\n"
            "research_product_tool(query='HSN code plastic storage containers food packaging India', max_results=3)\n"
            "Returns: HSN code 3923, classification, regulatory requirements\n\n"
            "RETURNS: Always a structured dict with success flag.\n"
            "- success=True: ProductResearchResult fields (e.g., query, answer?, sources[], confidence, key_findings[])\n"
            "- success=False: {error, error_type, query, Agent Action: ...}\n"
            "Use extract_web_content_tool on high-relevance URLs (0.8+) for deep-dive."
        ),
        args_schema=ResearchProductInput,
    )


def create_extract_web_content_tool(settings: Settings) -> StructuredTool:
    """Create web content extraction tool with dependency injection.

    Factory function following database tools pattern for consistency.

    Args:
        settings: Application settings (contains TAVILY_API_KEY)

    Returns:
        LangChain StructuredTool for content extraction
    """

    async def _extract_web_content_impl(
        url: str,
        format: Literal["markdown", "text"] = "markdown",
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

            # Initialize Tavily extract with injected API key and format
            # IMPORTANT: format MUST be in constructor, not invoke dict
            # Passing format in invoke causes "multiple values for keyword argument 'format'" error
            tavily = TavilyExtract(api_key=settings.TAVILY_API_KEY, format=format)

            logger.info(
                "Extracting web content",
                extra={
                    "url": url,
                    "format": format,
                }
            )

            # Execute extraction (only urls in invoke dict)
            raw_result = tavily.invoke({"urls": [url]})

            # Handle API response format
            # Success: dict with {results: [{url, title, raw_content, images}], failed_results: [], ...}
            # Failure: string with error message
            if isinstance(raw_result, str):
                # API returns string on extraction failure
                logger.error(
                    "Tavily Extract API returned error string",
                    extra={
                        "url": url,
                        "error": raw_result,
                    }
                )
                return build_agent_error_response(
                    exception=ValueError(f"Tavily Extract error: {raw_result}"),
                    context={"url": url},
                    fallback_type="API_ERROR",
                    fallback_action=(
                        "Content extraction failed. Possible causes: paywall, JavaScript-required, inaccessible. "
                        "Try alternative URL or use summary from research instead."
                    ),
                )

            # Parse successful extraction (dict with results array)
            if not isinstance(raw_result, dict):
                logger.error(
                    "Unexpected Tavily Extract response format",
                    extra={
                        "url": url,
                        "response_type": type(raw_result).__name__,
                    }
                )
                return build_agent_error_response(
                    exception=ValueError(f"Unexpected Tavily Extract response type: {type(raw_result)}"),
                    context={"url": url},
                    fallback_type="API_ERROR",
                    fallback_action="Content extraction returned unexpected format. Try alternative source.",
                )

            # Extract results from nested structure
            results = raw_result.get("results", [])
            failed_results = raw_result.get("failed_results", [])

            if not results or len(results) == 0:
                # Check failed_results for reason
                failure_reason = failed_results[0] if failed_results else "Unknown reason"
                logger.error(
                    "Tavily Extract returned no results",
                    extra={
                        "url": url,
                        "failed_results": failed_results,
                    }
                )
                return build_agent_error_response(
                    exception=ValueError(f"No content extracted from URL: {failure_reason}"),
                    context={"url": url},
                    fallback_type="EXTRACTION_ERROR",
                    fallback_action=(
                        "URL returned no extractable content. Possible causes: paywall, JavaScript-required, "
                        "inaccessible, or content not text-based. Try alternative source or use summary from research."
                    ),
                )

            # Extract first result (single URL request = single result)
            extraction = results[0]

            # Map API fields to expected schema
            # API returns: url, title, raw_content, images
            # Schema expects: url, title, content, description, structured_data, publish_date, author, word_count
            content = extraction.get("raw_content", "")
            if not content:
                return build_agent_error_response(
                    exception=ValueError("Extracted result has empty raw_content"),
                    context={"url": url},
                    fallback_type="EXTRACTION_ERROR",
                    fallback_action=(
                        "URL extraction succeeded but content is empty. Try alternative source or use summary."
                    ),
                )

            # Build structured result
            word_count = len(content.split()) if content else 0

            result = WebContentAnalysis(
                url=extraction.get("url", url),  # Use extracted URL (may differ due to redirects)
                title=extraction.get("title"),
                description=None,  # Tavily Extract API doesn't return description
                content=content,
                content_format=format,
                structured_data=None,  # Tavily Extract API doesn't return structured metadata
                publish_date=None,  # Tavily Extract API doesn't return publish date
                author=None,  # Tavily Extract API doesn't return author
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

    # Return StructuredTool with explicit schema
    return StructuredTool.from_function(
        coroutine=_extract_web_content_impl,
        name="extract_web_content_tool",
        description=(
            "PURPOSE: Extract full web page content (Tavily Extract API) - deep-dive into high-value sources from research_product_tool. Get complete specs, pricing tables, technical docs when research summaries insufficient.\n\n"
            "USE WHEN:\n"
            "- Research summary insufficient: Need full source content for details\n"
            "- High-value source: 0.8+ relevance score, comprehensive URL\n"
            "- Specifications needed: Product page with detailed specs, dimensions, materials\n"
            "- Technical docs: Safety data sheets, compliance docs, usage guidelines\n"
            "- Pricing details: Complete pricing table, variant pricing, bulk rates\n"
            "- Manufacturer info: About pages, contact details, product catalogs\n\n"
            "DON'T USE:\n"
            "- As first step (start with research_product_tool - includes summaries)\n"
            "- For every research source (extract is costly - only high-value URLs)\n"
            "- When research answer sufficient\n"
            "- For low-relevance sources (<0.5 score rarely worth extracting)\n"
            "- Paywalled/protected content (API cannot access, returns error)\n\n"
            "CRITICAL:\n"
            "- url: Valid HTTP/HTTPS URL (typically from research_product_tool sources)\n"
            "- format ('markdown' or 'text', default 'markdown'): Markdown preserves structure (headers, lists, tables) - best for LLM analysis\n"
            "- Workflow: research first → identify high-relevance URLs (0.8+) → extract 1-2 most valuable → synthesize\n"
            "- Cost: ~$0.008/extraction, 1000/month free tier (shared with research), 1-2 per product typical\n"
            "- Error handling: Paywall/JavaScript/404 returns graceful error - try alternative URL or use research summary\n"
            "- Be selective: Only extract high-value sources, not every link\n\n"
            "EXAMPLES:\n"
            "# Deep-dive product page\n"
            "extract_web_content_tool(url='https://manufacturer.com/products/pet-jars-food-grade', format='markdown')\n"
            "Returns: Full specs, pricing table, certifications, contact info in structured markdown\n\n"
            "# Technical spec sheet\n"
            "extract_web_content_tool(url='https://compliance.example.com/hsn-classification-plastics')\n"
            "Returns: Complete HSN guide, code definitions, customs requirements\n\n"
            "RETURNS: Always a structured dict with success flag.\n"
            "- success=True: WebContentAnalysis fields (url, title, content, format, word_count, extracted_at, etc.)\n"
            "- success=False: {error, error_type, url, Agent Action: ...}"
        ),
        args_schema=ExtractWebContentInput,
    )


# =============================================================================
# Convenience exports (for backward compatibility with decorator pattern)
# =============================================================================

# These are created with default settings for direct import compatibility
# Specialists should prefer factory functions for proper dependency injection
from autifyme_agents.core.config import settings as default_settings  # noqa: E402

research_product_tool = create_research_product_tool(default_settings)
extract_web_content_tool = create_extract_web_content_tool(default_settings)
