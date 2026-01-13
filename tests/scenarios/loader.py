"""Scenario loader - loads scenarios from YAML files.

Usage:
    from tests.scenarios import load_scenario, list_scenarios

    scenario = load_scenario("PM-01")
    all_scenarios = list_scenarios(category="pm")
"""

from pathlib import Path

import yaml

from .schema import ScenarioCategory, ScenarioDefinition

# Base directory for scenarios
SCENARIOS_DIR = Path(__file__).parent


def load_scenario(scenario_id: str) -> ScenarioDefinition:
    """Load scenario by ID.

    Args:
        scenario_id: Scenario ID (e.g., "PM-01", "VA-01")

    Returns:
        ScenarioDefinition

    Raises:
        FileNotFoundError: If scenario file not found
        ValueError: If scenario is invalid

    Example:
        >>> scenario = load_scenario("PM-01")
        >>> print(scenario.name)
        "Single Product Catalog"
    """
    # Determine category from prefix
    prefix = scenario_id.split("-")[0].lower()
    category_map = {
        "pm": "pm",
        "va": "analyst",  # visual_analyst
        "pa": "analyst",  # product_analyst
        "ca": "analyst",  # catalog_analyst
        "cs": "specialist",  # catalog_specialist
        "cr": "specialist",  # creative_specialist
        "e2e": "e2e",
    }

    category = category_map.get(prefix, "pm")
    yaml_path = SCENARIOS_DIR / category / f"{scenario_id}.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(f"Scenario not found: {yaml_path}")

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return ScenarioDefinition(**data)


def list_scenarios(category: str | ScenarioCategory | None = None) -> list[str]:
    """List available scenario IDs.

    Args:
        category: Filter by category (pm, analyst, specialist, e2e) or None for all

    Returns:
        List of scenario IDs sorted alphabetically

    Example:
        >>> list_scenarios()
        ['PM-01', 'PM-02', 'PM-03', 'PM-04']

        >>> list_scenarios(category="pm")
        ['PM-01', 'PM-02', 'PM-03', 'PM-04']
    """
    scenarios = []

    # Normalize category
    if isinstance(category, ScenarioCategory):
        category = category.value

    categories = [category] if category else ["pm", "analyst", "specialist", "e2e"]

    for cat in categories:
        cat_dir = SCENARIOS_DIR / cat
        if cat_dir.exists():
            for yaml_file in cat_dir.glob("*.yaml"):
                scenarios.append(yaml_file.stem)

    return sorted(scenarios)


def get_scenarios_by_tag(tag: str) -> list[ScenarioDefinition]:
    """Get all scenarios with a specific tag.

    Args:
        tag: Tag to filter by (e.g., "core", "hitl", "image")

    Returns:
        List of ScenarioDefinition objects with the tag

    Example:
        >>> hitl_scenarios = get_scenarios_by_tag("hitl")
        >>> len(hitl_scenarios)
        2
    """
    scenarios = []
    for scenario_id in list_scenarios():
        scenario = load_scenario(scenario_id)
        if tag in scenario.tags:
            scenarios.append(scenario)
    return scenarios


def get_core_scenarios() -> list[ScenarioDefinition]:
    """Get all core scenarios (tagged with 'core').

    These are the essential scenarios that should always pass.

    Returns:
        List of core ScenarioDefinition objects
    """
    return get_scenarios_by_tag("core")
