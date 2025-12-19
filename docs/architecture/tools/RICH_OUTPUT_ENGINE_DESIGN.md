# Rich Output Engine - Design Specification

**Status:** Draft - Ready for Review
**Created:** December 19, 2025
**Priority:** HIGH - Enhances agent output capabilities
**Related:** [IMAGE_STUDIO_TOOL.md](./IMAGE_STUDIO_TOOL.md), [UNIVERSAL_DATA_ENGINE_DESIGN.md](../core/UNIVERSAL_DATA_ENGINE_DESIGN.md)

---

## Executive Summary

Transform how AutifyME agents present complex data to users. Instead of forcing structured data into text messages (which hit character limits, lose hierarchy, and overwhelm users), agents autonomously decide when visual output serves better and generate rich, client-branded HTML pages on-demand.

**Core Principle:** Give agents the CAPABILITY to render rich outputs; let them DECIDE when to use it based on context. Trust agent intelligence, not rigid rules.

**Key Insight:** Modern LLMs excel at HTML/CSS generation. No templates needed - the rendering LLM analyzes data structure and company context to generate appropriate, branded layouts dynamically.

**Platform Architecture:** AutifyME is the platform serving client companies. Rich outputs are branded for the CLIENT (e.g., "Pavisha Packaging"), not AutifyME. Company context flows through the same middleware that powers PM.

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Vision](#vision)
- [Architecture](#architecture)
- [Company Context Integration](#company-context-integration)
- [Agent Protocol](#agent-protocol)
- [Tool Specification](#tool-specification)
- [HTML Generator LLM](#html-generator-llm)
- [Integration Points](#integration-points)
- [Security Considerations](#security-considerations)
- [Retention Policy](#retention-policy)
- [Edge Cases](#edge-cases)
- [Testing Strategy](#testing-strategy)
- [Known Limitations](#known-limitations)
- [Implementation Phases](#implementation-phases)

---

## Problem Statement

### Current Pain Points

**1. Text Limitations**

```text
User: "Create the new product line with 3 models and variants"

Current PM Response:
"Done! Created product line with:
- 3 products
- 12 variants total
- Price range: $499-$1299"
```

**What's Missing:**

- User cannot VERIFY what was created
- No visibility into details per item
- No visual hierarchy
- Character limits prevent sending complete data

**2. Verification Gap**

- Users approve changes they cannot fully inspect
- Errors discovered post-approval require costly rollbacks
- Complex data reduced to lossy summaries

**3. Platform Constraints**

- WhatsApp: 4096 character limit for text messages
- Long text walls = poor mobile UX
- No native support for hierarchical data display

### Impact

| Scenario | Current UX | Desired UX |
|----------|-----------|------------|
| Complex entity created | Text summary, no details | Visual page with full details |
| Validation errors (5 issues) | List in chat, hard to parse | Error cards with context |
| Comparison request | Side-by-side text (unreadable) | Visual comparison table |
| Large query result (50 items) | Truncated or paginated text | Browsable HTML view |

---

## Vision

### AutifyME Platform Model

```text
AutifyME Platform (We build this)
    |
    +-- Client Company A: "Pavisha Packaging" (Packaging industry)
    |       - Their brand, their data, their users
    |       - Rich outputs show "Pavisha Packaging" branding
    |
    +-- Client Company B: "Artisan Guitars" (Musical instruments)
    |       - Different brand, different domain, different users
    |       - Rich outputs show "Artisan Guitars" branding
    |
    +-- Client Company C: "EcoHome Supplies" (Retail)
            - Different everything
            - Rich outputs show "EcoHome Supplies" branding
```

**Critical:** The tool is domain-agnostic. It works for ANY structured data - not just "products" or "catalogs". The rendering LLM adapts to whatever data structure it receives.

### Intelligence-First Output Decisions

Agents don't follow rigid rules ("if >10 items, use HTML"). They REASON:

```text
Agent Internal Reasoning:
"User asked to create 12 items. Text would be:
- 800+ characters of structured data
- Hard to verify details
- No visual hierarchy
- Poor mobile experience

Decision: Generate visual output.
The rendering LLM will figure out the best layout from the data structure.
Company branding will be applied automatically.
"
```

### Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Agent Autonomy** | Agents decide format based on context, not hardcoded rules |
| **Domain Agnostic** | Works for ANY structured data, not tied to specific domain |
| **Client Branded** | Outputs show client company's brand, not AutifyME |
| **LLM-Powered Rendering** | No predefined templates; LLM generates appropriate HTML |
| **Context Injected** | Company profile flows via same middleware as PM |
| **Defense in Depth** | Sanitize inputs AND outputs (don't trust LLM blindly) |
| **Zero New Infrastructure** | Leverages existing Supabase Storage |
| **Mobile-First** | All outputs optimized for WhatsApp/mobile viewing |

---

## Architecture

### System Overview

```text
                    Agent (PM / Specialist)
                              |
                              | Has company_profile via middleware
                              | Decides: "Visual output needed"
                              v
                    +-------------------+
                    | GenerateRichOutput|
                    |       Tool        |
                    +--------+----------+
                             |
            +----------------+----------------+
            |                |                |
            v                v                v
    +-------+--------+ +-----+------+ +-------+-------+
    | Input          | |Company     | | Summary Gen  |
    | Sanitization   | |Context     | | (for chat)   |
    +-----------------+ |Extraction  | +-------+------+
                        +-----+------+         |
                              |                |
                              v                |
                    +---------+---------+      |
                    |  HTML Generator   |      |
                    |       LLM         |      |
                    | (with company     |      |
                    |  branding)        |      |
                    +---------+---------+      |
                              |                |
                              v                |
                    +---------+---------+      |
                    |  Output           |      |
                    |  Sanitization     |      |
                    |  (strip scripts)  |      |
                    +---------+---------+      |
                              |                |
                              v                |
                    +---------+---------+      |
                    | Supabase Storage  |      |
                    | (with TTL metadata)|     |
                    +---------+---------+      |
                              |                |
                              v                v
                    +---------+----------------+-------+
                    |              RichOutputResult    |
                    | {url, filename, summary, error}  |
                    +----------------------------------+
```

### Data Flow

```text
1. Agent Decision
   - Evaluates output complexity
   - Determines visual output is needed
   - Already has company_profile from middleware

2. Tool Invocation
   - Receives data + context + company_profile + field_hints
   - Sanitizes INPUT data (escape HTML entities)
   - Extracts primary image for OG preview

3. HTML Generation
   - LLM receives company context (name, industry, brand voice, style)
   - LLM receives field_hints for intelligent labeling
   - LLM analyzes data structure (no hardcoded domain assumptions)
   - LLM generates branded, appropriate HTML

4. Output Sanitization
   - Strip any <script> tags from LLM output
   - Remove on* event handlers
   - Remove javascript: URLs
   - Validate HTML structure

5. Storage Upload
   - Upload HTML to Supabase Storage
   - Set expires_at in user_metadata for TTL cleanup
   - Content-Type: text/html; charset=utf-8

6. Result Return
   - Public URL (browser renders directly)
   - Summary text (for chat context)
```

### Storage Architecture

```text
Supabase Storage
    |
    +-- assets/                    (existing bucket)
         |
         +-- outputs/              (new folder for rich outputs)
              |
              +-- {timestamp}_{uuid}.html
              ...
```

**URL Pattern:**

```text
https://{project}.supabase.co/storage/v1/object/public/assets/outputs/{filename}.html
```

---

## Company Context Integration

### Existing Infrastructure

Company context already flows through AutifyME via middleware:

```python
# From context_middleware.py
async def load_base_context(
    company_profile: CompanyProfile,
    storage: StorageInterface,
) -> PMBaseContext:
    """Load complete base context for Intelligent PM."""
    return PMBaseContext(
        company_profile=company_profile,  # <- THIS IS WHAT WE USE
        catalog_summary=...,
        taxonomy_tree=...,
        company_patterns=...,
    )
```

### CompanyProfile Model

```python
class CompanyProfile(BaseModel):
    """Company's profile and brand guidelines."""

    id: str
    name: str                              # "Pavisha Packaging"
    brand_voice: str                       # "Professional, innovative, eco-conscious"
    target_audience: str                   # "B2B packaging buyers"
    style_preferences: list[str] | None    # ["modern", "clean", "sustainable"]
    industry: str | None                   # "Packaging Manufacturing"
    sku_naming_convention: SKUNamingConvention | None
```

### How Rich Output Tool Gets Company Context

**Option A: Explicit Parameter (Recommended for v1)**

```python
# Agent calls tool with company context from its state
result = await generate_rich_output(
    data=structured_data,
    context="User needs to verify before approval",
    company_profile=self.company_profile,  # From agent's middleware-injected context
    ...
)
```

**Option B: Middleware Injection (Future Enhancement)**

```python
# Tool automatically receives company context via middleware
# Similar to how PM gets context
@inject_company_context
async def generate_rich_output(...):
    company = get_current_company_profile()
    ...
```

### v1 Brand Limitation

**Current CompanyProfile lacks visual brand assets:**

- No `logo_url`
- No `primary_color` / `secondary_color`
- Only `style_preferences` and `industry` for color derivation

**Impact:** v1 outputs will have "inferred" branding based on industry and style keywords. Colors will be derived, not explicit.

**Future Enhancement:**

```python
class CompanyProfile(BaseModel):
    # ... existing fields ...

    # Brand assets (v2 enhancement)
    logo_url: str | None = None
    primary_color: str | None = None      # "#0066cc"
    secondary_color: str | None = None    # "#f8f9fa"
    accent_color: str | None = None       # "#28a745"
```

---

## Agent Protocol

### Simplified Protocol (Intelligence-First)

```markdown
## Rich Output Capability

You can generate visual HTML pages when text is insufficient.

**Core Question:** "Can the user understand and verify this information as text?"
- No -> Use rich output
- Yes -> Use text

**When to Use:**
- Structured data with 5+ items requiring verification
- Hierarchical or nested data
- Comparisons between entities
- Multiple validation errors (3+)
- Large query results
- Any case where text would be a "wall of data"

**When NOT to Use:**
- Simple confirmations
- Short lists (< 5 items)
- Conversational responses
- Single error with clear message

**How to Use:**
1. Call generate_rich_output with your data
2. Provide field_hints for domain-specific labels
3. Provide context explaining what user needs to do with this
4. Company branding is applied automatically
5. Include the URL AND summary in your response

**Response Pattern:**
"Here's the [what] I've prepared:

[Summary from tool - e.g., "12 items, $499-$1299"]

[URL from tool]

[What you want user to do next]"
```

### Edge Case Guidance

| Scenario | Decision | Reasoning |
|----------|----------|-----------|
| 5 items, simple fields | TEXT | Borderline - text is sufficient |
| 5 items, with images | RICH | Images need visual display |
| 3 errors, simple | TEXT | Few enough to list inline |
| 3 errors, complex (nested) | RICH | Nested details need structure |
| Hierarchy, 2 levels | TEXT | Simple tree can be shown inline |
| Hierarchy, 3+ levels | RICH | Deep nesting needs visual |
| Comparison, 2 items | TEXT | Side-by-side text works |
| Comparison, 3+ items | RICH | Table needed for clarity |

### Canonical Examples

```xml
<example>
<scenario>Agent created complex nested data structure (12 items with hierarchy)</scenario>
<reasoning>
12 items with nested details - text would be 800+ chars.
User needs to verify before approval.
Visual layout shows structure clearly.
I have company_profile from my context - branding will be automatic.
</reasoning>
<tool_call>
generate_rich_output(
    title="New Product Line - Preview",
    data={...structured data...},
    context="Preview of items to be created. User needs to verify structure and details before approval.",
    company_profile=self.company_profile,
    field_hints={
        "sku_code": {"label": "SKU", "format": "code"},
        "unit_price": {"label": "Price", "format": "currency"},
        "moq": {"label": "Min Order Qty", "format": "number"}
    }
)
</tool_call>
<response>
"Here's the new product line I've prepared:

**3 categories, 12 items | $499 - $1,399**

https://supabase.../outputs/abc123.html

Please review the structure and details. Let me know if everything looks correct or if you'd like any changes."
</response>
</example>

<example>
<scenario>Simple single-item creation</scenario>
<reasoning>
Single item - simple enough for text.
Quick confirmation, no visual needed.
</reasoning>
<response>
"Added the new item: Red Variant at $799.

Shall I proceed with saving this?"
</response>
</example>

<example>
<scenario>5 items with simple fields (edge case)</scenario>
<reasoning>
5 items is borderline. Fields are simple (name, price, status).
Text list is readable. No visual needed.
</reasoning>
<response>
"Here are the 5 items ready for approval:

1. Standard Black - $499 (Active)
2. Standard Red - $529 (Active)
3. Pro Black - $799 (Active)
4. Pro Red - $849 (Draft)
5. Elite Black - $1,299 (Active)

Shall I proceed?"
</response>
</example>

<example>
<scenario>Validation found 5 errors during import</scenario>
<reasoning>
5 errors with field-level details - hard to parse in text.
User needs to understand each issue to resolve.
Visual error cards help comprehension.
</reasoning>
<tool_call>
generate_rich_output(
    title="Validation Issues Found",
    data={"errors": [...5 error objects...]},
    context="Validation errors requiring user resolution before operation can proceed.",
    company_profile=self.company_profile
)
</tool_call>
<response>
"I found 5 issues that need resolution:

https://supabase.../outputs/def456.html

Please review each issue and let me know how to proceed."
</response>
</example>
```

---

## Tool Specification

### Input Schema

```python
class FieldHint(BaseModel):
    """Hint for how to render a specific field."""

    label: str = Field(
        description="Human-friendly label to display (e.g., 'SKU' instead of 'sku_code')"
    )
    format: Literal["text", "code", "currency", "number", "date", "url", "image"] = Field(
        default="text",
        description="How to format the value"
    )
    currency: str | None = Field(
        default="USD",
        description="Currency code if format=currency"
    )


class RichOutputInput(BaseModel):
    """Input schema for rich output generation.

    Agents provide structured data and context; the rendering LLM
    analyzes data structure and company context to generate appropriate,
    branded visual output.
    """

    title: str = Field(
        description="Page title - appears in header and link preview (OG tags)"
    )

    data: dict | list[dict] = Field(
        description="Structured data to render. Any shape - LLM adapts layout."
    )

    context: str = Field(
        description="WHY this page exists, WHAT user needs to understand/do"
    )

    company_profile: CompanyProfile = Field(
        description="Client company profile for branding. Injected from agent context."
    )

    field_hints: dict[str, FieldHint] | None = Field(
        default=None,
        description="Hints for field rendering. Key=field_name, Value=display config. "
                    "Use this to provide human-friendly labels and formatting for domain-specific fields."
    )

    images: list[str] | None = Field(
        default=None,
        description="Image URLs. First = primary (OG preview). Full https:// URLs."
    )

    layout_hint: str | None = Field(
        default=None,
        description="Optional hint: 'grid', 'table', 'hierarchy', 'comparison', 'timeline'. LLM may override based on data."
    )

    highlight_fields: list[str] | None = Field(
        default=None,
        description="Field names to emphasize visually (e.g., ['price', 'status'])"
    )

    ttl_days: int = Field(
        default=30,
        description="Days until this output expires and is deleted. Default 30."
    )


class RichOutputResult(BaseModel):
    """Result from rich output generation."""

    success: bool
    url: str | None = Field(description="Public URL to branded page")
    filename: str | None = Field(description="Storage filename for reference")
    summary: str = Field(description="Text summary for chat context")
    expires_at: str | None = Field(description="ISO timestamp when output will be deleted")
    error: str | None = None
```

### Tool Implementation

```python
"""
Location: agents/src/autifyme_agents/tools/rich_output/tool.py
"""

from langchain.tools import StructuredTool
from autifyme_agents.schemas.models import CompanyProfile

def create_rich_output_tool() -> StructuredTool:
    """Create the generate_rich_output tool."""

    async def _generate_rich_output_impl(
        title: str,
        data: dict | list,
        context: str,
        company_profile: CompanyProfile,
        field_hints: dict | None = None,
        images: list[str] | None = None,
        layout_hint: str | None = None,
        highlight_fields: list[str] | None = None,
        ttl_days: int = 30,
    ) -> dict:
        """Generate branded HTML output from structured data.

        Flow:
        1. Sanitize INPUT data (escape HTML entities)
        2. Prepare prompt with company context + field_hints
        3. Generate HTML via LLM
        4. Sanitize OUTPUT HTML (strip scripts, event handlers)
        5. Validate HTML structure
        6. Upload to Supabase Storage with TTL metadata
        7. Return URL and summary
        """
        # Implementation in tool.py
        pass

    return StructuredTool.from_function(
        coroutine=_generate_rich_output_impl,
        name="generate_rich_output",
        description="""
Generate visual HTML output when text is insufficient.

USE WHEN:
- Structured data with 5+ items
- Hierarchical/nested data
- Comparisons between entities
- Multiple validation errors
- Large query results

DO NOT USE WHEN:
- Simple confirmations
- Short lists (< 5 items)
- Conversational responses

Use field_hints to provide human-friendly labels for domain-specific fields.
Output is automatically branded for the client company.
Always include the summary text in your response for context.
""",
        args_schema=RichOutputInput,
    )
```

---

## HTML Generator LLM

### Model Selection

| Consideration | Choice | Rationale |
|---------------|--------|-----------|
| **Model** | Claude Haiku | Fast, cheap, excellent at HTML |
| **Temperature** | 0 | Deterministic output |
| **Max Tokens** | 16000 | Sufficient for complex pages |

### System Prompt

```python
HTML_GENERATOR_SYSTEM_PROMPT = """
You are an expert HTML/CSS generator that creates beautiful, branded web pages from structured data.

## Your Role

Transform JSON data into self-contained, mobile-optimized HTML pages.
You make ALL layout decisions based on data structure and company context.
Output is branded for the CLIENT COMPANY, not the platform.

## Company Context

You are rendering data for **{company.name}**.

- **Industry:** {company.industry}
- **Brand Voice:** {company.brand_voice}
- **Target Audience:** {company.target_audience}
- **Style Keywords:** {company.style_preferences}

### Branding Guidelines

1. **Header:** Display company name prominently (NEVER show "AutifyME")
2. **Visual Tone:** Match brand voice:
   - "Professional" -> Clean lines, muted colors, formal typography
   - "Playful" -> Rounded corners, brighter accents, friendly fonts
   - "Luxury" -> Elegant spacing, refined typography, rich colors
   - "Eco-conscious" -> Earth tones, organic shapes, green accents
   - "Innovative" -> Modern design, bold accents, dynamic layout
3. **Color Derivation:** If no explicit colors provided, derive from industry and style:
   - Manufacturing/B2B -> Blues (#0d6efd), grays (#6c757d), professional palette
   - Retail/Consumer -> Warmer oranges, vibrant palette
   - Healthcare -> Clean whites, calming blues/greens
   - Creative/Arts -> Bold, expressive colors

## Field Hints

When field_hints are provided, use them for rendering:

```json
{
  "sku_code": {"label": "SKU", "format": "code"},
  "unit_price": {"label": "Price", "format": "currency", "currency": "USD"},
  "moq": {"label": "Min Order Qty", "format": "number"}
}
```

- **label:** Use this instead of converting field name
- **format:** Apply appropriate formatting:
  - "code" -> monospace font, subtle background
  - "currency" -> currency symbol, 2 decimals, right-aligned
  - "number" -> thousands separators
  - "date" -> human-readable format
  - "url" -> clickable link
  - "image" -> render as <img>

For fields WITHOUT hints, convert snake_case to Title Case.

## Output Requirements

### Technical Constraints

- Generate ONLY HTML code - no explanations, no markdown wrapper
- Single self-contained file (inline CSS, no external dependencies)
- Mobile-first responsive design
- **NO JAVASCRIPT** (static HTML only)
- **NO onclick, onload, onerror or any event handlers**
- Valid HTML5
- Start with <!DOCTYPE html>, end with </html>

### Document Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <!-- OG tags for link preview -->
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{auto-generated summary}">
    <meta property="og:image" content="{first image URL or placeholder}">
    <meta property="og:type" content="website">

    <title>{title} | {company.name}</title>
    <style>
        /* All CSS inline - mobile-first, brand-appropriate */
    </style>
</head>
<body>
    <header>
        <!-- Company name prominently -->
    </header>
    <main>
        <!-- Content -->
    </main>
    <footer>
        <!-- Minimal footer with company name -->
    </footer>
</body>
</html>
```

### Visual Design System

**Typography:**

- System font stack: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
- Base size: 16px minimum for readability
- Clear hierarchy: h1 > h2 > h3

**Layout:**

- Mobile-first (375px base, scale up)
- Maximum content width: 800px, centered
- Generous whitespace

**Components:**

- Cards: Subtle shadow, rounded corners
- Tables: Zebra striping, sticky headers
- Touch targets: 44px minimum

## Data-Driven Layout

Analyze the data structure and render appropriately.

**Array of objects (list of entities):**

- Few items (2-5) with images -> Card grid
- Many items (10+) -> Compact table or grouped list
- Items with parent-child -> Nested cards or tree view

**Single object (entity details):**

- Has image -> Hero image + attribute list
- No image -> Clean attribute table or definition list

**Comparison data (similar entities to compare):**

- Side-by-side columns
- Highlight differences with background color

**Error/validation data:**

- Red/warning accent
- Clear icon per item
- Field + message + suggested resolution

**Hierarchical data:**

- Indented tree structure
- Visual parent-child connectors
- Clear nesting levels

### Empty States

- Never blank page
- Friendly message: "No items to display"
- Subtle icon

### Large Data (20+ items)

- Show all items (browser handles scroll)
- Summary count at top: "Showing 47 items"
- Consider logical grouping with section headers

## Input Format

```json
{
  "title": "Page title",
  "data": { ... } or [ ... ],
  "context": "What user needs to understand/do with this",
  "company": {
    "name": "Pavisha Packaging",
    "industry": "Packaging Manufacturing",
    "brand_voice": "Professional, innovative, eco-conscious",
    "target_audience": "B2B packaging buyers",
    "style_preferences": ["modern", "clean", "sustainable"]
  },
  "field_hints": {
    "sku_code": {"label": "SKU", "format": "code"},
    "unit_price": {"label": "Price", "format": "currency"}
  },
  "images": ["url1", "url2"],
  "layout_hint": "grid|table|hierarchy|comparison|timeline",
  "highlight_fields": ["field1", "field2"]
}
```

## Output Format

Return ONLY the complete HTML code.

- No markdown fences
- No explanations
- Start: <!DOCTYPE html>
- End: </html>
"""
```

---

## Integration Points

### Supabase Storage

**Upload with TTL Metadata:**

```python
from datetime import datetime, timedelta

async def upload_rich_output(
    html_content: str,
    filename: str,
    ttl_days: int = 30,
) -> dict:
    """Upload HTML with expiration metadata."""

    expires_at = (datetime.utcnow() + timedelta(days=ttl_days)).isoformat()

    client.storage.from_("assets").upload(
        path=f"outputs/{filename}",
        file=html_content.encode("utf-8"),
        file_options={
            "content-type": "text/html; charset=utf-8",
            "x-upsert": "true",
        },
    )

    # Set expiration in user_metadata
    # Note: Supabase doesn't have native TTL - we track for cleanup job
    await storage.update_object_metadata(
        bucket="assets",
        path=f"outputs/{filename}",
        metadata={"expires_at": expires_at}
    )

    url = client.storage.from_("assets").get_public_url(f"outputs/{filename}")

    return {"url": url, "expires_at": expires_at}
```

### Agent Tool Registration

```python
# Add to any agent that needs rich output
from autifyme_agents.tools.rich_output import create_rich_output_tool

specialist_tools = [
    # ... existing tools ...
    create_rich_output_tool(),
]
```

### Company Context Access

Agents already have company context via middleware. They pass it to the tool:

```python
# In specialist or PM
result = await self.tools["generate_rich_output"].ainvoke({
    "title": "Preview",
    "data": structured_data,
    "context": "User verification needed",
    "company_profile": self.base_context.company_profile,  # From middleware
    "field_hints": {
        "sku_code": {"label": "SKU", "format": "code"},
        "unit_price": {"label": "Price", "format": "currency"},
    },
})
```

---

## Security Considerations

### Input Sanitization

```python
import html

def sanitize_input_data(data: Any) -> Any:
    """Sanitize INPUT data before sending to LLM.

    Escapes HTML entities to prevent injection via data values.
    """
    if isinstance(data, str):
        return html.escape(data)
    elif isinstance(data, dict):
        return {k: sanitize_input_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input_data(item) for item in data]
    return data
```

### Output Sanitization (Defense in Depth)

```python
import re

def sanitize_llm_html_output(html_content: str) -> str:
    """Sanitize LLM-generated HTML output.

    DO NOT trust LLM to follow instructions perfectly.
    Strip any potentially dangerous content.
    """
    # Remove <script> tags and content
    html_content = re.sub(
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
        '',
        html_content,
        flags=re.IGNORECASE
    )

    # Remove on* event handlers (onclick, onerror, onload, etc.)
    html_content = re.sub(
        r'\bon\w+\s*=\s*["\'][^"\']*["\']',
        '',
        html_content,
        flags=re.IGNORECASE
    )

    # Remove javascript: URLs
    html_content = re.sub(
        r'javascript\s*:',
        '',
        html_content,
        flags=re.IGNORECASE
    )

    # Remove data: URLs (potential XSS vector)
    html_content = re.sub(
        r'data\s*:\s*text/html',
        '',
        html_content,
        flags=re.IGNORECASE
    )

    return html_content
```

### HTML Structure Validation

```python
def validate_html_structure(content: str) -> tuple[bool, str | None]:
    """Validate HTML has required structure.

    Returns (is_valid, error_message).
    """
    content = content.strip()

    if not content.startswith("<!DOCTYPE html>"):
        return False, "Missing DOCTYPE"

    if not content.endswith("</html>"):
        return False, "Missing closing </html>"

    if "<head>" not in content:
        return False, "Missing <head>"

    if "<body>" not in content:
        return False, "Missing <body>"

    if "<title>" not in content:
        return False, "Missing <title>"

    return True, None
```

### Image URL Validation

```python
from urllib.parse import urlparse

def validate_image_url(url: str) -> bool:
    """Validate image URL is safe to include."""
    parsed = urlparse(url)

    # Must be HTTPS
    if parsed.scheme != "https":
        return False

    # Block known malicious patterns
    if "javascript:" in url.lower():
        return False

    return True
```

---

## Retention Policy

### Strategy

Supabase Storage does **not have built-in TTL/lifecycle policies**. We implement our own:

1. **Upload:** Set `expires_at` in object metadata
2. **Cleanup:** Daily cron job deletes expired objects

### Metadata Schema

```python
# When uploading
metadata = {
    "expires_at": "2025-01-19T00:00:00Z",  # ISO timestamp
    "created_by": "agent_id",
    "output_type": "rich_output",
}
```

### Cleanup Function

```sql
-- Function to delete expired rich outputs
-- Schedule via pg_cron or external scheduler

CREATE OR REPLACE FUNCTION cleanup_expired_rich_outputs()
RETURNS void AS $$
DECLARE
    expired_object RECORD;
BEGIN
    -- Query storage.objects for expired items
    -- Note: This requires access to storage.objects table
    FOR expired_object IN
        SELECT name
        FROM storage.objects
        WHERE bucket_id = 'assets'
          AND name LIKE 'outputs/%'
          AND (metadata->>'expires_at')::timestamptz < NOW()
    LOOP
        -- Delete via storage API
        PERFORM storage.delete('assets', expired_object.name);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Schedule daily at 3 AM UTC
SELECT cron.schedule('cleanup-rich-outputs', '0 3 * * *', 'SELECT cleanup_expired_rich_outputs()');
```

### Default TTL

- **Default:** 30 days
- **Configurable:** Via `ttl_days` parameter (1-365)
- **Permanent:** Set `ttl_days=0` for no expiration (use sparingly)

---

## Edge Cases

| Case | Handling |
|------|----------|
| Empty data | LLM generates "No items" message with icon |
| Very large data (100+) | Show all with scroll, summary count at top |
| Missing images | Placeholder or skip image section |
| Missing company fields | Use sensible defaults, neutral styling |
| HTML generation failure | Return error, agent falls back to text |
| Malformed HTML from LLM | Validate, retry once with feedback, then error |
| LLM generates scripts | Output sanitization strips them |
| Invalid image URLs | Skip invalid, render valid ones |

---

## Testing Strategy

### Testable Assertions

```python
class TestRichOutputAssertions:
    """Assertions for validating LLM-generated HTML."""

    @staticmethod
    def assert_branded(html: str, company_name: str):
        """Output shows client company, not platform."""
        assert company_name in html, f"Company name '{company_name}' not found"
        assert "AutifyME" not in html, "Platform name should not appear"

    @staticmethod
    def assert_data_rendered(html: str, data: dict | list):
        """All data fields are represented in output."""
        if isinstance(data, list) and data:
            sample = data[0]
        else:
            sample = data

        for key in sample.keys():
            # Either the key or a human-readable version should appear
            readable = key.replace("_", " ").title()
            assert key in html or readable in html, f"Field '{key}' not rendered"

    @staticmethod
    def assert_mobile_ready(html: str):
        """Output is mobile-optimized."""
        assert 'viewport' in html
        assert 'width=device-width' in html

    @staticmethod
    def assert_no_scripts(html: str):
        """Output contains no executable code."""
        assert '<script' not in html.lower()
        assert 'javascript:' not in html.lower()
        assert 'onclick=' not in html.lower()
        assert 'onerror=' not in html.lower()

    @staticmethod
    def assert_valid_structure(html: str):
        """Output has valid HTML structure."""
        assert html.strip().startswith('<!DOCTYPE html>')
        assert html.strip().endswith('</html>')
        assert '<head>' in html
        assert '<body>' in html
        assert '<title>' in html
```

### Unit Tests

```python
class TestRichOutputTool:
    async def test_generates_branded_output(self):
        """Output includes client company name, not AutifyME."""
        result = await generate_rich_output(
            title="Test",
            data=[{"item": "test"}],
            context="Testing",
            company_profile=CompanyProfile(
                id="test",
                name="Acme Corp",
                brand_voice="Professional",
                target_audience="B2B",
                industry="Manufacturing"
            )
        )

        html = await fetch_html(result["url"])
        TestRichOutputAssertions.assert_branded(html, "Acme Corp")
        TestRichOutputAssertions.assert_no_scripts(html)

    async def test_field_hints_applied(self):
        """Field hints produce correct labels and formatting."""
        result = await generate_rich_output(
            title="Test",
            data=[{"sku_code": "ABC-123", "unit_price": 49.99}],
            context="Testing",
            company_profile=...,
            field_hints={
                "sku_code": {"label": "SKU", "format": "code"},
                "unit_price": {"label": "Price", "format": "currency"}
            }
        )

        html = await fetch_html(result["url"])
        assert "SKU" in html  # Label applied
        assert "$49.99" in html or "49.99" in html  # Currency formatted

    async def test_xss_in_data_sanitized(self):
        """Malicious input data is escaped."""
        result = await generate_rich_output(
            title="Test",
            data=[{"name": "<script>alert('xss')</script>"}],
            context="Testing",
            company_profile=...
        )

        html = await fetch_html(result["url"])
        assert "<script>" not in html
        assert "&lt;script&gt;" in html  # Escaped

    async def test_xss_in_output_sanitized(self):
        """Even if LLM generates scripts, they are stripped."""
        # This tests the output sanitization layer
        html = sanitize_llm_html_output(
            '<html><body><script>alert("xss")</script><p>Content</p></body></html>'
        )
        assert "<script>" not in html
        assert "<p>Content</p>" in html
```

### Integration Tests

```python
class TestRichOutputIntegration:
    async def test_full_flow(self):
        """Generate -> Sanitize -> Upload -> Access -> Renders correctly."""
        result = await generate_rich_output(...)

        assert result["success"]
        assert result["url"].startswith("https://")
        assert result["expires_at"] is not None

        # Fetch and validate
        response = await httpx.get(result["url"])
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    async def test_og_tags_for_preview(self):
        """Link preview shows correct title and description."""
        result = await generate_rich_output(
            title="My Test Page",
            ...
        )

        html = await fetch_html(result["url"])
        assert 'og:title' in html
        assert 'My Test Page' in html
```

---

## Known Limitations

### v1 Limitations (Documented)

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **No explicit brand colors** | Colors derived from industry/style - may not match exact brand | Document, enhance CompanyProfile in v2 |
| **No logo support** | Header shows company name only | Add logo_url in v2 |
| **LLM output variability** | Same data may render slightly differently | Temperature=0 helps; accept minor variation |
| **No feedback/iteration** | Changes require full regeneration | Document; consider edit capability in v2 |
| **Additional LLM latency** | ~500ms-2s added to response time | Haiku is fast; acceptable for complex data |
| **30-day default retention** | Old links eventually break | Document; allow ttl_days=0 for permanent |

### Future Enhancements (v2+)

- [ ] Explicit brand colors in CompanyProfile
- [ ] Logo URL support
- [ ] PDF generation option
- [ ] Signed URLs for sensitive data
- [ ] Content-hash caching (skip regeneration for same data)
- [ ] Edit/modify existing output
- [ ] Analytics (view tracking)

---

## Implementation Phases

### Phase 1: Core Tool (MVP)

**Deliverables:**

- [ ] Input/Output schemas with field_hints
- [ ] HTML Generator LLM integration
- [ ] System prompt with company context + field_hints
- [ ] Input sanitization
- [ ] Output sanitization
- [ ] HTML structure validation
- [ ] Supabase Storage upload with TTL metadata
- [ ] Basic tool implementation
- [ ] Unit tests with assertions

**Timeline:** 4-5 days

**Success Criteria:**

- Generates branded HTML from any structured data
- Company name appears in output (not AutifyME)
- field_hints produce correct labels
- No scripts in output (even if LLM hallucinates)
- URL is publicly accessible
- Basic layouts work (list, detail, errors)

### Phase 2: Agent Integration

**Deliverables:**

- [ ] Add tool to PM and specialists
- [ ] Update agent prompts with protocol + edge cases
- [ ] Add canonical examples
- [ ] Integration tests

**Timeline:** 2-3 days

**Success Criteria:**

- Agents autonomously decide when to use
- Agents use field_hints for domain fields
- Agents include URL + summary in responses
- Users see branded pages

### Phase 3: Cleanup & Refinement

**Deliverables:**

- [ ] Storage cleanup function (pg_cron)
- [ ] OG tag optimization for rich previews
- [ ] Performance measurement
- [ ] Retry logic for malformed HTML

**Timeline:** 2-3 days

### Phase 4: Future Enhancements

- [ ] Brand colors in CompanyProfile
- [ ] Logo integration
- [ ] Content-hash caching
- [ ] Signed URLs option
- [ ] PDF generation

---

## File Structure

```text
agents/src/autifyme_agents/tools/rich_output/
    __init__.py
    tool.py                 # Main tool implementation
    schemas.py              # Input/output schemas, FieldHint
    html_generator.py       # LLM interaction
    prompts/
        __init__.py
        system_prompt.py    # HTML generator prompt
    utils/
        __init__.py
        input_sanitization.py   # Escape HTML in input data
        output_sanitization.py  # Strip scripts from LLM output
        validation.py           # HTML structure validation
        assertions.py           # Test assertion helpers

database/
    migrations/
        xxx_rich_output_cleanup.sql  # pg_cron cleanup function
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Generation time | < 5 seconds |
| HTML size | < 200KB typical |
| Agent adoption | 80%+ complex outputs use tool |
| Branding accuracy | 100% show client name, not platform |
| Security | 0% outputs with executable code |
| Error rate | < 1% generation failures |

---

## Key Principles Checklist

- [x] **Intelligence-First:** Agents reason about when to use, LLM reasons about layout
- [x] **Domain Agnostic:** Works for any structured data, field_hints enable labeling
- [x] **Client Branded:** Outputs show client company, not AutifyME
- [x] **Context Injected:** Uses same CompanyProfile as PM via middleware
- [x] **Defense in Depth:** Sanitize inputs AND outputs
- [x] **Minimal Scaffolding:** Simple protocol, trust agent intelligence
- [x] **Zero New Infrastructure:** Uses existing Supabase Storage

---

**Version History:**

- v1.2.0 (2025-12-19): Added field_hints, output sanitization, retention policy, testable assertions, edge case guidance, known limitations
- v1.1.0 (2025-12-19): Revised for platform model - domain agnostic, client branded, company context integration
- v1.0.0 (2025-12-19): Initial design document
