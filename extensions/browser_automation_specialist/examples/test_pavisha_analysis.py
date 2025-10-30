"""Test Browser Automation Specialist with real-world scenario.

Tests autonomous capabilities:
- Navigation and content analysis
- Scrolling to see all content
- Data extraction
- Multi-step reasoning
"""

import asyncio
import os
import sys
from pathlib import Path

# Load environment variables from AutifyME root
from dotenv import load_dotenv
root_dir = Path(__file__).parent.parent.parent.parent
env_path = root_dir / ".env"
load_dotenv(env_path)

# Add extensions to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from browser_automation_specialist import create_browser_specialist


async def test_company_profile_extraction():
    """Test: Extract comprehensive company profile from website."""
    print("=" * 80)
    print("TEST: Company Profile Extraction - Pavisha.com")
    print("=" * 80)
    print()

    # Create specialist (headless=False to watch execution)
    specialist = create_browser_specialist(headless=False)
    await specialist.initialize()

    # Define autonomous task
    goal = """Analyze https://www.pavisha.com and create comprehensive company profile.

EXTRACT:
- Company name and tagline
- Main services/products offered
- Value proposition
- Contact information (email, phone, location)
- Social media links
- Any other relevant business information

IMPORTANT: Scroll through entire page including footer to ensure complete data extraction.
Return structured information with confidence assessment."""

    try:
        print(f"GOAL: {goal}")
        print()
        print("Executing autonomous browser automation...")
        print("-" * 80)

        result = await specialist.execute_task(
            goal=goal,
            max_steps=50,  # Allow extensive exploration
            initial_url="https://www.pavisha.com"
        )

        print()
        print("=" * 80)
        print("RESULT")
        print("=" * 80)
        print(f"Success: {result['success']}")
        print(f"Steps taken: {result['steps_taken']}")
        print(f"Final URL: {result['final_url']}")
        print(f"Page title: {result['final_title']}")
        print()

        if result['success']:
            print("Actions executed:")
            for i, action in enumerate(result['actions_summary'], 1):
                print(f"  {i}. {action}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")

    finally:
        await specialist.cleanup()
        print()
        print("Cleanup complete.")


async def test_multi_page_navigation():
    """Test: Navigate through multiple pages and extract data."""
    print("=" * 80)
    print("TEST: Multi-Page Navigation and Data Extraction")
    print("=" * 80)
    print()

    specialist = create_browser_specialist(headless=False)
    await specialist.initialize()

    goal = """Go to https://www.pavisha.com and explore their services section.

OBJECTIVES:
1. Find and navigate to services or solutions page
2. List all services/solutions offered
3. Extract brief description for each service
4. Return structured list

Confidence target: 90%+"""

    try:
        print(f"GOAL: {goal}")
        print()
        print("Executing...")
        print("-" * 80)

        result = await specialist.execute_task(
            goal=goal,
            max_steps=40,
            initial_url="https://www.pavisha.com"
        )

        print()
        print("=" * 80)
        print("RESULT")
        print("=" * 80)
        print(f"Success: {result['success']}")
        print(f"Steps: {result['steps_taken']}")
        print(f"Final URL: {result['final_url']}")

        if result['actions_summary']:
            print()
            print("Key actions:")
            for action in result['actions_summary'][:10]:  # Show first 10
                print(f"  - {action}")

    finally:
        await specialist.cleanup()


async def test_form_interaction():
    """Test: Interact with forms (demonstration only - no actual submission)."""
    print("=" * 80)
    print("TEST: Form Interaction Capabilities")
    print("=" * 80)
    print()

    specialist = create_browser_specialist(headless=False)
    await specialist.initialize()

    goal = """Navigate to https://www.pavisha.com and find contact form.

OBJECTIVES:
1. Locate contact or inquiry form
2. Identify all form fields (name, email, message, etc.)
3. Report form structure without filling or submitting
4. Check if CAPTCHA or other security measures present

DO NOT actually fill or submit the form - just analyze its structure."""

    try:
        print(f"GOAL: {goal}")
        print()
        print("Executing...")
        print("-" * 80)

        result = await specialist.execute_task(
            goal=goal,
            max_steps=30,
            initial_url="https://www.pavisha.com"
        )

        print()
        print("=" * 80)
        print("RESULT")
        print("=" * 80)
        print(f"Success: {result['success']}")
        print(f"Steps: {result['steps_taken']}")
        print(f"Final URL: {result['final_url']}")

    finally:
        await specialist.cleanup()


if __name__ == "__main__":
    print("Browser Automation Specialist - Test Suite")
    print()

    # Run tests
    print("Running Test 1: Company Profile Extraction")
    asyncio.run(test_company_profile_extraction())

    print("\n" * 2)
    print("Running Test 2: Multi-Page Navigation")
    asyncio.run(test_multi_page_navigation())

    print("\n" * 2)
    print("Running Test 3: Form Interaction")
    asyncio.run(test_form_interaction())

    print("\n" * 2)
    print("All tests complete!")
