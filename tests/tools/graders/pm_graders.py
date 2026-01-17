"""PM-specific code graders.

Fast, deterministic checks for PM behavior:
- Protocol loading order
- Media download before delegation
- Analyst-before-specialist two-phase pattern
- Wave execution structure
"""

from ..models import DelegationGraph, ToolCallSequence
from .base import GraderCategory, GraderResult

# =============================================================================
# Taxonomy-Based Agent Classification
# =============================================================================
# Derive agent type from naming convention - no hardcoded lists.
# New agents are auto-classified by suffix: _analyst, _specialist, _reviewer


def is_analyst(agent_name: str) -> bool:
    """Check if agent is an analyst (read-only research layer).

    Analysts are identified by the '_analyst' suffix in their name.
    Examples: visual_analyst, product_analyst, catalog_analyst, order_analyst
    """
    return agent_name.endswith("_analyst")


def is_specialist(agent_name: str) -> bool:
    """Check if agent is a specialist (execution layer with HITL).

    Specialists are identified by the '_specialist' suffix in their name.
    Examples: creative_specialist, catalog_specialist, pricing_specialist
    """
    return agent_name.endswith("_specialist")


def is_reviewer(agent_name: str) -> bool:
    """Check if agent is a reviewer (quality gate layer).

    Reviewers are identified by the '_reviewer' suffix in their name.
    Examples: compliance_reviewer, safety_reviewer, brand_reviewer
    """
    return agent_name.endswith("_reviewer")


def classify_agents(agent_names: list[str]) -> dict[str, list[str]]:
    """Classify agents by type based on naming convention.

    Args:
        agent_names: List of agent names from delegation order

    Returns:
        Dict with keys 'analysts', 'specialists', 'reviewers', 'other'
    """
    result: dict[str, list[str]] = {
        "analysts": [],
        "specialists": [],
        "reviewers": [],
        "other": [],
    }

    for name in agent_names:
        if is_analyst(name):
            result["analysts"].append(name)
        elif is_specialist(name):
            result["specialists"].append(name)
        elif is_reviewer(name):
            result["reviewers"].append(name)
        else:
            result["other"].append(name)

    return result


def protocol_load_first(seq: ToolCallSequence, agent: str = "PM") -> GraderResult:
    """Check if agent loaded protocol as first action.

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Agent to check (default: PM)

    Returns:
        GraderResult with pass/fail and evidence
    """
    # Filter tool calls by agent
    agent_calls = [tc for tc in seq.tool_calls if tc.agent == agent]

    if not agent_calls:
        return GraderResult(
            name="protocol_load_first",
            passed=False,
            score=0.0,
            evidence={"agent": agent, "tool_calls": []},
            reason=f"No tool calls found for agent {agent}",
            category=GraderCategory.PM if agent == "PM" else GraderCategory.SPECIALIST,
            severity="HIGH",
        )

    first_call = agent_calls[0]
    passed = first_call.tool_name == "load_protocol"

    return GraderResult(
        name="protocol_load_first",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence={
            "agent": agent,
            "first_call": first_call.tool_name,
            "first_call_args": first_call.parsed_args,
            "expected": "load_protocol",
            "total_agent_calls": len(agent_calls),
        },
        reason=f"Agent {agent} first call was {first_call.tool_name}"
        + (" (CORRECT)" if passed else " (EXPECTED: load_protocol)"),
        category=GraderCategory.PM if agent == "PM" else GraderCategory.SPECIALIST,
        severity="HIGH",
    )


def media_download_first(seq: ToolCallSequence) -> GraderResult:
    """Check if PM downloaded media before any delegation.

    For image workflows, PM should download media BEFORE delegating to analysts.

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()

    Returns:
        GraderResult with pass/fail and evidence
    """
    pm_calls = [tc for tc in seq.tool_calls if tc.agent == "PM"]

    # Find media downloads
    media_downloads = [tc for tc in pm_calls if tc.tool_name == "download_whatsapp_media"]

    # Find delegations
    delegations = [tc for tc in pm_calls if tc.tool_name == "task"]

    # If no delegations, grader not applicable
    if not delegations:
        return GraderResult(
            name="media_download_first",
            passed=True,
            score=1.0,
            evidence={"media_present": bool(media_downloads), "delegations": 0},
            reason="No delegations found - grader not applicable",
            category=GraderCategory.PM,
            severity="LOW",
        )

    # If no media downloads but delegations exist, might not be image workflow
    if not media_downloads:
        return GraderResult(
            name="media_download_first",
            passed=True,
            score=1.0,
            evidence={
                "media_present": False,
                "first_delegation_seq": delegations[0].sequence,
            },
            reason="No media download - may not be image workflow",
            category=GraderCategory.PM,
            severity="LOW",
        )

    # Compare sequence numbers
    first_media_seq = media_downloads[0].sequence
    first_delegation_seq = delegations[0].sequence
    passed = first_media_seq < first_delegation_seq

    return GraderResult(
        name="media_download_first",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence={
            "media_download_seq": first_media_seq,
            "first_delegation_seq": first_delegation_seq,
            "media_present": True,
        },
        reason=f"Media download at seq {first_media_seq}, first delegation at seq {first_delegation_seq}"
        + (" (CORRECT)" if passed else " (SHOULD DOWNLOAD BEFORE DELEGATING)"),
        category=GraderCategory.PM,
        severity="HIGH",
    )


def analyst_before_specialist(graph: DelegationGraph) -> GraderResult:
    """Check two-phase delegation: analysts before specialists.

    The PM should delegate to analysts for research BEFORE delegating
    to specialists for execution.

    Uses taxonomy-based classification: agents ending in '_analyst' or '_specialist'.

    Args:
        graph: DelegationGraph from get_delegation_graph()

    Returns:
        GraderResult with pass/fail and evidence
    """
    order = graph.delegation_order

    # Find indices of analysts and specialists using taxonomy-based classification
    analyst_indices = [i for i, agent in enumerate(order) if is_analyst(agent)]
    specialist_indices = [i for i, agent in enumerate(order) if is_specialist(agent)]

    # If either list is empty, grader may not apply
    if not analyst_indices:
        return GraderResult(
            name="analyst_before_specialist",
            passed=True,
            score=1.0,
            evidence={
                "delegation_order": order,
                "analysts_found": False,
                "specialists_found": bool(specialist_indices),
            },
            reason="No analysts in delegation - grader not applicable",
            category=GraderCategory.PM,
            severity="MEDIUM",
        )

    if not specialist_indices:
        return GraderResult(
            name="analyst_before_specialist",
            passed=True,
            score=1.0,
            evidence={
                "delegation_order": order,
                "analysts_found": True,
                "specialists_found": False,
            },
            reason="No specialists in delegation - grader not applicable",
            category=GraderCategory.PM,
            severity="MEDIUM",
        )

    # Check if all analysts come before any specialist
    last_analyst = max(analyst_indices)
    first_specialist = min(specialist_indices)
    passed = last_analyst < first_specialist

    return GraderResult(
        name="analyst_before_specialist",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence={
            "delegation_order": order,
            "last_analyst_index": last_analyst,
            "first_specialist_index": first_specialist,
            "last_analyst": order[last_analyst],
            "first_specialist": order[first_specialist],
        },
        reason=f"Last analyst ({order[last_analyst]}) at index {last_analyst}, "
        f"first specialist ({order[first_specialist]}) at {first_specialist}"
        + (" (CORRECT two-phase)" if passed else " (SPECIALISTS SHOULD COME AFTER ANALYSTS)"),
        category=GraderCategory.PM,
        severity="HIGH",
    )


def wave_execution_correct(graph: DelegationGraph) -> GraderResult:
    """Check correct parallel/serial wave structure.

    Principle: Research before execution. All analysts complete before specialists start.

    Uses taxonomy-based classification: agents ending in '_analyst' or '_specialist'.

    Args:
        graph: DelegationGraph from get_delegation_graph()

    Returns:
        GraderResult with pass/fail and evidence
    """
    waves = graph.waves

    if not waves:
        return GraderResult(
            name="wave_execution_correct",
            passed=True,
            score=1.0,
            evidence={"waves": {}, "delegations": len(graph.delegations)},
            reason="No wave structure detected - single delegation or none",
            category=GraderCategory.PM,
            severity="LOW",
        )

    deviations = []
    score = 1.0

    # Check analysts and specialists don't overlap in waves (taxonomy-based)
    analyst_waves = set()
    specialist_waves = set()

    for wave_num, agents in waves.items():
        for agent in agents:
            if is_analyst(agent):
                analyst_waves.add(wave_num)
            if is_specialist(agent):
                specialist_waves.add(wave_num)

    if analyst_waves and specialist_waves and max(analyst_waves) >= min(specialist_waves):
        deviations.append("Analysts and specialists in overlapping waves")
        score -= 0.5

    # Check for reasonable wave count (not too fragmented)
    if len(waves) > 5:
        deviations.append(f"Too many waves ({len(waves)}) - may be overly sequential")
        score -= 0.2

    passed = len(deviations) == 0

    return GraderResult(
        name="wave_execution_correct",
        passed=passed,
        score=max(0.0, score),
        evidence={
            "waves": {str(k): v for k, v in waves.items()},
            "deviations": deviations,
            "analyst_waves": list(analyst_waves),
            "specialist_waves": list(specialist_waves),
            "delegation_order": graph.delegation_order,
        },
        reason="Wave execution correct" if passed else f"Issues: {'; '.join(deviations)}",
        category=GraderCategory.PM,
        severity="HIGH",
    )


def visual_analyst_for_images(
    seq: ToolCallSequence, graph: DelegationGraph, has_image: bool
) -> GraderResult:
    """Check if PM delegated to visual_analyst when trace has images.

    The PM should use visual_analyst (its "eyes") to understand image content
    BEFORE delegating to specialists. This applies even with shortcut commands.

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        graph: DelegationGraph from get_delegation_graph()
        has_image: Whether the trace input contained images

    Returns:
        GraderResult with pass/fail and evidence
    """
    # If no images, grader not applicable
    if not has_image:
        return GraderResult(
            name="visual_analyst_for_images",
            passed=True,
            score=1.0,
            evidence={"has_image": False},
            reason="No images in input - grader not applicable",
            category=GraderCategory.PM,
            severity="LOW",
        )

    # Check if visual_analyst was delegated to
    visual_analyst_delegated = "visual_analyst" in graph.delegation_order

    # Check if any specialist was delegated to
    specialists_in_order = [
        agent for agent in graph.delegation_order if is_specialist(agent)
    ]

    # If no specialists delegated, grader not fully applicable
    # (PM might have just done analysis)
    if not specialists_in_order:
        return GraderResult(
            name="visual_analyst_for_images",
            passed=True,
            score=1.0,
            evidence={
                "has_image": True,
                "visual_analyst_delegated": visual_analyst_delegated,
                "specialists_delegated": [],
            },
            reason="No specialists delegated - visual analysis may not be required",
            category=GraderCategory.PM,
            severity="LOW",
        )

    # If specialist delegated but visual_analyst was NOT - this is the failure case
    if not visual_analyst_delegated:
        return GraderResult(
            name="visual_analyst_for_images",
            passed=False,
            score=0.0,
            evidence={
                "has_image": True,
                "visual_analyst_delegated": False,
                "specialists_delegated": specialists_in_order,
                "delegation_order": graph.delegation_order,
            },
            reason=f"Image present but PM skipped visual_analyst - delegated directly to {specialists_in_order} without understanding image content",
            category=GraderCategory.PM,
            severity="HIGH",
        )

    # Check that visual_analyst came BEFORE any specialist
    visual_idx = graph.delegation_order.index("visual_analyst")
    first_specialist_idx = min(
        graph.delegation_order.index(s) for s in specialists_in_order
    )

    if visual_idx >= first_specialist_idx:
        return GraderResult(
            name="visual_analyst_for_images",
            passed=False,
            score=0.5,
            evidence={
                "has_image": True,
                "visual_analyst_delegated": True,
                "visual_analyst_index": visual_idx,
                "first_specialist_index": first_specialist_idx,
                "delegation_order": graph.delegation_order,
            },
            reason=f"visual_analyst delegated at index {visual_idx} but specialist at {first_specialist_idx} - should analyze image BEFORE delegating to specialist",
            category=GraderCategory.PM,
            severity="MEDIUM",
        )

    return GraderResult(
        name="visual_analyst_for_images",
        passed=True,
        score=1.0,
        evidence={
            "has_image": True,
            "visual_analyst_delegated": True,
            "visual_analyst_index": visual_idx,
            "first_specialist_index": first_specialist_idx,
            "specialists_delegated": specialists_in_order,
        },
        reason="Image present, visual_analyst used before specialist (CORRECT - PM used eyes)",
        category=GraderCategory.PM,
        severity="HIGH",
    )


def file_read_before_synthesis(seq: ToolCallSequence) -> GraderResult:
    """Check if PM read analysis files before synthesizing response.

    After analysts write files, PM should read them before responding to user.

    Evaluation logic (all conditions must be met to evaluate PM):
    1. PM delegated to analysts
    2. At least one delegation succeeded
    3. Successful analysts wrote output files
    Only then: check if PM read those files

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()

    Returns:
        GraderResult with pass/fail and evidence
    """
    pm_calls = [tc for tc in seq.tool_calls if tc.agent == "PM"]

    # Find delegation calls to analysts (taxonomy-based)
    analyst_delegations = [
        tc
        for tc in pm_calls
        if tc.tool_name == "task" and is_analyst(tc.parsed_args.get("subagent_type", ""))
    ]

    # Case 1: No analyst delegations
    if not analyst_delegations:
        return GraderResult(
            name="file_read_before_synthesis",
            passed=True,
            score=1.0,
            evidence={"analyst_delegations": 0},
            reason="No analyst delegations - grader not applicable",
            category=GraderCategory.PM,
            severity="LOW",
        )

    # Case 2: Check delegation success
    successful_delegations = [tc for tc in analyst_delegations if tc.status == "success"]
    failed_delegations = [tc for tc in analyst_delegations if tc.status != "success"]

    if not successful_delegations:
        return GraderResult(
            name="file_read_before_synthesis",
            passed=True,
            score=1.0,
            evidence={
                "analyst_delegations": len(analyst_delegations),
                "successful_delegations": 0,
                "failed_delegations": len(failed_delegations),
            },
            reason="All analyst delegations failed - grader not applicable (upstream failure)",
            category=GraderCategory.PM,
            severity="LOW",
        )

    # Case 3: Check if successful analysts wrote output files
    successful_analyst_names = {
        tc.parsed_args.get("subagent_type") for tc in successful_delegations
    }

    # Look for file write operations from successful analysts
    file_write_tools = ("write_file", "write_data", "save_analysis", "persist_analysis")
    analyst_file_writes = [
        tc
        for tc in seq.tool_calls
        if tc.agent in successful_analyst_names
        and tc.tool_name in file_write_tools
        and tc.status == "success"
    ]

    if not analyst_file_writes:
        return GraderResult(
            name="file_read_before_synthesis",
            passed=True,
            score=1.0,
            evidence={
                "analyst_delegations": len(analyst_delegations),
                "successful_delegations": len(successful_delegations),
                "failed_delegations": len(failed_delegations),
                "analyst_file_writes": 0,
                "successful_analysts": list(successful_analyst_names),
            },
            reason="Analysts completed but wrote no output files - grader not applicable",
            category=GraderCategory.PM,
            severity="LOW",
        )

    # Case 4 & 5: Analysts wrote files - now evaluate if PM read them
    pm_read_calls = [tc for tc in pm_calls if tc.tool_name in ("read_file", "read_data")]

    # Check reads came AFTER analyst delegations completed
    last_delegation_seq = max(tc.sequence for tc in successful_delegations)
    reads_after_delegation = [tc for tc in pm_read_calls if tc.sequence > last_delegation_seq]

    passed = len(reads_after_delegation) > 0

    return GraderResult(
        name="file_read_before_synthesis",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence={
            "analyst_delegations": len(analyst_delegations),
            "successful_delegations": len(successful_delegations),
            "failed_delegations": len(failed_delegations),
            "analyst_file_writes": len(analyst_file_writes),
            "files_written_by": [tc.agent for tc in analyst_file_writes],
            "pm_reads_after_delegation": len(reads_after_delegation),
            "last_delegation_seq": last_delegation_seq,
        },
        reason=(
            f"PM read {len(reads_after_delegation)} files after analyst delegations (CORRECT)"
            if passed
            else f"PM did not read analyst output files ({len(analyst_file_writes)} files available from {list(successful_analyst_names)})"
        ),
        category=GraderCategory.PM,
        severity="MEDIUM",
    )
