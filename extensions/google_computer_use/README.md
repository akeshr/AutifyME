# Google Computer Use Extension for AutifyME

**Optional extension** for browser automation using Gemini 2.5 Computer Use model.

This extension is kept separate from the core AutifyME package to avoid heavy dependencies (Playwright ~200MB, Chromium ~400MB).

---

## Features

- **Browser automation** via natural language
- **Screenshot-based** visual understanding
- **12 UI actions**: click, type, scroll, navigate, drag-drop, etc.
- **Built-in safety checks** for high-risk actions
- **70% accuracy** on Online-Mind2Web benchmark
- **Model:** `gemini-2.5-computer-use-preview-10-2025`

---

## Installation

### Option 1: With Playwright (Recommended)

```bash
# From AutifyME root directory
cd extensions/google_computer_use
uv pip install -e ".[playwright]"

# Install Chromium browser
playwright install chromium
```

### Option 2: With Selenium

```bash
cd extensions/google_computer_use
uv pip install -e ".[selenium]"

# You'll need to implement SeleniumExecutor (similar to PlaywrightExecutor)
```

### Option 3: Minimal (Custom Executor)

```bash
cd extensions/google_computer_use
uv pip install -e .

# Implement your own ActionExecutor
```

---

## Quick Start

```python
from google_computer_use import get_computer_use_agent
from google_computer_use.playwright_executor import PlaywrightExecutor
import asyncio

async def main():
    # Initialize browser automation
    executor = PlaywrightExecutor(
        viewport_width=1440,
        viewport_height=900,
        headless=False  # Show browser for debugging
    )
    await executor.initialize()

    # Create Computer Use agent
    agent = get_computer_use_agent(
        action_executor=executor,
        system_instruction="You are a careful browser automation agent.",
        auto_confirm=False  # Require approval for high-risk actions
    )

    # Execute browser automation task
    result = await agent.execute_task(
        goal="Go to Google and search for 'Python async best practices'",
        max_steps=10,
        initial_url="https://google.com"
    )

    print(f"Success: {result['success']}")
    print(f"Final URL: {result['final_state'].url}")

    # Cleanup
    await executor.cleanup()

asyncio.run(main())
```

---

## Architecture

### Components

**1. ComputerUseAgent** ([agent.py](agent.py))
- Core agent that orchestrates browser automation
- Handles model interaction and action generation
- Manages safety checks and confirmations
- Tracks action history

**2. ActionExecutor** (Abstract Base)
- Interface for browser automation implementations
- Normalizes coordinates (0-999 → pixels)
- Defines action execution contract

**3. PlaywrightExecutor** ([playwright_executor.py](playwright_executor.py))
- Reference implementation using Playwright
- Implements all 12 UI action types
- Production-ready browser automation

### UI Actions Supported

| Action | Purpose | Parameters |
|--------|---------|------------|
| click_at | Mouse click | x, y |
| type_text_at | Text input | x, y, text, clear_existing, press_enter |
| scroll_document | Page scroll | direction, magnitude |
| scroll_at | Element scroll | x, y, direction, magnitude |
| navigate | URL navigation | url |
| hover_at | Mouse hover | x, y |
| go_back/go_forward | Browser navigation | None |
| search | Open search engine | None |
| key_combination | Keyboard shortcuts | keys |
| drag_and_drop | Drag element | from_x, from_y, to_x, to_y |
| wait_5_seconds | Pause | None |
| open_web_browser | Launch browser | None |

---

## Use Cases

### AutifyME-Specific

**1. Product Data Extraction**
```python
result = await agent.execute_task(
    goal="Navigate to competitor product page, extract name, price, "
         "and specifications",
    initial_url="https://competitor.com/products"
)
```

**2. Supplier Verification**
```python
result = await agent.execute_task(
    goal="Verify supplier business registration and extract contact details",
    initial_url="https://supplier-website.com"
)
```

**3. Marketing Platform Automation**
```python
result = await agent.execute_task(
    goal="Schedule social media post for tomorrow 9am",
    excluded_actions=["key_combination"]  # Safety
)
```

**4. UI Testing**
```python
test_cases = [
    "Click 'Add Product' and verify form appears",
    "Fill form with test data and submit",
    "Verify product in catalog list",
]

for test in test_cases:
    result = await agent.execute_task(goal=test, max_steps=10)
    assert result["success"]
```

---

## Safety Features

### Built-in Safety Checks

The model evaluates each action for risk:

- **regular** — Safe, execute normally
- **require_confirmation** — High-risk, needs approval

High-risk actions:
- Accepting terms and conditions
- Financial transactions
- Solving CAPTCHAs
- Security bypasses
- System settings changes

### Handling Confirmations

**Manual Approval (Recommended)**
```python
agent = get_computer_use_agent(
    action_executor=executor,
    auto_confirm=False,
    confirmation_callback=lambda action: (
        input(f"Approve {action.action_type}? (y/n): ").lower() == 'y'
    )
)
```

**Auto-Approve (Use with Caution)**
```python
agent = get_computer_use_agent(
    action_executor=executor,
    auto_confirm=True
)
```

**Exclude Actions**
```python
result = await agent.execute_task(
    goal="...",
    excluded_actions=["drag_and_drop", "key_combination"]
)
```

---

## Custom Executor Implementation

Implement `ActionExecutor` for other automation frameworks:

```python
from google_computer_use import ActionExecutor, BrowserState, ComputerAction

class MyCustomExecutor(ActionExecutor):
    async def execute_action(self, action: ComputerAction) -> bool:
        # Convert coordinates
        x, y = self.normalize_coordinates(
            action.args.get("x", 0),
            action.args.get("y", 0)
        )

        # Execute action with your framework
        # ...

        return True

    async def get_screenshot(self) -> bytes:
        # Capture screenshot as PNG bytes
        return screenshot_bytes

    async def get_state(self) -> BrowserState:
        return BrowserState(
            screenshot=await self.get_screenshot(),
            url="...",
            title="...",
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
        )
```

---

## Limitations

### Current Scope

**✅ Optimized For:**
- Web browsers (primary focus)
- Android UIs (strong performance)

**❌ Not Optimized:**
- Desktop OS control
- Heavy JavaScript/React apps (may need wait times)
- CAPTCHA-protected sites (safety restriction)
- Real-time trading (timing critical)

### Accuracy

- 70% success rate on benchmark (excellent but not perfect)
- Complex UIs may need multiple attempts
- Ambiguous elements can cause confusion

---

## Troubleshooting

### Playwright Installation Issues

```bash
# Ensure Chromium is installed
playwright install chromium

# Check installation
playwright --version
```

### Import Errors

```bash
# Verify extension is installed
uv pip list | grep autifyme-google-computer-use

# Reinstall if needed
cd extensions/google_computer_use
uv pip install -e ".[playwright]"
```

### Model Access

```bash
# Ensure GOOGLE_API_KEY is set
export GOOGLE_API_KEY=your_api_key_here

# Or set in .env file (AutifyME root)
echo "GOOGLE_API_KEY=your_api_key_here" >> .env
```

---

## Documentation

**Detailed Guide:** `docs/architecture/tech/GOOGLE_COMPUTER_USE_GUIDE.md` (in AutifyME root)

**Multimodal Integration:** `docs/architecture/tech/GOOGLE_AI_MULTIMODAL_INTEGRATION.md`

**API Reference:** [Google Computer Use Docs](https://ai.google.dev/gemini-api/docs/computer-use)

---

## Development

### Running Tests

```bash
cd extensions/google_computer_use
uv pip install -e ".[dev,playwright]"
pytest tests/
```

### Contributing

When modifying the extension:

1. Keep it lightweight (avoid unnecessary dependencies)
2. Maintain backward compatibility
3. Update tests
4. Update this README

---

## License

Same as AutifyME main project

---

## Support

For issues related to this extension:
1. Check troubleshooting section above
2. Review [GOOGLE_COMPUTER_USE_GUIDE.md](../../docs/architecture/tech/GOOGLE_COMPUTER_USE_GUIDE.md)
3. Open issue in main AutifyME repository
