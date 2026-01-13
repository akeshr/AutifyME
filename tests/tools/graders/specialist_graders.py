"""Specialist-specific code graders.

Fast, deterministic checks for specialist behavior:
- HITL gate triggered before persist
- Protocol loading
- Tool mastery patterns
"""

from ..models import ToolCallSequence
from .base import GraderCategory, GraderResult


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
