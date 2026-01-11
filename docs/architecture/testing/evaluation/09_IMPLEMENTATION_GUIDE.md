# Implementation Guide

**Part of**: [Universal Evaluation Framework](00_INDEX.md)

**Version**: 3.2 - Bootstrap and Integration

---

## Overview

This document provides the **implementation order**, dependency resolution, and integration contracts for building the evaluation framework. Follow this sequence to avoid circular dependencies.

---

## Implementation Phases

```text
+===========================================================================+
|                        IMPLEMENTATION PHASES                               |
+===========================================================================+
|                                                                           |
|  PHASE 1: FOUNDATION (No dependencies)                                    |
|  +-------------------------------------------------------------------+   |
|  | 1.1 Schema Package (08_SCHEMAS.md)                                |   |
|  | 1.2 Storage Interface + Supabase Adapter                          |   |
|  | 1.3 Cost Tracker                                                  |   |
|  +-------------------------------------------------------------------+   |
|                                                                           |
|  PHASE 2: OBSERVABILITY (Depends on Phase 1)                              |
|  +-------------------------------------------------------------------+   |
|  | 2.1 ResilientTraceStore (local-first)                             |   |
|  | 2.2 LangSmithIntegration                                          |   |
|  | 2.3 HierarchicalTraceLoader                                       |   |
|  +-------------------------------------------------------------------+   |
|                                                                           |
|  PHASE 3: GRADING (Depends on Phase 1, 2)                                 |
|  +-------------------------------------------------------------------+   |
|  | 3.1 Code Graders                                                  |   |
|  | 3.2 Model Graders                                                 |   |
|  | 3.3 GraderRegistry                                                |   |
|  | 3.4 GradingOrchestrator (single implementation)                   |   |
|  +-------------------------------------------------------------------+   |
|                                                                           |
|  PHASE 4: INTELLIGENCE (Depends on Phase 1, 2, 3)                         |
|  +-------------------------------------------------------------------+   |
|  | 4.1 Pattern Library                                               |   |
|  | 4.2 IntelligenceLayer                                             |   |
|  | 4.3 MultiTrackInvestigator                                        |   |
|  | 4.4 RigorousFixValidator                                          |   |
|  +-------------------------------------------------------------------+   |
|                                                                           |
|  PHASE 5: PIPELINE (Depends on Phase 1-4)                                 |
|  +-------------------------------------------------------------------+   |
|  | 5.1 ScenarioLoader                                                |   |
|  | 5.2 EvaluationPipeline                                            |   |
|  | 5.3 StatefulHITLTestHarness (integrated)                          |   |
|  | 5.4 ImprovementTracker                                            |   |
|  +-------------------------------------------------------------------+   |
|                                                                           |
|  PHASE 6: CLI & INTEGRATION (Depends on Phase 1-5)                        |
|  +-------------------------------------------------------------------+   |
|  | 6.1 CLI Commands                                                  |   |
|  | 6.2 CI/CD Integration                                             |   |
|  | 6.3 Skill Integration (e2e-testing, workflow-evaluation)          |   |
|  +-------------------------------------------------------------------+   |
|                                                                           |
+===========================================================================+
```

---

## Phase 1: Foundation

### 1.1 Schema Package

**Location**: `autifyme_agents/evaluation/schemas/`

Create the schema package as a standalone module that both production code and evaluation code can import:

```
autifyme_agents/
  evaluation/
    __init__.py
    schemas/
      __init__.py
      trace.py      # TraceForEval, Delegation, ToolCall, etc.
      scenario.py   # Scenario, Expected, GradingConfig
      grading.py    # GradeResult, Judgment, GraderSpec
      investigation.py  # Finding, FixProposal, InvestigationSession
      pipeline.py   # EvaluationReport, Baseline, RolloutResult
      cost.py       # CostConfig, CostEstimate
```

**Contract**: Production tracing (LangSmith callbacks) must produce data convertible to `TraceForEval`.

### 1.2 Storage Interface

**Location**: `autifyme_agents/evaluation/storage/`

```python
# storage/interface.py
from abc import ABC, abstractmethod
from typing import Any

class Storage(ABC):
    """Abstract storage interface - see 08_SCHEMAS.md for full definition."""

    @abstractmethod
    async def get(self, key: str) -> Any: ...

    @abstractmethod
    async def put(self, key: str, value: Any) -> None: ...

    @abstractmethod
    async def append(self, collection: str, item: Any) -> None: ...

    @abstractmethod
    async def query(self, collection: str, filters: dict) -> list: ...


# storage/supabase.py
class SupabaseStorage(Storage):
    """Supabase implementation."""

    def __init__(self, url: str, key: str, table_prefix: str = "eval_"):
        self.client = create_client(url, key)
        self.prefix = table_prefix

    async def get(self, key: str) -> Any:
        result = self.client.table(f"{self.prefix}kv").select("*").eq("key", key).single().execute()
        return result.data.get("value") if result.data else None

    # ... implement other methods
```

### 1.3 Cost Tracker

**Location**: `autifyme_agents/evaluation/cost.py`

```python
from .schemas import CostConfig, CostEstimate, InvestigationDecision

class CostTracker:
    """Track and enforce cost budgets."""

    def __init__(self, config: CostConfig, storage: Storage):
        self.config = config
        self.storage = storage

    async def estimate_eval_cost(
        self,
        scenario_count: int,
        grader_specs: list[GraderSpec]
    ) -> CostEstimate:
        """Pre-estimate evaluation cost."""
        # Implementation from 07_OPERATIONAL_GUIDE.md
        ...

    async def should_investigate(
        self,
        failure_impact: float
    ) -> InvestigationDecision:
        """Decide if investigation is worth the cost."""
        # Implementation from 07_OPERATIONAL_GUIDE.md
        ...
```

---

## Phase 2: Observability

### 2.1 ResilientTraceStore

**Location**: `autifyme_agents/evaluation/trace_store.py`

```python
from pathlib import Path
import asyncio
from .schemas import TraceForEval

class ResilientTraceStore:
    """Local-first trace storage with LangSmith sync."""

    def __init__(self, local_path: Path, langsmith: "LangSmithIntegration"):
        self.local_path = local_path
        self.langsmith = langsmith
        self.sync_queue: asyncio.Queue[str] = asyncio.Queue()

        # Ensure local path exists
        self.local_path.mkdir(parents=True, exist_ok=True)

    async def store_trace(self, trace: TraceForEval) -> str:
        """Store locally FIRST, queue for LangSmith sync."""
        # Implementation from 01_LANGSMITH_FOUNDATION.md
        ...

    async def get_trace(self, trace_id: str) -> TraceForEval:
        """Get from local first, fallback to LangSmith."""
        ...

    async def sync_worker(self):
        """Background worker syncing to LangSmith."""
        ...
```

### 2.2 LangSmithIntegration

**Location**: `autifyme_agents/evaluation/langsmith_integration.py`

```python
from langsmith import Client

class LangSmithIntegration:
    """LangSmith integration for evaluation framework."""

    def __init__(self, project_name: str = "autifyme-evals"):
        self.client = Client()
        self.project_name = project_name

    async def get_trace(self, trace_id: str) -> TraceForEval:
        """Retrieve trace and convert to eval format."""
        run = self.client.read_run(trace_id)
        return self._convert_to_eval_format(run)

    def _convert_to_eval_format(self, run) -> TraceForEval:
        """
        Convert LangSmith Run to TraceForEval.

        This is the critical integration point between production
        tracing and evaluation. Map all fields carefully.
        """
        return TraceForEval(
            trace_id=str(run.id),
            thread_id=run.extra.get("thread_id", ""),
            timestamp=run.start_time,
            user_message=run.inputs.get("message", ""),
            media_paths=run.inputs.get("media_paths", []),
            context=run.inputs.get("context", {}),
            pm_reasoning=self._extract_reasoning(run),
            delegations=self._extract_delegations(run),
            tool_calls=self._extract_tool_calls(run),
            interrupts=self._extract_interrupts(run),
            final_response=run.outputs.get("response", ""),
            state_changes=self._extract_state_changes(run),
            total_tokens=run.total_tokens or 0,
            latency_ms=int((run.end_time - run.start_time).total_seconds() * 1000),
            error=str(run.error) if run.error else None
        )
```

### 2.3 HierarchicalTraceLoader

**Location**: `autifyme_agents/evaluation/trace_loader.py`

**IMPORTANT**: Unified signature that accepts optional token budget:

```python
class HierarchicalTraceLoader:
    """3-level lazy loading for efficient trace analysis."""

    def __init__(self, langsmith: LangSmithIntegration):
        self.langsmith = langsmith

    async def load_level_0(
        self,
        trace_id: str,
        max_tokens: int | None = None
    ) -> tuple[TraceOverview, int]:
        """
        Level 0: Structure Overview.

        Returns:
            tuple of (TraceOverview, tokens_used)
        """
        run = self.langsmith.client.read_run(trace_id)
        overview = TraceOverview(
            trace_id=trace_id,
            agents=[r.name for r in self._get_agent_runs(run)],
            tools=[r.name for r in self._get_tool_runs(run)],
            success=run.status == "success",
            total_tokens=run.total_tokens,
            latency_ms=run.latency_ms,
            error_summary=run.error[:100] if run.error else None
        )
        tokens_used = self._estimate_tokens(overview)
        return overview, tokens_used

    async def load_level_1(
        self,
        trace_id: str,
        focus_area: str,
        max_tokens: int | None = None
    ) -> tuple[TraceFocus, int]:
        """
        Level 1: Focused Investigation.

        Args:
            trace_id: The trace to load
            focus_area: Where to focus ("agent:pm", "tool:write_data", "error")
            max_tokens: Optional token budget (truncate if exceeded)

        Returns:
            tuple of (TraceFocus, tokens_used)
        """
        run = self.langsmith.client.read_run(trace_id)

        if focus_area.startswith("agent:"):
            agent_name = focus_area.split(":")[1]
            focus = self._extract_agent_details(run, agent_name)
        elif focus_area.startswith("tool:"):
            tool_name = focus_area.split(":")[1]
            focus = self._extract_tool_details(run, tool_name)
        elif focus_area == "error":
            focus = self._extract_error_context(run)
        else:
            raise ValueError(f"Unknown focus area: {focus_area}")

        tokens_used = self._estimate_tokens(focus)

        # Truncate if over budget
        if max_tokens and tokens_used > max_tokens:
            focus = self._truncate_focus(focus, max_tokens)
            tokens_used = max_tokens

        return focus, tokens_used

    async def load_level_2(
        self,
        trace_id: str,
        max_tokens: int | None = None
    ) -> tuple[TraceDeep, int]:
        """Level 2: Full trace deep dive."""
        ...

    async def load_level_2_chunked(
        self,
        trace_id: str,
        budget: int
    ) -> AsyncIterator[tuple[dict, int]]:
        """Yield trace chunks within budget."""
        ...
```

---

## Phase 3: Grading

### 3.1 Code Graders

**Location**: `autifyme_agents/evaluation/graders/code/`

```python
# graders/code/base.py
from ..schemas import Grader, GradeResult, Expected, TraceForEval

class CodeGrader(Grader):
    """Base class for deterministic code graders."""

    @property
    def grader_type(self) -> str:
        return "code"


# graders/code/tool_graders.py
class RequiredToolsGrader(CodeGrader):
    """Check that required tools were called."""

    @property
    def name(self) -> str:
        return "required_tools_called"

    async def grade(
        self,
        output: Any,
        expected: Expected,
        trace: TraceForEval,
        config: dict | None = None
    ) -> GradeResult:
        required = [t.name for t in expected.tools if t.required]
        called = {tc.tool_name for tc in trace.tool_calls}
        missing = set(required) - called

        return GradeResult(
            passed=len(missing) == 0,
            score=len(called & set(required)) / len(required) if required else 1.0,
            evidence={"missing": list(missing), "called": list(called)}
        )
```

### 3.2 Model Graders

**Location**: `autifyme_agents/evaluation/graders/model/`

```python
# graders/model/base.py
from langchain_anthropic import ChatAnthropic

class ModelGrader(Grader):
    """Base class for LLM-based graders."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.judge = ChatAnthropic(model=model)

    @property
    def grader_type(self) -> str:
        return "model"


# graders/model/hallucination.py
class HallucinationGrader(ModelGrader):
    """Check output for hallucinated information."""

    @property
    def name(self) -> str:
        return "hallucination_check"

    async def grade(
        self,
        output: Any,
        expected: Expected,
        trace: TraceForEval,
        config: dict | None = None
    ) -> GradeResult:
        # Implementation from 03_GRADER_ARCHITECTURE.md
        ...
```

### 3.3 GraderRegistry

**Location**: `autifyme_agents/evaluation/graders/registry.py`

```python
from .code.tool_graders import RequiredToolsGrader, ToolSequenceGrader
from .code.hitl_graders import HITLComplianceGrader
from .code.schema_graders import SchemaComplianceGrader
from .model.hallucination import HallucinationGrader
from .model.synthesis import SynthesisQualityGrader

def create_default_registry() -> GraderRegistry:
    """Create registry with all built-in graders."""
    registry = GraderRegistry()

    # Code graders
    registry.register(RequiredToolsGrader())
    registry.register(ToolSequenceGrader())
    registry.register(HITLComplianceGrader())
    registry.register(SchemaComplianceGrader())

    # Model graders
    registry.register(HallucinationGrader())
    registry.register(SynthesisQualityGrader())

    return registry
```

### 3.4 GradingOrchestrator (SINGLE implementation)

**Location**: `autifyme_agents/evaluation/grading/orchestrator.py`

**CRITICAL**: This is the ONLY grading orchestration. Remove duplicate from Pipeline.

```python
class GradingOrchestrator:
    """
    Single implementation of grading orchestration.

    This replaces both OutputOnlyGrader and Pipeline._grade_one.
    All grading flows through this class.
    """

    def __init__(self, registry: GraderRegistry):
        self.registry = registry

    async def grade(
        self,
        scenario: Scenario,
        result: RolloutResult,
        trace: TraceForEval
    ) -> Judgment:
        """
        Grade a scenario execution.

        Implements output-only grading by default.
        Path deviations are logged but only scored in PATH_STRICT mode.
        """
        grader_outputs: list[GraderOutput] = []
        path_deviations: list[PathDeviation] = []

        # 1. Run configured graders
        for spec in scenario.grading.graders:
            grader = self.registry.get(spec.name)

            start = time.time()
            grade = await grader.grade(
                output=result.response,
                expected=scenario.expected,
                trace=trace,
                config=spec.config
            )
            elapsed_ms = int((time.time() - start) * 1000)

            grader_outputs.append(GraderOutput(
                grader_name=spec.name,
                grader_type=grader.grader_type,
                grade=grade,
                weight=spec.weight,
                execution_time_ms=elapsed_ms
            ))

        # 2. Check for path deviations (logged regardless of mode)
        if scenario.expected.routing:
            actual_routing = [d.target for d in trace.delegations]
            if set(actual_routing) != set(scenario.expected.routing):
                path_deviations.append(PathDeviation(
                    type="routing",
                    expected=scenario.expected.routing,
                    actual=actual_routing,
                    analysis=self._analyze_routing_deviation(
                        scenario.expected.routing, actual_routing
                    )
                ))

        # 3. Calculate weighted score (graders only, not path deviations)
        total_weight = sum(go.weight for go in grader_outputs)
        weighted_score = sum(
            go.grade.score * go.weight for go in grader_outputs
        ) / total_weight if total_weight > 0 else 0.0

        # 4. Apply path deviation penalty ONLY in PATH_STRICT mode
        if scenario.grading.mode == GradingMode.PATH_STRICT and path_deviations:
            weighted_score *= 0.5  # 50% penalty for path deviations

        return Judgment(
            scenario_id=scenario.id,
            trace_id=result.trace_id,
            passed=weighted_score >= scenario.grading.pass_threshold,
            score=weighted_score,
            grader_outputs=grader_outputs,
            path_deviations=path_deviations,
            grading_mode=scenario.grading.mode
        )

    def _analyze_routing_deviation(
        self,
        expected: list[str],
        actual: list[str]
    ) -> str:
        """Explain why routing differed."""
        if set(actual).issubset(set(expected)):
            return "Agent found shorter path (skipped unnecessary specialists)"
        if set(expected).issubset(set(actual)):
            return "Agent used additional specialists (more thorough)"
        return "Different routing strategy"
```

---

## Phase 4: Intelligence

### 4.1 Pattern Library

**Location**: `autifyme_agents/evaluation/intelligence/patterns.py`

```python
class PatternLibrary:
    """
    Library of known failure patterns and their fixes.

    Persistence: Patterns stored in Supabase for durability.
    Bootstrap: Seed with patterns from 02_FAILURE_TAXONOMY.md.
    """

    def __init__(self, storage: Storage):
        self.storage = storage
        self._cache: dict[str, dict] = {}

    async def initialize(self):
        """Load patterns from storage into cache."""
        patterns = await self.storage.query("patterns", {})
        self._cache = {p["name"]: p for p in patterns}

        # Seed built-in patterns if empty
        if not self._cache:
            await self._seed_builtin_patterns()

    async def _seed_builtin_patterns(self):
        """Seed with known patterns from taxonomy."""
        builtin = [
            {
                "name": "pm_routing_single_intent",
                "symptoms": ["correct_routing failed", "single specialist expected"],
                "root_cause": "PM prompt lacks example for this intent type",
                "fix_template": {
                    "target": "prompt",
                    "component": "project_manager.prompt",
                    "change_type": "add_example",
                    "confidence": 0.85
                }
            },
            # ... more patterns from 05_INTELLIGENCE_LAYER.md
        ]

        for pattern in builtin:
            await self.storage.put(f"pattern_{pattern['name']}", pattern)
            self._cache[pattern["name"]] = pattern

    def match(self, findings: list[Finding]) -> dict | None:
        """Match findings against known patterns."""
        symptoms = [f.area for f in findings if f.significance == "symptom"]

        for pattern_name, pattern in self._cache.items():
            if all(s in symptoms for s in pattern["symptoms"]):
                return pattern

        return None

    async def add_pattern(self, pattern: dict):
        """Add new pattern learned from investigation."""
        await self.storage.put(f"pattern_{pattern['name']}", pattern)
        self._cache[pattern["name"]] = pattern
```

---

## Phase 5: Pipeline

### 5.1 EvaluationPipeline (with integrated HITL)

**Location**: `autifyme_agents/evaluation/pipeline.py`

```python
class EvaluationPipeline:
    """
    Complete evaluation pipeline.

    CRITICAL: Routes HITL scenarios to StatefulHITLTestHarness.
    """

    def __init__(
        self,
        langsmith: LangSmithIntegration,
        grading: GradingOrchestrator,
        intelligence: IntelligenceLayer,
        tracker: ImprovementTracker,
        hitl_harness: StatefulHITLTestHarness
    ):
        self.langsmith = langsmith
        self.grading = grading
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

        # Load scenarios
        scenarios = await self.langsmith.load_dataset(suite)

        if options.filter_tags:
            scenarios = [s for s in scenarios if any(
                t in s.metadata.tags for t in options.filter_tags
            )]

        # Separate HITL scenarios from regular scenarios
        hitl_scenarios = [s for s in scenarios if self._is_hitl_scenario(s)]
        regular_scenarios = [s for s in scenarios if not self._is_hitl_scenario(s)]

        # Execute regular scenarios with auto-approve
        regular_results = await self._execute_batch(
            regular_scenarios,
            parallelism=options.parallelism,
            hitl_mode="auto_approve"
        )

        # Execute HITL scenarios through StatefulHITLTestHarness
        hitl_results = await self._execute_hitl_batch(hitl_scenarios)

        # Combine results
        all_results = regular_results + hitl_results

        # Grade all results
        judgments = await self._grade_batch(all_results, scenarios)

        # ... rest of pipeline

    def _is_hitl_scenario(self, scenario: Scenario) -> bool:
        """Check if scenario requires HITL testing."""
        return (
            scenario.grading.mode == GradingMode.PATH_STRICT or
            "hitl" in scenario.metadata.tags or
            any("hitl" in str(b).lower() for b in scenario.expected.behavior)
        )

    async def _execute_hitl_batch(
        self,
        scenarios: list[Scenario]
    ) -> list[RolloutResult]:
        """Execute HITL scenarios through the test harness."""
        results = []

        for scenario in scenarios:
            # Convert scenario to HITLScenario format
            hitl_scenario = self._convert_to_hitl_scenario(scenario)

            # Execute through harness
            hitl_result = await self.hitl_harness.execute_hitl_scenario(hitl_scenario)

            # Convert back to RolloutResult
            results.append(RolloutResult(
                scenario_id=scenario.id,
                trace_id=hitl_result.trace_id,
                response=hitl_result.final_response,
                routing=hitl_result.routing,
                tools_called=hitl_result.tools_called,
                success=hitl_result.passed
            ))

        return results
```

---

## Phase 6: CLI & Integration

### 6.1 CLI Commands

**Location**: `tests/evaluation/cli.py`

```python
import click
from autifyme_agents.evaluation import (
    EvaluationPipeline,
    create_default_registry,
    LangSmithIntegration,
    # ... other imports
)

@click.group()
def cli():
    """Evaluation framework CLI."""
    pass

@cli.command()
@click.option("--suite", required=True, help="Suite name to run")
@click.option("--parallelism", default=5, help="Parallel executions")
@click.option("--tags", default=None, help="Filter by tags (comma-separated)")
@click.option("--dry-run", is_flag=True, help="Show what would run")
def run(suite: str, parallelism: int, tags: str, dry_run: bool):
    """Run evaluation suite."""
    # Implementation
    ...

@cli.command()
@click.option("--hours", default=24, help="Look back hours")
def create_from_failures(hours: int):
    """Create scenarios from production failures."""
    ...

# ... more commands from 07_OPERATIONAL_GUIDE.md
```

---

## Integration Contracts

### Contract 1: Production Tracing -> TraceForEval

Production code must emit traces compatible with `TraceForEval`:

```python
# In production PM code
from autifyme_agents.evaluation.schemas import TraceForEval

# LangSmith callback should capture:
# - inputs.message, inputs.media_paths, inputs.context
# - All child runs (delegations, tool calls)
# - outputs.response
# - Any interrupts (HITL)
# - State changes (via tool results)
```

### Contract 2: chat_with_pm Interface

```python
@dataclass
class PMResult:
    """Result from chat_with_pm that evaluation expects."""
    response: str
    trace_id: str
    routing: list[str]
    tools_called: list[str]
    error: str | None = None

async def chat_with_pm(
    message: str,
    media_paths: list[str] = None,
    context: dict = None,
    hitl_mode: str = "auto_approve"  # "auto_approve" | "pause" | "skip"
) -> PMResult:
    """
    Execute PM with given inputs.

    hitl_mode controls HITL behavior:
    - "auto_approve": Automatically approve all HITL requests (testing)
    - "pause": Actually pause and wait for approval (HITL testing)
    - "skip": Skip HITL scenarios entirely
    """
    ...
```

### Contract 3: Skill Integration

```yaml
# e2e-testing skill invokes:
pipeline = EvaluationPipeline(...)
report = await pipeline.run(suite="regression")

# workflow-evaluation skill invokes:
intelligence = IntelligenceLayer(...)
session = await intelligence.investigate(trigger, failures)

# agent-improvement skill invokes:
validator = RigorousFixValidator(...)
result = await validator.validate_fix(fix_proposal, scenarios)
```

---

## Checklist

### Phase 1 Complete When:
- [ ] All schemas compile without errors
- [ ] Storage interface has Supabase implementation
- [ ] Cost tracker can estimate and track costs

### Phase 2 Complete When:
- [ ] ResilientTraceStore stores locally and syncs
- [ ] LangSmithIntegration converts runs to TraceForEval
- [ ] HierarchicalTraceLoader returns (data, tokens) tuples

### Phase 3 Complete When:
- [ ] All code graders from taxonomy implemented
- [ ] Model graders for hallucination and synthesis working
- [ ] GradingOrchestrator handles all grading modes
- [ ] No duplicate grading code exists

### Phase 4 Complete When:
- [ ] Pattern Library persists to Supabase
- [ ] Pattern Library seeded with taxonomy patterns
- [ ] IntelligenceLayer produces fix proposals
- [ ] Fix validator runs k-out-of-n validation

### Phase 5 Complete When:
- [ ] Pipeline routes HITL scenarios correctly
- [ ] Pipeline integrates with StatefulHITLTestHarness
- [ ] ImprovementTracker maintains baselines with smoothing

### Phase 6 Complete When:
- [ ] All CLI commands from 07_OPERATIONAL_GUIDE.md work
- [ ] CI/CD workflow runs on push
- [ ] Skills invoke pipeline correctly

---

## Related Documents

- [08_SCHEMAS.md](08_SCHEMAS.md) - All schema definitions
- [00_INDEX.md](00_INDEX.md) - Framework overview

