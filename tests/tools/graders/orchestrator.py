"""Grading orchestrator - runs code graders on traces.

Provides the main entry point for running grader suites.

Usage:
    from tests.tools.graders import run_code_graders

    result = run_code_graders(trace_id)
    print(result.format_summary())
"""

from collections.abc import Callable

from ..trace_analysis import get_delegation_graph, get_tool_call_sequence
from .base import GraderCategory, GraderResult, GraderSuiteResult
from .pm_graders import (
    analyst_before_specialist,
    classify_agents,
    file_read_before_synthesis,
    is_analyst,
    is_reviewer,
    is_specialist,
    media_download_first,
    protocol_load_first,
    wave_execution_correct,
)
from .specialist_graders import (
    analyst_file_written,
    analyst_protocol_first,
    error_recovery_attempted,
    hitl_triggered,
    image_studio_core_specs_included,
    image_studio_fidelity_included,
    image_studio_output_verified,
    specialist_hitl_respected,
    specialist_protocol_loaded,
    specialist_read_upstream,
)

# Type alias for grader functions
GraderFn = Callable[..., GraderResult]


# Registry of PM graders - each tuple is (name, grader_function, kwargs)
PM_GRADERS: list[tuple[str, GraderFn, dict]] = [
    ("protocol_load_first", protocol_load_first, {"agent": "PM"}),
    ("media_download_first", media_download_first, {}),
    ("analyst_before_specialist", analyst_before_specialist, {}),
    ("wave_execution_correct", wave_execution_correct, {}),
    ("file_read_before_synthesis", file_read_before_synthesis, {}),
]

# Registry of specialist graders - these run against detected specialists
SPECIALIST_GRADERS: list[tuple[str, GraderFn, dict]] = [
    ("hitl_triggered", hitl_triggered, {}),  # agent filled dynamically
    ("specialist_protocol_loaded", specialist_protocol_loaded, {}),  # agent filled dynamically
    ("specialist_read_upstream", specialist_read_upstream, {}),  # agent filled dynamically
    ("specialist_hitl_respected", specialist_hitl_respected, {}),  # agent filled dynamically
]

# Registry of creative specialist graders - these run only against creative_specialist
CREATIVE_SPECIALIST_GRADERS: list[tuple[str, GraderFn, dict]] = [
    ("image_studio_fidelity_included", image_studio_fidelity_included, {"agent": "creative_specialist"}),
    ("image_studio_core_specs_included", image_studio_core_specs_included, {"agent": "creative_specialist"}),
    ("image_studio_output_verified", image_studio_output_verified, {"agent": "creative_specialist"}),
]

# Registry of analyst graders - these run against detected analysts
ANALYST_GRADERS: list[tuple[str, GraderFn, dict]] = [
    ("analyst_protocol_first", analyst_protocol_first, {}),  # agent filled dynamically
    ("analyst_file_written", analyst_file_written, {}),  # agent filled dynamically
]

# Registry of universal graders - these run against ALL detected agents
UNIVERSAL_GRADERS: list[tuple[str, GraderFn, dict]] = [
    ("error_recovery_attempted", error_recovery_attempted, {}),  # agent filled dynamically
]


def _run_grader_safely(
    name: str, grader_fn: GraderFn, category: GraderCategory, **kwargs
) -> GraderResult:
    """Run a grader with error handling.

    Args:
        name: Grader name
        grader_fn: Grader function to call
        category: Category for error result
        **kwargs: Arguments to pass to grader

    Returns:
        GraderResult (success or error)
    """
    try:
        return grader_fn(**kwargs)
    except Exception as e:
        return GraderResult(
            name=name,
            passed=False,
            score=0.0,
            evidence={"error": str(e), "error_type": type(e).__name__},
            reason=f"Grader error: {e}",
            category=category,
            severity="HIGH",
        )


def run_pm_graders(trace_id: str) -> GraderSuiteResult:
    """Run all PM-specific graders on a trace.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        GraderSuiteResult with PM grader outcomes
    """
    # Load trace data once
    seq = get_tool_call_sequence(trace_id)
    graph = get_delegation_graph(trace_id)

    results = []

    for name, grader_fn, default_kwargs in PM_GRADERS:
        # Build kwargs based on what the grader needs
        kwargs = dict(default_kwargs)
        if "seq" in grader_fn.__code__.co_varnames:
            kwargs["seq"] = seq
        if "graph" in grader_fn.__code__.co_varnames:
            kwargs["graph"] = graph

        result = _run_grader_safely(name, grader_fn, GraderCategory.PM, **kwargs)
        results.append(result)

    # Calculate aggregates
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    overall_score = sum(r.score for r in results) / len(results) if results else 0.0

    return GraderSuiteResult(
        trace_id=trace_id,
        total_graders=len(results),
        passed=passed,
        failed=failed,
        overall_score=overall_score,
        results=results,
    )


def run_specialist_graders(trace_id: str) -> GraderSuiteResult:
    """Run all specialist-specific graders on a trace.

    Dynamically detects specialists from trace using taxonomy-based classification.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        GraderSuiteResult with specialist grader outcomes
    """
    seq = get_tool_call_sequence(trace_id)

    # Detect specialists from trace
    detected_agents = {tc.agent for tc in seq.tool_calls}
    specialists = [a for a in detected_agents if is_specialist(a)]

    results = []

    for specialist in specialists:
        for name, grader_fn, default_kwargs in SPECIALIST_GRADERS:
            kwargs = dict(default_kwargs)
            kwargs["agent"] = specialist
            if "seq" in grader_fn.__code__.co_varnames:
                kwargs["seq"] = seq

            grader_name = f"{name}:{specialist}"
            result = _run_grader_safely(
                grader_name, grader_fn, GraderCategory.SPECIALIST, **kwargs
            )
            results.append(result)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    overall_score = sum(r.score for r in results) / len(results) if results else 0.0

    return GraderSuiteResult(
        trace_id=trace_id,
        total_graders=len(results),
        passed=passed,
        failed=failed,
        overall_score=overall_score,
        results=results,
    )


def run_analyst_graders(trace_id: str) -> GraderSuiteResult:
    """Run all analyst-specific graders on a trace.

    Dynamically detects analysts from trace using taxonomy-based classification.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        GraderSuiteResult with analyst grader outcomes
    """
    seq = get_tool_call_sequence(trace_id)

    # Detect analysts from trace
    detected_agents = {tc.agent for tc in seq.tool_calls}
    analysts = [a for a in detected_agents if is_analyst(a)]

    results = []

    for analyst in analysts:
        for name, grader_fn, default_kwargs in ANALYST_GRADERS:
            kwargs = dict(default_kwargs)
            kwargs["agent"] = analyst
            if "seq" in grader_fn.__code__.co_varnames:
                kwargs["seq"] = seq

            grader_name = f"{name}:{analyst}"
            result = _run_grader_safely(
                grader_name, grader_fn, GraderCategory.ANALYST, **kwargs
            )
            results.append(result)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    overall_score = sum(r.score for r in results) / len(results) if results else 0.0

    return GraderSuiteResult(
        trace_id=trace_id,
        total_graders=len(results),
        passed=passed,
        failed=failed,
        overall_score=overall_score,
        results=results,
    )


def run_code_graders(
    trace_id: str,
    categories: list[GraderCategory] | None = None,
) -> GraderSuiteResult:
    """Run all applicable code graders on a trace.

    This is the main entry point for code-based evaluation.
    Runs fast, deterministic checks that cost nothing.

    Args:
        trace_id: LangSmith trace ID
        categories: Filter to specific categories (default: all)

    Returns:
        GraderSuiteResult with all grader outcomes including trace status

    Usage:
        result = run_code_graders(trace_id)
        if result.overall_verdict == "PASS":
            print("Trace succeeded and all behavioral checks passed!")
        elif result.overall_verdict == "ERROR":
            print(f"Trace failed: {result.trace_error}")
        else:
            for failure in result.get_failures():
                print(f"FAILED: {failure.name} - {failure.reason}")
    """
    # Load trace data once (shared across all graders)
    seq = get_tool_call_sequence(trace_id)
    graph = get_delegation_graph(trace_id)

    # Get trace status from LangSmith
    from ..trace_loader import load_trace_for_eval
    trace_data = load_trace_for_eval(trace_id, include_issues=False)
    trace_status = trace_data.status or "unknown"
    trace_error = trace_data.error

    results = []
    warnings = []
    all_categories = categories or [
        GraderCategory.PM,
        GraderCategory.SPECIALIST,
        GraderCategory.ANALYST,
        GraderCategory.UNIVERSAL,
    ]

    # Run PM graders
    if GraderCategory.PM in all_categories:
        for name, grader_fn, default_kwargs in PM_GRADERS:
            kwargs = dict(default_kwargs)
            if "seq" in grader_fn.__code__.co_varnames:
                kwargs["seq"] = seq
            if "graph" in grader_fn.__code__.co_varnames:
                kwargs["graph"] = graph

            result = _run_grader_safely(name, grader_fn, GraderCategory.PM, **kwargs)
            results.append(result)

    # Detect and classify all agents from trace (taxonomy-based)
    detected_agents = set()
    for tc in seq.tool_calls:
        detected_agents.add(tc.agent)

    # Classify agents and detect unclassified ones
    classified = classify_agents(list(detected_agents))
    specialists_in_trace = classified["specialists"]
    analysts_in_trace = classified["analysts"]
    reviewers_in_trace = classified["reviewers"]
    unclassified_agents = [
        a for a in classified["other"]
        if a not in ("PM", "pm", "Project Manager")  # PM is expected, not a warning
    ]

    # Add warning for unclassified agents (excluding PM)
    if unclassified_agents:
        warnings.append(
            f"Unclassified agents detected (no graders run): {', '.join(sorted(unclassified_agents))}. "
            f"Consider renaming to *_analyst, *_specialist, or *_reviewer for proper evaluation."
        )

    # Run specialist graders against each detected specialist
    if GraderCategory.SPECIALIST in all_categories:
        for specialist in specialists_in_trace:
            for name, grader_fn, default_kwargs in SPECIALIST_GRADERS:
                kwargs = dict(default_kwargs)
                kwargs["agent"] = specialist  # Fill agent dynamically
                if "seq" in grader_fn.__code__.co_varnames:
                    kwargs["seq"] = seq

                # Name includes agent for clarity
                grader_name = f"{name}:{specialist}"
                result = _run_grader_safely(
                    grader_name, grader_fn, GraderCategory.SPECIALIST, **kwargs
                )
                results.append(result)

        # Run creative specialist graders if creative_specialist is in trace
        if "creative_specialist" in specialists_in_trace:
            for name, grader_fn, default_kwargs in CREATIVE_SPECIALIST_GRADERS:
                kwargs = dict(default_kwargs)
                if "seq" in grader_fn.__code__.co_varnames:
                    kwargs["seq"] = seq

                result = _run_grader_safely(
                    name, grader_fn, GraderCategory.SPECIALIST, **kwargs
                )
                results.append(result)

    # Run analyst graders against each detected analyst
    if GraderCategory.ANALYST in all_categories:
        for analyst in analysts_in_trace:
            for name, grader_fn, default_kwargs in ANALYST_GRADERS:
                kwargs = dict(default_kwargs)
                kwargs["agent"] = analyst  # Fill agent dynamically
                if "seq" in grader_fn.__code__.co_varnames:
                    kwargs["seq"] = seq

                # Name includes agent for clarity
                grader_name = f"{name}:{analyst}"
                result = _run_grader_safely(
                    grader_name, grader_fn, GraderCategory.ANALYST, **kwargs
                )
                results.append(result)

    # Run universal graders against ALL detected agents (including PM)
    if GraderCategory.UNIVERSAL in all_categories:
        all_agents_for_universal = list(detected_agents)
        for agent in all_agents_for_universal:
            for name, grader_fn, default_kwargs in UNIVERSAL_GRADERS:
                kwargs = dict(default_kwargs)
                kwargs["agent"] = agent
                if "seq" in grader_fn.__code__.co_varnames:
                    kwargs["seq"] = seq

                grader_name = f"{name}:{agent}"
                result = _run_grader_safely(
                    grader_name, grader_fn, GraderCategory.UNIVERSAL, **kwargs
                )
                results.append(result)

    # Calculate aggregates
    if not results:
        return GraderSuiteResult(
            trace_id=trace_id,
            total_graders=0,
            passed=0,
            failed=0,
            overall_score=1.0,
            results=[],
            verdict="PASS",
            trace_status=trace_status,
            trace_error=trace_error,
            warnings=warnings,
        )

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    # Weighted score: HIGH severity failures count more
    high_severity_failures = sum(
        1 for r in results if not r.passed and r.severity == "HIGH"
    )
    if high_severity_failures > 0:
        # Penalize HIGH severity failures more heavily
        overall_score = max(
            0.0,
            sum(r.score for r in results) / len(results) - (high_severity_failures * 0.1),
        )
    else:
        overall_score = sum(r.score for r in results) / len(results)

    return GraderSuiteResult(
        trace_id=trace_id,
        total_graders=len(results),
        passed=passed,
        failed=failed,
        overall_score=overall_score,
        results=results,
        trace_status=trace_status,
        trace_error=trace_error,
        warnings=warnings,
    )
