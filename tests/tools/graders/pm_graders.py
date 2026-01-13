"""PM-specific code graders.

Fast, deterministic checks for PM behavior:
- Protocol loading order
- Media download before delegation
- Analyst-before-specialist two-phase pattern
- Wave execution structure
"""

from ..models import DelegationGraph, ToolCallSequence
from .base import GraderCategory, GraderResult

# Known agent types
ANALYSTS = {"visual_analyst", "product_analyst", "catalog_analyst"}
SPECIALISTS = {"creative_specialist", "catalog_specialist"}


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

    Args:
        graph: DelegationGraph from get_delegation_graph()

    Returns:
        GraderResult with pass/fail and evidence
    """
    order = graph.delegation_order

    # Find indices of analysts and specialists
    analyst_indices = [i for i, agent in enumerate(order) if agent in ANALYSTS]
    specialist_indices = [i for i, agent in enumerate(order) if agent in SPECIALISTS]

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

    Expected pattern for image cataloging:
    - Wave 1: visual_analyst (needs image first)
    - Wave 2: product_analyst || catalog_analyst (can run parallel)
    - Wave 3: specialists (after analysts complete)

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

    # Check visual_analyst in earliest wave (needs image analysis first)
    wave_1_agents = waves.get(1, [])
    if "visual_analyst" in graph.delegation_order and "visual_analyst" not in wave_1_agents:
        deviations.append("visual_analyst not in wave 1 (should analyze image first)")
        score -= 0.3

    # Check analysts and specialists don't overlap in waves
    analyst_waves = set()
    specialist_waves = set()

    for wave_num, agents in waves.items():
        for agent in agents:
            if agent in ANALYSTS:
                analyst_waves.add(wave_num)
            if agent in SPECIALISTS:
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


def file_read_before_synthesis(seq: ToolCallSequence) -> GraderResult:
    """Check if PM read analysis files before synthesizing response.

    After analysts write files, PM should read them before responding to user.

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()

    Returns:
        GraderResult with pass/fail and evidence
    """
    pm_calls = [tc for tc in seq.tool_calls if tc.agent == "PM"]

    # Find file read calls
    read_calls = [tc for tc in pm_calls if tc.tool_name in ("read_file", "read_data")]

    # Find delegation calls to analysts
    analyst_delegations = [
        tc
        for tc in pm_calls
        if tc.tool_name == "task"
        and tc.parsed_args.get("subagent_type") in ANALYSTS
    ]

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

    if not read_calls:
        return GraderResult(
            name="file_read_before_synthesis",
            passed=False,
            score=0.0,
            evidence={
                "analyst_delegations": len(analyst_delegations),
                "read_calls": 0,
            },
            reason="PM delegated to analysts but did not read their output files",
            category=GraderCategory.PM,
            severity="MEDIUM",
        )

    # Check that reads come after delegations
    last_analyst_delegation_seq = max(tc.sequence for tc in analyst_delegations)
    read_after_delegation = [tc for tc in read_calls if tc.sequence > last_analyst_delegation_seq]

    passed = len(read_after_delegation) > 0

    return GraderResult(
        name="file_read_before_synthesis",
        passed=passed,
        score=1.0 if passed else 0.5,
        evidence={
            "analyst_delegations": len(analyst_delegations),
            "last_delegation_seq": last_analyst_delegation_seq,
            "read_calls_after": len(read_after_delegation),
            "total_read_calls": len(read_calls),
        },
        reason=f"PM read {len(read_after_delegation)} files after analyst delegations"
        + (" (CORRECT)" if passed else " (SHOULD READ ANALYST OUTPUT)"),
        category=GraderCategory.PM,
        severity="MEDIUM",
    )
