"""Replay Runner - End-to-End Production Replay Orchestration.

Orchestrates the full replay workflow:
1. Query production outcomes
2. Create scenarios from outcomes
3. Execute via PM
4. Grade with code graders
5. Compare to baseline

Usage:
    from tests.tools.replay_runner import (
        replay_outcome,
        replay_batch,
        ReplayResult,
    )

    # Replay single outcome
    result = replay_outcome(outcome)
    print(f"Verdict: {result.verdict}")

    # Replay batch with filters
    results = replay_batch(days=7, success=True, with_media=True, limit=5)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv

if TYPE_CHECKING:
    from tests.tools.workflow_outcomes import ProductionOutcome

logger = logging.getLogger(__name__)


@dataclass
class ReplayResult:
    """Result of replaying a production outcome."""

    # Source
    source_tracking_id: str
    source_trace_id: str | None
    scenario_id: str

    # Execution
    new_trace_id: str | None
    success: bool
    error: str | None

    # Grading
    grader_verdict: str  # PASS | PARTIAL | FAIL
    grader_score: float
    graders_passed: list[str]
    graders_failed: list[str]

    # Baseline comparison
    baseline_verdict: str | None  # REGRESSION | IMPROVEMENT | NO_CHANGE | None
    baseline_score_delta: float | None

    # Timing
    latency_ms: int
    cost: float

    # Details
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def is_regression(self) -> bool:
        """Check if this replay shows a regression."""
        return self.baseline_verdict == "REGRESSION"


def replay_outcome(
    outcome: ProductionOutcome,
    download_dir: str | Path | None = None,
    compare_baseline: bool = True,
) -> ReplayResult:
    """Replay a single production outcome.

    Args:
        outcome: ProductionOutcome to replay
        download_dir: Directory to download media (default: tests/test_assets/replay)
        compare_baseline: Whether to compare against baseline

    Returns:
        ReplayResult with execution and grading results

    Example:
        from tests.tools.workflow_outcomes import get_outcomes
        outcomes = get_outcomes(with_media=True, limit=1)
        result = replay_outcome(outcomes[0])
        print(f"Verdict: {result.grader_verdict}")
    """
    from tests.tools.pm_interaction import chat_with_pm
    from tests.tools.workflow_outcomes import create_scenario_from_outcome

    load_dotenv()

    # Set default download directory
    if download_dir is None:
        download_dir = Path("tests/test_assets/replay")

    download_dir = Path(download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)

    # Create scenario from outcome
    scenario = create_scenario_from_outcome(
        outcome,
        download_media_to=str(download_dir),
    )

    scenario_id = scenario.id
    source_tracking_id = scenario.source_tracking_id
    source_trace_id = scenario.source_trace_id

    # Get media paths
    media_paths = [a.local_path for a in scenario.media_assets if a.local_path]

    # Execute via PM
    start_time = datetime.now()
    new_trace_id = None
    execution_error = None

    try:
        result = chat_with_pm(
            scenario.message,
            media_paths=media_paths if media_paths else None,
        )
        new_trace_id = result.get("trace_id")
    except Exception as e:
        execution_error = str(e)
        logger.error(f"Replay execution failed: {e}")

    end_time = datetime.now()
    latency_ms = int((end_time - start_time).total_seconds() * 1000)

    # If execution failed, return early
    if execution_error or not new_trace_id:
        return ReplayResult(
            source_tracking_id=source_tracking_id,
            source_trace_id=source_trace_id,
            scenario_id=scenario_id,
            new_trace_id=new_trace_id,
            success=False,
            error=execution_error or "No trace ID returned",
            grader_verdict="FAIL",
            grader_score=0.0,
            graders_passed=[],
            graders_failed=[],
            baseline_verdict=None,
            baseline_score_delta=None,
            latency_ms=latency_ms,
            cost=0.0,
        )

    # Grade the result
    from tests.tools.graders import run_code_graders

    try:
        grades = run_code_graders(new_trace_id)
        grader_verdict = grades.verdict
        grader_score = grades.overall_score
        graders_passed = [r.name for r in grades.results if r.passed]
        graders_failed = [r.name for r in grades.results if not r.passed]
    except Exception as e:
        logger.warning(f"Grading failed: {e}")
        grader_verdict = "FAIL"
        grader_score = 0.0
        graders_passed = []
        graders_failed = []

    # Get cost from trace
    cost = _get_trace_cost(new_trace_id)

    # Compare to baseline if requested
    baseline_verdict = None
    baseline_score_delta = None

    if compare_baseline:
        from tests.tools.eval_results import compare_to_baseline

        grader_results = dict.fromkeys(graders_passed, True)
        grader_results.update(dict.fromkeys(graders_failed, False))

        comparison = compare_to_baseline(
            scenario_id=scenario_id,
            trace_id=new_trace_id,
            current_score=grader_score,
            current_grader_results=grader_results,
            latency_ms=latency_ms,
            cost=cost,
        )

        if comparison:
            baseline_verdict = comparison.verdict
            baseline_score_delta = comparison.score_delta

    return ReplayResult(
        source_tracking_id=source_tracking_id,
        source_trace_id=source_trace_id,
        scenario_id=scenario_id,
        new_trace_id=new_trace_id,
        success=True,
        error=None,
        grader_verdict=grader_verdict,
        grader_score=grader_score,
        graders_passed=graders_passed,
        graders_failed=graders_failed,
        baseline_verdict=baseline_verdict,
        baseline_score_delta=baseline_score_delta,
        latency_ms=latency_ms,
        cost=cost,
        details={
            "scenario_name": scenario.name,
            "media_count": len(media_paths),
            "expected_intent": scenario.expected_intent,
            "expected_success": scenario.expected_success,
        },
    )


def replay_batch(
    days: int = 7,
    intent: str | None = None,
    success: bool | None = None,
    with_media: bool | None = None,
    limit: int = 10,
    download_dir: str | Path | None = None,
    compare_baseline: bool = True,
    stop_on_regression: bool = False,
) -> list[ReplayResult]:
    """Replay a batch of production outcomes.

    Args:
        days: Look back this many days
        intent: Filter by intent
        success: Filter by success status
        with_media: Filter by media presence
        limit: Maximum outcomes to replay
        download_dir: Directory for media downloads
        compare_baseline: Whether to compare against baselines
        stop_on_regression: Stop if regression detected

    Returns:
        List of ReplayResult

    Example:
        # Replay successful outcomes with media
        results = replay_batch(days=7, success=True, with_media=True, limit=5)
        regressions = [r for r in results if r.is_regression]
        print(f"Found {len(regressions)} regressions")
    """
    from tests.tools.workflow_outcomes import get_outcomes

    outcomes = get_outcomes(
        days=days,
        intent=intent,
        success=success,
        with_media=with_media,
        limit=limit,
    )

    if not outcomes:
        logger.info("No outcomes found matching filters")
        return []

    logger.info(f"Replaying {len(outcomes)} outcomes...")

    results = []
    for i, outcome in enumerate(outcomes, 1):
        logger.info(f"[{i}/{len(outcomes)}] Replaying {outcome.tracking_id[:12]}...")

        result = replay_outcome(
            outcome,
            download_dir=download_dir,
            compare_baseline=compare_baseline,
        )
        results.append(result)

        # Log result
        status = "PASS" if result.success and result.grader_verdict == "PASS" else "FAIL"
        logger.info(f"  -> {status} (score: {result.grader_score:.2f})")

        if result.baseline_verdict:
            logger.info(f"  -> Baseline: {result.baseline_verdict}")

        # Stop on regression if requested
        if stop_on_regression and result.is_regression:
            logger.warning("Regression detected! Stopping batch.")
            break

    return results


def format_batch_summary(results: list[ReplayResult]) -> str:
    """Format batch replay summary for display.

    Args:
        results: List of ReplayResult from replay_batch

    Returns:
        Formatted summary string
    """
    if not results:
        return "No results to summarize."

    total = len(results)
    successful = sum(1 for r in results if r.success)
    passed = sum(1 for r in results if r.grader_verdict == "PASS")
    partial = sum(1 for r in results if r.grader_verdict == "PARTIAL")
    failed = sum(1 for r in results if r.grader_verdict == "FAIL")

    regressions = sum(1 for r in results if r.baseline_verdict == "REGRESSION")
    improvements = sum(1 for r in results if r.baseline_verdict == "IMPROVEMENT")

    avg_score = sum(r.grader_score for r in results) / total
    avg_latency = sum(r.latency_ms for r in results) / total
    total_cost = sum(r.cost for r in results)

    lines = [
        f"\n{'=' * 60}",
        "REPLAY BATCH SUMMARY",
        f"{'=' * 60}",
        "",
        f"Execution: {successful}/{total} successful",
        "",
        "Grading:",
        f"  PASS:    {passed}",
        f"  PARTIAL: {partial}",
        f"  FAIL:    {failed}",
        f"  Avg Score: {avg_score:.2f}",
        "",
        "Baseline Comparison:",
        f"  Regressions:  {regressions}",
        f"  Improvements: {improvements}",
        "",
        "Performance:",
        f"  Avg Latency: {avg_latency / 1000:.1f}s",
        f"  Total Cost:  ${total_cost:.4f}",
    ]

    # List regressions if any
    if regressions > 0:
        lines.append("")
        lines.append("REGRESSIONS DETECTED:")
        for r in results:
            if r.is_regression:
                lines.append(f"  - {r.scenario_id}: {r.graders_failed}")

    lines.append(f"{'=' * 60}")

    return "\n".join(lines)


def _get_trace_cost(trace_id: str) -> float:
    """Get total cost for a trace from LangSmith."""
    from langsmith import Client

    try:
        client = Client()
        runs = list(client.list_runs(trace_id=trace_id))
        return sum(r.total_cost or 0 for r in runs)
    except Exception:
        return 0.0
