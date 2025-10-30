"""
Google Computer Use Extension for AutifyME

This optional extension provides browser automation capabilities using
Gemini 2.5 Computer Use model. Install only when needed to avoid heavy
dependencies (Playwright, Chromium).

Installation:
    uv pip install -e "extensions/google_computer_use[playwright]"

    Or manually:
    uv pip install google-generativeai playwright
    playwright install chromium

Usage:
    from google_computer_use import get_computer_use_agent
    from google_computer_use.playwright_executor import PlaywrightExecutor

    executor = PlaywrightExecutor()
    await executor.initialize()
    agent = get_computer_use_agent(action_executor=executor)
"""

__version__ = "0.1.0"

from .agent import (
    ActionExecutor,
    ActionType,
    BrowserState,
    ComputerAction,
    ComputerUseAgent,
    get_computer_use_agent,
)

__all__ = [
    "ActionExecutor",
    "ActionType",
    "BrowserState",
    "ComputerAction",
    "ComputerUseAgent",
    "get_computer_use_agent",
]
