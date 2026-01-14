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
    file_read_before_synthesis,
    is_analyst,
    is_specialist,
    media_download_first,
    protocol_load_first,
    wave_execution_correct,
)
from .specialist_graders import (
    analyst_file_written,
    analyst_protocol_first,
    hitl_triggered,
    specialist_protocol_loaded,
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
]

# Registry of analyst graders - these run against detected analysts
ANALYST_GRADERS: list[tuple[str, GraderFn, dict]] = [
    ("analyst_protocol_first", analyst_protocol_first, {}),  # agent filled dynamically
    ("analyst_file_written", analyst_file_written, {}),  # agent filled dynamically
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
        GraderSuiteResult with all grader outcomes

    Usage:
        result = run_code_graders(trace_id)
        if result.verdict == "PASS":
            print("All checks passed!")
        else:
            for failure in result.get_failures():
                print(f"FAILED: {failure.name} - {failure.reason}")
    """
    # Load trace data once (shared across all graders)
    seq = get_tool_call_sequence(trace_id)
    graph = get_delegation_graph(trace_id)

    results = []
    all_categories = categories or [
        GraderCategory.PM,
        GraderCategory.SPECIALIST,
        GraderCategory.ANALYST,
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

    # Detect specialists and analysts from trace (taxonomy-based)
    detected_agents = set()
    for tc in seq.tool_calls:
        detected_agents.add(tc.agent)

    specialists_in_trace = [a for a in detected_agents if is_specialist(a)]
    analysts_in_trace = [a for a in detected_agents if is_analyst(a)]

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
    )
