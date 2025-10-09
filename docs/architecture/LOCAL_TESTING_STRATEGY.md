# Local Testing Strategy for AutifyME Agents

**Date**: 2025-10-09
**Status**: ✅ IMPLEMENTED
**Purpose**: Enable rapid local testing without WhatsApp dependency

---

## Quick Start

**Two CLI tools available for local testing:**

### 1. PM Chat (fastest iteration)
```bash
# Simple message
uv run python -m autifyme_agents.cli.pm_chat "Catalog these sneakers, price $79"

# With image
uv run python -m autifyme_agents.cli.pm_chat --image test_images/sneaker.jpg "Catalog this"

# Interactive mode (best for rapid iteration)
uv run python -m autifyme_agents.cli.pm_chat --interactive
```

### 2. Full Workflow Simulator (realistic testing with HITL)
```bash
# Single scenario with auto-approve
uv run python -m autifyme_agents.cli.simulate "Catalog sneakers, $79" --auto-approve

# With image
uv run python -m autifyme_agents.cli.simulate "Catalog this product" --image test_images/sneaker.jpg

# Run predefined scenario
uv run python -m autifyme_agents.cli.simulate --scenario cataloging_with_image

# Run all scenarios
uv run python -m autifyme_agents.cli.simulate --all
```

**All media types supported**:
- **Images**: .jpg, .png, .webp, .gif
- **Audio/Voice**: .ogg, .m4a, .mp3, .wav, .aac
- **Videos**: .mp4, .mov, .avi, .webm, .mkv
- **Documents**: .pdf, .xlsx, .csv, .docx, .txt

Use `--media <path>` for all types (or legacy `--image` for images).

**Windows note**: Emoji fallbacks implemented for console encoding compatibility.

---

## Problem Statement

**Current state**: Testing requires WhatsApp integration
- Can't test from terminal where Claude Code has access
- Slow iteration cycle (deploy → test on WhatsApp → debug)
- Hard to reproduce issues without WhatsApp
- Can't test HITL approvals locally
- No automated regression testing

**Desired state**: Multiple testing tiers
1. **Quick PM testing** - Direct PM invocation, fast iteration
2. **Full workflow testing** - Runner + all components, realistic simulation
3. **HITL testing** - Test approval flows locally
4. **Scenario testing** - Automated regression tests

---

## Testing Architecture

### Tier 1: Direct PM Chat (Fastest)

**Purpose**: Rapid iteration on PM logic and prompts

```bash
# Simple chat with PM
uv run python -m autifyme_agents.cli.pm_chat "Catalog these sneakers, price $79"

# With image
uv run python -m autifyme_agents.cli.pm_chat "Catalog this product" --image test_images/sneaker.jpg

# Interactive mode
uv run python -m autifyme_agents.cli.pm_chat --interactive
```

**What it tests**:
- PM intent classification
- PM delegation to departments
- Department execution
- Response formatting

**What it skips**:
- Channel adapters (WhatsApp-specific logic)
- Media download (uses local files)
- Real HITL (simulated auto-approve)

**Use when**:
- Testing PM prompt changes
- Testing new intents
- Debugging department delegation
- Quick sanity checks

---

### Tier 2: Full Workflow Simulator (Realistic)

**Purpose**: Test complete flow with HITL

```bash
# Custom message with HITL (interactive approval)
uv run python -m autifyme_agents.cli.simulate "Catalog these sneakers, $79"

# Auto-approve mode (skip HITL prompts)
uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" --auto-approve

# Predefined scenario
uv run python -m autifyme_agents.cli.simulate --scenario cataloging_with_image

# All predefined scenarios
uv run python -m autifyme_agents.cli.simulate --all

# With image (supports all media types)
uv run python -m autifyme_agents.cli.simulate "Catalog this" --image test_images/product.jpg
```

**What it tests**:
- Full Runner orchestration
- HITL interrupt and resume
- State persistence (checkpointer)
- Error recovery
- Message formatting

**What it skips**:
- Real WhatsApp API calls
- Real media download (uses local files)

**Use when**:
- Testing HITL flows
- Testing state persistence
- Testing error recovery
- Integration testing before WhatsApp

---

### Tier 3: Scenario Test Suite (Automated)

**Purpose**: Regression testing for critical flows

```bash
# Run all scenarios
pytest agents/tests/scenarios/

# Run specific category
pytest agents/tests/scenarios/test_cataloging_scenarios.py

# With coverage
pytest agents/tests/scenarios/ --cov=autifyme_agents
```

**What it tests**:
- All critical user scenarios (9 from PM doc)
- Edge cases (empty messages, ambiguous intent)
- Error conditions (missing fields, network errors)
- Multi-step workflows

**Use when**:
- Before commits
- CI/CD pipeline
- Validating refactors
- Ensuring no regressions

---

### Tier 4: Streamlit UI (Optional Visual Testing)

**Purpose**: Visual testing and demos

```bash
# Launch local UI
uv run streamlit run agents/src/autifyme_agents/cli/streamlit_tester.py
```

**What it provides**:
- Visual chat interface
- Image upload
- HITL approval UI
- Conversation history
- State inspection

**Use when**:
- Demonstrating to stakeholders
- Manual exploratory testing
- Visual validation of outputs

---

## Implementation Details

### 1. Simple PM Chat CLI ✅ IMPLEMENTED

**File**: `agents/src/autifyme_agents/cli/pm_chat.py`

```python
"""Simple CLI for chatting with PM directly."""

import sys
from pathlib import Path
from dotenv import load_dotenv

from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.workflows.project_manager import create_project_manager
from langchain_core.messages import HumanMessage


def chat_with_pm(message: str, image_path: Path | None = None):
    """Send a message to PM and print response."""

    # Setup
    storage = SupabaseStorageClient()
    company_profile = storage.get_company_profile()
    checkpointer = get_checkpointer()

    # Create PM
    pm = create_project_manager(
        company_profile=company_profile,
        checkpointer=checkpointer,
        storage=storage,
    )

    # Build message
    content = f"User message: {message}"
    if image_path:
        content += f"\nUser provided an image (path: {image_path})"

    # Invoke PM
    result = pm.invoke(
        {"messages": [HumanMessage(content=content)]},
        config={"configurable": {"thread_id": "local_test"}},
    )

    # Extract response
    messages = result.get("messages", [])
    if messages:
        last_message = messages[-1]
        response = getattr(last_message, "content", str(last_message))
        print(f"\nPM Response:\n{response}\n")
    else:
        print("\n[No response from PM]\n")


def interactive_mode():
    """Interactive chat loop."""
    print("=" * 60)
    print("PM INTERACTIVE CHAT")
    print("=" * 60)
    print("Commands: exit, quit, image <path>")
    print()

    image_path = None

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ["exit", "quit"]:
                break

            if user_input.lower().startswith("image "):
                image_path = Path(user_input[6:].strip())
                print(f"[Image set: {image_path}]")
                continue

            if not user_input:
                continue

            chat_with_pm(user_input, image_path)
            image_path = None  # Reset after use

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def main():
    load_dotenv(Path.cwd() / ".env")

    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive":
            interactive_mode()
        elif sys.argv[1] == "--image" and len(sys.argv) > 3:
            chat_with_pm(sys.argv[3], Path(sys.argv[2]))
        else:
            message = " ".join(sys.argv[1:])
            chat_with_pm(message)
    else:
        print("Usage:")
        print("  uv run python -m autifyme_agents.cli.pm_chat 'Your message'")
        print("  uv run python -m autifyme_agents.cli.pm_chat --image path/to/image.jpg 'Catalog this'")
        print("  uv run python -m autifyme_agents.cli.pm_chat --interactive")


if __name__ == "__main__":
    main()
```

---

### 2. Full Workflow Simulator ✅ IMPLEMENTED

**File**: `agents/src/autifyme_agents/cli/simulate.py`

**Key features**:
- `ConsoleChannel` - Platform-agnostic messaging adapter for console testing
- `safe_print()` - Windows console encoding compatibility (handles emoji fallback)
- Auto-approve mode for automated testing
- Predefined scenarios (cataloging, conversational, inquiry, etc.)
- Elapsed time tracking
- Interactive HITL approval prompts

```python
"""Full workflow simulator with HITL support."""

import json
from pathlib import Path
from dotenv import load_dotenv

from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner
from autifyme_agents.workflows.channels.protocol import MessagingChannel


class ConsoleChannel(MessagingChannel):
    """Console-based messaging channel for local testing."""

    def format_thread_id(self, sender: str) -> str:
        return f"console:{sender}"

    def send_text(self, recipient: str, message: str, *, preview_url: bool = False) -> dict:
        print(f"\n{'='*60}")
        print(f"MESSAGE TO {recipient}:")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")
        return {"status": "sent"}

    def send_approval_request(self, recipient: str, draft: dict) -> dict:
        print(f"\n{'='*60}")
        print(f"APPROVAL REQUEST TO {recipient}:")
        print(f"{'='*60}")
        print(json.dumps(draft, indent=2))
        print(f"{'='*60}")

        # Interactive approval
        while True:
            decision = input("\nApprove this draft? (yes/no): ").strip().lower()
            if decision in ["yes", "y"]:
                return {"status": "pending_approval", "draft": draft}
            elif decision in ["no", "n"]:
                return {"status": "rejected"}
            else:
                print("Please answer 'yes' or 'no'")

    def send_completion(self, recipient: str, result: dict) -> dict:
        print(f"\n{'='*60}")
        print(f"COMPLETION MESSAGE TO {recipient}:")
        print(f"{'='*60}")
        print(json.dumps(result, indent=2))
        print(f"{'='*60}\n")
        return {"status": "sent"}

    def send_error(self, recipient: str, error_type: str, custom_message: str | None = None) -> dict:
        print(f"\n{'='*60}")
        print(f"ERROR MESSAGE TO {recipient}:")
        print(f"{'='*60}")
        print(f"Error Type: {error_type}")
        if custom_message:
            print(f"Message: {custom_message}")
        print(f"{'='*60}\n")
        return {"status": "sent"}

    def download_media(self, media_id: str) -> Path:
        # For local testing, media_id is already a path
        return Path(media_id)


def run_scenario(scenario_name: str, text: str, image_path: Path | None = None):
    """Run a test scenario."""
    print(f"\n{'#'*60}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'#'*60}\n")

    # Setup
    load_dotenv(Path.cwd() / ".env")
    storage = SupabaseStorageClient()
    channel = ConsoleChannel()
    checkpointer = get_checkpointer()

    # Create runner
    runner = WorkflowRunner(
        channel=channel,
        storage=storage,
        checkpointer=checkpointer,
    )

    # Run scenario
    print(f"User Input: {text}")
    if image_path:
        print(f"Image: {image_path}")

    runner.handle_message(
        sender="local_test_user",
        text=text,
        media_id=str(image_path) if image_path else None,
    )

    print(f"\n{'#'*60}")
    print(f"SCENARIO COMPLETE: {scenario_name}")
    print(f"{'#'*60}\n")


def run_all_scenarios():
    """Run all predefined scenarios."""
    scenarios = [
        {
            "name": "Cataloging with Image",
            "text": "Catalog these canvas sneakers. Price $79.99, sizes 7-11.",
            "image": Path("test_images/sneaker.jpg") if Path("test_images/sneaker.jpg").exists() else None,
        },
        {
            "name": "Cataloging Text Only",
            "text": "Add a new product: Blue Cotton T-Shirt, price $29.99, sizes S-XL",
            "image": None,
        },
        {
            "name": "Ambiguous Image",
            "text": None,
            "image": Path("test_images/product.jpg") if Path("test_images/product.jpg").exists() else None,
        },
        {
            "name": "Conversational",
            "text": "Hi, how are you?",
            "image": None,
        },
        {
            "name": "Product Inquiry",
            "text": "What colors do we have for SKU-456?",
            "image": None,
        },
    ]

    for scenario in scenarios:
        run_scenario(scenario["name"], scenario["text"], scenario["image"])
        input("\nPress Enter to continue to next scenario...")


def main():
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--run-all-scenarios":
            run_all_scenarios()
        elif sys.argv[1] == "--scenario":
            # Custom scenario
            text = sys.argv[2] if len(sys.argv) > 2 else "Test message"
            image = Path(sys.argv[3]) if len(sys.argv) > 3 else None
            run_scenario("Custom", text, image)
        else:
            print("Unknown option")
    else:
        print("Usage:")
        print("  uv run python -m autifyme_agents.cli.simulate_workflow --run-all-scenarios")
        print("  uv run python -m autifyme_agents.cli.simulate_workflow --scenario 'Your message' [image_path]")


if __name__ == "__main__":
    main()
```

---

### 3. Scenario Test Suite

**File**: `agents/tests/scenarios/test_cataloging_scenarios.py`

```python
"""Automated scenario tests for cataloging workflows."""

import pytest
from pathlib import Path

from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.workflows.project_manager import create_project_manager
from langchain_core.messages import HumanMessage


@pytest.fixture
def pm_agent():
    """Create PM agent for testing."""
    storage = SupabaseStorageClient()
    company_profile = storage.get_company_profile()
    checkpointer = get_checkpointer()

    return create_project_manager(
        company_profile=company_profile,
        checkpointer=checkpointer,
        storage=storage,
    )


def test_catalog_with_text_and_image(pm_agent):
    """Test: User provides text description + image."""
    message = (
        "User message: Catalog these canvas sneakers. Price $79.99, sizes 7-11.\n"
        "User provided an image (path: /test/sneaker.jpg)"
    )

    result = pm_agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": "test_1"}},
    )

    messages = result.get("messages", [])
    assert len(messages) > 0

    last_message = messages[-1]
    response = getattr(last_message, "content", "")

    # PM should delegate to cataloging_department
    assert "cataloging" in response.lower() or "product" in response.lower()


def test_conversational_intent(pm_agent):
    """Test: User sends greeting."""
    message = "User message: Hi, how are you?"

    result = pm_agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": "test_2"}},
    )

    messages = result.get("messages", [])
    assert len(messages) > 0

    last_message = messages[-1]
    response = getattr(last_message, "content", "")

    # PM should respond directly, not delegate
    assert any(word in response.lower() for word in ["hello", "hi", "help", "ready"])


def test_ambiguous_image_only(pm_agent):
    """Test: User sends image with no text."""
    message = "User provided an image (path: /test/product.jpg)"

    result = pm_agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": "test_3"}},
    )

    messages = result.get("messages", [])
    assert len(messages) > 0

    last_message = messages[-1]
    response = getattr(last_message, "content", "")

    # PM should ask for clarification
    assert "?" in response or any(word in response.lower() for word in ["confirm", "clarify", "details"])


def test_text_only_cataloging(pm_agent):
    """Test: User provides text description without image."""
    message = "User message: Add a new product: Blue Cotton T-Shirt, price $29.99, sizes S-XL"

    result = pm_agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": "test_4"}},
    )

    messages = result.get("messages", [])
    assert len(messages) > 0

    last_message = messages[-1]
    response = getattr(last_message, "content", "")

    # PM should delegate to cataloging_department
    assert "cataloging" in response.lower() or "product" in response.lower() or "added" in response.lower()


def test_product_inquiry(pm_agent):
    """Test: User asks question about products."""
    message = "User message: What colors do we have for SKU-456?"

    result = pm_agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": "test_5"}},
    )

    messages = result.get("messages", [])
    assert len(messages) > 0

    # PM should delegate to cataloging_department for product inquiry
    # Response will vary based on implementation
```

---

## Testing Workflow

### Development Workflow

```bash
# 1. Make changes to PM prompt or logic
# Edit: agents/src/autifyme_agents/prompts/project_manager.prompt

# 2. Quick test with PM CLI (fastest)
uv run python -m autifyme_agents.cli.pm_chat "Catalog these sneakers, $79"

# 3. Test with image
uv run python -m autifyme_agents.cli.pm_chat --image test_images/sneaker.jpg "Catalog this"

# 4. Interactive testing (best for rapid iteration)
uv run python -m autifyme_agents.cli.pm_chat --interactive
# > Catalog sneakers
# > image test_images/sneaker.jpg
# > Catalog this product
# > exit

# 5. Full workflow test with HITL
uv run python -m autifyme_agents.cli.simulate "Catalog these sneakers, $79"
# (Approve interactively when prompted)

# 6. Full workflow with auto-approve (faster iteration)
uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" --auto-approve

# 7. Run all predefined scenarios
uv run python -m autifyme_agents.cli.simulate --all --auto-approve

# 8. Run regression tests (when implemented)
pytest agents/tests/scenarios/ -v

# 9. Once confident, test on WhatsApp
```

### Pre-Commit Workflow

```bash
# Run all predefined scenarios with auto-approve
uv run python -m autifyme_agents.cli.simulate --all --auto-approve

# Run automated tests (when implemented)
pytest agents/tests/scenarios/ --cov=autifyme_agents

# If all pass, commit
git commit -m "Update PM intent classification"
```

---

## Test Data Setup

### Directory Structure ✅ CREATED

```
agents/
├── test_images/          # Product images (README with guidance)
│   ├── README.md
│   ├── sneaker.jpg       # (add your test images)
│   ├── tshirt.jpg
│   ├── product.jpg
│   └── batch/            # Multiple products
├── test_audio/           # Voice notes and audio (README with guidance)
│   ├── README.md
│   ├── voice_note.ogg    # (add your voice notes)
│   └── voice_inquiry.ogg
├── test_videos/          # Product videos (README with guidance)
│   ├── README.md
│   └── product_demo.mp4  # (add your videos)
├── test_documents/       # PDFs, spreadsheets (README with guidance)
│   ├── README.md
│   ├── invoice.pdf       # (add your documents)
│   └── pricelist.xlsx
└── tests/
    └── scenarios/        # Automated pytest scenarios (TODO)
        ├── test_cataloging_scenarios.py
        ├── test_inquiry_scenarios.py
        └── test_conversational_scenarios.py
```

Each test media directory contains a README with:
- Recommended file names
- Supported formats
- Usage examples
- Creation tips

### Adding Test Media

```bash
# Add your own test files to appropriate directories
# Images: agents/test_images/
# Voice: agents/test_audio/
# Videos: agents/test_videos/
# Docs: agents/test_documents/

# Test with any media type
uv run python -m autifyme_agents.cli.pm_chat "Catalog this" --media test_images/your_product.jpg
uv run python -m autifyme_agents.cli.simulate "Transcribe" --media test_audio/voice_note.ogg
```

---

## Benefits of This Approach

1. **Fast Iteration**: Test PM changes in seconds, not minutes
2. **Full Coverage**: Test from simple PM logic to full workflow with HITL
3. **Debuggable**: All logs visible in terminal, easy to add breakpoints
4. **Reproducible**: Same scenarios run consistently
5. **Automatable**: Pytest integration for CI/CD
6. **Platform-Agnostic**: Test before adding new channels (Telegram, Email)
7. **Regression Protection**: Catch breaking changes before deployment

---

## Next Steps

1. Implement CLI tools (pm_chat.py, simulate_workflow.py)
2. Create test image directory with sample products
3. Write automated scenario tests
4. Document testing commands in README
5. Add pre-commit hook to run scenarios
6. (Optional) Add Streamlit UI for visual testing
