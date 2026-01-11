# Evaluation Pipeline

**Part of**: [Universal Evaluation Framework](00_INDEX.md)

**Version**: 3.2 - HITL Integration & Unified Grading

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

**NOTE**: All data models defined in [08_SCHEMAS.md](08_SCHEMAS.md). Grading uses the unified `GradingOrchestrator` from [03_GRADER_ARCHITECTURE.md](03_GRADER_ARCHITECTURE.md).

```python
class EvaluationPipeline:
    """
    Complete evaluation pipeline.

    CRITICAL: Routes HITL scenarios to StatefulHITLTestHarness.
    Uses GradingOrchestrator for all grading (no duplicate logic).
    """

    def __init__(
        self,
        langsmith: LangSmithIntegration,
        grading: GradingOrchestrator,  # Single grading implementation
        intelligence: IntelligenceLayer,
        tracker: ImprovementTracker,
        hitl_harness: StatefulHITLTestHarness  # For HITL scenarios
    ):
        self.langsmith = langsmith
        self.grading = grading  # Not GraderRegistry - use orchestrator
        self.intelligence = intelligence
        self.tracker = tracker
        self.hitl_harness = hitl_harness

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

        # Step 2: Separate HITL from regular scenarios
        hitl_scenarios = [s for s in scenarios if self._is_hitl_scenario(s)]
        regular_scenarios = [s for s in scenarios if not self._is_hitl_scenario(s)]

        # Step 3: Execute regular scenarios (auto-approve HITL)
        regular_results = await self._execute_batch(
            regular_scenarios,
            parallelism=options.parallelism,
            hitl_mode="auto_approve"
        )

        # Step 4: Execute HITL scenarios through dedicated harness
        hitl_results = await self._execute_hitl_batch(hitl_scenarios)

        # Step 5: Combine and grade all results
        all_results = regular_results + hitl_results
        judgments = await self._grade_batch(all_results, scenarios)

        # Step 6: Compile report
        report = self._compile_report(judgments, scenarios)

        # Step 7: Compare to baseline (with smoothing)
        if options.baseline_comparison:
            baseline = await self.tracker.get_baseline(suite)
            report.regression_analysis = self._compare_to_baseline(report, baseline)

        # Step 8: Trigger investigation if needed
        if report.failures and options.auto_investigate:
            report.investigation = await self.intelligence.investigate(
                InvestigationTrigger(
                    type="eval_failure",
                    eval_report_id=report.id,
                    scenario_ids=[j.scenario_id for j in report.failures]
                ),
                report.failures
            )

        # Step 9: Store report
        await self._store_report(report)

        return report

    async def run_monitoring(
        self,
        options: "MonitoringOptions" = None
    ) -> MonitoringReport:
        """
        Run monitoring evaluation on existing production traces.

        This mode grades traces WITHOUT re-execution - useful for:
        - Continuous quality monitoring
        - Historical analysis
        - Regression detection without re-running scenarios
        - Sampling production traffic for quality

        Unlike run(), this does NOT execute chat_with_pm().

        Args:
            options: Configuration for monitoring run

        Returns:
            MonitoringReport with aggregated scores and anomalies
        """
        options = options or MonitoringOptions()

        # Step 1: Get traces to evaluate
        trace_ids = await self.langsmith.get_traces_for_monitoring(
            hours=options.time_window_hours,
            sample_rate=options.sample_rate,
            filters=options.filters
        )

        if not trace_ids:
            return MonitoringReport(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                time_window_hours=options.time_window_hours,
                sample_rate=options.sample_rate,
                total_traces_evaluated=0,
                passed_count=0,
                failed_count=0,
                mean_score=0.0,
                min_score=0.0,
                max_score=0.0,
                score_std_dev=0.0
            )

        # Step 2: Grade existing traces
        judgments = await self.langsmith.grade_existing_traces(
            trace_ids=trace_ids,
            grading_config=options.grading_config
        )

        # Step 3: Calculate statistics
        scores = [j.score for j in judgments]
        passed = [j for j in judgments if j.passed]
        failed = [j for j in judgments if not j.passed]

        # Step 4: Detect anomalies (scores significantly below mean)
        mean_score = sum(scores) / len(scores)
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0
        anomaly_threshold = mean_score - (2 * std_dev)  # 2 sigma below

        anomalies = []
        for j in judgments:
            if j.score < anomaly_threshold:
                j.is_anomaly = True
                j.anomaly_reason = f"Score {j.score:.2f} is >2 std below mean {mean_score:.2f}"
                anomalies.append(j)

        # Step 5: Group by domain
        domain_scores = {}
        for j in judgments:
            if j.domain not in domain_scores:
                domain_scores[j.domain] = []
            domain_scores[j.domain].append(j.score)

        domain_means = {
            domain: sum(scores) / len(scores)
            for domain, scores in domain_scores.items()
        }

        # Step 6: Compare to baseline if available
        baseline_comparison = None
        if options.compare_to_baseline:
            baseline = await self.tracker.get_monitoring_baseline()
            if baseline:
                delta = mean_score - baseline.mean_score
                trending = "up" if delta > 0.02 else "down" if delta < -0.02 else "stable"
                baseline_comparison = {
                    "delta": delta,
                    "trending": trending,
                    "baseline_mean": baseline.mean_score
                }

        # Step 7: Build report
        report = MonitoringReport(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            time_window_hours=options.time_window_hours,
            sample_rate=options.sample_rate,
            total_traces_evaluated=len(judgments),
            passed_count=len(passed),
            failed_count=len(failed),
            mean_score=mean_score,
            min_score=min(scores),
            max_score=max(scores),
            score_std_dev=std_dev,
            domain_scores=domain_means,
            anomalies=anomalies,
            judgments=judgments if options.include_all_judgments else [],
            baseline_comparison=baseline_comparison
        )

        # Step 8: Trigger investigation for anomalies if configured
        if anomalies and options.auto_investigate_anomalies:
            await self.intelligence.investigate_anomalies(anomalies)

        # Step 9: Store report
        await self._store_monitoring_report(report)

        return report

    def _is_hitl_scenario(self, scenario: Scenario) -> bool:
        """
        Determine if scenario requires HITL testing.

        HITL scenarios use StatefulHITLTestHarness instead of auto-approve.
        """
        return (
            scenario.grading.mode == GradingMode.PATH_STRICT or
            "hitl" in scenario.metadata.tags or
            any("hitl" in str(b).lower() for b in scenario.expected.behavior)
        )

    async def _execute_batch(
        self,
        scenarios: list[Scenario],
        parallelism: int,
        hitl_mode: str = "auto_approve"
    ) -> list[RolloutResult]:
        """Execute scenarios with controlled parallelism."""
        semaphore = asyncio.Semaphore(parallelism)

        async def execute_one(scenario: Scenario) -> RolloutResult:
            async with semaphore:
                return await self._execute_scenario(scenario, hitl_mode)

        tasks = [execute_one(s) for s in scenarios]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r for r in results if not isinstance(r, Exception)]

    async def _execute_scenario(
        self,
        scenario: Scenario,
        hitl_mode: str
    ) -> RolloutResult:
        """Execute single scenario via PM."""
        result = await chat_with_pm(
            message=scenario.input.message,
            media_paths=[m.path for m in scenario.input.media],
            context=scenario.input.context,
            hitl_mode=hitl_mode
        )

        return RolloutResult(
            scenario_id=scenario.id,
            trace_id=result.trace_id,
            response=result.response,
            routing=result.routing,
            tools_called=result.tools_called,
            success=not result.error
        )

    async def _execute_hitl_batch(
        self,
        scenarios: list[Scenario]
    ) -> list[RolloutResult]:
        """
        Execute HITL scenarios through StatefulHITLTestHarness.

        This tests actual blocking behavior, approval flow, and edit handling.
        """
        results = []

        for scenario in scenarios:
            # Convert to HITLScenario format expected by harness
            hitl_scenario = self._convert_to_hitl_scenario(scenario)

            # Execute through harness (actually pauses, injects approval)
            hitl_result = await self.hitl_harness.execute_hitl_scenario(hitl_scenario)

            # Convert back to RolloutResult
            results.append(RolloutResult(
                scenario_id=scenario.id,
                trace_id=hitl_result.trace_id if hasattr(hitl_result, 'trace_id') else "",
                response=hitl_result.final_response if hasattr(hitl_result, 'final_response') else "",
                routing=[],  # Extracted from trace if needed
                tools_called=[],  # Extracted from trace if needed
                success=hitl_result.passed
            ))

        return results

    def _convert_to_hitl_scenario(self, scenario: Scenario) -> HITLScenario:
        """Convert Scenario to HITLScenario format for harness."""
        # Determine approval action from scenario expectations
        approval_action = "approve"  # Default
        if "reject" in str(scenario.expected.behavior).lower():
            approval_action = "reject"
        elif "edit" in str(scenario.expected.behavior).lower():
            approval_action = "approve_with_edit"

        return HITLScenario(
            input=scenario.input,
            expected_interrupt=scenario.expected.output,
            approval_action=approval_action,
            expected_post_approval=scenario.expected.state_changes
        )

    async def _grade_batch(
        self,
        results: list[RolloutResult],
        scenarios: list[Scenario]
    ) -> list[Judgment]:
        """Grade all results using GradingOrchestrator."""
        scenario_map = {s.id: s for s in scenarios}
        judgments = []

        for result in results:
            scenario = scenario_map[result.scenario_id]
            trace = await self.langsmith.get_trace(result.trace_id)

            # Use unified GradingOrchestrator - NO duplicate logic here
            judgment = await self.grading.grade(scenario, result, trace)
            judgments.append(judgment)

        return judgments

    # NOTE: _grade_one method REMOVED - use self.grading.grade() instead
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
- [03_GRADER_ARCHITECTURE.md](03_GRADER_ARCHITECTURE.md) - GradingOrchestrator (single grading implementation)
- [05_INTELLIGENCE_LAYER.md](05_INTELLIGENCE_LAYER.md) - Investigation on failures
- [07_OPERATIONAL_GUIDE.md](07_OPERATIONAL_GUIDE.md) - StatefulHITLTestHarness, cost concerns
- [08_SCHEMAS.md](08_SCHEMAS.md) - All data models (EvaluationReport, Judgment, RolloutResult)
- [09_IMPLEMENTATION_GUIDE.md](09_IMPLEMENTATION_GUIDE.md) - Bootstrap order and integration contracts
