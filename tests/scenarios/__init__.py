"""Scenario definitions for evaluation framework.

Provides canonical test scenarios for PM, analysts, and specialists.

Usage:
    from tests.scenarios import load_scenario, list_scenarios

    # Load a specific scenario
    scenario = load_scenario("PM-01")
    print(scenario.input.message)

    # List all available scenarios
    for scenario_id in list_scenarios():
        print(scenario_id)
"""

from .loader import list_scenarios, load_scenario
from .schema import (
    ExpectedBehavior,
    ScenarioCategory,
    ScenarioDefinition,
    ScenarioInput,
    SuccessCriteria,
)

__all__ = [
    "ScenarioDefinition",
    "ScenarioInput",
    "ExpectedBehavior",
    "SuccessCriteria",
    "ScenarioCategory",
    "load_scenario",
    "list_scenarios",
]
