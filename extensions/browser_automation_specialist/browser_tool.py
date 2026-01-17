"""Browser Automation Tool - LangChain tool wrapping Computer Use agent.

This tool encapsulates the Computer Use agent's execute_task() method,
making it available to LangChain agents.
"""

from typing import Annotated

from langchain_core.tools import ToolException, tool
from pydantic import Field

try:
    from google_computer_use import get_computer_use_agent
    from google_computer_use.playwright_executor import PlaywrightExecutor
except ImportError:
    raise ImportError(
        "google_computer_use extension required. Install with:\n"
        "cd extensions/google_computer_use && uv pip install -e '.[playwright]'"
    ) from None


# Global executor (reused across tool calls for session persistence)
_executor = None


async def _get_executor(headless: bool = True):
    """Get or create PlaywrightExecutor singleton."""
    global _executor
    if _executor is None:
        _executor = PlaywrightExecutor(
            viewport_width=1440,
            viewport_height=900,
            headless=headless,
        )
        await _executor.initialize()
    return _executor


@tool
async def browser_automation_tool(
    goal: Annotated[
        str,
        Field(description="Natural language description of browser automation task to accomplish"),
    ],
    max_steps: Annotated[
        int, Field(description="Maximum number of UI actions to take (default 30)", default=30)
    ] = 30,
    initial_url: Annotated[
        str | None, Field(description="Starting URL to navigate to before task execution")
    ] = None,
) -> dict:
    """Execute autonomous browser automation task using Google Computer Use model.

    This tool wraps a visual AI that sees web pages through screenshots and takes
    UI actions (click, type, scroll, navigate) to accomplish goals.

    Use Cases:
    - Extract data from websites (products, pricing, company info)
    - Research competitors or suppliers
    - Analyze page structure and content
    - Navigate multi-page workflows
    - Verify information across sites

    The agent:
    - Sees screenshots and reasons visually
    - Plans actions autonomously
    - Adapts to unexpected page layouts
    - Self-reviews and iterates

    Example goals:
    - "Go to pavisha.com and extract complete company profile including services and contact info"
    - "Navigate to competitor product page and extract all specifications and pricing"
    - "Find the contact form and report what fields it requires"

    Args:
        goal: Clear description of what to accomplish
        max_steps: Maximum UI actions (increase for complex tasks)
        initial_url: Starting URL (optional)

    Returns:
        Dict with:
        - success: bool
        - steps_taken: int
        - final_url: str
        - final_title: str
        - actions_summary: list of actions taken
        - error: str (if failed)
    """
    try:
        # Get browser executor
        executor = await _get_executor(headless=False)  # Headful for visibility

        # Create Computer Use agent
        agent = get_computer_use_agent(
            action_executor=executor,
            auto_confirm=True,  # Auto-approve high-risk actions
        )

        # Execute autonomous task
        result = await agent.execute_task(
            goal=goal,
            max_steps=max_steps,
            initial_url=initial_url,
        )

        # Transform to structured output
        final_state = result.get("final_state")
        actions = result.get("actions", [])

        return {
            "success": result.get("success", False),
            "steps_taken": result.get("steps_taken", 0),
            "final_url": final_state.url if final_state else "unknown",
            "final_title": final_state.title if final_state else "unknown",
            "actions_summary": [
                f"{action.action_type}: {action.reasoning[:80]}" for action in actions
            ],
            "error": result.get("error"),
        }

    except Exception as e:
        raise ToolException(f"Browser automation failed: {str(e)}") from e


async def cleanup_browser():
    """Clean up browser resources."""
    global _executor
    if _executor:
        await _executor.cleanup()
        _executor = None


__all__ = ["browser_automation_tool", "cleanup_browser"]
