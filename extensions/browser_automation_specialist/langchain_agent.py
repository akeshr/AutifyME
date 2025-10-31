"""LangChain Agent with Browser Automation Tool.

Demonstrates how to create a LangChain agent that uses Google Computer Use
for autonomous browser automation.
"""

from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver

from .browser_tool import browser_automation_tool, cleanup_browser


def create_browser_agent(
    llm: BaseChatModel,
    system_prompt: str | None = None,
) -> Any:
    """Create LangChain agent with browser automation capability.

    Args:
        llm: Language model for agent reasoning
        system_prompt: System prompt defining agent behavior

    Returns:
        LangChain agent with browser_automation_tool

    Example:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.1,
        )

        agent = create_browser_agent(llm)

        result = await agent.ainvoke(
            {"messages": [("user", "Go to pavisha.com and extract company info")]},
            config={"configurable": {"thread_id": "test-1"}}
        )
    """
    if system_prompt is None:
        system_prompt = _default_system_prompt()

    # Create agent with browser automation tool
    agent = create_agent(
        model=llm,
        tools=[browser_automation_tool],
        checkpointer=MemorySaver(),
        system_prompt=system_prompt,
    )

    return agent


def _default_system_prompt() -> str:
    """Default system prompt for browser automation agent."""
    return """You are a Browser Automation Specialist.

CAPABILITIES:
You have access to browser_automation_tool which gives you autonomous web browsing powered by Google Computer Use model. This tool:
- Sees web pages through screenshots
- Takes UI actions (click, type, scroll, navigate)
- Reasons visually about page content and layout
- Handles multi-step workflows autonomously

USE CASES:
- Extract data from websites (company info, products, pricing)
- Research competitors or suppliers
- Analyze page structure and content
- Navigate multi-page workflows
- Verify information across sites

APPROACH:
1. Analyze the user's request and determine what needs to be extracted/accomplished
2. Craft a clear, specific goal for the browser_automation_tool
3. Set appropriate max_steps (20-50 depending on complexity)
4. Review the tool's output for completeness
5. If data is incomplete or task failed, retry with refined goal
6. Extract and structure the final results for the user

TOOL USAGE BEST PRACTICES:
- Be specific about what to extract ("extract company name, services, and contact info")
- Mention if scrolling needed ("scroll to footer to see contact information")
- Set confidence targets ("ensure 90%+ data completeness")
- Include visual landmarks ("look for blue 'About Us' link in header")
- Start with reasonable max_steps (30) and increase if needed

SELF-REVIEW:
Before returning results:
- Validate data completeness
- Check if confidence targets met
- Flag any missing information
- Suggest retry with different approach if task failed

LIMITATIONS:
- Cannot solve CAPTCHAs or bypass authentication
- 70% success rate on complex UIs (may need retries)
- Cannot execute JavaScript or modify browser settings
- Timeout issues with slow-loading sites

Execute tasks thoughtfully and communicate clearly about results and limitations."""


__all__ = ["create_browser_agent", "cleanup_browser"]
