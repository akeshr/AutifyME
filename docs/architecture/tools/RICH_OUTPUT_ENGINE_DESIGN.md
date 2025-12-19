# Rich Output Engine - Design Specification

**Status:** Draft - Ready for Review
**Created:** December 19, 2025
**Priority:** HIGH - Enhances agent output capabilities
**Related:** [IMAGE_STUDIO_TOOL.md](./IMAGE_STUDIO_TOOL.md), [UNIVERSAL_DATA_ENGINE_DESIGN.md](../core/UNIVERSAL_DATA_ENGINE_DESIGN.md)

---

## Executive Summary

Transform how AutifyME agents present complex data to users. Instead of forcing structured data into text messages (which hit character limits, lose hierarchy, and overwhelm users), agents autonomously decide when visual output serves better and generate rich HTML pages on-demand.

**Core Principle:** Give agents the CAPABILITY to render rich outputs; let them DECIDE when to use it based on context.

**Key Insight:** Modern LLMs excel at HTML/CSS generation. No templates needed - the rendering LLM analyzes data structure and generates appropriate layouts dynamically.

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Vision](#vision)
- [Architecture](#architecture)
- [Agent Protocol](#agent-protocol)
- [Tool Specification](#tool-specification)
- [HTML Generator LLM](#html-generator-llm)
- [Integration Points](#integration-points)
- [Security Considerations](#security-considerations)
- [Edge Cases](#edge-cases)
- [Testing Strategy](#testing-strategy)
- [Implementation Phases](#implementation-phases)

---

## Problem Statement

### Current Pain Points

**1. Text Limitations**
```
User: "Catalog the Jarvis Guitar line with 3 models and 2 finishes each"

Current PM Response:
"Done! Created Jarvis Guitar family with:
- 3 products (Standard, Pro, Elite)
- 6 variants total
- Price range: $499-$1299"
```

**What's Missing:**
- User cannot VERIFY what was created
- No visibility into SKUs, attributes, pricing per variant
- No visual hierarchy showing family -> products -> variants
- Character limits prevent sending complete data

**2. Verification Gap**
- Users approve changes they cannot fully inspect
- Errors discovered post-approval require costly rollbacks
- Complex data (catalogs, comparisons, reports) reduced to lossy summaries

**3. Platform Constraints**
- WhatsApp: 4096 character limit for text messages
- Long text walls = poor mobile UX
- No native support for hierarchical data display

### Impact

| Scenario | Current UX | Desired UX |
|----------|-----------|------------|
| Product family created (12 variants) | Text summary, no details | Visual page with all variants |
| Validation errors (5 conflicts) | List in chat, hard to parse | Error cards with context |
| Comparison request | Side-by-side text (unreadable) | Visual comparison table |
| Large query result (50 products) | Truncated or paginated text | Filterable HTML table |

---

## Vision

### Intelligence-First Output Decisions

Agents don't follow rigid rules ("if >10 items, use HTML"). They REASON:

```
Agent Internal Reasoning:
"User asked to catalog 12 variants. Text would be:
- 800+ characters of structured data
- Hard to verify SKUs and prices
- No visual hierarchy
- Poor mobile experience

Decision: Generate visual output with:
- content_type: 'preview' (pending changes)
- Highlight: SKU codes, prices
- Context: 'User needs to verify before approval'
"
```

### Capability + Autonomy Model

```
+------------------+
|  Agent Reasoning |  <- "Is text sufficient for user to understand/verify?"
+--------+---------+
         |
         | NO - Complex data, verification needed
         v
+--------+---------+
| GenerateRichOutput|  <- Tool capability
|       Tool        |
+--------+---------+
         |
         v
+--------+---------+
|  HTML Generator  |  <- LLM generates layout from data
|       LLM        |
+--------+---------+
         |
         v
+--------+---------+
| Supabase Storage |  <- Existing infrastructure
+--------+---------+
         |
         v
+--------+---------+
|   Public URL     |  <- Browser renders HTML
+------------------+
```

### Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Agent Autonomy** | Agents decide format based on context, not hardcoded rules |
| **LLM-Powered Rendering** | No predefined templates; LLM generates appropriate HTML |
| **Zero New Infrastructure** | Leverages existing Supabase Storage |
| **Generic Tool** | Any agent can use for any data type |
| **Mobile-First** | All outputs optimized for WhatsApp/mobile viewing |

---

## Architecture

### System Overview

```
                    Agent (PM / Specialist)
                              |
                              | Decides: "Visual output needed"
                              | Prepares: content_type, data, context
                              v
                    +-------------------+
                    | GenerateRichOutput|
                    |       Tool        |
                    +--------+----------+
                             |
            +----------------+----------------+
            |                                 |
            v                                 v
    +-------+--------+               +--------+-------+
    | Input Validation|               | Summary Gen   |
    | & Sanitization  |               | (for chat)    |
    +-------+--------+               +--------+-------+
            |                                 |
            v                                 |
    +-------+--------+                        |
    | HTML Generator |                        |
    |     LLM        |                        |
    | (Claude Haiku) |                        |
    +-------+--------+                        |
            |                                 |
            v                                 |
    +-------+--------+                        |
    | Supabase       |                        |
    | Storage Upload |                        |
    | (text/html)    |                        |
    +-------+--------+                        |
            |                                 |
            v                                 v
    +-------+---------------------------------+-------+
    |              RichOutputResult                   |
    | {url, filename, summary, preview_image, error} |
    +------------------------------------------------+
                              |
                              v
                    Agent Response to User:
                    "[Summary text]
                     [URL to visual page]"
```

### Data Flow

```
1. Agent Decision
   - Evaluates output complexity
   - Determines content_type
   - Prepares structured data

2. Tool Invocation
   - Validates input schema
   - Sanitizes data (XSS prevention)
   - Extracts primary image for OG preview

3. HTML Generation
   - Fast LLM (Haiku) generates HTML
   - Includes OG meta tags for link preview
   - Mobile-first responsive design
   - Self-contained (inline CSS, no external deps)

4. Storage Upload
   - Upload HTML to Supabase Storage
   - Content-Type: text/html; charset=utf-8
   - Public bucket = no expiration

5. Result Return
   - Public URL (browser renders directly)
   - Summary text (for chat context)
   - Preview image URL (for OG tags)
```

### Storage Architecture

```
Supabase Storage
    |
    +-- assets/                    (existing bucket)
         |
         +-- outputs/              (new folder for rich outputs)
              |
              +-- {timestamp}_{uuid}.html
              +-- {timestamp}_{uuid}.html
              ...
```

**URL Pattern:**
```
https://{project}.supabase.co/storage/v1/object/public/assets/outputs/{filename}.html
```

**Behavior:**
- User clicks URL in WhatsApp
- Browser fetches HTML from Supabase
- Browser RENDERS the page (not download)
- User sees visual content

---

## Agent Protocol

### Protocol Specification

```yaml
name: RichOutputProtocol
version: "1.0"
purpose: |
  Enable agents to generate visual HTML outputs when text is insufficient.
  Agents decide format autonomously; rendering LLM handles layout.

decision_criteria:
  USE_RICH_OUTPUT:
    - Structured data with 5+ items requiring verification
    - Hierarchical data (parent-child relationships)
    - Side-by-side comparisons (2+ entities)
    - Complex validation errors (multiple fields/issues)
    - Query results exceeding 500 characters
    - Preview of pending changes (HITL verification)
    - Any case where text would be "wall of data"

  USE_TEXT:
    - Simple confirmations ("Created product X")
    - Single values or short lists (< 5 items)
    - Conversational responses
    - Single error with clear message

content_types:
  catalog:
    description: "Product listings, inventory views, search results"
    layout: "Grid of cards with images, titles, key attributes"
    best_for: "Showing multiple products/items"

  detail:
    description: "Single entity with full attributes"
    layout: "Hero image, title, attribute table"
    best_for: "Deep-dive into one item"

  comparison:
    description: "Side-by-side analysis of 2-5 entities"
    layout: "Columns or rows highlighting differences"
    best_for: "Helping user choose between options"

  table:
    description: "Structured query results, reports"
    layout: "Data grid with headers, sorting visual"
    best_for: "Tabular data, SKU lists, inventory"

  hierarchy:
    description: "Tree structures, nested categories"
    layout: "Indented tree view with expand indicators"
    best_for: "Family -> Products -> Variants structure"

  report:
    description: "Analytics, status summaries, dashboards"
    layout: "Metric cards, charts representation"
    best_for: "KPIs, workflow outcomes, summaries"

  timeline:
    description: "Sequential events, audit logs"
    layout: "Chronological list with timestamps"
    best_for: "Change history, activity feeds"

  preview:
    description: "Pending changes awaiting approval"
    layout: "Clear PREVIEW label, grouped by operation"
    best_for: "HITL verification before commit"

  error:
    description: "Validation failures, conflicts"
    layout: "Red accent, error cards with context"
    best_for: "Showing what's wrong and why"

input_formatting:
  data:
    - Can be single dict or list of dicts
    - Nested structures supported (3 levels max)
    - Dates as ISO strings (renderer formats)
    - Prices as numbers (renderer adds currency)

  images:
    - Full URLs (https://...)
    - First image = primary (used for OG preview)
    - Supported: jpg, png, webp
    - Missing images = placeholder shown

  highlight:
    primary: "Fields shown large/bold (price, name, status)"
    secondary: "Fields shown smaller (SKU, category, dates)"

  actions:
    - Optional buttons for visual context
    - Not interactive (visual only in v1)
    - Example: [{"label": "Approve", "style": "primary"}]

output_handling:
  url:
    - Always include in response to user
    - Works on mobile and desktop browsers
    - No expiration (public bucket)

  summary:
    - ALWAYS include text summary WITH the URL
    - Provides context before user clicks
    - Format: "Here's the [title] ([count] items): [URL]"
```

### Agent Prompt Addition

Add to PM and Specialist prompts:

```markdown
## Rich Output Capability

You have access to `generate_rich_output` tool for visual presentation of complex data.

### When to Use
Use rich output when text would be insufficient for the user to understand or verify:
- Product catalogs with 5+ items
- Hierarchical data (families -> products -> variants)
- Side-by-side comparisons
- Complex validation errors (multiple issues)
- Large query results
- Preview of changes before approval

### When NOT to Use
- Simple confirmations ("Created product X")
- Short lists (< 5 items that fit nicely in text)
- Conversational responses
- Single, clear error message

### How to Use
1. Reason about whether text is sufficient
2. Choose appropriate content_type based on data nature
3. Provide clear title and context for the rendering LLM
4. Include relevant images if available
5. Specify which fields to highlight

### Output Handling
ALWAYS include BOTH the URL and text summary in your response:

"Here's the complete catalog I've prepared:

**3 products, 12 variants | $499 - $1,399**

[URL from tool result]

Please review and let me know if you'd like any changes."

The summary gives context; the URL provides full details.
```

### Canonical Examples

```xml
<example>
<scenario>User asked to catalog product family with 3 products, 12 variants</scenario>
<reasoning>
12 variants with SKUs, prices, attributes - text would be 800+ chars.
User needs to verify before approval.
Visual layout shows hierarchy clearly.
</reasoning>
<tool_call>
generate_rich_output(
    content_type="preview",
    title="Jarvis Guitar - Cataloging Preview",
    data={...full structure...},
    context="Preview of product family to be created. User needs to verify SKUs, pricing, and structure.",
    highlight={"primary": ["sku", "price"], "secondary": ["name", "finish"]}
)
</tool_call>
<response>
"Here's the Jarvis Guitar catalog I've prepared:

**3 products, 12 variants | $499 - $1,399**

https://supabase.../outputs/abc123.html

Please review the SKUs, pricing, and structure. Let me know if everything looks correct."
</response>
</example>

<example>
<scenario>User asked to add one variant to existing product</scenario>
<reasoning>
Single variant - simple enough for text.
Quick confirmation, no visual needed.
</reasoning>
<response>
"Added variant JRV-PRO-RED (Red/Humbucker) at $799 to Jarvis Pro.

Shall I proceed with saving this?"
</response>
</example>

<example>
<scenario>Validation found 5 SKU conflicts during import</scenario>
<reasoning>
5 errors with conflicting values - hard to parse in text.
User needs to understand each conflict to resolve.
Error visualization helps.
</reasoning>
<tool_call>
generate_rich_output(
    content_type="error",
    title="SKU Conflicts Detected",
    data={"errors": [...5 error objects...]},
    context="Validation errors requiring user resolution before import can proceed."
)
</tool_call>
<response>
"I found 5 SKU conflicts that need resolution:

https://supabase.../outputs/def456.html

Please review each conflict and let me know how to proceed."
</response>
</example>

<example>
<scenario>User asked "show me all products in Guitar category"</scenario>
<reasoning>
Query returned 47 products.
Text listing would be unusable on mobile.
HTML page with visual cards serves better.
</reasoning>
<tool_call>
generate_rich_output(
    content_type="catalog",
    title="Guitar Category - 47 Products",
    data=[...47 products...],
    context="Complete product listing for Guitar category.",
    images=[...product images...]
)
</tool_call>
<response>
"Here's your Guitar catalog:

**47 products across 8 families**

https://supabase.../outputs/ghi789.html

Let me know if you'd like to filter or take action on any products."
</response>
</example>
```

---

## Tool Specification

### Input Schema

```python
class RichOutputInput(BaseModel):
    """Input schema for rich output generation.

    Agents provide structured data and context; the rendering LLM
    decides visual layout based on content_type and data structure.
    """

    content_type: Literal[
        "catalog",      # Product listings, search results
        "detail",       # Single entity deep-dive
        "comparison",   # Side-by-side analysis
        "table",        # Tabular data, query results
        "hierarchy",    # Tree structures, nested data
        "report",       # Analytics, summaries
        "timeline",     # Sequential events, history
        "preview",      # Pending changes (HITL)
        "error",        # Validation errors, conflicts
    ] = Field(
        description="Content type guides layout decisions. Choose based on data nature."
    )

    title: str = Field(
        description="Page title - appears in header and link preview (OG tags)"
    )

    data: dict | list[dict] = Field(
        description="Structured data to render. Single entity or list. Nested OK."
    )

    context: str = Field(
        description="Context for the rendering LLM - WHY this data, WHAT user needs"
    )

    images: list[str] | None = Field(
        default=None,
        description="Image URLs. First = primary (OG preview). Full https:// URLs."
    )

    highlight: dict | None = Field(
        default=None,
        description="Fields to emphasize. {'primary': ['price'], 'secondary': ['sku']}"
    )

    actions: list[dict] | None = Field(
        default=None,
        description="Visual action buttons (not interactive in v1)"
    )

    brand: dict | None = Field(
        default=None,
        description="Optional brand overrides: {'primary_color': '#0066cc', 'logo_url': '...'}"
    )
```

### Output Schema

```python
class RichOutputResult(BaseModel):
    """Result from rich output generation."""

    success: bool = Field(description="Whether generation succeeded")

    url: str | None = Field(
        default=None,
        description="Public URL to rendered page. User clicks -> browser renders."
    )

    filename: str | None = Field(
        default=None,
        description="Storage filename for reference/debugging"
    )

    summary: str = Field(
        description="Text summary for chat. Always include with URL."
    )

    preview_image: str | None = Field(
        default=None,
        description="Primary image URL for OG preview"
    )

    error: str | None = Field(
        default=None,
        description="Error message if generation failed"
    )
```

### Tool Implementation

```python
"""
Location: agents/src/autifyme_agents/tools/rich_output/tool.py
"""

from langchain.tools import StructuredTool

def create_rich_output_tool() -> StructuredTool:
    """Create the generate_rich_output tool.

    Returns:
        StructuredTool with full schema for LLM introspection.
    """

    async def _generate_rich_output_impl(
        content_type: str,
        title: str,
        data: dict | list,
        context: str,
        images: list[str] | None = None,
        highlight: dict | None = None,
        actions: list[dict] | None = None,
        brand: dict | None = None,
    ) -> dict:
        """Generate rich HTML output from structured data.

        Flow:
        1. Validate and sanitize input
        2. Prepare prompt for HTML generator LLM
        3. Generate HTML with OG tags
        4. Upload to Supabase Storage
        5. Return URL and summary
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
- Hierarchical data (families, trees)
- Comparisons between entities
- Complex validation errors
- Large query results
- Preview of pending changes

DO NOT USE WHEN:
- Simple confirmations
- Short lists (< 5 items)
- Conversational responses

The URL returned renders as a webpage when clicked.
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
You are an expert HTML/CSS generator that creates beautiful, functional web pages from structured data.

## Your Role
Transform JSON data into self-contained HTML pages optimized for mobile viewing.
You make ALL visual and layout decisions based on the data structure and context provided.

## Output Requirements

### Technical Constraints
- Generate ONLY the HTML code - no explanations, no markdown, no wrapper
- Single self-contained file (inline CSS, no external dependencies)
- Mobile-first responsive design
- Fast loading (no heavy frameworks, no JavaScript)
- Valid HTML5
- Start with <!DOCTYPE html>, end with </html>

### Document Structure
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <!-- OG tags for WhatsApp/social preview -->
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{auto-generated summary}">
    <meta property="og:image" content="{first image URL or placeholder}">
    <meta property="og:type" content="website">

    <title>{title}</title>
    <style>
        /* All CSS inline here - mobile-first */
    </style>
</head>
<body>
    <!-- Content here -->
</body>
</html>
```

### Visual Design System

**Layout:**
- Mobile-first (design for 375px width, scale up)
- Maximum content width: 800px, centered
- Generous padding: 16px mobile, 24px desktop

**Typography:**
- System font stack: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
- Base size: 16px (never smaller for readability)
- Line height: 1.5 for body, 1.2 for headings
- Clear hierarchy: h1 (24px), h2 (20px), h3 (18px)

**Colors (Default Palette):**
- Background: #ffffff (white)
- Surface: #f8f9fa (light gray for cards)
- Text primary: #212529 (near black)
- Text secondary: #6c757d (gray)
- Primary accent: #0d6efd (blue)
- Success: #198754 (green)
- Warning: #ffc107 (amber)
- Error: #dc3545 (red)
- Border: #dee2e6 (light gray)

**Spacing Scale (8px base):**
- xs: 4px
- sm: 8px
- md: 16px
- lg: 24px
- xl: 32px

**Components:**
- Cards: White background, 8px border-radius, subtle shadow
- Buttons: 44px min height (touch-friendly), 8px border-radius
- Tables: Zebra striping, sticky headers on scroll
- Images: max-width: 100%, maintain aspect ratio

### Content Type Layouts

**catalog:**
- Grid of cards (1 col mobile, 2-3 cols desktop)
- Card: Image (if available), title, 2-3 key attributes
- Show count in header: "47 products"

**detail:**
- Hero image at top (full width)
- Title and description
- Attributes in clean table or definition list
- Related items at bottom if provided

**comparison:**
- Sticky header row with entity names/images
- Rows for each attribute being compared
- Highlight differences with background color
- Works as scrollable table on mobile

**table:**
- Full-width responsive table
- Sticky header
- Zebra striping for readability
- Horizontal scroll on mobile if needed

**hierarchy:**
- Indented tree structure
- Visual connectors (optional)
- Expand/collapse indicators (visual only, not functional)
- Clear parent-child relationship

**report:**
- Summary cards at top (big numbers)
- Sections with headers
- Clean data presentation

**timeline:**
- Vertical timeline with line
- Date/time on one side, content on other
- Most recent first (or chronological based on context)

**preview:**
- Clear "PREVIEW" badge/banner at top
- Grouped by entity type
- Show what will be created/modified
- Summary counts

**error:**
- Red accent color
- Error icon per item
- Field name + error message + suggestion if available
- Clear visual separation between errors

### Image Handling
- Always include alt text (generate from context if not provided)
- Use loading="lazy" for images below fold
- If image URL provided: <img src="..." alt="..." loading="lazy">
- If no images: Use colored placeholder or relevant icon
- Max width 100%, maintain aspect ratio

### Empty States
- Never show blank page
- Friendly message: "No items found"
- Subtle icon or illustration

### Large Data (20+ items)
- Show all items (let browser scroll)
- Or logical grouping with section headers
- Summary count at top: "Showing 47 items"

### Highlighted Fields
- primary: Larger font, bold, prominent position
- secondary: Normal size, visible but not dominant
- Use highlight info to prioritize what user sees first

### Accessibility
- Semantic HTML (header, main, section, article, nav)
- Alt text on all images
- Sufficient color contrast (WCAG AA)
- Logical heading hierarchy (h1 -> h2 -> h3)

## Input Format

You will receive JSON:
```json
{
  "content_type": "catalog|detail|comparison|table|hierarchy|report|timeline|preview|error",
  "title": "Page title",
  "data": { ... } or [ ... ],
  "context": "Why this page exists, what user needs",
  "images": ["url1", "url2", ...],
  "highlight": {"primary": ["field1"], "secondary": ["field2"]},
  "actions": [{"label": "Approve", "style": "primary"}],
  "brand": {"primary_color": "#hex", "logo_url": "..."}
}
```

## Output Format

Return ONLY the complete HTML code.
- No markdown code fences
- No explanations before or after
- Start with: <!DOCTYPE html>
- End with: </html>
"""
```

---

## Integration Points

### Supabase Storage

**Existing Infrastructure:**
```python
# Already available in SupabaseStorageClient
client.storage.from_("assets").upload(
    path=storage_path,
    file=html_content.encode("utf-8"),
    file_options={"content-type": "text/html; charset=utf-8"},
)

url = client.storage.from_("assets").get_public_url(storage_path)
```

**New Method (Optional Helper):**
```python
async def upload_html_output(
    self,
    html_content: str,
    filename: str,
    folder: str = "outputs",
    bucket: str = "assets",
) -> dict[str, Any]:
    """Upload HTML content to storage and return public URL.

    Args:
        html_content: Complete HTML string
        filename: Output filename (should include .html)
        folder: Folder within bucket
        bucket: Storage bucket name

    Returns:
        {"success": True, "url": "...", "storage_path": "..."}
    """
    storage_path = f"{folder}/{filename}"

    client = self._ensure_client()
    client.storage.from_(bucket).upload(
        path=storage_path,
        file=html_content.encode("utf-8"),
        file_options={"content-type": "text/html; charset=utf-8"},
    )

    url = client.storage.from_(bucket).get_public_url(storage_path)

    return {
        "success": True,
        "url": url,
        "storage_path": storage_path,
    }
```

### Agent Tool Registration

```python
# In specialist tool configuration
from autifyme_agents.tools.rich_output import create_rich_output_tool

# Add to any specialist that needs rich output capability
specialist_tools = [
    # ... existing tools ...
    create_rich_output_tool(),
]
```

### WhatsApp Response Integration

The tool returns a URL that agents include in their response. No special WhatsApp handling needed - it's just a URL in the message text.

```python
# Agent response pattern
f"""Here's the {result['summary']}

{result['url']}

Please review and let me know if you'd like any changes."""
```

---

## Security Considerations

### Input Sanitization

**XSS Prevention:**
```python
def sanitize_for_html(data: Any) -> Any:
    """Sanitize data before passing to HTML generator.

    Prevents XSS by escaping HTML special characters in string values.
    """
    if isinstance(data, str):
        return html.escape(data)
    elif isinstance(data, dict):
        return {k: sanitize_for_html(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_html(item) for item in data]
    else:
        return data
```

**Image URL Validation:**
```python
def validate_image_url(url: str) -> bool:
    """Validate image URL is safe to include.

    - Must be HTTPS
    - Must be from allowed domains or Supabase storage
    """
    parsed = urlparse(url)

    if parsed.scheme != "https":
        return False

    allowed_domains = [
        "supabase.co",
        # Add other trusted image CDNs
    ]

    return any(parsed.netloc.endswith(domain) for domain in allowed_domains)
```

### Storage Security

**Public Bucket Considerations:**
- HTML files are publicly accessible via URL
- URLs are not guessable (contain UUID)
- No sensitive data should be in HTML (by design - it's for user display)
- Consider signed URLs if confidentiality needed (future enhancement)

**Content-Type Header:**
- Always set `text/html; charset=utf-8`
- Prevents browser MIME-type sniffing issues

### Rate Limiting

```python
# Implement at tool level
MAX_GENERATIONS_PER_MINUTE = 10
MAX_HTML_SIZE_BYTES = 500_000  # 500KB

async def _generate_rich_output_impl(...):
    # Check rate limit
    if not await rate_limiter.allow("rich_output", thread_id):
        return {
            "success": False,
            "error": "Rate limit exceeded. Please wait before generating more outputs."
        }

    # Check output size
    if len(html_content) > MAX_HTML_SIZE_BYTES:
        return {
            "success": False,
            "error": f"Generated HTML exceeds size limit ({MAX_HTML_SIZE_BYTES} bytes)"
        }
```

---

## Edge Cases

### Empty Data

```python
# Input
data = []

# LLM generates appropriate empty state
"""
<div class="empty-state">
    <svg><!-- empty icon --></svg>
    <h2>No items found</h2>
    <p>There are no items matching your criteria.</p>
</div>
"""
```

### Very Large Data (100+ items)

```python
# Context instructs LLM
context = "Large dataset (156 products). Show all but consider performance."

# LLM may:
# - Group by category with section headers
# - Use lazy loading for images
# - Show summary at top with total count
```

### Missing Images

```python
# LLM generates placeholder
"""
<div class="image-placeholder" style="background: #e9ecef;">
    <svg><!-- product icon --></svg>
</div>
"""
```

### Mixed Data Types

```python
# LLM adapts based on structure analysis
data = {
    "summary": {...},      # Renders as cards
    "products": [...],     # Renders as grid
    "errors": [...]        # Renders as error list
}
```

### Generation Failure

```python
# Graceful degradation
if not html_content or generation_failed:
    return {
        "success": False,
        "url": None,
        "summary": "Could not generate visual output. Here's the data in text format:\n...",
        "error": "HTML generation failed"
    }
```

### Malformed HTML from LLM

```python
def validate_html(content: str) -> bool:
    """Basic HTML validation."""
    return (
        content.strip().startswith("<!DOCTYPE html>") and
        content.strip().endswith("</html>") and
        "<head>" in content and
        "<body>" in content
    )

# If invalid, retry once or fall back to text
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/tools/rich_output/test_tool.py

class TestRichOutputTool:
    """Unit tests for rich output generation."""

    async def test_catalog_generation(self):
        """Test catalog content type generates valid output."""
        result = await generate_rich_output(
            content_type="catalog",
            title="Test Catalog",
            data=[{"name": "Product 1"}, {"name": "Product 2"}],
            context="Test catalog generation"
        )

        assert result["success"] is True
        assert result["url"] is not None
        assert "2 items" in result["summary"].lower()

    async def test_empty_data_handling(self):
        """Test empty data generates appropriate empty state."""
        result = await generate_rich_output(
            content_type="table",
            title="Empty Table",
            data=[],
            context="Test empty handling"
        )

        assert result["success"] is True
        # HTML should contain empty state, not be blank

    async def test_xss_prevention(self):
        """Test XSS attack vectors are sanitized."""
        malicious_data = {
            "name": "<script>alert('xss')</script>",
            "description": "Test <img src=x onerror=alert('xss')>"
        }

        result = await generate_rich_output(
            content_type="detail",
            title="XSS Test",
            data=malicious_data,
            context="Security test"
        )

        # Verify scripts are escaped
        html = await fetch_html(result["url"])
        assert "<script>" not in html
        assert "onerror=" not in html

    async def test_large_data_performance(self):
        """Test performance with large datasets."""
        large_data = [{"id": i, "name": f"Item {i}"} for i in range(100)]

        start = time.time()
        result = await generate_rich_output(
            content_type="catalog",
            title="Large Catalog",
            data=large_data,
            context="Performance test"
        )
        duration = time.time() - start

        assert result["success"] is True
        assert duration < 10  # Should complete within 10 seconds
```

### Integration Tests

```python
# tests/integration/test_rich_output_e2e.py

class TestRichOutputIntegration:
    """End-to-end tests with real Supabase."""

    async def test_full_flow_catalog(self):
        """Test complete flow: generate -> upload -> access."""
        result = await generate_rich_output(
            content_type="catalog",
            title="Integration Test Catalog",
            data=[...],
            context="E2E test"
        )

        # Verify URL is accessible
        response = await httpx.get(result["url"])
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Verify HTML renders (basic check)
        assert "<!DOCTYPE html>" in response.text
        assert "Integration Test Catalog" in response.text

    async def test_og_tags_present(self):
        """Test OG tags are present for link preview."""
        result = await generate_rich_output(...)

        html = await fetch_html(result["url"])
        assert 'property="og:title"' in html
        assert 'property="og:description"' in html
```

### Agent Integration Tests

```python
# tests/integration/test_agent_rich_output.py

class TestAgentRichOutputUsage:
    """Test agents using rich output tool correctly."""

    async def test_pm_uses_rich_output_for_large_catalog(self):
        """PM should use rich output when cataloging 10+ variants."""
        response = await pm.process(
            "Create Jarvis Guitar family with Standard, Pro, Elite models, "
            "each in Black, Sunburst, Red, White finishes"
        )

        # Should include URL in response
        assert "http" in response
        assert "supabase" in response

        # Should include summary
        assert "12 variants" in response.lower() or "preview" in response.lower()

    async def test_pm_uses_text_for_simple_confirmation(self):
        """PM should use text for simple operations."""
        response = await pm.process(
            "Add one Red variant to the existing Jarvis Standard"
        )

        # Should NOT include rich output URL for simple addition
        # (This tests agent reasoning, not just tool capability)
```

---

## Implementation Phases

### Phase 1: Core Tool (MVP)

**Deliverables:**
- [ ] `RichOutputInput` and `RichOutputResult` schemas
- [ ] HTML Generator LLM integration (Haiku)
- [ ] System prompt for HTML generation
- [ ] Supabase Storage upload
- [ ] Basic tool implementation
- [ ] Unit tests for core functionality

**Timeline:** 3-4 days

**Success Criteria:**
- Can generate HTML from JSON data
- HTML renders correctly in browser
- URL is publicly accessible
- Basic content types work (catalog, detail, error)

### Phase 2: Agent Integration

**Deliverables:**
- [ ] Add tool to PM and relevant specialists
- [ ] Update agent prompts with protocol
- [ ] Add canonical examples to prompts
- [ ] Integration tests with agents

**Timeline:** 2-3 days

**Success Criteria:**
- Agents autonomously decide when to use rich output
- Agents include both URL and summary in responses
- Users can click URL and see rendered content

### Phase 3: Refinement

**Deliverables:**
- [ ] OG tag optimization for better previews
- [ ] Brand customization support
- [ ] Additional content types (timeline, report)
- [ ] Performance optimization
- [ ] Rate limiting

**Timeline:** 2-3 days

**Success Criteria:**
- WhatsApp shows rich link preview
- All content types work correctly
- Performance meets targets (< 5s generation)

### Phase 4: Advanced Features (Future)

**Potential Enhancements:**
- [ ] Signed URLs for sensitive data
- [ ] PDF generation option
- [ ] Image generation (visual cards as images)
- [ ] Interactive elements (JavaScript)
- [ ] Template caching for common layouts
- [ ] Analytics (view tracking)

---

## File Structure

```
agents/src/autifyme_agents/tools/rich_output/
    __init__.py
    tool.py                 # Main tool implementation
    schemas.py              # Pydantic input/output schemas
    html_generator.py       # LLM interaction for HTML generation
    prompts/
        __init__.py
        system_prompt.py    # HTML generator system prompt
    utils/
        __init__.py
        sanitization.py     # XSS prevention, input sanitization
        validation.py       # HTML validation, URL validation

docs/architecture/tools/
    RICH_OUTPUT_ENGINE_DESIGN.md  # This document
```

---

## Open Questions

1. **Cleanup Policy:** Should old HTML files be auto-deleted after X days? Or keep indefinitely (storage is cheap)?

2. **Caching:** If same data generates same HTML, should we cache/dedupe? Probably overkill for v1.

3. **Analytics:** Do we want to track when users view generated pages? Could inform agent learning.

4. **Offline Support:** Should generated HTML work offline? Currently images are URLs (need internet).

5. **Branding:** How much brand customization is needed in v1? Logo? Colors? Full themes?

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Generation time | < 5 seconds | LangSmith trace |
| HTML size | < 200KB typical | Storage metrics |
| Agent adoption | 80%+ large outputs use tool | Trace analysis |
| User engagement | Higher than text links | Click tracking (future) |
| Error rate | < 1% generation failures | Error logging |

---

## References

- [Supabase Storage Docs](https://supabase.com/docs/guides/storage)
- [Open Graph Protocol](https://ogp.me/)
- [WhatsApp Link Preview](https://developers.facebook.com/docs/sharing/webmasters/)
- [IMAGE_STUDIO_TOOL.md](./IMAGE_STUDIO_TOOL.md) - Similar tool pattern
- [UNIVERSAL_DATA_ENGINE_DESIGN.md](../core/UNIVERSAL_DATA_ENGINE_DESIGN.md) - Tool design patterns

---

**Version History:**
- v1.0.0 (2025-12-19): Initial design document
