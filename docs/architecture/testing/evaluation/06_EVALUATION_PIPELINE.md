# Evaluation Pipeline

**Part of**: [Universal Evaluation Framework](00_INDEX.md)

---

## Overview

The evaluation pipeline orchestrates scenario execution, grading, and improvement tracking. This document covers the end-to-end flow from trigger to improvement.

---

## Pipeline Flow

```text
+------------------------------------------------------------------------+
|                        EVALUATION PIPELINE                              |
+------------------------------------------------------------------------+
|                                                                        |
|  1. TRIGGER                                                            |
|     - Scheduled (daily regression)                                     |
|     - On-demand (feature validation)                                   |
|     - On-commit (CI/CD)                                                |
|     - Production feedback (failures converted to scenarios)            |
|                                                                        |
|  2. SCENARIO LOADING                                                   |
|     - Load from LangSmith datasets                                     |
|     - Filter by tags, suite, priority                                  |
|     - Apply versioning migrations if needed                            |
|                                                                        |
|  3. EXECUTION                                                          |
|     - Execute via chat_with_pm()                                       |
|     - Capture traces in LangSmith                                      |
|     - Parallel execution with concurrency limits                       |
|                                                                        |
|  4. GRADING                                                            |
|     - Apply graders (code -> model -> human)                           |
|     - Output-only mode by default                                      |
|     - Aggregate scores                                                 |
|                                                                        |
|  5. REPORTING                                                          |
|     - Calculate metrics (pass@k, pass^k)                               |
|     - Compare to baseline                                              |
|     - Identify regressions                                             |
|                                                                        |
|  6. INVESTIGATION (if failures)                                        |
|     - Trigger Intelligence Layer                                       |
|     - Generate fix proposals                                           |
|     - Create regression scenarios                                      |
|                                                                        |
|  7. IMPROVEMENT                                                        |
|     - Apply fixes                                                      |
|     - Run k-out-of-n validation                                        |
|     - Update baseline                                                  |
|                                                                        |
+------------------------------------------------------------------------+
```

---

## Pipeline Implementation

```python
class EvaluationPipeline:
    """Complete evaluation pipeline."""

    def __init__(
        self,
        langsmith: LangSmithIntegration,
        graders: GraderRegistry,
        intelligence: IntelligenceLayer,
        tracker: ImprovementTracker
    ):
        self.langsmith = langsmith
        self.graders = graders
        self.intelligence = intelligence
        self.tracker = tracker

    async def run(
        self,
        suite: str,
        options: PipelineOptions = None
    ) -> EvaluationReport:
        """Run full evaluation pipeline."""

        options = options or PipelineOptions()

        # Step 1: Load scenarios
        scenarios = await self.langsmith.load_dataset(suite)

        if options.filter_tags:
            scenarios = [s for s in scenarios if any(
                t in s.metadata.tags for t in options.filter_tags
            )]

        # Step 2: Execute scenarios
        results = await self._execute_batch(
            scenarios,
            parallelism=options.parallelism
        )

        # Step 3: Grade results
        judgments = await self._grade_batch(results, scenarios)

        # Step 4: Compile report
        report = self._compile_report(judgments, scenarios)

        # Step 5: Compare to baseline
        if options.baseline_comparison:
            baseline = await self.tracker.get_baseline(suite)
            report.regression_analysis = self._compare_to_baseline(report, baseline)

        # Step 6: Trigger investigation if needed
        if report.failures and options.auto_investigate:
            report.investigation = await self.intelligence.investigate(
                InvestigationTrigger(
                    type="eval_failure",
                    eval_report_id=report.id,
                    scenario_ids=[j.scenario_id for j in report.failures]
                ),
                report.failures
            )

        # Step 7: Store report
        await self._store_report(report)

        return report

    async def _execute_batch(
        self,
        scenarios: list[Scenario],
        parallelism: int
    ) -> list[RolloutResult]:
        """Execute scenarios with controlled parallelism."""
        semaphore = asyncio.Semaphore(parallelism)
        results = []

        async def execute_one(scenario: Scenario) -> RolloutResult:
            async with semaphore:
                return await self._execute_scenario(scenario)

        tasks = [execute_one(s) for s in scenarios]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r for r in results if not isinstance(r, Exception)]

    async def _execute_scenario(
        self,
        scenario: Scenario
    ) -> RolloutResult:
        """Execute single scenario via PM."""
        result = await chat_with_pm(
            message=scenario.input.message,
            media_paths=[m.path for m in scenario.input.media],
            context=scenario.input.context,
            hitl_mode="auto_approve"  # For testing
        )

        return RolloutResult(
            scenario_id=scenario.id,
            trace_id=result.trace_id,
            response=result.response,
            routing=result.routing,
            tools_called=result.tools_called,
            success=not result.error
        )

    async def _grade_batch(
        self,
        results: list[RolloutResult],
        scenarios: list[Scenario]
    ) -> list[Judgment]:
        """Grade all results."""
        scenario_map = {s.id: s for s in scenarios}
        judgments = []

        for result in results:
            scenario = scenario_map[result.scenario_id]
            trace = await self.langsmith.get_trace(result.trace_id)

            judgment = await self._grade_one(result, scenario, trace)
            judgments.append(judgment)

        return judgments

    async def _grade_one(
        self,
        result: RolloutResult,
        scenario: Scenario,
        trace: TraceForEval
    ) -> Judgment:
        """Apply graders to single result."""
        grader_results = []

        for grader_config in scenario.grading.graders:
            grader = self.graders.get(grader_config.name)
            grade = await grader.grade(
                output=result.response,
                expected=scenario.expected,
                trace=trace,
                config=grader_config.config
            )
            grader_results.append(GraderResult(
                grader=grader_config.name,
                grade=grade,
                weight=grader_config.weight
            ))

        # Calculate weighted score
        total_weight = sum(gr.weight for gr in grader_results)
        weighted_score = sum(
            gr.grade.score * gr.weight for gr in grader_results
        ) / total_weight

        return Judgment(
            scenario_id=scenario.id,
            passed=weighted_score >= scenario.grading.pass_threshold,
            score=weighted_score,
            grader_results=grader_results,
            trace_id=result.trace_id
        )
```

---

## Metrics

### pass@k and pass^k

```python
class EvalMetrics:
    """Evaluation metrics calculations."""

    @staticmethod
    def pass_at_k(judgments_per_scenario: dict[str, list[Judgment]], k: int) -> float:
        """
        % of scenarios passing AT LEAST ONCE in k tries.
        High pass@k but low pass^k = inconsistent but capable.
        """
        passing = 0
        for scenario_id, js in judgments_per_scenario.items():
            if any(j.passed for j in js[:k]):
                passing += 1
        return passing / len(judgments_per_scenario)

    @staticmethod
    def pass_k(judgments_per_scenario: dict[str, list[Judgment]], k: int) -> float:
        """
        % of scenarios passing ALL k tries (consistency metric).
        High pass^k = reliable, consistent behavior.
        """
        consistent = 0
        for scenario_id, js in judgments_per_scenario.items():
            if all(j.passed for j in js[:k]):
                consistent += 1
        return consistent / len(judgments_per_scenario)

    @staticmethod
    def score_distribution(judgments: list[Judgment]) -> dict:
        """Distribution of scores for analysis."""
        scores = [j.score for j in judgments]
        return {
            "mean": sum(scores) / len(scores),
            "min": min(scores),
            "max": max(scores),
            "std": statistics.stdev(scores) if len(scores) > 1 else 0,
            "below_threshold": len([s for s in scores if s < 0.7])
        }
```

---

## Continuous Improvement Loop

```text
+-------------------------------------------------------------------+
|                   IMPROVEMENT LOOP                                 |
+-------------------------------------------------------------------+
|                                                                   |
|  EVAL FAILURE                                                     |
|       |                                                           |
|       v                                                           |
|  +--------------------+                                           |
|  | INTELLIGENCE LAYER |  <-- Analyze failures, find root cause    |
|  +--------------------+                                           |
|       |                                                           |
|       v                                                           |
|  +--------------------+                                           |
|  | FIX PROPOSAL       |  <-- Concrete changes with confidence     |
|  +--------------------+                                           |
|       |                                                           |
|       v                                                           |
|  +--------------------+                                           |
|  | VALIDATION (k/n)   |  <-- Statistical validation               |
|  +--------------------+                                           |
|       |                                                           |
|    PASS?                                                          |
|    /    \                                                         |
|   v      v                                                        |
| YES      NO                                                       |
|  |        |                                                       |
|  v        v                                                       |
| UPDATE   ITERATE                                                  |
| BASELINE (new fix)                                                |
|                                                                   |
+-------------------------------------------------------------------+
```

### Improvement Tracker

```python
class ImprovementTracker:
    """Track improvements and baselines."""

    def __init__(self, storage: Storage):
        self.storage = storage

    async def get_baseline(self, suite: str) -> Baseline:
        """Get current baseline for suite."""
        return await self.storage.get(f"baseline_{suite}")

    async def update_baseline(
        self,
        suite: str,
        report: EvaluationReport
    ):
        """Update baseline with new passing scores."""
        current = await self.get_baseline(suite) or Baseline(scores={})

        for j in report.judgments:
            if j.passed:
                current.scores[j.scenario_id] = j.score

        current.updated_at = datetime.now()
        current.report_id = report.id

        await self.storage.put(f"baseline_{suite}", current)

    async def record_improvement(
        self,
        fix: FixProposal,
        validation_result: ValidationResult,
        investigation_id: str
    ):
        """Record successful improvement for future reference."""
        improvement = Improvement(
            id=str(uuid4()),
            fix=fix,
            validation=validation_result,
            investigation_id=investigation_id,
            timestamp=datetime.now(),
            status="validated" if validation_result.passed else "failed"
        )

        await self.storage.append("improvements", improvement)

        # Update Pattern Library if this is a new pattern
        if validation_result.passed and fix.confidence >= 0.85:
            await self._add_to_pattern_library(fix, investigation_id)
```

---

## Reporting

```python
@dataclass
class EvaluationReport:
    """Complete evaluation report."""

    # Identity
    id: str
    suite: str
    timestamp: datetime

    # Summary
    total_scenarios: int
    passed: int
    failed: int
    pass_rate: float

    # Details
    judgments: list[Judgment]

    @property
    def failures(self) -> list[Judgment]:
        return [j for j in self.judgments if not j.passed]

    # Metrics
    metrics: dict  # pass@k, pass^k, score distribution

    # Regression analysis (if baseline comparison)
    regression_analysis: RegressionAnalysis | None = None

    # Investigation (if auto-triggered)
    investigation: InvestigationSession | None = None


@dataclass
class RegressionAnalysis:
    """Analysis comparing to baseline."""

    baseline_id: str
    new_failures: list[str]  # Scenario IDs that newly failed
    fixed: list[str]  # Scenario IDs that newly passed
    stable_pass: list[str]
    stable_fail: list[str]
    score_delta: dict[str, float]  # scenario_id -> score change
```

---

## CLI Interface

```bash
# Run evaluation
uv run python -m tests.evaluation.cli run --suite regression --parallelism 5

# Create scenarios from production failures
uv run python -m tests.evaluation.cli create-from-failures --hours 24

# View latest report
uv run python -m tests.evaluation.cli report --latest

# Compare to baseline
uv run python -m tests.evaluation.cli compare --suite regression --baseline latest

# Validate pending fixes
uv run python -m tests.evaluation.cli validate --all-pending

# Run investigation on specific failures
uv run python -m tests.evaluation.cli investigate --report-id <id>
```

---

## Related Documents

- [01_LANGSMITH_FOUNDATION.md](01_LANGSMITH_FOUNDATION.md) - Trace and dataset management
- [03_GRADER_ARCHITECTURE.md](03_GRADER_ARCHITECTURE.md) - Graders used in pipeline
- [05_INTELLIGENCE_LAYER.md](05_INTELLIGENCE_LAYER.md) - Investigation on failures
- [07_OPERATIONAL_GUIDE.md](07_OPERATIONAL_GUIDE.md) - Cost and operational concerns
