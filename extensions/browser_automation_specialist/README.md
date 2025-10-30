# Browser Automation Specialist

Autonomous browser automation agent using **Google Gemini 2.5 Computer Use** model with Intelligence-First design principles.

---

## Overview

This specialist wraps the [google_computer_use](../google_computer_use) extension with autonomous reasoning capabilities:

- **Sees pages** through screenshots with visual understanding
- **Reasons dynamically** about goals and adapts execution
- **Self-reviews** actions and iterates when needed
- **Extracts data** autonomously with comprehensive coverage
- **Handles failures** gracefully with fallback strategies

**Model:** `gemini-2.5-computer-use-preview-10-2025` (70% accuracy on Online-Mind2Web benchmark)

---

## Installation

### Prerequisites

1. **Install google_computer_use extension:**
   ```bash
   cd extensions/google_computer_use
   uv pip install -e ".[playwright]"
   playwright install chromium
   ```

2. **Set API key:**
   ```bash
   # Add to .env file in AutifyME root
   GOOGLE_API_KEY=your_api_key_here
   ```

3. **Verify installation:**
   ```bash
   uv run python -c "from google_computer_use import get_computer_use_agent; print('✓ Ready')"
   ```

---

## Quick Start

```python
import asyncio
from browser_automation_specialist import create_browser_specialist

async def main():
    # Create specialist (headless=False to watch execution)
    specialist = create_browser_specialist(headless=False)
    await specialist.initialize()

    # Execute autonomous task
    result = await specialist.execute_task(
        goal="Go to pavisha.com and extract comprehensive company profile",
        max_steps=30,
        initial_url="https://www.pavisha.com"
    )

    print(f"Success: {result['success']}")
    print(f"Steps taken: {result['steps_taken']}")
    print(f"Final URL: {result['final_url']}")

    # Cleanup
    await specialist.cleanup()

asyncio.run(main())
```

---

## Architecture

### Components

**[specialist.py](specialist.py)** - Core specialist class
- `BrowserAutomationSpecialist`: Main class wrapping ComputerUseAgent
- `create_browser_specialist()`: Factory function
- Handles initialization, execution, and cleanup

**[system_prompt.txt](system_prompt.txt)** - Autonomous behavior prompt
- Intelligence-First principles
- Self-review and adaptation strategies
- Safety guidelines

**[examples/](examples/)** - Test scenarios
- Company profile extraction
- Multi-page navigation
- Form interaction analysis

### Architecture Diagram

```
BrowserAutomationSpecialist
    ↓
ComputerUseAgent (google_computer_use)
    ↓
PlaywrightExecutor
    ↓
Chromium Browser
```

---

## Usage Patterns

### 1. Data Extraction

```python
result = await specialist.execute_task(
    goal="""Extract complete product information from competitor site:
    - Product name and SKU
    - Price and availability
    - Specifications and features
    - Customer reviews summary

    Scroll through entire page to ensure comprehensive extraction.""",
    max_steps=40,
    initial_url="https://competitor.com/product/12345"
)
```

### 2. Multi-Step Workflows

```python
result = await specialist.execute_task(
    goal="""Research company profile:
    1. Navigate to About page
    2. Extract company history and mission
    3. Go to Services page
    4. List all services with descriptions
    5. Find contact information

    Return structured profile with confidence assessment.""",
    max_steps=50
)
```

### 3. UI Analysis

```python
result = await specialist.execute_task(
    goal="""Analyze website navigation structure:
    - Identify main menu items and hierarchy
    - Find all call-to-action buttons
    - Check if contact form is present
    - Note any CAPTCHAs or auth requirements

    Do NOT interact - just analyze structure.""",
    max_steps=20,
    initial_url="https://example.com"
)
```

### 4. Safety-Constrained Tasks

```python
result = await specialist.execute_task(
    goal="Extract pricing information from pricing page",
    max_steps=20,
    initial_url="https://example.com/pricing",
    excluded_actions=["key_combination", "drag_and_drop"]  # Extra safety
)
```

---

## Configuration Options

### Specialist Initialization

```python
specialist = create_browser_specialist(
    headless=True,           # Run without visible browser
    viewport_width=1440,     # Browser width (default 1440)
    viewport_height=900,     # Browser height (default 900)
    auto_confirm=True,       # Auto-approve high-risk actions
)
```

### Task Execution

```python
result = await specialist.execute_task(
    goal="Natural language task description",
    max_steps=30,            # Maximum actions to take
    initial_url=None,        # Starting URL (optional)
    excluded_actions=None,   # Actions to exclude (e.g., ["key_combination"])
)
```

### Result Format

```python
{
    "success": bool,              # Task completed successfully
    "steps_taken": int,           # Number of actions executed
    "final_url": str,             # Final page URL
    "final_title": str,           # Final page title
    "actions_summary": [          # List of actions taken
        "action_type: reasoning",
        ...
    ],
    "error": str | None           # Error message if failed
}
```

---

## Intelligence-First Design

### Autonomous Capabilities

**Dynamic Planning:**
- Analyzes goal and breaks into logical steps
- Adapts strategy based on visual feedback
- Explores alternative paths when blocked

**Visual Reasoning:**
- Examines screenshots before each action
- Verifies actions succeeded by checking visual changes
- Scrolls to see all content before concluding

**Self-Review:**
- Assesses confidence in extracted data
- Flags incomplete or ambiguous information
- Retries with different approach if low confidence

**Graceful Failure:**
- Communicates limitations transparently
- Returns partial results with context
- Suggests alternative approaches when stuck

### Safety Features

**Built-in Safety Checks:**
- Computer Use model evaluates risk for each action
- High-risk actions (CAPTCHAs, financial, auth) require confirmation
- `auto_confirm=True` delegates approval to specialist prompt logic

**Excluded Actions:**
- Can disable specific actions for extra safety
- Common exclusions: `key_combination`, `drag_and_drop`

**Ethical Boundaries:**
- Respects robots.txt and rate limits
- Avoids destructive or irreversible actions
- Stops at authentication barriers

---

## Use Cases

### AutifyME-Specific

**1. Competitor Analysis:**
```python
goal = "Extract competitor product catalog: names, prices, features, compare to our products"
```

**2. Supplier Verification:**
```python
goal = "Verify supplier business registration, certifications, and contact details"
```

**3. Market Research:**
```python
goal = "Analyze pricing strategy: extract all pricing tiers, features, and compare to industry"
```

**4. Content Extraction:**
```python
goal = "Extract all blog posts: titles, dates, summaries, authors - for content intelligence"
```

### General Use Cases

- Web scraping with visual understanding
- Form automation (testing)
- UI testing and verification
- Data extraction from dynamic sites
- Competitive intelligence gathering

---

## Examples

### Test Suite

Run comprehensive test scenarios:

```bash
cd extensions/browser_automation_specialist/examples
uv run python test_pavisha_analysis.py
```

**Includes:**
1. Company profile extraction (comprehensive data)
2. Multi-page navigation and data aggregation
3. Form structure analysis (no submission)

### Custom Test

```python
import asyncio
from browser_automation_specialist import create_browser_specialist

async def custom_test():
    specialist = create_browser_specialist(headless=False)
    await specialist.initialize()

    result = await specialist.execute_task(
        goal="Your autonomous task here",
        max_steps=30
    )

    print(result)
    await specialist.cleanup()

asyncio.run(custom_test())
```

---

## Troubleshooting

### Import Error: google_computer_use not found

```bash
# Install google_computer_use extension
cd extensions/google_computer_use
uv pip install -e ".[playwright]"
playwright install chromium
```

### API Key Error

```bash
# Set in .env file (AutifyME root)
echo "GOOGLE_API_KEY=your_key_here" >> ../../.env
```

### Browser Not Opening (Headless=False)

Check Playwright installation:
```bash
playwright --version
playwright install chromium
```

### Max Steps Reached

Increase `max_steps` parameter:
```python
result = await specialist.execute_task(goal="...", max_steps=50)
```

### Low Accuracy / Wrong Actions

- Refine goal with more specific instructions
- Add visual landmarks ("look for blue button")
- Exclude problematic actions via `excluded_actions`

---

## Limitations

**Current Scope:**
- ✅ Web browsers (primary focus)
- ✅ Screenshot-based reasoning
- ❌ Not optimized for desktop OS control
- ❌ CAPTCHA-solving requires manual intervention
- ❌ Real-time trading (timing-critical tasks)

**Accuracy:**
- 70% success on benchmark (excellent but not perfect)
- Complex UIs may need multiple attempts
- Ambiguous goals can cause confusion

---

## Development

### Customizing System Prompt

Edit [system_prompt.txt](system_prompt.txt) to change autonomous behavior:

```python
# Or provide custom prompt at initialization
specialist = BrowserAutomationSpecialist(
    system_instruction="Your custom instructions here"
)
```

### Adding Safety Rules

```python
# Exclude risky actions
result = await specialist.execute_task(
    goal="...",
    excluded_actions=["key_combination", "drag_and_drop", "navigate"]
)
```

### Debugging

Enable verbose mode by running headful:
```python
specialist = create_browser_specialist(headless=False)
```

Watch browser actions in real-time to understand agent reasoning.

---

## Documentation

**Related Docs:**
- [Google Computer Use Extension](../google_computer_use/README.md)
- [Google Computer Use Guide](../../docs/architecture/tech/GOOGLE_COMPUTER_USE_GUIDE.md) (if available)
- [Multimodal Integration](../../docs/architecture/tech/GOOGLE_AI_MULTIMODAL_INTEGRATION.md) (if available)

**Official Resources:**
- [Google Computer Use API](https://ai.google.dev/gemini-api/docs/computer-use)
- [Gemini 2.5 Documentation](https://ai.google.dev/gemini-api/docs)

---

## License

Same as AutifyME main project

---

## Support

For issues:
1. Check troubleshooting section above
2. Review google_computer_use extension docs
3. Open issue in main AutifyME repository
