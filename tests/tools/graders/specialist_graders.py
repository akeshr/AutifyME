"""Specialist and universal code graders.

Fast, deterministic checks for specialist behavior:
- HITL gate triggered before persist
- Protocol loading
- Tool mastery patterns

Universal graders (applicable to all agent types):
- Error recovery attempted
"""

from ..models import ToolCallSequence
from .base import GraderCategory, GraderResult

# =============================================================================
# Universal Graders (applicable to all agents)
# =============================================================================


def error_recovery_attempted(seq: ToolCallSequence, agent: str) -> GraderResult:
    """Check if agent attempted recovery after encountering an error.

    If an agent encounters a tool error, it should not give up immediately.
    It should attempt recovery by trying alternative actions or retrying.

    Logic:
    - If no errors occurred: PASS (nothing to recover from)
    - If error occurred AND agent continued with subsequent calls: PASS
    - If error occurred AND agent stopped: FAIL (gave up without trying)
    - GraphInterrupt errors are EXCLUDED (HITL pause, not actual error)

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Agent to check

    Returns:
        GraderResult with pass/fail and evidence
    """
    agent_calls = [tc for tc in seq.tool_calls if tc.agent == agent]

    if not agent_calls:
        return GraderResult(
            name="error_recovery_attempted",
            passed=True,
            score=1.0,
            evidence={"agent": agent, "agent_calls": 0},
            reason=f"No tool calls found for agent {agent} - grader not applicable",
            category=GraderCategory.UNIVERSAL,
            severity="LOW",
        )

    # Find error calls, EXCLUDING GraphInterrupt (HITL pause, not error)
    # GraphInterrupt is how HITL works - workflow intentionally pauses for approval
    error_calls = [
        tc for tc in agent_calls
        if (tc.status == "error" or tc.error)
        and not (tc.error and "GraphInterrupt" in tc.error)
    ]

    # Case 1: No errors - nothing to recover from
    if not error_calls:
        return GraderResult(
            name="error_recovery_attempted",
            passed=True,
            score=1.0,
            evidence={
                "agent": agent,
                "total_calls": len(agent_calls),
                "error_calls": 0,
            },
            reason=f"No errors encountered by {agent} - no recovery needed",
            category=GraderCategory.UNIVERSAL,
            severity="LOW",
        )

    # Case 2: Errors occurred - check if agent continued
    last_error_seq = max(tc.sequence for tc in error_calls)
    calls_after_error = [tc for tc in agent_calls if tc.sequence > last_error_seq]

    # Agent attempted recovery if it made calls after the error
    recovery_attempted = len(calls_after_error) > 0

    if recovery_attempted:
        return GraderResult(
            name="error_recovery_attempted",
            passed=True,
            score=1.0,
            evidence={
                "agent": agent,
                "total_calls": len(agent_calls),
                "error_calls": len(error_calls),
                "last_error_seq": last_error_seq,
                "last_error_tool": next(
                    tc.tool_name for tc in error_calls if tc.sequence == last_error_seq
                ),
                "calls_after_error": len(calls_after_error),
                "recovery_actions": [tc.tool_name for tc in calls_after_error[:3]],
            },
            reason=f"{agent} encountered {len(error_calls)} error(s) and continued with {len(calls_after_error)} recovery action(s)",
            category=GraderCategory.UNIVERSAL,
            severity="MEDIUM",
        )
    else:
        # Agent gave up after error
        first_error = next(tc for tc in error_calls if tc.sequence == min(tc.sequence for tc in error_calls))
        return GraderResult(
            name="error_recovery_attempted",
            passed=False,
            score=0.0,
            evidence={
                "agent": agent,
                "total_calls": len(agent_calls),
                "error_calls": len(error_calls),
                "first_error_seq": first_error.sequence,
                "first_error_tool": first_error.tool_name,
                "first_error_message": first_error.error[:200] if first_error.error else "Unknown error",
                "calls_after_error": 0,
            },
            reason=f"{agent} gave up after error in {first_error.tool_name} - no recovery attempted",
            category=GraderCategory.UNIVERSAL,
            severity="HIGH",
        )


# =============================================================================
# Specialist Graders
# =============================================================================


def hitl_triggered(seq: ToolCallSequence, agent: str = "catalog_specialist") -> GraderResult:
    """Check if HITL approval was requested before persist.

    Specialists must request human approval before persisting data.

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Agent to check (default: catalog_specialist)

    Returns:
        GraderResult with pass/fail and evidence
    """
    agent_calls = [tc for tc in seq.tool_calls if tc.agent == agent]

    # HITL-related tool names (adjust based on actual implementation)
    hitl_names = {
        "interrupt",
        "interrupt_with_approval",
        "request_approval",
        "hitl_gate",
        "await_approval",
    }

    # Persist-related tool names
    persist_names = {
        "save_product",
        "persist",
        "write_to_db",
        "create_product",
        "save_catalog_entry",
        "create_listing",
    }

    hitl_calls = [
        tc
        for tc in agent_calls
        if tc.tool_name in hitl_names or any(h in tc.tool_name.lower() for h in ["interrupt", "approval"])
    ]

    persist_calls = [tc for tc in agent_calls if tc.tool_name in persist_names]

    # If no persist calls, grader not applicable
    if not persist_calls:
        return GraderResult(
            name="hitl_triggered",
            passed=True,
            score=1.0,
            evidence={"agent": agent, "persist_calls": 0},
            reason="No persist calls found - HITL check not applicable",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    # If no HITL calls but persist exists, this is a violation
    if not hitl_calls:
        return GraderResult(
            name="hitl_triggered",
            passed=False,
            score=0.0,
            evidence={
                "agent": agent,
                "hitl_calls": 0,
                "persist_calls": len(persist_calls),
                "first_persist": persist_calls[0].tool_name,
                "first_persist_seq": persist_calls[0].sequence,
            },
            reason=f"No HITL approval request before {len(persist_calls)} persist call(s)",
            category=GraderCategory.SPECIALIST,
            severity="HIGH",
        )

    # Check sequence: HITL should come before persist
    first_hitl_seq = min(tc.sequence for tc in hitl_calls)
    first_persist_seq = min(tc.sequence for tc in persist_calls)
    passed = first_hitl_seq < first_persist_seq

    return GraderResult(
        name="hitl_triggered",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence={
            "agent": agent,
            "first_hitl_seq": first_hitl_seq,
            "first_hitl_tool": next(tc.tool_name for tc in hitl_calls if tc.sequence == first_hitl_seq),
            "first_persist_seq": first_persist_seq,
            "first_persist_tool": persist_calls[0].tool_name,
        },
        reason=f"HITL at seq {first_hitl_seq}, persist at seq {first_persist_seq}"
        + (" (CORRECT)" if passed else " (HITL SHOULD COME BEFORE PERSIST)"),
        category=GraderCategory.SPECIALIST,
        severity="HIGH",
    )


def specialist_protocol_loaded(seq: ToolCallSequence, agent: str) -> GraderResult:
    """Check if specialist loaded protocol as first action.

    Wrapper around protocol_load_first for specialist context.

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Specialist agent to check

    Returns:
        GraderResult with pass/fail and evidence
    """
    from .pm_graders import protocol_load_first

    result = protocol_load_first(seq, agent)
    # Update category to SPECIALIST
    result.category = GraderCategory.SPECIALIST
    return result


def output_file_written(seq: ToolCallSequence, agent: str) -> GraderResult:
    """Check if specialist wrote output file for PM to consume.

    Specialists should write structured output files that PM can read.

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Specialist agent to check

    Returns:
        GraderResult with pass/fail and evidence
    """
    agent_calls = [tc for tc in seq.tool_calls if tc.agent == agent]

    # File write tool names
    write_names = {
        "write_file",
        "write_output",
        "save_analysis",
        "write_data",
    }

    write_calls = [
        tc
        for tc in agent_calls
        if tc.tool_name in write_names or "write" in tc.tool_name.lower()
    ]

    if not agent_calls:
        return GraderResult(
            name="output_file_written",
            passed=True,
            score=1.0,
            evidence={"agent": agent, "agent_calls": 0},
            reason=f"No calls found for agent {agent} - grader not applicable",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    passed = len(write_calls) > 0

    return GraderResult(
        name="output_file_written",
        passed=passed,
        score=1.0 if passed else 0.5,
        evidence={
            "agent": agent,
            "write_calls": len(write_calls),
            "write_tools": [tc.tool_name for tc in write_calls],
        },
        reason=f"{agent} wrote {len(write_calls)} output file(s)"
        + ("" if passed else " (SHOULD WRITE OUTPUT FOR PM)"),
        category=GraderCategory.SPECIALIST,
        severity="MEDIUM",
    )


def analyst_file_written(seq: ToolCallSequence, agent: str) -> GraderResult:
    """Check if analyst wrote analysis file for downstream consumption.

    Analysts should write structured analysis files.

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Analyst agent to check

    Returns:
        GraderResult with pass/fail and evidence
    """
    result = output_file_written(seq, agent)
    result.name = "analyst_file_written"
    result.category = GraderCategory.ANALYST
    return result


def analyst_protocol_first(seq: ToolCallSequence, agent: str) -> GraderResult:
    """Check if analyst loaded protocol as first action.

    Wrapper around protocol_load_first for analyst context.

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Analyst agent to check

    Returns:
        GraderResult with pass/fail and evidence
    """
    from .pm_graders import protocol_load_first

    result = protocol_load_first(seq, agent)
    result.name = "analyst_protocol_first"
    result.category = GraderCategory.ANALYST
    return result


def specialist_read_upstream(seq: ToolCallSequence, agent: str) -> GraderResult:
    """Check if specialist read analyst findings before taking action.

    Specialists should consume analyst output files before executing.
    This ensures specialists work with analyzed data, not raw inputs.

    Logic:
    - Find analysts in trace (by _analyst suffix)
    - Find analyst file writes
    - Check if specialist read files before its first action tool
    - If no analysts participated, grader is not applicable

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Specialist agent to check

    Returns:
        GraderResult with pass/fail and evidence
    """
    from .pm_graders import is_analyst

    agent_calls = [tc for tc in seq.tool_calls if tc.agent == agent]

    if not agent_calls:
        return GraderResult(
            name="specialist_read_upstream",
            passed=True,
            score=1.0,
            evidence={"agent": agent, "agent_calls": 0},
            reason=f"No tool calls found for agent {agent} - grader not applicable",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    # Find all analysts in trace
    all_agents = {tc.agent for tc in seq.tool_calls}
    analysts_in_trace = [a for a in all_agents if is_analyst(a)]

    # If no analysts, this grader is not applicable (specialist might work standalone)
    if not analysts_in_trace:
        return GraderResult(
            name="specialist_read_upstream",
            passed=True,
            score=1.0,
            evidence={
                "agent": agent,
                "analysts_in_trace": [],
                "reason": "No analysts participated",
            },
            reason="No analysts in trace - upstream read check not applicable",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    # Find analyst file writes
    write_tools = {"write_file", "write_output", "save_analysis", "write_data"}
    analyst_writes = [
        tc
        for tc in seq.tool_calls
        if tc.agent in analysts_in_trace
        and (tc.tool_name in write_tools or "write" in tc.tool_name.lower())
    ]

    # If analysts didn't write files, this grader is not applicable
    if not analyst_writes:
        return GraderResult(
            name="specialist_read_upstream",
            passed=True,
            score=1.0,
            evidence={
                "agent": agent,
                "analysts_in_trace": analysts_in_trace,
                "analyst_writes": 0,
            },
            reason="Analysts did not write output files - upstream read check not applicable",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    # Find specialist read_file calls
    read_tools = {"read_file", "read_data", "load_file", "get_file"}
    specialist_reads = [
        tc
        for tc in agent_calls
        if tc.tool_name in read_tools or "read" in tc.tool_name.lower()
    ]

    # Find specialist action tools (non-read, non-protocol tools)
    non_action_tools = read_tools | {"load_protocol", "get_protocol"}
    specialist_actions = [
        tc
        for tc in agent_calls
        if tc.tool_name not in non_action_tools
        and "read" not in tc.tool_name.lower()
        and "protocol" not in tc.tool_name.lower()
    ]

    # Check: Did specialist read BEFORE first action?
    if not specialist_actions:
        # No action tools, just reads - PASS
        return GraderResult(
            name="specialist_read_upstream",
            passed=True,
            score=1.0,
            evidence={
                "agent": agent,
                "analysts_in_trace": analysts_in_trace,
                "analyst_writes": len(analyst_writes),
                "specialist_reads": len(specialist_reads),
                "specialist_actions": 0,
            },
            reason=f"Specialist made {len(specialist_reads)} reads with no action tools",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    first_action_seq = min(tc.sequence for tc in specialist_actions)

    # Did specialist read anything before first action?
    reads_before_action = [tc for tc in specialist_reads if tc.sequence < first_action_seq]
    passed = len(reads_before_action) > 0

    return GraderResult(
        name="specialist_read_upstream",
        passed=passed,
        score=1.0 if passed else 0.3,
        evidence={
            "agent": agent,
            "analysts_in_trace": analysts_in_trace,
            "analyst_writes": len(analyst_writes),
            "analyst_write_files": [
                tc.parsed_args.get("path", tc.parsed_args.get("file_path", "unknown"))
                for tc in analyst_writes[:3]
            ],
            "specialist_reads": len(specialist_reads),
            "reads_before_action": len(reads_before_action),
            "first_action_seq": first_action_seq,
            "first_action_tool": next(
                tc.tool_name for tc in specialist_actions if tc.sequence == first_action_seq
            ),
        },
        reason=(
            f"{agent} read {len(reads_before_action)} file(s) before first action (CORRECT)"
            if passed
            else f"{agent} took action at seq {first_action_seq} without reading analyst findings"
        ),
        category=GraderCategory.SPECIALIST,
        severity="MEDIUM",
    )


# =============================================================================
# Creative Specialist Graders
# =============================================================================


def image_studio_fidelity_included(
    seq: ToolCallSequence, agent: str = "creative_specialist"
) -> GraderResult:
    """Check if image_studio calls include fidelity spec for product identity preservation.

    Fidelity is CRITICAL when processing source product images - without it, the AI may
    alter product colors, artwork, or texture. The product owner wouldn't recognize their product.

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Agent to check (default: creative_specialist)

    Returns:
        GraderResult with pass/fail and evidence
    """
    agent_calls = [tc for tc in seq.tool_calls if tc.agent == agent]
    image_studio_calls = [tc for tc in agent_calls if tc.tool_name == "image_studio"]

    if not image_studio_calls:
        return GraderResult(
            name="image_studio_fidelity_included",
            passed=True,
            score=1.0,
            evidence={"agent": agent, "image_studio_calls": 0},
            reason=f"No image_studio calls found for {agent} - grader not applicable",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    calls_without_fidelity: list[dict] = []

    for tc in image_studio_calls:
        args = tc.parsed_args or {}
        fidelity = args.get("fidelity")

        if not fidelity:
            calls_without_fidelity.append({"sequence": tc.sequence})

    if not calls_without_fidelity:
        return GraderResult(
            name="image_studio_fidelity_included",
            passed=True,
            score=1.0,
            evidence={
                "agent": agent,
                "image_studio_calls": len(image_studio_calls),
                "all_have_fidelity": True,
            },
            reason=f"All {len(image_studio_calls)} image_studio call(s) include fidelity spec",
            category=GraderCategory.SPECIALIST,
            severity="HIGH",
        )
    else:
        score = max(0.0, 1.0 - (len(calls_without_fidelity) / len(image_studio_calls)))
        return GraderResult(
            name="image_studio_fidelity_included",
            passed=False,
            score=score,
            evidence={
                "agent": agent,
                "image_studio_calls": len(image_studio_calls),
                "calls_without_fidelity": calls_without_fidelity,
            },
            reason=f"{len(calls_without_fidelity)} of {len(image_studio_calls)} image_studio call(s) missing fidelity spec - product identity at risk",
            category=GraderCategory.SPECIALIST,
            severity="HIGH",
        )


def image_studio_core_specs_included(
    seq: ToolCallSequence, agent: str = "creative_specialist"
) -> GraderResult:
    """Check if image_studio calls include core specs that prevent garbage output.

    Based on the "garbage hero shot" anti-pattern, these specs are essential:
    - fidelity: Without it, AI generates colors (product identity at risk)
    - focus: Without it, random depth of field
    - lighting OR material_treatment: Either gives rendering hints
    - composition OR output: At least framing/size specified

    This is principle-based, not a checklist of all 8 specs. It catches the
    "minimal call = garbage" pattern without being overly prescriptive.

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Agent to check (default: creative_specialist)

    Returns:
        GraderResult with pass/fail and evidence
    """
    agent_calls = [tc for tc in seq.tool_calls if tc.agent == agent]
    image_studio_calls = [tc for tc in agent_calls if tc.tool_name == "image_studio"]

    if not image_studio_calls:
        return GraderResult(
            name="image_studio_core_specs_included",
            passed=True,
            score=1.0,
            evidence={"agent": agent, "image_studio_calls": 0},
            reason=f"No image_studio calls found for {agent} - grader not applicable",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    calls_missing_core_specs: list[dict] = []

    for tc in image_studio_calls:
        args = tc.parsed_args or {}
        missing = []

        # Core spec 1: fidelity (CRITICAL for product identity)
        if not args.get("fidelity"):
            missing.append("fidelity")

        # Core spec 2: focus (prevents random DOF)
        if not args.get("focus"):
            missing.append("focus")

        # Core spec 3: lighting OR material_treatment (rendering hints)
        if not args.get("lighting") and not args.get("material_treatment"):
            missing.append("lighting|material_treatment")

        # Core spec 4: composition OR output (framing/size)
        if not args.get("composition") and not args.get("output"):
            missing.append("composition|output")

        if missing:
            calls_missing_core_specs.append({
                "sequence": tc.sequence,
                "missing_specs": missing,
            })

    if not calls_missing_core_specs:
        return GraderResult(
            name="image_studio_core_specs_included",
            passed=True,
            score=1.0,
            evidence={
                "agent": agent,
                "image_studio_calls": len(image_studio_calls),
                "all_have_core_specs": True,
            },
            reason=f"All {len(image_studio_calls)} image_studio call(s) include core specs",
            category=GraderCategory.SPECIALIST,
            severity="HIGH",
        )
    else:
        # Calculate score based on how many calls are missing specs
        score = max(0.0, 1.0 - (len(calls_missing_core_specs) / len(image_studio_calls)))
        return GraderResult(
            name="image_studio_core_specs_included",
            passed=False,
            score=score,
            evidence={
                "agent": agent,
                "image_studio_calls": len(image_studio_calls),
                "calls_missing_core_specs": calls_missing_core_specs,
            },
            reason=f"{len(calls_missing_core_specs)} of {len(image_studio_calls)} image_studio call(s) missing core specs - minimal specs produce garbage output",
            category=GraderCategory.SPECIALIST,
            severity="HIGH",
        )


def image_studio_output_verified(
    seq: ToolCallSequence, agent: str = "creative_specialist"
) -> GraderResult:
    """Check if view_image was called after image_studio to verify output quality.

    Outputs should NEVER be shipped without visual verification.
    Pattern: image_studio -> view_image (verify) -> [iterate or ship]

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Agent to check (default: creative_specialist)

    Returns:
        GraderResult with pass/fail and evidence
    """
    agent_calls = [tc for tc in seq.tool_calls if tc.agent == agent]
    image_studio_calls = [tc for tc in agent_calls if tc.tool_name == "image_studio"]
    view_image_calls = [tc for tc in agent_calls if tc.tool_name == "view_image"]

    if not image_studio_calls:
        return GraderResult(
            name="image_studio_output_verified",
            passed=True,
            score=1.0,
            evidence={"agent": agent, "image_studio_calls": 0},
            reason=f"No image_studio calls found for {agent} - grader not applicable",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    # For each image_studio call, check if view_image was called after it
    unverified_outputs: list[dict] = []

    for studio_call in image_studio_calls:
        # Find view_image calls after this studio call
        subsequent_views = [
            v for v in view_image_calls if v.sequence > studio_call.sequence
        ]

        if not subsequent_views:
            unverified_outputs.append({
                "image_studio_seq": studio_call.sequence,
                "view_image_after": False,
            })

    if not unverified_outputs:
        return GraderResult(
            name="image_studio_output_verified",
            passed=True,
            score=1.0,
            evidence={
                "agent": agent,
                "image_studio_calls": len(image_studio_calls),
                "all_verified": True,
                "view_image_calls": len(view_image_calls),
            },
            reason=f"All {len(image_studio_calls)} image_studio output(s) verified with view_image",
            category=GraderCategory.SPECIALIST,
            severity="MEDIUM",
        )
    else:
        score = max(0.0, 1.0 - (len(unverified_outputs) / len(image_studio_calls)))
        return GraderResult(
            name="image_studio_output_verified",
            passed=False,
            score=score,
            evidence={
                "agent": agent,
                "image_studio_calls": len(image_studio_calls),
                "view_image_calls": len(view_image_calls),
                "unverified_outputs": unverified_outputs,
            },
            reason=f"{len(unverified_outputs)} of {len(image_studio_calls)} image_studio output(s) not verified - shipping without quality check",
            category=GraderCategory.SPECIALIST,
            severity="MEDIUM",
        )


def image_studio_consistency_params(
    seq: ToolCallSequence,
    agent: str = "creative_specialist",
    user_message: str = "",
) -> GraderResult:
    """Check if batch image_studio calls include consistency parameters (seed, temperature).

    For batch operations (multiple items, regeneration, variants), consistency parameters
    are critical to ensure uniform visual output across the set.

    Detection:
    - Multiple image_studio calls in trace = batch scenario
    - User message contains batch keywords = batch scenario
    - Single call without batch context = grader not applicable

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Agent to check (default: creative_specialist)
        user_message: Original user message (for batch keyword detection)

    Returns:
        GraderResult with pass/fail and evidence
    """
    agent_calls = [tc for tc in seq.tool_calls if tc.agent == agent]
    image_studio_calls = [tc for tc in agent_calls if tc.tool_name == "image_studio"]

    if not image_studio_calls:
        return GraderResult(
            name="image_studio_consistency_params",
            passed=True,
            score=1.0,
            evidence={"agent": agent, "image_studio_calls": 0},
            reason=f"No image_studio calls found for {agent} - grader not applicable",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    # Detect batch scenario
    batch_keywords = ["batch", "regenerate", "all", "consistency", "variant", "family", "set", "multiple"]
    is_batch_by_keyword = any(kw in user_message.lower() for kw in batch_keywords)
    is_batch_by_count = len(image_studio_calls) > 1

    is_batch_scenario = is_batch_by_keyword or is_batch_by_count

    if not is_batch_scenario:
        return GraderResult(
            name="image_studio_consistency_params",
            passed=True,
            score=1.0,
            evidence={
                "agent": agent,
                "image_studio_calls": len(image_studio_calls),
                "is_batch_scenario": False,
            },
            reason="Single image_studio call without batch context - consistency params not required",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    # Batch scenario detected - check for consistency params
    calls_analysis: list[dict] = []
    calls_with_seed = 0
    calls_with_temperature = 0

    for tc in image_studio_calls:
        args = tc.parsed_args or {}
        has_seed = args.get("seed") is not None
        has_temperature = args.get("temperature") is not None

        if has_seed:
            calls_with_seed += 1
        if has_temperature:
            calls_with_temperature += 1

        calls_analysis.append({
            "sequence": tc.sequence,
            "has_seed": has_seed,
            "has_temperature": has_temperature,
            "seed_value": args.get("seed"),
            "temperature_value": args.get("temperature"),
        })

    # For batch consistency: ALL calls should have seed, and ideally same seed
    all_have_seed = calls_with_seed == len(image_studio_calls)
    all_have_temperature = calls_with_temperature == len(image_studio_calls)

    # Check if same seed is used across calls (for true batch consistency)
    seed_values = [c["seed_value"] for c in calls_analysis if c["seed_value"] is not None]
    same_seed_used = len(set(seed_values)) == 1 if seed_values else False

    # Scoring:
    # - All have seed + same seed = 1.0 (perfect batch consistency)
    # - All have seed + different seeds = 0.7 (seed used but not for consistency)
    # - Some have seed = 0.4 (partial adoption)
    # - None have seed = 0.0 (no consistency controls for batch)
    if all_have_seed and same_seed_used:
        score = 1.0
        passed = True
        reason = f"All {len(image_studio_calls)} batch calls use same seed ({seed_values[0]}) - maximum consistency"
    elif all_have_seed:
        score = 0.7
        passed = True
        reason = f"All {len(image_studio_calls)} batch calls have seed but values differ - partial consistency"
    elif calls_with_seed > 0:
        score = 0.4
        passed = False
        reason = f"Only {calls_with_seed}/{len(image_studio_calls)} batch calls have seed - inconsistent adoption"
    else:
        score = 0.0
        passed = False
        reason = f"Batch scenario ({len(image_studio_calls)} calls) with NO seed parameters - consistency at risk"

    return GraderResult(
        name="image_studio_consistency_params",
        passed=passed,
        score=score,
        evidence={
            "agent": agent,
            "image_studio_calls": len(image_studio_calls),
            "is_batch_scenario": True,
            "batch_detection": {
                "by_keyword": is_batch_by_keyword,
                "by_count": is_batch_by_count,
            },
            "calls_with_seed": calls_with_seed,
            "calls_with_temperature": calls_with_temperature,
            "same_seed_used": same_seed_used,
            "calls_analysis": calls_analysis,
        },
        reason=reason,
        category=GraderCategory.SPECIALIST,
        severity="MEDIUM",
    )


def specialist_hitl_respected(
    seq: ToolCallSequence,
    agent: str,
    hitl_decision: str | None = None,
) -> GraderResult:
    """Check if specialist honored the HITL decision.

    After HITL approval/rejection/edit, the specialist should act accordingly:
    - Approved: Proceed with persist
    - Rejected: Stop, do not persist
    - Edited: Use edited data for persist

    NOTE: This grader requires multi-turn context. In a single trace, we can only
    check for structural patterns. For full verification, use thread-based analysis.

    Single-trace check:
    - If HITL was triggered and persist followed: structurally correct
    - If HITL was triggered but no persist: might be rejection (needs context)

    Args:
        seq: ToolCallSequence from get_tool_call_sequence()
        agent: Specialist agent to check
        hitl_decision: If known from multi-turn context: 'approved' | 'rejected' | 'edited'

    Returns:
        GraderResult with pass/fail and evidence
    """
    agent_calls = [tc for tc in seq.tool_calls if tc.agent == agent]

    if not agent_calls:
        return GraderResult(
            name="specialist_hitl_respected",
            passed=True,
            score=1.0,
            evidence={"agent": agent, "agent_calls": 0},
            reason=f"No tool calls found for agent {agent} - grader not applicable",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    # HITL-related tool names
    hitl_names = {
        "interrupt",
        "interrupt_with_approval",
        "request_approval",
        "hitl_gate",
        "await_approval",
    }

    # Persist-related tool names
    persist_names = {
        "save_product",
        "persist",
        "write_to_db",
        "create_product",
        "save_catalog_entry",
        "create_listing",
    }

    hitl_calls = [
        tc
        for tc in agent_calls
        if tc.tool_name in hitl_names
        or any(h in tc.tool_name.lower() for h in ["interrupt", "approval"])
    ]

    persist_calls = [tc for tc in agent_calls if tc.tool_name in persist_names]

    # If no HITL calls, this grader is not applicable
    if not hitl_calls:
        return GraderResult(
            name="specialist_hitl_respected",
            passed=True,
            score=1.0,
            evidence={
                "agent": agent,
                "hitl_calls": 0,
                "persist_calls": len(persist_calls),
            },
            reason="No HITL calls found - HITL respect check not applicable",
            category=GraderCategory.SPECIALIST,
            severity="LOW",
        )

    # If hitl_decision is provided (from multi-turn context), validate against it
    if hitl_decision:
        if hitl_decision == "approved":
            # Should have persisted
            passed = len(persist_calls) > 0
            return GraderResult(
                name="specialist_hitl_respected",
                passed=passed,
                score=1.0 if passed else 0.0,
                evidence={
                    "agent": agent,
                    "hitl_decision": hitl_decision,
                    "persist_calls": len(persist_calls),
                },
                reason=(
                    f"HITL approved, {agent} persisted {len(persist_calls)} item(s) (CORRECT)"
                    if passed
                    else f"HITL approved but {agent} did not persist"
                ),
                category=GraderCategory.SPECIALIST,
                severity="HIGH",
            )
        elif hitl_decision == "rejected":
            # Should NOT have persisted
            passed = len(persist_calls) == 0
            return GraderResult(
                name="specialist_hitl_respected",
                passed=passed,
                score=1.0 if passed else 0.0,
                evidence={
                    "agent": agent,
                    "hitl_decision": hitl_decision,
                    "persist_calls": len(persist_calls),
                },
                reason=(
                    f"HITL rejected, {agent} correctly did not persist"
                    if passed
                    else f"HITL rejected but {agent} persisted {len(persist_calls)} item(s) - VIOLATION"
                ),
                category=GraderCategory.SPECIALIST,
                severity="HIGH",
            )
        elif hitl_decision == "edited":
            # Should have persisted (with edited data - can't verify content in code grader)
            passed = len(persist_calls) > 0
            return GraderResult(
                name="specialist_hitl_respected",
                passed=passed,
                score=1.0 if passed else 0.0,
                evidence={
                    "agent": agent,
                    "hitl_decision": hitl_decision,
                    "persist_calls": len(persist_calls),
                    "note": "Content verification requires model grader",
                },
                reason=(
                    f"HITL edited, {agent} persisted {len(persist_calls)} item(s) (content check needs model grader)"
                    if passed
                    else f"HITL edited but {agent} did not persist"
                ),
                category=GraderCategory.SPECIALIST,
                severity="HIGH",
            )

    # No decision provided - single trace structural check only
    # In a single trace with HITL, we expect the trace to end at HITL (awaiting response)
    # OR if this is a resume trace, we'd see HITL followed by persist
    last_hitl_seq = max(tc.sequence for tc in hitl_calls)
    persists_after_hitl = [tc for tc in persist_calls if tc.sequence > last_hitl_seq]

    return GraderResult(
        name="specialist_hitl_respected",
        passed=True,  # Can't definitively fail without decision context
        score=0.8,  # Partial score - structural check only
        evidence={
            "agent": agent,
            "hitl_calls": len(hitl_calls),
            "last_hitl_seq": last_hitl_seq,
            "persist_calls": len(persist_calls),
            "persists_after_hitl": len(persists_after_hitl),
            "note": "Full verification requires multi-turn thread analysis with hitl_decision",
        },
        reason=(
            f"HITL triggered at seq {last_hitl_seq}, {len(persists_after_hitl)} persist(s) followed. "
            f"Full HITL respect check requires thread context."
        ),
        category=GraderCategory.SPECIALIST,
        severity="MEDIUM",
    )
