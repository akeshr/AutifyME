"""Pydantic schemas for scenario definitions.

Scenarios are loaded from YAML files and validated against these schemas.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ScenarioCategory(str, Enum):
    """Category of scenario for filtering."""

    PM = "pm"
    ANALYST = "analyst"
    SPECIALIST = "specialist"
    E2E = "e2e"


class ScenarioInput(BaseModel):
    """Input configuration for a scenario.

    Defines what message, media, and context to send to the agent.
    """

    message: str = Field(..., description="User message to send")
    media_paths: list[str] = Field(
        default_factory=list,
        description="Paths to media files. Use [test_assets] for relative paths.",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (product_type, price_hint, etc.)",
    )


class ExpectedBehavior(BaseModel):
    """Expected behavior for scenario validation.

    Defines what the agent should do when processing this scenario.
    """

    delegation_order: list[str] = Field(
        default_factory=list,
        description="Expected order of delegations (e.g., [visual_analyst, product_analyst])",
    )
    waves: dict[int, list[str]] = Field(
        default_factory=dict,
        description="Expected wave structure (e.g., {1: [visual_analyst], 2: [product_analyst]})",
    )
    protocol_loads: dict[str, str] = Field(
        default_factory=dict,
        description="Expected protocol loads by agent (e.g., {PM: hitl})",
    )
    hitl_expected: bool = Field(
        default=False,
        description="Whether HITL approval should be triggered",
    )
    tool_sequence_contains: list[str] = Field(
        default_factory=list,
        description="Tool calls that must appear in sequence",
    )
    final_response_contains: list[str] = Field(
        default_factory=list,
        description="Keywords that must appear in final response",
    )
    final_response_not_contains: list[str] = Field(
        default_factory=list,
        description="Keywords that must NOT appear in final response",
    )


class SuccessCriteria(BaseModel):
    """Success criteria for scenario validation.

    Defines thresholds and requirements for the scenario to pass.
    """

    graders_must_pass: list[str] = Field(
        default_factory=list,
        description="Code graders that must pass (e.g., [protocol_load_first])",
    )
    min_overall_score: float = Field(
        default=0.7,
        description="Minimum overall score from code graders (0.0-1.0)",
    )
    max_latency_ms: int | None = Field(
        default=None,
        description="Maximum acceptable latency in milliseconds",
    )
    max_cost: float | None = Field(
        default=None,
        description="Maximum acceptable cost in USD",
    )
    max_tokens: int | None = Field(
        default=None,
        description="Maximum acceptable token usage",
    )


class ScenarioDefinition(BaseModel):
    """Complete scenario definition.

    Loaded from YAML files in tests/scenarios/<category>/<id>.yaml

    Example YAML:
        id: PM-01
        name: Single Product Catalog
        description: Basic image cataloging workflow
        category: pm
        input:
          message: "Catalog these sneakers for $79.99"
          media_paths: ["[test_assets]/sneaker.jpg"]
        expected:
          delegation_order: [visual_analyst, product_analyst]
          hitl_expected: true
        success_criteria:
          graders_must_pass: [protocol_load_first]
          min_overall_score: 0.85
    """

    id: str = Field(..., description="Unique scenario ID (e.g., PM-01)")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="What this scenario tests")
    category: ScenarioCategory = Field(..., description="Category for filtering")
    input: ScenarioInput = Field(..., description="Input configuration")
    expected: ExpectedBehavior = Field(
        default_factory=ExpectedBehavior,
        description="Expected behavior",
    )
    success_criteria: SuccessCriteria = Field(
        default_factory=SuccessCriteria,
        description="Pass/fail criteria",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for filtering (e.g., [core, image, hitl])",
    )
    baseline_trace_id: str | None = Field(
        default=None,
        description="LangSmith trace ID of baseline run",
    )
    version: str = Field(
        default="1.0",
        description="Schema version",
    )

    def resolve_media_paths(self, test_assets_dir: str) -> list[str]:
        """Resolve [test_assets] placeholder in media paths.

        Args:
            test_assets_dir: Absolute path to test assets directory

        Returns:
            List of resolved absolute paths
        """
        resolved = []
        for path in self.input.media_paths:
            if path.startswith("[test_assets]"):
                resolved.append(path.replace("[test_assets]", test_assets_dir))
            else:
                resolved.append(path)
        return resolved

    def get_required_graders(self) -> list[str]:
        """Get list of graders that must pass for this scenario."""
        return self.success_criteria.graders_must_pass

    def is_hitl_scenario(self) -> bool:
        """Check if this scenario expects HITL interaction."""
        return self.expected.hitl_expected
