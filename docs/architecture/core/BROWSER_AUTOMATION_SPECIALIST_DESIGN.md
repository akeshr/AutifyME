# Browser Automation Specialist - Computer Use Integration Design

**Status:** 🚧 Design Phase
**Date:** October 30, 2025
**Owner:** Architecture
**Model:** gemini-2.5-computer-use-preview-10-2025

---

## Executive Summary

Design for Browser Automation Specialist that integrates Google's Gemini 2.5 Computer Use model into AutifyME's hierarchical agent architecture. This specialist brings visual-based browser automation as a reusable domain capability, enabling any workflow to extract web data, fill forms, handle CAPTCHAs, and interact with web UIs through screenshot-based reasoning.

**Key Innovation:** First specialist to use **visual reasoning** instead of DOM/API parsing. The Computer Use model "sees" web pages like humans do, enabling automation of any website without custom scrapers.

**Architectural Fit:**
```
PM Agent (Orchestrator)
  ↓
Domain Specialists (Product, Marketing, Inventory)
  ↓
Browser Automation Specialist ← NEW (Computer Use powered)
  ↓
Computer Use Tool → Playwright Executor
```

---

## 1. Problem Statement & Vision

### Current Gap
AutifyME specialists need web data but have no way to:
- Extract product info from competitor websites
- Scrape pricing data dynamically
- Fill forms on vendor portals
- Handle CAPTCHAs autonomously (with approval)
- Interact with JavaScript-heavy sites
- Automate repetitive browser tasks

### Existing Approaches (Inadequate)
1. **Static scrapers** - Break when sites change
2. **DOM selectors** - Brittle, site-specific
3. **API-only** - Many sites don't have APIs
4. **Manual data entry** - Not scalable

### Vision: Visual Browser Automation
Computer Use model brings human-like interaction:
- **See** pages via screenshots (visual analysis)
- **Understand** layout and elements (spatial reasoning)
- **Act** through clicks/typing (function generation)
- **Adapt** when sites change (no brittle selectors)
- **Solve** CAPTCHAs (visual pattern recognition)

### Use Cases Enabled
**Product Domain:**
- Extract competitor product details from URLs
- Scrape pricing for competitive analysis
- Monitor stock availability across retailers

**Marketing Domain:**
- Research competitor ad copy from landing pages
- Extract social media metrics visually
- Analyze competitor website content

**Inventory Domain:**
- Check supplier stock via vendor portals
- Automate reorder form submissions
- Monitor shipping status from carrier sites

**Cross-Domain:**
- Handle authentication flows
- Navigate multi-step forms
- Download reports from dashboards
- Verify data across platforms

---

## 2. Domain Analysis

### Domain Definition
**Domain:** Browser-Based Web Interaction & Data Extraction

**Core Capabilities:**
1. Navigate to URLs
2. Extract structured data from visual elements
3. Fill and submit forms
4. Handle authentication (with HITL)
5. Solve CAPTCHAs (with approval)
6. Scroll and paginate
7. Wait for dynamic content
8. Take targeted screenshots

### Domain Boundaries

**In Scope:**
- Any task requiring browser interaction
- Visual analysis of web content
- Form automation
- Dynamic content handling
- Screenshot-based data extraction

**Out of Scope:**
- Data interpretation (delegates back to requesting specialist)
- Business logic (requesting specialist decides what to do with data)
- Storage (requesting specialist handles persistence)
- Rate limiting strategy (handled by middleware)

### Reusability Matrix

| Requesting Specialist | Use Case | Data Returned |
|----------------------|----------|---------------|
| Product Architecture | Extract competitor product info | Product details (title, price, specs) |
| Market Intelligence | Scrape pricing data | Pricing table |
| Marketing Content | Research competitor copy | Page text + screenshots |
| Inventory | Check supplier stock | Availability status |
| Taxonomy | Extract category structure | Category hierarchy |

---

## 3. Architecture Design

### 3.1 Hierarchical Position

```
PM Agent (gpt-4o-mini-2025-04-14)
  ↓ delegates "extract product from URL"
Product Architecture Specialist (gpt-4o-mini)
  ↓ delegates "get product details from https://..."
Browser Automation Specialist (gemini-2.5-computer-use) ← NEW
  ↓ uses tools
  ├── navigate_and_analyze (screenshot → model analysis)
  ├── extract_structured_data (visual → structured output)
  └── handle_interaction (click, type, scroll)
    ↓ executes via
  Playwright Executor (Chromium browser)
```

### 3.2 Specialist Pattern

**Architecture:** SubAgent dict format (DeepAgents pattern)

**Specialist Factory:**
```python
def create_browser_automation_specialist() -> dict[str, Any]:
    """
    Create Browser Automation Specialist with Computer Use.

    Returns SubAgent spec with:
    - name: "browser_automation_specialist"
    - description: delegation criteria
    - tools: navigation, extraction, interaction tools
    - system_prompt: visual reasoning instructions
    - response_format: BrowserResult
    """
```

**Response Format:** Pydantic model with structured data + metadata

### 3.3 Intelligence-First Design

Following Intelligence-First principle:

**Don't specify:**
- ❌ "Click element at (x, y), then wait 2 seconds, then extract div.price"
- ❌ "Use CSS selector .product-title to find name"
- ❌ "First scroll down 500px, then click third button"

**Do specify:**
- ✅ Goal: "Extract product name, price, and availability"
- ✅ URL: "https://example.com/product/123"
- ✅ Expected schema: `ProductInfo(name, price, availability)`
- ✅ Constraints: "Don't submit any forms, read-only extraction"

**Let the specialist reason:**
- Navigate and take screenshot
- Analyze visual layout
- Identify relevant elements (by visual appearance, not selectors)
- Generate actions (click_at, scroll, extract)
- Validate data matches expected schema
- Return structured output or report failure

---

## 4. Component Specifications

### 4.1 Specialist Module

**File:** `agents/src/autifyme_agents/specialists/browser_automation_specialist.py`

**Key Functions:**
```python
def create_browser_automation_specialist(
    auto_approve_captcha: bool = False,
    headless: bool = True,
    viewport_size: tuple[int, int] = (1440, 900),
) -> dict[str, Any]:
    """Factory for Browser Automation Specialist."""

def get_browser_automation_specialist(...) -> dict[str, Any]:
    """Convenience getter with defaults."""
```

**Configuration:**
- `auto_approve_captcha`: Auto-approve CAPTCHA solving (default: False, requires HITL)
- `headless`: Browser visibility (False for debugging)
- `viewport_size`: Browser viewport dimensions
- `timeout`: Navigation timeout (default: 30s)

### 4.2 Tools Design

#### Tool 1: navigate_and_analyze
```python
async def navigate_and_analyze(
    url: str,
    goal: str,
    wait_for: str | None = None,
) -> dict[str, Any]:
    """
    Navigate to URL, capture screenshot, analyze with Computer Use model.

    Args:
        url: Target URL
        goal: What to look for (e.g., "locate product price")
        wait_for: Optional element description to wait for

    Returns:
        {
            "screenshot_base64": str,
            "analysis": str,  # Model's description of page
            "suggested_actions": list[dict],  # Model's action recommendations
            "page_state": {"url": str, "title": str}
        }
    """
```

#### Tool 2: extract_structured_data
```python
async def extract_structured_data(
    goal: str,
    expected_schema: type[BaseModel],
    current_screenshot: str | None = None,
) -> dict[str, Any]:
    """
    Extract structured data from current page using Computer Use visual analysis.

    Args:
        goal: What data to extract (e.g., "product name and price")
        expected_schema: Pydantic model defining structure
        current_screenshot: Optional screenshot (uses current page if None)

    Returns:
        {
            "data": dict,  # Extracted data matching schema
            "confidence": float,  # 0-1 confidence score
            "screenshot_b64": str,  # Screenshot used for extraction
            "extraction_log": list[str]  # Step-by-step extraction process
        }
    """
```

#### Tool 3: execute_browser_action
```python
async def execute_browser_action(
    action_type: Literal["click_at", "type_text_at", "scroll_document", "navigate"],
    args: dict[str, Any],
    requires_approval: bool = False,
) -> dict[str, Any]:
    """
    Execute single browser action via Computer Use model.

    Args:
        action_type: Action to perform
        args: Action-specific arguments
        requires_approval: If True, request HITL approval

    Returns:
        {
            "success": bool,
            "action_executed": dict,
            "new_screenshot_b64": str,  # Page after action
            "error": str | None
        }
    """
```

#### Tool 4: handle_captcha
```python
async def handle_captcha(
    captcha_type: Literal["checkbox", "image_selection", "text"],
    auto_approve: bool = False,
) -> dict[str, Any]:
    """
    Detect and solve CAPTCHA using Computer Use visual analysis.

    Args:
        captcha_type: Type of CAPTCHA detected
        auto_approve: Skip user confirmation (use with caution)

    Returns:
        {
            "solved": bool,
            "method": str,  # How it was solved
            "attempts": int,
            "screenshot_after": str
        }
    """
```

### 4.3 Tool Implementation Strategy

**Single Computer Use Client (Singleton Pattern):**
```python
class ComputerUseClient:
    """Singleton client for Computer Use model + Playwright executor."""

    _instance: ComputerUseClient | None = None

    def __init__(self):
        self.model_client: genai.Client
        self.playwright_executor: PlaywrightExecutor
        self.action_history: list[ComputerAction] = []

    @classmethod
    def get_instance(cls) -> ComputerUseClient:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def analyze_screenshot(
        self, screenshot: bytes, goal: str
    ) -> types.GenerateContentResponse:
        """Send screenshot + goal to Computer Use model."""

    async def execute_action(
        self, action: ComputerAction
    ) -> BrowserState:
        """Execute action via Playwright, return new state."""
```

---

## 5. Schema Design

**File:** `agents/src/autifyme_agents/schemas/browser_automation.py`

```python
from pydantic import BaseModel, Field
from typing import Literal, Any

class BrowserTask(BaseModel):
    """Input: Task for Browser Automation Specialist."""

    goal: str = Field(
        description="High-level goal (e.g., 'Extract product price and availability')"
    )
    url: str = Field(description="Target URL")
    expected_schema: type[BaseModel] | None = Field(
        default=None,
        description="Pydantic model for extracted data structure"
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Constraints (e.g., 'read-only', 'no form submissions')"
    )
    max_interactions: int = Field(
        default=10,
        description="Max browser actions before returning"
    )

class ActionLog(BaseModel):
    """Record of single browser action."""

    action_type: str
    args: dict[str, Any]
    timestamp: str
    screenshot_before: str | None
    screenshot_after: str | None
    success: bool
    reasoning: str

class BrowserResult(BaseModel):
    """Output: Result from Browser Automation Specialist."""

    success: bool
    data: dict[str, Any] | None = Field(
        description="Extracted data (structure matches expected_schema)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in extraction (0-1)"
    )
    action_log: list[ActionLog] = Field(
        description="Complete history of browser actions"
    )
    final_screenshot_b64: str | None
    error: str | None
    captcha_encountered: bool = False
    captcha_solved: bool = False

class VisualElement(BaseModel):
    """Detected element from visual analysis."""

    description: str = Field(description="What the element is")
    coordinates: tuple[int, int] = Field(description="Normalized (x, y) on 1000x1000 grid")
    element_type: Literal["button", "input", "link", "text", "image", "other"]
    confidence: float
```

---

## 6. Prompt Strategy

**File:** `agents/src/autifyme_agents/prompts/specialists/browser_automation_specialist.prompt`

### Prompt Structure (XML)

```xml
<role>
You are the Browser Automation Specialist in the AutifyME agentic system.
Your domain: Visual-based web interaction and data extraction using Computer Use.
</role>

<capabilities>
- Navigate to URLs and analyze pages visually (screenshot-based reasoning)
- Extract structured data from web pages without DOM selectors
- Fill forms and interact with web UIs through visual understanding
- Handle CAPTCHAs with visual pattern recognition (requires approval)
- Adapt to site changes automatically (no brittle selectors)
</capabilities>

<decision_framework>
Given a browser automation task:

1. Analyze the Goal
   - What data needs extraction?
   - What interactions are required?
   - What is the expected output format?

2. Plan the Approach
   - Navigate to target URL
   - Capture screenshot for visual analysis
   - Identify relevant elements visually
   - Plan sequence of actions (click, scroll, extract)

3. Execute with Adaptation
   - Use tools to interact (navigate_and_analyze, extract_structured_data)
   - Analyze each screenshot to determine next action
   - Adapt if page layout differs from expectation
   - Validate extracted data matches expected schema

4. Handle Edge Cases
   - CAPTCHAs: Detect visually, request approval, solve
   - Dynamic content: Wait for loading indicators to disappear
   - Pop-ups: Dismiss automatically if blocking goal
   - Missing data: Report what was found + what's missing

5. Return Structured Result
   - Extracted data in expected schema format
   - Confidence score based on data quality
   - Complete action log for transparency
   - Final screenshot for verification
</decision_framework>

<tools_usage>
- navigate_and_analyze: Navigate + capture screenshot + get visual analysis
- extract_structured_data: Extract data matching Pydantic schema from screenshot
- execute_browser_action: Perform single action (click, type, scroll)
- handle_captcha: Solve CAPTCHA with user approval
</tools_usage>

<safety_rules>
CRITICAL Safety Requirements:

1. CAPTCHA Solving
   - Always request user approval unless auto_approve_captcha=True
   - Explain why CAPTCHA is being solved
   - Log CAPTCHA attempts in action_log

2. Form Submissions
   - Never submit forms containing sensitive data without HITL approval
   - Financial transactions require explicit user confirmation
   - Authentication flows need approval

3. Rate Limiting
   - Respect rate limits (wait between actions if needed)
   - Don't hammer websites with rapid requests
   - Abort if rate-limited (don't retry endlessly)

4. Data Privacy
   - Don't extract or log sensitive data (passwords, credit cards)
   - Redact sensitive fields in screenshots
   - Follow robots.txt (ethical scraping)
</safety_rules>

<error_handling>
When things go wrong:

- Page Load Failure: Return error with URL + timeout details
- Element Not Found: Return partial data + missing fields list
- CAPTCHA Blocks: Request approval, solve, retry (max 3 attempts)
- Timeout: Return what was extracted before timeout
- Rate Limited: Return error with retry-after suggestion

Always provide actionable error messages to requesting specialist.
</error_handling>

<output_format>
Return BrowserResult with:
- success: bool (True if goal achieved)
- data: Extracted data matching expected_schema
- confidence: Float 0-1 (data quality assessment)
- action_log: Complete action history
- final_screenshot_b64: Final page state
- error: Detailed error if success=False
</output_format>

<examples>
[Canonical examples of successful extractions, CAPTCHA handling, error cases]
</examples>
```

### Prompt Altitude
**Level:** Specialist (Low-Medium Altitude)
- Not too low: No code, no exact selectors
- Not too high: Clear decision framework, specific tools

**Reasoning Enabled:**
- Specialist decides action sequence
- Adapts to unexpected page layouts
- Validates data quality autonomously

---

## 7. Integration Patterns

### 7.1 Pattern: Data Extraction

```python
# Product Architecture Specialist delegates to Browser Automation Specialist
from autifyme_agents.specialists.browser_automation_specialist import (
    get_browser_automation_specialist,
)
from autifyme_agents.schemas.browser_automation import BrowserTask, BrowserResult
from autifyme_agents.schemas.product import ProductInfo

# Create task
task = BrowserTask(
    goal="Extract product name, price, and availability status",
    url="https://competitor.com/product/wireless-headphones",
    expected_schema=ProductInfo,  # Pydantic model
    constraints=["read-only", "no form submissions"],
    max_interactions=5
)

# Get specialist
browser_specialist = get_browser_automation_specialist()

# Execute (specialist uses Computer Use tools internally)
result: BrowserResult = await browser_specialist.execute(task)

if result.success:
    product_info = ProductInfo(**result.data)
    # Use extracted data...
else:
    # Handle extraction failure...
    logger.error(f"Extraction failed: {result.error}")
```

### 7.2 Pattern: Form Automation (with HITL)

```python
# Inventory Specialist delegates form filling
task = BrowserTask(
    goal="Fill reorder form with: product=ABC123, quantity=50, ship to warehouse",
    url="https://supplier-portal.com/reorder",
    constraints=["requires_approval_before_submit"],
    max_interactions=15
)

result = await browser_specialist.execute(task)

# Specialist will request HITL approval before form submission
# Action log shows each field filled + final confirmation request
```

### 7.3 Pattern: CAPTCHA Handling

```python
# Marketing specialist encounters CAPTCHA during competitor research
task = BrowserTask(
    goal="Extract pricing table from competitor landing page",
    url="https://competitor.com/pricing",
    expected_schema=PricingTable,
    max_interactions=20
)

result = await browser_specialist.execute(task)

# If CAPTCHA encountered:
if result.captcha_encountered:
    if result.captcha_solved:
        logger.info("CAPTCHA solved, data extracted successfully")
    else:
        logger.warning("CAPTCHA blocked extraction, user approval required")
        # Retry with auto_approve=True after user consent
```

---

## 8. Error Handling & Safety

### 8.1 Error Categories

| Error Type | Handling Strategy | Retry | Return |
|------------|-------------------|-------|--------|
| Page load timeout | Return error immediately | No | BrowserResult(success=False, error="Timeout") |
| Element not found | Continue with partial data | No | BrowserResult(success=True, data=partial, confidence=0.6) |
| CAPTCHA without approval | Pause, request HITL | Yes (after approval) | BrowserResult(success=False, captcha_encountered=True) |
| Rate limited | Return error with retry-after | No | BrowserResult(success=False, error="Rate limited: retry in 60s") |
| Network failure | Retry once | Yes (1 attempt) | Error after retry fails |

### 8.2 Safety Mechanisms

**Built-in Safety (Computer Use Model):**
1. Flags sensitive actions (`safety_decision: require_confirmation`)
2. Explains why approval needed
3. Waits for explicit approval

**Specialist-Level Safety:**
1. CAPTCHA approval required by default
2. Form submission approval for sensitive data
3. Authentication flows require HITL
4. Financial transactions blocked without explicit consent

**Action Logging:**
Every action logged with:
- Timestamp
- Action type + args
- Screenshot before/after
- Success/failure
- Reasoning

**Observability:** All logs sent to LangSmith with screenshots as metadata

---

## 9. Observability & Debugging

### 9.1 LangSmith Integration

**Trace Structure:**
```
Run: Browser Automation Task
├── Tool: navigate_and_analyze
│   ├── Input: {url, goal}
│   ├── Screenshot (metadata)
│   └── Output: {analysis, suggested_actions}
├── Tool: extract_structured_data
│   ├── Input: {goal, schema}
│   ├── Screenshot (metadata)
│   └── Output: {data, confidence}
├── Tool: execute_browser_action (if needed)
│   ├── Input: {action_type, args}
│   ├── Screenshot before (metadata)
│   ├── Screenshot after (metadata)
│   └── Output: {success}
└── Final Result: BrowserResult
```

**Screenshot Management:**
- Store in LangSmith as base64 metadata
- Limit resolution for token efficiency (1440x900)
- Redact sensitive info before logging

### 9.2 Debugging Tools

**CLI Tool: `test_browser_automation.py`**
```python
# Interactive testing with visual feedback
python test_browser_automation.py \
    --url "https://example.com" \
    --goal "extract product price" \
    --headless false \
    --debug true
```

**Debug Mode Features:**
- Browser stays open after task
- Action-by-action console output
- Screenshots saved to local directory
- Detailed Computer Use model responses

---

## 10. Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] Create `browser_automation_specialist.py` with factory function
- [ ] Create `computer_use_tool.py` with ComputerUseClient
- [ ] Create `browser_automation.py` schemas (BrowserTask, BrowserResult)
- [ ] Create specialist prompt following standards
- [ ] Update `specialists/__init__.py` to export new specialist

### Phase 2: Tool Implementation
- [ ] Implement `navigate_and_analyze` tool
- [ ] Implement `extract_structured_data` tool
- [ ] Implement `execute_browser_action` tool
- [ ] Implement `handle_captcha` tool with HITL
- [ ] Add tool error handling and retries

### Phase 3: Integration
- [ ] Create example: Product price extraction
- [ ] Create example: Form automation with HITL
- [ ] Create example: CAPTCHA handling
- [ ] Update Product Architecture Specialist to delegate extraction tasks
- [ ] Add LangSmith tracing with screenshot metadata

### Phase 4: Testing
- [ ] Unit tests: Tool functions
- [ ] Integration tests: Specialist with mock Computer Use
- [ ] E2E tests: Real browser automation scenarios
- [ ] CAPTCHA solving test with auto-approve
- [ ] Performance test: Multiple concurrent tasks

### Phase 5: Documentation
- [ ] Update `docs/architecture/README.md` with new specialist
- [ ] Create usage guide with examples
- [ ] Document safety considerations
- [ ] Add troubleshooting section

---

## 11. Open Questions & Decisions Needed

### Q1: Auto-Approve CAPTCHA Policy
**Options:**
A. Default to manual approval, opt-in auto-approve
B. Auto-approve by default, opt-out for sensitive flows
C. Per-workflow configuration

**Recommendation:** Option A (manual by default) for safety

**Decision:** _To be discussed_

---

### Q2: Screenshot Storage Strategy
**Options:**
A. Store all screenshots in LangSmith (high token cost)
B. Store only key screenshots (before/after major actions)
C. Store locally + S3 reference in LangSmith

**Recommendation:** Option B (key screenshots only)

**Decision:** _To be discussed_

---

### Q3: Rate Limiting Strategy
**Options:**
A. Fixed delay between actions (e.g., 1 second)
B. Adaptive delay based on site response
C. No built-in delay (rely on middleware)

**Recommendation:** Option B (adaptive) + middleware override

**Decision:** _To be discussed_

---

### Q4: Extension vs Core
**Options:**
A. Keep specialist in core, import Computer Use extension
B. Move specialist to extension (requires extension to use)
C. Hybrid: Lightweight specialist in core, delegates to extension

**Recommendation:** Option A (specialist in core, graceful degradation if extension missing)

**Decision:** _To be discussed_

---

## 12. Success Metrics

**Functional Metrics:**
- Extraction accuracy: >90% for common sites
- CAPTCHA solve rate: >85% (aligned with model benchmarks)
- Task completion rate: >80% end-to-end

**Performance Metrics:**
- Average task time: <30 seconds for simple extraction
- Screenshot processing: <3 seconds per image
- Action execution: <1 second per action

**Safety Metrics:**
- HITL approval rate: 100% for sensitive actions
- Unauthorized form submissions: 0
- Rate limit violations: <1% of tasks

---

## 13. References

**Internal Docs:**
- [CLAUDE.md](../../CLAUDE.md) - Architectural principles
- [PROMPT_ENGINEERING_STANDARDS.md](../tech/PROMPT_ENGINEERING_STANDARDS.md) - Prompt design
- [GOOGLE_AI_MULTIMODAL_INTEGRATION.md](../tech/GOOGLE_AI_MULTIMODAL_INTEGRATION.md) - Computer Use infrastructure
- [GOOGLE_COMPUTER_USE_GUIDE.md](../tech/GOOGLE_COMPUTER_USE_GUIDE.md) - Computer Use API details

**External References:**
- [Gemini Computer Use API Docs](https://ai.google.dev/gemini-api/docs/computer-use)
- [Gemini 2.5 Computer Use Blog](https://blog.google/technology/google-deepmind/gemini-computer-use-model/)
- [LangChain Agent Patterns](https://python.langchain.com/docs/concepts/agents/)
- [Playwright Documentation](https://playwright.dev/python/)

---

## 14. Next Steps

1. **Review this design** with architecture team
2. **Discuss open questions** and make decisions
3. **Create implementation plan** with timeline
4. **Implement Phase 1** (core infrastructure)
5. **Test with real scenario** (product price extraction)
6. **Iterate based on feedback**

---

**Design Status:** Ready for Review
**Estimated Implementation:** 3-5 days
**Complexity:** Medium (leverages existing patterns + new Computer Use capability)
