"""Browser Automation Specialist - Autonomous agent using Google Computer Use.

Intelligence-First Design:
- Reasons about goals before execution
- Analyzes results and adapts strategy
- Self-reviews and iterates when needed
- Transparent about capabilities and limitations
"""

from pathlib import Path
from typing import Any

try:
    from google_computer_use import ComputerUseAgent, get_computer_use_agent
    from google_computer_use.playwright_executor import PlaywrightExecutor
except ImportError:
    raise ImportError(
        "google_computer_use extension required. Install with:\n"
        "cd extensions/google_computer_use && uv pip install -e '.[playwright]' && playwright install chromium"
    ) from None


class BrowserAutomationSpecialist:
    """Autonomous browser automation specialist using Google Computer Use model.

    Wraps ComputerUseAgent with Intelligence-First principles:
    - Dynamic planning based on goals
    - Visual reasoning from screenshots
    - Self-review and adaptation
    - Graceful failure handling

    Usage:
        specialist = BrowserAutomationSpecialist(headless=False)
        await specialist.initialize()

        result = await specialist.execute_task(
            goal="Go to pavisha.com and extract company profile",
            max_steps=30
        )

        await specialist.cleanup()
    """

    def __init__(
        self,
        headless: bool = True,
        viewport_width: int = 1440,
        viewport_height: int = 900,
        auto_confirm: bool = True,
        system_instruction: str | None = None,
    ):
        """Initialize Browser Automation Specialist.

        Args:
            headless: Run browser in headless mode
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
            auto_confirm: Auto-approve high-risk actions (use with caution)
            system_instruction: Custom system instruction (uses default if None)
        """
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.auto_confirm = auto_confirm

        # Load default system instruction if not provided
        if system_instruction is None:
            prompt_path = Path(__file__).parent / "system_prompt.txt"
            if prompt_path.exists():
                system_instruction = prompt_path.read_text(encoding="utf-8")
            else:
                system_instruction = self._default_system_instruction()

        self.system_instruction = system_instruction

        # Will be initialized in initialize()
        self.executor: PlaywrightExecutor | None = None
        self.agent: ComputerUseAgent | None = None

    def _default_system_instruction(self) -> str:
        """Default system instruction for autonomous behavior."""
        return """You are an expert Browser Automation Specialist.

CAPABILITIES:
- Navigate web pages and analyze content visually
- Extract structured data from websites
- Fill forms and interact with UI elements
- Handle multi-step workflows autonomously
- Verify actions succeeded by examining screenshots

AUTONOMOUS APPROACH:
1. Analyze the goal and break into logical steps
2. Execute actions while observing visual feedback
3. Adapt strategy based on what you see in screenshots
4. Self-review: verify each action worked before proceeding
5. If stuck or uncertain, try alternative approaches

BEST PRACTICES:
- Take time to analyze screenshots before acting
- Verify critical actions (form submissions, clicks)
- Scroll to see all content before concluding
- Extract complete information, not partial data
- Flag limitations transparently if goal unreachable

SAFETY:
- Avoid destructive actions (deletes, irreversible changes)
- Be cautious with form submissions
- Respect site terms and rate limits
- Stop if encountering CAPTCHAs or auth barriers

Execute tasks thoughtfully, adapt dynamically, and communicate clearly."""

    async def initialize(self):
        """Initialize browser executor and computer use agent."""
        # Initialize Playwright executor
        self.executor = PlaywrightExecutor(
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
            headless=self.headless,
        )
        await self.executor.initialize()

        # Create Computer Use agent
        self.agent = get_computer_use_agent(
            action_executor=self.executor,
            system_instruction=self.system_instruction,
            auto_confirm=self.auto_confirm,
        )

    async def execute_task(
        self,
        goal: str,
        max_steps: int = 30,
        initial_url: str | None = None,
        excluded_actions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute browser automation task autonomously.

        Args:
            goal: Natural language description of what to accomplish
            max_steps: Maximum actions to take (default 30)
            initial_url: Starting URL (optional)
            excluded_actions: Actions to exclude for safety

        Returns:
            Dict with:
                - success: bool
                - steps_taken: int
                - final_url: str
                - final_title: str
                - actions_summary: list of action descriptions
                - error: str (if failed)

        Example:
            result = await specialist.execute_task(
                goal="Go to pavisha.com and extract company profile including services and contact info",
                max_steps=30,
                initial_url="https://www.pavisha.com"
            )
        """
        if not self.agent:
            raise RuntimeError("Specialist not initialized. Call initialize() first.")

        # Execute task through Computer Use agent
        result = await self.agent.execute_task(
            goal=goal,
            max_steps=max_steps,
            initial_url=initial_url,
            excluded_actions=excluded_actions,
        )

        # Transform result to specialist format
        final_state = result.get("final_state")
        actions = result.get("actions", [])

        return {
            "success": result.get("success", False),
            "steps_taken": result.get("steps_taken", 0),
            "final_url": final_state.url if final_state else "unknown",
            "final_title": final_state.title if final_state else "unknown",
            "actions_summary": [
                f"{action.action_type}: {action.reasoning[:100]}" for action in actions
            ],
            "error": result.get("error"),
        }

    async def cleanup(self):
        """Clean up browser resources."""
        if self.executor:
            await self.executor.cleanup()


def create_browser_specialist(
    headless: bool = True,
    viewport_width: int = 1440,
    viewport_height: int = 900,
    auto_confirm: bool = True,
) -> BrowserAutomationSpecialist:
    """Factory function to create Browser Automation Specialist.

    Args:
        headless: Run browser in headless mode
        viewport_width: Browser viewport width (default 1440)
        viewport_height: Browser viewport height (default 900)
        auto_confirm: Auto-approve high-risk actions (default True)

    Returns:
        Configured BrowserAutomationSpecialist instance

    Example:
        specialist = create_browser_specialist(headless=False)
        await specialist.initialize()

        result = await specialist.execute_task(
            goal="Analyze https://competitor.com homepage",
            max_steps=20
        )

        print(f"Success: {result['success']}")
        print(f"Final URL: {result['final_url']}")

        await specialist.cleanup()
    """
    return BrowserAutomationSpecialist(
        headless=headless,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        auto_confirm=auto_confirm,
    )
