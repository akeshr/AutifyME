# LangSmith Foundation

**Part of**: [Universal Evaluation Framework](00_INDEX.md)

---

## Overview

LangSmith is not just logging - it's the **source of truth** for the entire evaluation loop. This document covers the observability layer including trace capture, datasets, and resilient fallback mechanisms.

```text
+===========================================================================+
|                          LANGSMITH CAPABILITIES                           |
+===========================================================================+
|                                                                           |
|  TRACE CAPTURE                    DATASETS                                |
|  +---------------------------+    +---------------------------+           |
|  | Every agent run traced    |    | Store eval scenarios      |           |
|  | - Inputs/outputs          |    | - Versioned test sets     |           |
|  | - Tool calls + params     |    | - Golden outputs          |           |
|  | - Latencies               |    | - Expected behaviors      |           |
|  | - Error states            |    +---------------------------+           |
|  | - Token usage             |                                            |
|  +---------------------------+    ANNOTATION QUEUES                       |
|                                   +---------------------------+           |
|  EVALUATORS                       | Human labeling interface  |           |
|  +---------------------------+    | - Calibration samples     |           |
|  | Run custom graders        |    | - Edge case review        |           |
|  | - Code-based (via SDK)    |    | - Model grader feedback   |           |
|  | - Model-based (LLM judge) |    +---------------------------+           |
|  | - Comparison views        |                                            |
|  +---------------------------+    FEEDBACK                                |
|                                   +---------------------------+           |
|  EXPERIMENTS                      | Production thumbs up/down |           |
|  +---------------------------+    | - Real failures -> cases  |           |
|  | A/B test prompts          |    | - User satisfaction       |           |
|  | - Version comparison      |    +---------------------------+           |
|  | - Statistical analysis    |                                            |
|  +---------------------------+                                            |
|                                                                           |
+===========================================================================+
```

---

## Trace Structure for Evaluation

```python
@dataclass
class TraceForEval:
    """Trace structure optimized for evaluation."""

    # Identity
    trace_id: str
    thread_id: str
    timestamp: datetime

    # Input
    user_message: str
    media_paths: list[str]
    context: dict  # company_profile, conversation_history, etc.

    # Execution
    pm_reasoning: str
    delegations: list[Delegation]  # PM -> Analyst/Specialist
    tool_calls: list[ToolCall]
    interrupts: list[Interrupt]  # HITL pauses

    # Output
    final_response: str
    state_changes: list[StateChange]  # DB writes

    # Metadata
    total_tokens: int
    latency_ms: int
    error: str | None


@dataclass
class Delegation:
    """PM delegation to sub-agent."""
    target: str  # "visual_analyst", "catalog_specialist", etc.
    task: str
    context_passed: dict
    response_received: str


@dataclass
class ToolCall:
    """Individual tool invocation."""
    tool_name: str
    agent: str  # Which agent called it
    params: dict
    result: dict
    success: bool
    latency_ms: int
```

---

## LangSmith Integration

```python
from langsmith import Client
from langsmith.evaluation import evaluate
from langsmith.schemas import Run, Example


class LangSmithIntegration:
    """LangSmith integration for evaluation framework."""

    def __init__(self):
        self.client = Client()
        self.project_name = "autifyme-evals"

    # --- Trace Retrieval ---
    async def get_trace(self, trace_id: str) -> TraceForEval:
        """Retrieve trace and convert to eval format."""
        run = self.client.read_run(trace_id)
        return self._convert_to_eval_format(run)

    async def get_recent_failures(
        self,
        hours: int = 24,
        min_feedback_score: float = 0.5
    ) -> list[TraceForEval]:
        """Get recent traces with negative feedback."""
        runs = self.client.list_runs(
            project_name=self.project_name,
            filter=f"gt(start_time, datetime.now() - timedelta(hours={hours}))",
            execution_order=1  # Top-level runs only
        )

        failures = []
        for run in runs:
            feedback = self.client.list_feedback(run_ids=[run.id])
            if any(f.score < min_feedback_score for f in feedback):
                failures.append(self._convert_to_eval_format(run))

        return failures

    # --- Dataset Management ---
    async def create_dataset(
        self,
        name: str,
        scenarios: list[Scenario]
    ) -> str:
        """Create LangSmith dataset from scenarios."""
        dataset = self.client.create_dataset(
            dataset_name=name,
            description=f"Eval scenarios for {name}"
        )

        for scenario in scenarios:
            self.client.create_example(
                inputs={
                    "message": scenario.input.message,
                    "media": [m.path for m in scenario.input.media],
                    "context": scenario.input.context
                },
                outputs={
                    "expected_intent": scenario.expected.intent,
                    "expected_routing": scenario.expected.routing,
                    "expected_tools": scenario.expected.tools
                },
                dataset_id=dataset.id,
                metadata=scenario.metadata.model_dump()
            )

        return dataset.id

    async def load_dataset(self, name: str) -> list[Scenario]:
        """Load scenarios from LangSmith dataset."""
        dataset = self.client.read_dataset(dataset_name=name)
        examples = list(self.client.list_examples(dataset_id=dataset.id))

        return [
            Scenario(
                id=str(ex.id),
                input=ScenarioInput(
                    message=ex.inputs["message"],
                    media=[MediaRef(path=p) for p in ex.inputs.get("media", [])],
                    context=ex.inputs.get("context", {})
                ),
                expected=Expected(
                    intent=ex.outputs.get("expected_intent"),
                    routing=ex.outputs.get("expected_routing", []),
                    tools=ex.outputs.get("expected_tools", [])
                ),
                metadata=Metadata(**ex.metadata)
            )
            for ex in examples
        ]

    # --- Running Evaluations ---
    async def run_evaluation(
        self,
        dataset_name: str,
        graders: list[Grader],
        parallelism: int = 5
    ) -> EvaluationReport:
        """Run evaluation using LangSmith's evaluate function."""

        def target_function(inputs: dict) -> dict:
            """Execute scenario via PM."""
            import asyncio
            result = asyncio.run(chat_with_pm(
                message=inputs["message"],
                media_paths=inputs.get("media", []),
                context=inputs.get("context", {})
            ))
            return {
                "response": result.response,
                "trace_id": result.trace_id,
                "routing": result.routing,
                "tools_called": result.tools_called
            }

        # Convert graders to LangSmith evaluators
        evaluators = [
            self._grader_to_evaluator(g) for g in graders
        ]

        # Run evaluation
        results = evaluate(
            target_function,
            data=dataset_name,
            evaluators=evaluators,
            experiment_prefix=f"eval_{datetime.now().strftime('%Y%m%d_%H%M')}",
            max_concurrency=parallelism
        )

        return self._convert_results(results)

    def _grader_to_evaluator(self, grader: Grader):
        """Convert our grader to LangSmith evaluator."""
        def evaluator(run: Run, example: Example) -> dict:
            grade = grader.grade(
                output=run.outputs,
                expected=example.outputs,
                trace_id=str(run.id)
            )
            return {
                "key": grader.name,
                "score": grade.score,
                "comment": grade.reasoning
            }
        return evaluator

    # --- Annotation Queues ---
    async def queue_for_human_review(
        self,
        trace_ids: list[str],
        queue_name: str = "calibration"
    ):
        """Send traces to annotation queue for human review."""
        for trace_id in trace_ids:
            self.client.create_annotation_queue_item(
                queue_name=queue_name,
                run_id=trace_id
            )

    async def get_human_annotations(
        self,
        queue_name: str
    ) -> list[HumanAnnotation]:
        """Retrieve completed human annotations."""
        items = self.client.list_annotation_queue_items(
            queue_name=queue_name,
            status="completed"
        )
        return [
            HumanAnnotation(
                trace_id=item.run_id,
                scores=item.feedback,
                notes=item.comment
            )
            for item in items
        ]

    # --- Feedback Loop ---
    async def log_production_feedback(
        self,
        trace_id: str,
        score: float,
        comment: str = ""
    ):
        """Log user feedback on production trace."""
        self.client.create_feedback(
            run_id=trace_id,
            key="user_satisfaction",
            score=score,
            comment=comment
        )

    async def convert_feedback_to_scenario(
        self,
        trace_id: str
    ) -> Scenario:
        """Convert production failure to eval scenario."""
        trace = await self.get_trace(trace_id)
        feedback = list(self.client.list_feedback(run_ids=[trace_id]))

        # Infer expected behavior from feedback
        expected = self._infer_expected_from_feedback(trace, feedback)

        return Scenario(
            id=f"from_prod_{trace_id[:8]}",
            input=ScenarioInput(
                message=trace.user_message,
                media=[MediaRef(path=p) for p in trace.media_paths],
                context=trace.context
            ),
            expected=expected,
            metadata=Metadata(
                domain=self._infer_domain(trace),
                complexity="real_world",
                failure_mode=self._infer_failure_mode(trace, feedback),
                source="production"
            )
        )
```

---

## Hierarchical Trace Loading

3-level lazy loading for efficient trace analysis during investigation.

**NOTE**: All data models defined in [08_SCHEMAS.md](08_SCHEMAS.md). Token budgets are canonical values from that document.

```python
class HierarchicalTraceLoader:
    """
    3-level lazy loading for efficient trace analysis.

    All methods return (data, tokens_used) tuples for budget tracking.
    See 08_SCHEMAS.md for TraceOverview, TraceFocus, TraceDeep definitions.
    """

    def __init__(self, langsmith: LangSmithIntegration):
        self.langsmith = langsmith

    async def load_level_0(
        self,
        trace_id: str,
        max_tokens: int | None = None
    ) -> tuple[TraceOverview, int]:
        """
        Level 0: Structure Overview (~500-1000 tokens)
        - Agent names and delegation chain
        - Tool names called (not params)
        - Pass/fail status
        - Total tokens and latency

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
        Level 1: Focused Investigation (~1500-3000 tokens)
        - Full details for specific agent/tool
        - Inputs, outputs, reasoning
        - Surrounding context

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
        """
        Level 2: Deep Dive (~5000-10000 tokens)
        - Full trace with all details
        - Every input/output/reasoning
        - Complete error stack traces

        Returns:
            tuple of (TraceDeep, tokens_used)
        """
        run = self.langsmith.client.read_run(trace_id)
        children = list(self.langsmith.client.list_runs(
            parent_run_id=trace_id
        ))
        deep = self._build_full_trace(run, children)
        tokens_used = self._estimate_tokens(deep)
        return deep, tokens_used

    async def load_level_2_chunked(
        self,
        trace_id: str,
        budget: int
    ) -> AsyncIterator[tuple[dict, int]]:
        """Yield trace chunks within budget for very large traces."""
        # Implementation yields chunks until budget exhausted
        ...

    def _estimate_tokens(self, data: Any) -> int:
        """Estimate tokens for data structure (rough: 4 chars = 1 token)."""
        import json
        text = json.dumps(data, default=str)
        return len(text) // 4
```

---

## Fallback Mechanism (Resilience)

**Problem**: Single point of failure - no evaluation possible during LangSmith outages.

**Solution**: Local-first tracing with async sync.

```python
class ResilientTraceStore:
    """Local-first trace storage with LangSmith sync."""

    def __init__(self, local_path: Path, langsmith: LangSmithIntegration):
        self.local_path = local_path
        self.langsmith = langsmith
        self.sync_queue: asyncio.Queue[str] = asyncio.Queue()

    async def store_trace(self, trace: TraceForEval) -> str:
        """Store locally FIRST, queue for LangSmith sync."""
        # 1. Always store locally (never fails)
        trace_id = str(uuid4())
        local_file = self.local_path / f"{trace_id}.json"
        local_file.write_text(trace.model_dump_json())

        # 2. Queue for async LangSmith sync
        await self.sync_queue.put(trace_id)

        return trace_id

    async def sync_worker(self):
        """Background worker syncing to LangSmith."""
        while True:
            trace_id = await self.sync_queue.get()
            try:
                local_file = self.local_path / f"{trace_id}.json"
                trace = TraceForEval.model_validate_json(local_file.read_text())
                await self.langsmith.upload_trace(trace)
                # Mark as synced
                (self.local_path / f"{trace_id}.synced").touch()
            except Exception as e:
                # Re-queue with backoff
                logger.warning(f"LangSmith sync failed: {e}, re-queueing")
                await asyncio.sleep(60)
                await self.sync_queue.put(trace_id)

    async def get_trace(self, trace_id: str) -> TraceForEval:
        """Get from local first, fallback to LangSmith."""
        local_file = self.local_path / f"{trace_id}.json"
        if local_file.exists():
            return TraceForEval.model_validate_json(local_file.read_text())

        # Fallback to LangSmith
        return await self.langsmith.get_trace(trace_id)

    def get_unsynced_count(self) -> int:
        """Check sync health."""
        synced = set(f.stem for f in self.local_path.glob("*.synced"))
        all_traces = set(f.stem for f in self.local_path.glob("*.json"))
        return len(all_traces - synced)


class OfflineEvaluationMode:
    """Run evaluations without LangSmith dependency."""

    def __init__(self, local_store: ResilientTraceStore):
        self.local_store = local_store

    async def run_offline(
        self,
        scenarios: list[Scenario],
        graders: list[Grader]
    ) -> EvaluationReport:
        """Full evaluation using only local traces."""
        results = []
        for scenario in scenarios:
            result = await self._execute_scenario(scenario)
            trace = await self.local_store.store_trace(result.trace)
            judgment = await self._grade_locally(result, scenario, graders)
            results.append(judgment)

        return self._compile_report(results)
```

---

## Operational Mode Matrix

| LangSmith Status | Trace Storage | Evaluation | Investigation |
|------------------|---------------|------------|---------------|
| Online | Local + Sync | Full | Full |
| Degraded (slow) | Local + Queue | Full | Local patterns only |
| Offline | Local only | Full (offline mode) | Deferred |

---

## Related Documents

- [03_GRADER_ARCHITECTURE.md](03_GRADER_ARCHITECTURE.md) - How graders integrate with LangSmith evaluators
- [05_INTELLIGENCE_LAYER.md](05_INTELLIGENCE_LAYER.md) - Hierarchical trace loading for investigation
- [07_OPERATIONAL_GUIDE.md](07_OPERATIONAL_GUIDE.md) - Human review SLA and annotation queues
- [08_SCHEMAS.md](08_SCHEMAS.md) - Canonical data model definitions (TraceForEval, TraceOverview, etc.)
- [09_IMPLEMENTATION_GUIDE.md](09_IMPLEMENTATION_GUIDE.md) - Implementation order and contracts
