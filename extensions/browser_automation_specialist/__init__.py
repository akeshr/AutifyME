"""Browser Automation Specialist - Autonomous agent using Google Computer Use.

Wraps ComputerUseAgent with Intelligence-First design for autonomous browser automation.
"""

__version__ = "0.1.0"

from .specialist import BrowserAutomationSpecialist, create_browser_specialist

__all__ = [
    "BrowserAutomationSpecialist",
    "create_browser_specialist",
]
