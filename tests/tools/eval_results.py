"""Store and retrieve evaluation results via LangSmith.

Provides storage for /evaluate skill results as LangSmith feedback
annotations on traces - the single source of truth.

Usage:
    from tests.tools.eval_results import store_eval_result, get_eval_history, EvalResult

    result = EvalResult(
        trace_id="f264838e-...",
        rubric="all",
        score=0.72,
        reasoning="Good intent understanding but synthesis lost attributes",
        evidence={"intent": 0.9, "routing": 0.8, "synthesis": 0.5, ...},
        suggestions=["Ensure all attributes flow to output"]
    )
    store_eval_result(result)
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv
from langsmith import Client

# Lazy client initialization
_client: Client | None = None


def _get_client() -> Client:
    """Get or create LangSmith client."""
    global _client
    if _client is None:
        load_dotenv()
        _client = Client()
    return _client


@dataclass
class EvalResult:
    """Single evaluation result from /evaluate skill."""

    trace_id: str
    """LangSmith trace ID that was evaluated."""

    rubric: str
    """Rubric used: 'all' | 'intent' | 'routing' | etc."""

    score: float
    """Overall score (0.0 - 1.0)."""

    reasoning: str
    """Why this score was given (summary)."""

    evidence: dict[str, Any] = field(default_factory=dict)
    """Per-rubric scores and evidence: {"intent": 0.9, "routing": 0.8, ...}"""

    suggestions: list[str] = field(default_factory=list)
    """How to improve the score."""

    timestamp: datetime = field(default_factory=datetime.now)
    """When evaluation was performed."""

    evaluator: str = "claude_code"
    """Who performed evaluation: 'claude_code' | 'python_grader' | 'human'"""

    verdict: str = ""
    """Overall verdict: EXCELLENT | GOOD | ACCEPTABLE | NEEDS_IMPROVEMENT | FAILED"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata (thread_id, scenario_id, etc.)"""

    def __post_init__(self):
        """Set verdict based on score if not provided."""
        if not self.verdict:
            if self.score >= 0.85:
                self.verdict = "EXCELLENT"
            elif self.score >= 0.70:
                self.verdict = "GOOD"
            elif self.score >= 0.55:
                self.verdict = "ACCEPTABLE"
            elif self.score >= 0.40:
                self.verdict = "NEEDS_IMPROVEMENT"
            else:
                self.verdict = "FAILED"


def store_eval_result(result: EvalResult) -> bool:
    """Store evaluation result in LangSmith as feedback.

    Args:
        result: EvalResult from /evaluate skill

    Returns:
        True if stored successfully

    Example:
        >>> result = EvalResult(
        ...     trace_id="f264838e-...",
        ...     rubric="all",
        ...     score=0.72,
        ...     reasoning="Good overall but synthesis issues",
        ...     evidence={"intent": 0.9, "routing": 0.8, "synthesis": 0.5},
        ...     suggestions=["Improve attribute flow"]
        ... )
        >>> store_eval_result(result)
        True
    """
    try:
        client = _get_client()

        # Get root run ID for trace
        runs = list(client.list_runs(trace_id=result.trace_id, limit=1))
        if not runs:
            print(f"Warning: No runs found for trace {result.trace_id}")
            return False

        run_id = str(runs[0].id)

        # Store overall score as feedback
        client.create_feedback(
            run_id=run_id,
            key=f"eval_{result.rubric}",
            score=result.score,
            value=result.verdict,
            comment=result.reasoning,
        )

        # Store per-rubric scores if available
        if result.evidence:
            for rubric_name, rubric_score in result.evidence.items():
                if isinstance(rubric_score, (int, float)):
                    client.create_feedback(
                        run_id=run_id,
                        key=f"eval_{rubric_name}",
                        score=float(rubric_score),
                    )

        print(f"Stored evaluation in LangSmith for trace {result.trace_id}")
        return True

    except Exception as e:
        print(f"Failed to store in LangSmith: {e}")
        return False


def get_eval_history(
    trace_id: str | None = None,
    days: int = 7,
    rubric: str = "all",
) -> list[EvalResult]:
    """Get previous evaluations from LangSmith feedback.

    Args:
        trace_id: Filter by specific trace (optional)
        days: How many days of history (default: 7)
        rubric: Filter by rubric type (default: "all")

    Returns:
        List of EvalResult, newest first

    Example:
        >>> history = get_eval_history(trace_id="f264838e-...")
        >>> for r in history:
        ...     print(f"{r.timestamp}: {r.score} - {r.verdict}")
    """
    results = []
    client = _get_client()

    try:
        if trace_id:
            # Get feedback for specific trace
            runs = list(client.list_runs(trace_id=trace_id, limit=1))
            if runs:
                feedbacks = list(client.list_feedback(run_ids=[str(runs[0].id)]))
                for fb in feedbacks:
                    if fb.key == f"eval_{rubric}" and fb.score is not None:
                        results.append(
                            EvalResult(
                                trace_id=trace_id,
                                rubric=rubric,
                                score=fb.score,
                                reasoning=fb.comment or "",
                                verdict=fb.value or "",
                                timestamp=fb.created_at or datetime.now(),
                            )
                        )
        else:
            # Get recent traces with evaluations
            start_time = datetime.now() - timedelta(days=days)
            runs = list(
                client.list_runs(
                    project_name="autifyme-dev",
                    is_root=True,
                    start_time=start_time,
                    limit=100,
                )
            )

            for run in runs:
                feedbacks = list(client.list_feedback(run_ids=[str(run.id)]))
                for fb in feedbacks:
                    if fb.key == f"eval_{rubric}" and fb.score is not None:
                        results.append(
                            EvalResult(
                                trace_id=str(run.trace_id),
                                rubric=rubric,
                                score=fb.score,
                                reasoning=fb.comment or "",
                                verdict=fb.value or "",
                                timestamp=fb.created_at or datetime.now(),
                            )
                        )

    except Exception as e:
        print(f"Failed to get history from LangSmith: {e}")

    # Sort by timestamp, newest first
    results.sort(key=lambda r: r.timestamp, reverse=True)
    return results


def get_trace_eval_summary(trace_id: str) -> dict[str, Any] | None:
    """Get evaluation summary for a specific trace.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        Dict with evaluation summary or None if no evaluations found

    Example:
        >>> summary = get_trace_eval_summary("f264838e-...")
        >>> if summary:
        ...     print(f"Score: {summary['score']}")
    """
    client = _get_client()

    try:
        runs = list(client.list_runs(trace_id=trace_id, limit=1))
        if not runs:
            return None

        feedbacks = list(client.list_feedback(run_ids=[str(runs[0].id)]))

        # Find overall eval
        overall = next((fb for fb in feedbacks if fb.key == "eval_all"), None)
        if not overall:
            return None

        # Collect per-rubric scores
        rubric_scores = {}
        for fb in feedbacks:
            if fb.key.startswith("eval_") and fb.key != "eval_all" and fb.score is not None:
                rubric_name = fb.key.replace("eval_", "")
                rubric_scores[rubric_name] = fb.score

        return {
            "trace_id": trace_id,
            "score": overall.score,
            "verdict": overall.value,
            "reasoning": overall.comment,
            "rubric_scores": rubric_scores,
            "timestamp": overall.created_at.isoformat() if overall.created_at else None,
        }

    except Exception as e:
        print(f"Failed to get summary: {e}")
        return None


def get_aggregate_stats(days: int = 7) -> dict[str, Any]:
    """Get aggregate evaluation statistics.

    Args:
        days: How many days of history

    Returns:
        Dict with aggregate statistics

    Example:
        >>> stats = get_aggregate_stats(days=7)
        >>> print(f"Average score: {stats['avg_score']:.2f}")
        >>> print(f"Pass rate: {stats['pass_rate']:.1%}")
    """
    results = get_eval_history(days=days)

    if not results:
        return {
            "total_evaluations": 0,
            "days": days,
        }

    scores = [r.score for r in results]
    verdicts = [r.verdict for r in results]

    # Count by verdict
    verdict_counts = {}
    for v in ["EXCELLENT", "GOOD", "ACCEPTABLE", "NEEDS_IMPROVEMENT", "FAILED"]:
        verdict_counts[v] = verdicts.count(v)

    # Calculate pass rate (EXCELLENT + GOOD + ACCEPTABLE)
    passing = verdict_counts["EXCELLENT"] + verdict_counts["GOOD"] + verdict_counts["ACCEPTABLE"]
    pass_rate = passing / len(results) if results else 0.0

    return {
        "total_evaluations": len(results),
        "days": days,
        "avg_score": sum(scores) / len(scores),
        "min_score": min(scores),
        "max_score": max(scores),
        "pass_rate": pass_rate,
        "verdict_distribution": verdict_counts,
        "unique_traces": len({r.trace_id for r in results}),
    }


# =============================================================================
# Baseline Management
# =============================================================================


@dataclass
class BaselineComparison:
    """Result of comparing trace against baseline."""

    trace_id: str
    baseline_trace_id: str
    scenario_id: str

    # Overall verdict
    regression: bool
    improvement: bool
    verdict: str  # REGRESSION | IMPROVEMENT | NO_CHANGE

    # Score comparison
    current_score: float
    baseline_score: float
    score_delta: float

    # Grader comparison
    graders_regressed: list[str]
    graders_improved: list[str]
    graders_unchanged: list[str]

    # Performance
    latency_delta_ms: int
    cost_delta: float

    details: dict[str, Any] = field(default_factory=dict)


def store_baseline(
    scenario_id: str,
    trace_id: str,
    score: float,
    grader_results: dict[str, bool] | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Store a trace as the baseline for a scenario.

    Stores grader results as LangSmith feedback on the trace.
    You must also update the scenario YAML's baseline_trace_id field.

    Args:
        scenario_id: Scenario ID (e.g., "PM-01")
        trace_id: LangSmith trace ID to use as baseline
        score: Overall score for this baseline
        grader_results: Dict of grader_name -> passed (optional)
        metadata: Additional metadata (optional)

    Returns:
        True if stored successfully

    Example:
        >>> store_baseline("PM-01", "f264838e-...", 0.85)
        True
        >>> # Then update PM-01.yaml: baseline_trace_id: "f264838e-..."
    """
    try:
        client = _get_client()

        # Get root run for trace
        runs = list(client.list_runs(trace_id=trace_id, limit=1))
        if not runs:
            print(f"Warning: No runs found for trace {trace_id}")
            return False

        run_id = str(runs[0].id)

        # Build baseline data
        baseline_data = {
            "scenario_id": scenario_id,
            "trace_id": trace_id,
            "score": score,
            "grader_results": grader_results or {},
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }

        # Store as LangSmith feedback on the trace
        client.create_feedback(
            run_id=run_id,
            key=f"baseline_{scenario_id}",
            score=score,
            value=json.dumps(baseline_data),
            comment=f"Baseline for scenario {scenario_id}",
        )

        print(f"Stored baseline for {scenario_id}: trace={trace_id[:12]}..., score={score:.2f}")
        print(f"  -> Update scenario YAML: baseline_trace_id: \"{trace_id}\"")
        return True

    except Exception as e:
        print(f"Failed to store baseline: {e}")
        return False


def get_baseline(scenario_id: str, baseline_trace_id: str | None = None) -> dict[str, Any] | None:
    """Get baseline data for a scenario from LangSmith.

    Fetches feedback from the baseline trace directly (no iteration).

    Args:
        scenario_id: Scenario ID (e.g., "PM-01")
        baseline_trace_id: Trace ID from scenario's baseline_trace_id field.
                          If None, loads from scenario definition.

    Returns:
        Baseline data dict or None if no baseline exists

    Example:
        >>> from tests.scenarios import load_scenario
        >>> scenario = load_scenario("PM-01")
        >>> baseline = get_baseline("PM-01", scenario.baseline_trace_id)
    """
    # Get baseline trace_id from scenario if not provided
    if baseline_trace_id is None:
        try:
            from tests.scenarios import load_scenario
            scenario = load_scenario(scenario_id)
            baseline_trace_id = scenario.baseline_trace_id
        except Exception:
            return None

    if not baseline_trace_id:
        return None

    try:
        client = _get_client()

        # Direct lookup - get the baseline trace's feedback
        runs = list(client.list_runs(trace_id=baseline_trace_id, limit=1))
        if not runs:
            return None

        feedbacks = list(client.list_feedback(run_ids=[str(runs[0].id)]))
        # LangSmith normalizes keys to lowercase
        expected_key = f"baseline_{scenario_id}".lower()
        for fb in feedbacks:
            if fb.key == expected_key and fb.value:
                # Handle both dict and JSON string
                if isinstance(fb.value, dict):
                    return fb.value
                return json.loads(fb.value)

        return None

    except Exception as e:
        print(f"Failed to get baseline: {e}")
        return None


def compare_to_baseline(
    scenario_id: str,
    trace_id: str,
    current_score: float,
    current_grader_results: dict[str, bool],
    baseline_trace_id: str | None = None,
    latency_ms: int = 0,
    cost: float = 0.0,
) -> BaselineComparison | None:
    """Compare a trace against the scenario baseline.

    Args:
        scenario_id: Scenario ID (e.g., "PM-01")
        trace_id: New trace to compare
        current_score: Current trace's overall score
        current_grader_results: Dict of grader_name -> passed
        baseline_trace_id: Baseline trace ID (loads from scenario if None)
        latency_ms: Current trace latency (optional)
        cost: Current trace cost (optional)

    Returns:
        BaselineComparison or None if no baseline exists

    Example:
        >>> comparison = compare_to_baseline("PM-01", "abc123...", 0.80, {"protocol": True})
        >>> if comparison:
        ...     print(f"Regression: {comparison.regression}")
    """
    baseline = get_baseline(scenario_id, baseline_trace_id)
    if not baseline:
        print(f"No baseline found for scenario {scenario_id}")
        return None

    baseline_score = baseline.get("score", 0.0)
    baseline_graders = baseline.get("grader_results", {})
    baseline_metadata = baseline.get("metadata", {})

    # Calculate score delta
    score_delta = current_score - baseline_score

    # Compare graders
    graders_regressed = []
    graders_improved = []
    graders_unchanged = []

    all_graders = set(current_grader_results.keys()) | set(baseline_graders.keys())
    for grader in all_graders:
        current_passed = current_grader_results.get(grader, False)
        baseline_passed = baseline_graders.get(grader, False)

        if baseline_passed and not current_passed:
            graders_regressed.append(grader)
        elif not baseline_passed and current_passed:
            graders_improved.append(grader)
        else:
            graders_unchanged.append(grader)

    # Determine verdict
    regression = len(graders_regressed) > 0 or score_delta < -0.05
    improvement = len(graders_improved) > 0 and len(graders_regressed) == 0 and score_delta > 0.05

    if regression:
        verdict = "REGRESSION"
    elif improvement:
        verdict = "IMPROVEMENT"
    else:
        verdict = "NO_CHANGE"

    # Calculate performance deltas
    baseline_latency = baseline_metadata.get("latency_ms", 0)
    baseline_cost = baseline_metadata.get("cost", 0.0)

    return BaselineComparison(
        trace_id=trace_id,
        baseline_trace_id=baseline.get("trace_id", ""),
        scenario_id=scenario_id,
        regression=regression,
        improvement=improvement,
        verdict=verdict,
        current_score=current_score,
        baseline_score=baseline_score,
        score_delta=score_delta,
        graders_regressed=graders_regressed,
        graders_improved=graders_improved,
        graders_unchanged=graders_unchanged,
        latency_delta_ms=latency_ms - baseline_latency,
        cost_delta=cost - baseline_cost,
        details={
            "baseline_timestamp": baseline.get("timestamp"),
            "baseline_metadata": baseline_metadata,
        },
    )


def format_baseline_comparison(comparison: BaselineComparison) -> str:
    """Format baseline comparison for display.

    Args:
        comparison: BaselineComparison result

    Returns:
        Formatted string for display
    """
    lines = [
        f"\n{'='*60}",
        f"BASELINE COMPARISON: {comparison.scenario_id}",
        f"{'='*60}",
        f"Verdict: {comparison.verdict}",
        "",
        "Scores:",
        f"  Current:  {comparison.current_score:.2f}",
        f"  Baseline: {comparison.baseline_score:.2f}",
        f"  Delta:    {comparison.score_delta:+.2f}",
    ]

    if comparison.graders_regressed:
        lines.append("")
        lines.append("REGRESSIONS:")
        for g in comparison.graders_regressed:
            lines.append(f"  [!] {g}")

    if comparison.graders_improved:
        lines.append("")
        lines.append("IMPROVEMENTS:")
        for g in comparison.graders_improved:
            lines.append(f"  [+] {g}")

    if comparison.latency_delta_ms != 0:
        lines.append("")
        lines.append(f"Latency delta: {comparison.latency_delta_ms:+d}ms")

    if comparison.cost_delta != 0:
        lines.append(f"Cost delta: ${comparison.cost_delta:+.4f}")

    lines.append(f"{'='*60}")

    return "\n".join(lines)


# CLI entry point
if __name__ == "__main__":
    import json
    import sys

    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python eval_results.py stats [days]")
        print("  python eval_results.py summary <trace_id>")
        print("  python eval_results.py history [trace_id]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "stats":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        stats = get_aggregate_stats(days=days)
        print(json.dumps(stats, indent=2, default=str))

    elif command == "summary":
        if len(sys.argv) < 3:
            print("Error: trace_id required")
            sys.exit(1)
        summary = get_trace_eval_summary(sys.argv[2])
        print(json.dumps(summary, indent=2, default=str))

    elif command == "history":
        trace_id = sys.argv[2] if len(sys.argv) > 2 else None
        history = get_eval_history(trace_id=trace_id)
        for r in history[:10]:
            print(f"{r.timestamp}: {r.trace_id[:12]}... {r.score:.2f} ({r.verdict})")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
