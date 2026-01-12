# Operational Guide

**Part of**: [Universal Evaluation Framework](00_INDEX.md)

---

## Overview

This document covers operational concerns for running the evaluation framework in production: cost management, HITL testing, scenario versioning, human review SLA, and CLI usage.

---

## Cost Model and Budget Management

**Problem**: Unbounded spend on model graders and investigations.

**Solution**: Cost tracking with budget caps and ROI-based prioritization.

```python
@dataclass
class CostConfig:
    """Cost configuration for evaluation components."""

    # Per-unit costs (USD)
    scenario_execution: float = 0.02      # PM call average
    code_grader: float = 0.0              # Free
    model_grader: float = 0.01            # Claude Haiku for grading
    model_grader_sonnet: float = 0.03     # Claude Sonnet for complex grading
    investigation_l0: float = 0.005       # Minimal tokens
    investigation_l1: float = 0.02        # Focused analysis
    investigation_l2: float = 0.10        # Deep dive
    fix_generation: float = 0.15          # Full fix proposal

    # Budget caps
    daily_eval_budget: float = 50.0       # USD
    daily_investigation_budget: float = 30.0
    per_investigation_cap: float = 5.0    # Max spend per failure


class CostTracker:
    """Track and enforce cost budgets."""

    def __init__(self, config: CostConfig, storage: Storage):
        self.config = config
        self.storage = storage

    async def estimate_eval_cost(
        self,
        scenario_count: int,
        grader_config: list[GraderConfig]
    ) -> CostEstimate:
        """Pre-estimate evaluation cost."""
        execution_cost = scenario_count * self.config.scenario_execution

        grader_cost = 0
        for gc in grader_config:
            if gc.type == "code":
                grader_cost += 0
            elif gc.type == "model":
                grader_cost += scenario_count * self.config.model_grader

        return CostEstimate(
            execution=execution_cost,
            grading=grader_cost,
            total=execution_cost + grader_cost,
            within_budget=self._check_daily_budget(execution_cost + grader_cost)
        )

    async def should_investigate(
        self,
        failure: Judgment,
        failure_impact: float  # 0.0-1.0 based on scenario priority
    ) -> InvestigationDecision:
        """Decide if investigation is worth the cost."""
        remaining_budget = await self._get_remaining_investigation_budget()

        estimated_cost = (
            self.config.investigation_l0 +
            self.config.investigation_l1 * 2 +
            self.config.fix_generation
        )

        # ROI: impact / cost
        roi = failure_impact / estimated_cost

        return InvestigationDecision(
            should_proceed=estimated_cost <= remaining_budget and roi > 0.5,
            estimated_cost=estimated_cost,
            remaining_budget=remaining_budget,
            roi=roi
        )
```

### Daily Cost Report

| Category | Budget | Typical | Max |
|----------|--------|---------|-----|
| Scenario execution (100) | - | $2.00 | $5.00 |
| Code graders | - | $0.00 | $0.00 |
| Model graders | $20 | $3.00 | $10.00 |
| Investigations (5 failures) | $30 | $2.50 | $25.00 |
| **Total** | **$50** | **$7.50** | **$40.00** |

---

## HITL Test Protocol (Stateful Testing)

**Problem**: Can't test "blocked until approval" with auto-approve mode.

**Solution**: Stateful test harness with explicit interrupt injection.

```python
class StatefulHITLTestHarness:
    """Test HITL flows with controlled interrupt injection."""

    def __init__(self, pm_client: PMClient):
        self.pm_client = pm_client

    async def execute_hitl_scenario(
        self,
        scenario: HITLScenario
    ) -> HITLTestResult:
        """Execute scenario with controlled HITL flow."""

        # Phase 1: Start execution (should pause at HITL point)
        execution = await self.pm_client.start_async(
            message=scenario.input.message,
            media_paths=[m.path for m in scenario.input.media],
            context=scenario.input.context,
            hitl_mode="pause"  # Actually pause, don't auto-approve
        )

        # Phase 2: Verify interrupt occurred
        interrupt_check = await self._wait_for_interrupt(
            execution.id,
            timeout_ms=scenario.expected_interrupt_timeout_ms
        )

        if not interrupt_check.interrupted:
            return HITLTestResult(
                passed=False,
                phase_failed="interrupt_expected",
                error="Expected HITL interrupt but execution completed"
            )

        # Phase 3: Verify correct interrupt type and content
        interrupt = interrupt_check.interrupt
        interrupt_validation = self._validate_interrupt(
            interrupt,
            scenario.expected_interrupt
        )

        if not interrupt_validation.valid:
            return HITLTestResult(
                passed=False,
                phase_failed="interrupt_validation",
                error=interrupt_validation.error
            )

        # Phase 4: Inject approval/rejection based on scenario
        if scenario.approval_action == "approve":
            response = await self.pm_client.resume(
                execution_id=execution.id,
                approval=True
            )
        elif scenario.approval_action == "approve_with_edit":
            response = await self.pm_client.resume(
                execution_id=execution.id,
                approval=True,
                edits=scenario.edits
            )
        elif scenario.approval_action == "reject":
            response = await self.pm_client.resume(
                execution_id=execution.id,
                approval=False,
                rejection_reason=scenario.rejection_reason
            )

        # Phase 5: Verify post-approval behavior
        post_approval_check = await self._verify_post_approval(
            response,
            scenario.expected_post_approval
        )

        return HITLTestResult(
            passed=post_approval_check.valid,
            phases_completed=["interrupt", "validation", "injection", "post_approval"],
            interrupt_captured=interrupt,
            final_response=response
        )
```

### HITL Test Categories

| Test | Approval Action | Verifies |
|------|-----------------|----------|
| `hitl_blocks_write` | None (timeout) | Write tool blocked without approval |
| `hitl_approve_proceeds` | approve | Write executes after approval |
| `hitl_edit_respected` | approve_with_edit | Edits applied to final write |
| `hitl_reject_aborts` | reject | Write not executed, user informed |
| `hitl_multi_approval` | approve x2 | Multiple writes need multiple approvals |

---

## Scenario Versioning

**Problem**: Schema/tool changes break scenarios with no migration path.

**Solution**: Versioned scenarios with automated migration.

```python
@dataclass
class VersionedScenario:
    """Scenario with version tracking and migration support."""

    id: str
    input: ScenarioInput
    expected: Expected
    grading: GradingConfig
    metadata: Metadata

    # Versioning
    schema_version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    last_migrated: datetime | None = None
    migration_history: list[str] = field(default_factory=list)

    # Deprecation
    deprecated: bool = False
    deprecation_reason: str | None = None
    replacement_id: str | None = None


class ScenarioMigrator:
    """Handle scenario schema migrations."""

    MIGRATIONS = {
        ("1.0.0", "1.1.0"): migrate_1_0_to_1_1,
        ("1.1.0", "1.2.0"): migrate_1_1_to_1_2,
    }

    async def migrate_all(
        self,
        scenarios: list[VersionedScenario],
        target_version: str
    ) -> MigrationReport:
        """Migrate all scenarios to target version."""
        report = MigrationReport()

        for scenario in scenarios:
            if scenario.schema_version == target_version:
                report.already_current.append(scenario.id)
                continue

            try:
                migrated = await self._migrate_scenario(scenario, target_version)
                report.migrated.append({
                    "id": scenario.id,
                    "from": scenario.schema_version,
                    "to": target_version
                })
            except MigrationError as e:
                report.failed.append({
                    "id": scenario.id,
                    "error": str(e)
                })

        return report


class ToolChangeDetector:
    """Detect tool changes that require scenario migration."""

    async def detect_changes(
        self,
        old_tools: dict[str, ToolSchema],
        new_tools: dict[str, ToolSchema]
    ) -> list[ToolChange]:
        """Detect breaking changes between tool versions."""
        changes = []

        # Removed tools
        for name in old_tools:
            if name not in new_tools:
                changes.append(ToolChange(
                    type="removed",
                    tool=name,
                    impact="breaking"
                ))

        # Renamed tools (heuristic: same schema, different name)
        for old_name, old_schema in old_tools.items():
            if old_name not in new_tools:
                for new_name, new_schema in new_tools.items():
                    if new_name not in old_tools and self._schemas_match(old_schema, new_schema):
                        changes.append(ToolChange(
                            type="renamed",
                            tool=old_name,
                            new_name=new_name,
                            impact="migratable"
                        ))

        return changes
```

---

## Human Review SLA

**Problem**: Annotation queue backs up with no processing guarantee.

**Solution**: SLA-based queue management with automatic fallback.

```python
@dataclass
class HumanReviewSLA:
    """SLA configuration for human review."""

    # Time limits
    calibration_review_hours: int = 24
    edge_case_review_hours: int = 48
    critical_review_hours: int = 4

    # Queue limits
    max_queue_depth: int = 50
    overflow_action: str = "model_fallback"  # "model_fallback" | "skip" | "alert"

    # Minimum review cadence
    min_reviews_per_week: int = 20


class SLAManagedReviewQueue:
    """Human review queue with SLA enforcement."""

    def __init__(self, sla: HumanReviewSLA, langsmith: LangSmithIntegration):
        self.sla = sla
        self.langsmith = langsmith

    async def queue_for_review(
        self,
        trace_id: str,
        priority: str,
        review_type: str
    ) -> QueueResult:
        """Queue trace for review, respecting SLA."""

        queue_status = await self._get_queue_status()

        if queue_status.depth >= self.sla.max_queue_depth:
            return await self._handle_overflow(trace_id, priority, review_type)

        deadline = self._calculate_deadline(priority)

        await self.langsmith.queue_for_human_review(
            trace_ids=[trace_id],
            queue_name=f"{review_type}_{priority}",
            metadata={
                "deadline": deadline.isoformat(),
                "queued_at": datetime.now().isoformat()
            }
        )

        return QueueResult(
            queued=True,
            queue_position=queue_status.depth + 1,
            deadline=deadline
        )

    async def _handle_overflow(
        self,
        trace_id: str,
        priority: str,
        review_type: str
    ) -> QueueResult:
        """Handle queue overflow based on SLA config."""

        if self.sla.overflow_action == "model_fallback":
            model_grade = await self._model_grade_fallback(trace_id)
            return QueueResult(
                queued=False,
                fallback_used=True,
                fallback_result=model_grade,
                reason="Queue at capacity, used model fallback"
            )

        elif self.sla.overflow_action == "skip":
            return QueueResult(
                queued=False,
                skipped=True,
                reason="Queue at capacity, review skipped"
            )

        elif self.sla.overflow_action == "alert":
            await self._send_alert(f"Review queue overflow")
            return await self._force_queue(trace_id, priority)

    async def get_sla_report(self) -> SLAReport:
        """Generate SLA compliance report."""
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        completed = await self._get_completed_reviews(since=week_ago)
        breaches = await self._get_sla_breaches(since=week_ago)

        return SLAReport(
            period_start=week_ago,
            period_end=now,
            reviews_completed=len(completed),
            reviews_target=self.sla.min_reviews_per_week,
            on_track=len(completed) >= self.sla.min_reviews_per_week,
            sla_breaches=len(breaches),
            breach_rate=len(breaches) / len(completed) if completed else 0
        )
```

### SLA Dashboard

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Queue depth | < 50 | > 40 |
| Calibration review time | < 24h | > 20h |
| Critical review time | < 4h | > 2h |
| Weekly reviews | > 20 | < 15 |
| SLA breach rate | < 5% | > 3% |

---

## CLI Reference

### Running Evaluations

```bash
# Run full regression suite
uv run python -m tests.evaluation.cli run --suite regression --parallelism 5

# Run specific categories
uv run python -m tests.evaluation.cli run --suite regression --tags security,hitl

# Dry run (no execution, show what would run)
uv run python -m tests.evaluation.cli run --suite regression --dry-run
```

### Scenario Management

```bash
# Create scenarios from production failures
uv run python -m tests.evaluation.cli create-from-failures --hours 24

# Import scenarios from YAML
uv run python -m tests.evaluation.cli import --file scenarios/new_tests.yaml

# Migrate scenarios to new version
uv run python -m tests.evaluation.cli migrate --suite regression --target-version 1.2.0
```

### Reporting

```bash
# View latest report
uv run python -m tests.evaluation.cli report --latest

# Compare to baseline
uv run python -m tests.evaluation.cli compare --suite regression --baseline latest

# Export report as JSON
uv run python -m tests.evaluation.cli report --latest --format json --output report.json
```

### Investigation

```bash
# Investigate specific report's failures
uv run python -m tests.evaluation.cli investigate --report-id <id>

# Investigate with custom budget
uv run python -m tests.evaluation.cli investigate --report-id <id> --budget 10000

# Validate pending fixes
uv run python -m tests.evaluation.cli validate --all-pending
```

### Cost Management

```bash
# Show today's cost summary
uv run python -m tests.evaluation.cli costs --today

# Estimate cost for suite
uv run python -m tests.evaluation.cli costs --estimate --suite regression

# Set budget
uv run python -m tests.evaluation.cli costs --set-daily-budget 50
```

---

## Integration Points

### CI/CD Integration

```yaml
# .github/workflows/eval.yml
name: Evaluation

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 6 * * *'  # Daily at 6am

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run regression
        run: |
          uv run python -m tests.evaluation.cli run \
            --suite regression \
            --parallelism 10 \
            --fail-on-regression

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: eval-report
          path: reports/latest.json
```

### LangSmith Configuration

```bash
# Required environment variables
export LANGCHAIN_API_KEY=<your-key>
export LANGCHAIN_PROJECT=autifyme-evals
export LANGCHAIN_TRACING_V2=true
```

### Supabase Storage

```python
# Baseline and improvement storage
storage = SupabaseStorage(
    url=os.environ["SUPABASE_URL"],
    key=os.environ["SUPABASE_KEY"],
    table_prefix="eval_"
)
```

---

## Related Documents

- [00_INDEX.md](00_INDEX.md) - Framework overview
- [01_LANGSMITH_FOUNDATION.md](01_LANGSMITH_FOUNDATION.md) - LangSmith integration
- [05_INTELLIGENCE_LAYER.md](05_INTELLIGENCE_LAYER.md) - Investigation cost model
- [06_EVALUATION_PIPELINE.md](06_EVALUATION_PIPELINE.md) - Pipeline execution
