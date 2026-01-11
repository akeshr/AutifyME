# Intelligence Layer (Claude)

**Part of**: [Universal Evaluation Framework](00_INDEX.md)

---

## Overview

The Intelligence Layer is where **deep reasoning** happens. Automated graders detect THAT something failed; the Intelligence Layer figures out **WHY** and **HOW TO FIX IT**.

```text
+===========================================================================+
|                        INTELLIGENCE LAYER (CLAUDE)                        |
+===========================================================================+
|                                                                           |
|  TRIGGER: Automated graders report failure(s)                             |
|                                                                           |
|  +-----------------------------------------------------------------+     |
|  |                    INVESTIGATION PROTOCOL                        |     |
|  +-----------------------------------------------------------------+     |
|  |                                                                   |     |
|  |  1. LOAD TRACE (Hierarchical, Token-Budgeted)                   |     |
|  |     - Level 0: Get structure overview                           |     |
|  |     - Level 1: Focus on failing area                            |     |
|  |     - Level 2: Deep dive if needed (chunked)                    |     |
|  |                                                                   |     |
|  |  2. ROOT CAUSE ANALYSIS                                          |     |
|  |     - What exactly failed? (symptom)                             |     |
|  |     - Why did it fail? (cause)                                   |     |
|  |     - Where in the system? (agent/tool/prompt)                   |     |
|  |     - Is this a new failure or pattern?                          |     |
|  |                                                                   |     |
|  |  3. PATTERN DETECTION (Cross-Failure)                            |     |
|  |     - Do multiple failures share root cause?                     |     |
|  |     - Is there a systemic issue?                                 |     |
|  |     - Historical comparison: seen before?                        |     |
|  |                                                                   |     |
|  |  4. FIX HYPOTHESIS                                               |     |
|  |     - What change would prevent this?                            |     |
|  |     - Confidence level (high/medium/low)                         |     |
|  |     - Risk of regression?                                        |     |
|  |                                                                   |     |
|  |  5. CONCRETE PROPOSAL                                            |     |
|  |     - Specific file(s) to change                                 |     |
|  |     - Exact modifications                                        |     |
|  |     - Test scenarios to validate                                 |     |
|  |                                                                   |     |
|  |  6. SCENARIO GENERATION                                          |     |
|  |     - Create 2-3 scenarios that catch this failure               |     |
|  |     - Add to regression suite                                    |     |
|  |                                                                   |     |
|  +-----------------------------------------------------------------+     |
|                                                                           |
|  OUTPUT: AnalysisReport with fix proposal + new scenarios                 |
|                                                                           |
+===========================================================================+
```

---

## Investigation Session Format

```python
@dataclass
class InvestigationSession:
    """Structure for Claude's investigation of failures."""

    # Input
    trigger: InvestigationTrigger
    failed_judgments: list[Judgment]
    traces: dict[str, TraceForEval]  # scenario_id -> trace

    # Investigation State
    current_level: int = 0  # 0, 1, or 2
    focus_areas: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    # Output
    root_cause: str | None = None
    pattern_detected: str | None = None
    fix_proposal: FixProposal | None = None
    new_scenarios: list[Scenario] = field(default_factory=list)
    confidence: float = 0.0

    # Token tracking
    tokens_used: int = 0
    budget_exceeded: bool = False


@dataclass
class Finding:
    """Individual finding during investigation."""
    level: int  # Which level of investigation
    area: str  # "pm_routing", "tool_params", "hallucination", etc.
    observation: str
    evidence: str  # Specific trace excerpt
    significance: str  # "root_cause" | "contributing" | "symptom"


@dataclass
class FixProposal:
    """Proposed fix for the root cause."""
    target: str  # "prompt" | "tool" | "code" | "architecture"
    component: str  # e.g., "project_manager.prompt", "write_data.py"
    change_type: str  # "add_example" | "add_instruction" | "modify_logic"
    description: str
    specific_changes: str  # Actual text/code to add/modify
    confidence: float
    risk_assessment: str
    validation_scenarios: list[str]  # Scenario IDs to run
```

---

## Intelligence Layer Implementation

```python
class IntelligenceLayer:
    """Claude-powered deep analysis and fix generation."""

    def __init__(
        self,
        langsmith: LangSmithIntegration,
        trace_loader: HierarchicalTraceLoader,
        pattern_library: PatternLibrary
    ):
        self.langsmith = langsmith
        self.trace_loader = trace_loader
        self.patterns = pattern_library

    async def investigate(
        self,
        trigger: InvestigationTrigger,
        failed_judgments: list[Judgment]
    ) -> InvestigationSession:
        """Run full investigation on failures."""

        session = InvestigationSession(
            trigger=trigger,
            failed_judgments=failed_judgments,
            traces={}
        )

        # Step 1: Load traces at Level 0
        for j in failed_judgments:
            session.traces[j.scenario_id] = await self.trace_loader.load_level_0(
                j.trace_id
            )

        # Step 2: Initial analysis - identify focus areas
        session.focus_areas = self._identify_focus_areas(session)

        # Step 3: Load Level 1 for focus areas
        for focus in session.focus_areas:
            for scenario_id, trace_l0 in session.traces.items():
                trace_l1 = await self.trace_loader.load_level_1(
                    trace_l0.trace_id, focus
                )
                session.findings.extend(
                    self._analyze_level_1(trace_l1, focus)
                )

        # Step 4: Check for known patterns
        known_pattern = self.patterns.match(session.findings)
        if known_pattern:
            session.pattern_detected = known_pattern["name"]
            session.fix_proposal = known_pattern["fix_template"]
            session.confidence = 0.9  # High confidence for known patterns
        else:
            # Step 5: Deep dive (Level 2) if needed
            if self._needs_deep_dive(session):
                await self._deep_dive(session)

            # Step 6: Generate fix hypothesis
            session.fix_proposal = await self._generate_fix(session)
            session.confidence = self._calculate_confidence(session)

        # Step 7: Generate regression scenarios
        session.new_scenarios = self._generate_scenarios(session)

        return session

    def _identify_focus_areas(
        self,
        session: InvestigationSession
    ) -> list[str]:
        """Identify which areas to focus investigation on."""
        areas = []

        for j in session.failed_judgments:
            for gr in j.grader_results:
                if not gr.grade.passed:
                    if gr.grader == "correct_routing":
                        areas.append("agent:project_manager")
                    elif gr.grader == "hallucination_check":
                        areas.append("agent:" + self._get_output_agent(j))
                    elif gr.grader.startswith("tool_"):
                        areas.append("tool:" + gr.grade.evidence.get("tool"))
                    elif gr.grader == "hitl_compliance":
                        areas.append("agent:specialists")

        return list(set(areas))  # Deduplicate

    async def _generate_fix(
        self,
        session: InvestigationSession
    ) -> FixProposal:
        """Generate fix proposal based on findings."""

        findings_summary = "\n".join([
            f"- [{f.significance}] {f.area}: {f.observation}"
            for f in session.findings
        ])

        prompt = f"""You are a senior software architect investigating agent failures.

## Failures Being Investigated
{[j.scenario_id for j in session.failed_judgments]}

## Investigation Findings
{findings_summary}

## Task
Based on these findings, propose a CONCRETE fix:

1. ROOT CAUSE: One sentence explaining why this failed
2. TARGET: What to fix (prompt/tool/code/architecture)
3. COMPONENT: Specific file path
4. CHANGE TYPE: What kind of change (add_example, add_instruction, modify_logic)
5. SPECIFIC CHANGES: The actual text/code to add or modify
6. CONFIDENCE: Your confidence level (0.0-1.0)
7. RISK: Any regression risks
8. VALIDATION: Which scenarios should verify this fix

Respond in JSON format matching FixProposal schema.
"""
        # This would be invoked via the agent-improvement skill
        return FixProposal(
            target="prompt",
            component="prompts/project_manager.prompt",
            change_type="add_instruction",
            description="Add instruction based on findings",
            specific_changes="[Generated by Claude based on findings]",
            confidence=0.7,
            risk_assessment="Low - additive change",
            validation_scenarios=[j.scenario_id for j in session.failed_judgments]
        )
```

---

## Token Budget Management

**Problem**: Large traces can exceed context limits.

**Solution**: Dynamic token budgeting with chunked investigation.

```python
@dataclass
class TokenBudget:
    """Token budget configuration."""

    investigation_total: int = 50000      # Max tokens per investigation
    level_0_target: int = 1000            # Target, not guarantee
    level_1_target: int = 3000
    level_2_target: int = 10000
    overflow_strategy: str = "summarize"  # "summarize" | "chunk" | "abort"


class BudgetAwareInvestigation:
    """Investigation that respects token budget."""

    async def investigate(
        self,
        failures: list[Judgment],
        budget: TokenBudget
    ) -> InvestigationSession:
        """Investigate within token budget."""
        remaining = budget.investigation_total
        session = InvestigationSession(failures=failures)

        # Phase 1: Load all L0 (must fit)
        for failure in failures:
            overview, tokens = await self.trace_loader.load_level_0(failure.trace_id)
            remaining -= tokens
            session.traces[failure.scenario_id] = {"l0": overview}

            if remaining <= 0:
                session.budget_exceeded = True
                session.analysis_depth = "overview_only"
                return await self._shallow_analysis(session)

        # Phase 2: Prioritize which traces need L1
        priority_order = self._prioritize_by_failure_severity(failures)

        for failure in priority_order[:3]:  # Max 3 deep dives
            if remaining < budget.level_1_target:
                break

            focus_areas = self._identify_focus_areas(session.traces[failure.scenario_id]["l0"])

            for focus in focus_areas[:2]:  # Max 2 focus areas per trace
                focus_data, tokens = await self.trace_loader.load_level_1(
                    failure.trace_id, focus, remaining
                )
                remaining -= tokens
                session.traces[failure.scenario_id][f"l1_{focus}"] = focus_data

        # Phase 3: L2 only if budget allows and needed
        if remaining > budget.level_2_target and self._needs_deep_dive(session):
            best_candidate = self._select_l2_candidate(session)
            async for chunk, tokens in self.trace_loader.load_level_2_chunked(
                best_candidate, remaining
            ):
                session.traces[best_candidate]["l2_chunks"] = session.traces[best_candidate].get("l2_chunks", [])
                session.traces[best_candidate]["l2_chunks"].append(chunk)
                remaining -= tokens
                if remaining <= 0:
                    break

        session.tokens_used = budget.investigation_total - remaining
        return session
```

---

## Multi-Track Investigation

**Problem**: Serial investigation can't handle multiple concurrent failures.

**Solution**: Parallel investigation with clustering and shared root cause detection.

```python
class MultiTrackInvestigator:
    """Parallel investigation of multiple failures."""

    def __init__(self, intelligence: IntelligenceLayer, max_parallel: int = 3):
        self.intelligence = intelligence
        self.max_parallel = max_parallel

    async def investigate_batch(
        self,
        failures: list[Judgment]
    ) -> BatchInvestigationResult:
        """Investigate failures in parallel, detect shared root causes."""

        # Phase 1: Quick clustering by symptom similarity
        clusters = self._cluster_by_symptoms(failures)

        # Phase 2: Parallel investigation per cluster
        investigations = []
        async with asyncio.TaskGroup() as tg:
            for cluster_id, cluster_failures in clusters.items():
                if len(investigations) < self.max_parallel:
                    task = tg.create_task(
                        self._investigate_cluster(cluster_id, cluster_failures)
                    )
                    investigations.append(task)

        # Phase 3: Merge findings, detect cross-cluster patterns
        cluster_results = [t.result() for t in investigations]
        merged = self._merge_investigations(cluster_results)

        # Phase 4: Detect shared root causes
        shared_causes = self._find_shared_root_causes(cluster_results)

        # Phase 5: Generate unified fix proposals
        fix_proposals = self._generate_unified_fixes(merged, shared_causes)

        return BatchInvestigationResult(
            total_failures=len(failures),
            clusters=len(clusters),
            cluster_results=cluster_results,
            shared_root_causes=shared_causes,
            fix_proposals=fix_proposals
        )

    def _cluster_by_symptoms(
        self,
        failures: list[Judgment]
    ) -> dict[str, list[Judgment]]:
        """Group failures by similar symptoms."""
        clusters = {}

        for failure in failures:
            symptoms = frozenset(
                gr.grader for gr in failure.grader_results if not gr.grade.passed
            )
            cluster_key = str(sorted(symptoms))
            if cluster_key not in clusters:
                clusters[cluster_key] = []
            clusters[cluster_key].append(failure)

        return clusters
```

---

## k-out-of-n Fix Validation

**Problem**: Single validation pass doesn't prove fix works reliably.

**Solution**: Statistical validation with early termination.

```python
@dataclass
class ValidationConfig:
    """Configuration for rigorous fix validation."""

    min_runs: int = 5                    # Minimum validation runs
    max_runs: int = 10                   # Maximum runs (cost cap)
    required_pass_rate: float = 0.9      # 90% must pass
    confidence_threshold: float = 0.95   # Statistical confidence
    consistency_required: bool = True


class RigorousFixValidator:
    """Validate fixes with statistical rigor."""

    async def validate_fix(
        self,
        fix: FixProposal,
        validation_scenarios: list[Scenario]
    ) -> ValidationResult:
        """Run k-out-of-n validation."""

        all_runs = []
        passes = 0
        fails = 0

        for run_num in range(self.config.max_runs):
            run_results = await self._execute_run(validation_scenarios)
            all_runs.append(run_results)

            run_passed = all(r.passed for r in run_results)
            if run_passed:
                passes += 1
            else:
                fails += 1

            # Early termination checks
            if self._can_conclude_pass(passes, fails, run_num + 1):
                break
            if self._can_conclude_fail(passes, fails, run_num + 1):
                break

        pass_rate = passes / len(all_runs)
        consistency = self._calculate_consistency(all_runs)

        return ValidationResult(
            passed=pass_rate >= self.config.required_pass_rate,
            pass_rate=pass_rate,
            consistency_score=consistency,
            total_runs=len(all_runs),
            passes=passes,
            fails=fails
        )
```

**Validation Decision Matrix**:

| Pass Rate | Confidence | Consistency | Decision |
|-----------|------------|-------------|----------|
| >= 90% | >= 95% | >= 80% | **PASS** - Deploy fix |
| >= 90% | >= 95% | < 80% | **INVESTIGATE** - Inconsistent |
| >= 90% | < 95% | Any | **MORE RUNS** - Need data |
| < 90% | Any | Any | **FAIL** - Fix doesn't work |

---

## Pattern Library

Known failure patterns with pre-defined fix templates:

```python
class PatternLibrary:
    """Library of known failure patterns and their fixes."""

    PATTERNS = {
        "pm_routing_single_intent": {
            "symptoms": ["correct_routing failed", "single specialist expected"],
            "root_cause": "PM prompt lacks example for this intent type",
            "fix_template": FixProposal(
                target="prompt",
                component="project_manager.prompt",
                change_type="add_example",
                description="Add canonical example for {intent} routing",
                confidence=0.85
            )
        },
        "analyst_hallucination": {
            "symptoms": ["hallucination_check failed", "claims not in source"],
            "root_cause": "Analyst prompt lacks grounding instruction",
            "fix_template": FixProposal(
                target="prompt",
                component="{agent_name}.prompt",
                change_type="add_instruction",
                description="Add explicit grounding instruction",
                specific_changes=(
                    "CRITICAL: Only report information directly visible in the source data. "
                    "If uncertain, state 'I cannot determine X from the provided data.'"
                ),
                confidence=0.8
            )
        },
        "specialist_hitl_bypass": {
            "symptoms": ["hitl_compliance failed", "write_data called"],
            "root_cause": "Specialist not pausing for approval before write",
            "fix_template": FixProposal(
                target="code",
                component="{specialist_name}.py",
                change_type="modify_logic",
                description="Ensure HITL interrupt before write tools",
                specific_changes="Add interrupt_before=['write_data'] to tool_configs",
                confidence=0.95
            )
        }
    }

    def match(self, findings: list[Finding]) -> dict | None:
        """Match findings against known patterns."""
        symptoms = [f.area for f in findings if f.significance == "symptom"]

        for pattern_name, pattern in self.PATTERNS.items():
            if all(s in symptoms for s in pattern["symptoms"]):
                return {
                    "name": pattern_name,
                    "root_cause": pattern["root_cause"],
                    "fix_template": pattern["fix_template"]
                }

        return None
```

---

## Skill Integration

```yaml
# workflow-evaluation skill triggers investigation
/workflow-evaluation:
  - Load eval report
  - Identify failures
  - Invoke IntelligenceLayer.investigate()
  - Present findings and fix proposal
  - On approval: implement fix

# agent-improvement skill implements fixes
/agent-improvement:
  - Receive fix proposal from investigation
  - Apply changes to target component
  - Run k-out-of-n validation
  - Update baseline if successful
```

---

## Related Documents

- [01_LANGSMITH_FOUNDATION.md](01_LANGSMITH_FOUNDATION.md) - Hierarchical trace loading
- [03_GRADER_ARCHITECTURE.md](03_GRADER_ARCHITECTURE.md) - Graders that trigger investigation
- [06_EVALUATION_PIPELINE.md](06_EVALUATION_PIPELINE.md) - How investigation fits in pipeline
- [07_OPERATIONAL_GUIDE.md](07_OPERATIONAL_GUIDE.md) - Cost model for investigations
