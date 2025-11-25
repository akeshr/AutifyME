# Product Research & Analysis Capability

**Created:** November 10, 2025
**Status:** 🔄 Planning
**Related:** SPECIALIST_BUILD_UP_PLAN.md (Phase 3 - Product Architecture Specialist)
**Architecture Pattern:** Intelligence-First, Tool-Based Enhancement

---

## Executive Summary

**Problem:** Product Specialist creates catalog entries from user-provided data only. No external research to enrich product information, validate market positioning, or discover competitive insights.

**Solution:** Add web research tools (Tavily) to Product Architecture Specialist, enabling autonomous research for:
- Product specifications (materials, dimensions, certifications)
- Market pricing and competitive analysis
- Brand/manufacturer information
- Technical documentation and safety data sheets
- Customer reviews and quality signals

**Why Now:** Product Specialist is next in build-up sequence (Phase 3). Perfect timing to integrate research capability before first deployment.

**Approach:** Tool-based enhancement (not separate specialist) - maintains 2-level architecture, leverages specialist's domain expertise to guide research.

---

## Architectural Decision: Tool vs Specialist

### Options Analyzed

**Option A: Add Tools to Product Specialist** ✅ CHOSEN
- Product Specialist gets `research_product_tool` and `extract_web_content_tool`
- Specialist decides when/what to research (intelligence-first)
- Domain knowledge guides research strategy

**Option B: Dedicated Research Specialist**
- Separate specialist on cheaper model (Haiku)
- PM orchestrates handoffs
- **Rejected:** Breaks 2-level architecture, research needs product domain context anyway

**Option C: Research Tool (Agent-Wrapped)**
- Tool wraps internal Haiku agent
- **Rejected:** Over-engineering, doesn't leverage specialist intelligence

### Why Option A Wins

**Architecture Alignment:**
- **Intelligence-First:** Modern LLMs excel at autonomous research with proper context
- **2-Level:** PM → Specialists → Tools (research tools are cross-cutting)
- **Domain-Centric:** Product research requires product expertise (query formulation, relevance assessment, synthesis)

**Cost Reality:**
- Research isn't "fetch data" - requires domain judgment throughout
- Haiku without product context needs extensive back-and-forth (negates savings)
- Optimization: efficient prompting, caching, targeted queries (not model switching)

**Future Extensibility:**
- Customer Specialist needs customer research → same tools
- Inventory Specialist needs supplier research → same tools
- Deep research (patents, specs) → add specialized tools later

---

## Research Tool Selection: Tavily vs Alternatives

### Comparison Matrix

| Feature | Tavily | SerpAPI | Google Custom Search | Raw Scraping |
|---------|--------|---------|----------------------|--------------|
| **Cost** | $0.008/credit (1000 free/mo) | $50/mo (100 free) | $5/1000 (100/day free) | Free |
| **AI-Optimized** | ✅ Yes (multi-source summaries) | ❌ Raw SERP JSON | ❌ Raw HTML | ❌ Raw HTML |
| **LangChain Native** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Content Extraction** | ✅ Built-in | ❌ No | ❌ No | Custom |
| **Production Ready** | ✅ Yes | ✅ Yes | ⚠️ Quota limits | ❌ Fragile |
| **Multi-Source** | ✅ Yes | ❌ Single engine | ❌ Google only | N/A |
| **Maintenance** | Zero | Low | Medium | High |

### Decision: Tavily

**Why Tavily:**
1. **AI-Native:** Returns LLM-optimized summaries (not token-heavy raw HTML)
2. **Cost-Effective:** 6-10x cheaper than SerpAPI at scale, better free tier than Google
3. **Feature-Rich:** Search + Extract + Crawl (future: Map, Crawl) in one API
4. **Production-Ready:** Built for agents, 93.3% accuracy on SimpleQA benchmark
5. **Intelligence-Optimized:** Multi-source verification, confidence scoring, citation quality

**Why Not Alternatives:**
- **SerpAPI:** 10x more expensive, returns raw SERP data (requires LLM post-processing)
- **Google Custom Search:** Raw HTML (massive tokens), 100/day limit too restrictive, no extraction
- **Raw Scraping:** Violates ToS, CAPTCHA blocking, maintenance nightmare

---

## Implementation Design

### Phase 1: Core Research Tools (Initial)

#### Tool 1: `research_product_tool`

**Purpose:** Broad product research (specifications, market info, competitive analysis)

**Signature:**
```python
@tool
def research_product_tool(
    query: Annotated[str, Field(description="Natural language research query (e.g., 'PET jar specifications 500ml food grade India')")],
    max_results: Annotated[int, Field(default=5, description="Max search results (1-10, default 5)")],
    include_answer: Annotated[bool, Field(default=True, description="Include AI-generated answer summary")],
) -> dict[str, Any]:
    """Research product information using Tavily web search.

    Returns structured ProductResearchResult with:
    - AI-generated answer summary
    - Source citations with URLs
    - Confidence score
    - Key findings extracted
    """
```

**Output Schema:**
```python
class ProductResearchResult(BaseModel):
    """Structured research findings"""
    query: str  # Original query
    answer: str | None  # AI-generated summary (if include_answer=True)
    sources: list[ResearchSource]  # Citations with URLs, relevance scores
    key_findings: list[str]  # Extracted bullet points
    confidence: float  # Research quality score (0.0-1.0)
    timestamp: str  # ISO 8601 timestamp
```

#### Tool 2: `extract_web_content_tool`

**Purpose:** Deep content extraction from specific URLs (product pages, spec sheets, documentation)

**Signature:**
```python
@tool
def extract_web_content_tool(
    url: Annotated[str, Field(description="URL to extract content from")],
    format: Annotated[Literal["markdown", "text"], Field(default="markdown", description="Output format")],
) -> dict[str, Any]:
    """Extract and parse web page content for LLM analysis.

    Returns structured WebContentAnalysis with:
    - Extracted content (markdown/text)
    - Metadata (title, description, publish date)
    - Structured data (if available)
    """
```

**Output Schema:**
```python
class WebContentAnalysis(BaseModel):
    """Parsed web content for LLM consumption"""
    url: str
    title: str | None
    description: str | None
    content: str  # Markdown or text
    structured_data: dict[str, Any] | None  # JSON-LD, microdata
    publish_date: str | None
    author: str | None
    timestamp: str
```

### Phase 2: Advanced Research (Future)

**Planned Tools:**
1. `extract_pdf_content_tool`: Technical specs, catalogs, certifications (PyPDF2/pdfplumber)
2. `reverse_image_search_tool`: Product identification via image (Google Vision API)
3. `extract_structured_data_tool`: Pricing tables, competitor analysis (custom parsing)

---

## Integration Pattern

### Tool Implementation (Follows Existing Pattern)

**Reference:** `image_analysis_tool.py` (deterministic API wrapper with structured output)

**Pattern:**
```python
# agents/src/autifyme_agents/tools/research_tools.py

from langchain.tools import tool
from pydantic import Field
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)
from autifyme_agents.schemas.agent_outputs import ProductResearchResult

@tool
def research_product_tool(
    query: Annotated[str, Field(...)],
    max_results: Annotated[int, Field(default=5)],
    include_answer: Annotated[bool, Field(default=True)],
) -> dict[str, Any]:
    """Research product information using Tavily..."""
    try:
        # Call Tavily API via langchain-tavily
        from langchain_tavily import TavilySearch

        tavily = TavilySearch(api_key=settings.TAVILY_API_KEY)
        results = tavily.search(
            query=query,
            max_results=max_results,
            include_answer=include_answer,
        )

        # Convert to structured output
        research_result = ProductResearchResult(
            query=query,
            answer=results.get("answer"),
            sources=[...],
            key_findings=[...],
            confidence=_calculate_confidence(results),
            timestamp=datetime.utcnow().isoformat(),
        )

        return build_success_response(research_result.model_dump())

    except Exception as exc:
        return build_agent_error_response(
            exception=exc,
            context={"query": query},
            fallback_type="RESEARCH_ERROR",
            fallback_action="Continue without research data, inform user",
        )
```

### Product Specialist Integration

**Tool Registration:**
```python
# agents/src/autifyme_agents/specialists/product_architecture_specialist.py

from autifyme_agents.tools.research_tools import (
    research_product_tool,
    extract_web_content_tool,
)

tools = [
    search_product_families_tool,
    universal_crud_tool,
    research_product_tool,        # NEW
    extract_web_content_tool,     # NEW
]
```

**Prompt Guidance (Added to Specialist Prompt):**
```xml
<research_capability>
You have web research tools to enrich product data beyond user-provided information.

WHEN TO RESEARCH:
- User provides minimal data (just product name/image)
- Validating specifications (material safety, certifications)
- Competitive analysis (market pricing, alternatives)
- Brand/manufacturer verification
- Technical documentation needed

RESEARCH STRATEGY:
1. Formulate targeted queries (use domain knowledge)
2. Assess source quality (prioritize manufacturer sites, industry databases)
3. Synthesize findings with user data
4. Flag confidence gaps (inform user if research inconclusive)

COST AWARENESS:
- Research efficiently (targeted queries, not exploratory)
- Cache results for similar products
- Don't over-research obvious cases
</research_capability>
```

---

## Cost Optimization Strategy

### Tavily Pricing
- **Free Tier:** 1000 credits/month (1 search = ~1 credit)
- **Paid:** $30/month for 4000 credits ($0.0075/credit)
- **Add-On:** $100 one-time for 8000 credits (no expiration)

### Expected Usage (Conservative Estimate)
- **Product Onboarding:** 2-3 searches/product (specs, pricing, brand)
- **Monthly Products:** ~50 products
- **Monthly Searches:** ~150 searches
- **Cost:** Well within free tier (1000/month)

### Optimization Tactics

**1. Result Caching (PostgreSQL)**
```sql
CREATE TABLE research_cache (
    query_hash TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '24 hours'
);
```
- 24hr TTL for research results
- Hash-based deduplication (similar queries share cache)
- Reduces duplicate API calls

**2. Prompt Engineering**
- Teach specialist to formulate precise queries (not exploratory)
- "PET jar 500ml food grade specifications India" (good)
- "PET jars" (bad - too broad)

**3. LangSmith Monitoring**
- Track cost per product workflow
- Identify over-research patterns
- Tune specialist prompts based on usage

**4. Graceful Degradation**
- Continue workflow if research fails (don't block)
- Inform user of missing research data
- Cache partial results

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/tools/test_research_tools.py

def test_research_product_tool_success():
    """Test successful product research"""
    result = research_product_tool(
        query="PET jar 500ml food grade India",
        max_results=5,
        include_answer=True,
    )
    assert result["success"] is True
    assert "answer" in result
    assert len(result["sources"]) <= 5

def test_research_product_tool_api_failure():
    """Test graceful API failure handling"""
    # Mock Tavily API failure
    result = research_product_tool(query="test")
    assert result["success"] is False
    assert result["agent_action"] == "Continue without research data, inform user"
```

### Integration Tests (Intelligent Monitoring Framework)
```python
# tests/cli/test_product_research_workflow.py

async def test_product_onboarding_with_research():
    """Test full workflow with research enhancement"""
    scenario = {
        "user_message": "Catalog this product: PET jar, 500ml",
        "expected_research": True,
        "expected_specialist": "product_architecture",
    }

    result = await intelligent_test(scenario)
    assert "research_product_tool" in result.tools_used
    assert result.product_draft.specifications  # Enriched via research
```

### Cost Monitoring
- Track Tavily API usage via LangSmith custom metadata
- Alert if monthly usage exceeds 800 credits (80% of free tier)
- Monthly review of research ROI (quality improvement vs cost)

---

## Environment Configuration

### API Key Setup

**Step 1: Get Tavily API Key**
1. Sign up at https://app.tavily.com/sign-up
2. Free tier: 1000 credits/month (no credit card)
3. Copy API key from dashboard

**Step 2: Add to .env File**
```bash
# In /home/user/AutifyME/.env (root directory)
# Add this line:
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Step 3: Update Settings**
```python
# agents/src/autifyme_agents/core/config.py

class Settings(BaseSettings):
    # ... existing settings ...

    # Research API Keys
    TAVILY_API_KEY: str = Field(
        ...,
        description="Tavily API key for web research (https://app.tavily.com)"
    )

    class Config:
        env_file = ".env"
```

**Step 4: Verify Setup (REPL)**
```bash
uv run python -c "
from dotenv import load_dotenv
load_dotenv('.env')
import os
print('Tavily API Key:', os.getenv('TAVILY_API_KEY')[:10] + '...')
"
```

### Deployment (Vercel/Railway)

**Add to deployment environment:**
```bash
# Vercel
vercel env add TAVILY_API_KEY

# Railway
# Add via Railway dashboard: Variables → TAVILY_API_KEY
```

---

## Dependencies

### Add to pyproject.toml
```toml
[project]
dependencies = [
    # ... existing dependencies ...

    # Web Research (Tavily)
    "langchain-tavily>=0.2.13",  # Latest stable (Nov 2025)
]
```

### Install
```bash
uv pip install -e ".[dev]"
```

---

## Success Metrics

### Quality Metrics
- **Research Accuracy:** 90%+ relevance of research findings to product context
- **Source Quality:** 80%+ citations from manufacturer/industry authoritative sources
- **Enrichment Rate:** 70%+ of products have ≥1 specification enriched via research

### Performance Metrics
- **Latency:** Research adds <2s to product analysis workflow
- **Cache Hit Rate:** 30%+ queries served from cache (after 1 month)
- **Cost:** Stay within free tier (800/1000 credits/month)

### User Impact Metrics
- **Catalog Completeness:** 40% increase in specification fields populated
- **User Corrections:** 30% reduction in user-reported spec errors
- **Approval Speed:** 20% faster approval (less back-and-forth for missing data)

---

## Rollout Plan

### Phase 1: Tool Implementation (2-3 hours)
- [ ] Add `langchain-tavily` dependency
- [ ] Implement `research_product_tool` (following image_analysis_tool pattern)
- [ ] Implement `extract_web_content_tool`
- [ ] Add schemas: ProductResearchResult, WebContentAnalysis
- [ ] Unit tests (success, failure, edge cases)

### Phase 2: Specialist Integration (1-2 hours)
- [ ] Register tools with Product Architecture Specialist
- [ ] Update specialist prompt (research guidance)
- [ ] Integration test with intelligent monitoring framework
- [ ] Verify LangSmith traces show research usage

### Phase 3: Cost Optimization (1 hour)
- [ ] Implement research_cache table in PostgreSQL
- [ ] Add caching logic to tools
- [ ] Set up LangSmith cost tracking dashboard

### Phase 4: Production Validation (2-3 hours)
- [ ] Test with real product onboarding scenarios
- [ ] Validate research quality (source authority, relevance)
- [ ] Monitor cost (Tavily dashboard + LangSmith)
- [ ] Tune specialist prompts based on usage patterns

**Total Estimate:** 6-9 hours

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **API Cost Overrun** | High | Cache results, monitor usage, set alerts at 80% free tier |
| **Research Quality Issues** | Medium | Source filtering, confidence scoring, user feedback loop |
| **API Latency** | Low | Parallel tool calls, timeout handling, cache warming |
| **API Outage** | Low | Graceful degradation, continue workflow without research |
| **Over-Research (Waste)** | Medium | Prompt engineering, cost monitoring, specialist tuning |

---

## Future Enhancements

### Phase 2: Specialized Research (Q2 2025)
- **PDF Extraction:** Technical specs, safety data sheets, certifications
- **Reverse Image Search:** Product identification from images
- **Structured Data Extraction:** Pricing tables, competitive analysis

### Phase 3: Cross-Specialist Research (Q3 2025)
- **Customer Research:** Market analysis, customer reviews, sentiment
- **Supplier Research:** Vendor discovery, reliability, pricing
- **Inventory Research:** Demand forecasting, market trends

### Phase 4: Research Intelligence (Q4 2025)
- **Research Summarization:** Multi-source synthesis for PM context
- **Confidence Scoring:** ML-based research quality assessment
- **Proactive Research:** Agent initiates research based on gaps

---

## References

**Architecture Docs:**
- SPECIALIST_BUILD_UP_PLAN.md (Phase 3 tracking)
- PROMPT_ENGINEERING_STANDARDS.md (specialist prompt guidance)
- TOOL_DEVELOPMENT_GUIDE.md (tool implementation pattern)

**Technical Docs:**
- Tavily Docs: https://docs.tavily.com
- LangChain Tavily Integration: https://python.langchain.com/docs/integrations/tools/tavily_search/
- UV REPL Best Practices: docs/architecture/tech/UV_REPL_BEST_PRACTICES.md

**Related Issues:**
- Product Specialist Build-Up (Phase 3)
- Tool-Based Enhancement Pattern
- Cost Optimization Strategy
