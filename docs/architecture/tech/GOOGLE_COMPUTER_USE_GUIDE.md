# Google Computer Use - Browser Automation Guide

**Status:** ✅ Implemented
**Date:** 2025-10-30
**Model:** gemini-2.5-computer-use-preview-10-2025

---

## Executive Summary

Gemini 2.5 Computer Use enables building browser automation agents that "see" screenshots and "act" through UI interactions. The model achieves 70% accuracy on Online-Mind2Web benchmark with lower latency than competitors, making it ideal for web scraping, form automation, UI testing, and agentic workflows.

**Key Capabilities:**
- Screenshot-based visual understanding
- 12 UI action types (click, type, scroll, navigate, etc.)
- Built-in safety checks for high-risk actions
- Optimized for web browsers and Android UIs
- Natural language task execution

---

## Architecture

### Three-Component System

**1. Computer Use Model**
- Analyzes screenshots visually
- Generates structured UI actions
- Provides reasoning for decisions
- Flags high-risk actions for approval

**2. ActionExecutor** (Your Implementation)
- Browser automation client (Playwright/Selenium)
- Executes model-generated actions
- Captures screenshots
- Manages browser state

**3. Agent Loop**
- Screenshot → Model → Actions → Execute → Screenshot
- Continues until task complete or max steps reached
- Handles safety confirmations
- Maintains action history

---

## Model Specifications

| Attribute | Value |
|-----------|-------|
| **Model ID** | `gemini-2.5-computer-use-preview-10-2025` |
| **Input Tokens** | 128,000 |
| **Output Tokens** | 64,000 |
| **Viewport** | 1440x900 recommended |
| **Coordinate System** | Normalized 0-999 (converted to pixels) |
| **Release** | October 2025 (Preview) |
| **Benchmarks** | 70% accuracy on Online-Mind2Web |

---

## Supported Actions

### 12 UI Action Types

| Action | Purpose | Parameters |
|--------|---------|------------|
| **open_web_browser** | Launch browser | None |
| **click_at** | Mouse click | `x`, `y` (0-999) |
| **type_text_at** | Text input | `x`, `y`, `text`, `clear_existing`, `press_enter` |
| **scroll_document** | Page scroll | `direction` (up/down/left/right), `magnitude` |
| **scroll_at** | Element scroll | `x`, `y`, `direction`, `magnitude` |
| **navigate** | URL navigation | `url` |
| **hover_at** | Mouse hover | `x`, `y` |
| **go_back** | Browser back | None |
| **go_forward** | Browser forward | None |
| **search** | Open search engine | None |
| **key_combination** | Keyboard shortcuts | `keys` (e.g., "Control+C") |
| **drag_and_drop** | Drag element | `from_x`, `from_y`, `to_x`, `to_y` |
| **wait_5_seconds** | Pause execution | None |

---

## Implementation Guide

### Step 1: Install Computer Use Extension

**Note:** Computer Use is an optional extension with heavy dependencies (~600MB). Install only when browser automation is needed.

```bash
# Navigate to extension directory
cd extensions/google_computer_use

# Install with Playwright support (recommended)
uv pip install -e ".[playwright]"
playwright install chromium

# This installs:
# - google-generativeai (base SDK)
# - playwright (browser automation, ~200MB)
# - chromium (browser binary, ~400MB)
```

### Step 2: Create ActionExecutor

```python
# Import from extension (after installing with Step 1)
from google_computer_use.playwright_executor import PlaywrightExecutor

async def main():
    # Initialize executor
    executor = PlaywrightExecutor(
        viewport_width=1440,
        viewport_height=900,
        headless=False  # Set True for production
    )
    await executor.initialize()

    # Use executor...

    # Cleanup
    await executor.cleanup()
```

### Step 3: Create Computer Use Agent

```python
from google_computer_use import get_computer_use_agent
import os

# Create agent
agent = get_computer_use_agent(
    action_executor=executor,
    api_key=os.getenv("GOOGLE_API_KEY"),  # Or None to auto-read
    system_instruction="You are a careful browser automation agent. "
                      "Always verify information before submitting forms.",
    auto_confirm=False  # Require manual approval for high-risk actions
)
```

### Step 4: Execute Tasks

```python
# Execute a browser automation task
result = await agent.execute_task(
    goal="Search for 'Python tutorials' on Google and click the first result",
    max_steps=10,
    initial_url="https://google.com"
)

# Check result
if result["success"]:
    print(f"Task completed in {result['steps_taken']} steps")
    print(f"Final URL: {result['final_state'].url}")
else:
    print(f"Task failed: {result['error']}")

# Access action history
for action in result["actions"]:
    print(f"{action.action_type}: {action.reasoning}")
```

---

## Usage Examples

### Example 1: Web Search and Navigation

```python
from google_computer_use import get_computer_use_agent
from google_computer_use.playwright_executor import PlaywrightExecutor
import asyncio

async def search_example():
    async with PlaywrightExecutor(headless=False) as executor:
        agent = get_computer_use_agent(action_executor=executor)

        result = await agent.execute_task(
            goal="Go to Google, search for 'Gemini API documentation', "
                 "and open the first result",
            max_steps=15,
            initial_url="https://google.com"
        )

        if result["success"]:
            print(f"Successfully navigated to: {result['final_state'].url}")
            print(f"Page title: {result['final_state'].title}")

asyncio.run(search_example())
```

### Example 2: Form Automation

```python
async def form_automation_example():
    async with PlaywrightExecutor() as executor:
        agent = get_computer_use_agent(
            action_executor=executor,
            system_instruction="Fill forms carefully and verify before submitting. "
                              "Ask for confirmation before final submission."
        )

        result = await agent.execute_task(
            goal="Fill out the contact form with: "
                 "Name: John Doe, Email: john@example.com, "
                 "Message: I'm interested in your services. "
                 "Then submit the form.",
            max_steps=20,
            initial_url="https://example.com/contact"
        )

        print(f"Form submission: {'Success' if result['success'] else 'Failed'}")

asyncio.run(form_automation_example())
```

### Example 3: Data Extraction

```python
async def data_extraction_example():
    async with PlaywrightExecutor() as executor:
        agent = get_computer_use_agent(action_executor=executor)

        result = await agent.execute_task(
            goal="Navigate to the pricing page and extract all plan names "
                 "and their monthly prices. Click through any dropdowns needed.",
            max_steps=25,
            initial_url="https://example.com"
        )

        # Model provides reasoning in text responses
        for action in result["actions"]:
            if action.reasoning:
                print(f"Step: {action.reasoning}")

asyncio.run(data_extraction_example())
```

### Example 4: E-commerce Workflow

```python
async def ecommerce_example():
    async with PlaywrightExecutor() as executor:
        agent = get_computer_use_agent(
            action_executor=executor,
            auto_confirm=False,  # Require confirmation for purchases
            confirmation_callback=lambda action: (
                input(f"Confirm {action.action_type}? (y/n): ").lower() == 'y'
            )
        )

        result = await agent.execute_task(
            goal="Search for 'wireless headphones', filter by price under $100, "
                 "select the top-rated product, add to cart, and proceed to checkout "
                 "(but do not complete purchase)",
            max_steps=30,
            initial_url="https://example-store.com"
        )

asyncio.run(ecommerce_example())
```

### Example 5: UI Testing

```python
async def ui_testing_example():
    """Use Computer Use for automated UI testing."""
    async with PlaywrightExecutor() as executor:
        agent = get_computer_use_agent(action_executor=executor)

        test_cases = [
            {
                "goal": "Click the Sign Up button and verify the registration form appears",
                "expected_url_contains": "register",
            },
            {
                "goal": "Navigate to the About page and verify it contains 'Our Mission'",
                "expected_title_contains": "About",
            },
        ]

        results = []
        for test in test_cases:
            result = await agent.execute_task(
                goal=test["goal"],
                max_steps=10,
                initial_url="https://example.com"
            )
            results.append({
                "test": test["goal"],
                "passed": result["success"],
                "steps": result["steps_taken"],
            })

        # Generate test report
        for r in results:
            status = "✓ PASS" if r["passed"] else "✗ FAIL"
            print(f"{status}: {r['test']} ({r['steps']} steps)")

asyncio.run(ui_testing_example())
```

---

## Safety Features

### Built-in Safety Checks

The model includes internal safety system that evaluates each proposed action:

**Safety Decisions:**
- `regular` — Action is safe, execute normally
- `require_confirmation` — High-risk action, requires user approval

**High-Risk Actions Include:**
- Accepting terms and conditions
- Completing financial transactions
- Solving CAPTCHAs
- Bypassing security measures
- Modifying system settings

### Handling Confirmations

**Option 1: Manual Approval (Recommended)**
```python
agent = get_computer_use_agent(
    action_executor=executor,
    auto_confirm=False,  # Default
    confirmation_callback=lambda action: (
        input(f"Approve {action.action_type}? (y/n): ").lower() == 'y'
    )
)
```

**Option 2: Auto-Approve (Use with Caution)**
```python
agent = get_computer_use_agent(
    action_executor=executor,
    auto_confirm=True  # Automatically approve all actions
)
```

**Option 3: Exclude Risky Actions**
```python
result = await agent.execute_task(
    goal="...",
    excluded_actions=[
        "drag_and_drop",
        "key_combination"
    ]
)
```

---

## Use Cases for AutifyME

### 1. WhatsApp Business Automation
- Extract product information from supplier websites
- Monitor competitor pricing automatically
- Scrape product specifications for cataloging
- Verify product availability on vendor sites

### 2. Marketing Platform Integration
- Automate social media post scheduling
- Extract analytics from marketing dashboards
- Generate reports from ad platform UIs
- Monitor campaign performance across platforms

### 3. Data Collection & Enrichment
- Gather product data from multiple sources
- Enrich product catalogs with web research
- Validate supplier information automatically
- Extract customer reviews and feedback

### 4. Testing & QA
- Automated UI testing for custom dashboards
- Regression testing for web interfaces
- Cross-browser compatibility verification
- User journey simulation and validation

### 5. Workflow Automation
- Multi-step form submissions
- Account creation and configuration
- Data migration between platforms
- Scheduled data exports and backups

---

## Performance Optimization

### Best Practices

**Viewport Configuration:**
```python
# Recommended: 1440x900
executor = PlaywrightExecutor(viewport_width=1440, viewport_height=900)
```

**Step Limits:**
- Simple tasks: 10-15 steps
- Medium complexity: 20-30 steps
- Complex workflows: 40-50 steps
- Maximum: 100 steps (consider breaking into sub-tasks)

**System Instructions:**
```python
# Provide clear context and constraints
system_instruction = """
You are a browser automation agent for e-commerce workflows.

Guidelines:
- Verify information carefully before form submissions
- Use search filters to narrow results efficiently
- Prefer clicking specific elements over scrolling extensively
- Report progress clearly in your reasoning
- Ask for confirmation before checkout/payment steps
"""
```

**Error Handling:**
```python
result = await agent.execute_task(
    goal="...",
    max_steps=20
)

if not result["success"]:
    if result.get("error") == "Max steps (20) reached":
        # Task too complex, break into smaller sub-tasks
        print("Task needs to be decomposed")
    else:
        # Handle execution error
        print(f"Error: {result['error']}")
```

---

## Custom ActionExecutor Implementation

### Minimal Executor Template

```python
from google_computer_use import ActionExecutor, BrowserState, ComputerAction

class CustomExecutor(ActionExecutor):
    """Custom browser automation executor."""

    async def execute_action(self, action: ComputerAction) -> bool:
        """Execute UI action using your automation framework."""
        # Convert normalized coordinates
        x, y = self.normalize_coordinates(
            action.args.get("x", 0),
            action.args.get("y", 0)
        )

        # Implement action execution
        # ...

        return True

    async def get_screenshot(self) -> bytes:
        """Capture screenshot as PNG bytes."""
        # Capture and return screenshot
        # ...
        return screenshot_bytes

    async def get_state(self) -> BrowserState:
        """Get current browser state."""
        return BrowserState(
            screenshot=await self.get_screenshot(),
            url="...",
            title="...",
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
        )
```

---

## Limitations & Considerations

### Current Limitations

**Browser-Focused:**
- Optimized for web browsers
- Android UI support (strong performance on AndroidWorld)
- **Not** optimized for desktop OS-level control

**Authentication:**
- Cannot solve CAPTCHAs (safety restriction)
- May struggle with complex authentication flows
- Multi-factor authentication requires manual intervention

**Dynamic Content:**
- Heavy JavaScript/React apps may need wait times
- Infinite scroll requires multiple scroll actions
- Real-time updates may miss timing windows

**Accuracy:**
- 70% success rate on benchmark (excellent but not perfect)
- Complex UIs may require multiple attempts
- Ambiguous elements may cause confusion

### When to Use Computer Use

**✅ Good Fit:**
- Repetitive web form filling
- Data extraction from structured sites
- UI testing and verification
- Multi-step workflow automation
- Simple navigation and search tasks

**❌ Not Ideal:**
- Real-time trading/bidding (timing critical)
- CAPTCHA-protected sites
- Sites with aggressive bot detection
- Tasks requiring perfect accuracy (financial)
- Desktop application automation

---

## Cost Analysis

### Pricing (Google AI Gemini API)

| Component | Cost |
|-----------|------|
| **Input** | $X per 1M tokens (128K limit) |
| **Output** | $Y per 1M tokens (64K limit) |
| **Typical Task** | ~10-50K tokens (screenshots + actions) |

**Cost Optimization:**
- Use headless mode (lower overhead)
- Set appropriate max_steps limits
- Break complex tasks into subtasks
- Cache screenshots when possible
- Use system instructions to guide efficiency

---

## Integration Checklist

### Prerequisites

```bash
# 1. Install dependencies
uv pip install google-generativeai playwright
playwright install chromium

# 2. Set API key
export GOOGLE_API_KEY=your_api_key_here
```

### Implementation Steps

**1. Choose/Create ActionExecutor**
```python
# Use built-in Playwright executor
from google_computer_use.playwright_executor import PlaywrightExecutor
executor = PlaywrightExecutor()

# Or implement custom executor
# executor = MyCustomExecutor()
```

**2. Initialize Agent**
```python
from google_computer_use import get_computer_use_agent

agent = get_computer_use_agent(
    action_executor=executor,
    system_instruction="...",
    auto_confirm=False
)
```

**3. Execute Tasks**
```python
result = await agent.execute_task(
    goal="Natural language task description",
    max_steps=20,
    initial_url="https://example.com"
)
```

**4. Handle Results**
```python
if result["success"]:
    # Task completed
    print(f"Final state: {result['final_state']}")
else:
    # Task failed
    print(f"Error: {result['error']}")
```

---

## Reference Links

- [Computer Use API Docs](https://ai.google.dev/gemini-api/docs/computer-use)
- [Gemini 2.5 Computer Use Blog](https://blog.google/technology/google-deepmind/gemini-computer-use-model/)
- [Vertex AI Computer Use](https://cloud.google.com/vertex-ai/generative-ai/docs/computer-use)
- [Playwright Documentation](https://playwright.dev/python/)

---

## Quick Reference

### Import Paths

```python
# Core agent (from extension)
from google_computer_use import (
    get_computer_use_agent,
    ComputerUseAgent,
    ActionExecutor,
    ActionType,
    ComputerAction,
    BrowserState,
)

# Playwright executor (from extension)
from google_computer_use.playwright_executor import PlaywrightExecutor
```

### Model Name

```python
model = "gemini-2.5-computer-use-preview-10-2025"
```

### Essential Parameters

```python
agent.execute_task(
    goal="Task description",      # Required
    max_steps=20,                  # Default: 20
    excluded_actions=[...],        # Optional
    initial_url="https://..."      # Optional
)
```
