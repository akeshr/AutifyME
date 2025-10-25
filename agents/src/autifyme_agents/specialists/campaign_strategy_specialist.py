"""
Campaign Strategy Specialist - Campaign planning and orchestration.

Domain Expertise:
- Campaign objective definition (awareness, conversion, retention, engagement)
- KPI measurement and benchmarking
- Budget allocation across channels (paid social, organic, ads, influencers)
- Timeline design and scheduling (launch date, milestones, duration)
- Channel mix optimization based on audience and objectives

Responsibilities:
- Analyze campaign brief and business objectives
- Define measurable KPIs aligned with objectives
- Allocate budget across platforms
- Design campaign timeline with milestones
- Recommend optimal channel mix
- Return structured CampaignStrategyDraft

Does NOT:
- Create actual content (Marketing Content Specialist handles this)
- Target specific audiences (Audience Intelligence Specialist handles this)
- Format for platforms (Platform Adaptation Specialist handles this)
- Persist to database (PM handles persistence with HITL)

Architecture Pattern:
- SubAgent dict format (NOT create_agent)
- Returns structured Pydantic models
- PM orchestrates delegation and approval
"""

from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, Field

from autifyme_agents.core.prompt_loader import load_prompt

# =============================================================================
# Data Models - Campaign Strategy Specialist Outputs
# =============================================================================


class ChannelAllocationDraft(BaseModel):
    """Draft budget allocation for a single channel."""

    platform: str = Field(
        ..., description="Platform name (facebook, instagram, youtube, etc.)"
    )
    allocated_budget: float = Field(..., description="Budget allocated to this channel")
    budget_percentage: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage of total budget"
    )
    expected_reach: int | None = Field(
        None, description="Estimated audience reach for this channel"
    )
    rationale: str = Field(
        ..., description="Why this allocation makes sense for campaign objectives"
    )


class CampaignKPIDraft(BaseModel):
    """Draft KPI definition for campaign success measurement."""

    metric_name: str = Field(..., description="KPI name (impressions, conversions, CTR)")
    target_value: float = Field(..., description="Target value for this metric")
    measurement_unit: str = Field(
        ..., description="Unit (count, percentage, currency)"
    )
    priority: str = Field(
        ..., description="Priority level (primary, secondary, tertiary)"
    )
    rationale: str = Field(..., description="Why this KPI matters for this campaign")


class CampaignStrategyDraft(BaseModel):
    """Complete campaign strategy from Campaign Strategy Specialist."""

    # Core campaign metadata
    campaign_name: str = Field(..., description="Campaign name")
    campaign_id: str = Field(
        ..., description="Business-friendly campaign identifier (e.g., SUMMER2024)"
    )
    campaign_type: str = Field(
        ...,
        description="Campaign type (product_launch, seasonal, promotional, awareness, retention, acquisition)",
    )

    # Objectives and KPIs
    primary_objective: str = Field(
        ..., description="Primary objective (sales, awareness, engagement, traffic, leads, retention)"
    )
    secondary_objectives: list[str] = Field(
        default_factory=list, description="Secondary objectives"
    )
    target_kpis: list[CampaignKPIDraft] = Field(
        ..., description="Measurable KPIs for success"
    )

    # Budget planning
    total_budget: float = Field(..., ge=0, description="Total campaign budget")
    budget_currency: str = Field(default="INR", description="Currency code (INR, USD)")
    channel_allocations: list[ChannelAllocationDraft] = Field(
        ..., description="Budget allocation per channel"
    )

    # Timeline
    planned_start_date: str = Field(
        ..., description="Campaign start date (ISO format YYYY-MM-DD)"
    )
    planned_end_date: str = Field(
        ..., description="Campaign end date (ISO format YYYY-MM-DD)"
    )
    campaign_duration_days: int = Field(
        ..., ge=1, description="Total campaign duration in days"
    )
    key_milestones: list[str] = Field(
        default_factory=list, description="Important campaign milestones"
    )

    # Target audience (high-level description)
    target_audience_description: str = Field(
        ..., description="High-level target audience description"
    )

    # Analysis metadata
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in strategy design"
    )
    strategy_notes: str = Field(
        ..., description="Additional strategy recommendations and considerations"
    )
    risks_and_mitigations: list[str] = Field(
        default_factory=list, description="Potential risks and mitigation strategies"
    )


# =============================================================================
# Tools - Campaign Strategy Analysis
# =============================================================================


@tool
def calculate_channel_budget_allocation(
    total_budget: float, channel_priorities: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Calculate optimal budget allocation across channels based on priorities.

    Args:
        total_budget: Total campaign budget
        channel_priorities: List of channels with priority weights
            Example: [
                {"platform": "facebook", "priority_weight": 0.35},
                {"platform": "instagram", "priority_weight": 0.25},
                {"platform": "youtube", "priority_weight": 0.20}
            ]

    Returns:
        Dict with:
        - allocations: list of channel allocations
        - total_allocated: total budget allocated
        - remaining: unallocated budget
    """
    if not channel_priorities:
        return {
            "allocations": [],
            "total_allocated": 0,
            "remaining": total_budget,
            "warning": "No channels specified",
        }

    # Normalize weights to sum to 1.0
    total_weight = sum(ch.get("priority_weight", 0) for ch in channel_priorities)

    if total_weight == 0:
        return {
            "allocations": [],
            "total_allocated": 0,
            "remaining": total_budget,
            "warning": "All priority weights are zero",
        }

    allocations = []
    total_allocated = 0

    for channel in channel_priorities:
        weight = channel.get("priority_weight", 0)
        normalized_weight = weight / total_weight
        allocated = round(total_budget * normalized_weight, 2)

        allocations.append({
            "platform": channel["platform"],
            "allocated_budget": allocated,
            "budget_percentage": round(normalized_weight * 100, 2),
            "priority_weight": weight,
        })

        total_allocated += allocated

    # Handle rounding differences
    remaining = round(total_budget - total_allocated, 2)

    return {
        "allocations": allocations,
        "total_allocated": total_allocated,
        "remaining": remaining,
        "is_fully_allocated": abs(remaining) < 0.01,
    }


@tool
def estimate_campaign_duration(
    start_date: str, end_date: str
) -> dict[str, Any]:
    """
    Calculate campaign duration and suggest milestones.

    Args:
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)

    Returns:
        Dict with:
        - duration_days: int
        - duration_weeks: int
        - suggested_milestones: list of milestone dates
        - is_valid: bool
    """
    from datetime import datetime, timedelta

    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        if end < start:
            return {
                "duration_days": 0,
                "duration_weeks": 0,
                "suggested_milestones": [],
                "is_valid": False,
                "error": "End date must be after start date",
            }

        duration = (end - start).days + 1  # Inclusive
        weeks = duration // 7

        # Suggest milestones (every 7 days or at 25%, 50%, 75% for shorter campaigns)
        milestones = []
        if duration <= 21:  # Short campaign
            quarter = duration // 4
            for i in [1, 2, 3]:
                milestone_date = start + timedelta(days=quarter * i)
                milestones.append(milestone_date.strftime("%Y-%m-%d"))
        else:  # Longer campaign - weekly milestones
            current = start + timedelta(days=7)
            while current < end:
                milestones.append(current.strftime("%Y-%m-%d"))
                current += timedelta(days=7)

        return {
            "duration_days": duration,
            "duration_weeks": weeks,
            "suggested_milestones": milestones,
            "is_valid": True,
            "campaign_length_category": (
                "short" if duration <= 7
                else "medium" if duration <= 30
                else "long"
            ),
        }

    except ValueError as e:
        return {
            "duration_days": 0,
            "duration_weeks": 0,
            "suggested_milestones": [],
            "is_valid": False,
            "error": f"Invalid date format: {str(e)}",
        }


# =============================================================================
# Specialist Factory
# =============================================================================


def create_campaign_strategy_specialist() -> dict[str, Any]:
    """
    Create Campaign Strategy Specialist as SubAgent spec.

    Specialist Responsibilities:
    - Analyze campaign brief and define objectives
    - Set measurable KPIs aligned with business goals
    - Allocate budget across channels optimally
    - Design campaign timeline and milestones
    - Recommend channel mix based on objectives
    - Return CampaignStrategyDraft for PM review

    Architecture:
    - SubAgent dict format (DeepAgents pattern)
    - Strategy tools only (no persistence, no content creation)
    - Returns structured Pydantic model
    - PM handles HITL and persistence

    Returns:
        SubAgent spec with:
        - name: specialist identifier
        - description: delegation criteria
        - tools: strategy analysis tools
        - system_prompt: domain expertise instructions
    """
    system_prompt = load_prompt("specialists/campaign_strategy_specialist.prompt")

    description = (
        "Defines campaign objectives, KPIs, budget allocation, and timeline. "
        "Adapts to missing data (suggests ranges if budget unclear). "
        "Self-reviews strategy (validates channel-objective alignment). "
        "Returns CampaignStrategyDraft. "
        "Run FIRST - other specialists depend on strategy output."
    )

    # Tools for campaign strategy analysis
    tools = [
        calculate_channel_budget_allocation,  # Budget optimization
        estimate_campaign_duration,  # Timeline planning
    ]

    return {
        "name": "campaign_strategy_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
    }
