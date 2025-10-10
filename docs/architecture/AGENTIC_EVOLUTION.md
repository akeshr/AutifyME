# AutifyME Agentic Evolution

**Date**: 2025-10-09
**Status**: Design Specification
**Purpose**: Transform AutifyME from hierarchical delegation to truly autonomous agentic system

---

## Executive Summary

**Current State**: Hierarchical agent system with rule-based delegation (PM → Departments → Specialists)
**Target State**: Self-learning, self-healing, autonomous agent system with feedback loops and continuous improvement
**Timeline**: 6 weeks across 3 phases
**Core Principle**: Every interaction makes the system smarter

---

## Vision: From Hierarchical to Agentic

### Current Architecture (Hierarchical)
```
User Message → PM (static rules) → Department (hardcoded) → Specialist → Tools
                ↓
            Response
```

**Characteristics**:
- PM follows static prompt with predefined intent classification
- Department selection is rule-based
- No learning from past interactions
- Manual intervention required for failures
- Tests are manually created and maintained

**Problems**:
- Doesn't improve with usage
- Can't adapt to new patterns
- Requires manual updates for edge cases
- No autonomous error recovery
- Testing lags behind real usage patterns

---

### Target Architecture (Agentic)
```
User Message → PM (learns optimal routing) → Department (self-selects) → Specialist
                ↑                              ↑                           ↓
                └──── Feedback Loop ───────────┴──────── Outcome ─────────┘

                Memory Layer: Stores patterns, successful strategies, learnings
                Recovery Layer: Auto-heals errors, tries alternatives
                Test Synthesizer: Auto-generates tests from production patterns
```

**Characteristics**:
- PM learns which routing strategies work best
- Workflows remember similar past cases and apply successful patterns
- System auto-recovers from 80% of errors
- Tests auto-generate from production usage
- Prompts evolve based on feedback

**Benefits**:
- Improves continuously with every interaction
- Adapts to new message patterns automatically
- Self-heals most errors without human intervention
- Testing stays current with real usage
- Reduces manual maintenance burden

---

## Core Agentic Principles

### 1. **Observability First**
- Every decision logged with context
- Outcomes tracked for learning
- Performance metrics captured automatically
- Patterns extracted from execution traces

### 2. **Feedback Loops Everywhere**
- Agent performance → Prompt refinement
- Routing decisions → Strategy optimization
- Failures → Auto-generated regression tests
- User patterns → Test scenario synthesis

### 3. **Graceful Degradation**
- Multiple fallback strategies per decision point
- Escalate to human only when all automated recovery fails
- System never fully fails, always has a response

### 4. **Continuous Learning**
- Knowledge accumulates across workflows
- Similar cases inform new decisions
- Successful patterns become default strategies
- Edge cases become documented scenarios

### 5. **Autonomous Operation**
- Minimize human intervention
- Self-correct before escalating
- Auto-generate tests from failures
- Optimize routing based on outcomes

---

## Phase 1: Foundation (Weeks 1-2)

### 1.1 Adaptive Prompts Framework

**Purpose**: Prompts that evolve based on feedback instead of static files

**Implementation**: `agents/src/autifyme_agents/core/adaptive_prompts.py`

```python
class AdaptivePromptManager:
    """Self-improving prompt system with feedback loops."""

    def __init__(self, storage: StorageInterface):
        self.storage = storage
        self.base_prompts = {}  # Static prompt templates
        self.learned_patterns = {}  # Extracted from successful workflows
        self.failure_cases = {}  # Known failure patterns to avoid

    def get_prompt(self, agent_name: str, context: dict) -> str:
        """Get contextualized prompt with learned patterns."""
        # 1. Load base prompt template
        base = self._load_base_prompt(agent_name)

        # 2. Inject learned successful patterns
        patterns = self._get_relevant_patterns(agent_name, context)

        # 3. Add warnings for known failure cases
        warnings = self._get_failure_warnings(agent_name, context)

        # 4. Compose final prompt
        return self._compose_prompt(base, patterns, warnings, context)

    def record_outcome(self, agent_name: str, context: dict,
                      outcome: dict, success: bool):
        """Learn from workflow outcome."""
        if success:
            self._extract_success_pattern(agent_name, context, outcome)
        else:
            self._record_failure_case(agent_name, context, outcome)
```

**Integration Points**:
- PM: `create_project_manager()` uses adaptive prompts
- Departments: Inject learned delegation strategies
- Specialists: Context-aware tool selection

**Metrics**:
- Track prompt version performance
- Success rate by prompt variant
- Time to resolution by strategy

---

### 1.2 Outcome Tracking Infrastructure

**Purpose**: Capture workflow outcomes for learning

**Implementation**: `agents/src/autifyme_agents/workflows/outcome_tracker.py`

```python
class OutcomeTracker:
    """Tracks workflow outcomes for learning."""

    def track_workflow_start(self, thread_id: str, message: IncomingMessage):
        """Record workflow initiation."""
        return {
            "thread_id": thread_id,
            "message": message.model_dump(),
            "started_at": datetime.now(),
        }

    def track_routing_decision(self, thread_id: str,
                              intent: str, department: str, reasoning: str):
        """Record PM routing decision."""
        # Store: intent, department chosen, PM's reasoning

    def track_workflow_end(self, thread_id: str, success: bool,
                          result: dict, error: Optional[Exception] = None):
        """Record workflow completion."""
        # Calculate metrics: duration, success, error type
        # Trigger learning: update adaptive prompts, routing model
```

**Database Schema**:
```sql
CREATE TABLE workflow_outcomes (
    id UUID PRIMARY KEY,
    thread_id TEXT,
    message_hash TEXT,  -- For similar case retrieval
    intent TEXT,
    department TEXT,
    success BOOLEAN,
    duration_seconds FLOAT,
    error_type TEXT,
    resolution_strategy TEXT,
    created_at TIMESTAMP,

    -- Embeddings for similarity search
    message_embedding VECTOR(1536),

    -- Learning metadata
    learned_pattern JSONB,
    applied_patterns TEXT[]
);
```

---

### 1.3 Test Synthesizer (Auto-Generate Tests from Production)

**Purpose**: Testing stays current with real usage patterns automatically

**Implementation**: `agents/src/autifyme_agents/testing/test_synthesizer.py`

```python
class TestSynthesizer:
    """Generates test scenarios from production usage patterns."""

    def analyze_production_logs(self, time_window: timedelta) -> List[dict]:
        """Extract unique patterns from production."""
        # 1. Query workflow_outcomes for time window
        # 2. Cluster similar messages
        # 3. Identify edge cases (low frequency, high complexity)
        # 4. Extract representative samples
        return unique_patterns

    def synthesize_test_scenario(self, pattern: dict) -> dict:
        """Create test scenario from pattern."""
        return {
            "name": f"Production Pattern: {pattern['intent']}",
            "text": pattern['message_text'],
            "media": pattern.get('media_path'),
            "expected_intent": pattern['intent'],
            "expected_department": pattern['department'],
            "origin": "synthesized",
            "frequency": pattern['occurrence_count'],
            "last_seen": pattern['last_occurrence'],
        }

    def generate_regression_test(self, failure: dict) -> str:
        """Auto-generate pytest test from failure."""
        # Generate test code that reproduces the failure
        # Add to test suite automatically
        # Return path to generated test file
```

**Integration**:
```python
# Scheduled job (daily)
def daily_test_synthesis():
    synthesizer = TestSynthesizer()
    patterns = synthesizer.analyze_production_logs(timedelta(days=7))

    for pattern in patterns[:10]:  # Top 10 new patterns
        scenario = synthesizer.synthesize_test_scenario(pattern)
        # Add to simulate.py predefined scenarios
        # Or generate pytest test file
```

**Benefits**:
- Tests evolve with real user behavior
- Edge cases automatically become regression tests
- Coverage increases without manual effort

---

## Phase 2: Intelligence (Weeks 3-4)

### 2.1 Adaptive Routing Engine

**Purpose**: PM learns optimal department routing from historical outcomes

**Implementation**: `agents/src/autifyme_agents/workflows/adaptive_router.py`

```python
class AdaptiveRouter:
    """Learns optimal department routing from outcomes."""

    def __init__(self, storage: StorageInterface):
        self.routing_model = self._load_routing_model()
        self.success_cache = {}  # intent → department → success_rate

    def route_message(self, message: IncomingMessage,
                     pm_reasoning: str) -> RouterDecision:
        """Select optimal department based on learning."""
        # 1. Get PM's intent classification
        intent = self._classify_intent(message)

        # 2. Retrieve historical success rates
        success_rates = self._get_department_success_rates(intent)

        # 3. Consider current system state
        load = self._get_department_load()

        # 4. Make routing decision
        department = self._select_department(
            intent, success_rates, load, pm_reasoning
        )

        return RouterDecision(
            department=department,
            confidence=success_rates[department],
            reasoning=f"Based on {len(success_rates)} similar cases",
            fallback_departments=self._get_fallbacks(intent),
        )

    def learn_from_outcome(self, routing: RouterDecision, outcome: dict):
        """Update routing model based on outcome."""
        # Update success rates
        # Adjust routing probabilities
        # Identify new patterns
```

**Database Schema**:
```sql
CREATE TABLE routing_history (
    id UUID PRIMARY KEY,
    intent TEXT,
    department TEXT,
    success BOOLEAN,
    duration_seconds FLOAT,
    confidence_score FLOAT,
    created_at TIMESTAMP,

    INDEX idx_intent_dept (intent, department),
    INDEX idx_created (created_at DESC)
);
```

---

### 2.2 Contextual Memory Layer

**Purpose**: Workflows remember and reference similar past cases

**Implementation**: `agents/src/autifyme_agents/memory/contextual_memory.py`

```python
class ContextualMemory:
    """Long-term memory across workflows."""

    def recall_similar_cases(self, current_message: IncomingMessage,
                            limit: int = 5) -> List[dict]:
        """Vector search for similar past workflows."""
        # 1. Generate embedding for current message
        embedding = self._embed_message(current_message)

        # 2. Query vector database
        similar = self._vector_search(embedding, limit)

        # 3. Filter for successful outcomes only
        successful = [case for case in similar if case['success']]

        return successful

    def inject_context(self, prompt: str, similar_cases: List[dict]) -> str:
        """Add similar case context to prompt."""
        if not similar_cases:
            return prompt

        context = "\n\n## Relevant Past Cases:\n"
        for i, case in enumerate(similar_cases, 1):
            context += f"\n{i}. Similar message: '{case['message']}'\n"
            context += f"   Resolution: {case['resolution_summary']}\n"
            context += f"   Success: {case['success']}\n"

        return prompt + context

    def store_experience(self, workflow_result: dict):
        """Store workflow as retrievable experience."""
        # Generate embedding
        # Extract key learnings
        # Store in vector DB with metadata
```

**Technology**:
- Use PostgreSQL pgvector extension for embeddings
- OpenAI text-embedding-3-small for message embeddings
- Cosine similarity search for retrieval

---

### 2.3 Feedback Loop Integration

**Purpose**: Connect all learning components into cohesive system

**Implementation**: Wire all components together

```python
# In WorkflowRunner
class WorkflowRunner:
    def __init__(self, ...):
        self.outcome_tracker = OutcomeTracker(storage)
        self.adaptive_router = AdaptiveRouter(storage)
        self.contextual_memory = ContextualMemory(storage)
        self.prompt_manager = AdaptivePromptManager(storage)

    def handle_message(self, sender: str, text: str, media_id: str):
        # 1. Track workflow start
        tracking_id = self.outcome_tracker.track_workflow_start(...)

        # 2. Recall similar cases
        similar = self.contextual_memory.recall_similar_cases(message)

        # 3. Get adaptive prompt with context
        pm_prompt = self.prompt_manager.get_prompt(
            "project_manager",
            context={"similar_cases": similar}
        )

        # 4. Route with learned strategy
        routing = self.adaptive_router.route_message(message)

        # 5. Execute workflow
        result = self._execute_workflow(routing)

        # 6. Track outcome and learn
        self.outcome_tracker.track_workflow_end(tracking_id, result)
        self.adaptive_router.learn_from_outcome(routing, result)
        self.contextual_memory.store_experience(result)
        self.prompt_manager.record_outcome("project_manager", ...)
```

---

## Phase 3: Autonomy (Weeks 5-6)

### 3.1 Self-Healing Workflow Engine

**Purpose**: Auto-recover from errors without human intervention

**Implementation**: `agents/src/autifyme_agents/workflows/recovery/auto_healer.py`

```python
class WorkflowHealer:
    """Autonomous error detection and recovery."""

    def monitor_execution(self, workflow_state: dict) -> Optional[Alert]:
        """Detect anomalies during execution."""
        # Check for slow responses
        # Detect repeated failures
        # Identify resource exhaustion
        # Predict potential failures

    def auto_recover(self, error: Exception, context: dict) -> RecoveryResult:
        """Attempt automated recovery."""
        recovery_strategies = [
            self._retry_with_backoff,
            self._try_alternative_department,
            self._fallback_to_manual_mode,
            self._request_clarification,
        ]

        for strategy in recovery_strategies:
            try:
                result = strategy(error, context)
                if result.success:
                    self._log_successful_recovery(strategy, error, context)
                    return result
            except Exception as recovery_error:
                continue

        # All strategies failed - escalate to human
        return self._escalate_to_human(error, context)
```

**Recovery Strategies**:
1. **Retry with exponential backoff**: Transient failures (API timeouts)
2. **Alternative department**: Routing error, try fallback
3. **Decompose task**: Break complex request into smaller parts
4. **Request clarification**: Send message to user asking for details
5. **Fallback to basic mode**: Disable advanced features, use simple path
6. **Escalate to human**: Create support ticket with full context

---

### 3.2 Automated Regression Test Generation

**Purpose**: Every failure becomes a regression test automatically

**Implementation**: Extend TestSynthesizer

```python
class TestSynthesizer:
    def generate_regression_test_from_failure(self, failure: dict) -> Path:
        """Create pytest test from failure case."""
        test_code = f'''
"""Auto-generated regression test from production failure."""

import pytest
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner
from autifyme_agents.schemas.messages import IncomingMessage

def test_regression_{failure['id'].replace('-', '_')}():
    """
    Regression test for: {failure['error_type']}

    Original failure: {failure['created_at']}
    Message: {failure['message_text']}
    Expected: Should not raise {failure['error_type']}
    """
    runner = WorkflowRunner(...)
    message = IncomingMessage(
        text="{failure['message_text']}",
        platform="test",
        sender_id="regression_test",
        ...
    )

    # This should not raise the original error
    result = runner.handle_message(message)
    assert result is not None
    assert "error" not in result
'''

        # Write to file
        test_file = Path(f"tests/regression/test_failure_{failure['id']}.py")
        test_file.write_text(test_code)

        return test_file
```

**Workflow**:
```
Failure in Production
    ↓
Auto-generate regression test
    ↓
Add to CI/CD pipeline
    ↓
Fix issue
    ↓
Test passes → Deploy
    ↓
Failure prevented in future
```

---

### 3.3 Performance Optimization Agent

**Purpose**: System autonomously optimizes its own performance

**Implementation**: `agents/src/autifyme_agents/optimization/performance_agent.py`

```python
class PerformanceOptimizer:
    """Autonomous performance monitoring and optimization."""

    def analyze_performance(self) -> List[Optimization]:
        """Identify optimization opportunities."""
        # Analyze slow workflows
        # Find redundant API calls
        # Identify cacheable operations
        # Detect inefficient routing

        return optimization_recommendations

    def apply_optimization(self, optimization: Optimization):
        """Autonomously apply safe optimizations."""
        if optimization.risk_level == "low":
            # Apply automatically
            self._apply(optimization)
            self._log_optimization(optimization)
        else:
            # Create proposal for human review
            self._create_optimization_proposal(optimization)
```

---

## Implementation Checklist

### Phase 1: Foundation ✅
- [x] Create `adaptive_prompts.py` with AdaptivePromptManager
- [x] Create `outcome_tracker.py` with OutcomeTracker
- [x] Add `workflow_outcomes` table to database schema
- [x] Create `test_synthesizer.py` with TestSynthesizer
- [x] Extend StorageInterface for outcome persistence
- [x] Implement storage methods in SupabaseStorageClient
- [x] Wire outcome persistence in OutcomeTracker
- [ ] Integrate outcome tracking in WorkflowRunner (IN PROGRESS)
- [ ] Wire AdaptivePromptManager to PM creation (PENDING)
- [ ] Apply database migration to Supabase (PENDING)
- [ ] Create daily test synthesis scheduled job (PENDING Phase 2)
- [ ] Test: Verify outcomes are tracked correctly (PENDING)
- [ ] Test: Generate test scenarios from logs (PENDING)

### Phase 2: Intelligence
- [ ] Create `adaptive_router.py` with AdaptiveRouter
- [ ] Add `routing_history` table to database
- [ ] Create `contextual_memory.py` with ContextualMemory
- [ ] Set up pgvector extension in PostgreSQL
- [ ] Integrate adaptive routing in PM
- [ ] Integrate contextual memory in prompts
- [ ] Test: Verify routing improves over time
- [ ] Test: Similar case retrieval works correctly

### Phase 3: Autonomy
- [ ] Create `auto_healer.py` with WorkflowHealer
- [ ] Implement recovery strategies
- [ ] Extend TestSynthesizer for regression tests
- [ ] Create `performance_agent.py` with PerformanceOptimizer
- [ ] Integrate auto-healing in WorkflowRunner
- [ ] Set up automated regression test generation
- [ ] Test: Verify auto-recovery works
- [ ] Test: Performance optimizations apply correctly

---

## Success Metrics

### Phase 1
- **Prompt Evolution**: 3+ prompt variations per agent tested
- **Outcome Tracking**: 100% of workflows tracked
- **Test Synthesis**: 10+ scenarios auto-generated from production

### Phase 2
- **Routing Accuracy**: 90%+ correct department selection
- **Memory Recall**: 5+ similar cases retrieved per workflow
- **Feedback Loops**: All outcomes feeding back to learning

### Phase 3
- **Auto-Recovery Rate**: 80%+ errors self-healed
- **Regression Coverage**: 100% of failures become tests
- **Performance Gains**: 20%+ reduction in average workflow duration

---

## Architectural Alignment

**Hexagonal Architecture**: Maintained
- Adaptive components are adapters around core domain
- Learning logic stays in ports/interfaces
- Domain logic unchanged

**Hierarchical Model**: Enhanced
- PM still top of hierarchy
- Learning enhances decision-making
- Context flows top-down with memory

**Type Safety**: Preserved
- All learning components use Pydantic models
- Database schemas strongly typed
- Outcome tracking fully structured

**Observability**: Amplified
- Every decision logged
- Metrics captured automatically
- Learning traceable

---

## Risks & Mitigations

### Risk: Learning Degrades Performance
**Mitigation**: A/B testing framework, rollback capability, human override

### Risk: Feedback Loops Create Bias
**Mitigation**: Diverse scenario testing, manual review of learned patterns, bias detection

### Risk: Auto-Generated Tests Are Brittle
**Mitigation**: Human review queue, test quality scoring, automatic pruning of flaky tests

### Risk: Memory Retrieval Slows System
**Mitigation**: Caching layer, async retrieval, vector index optimization

---

## Future Extensions

**Phase 4: Multi-Agent Collaboration**
- Agents negotiate task delegation
- Parallel execution with coordination
- Consensus-based decision making

**Phase 5: Meta-Learning**
- System learns how to learn better
- Optimization of learning parameters
- Cross-department knowledge transfer

**Phase 6: Proactive Intelligence**
- Predict user needs before explicit request
- Suggest optimizations proactively
- Auto-create missing documentation

---

## References

- `AGENTS_DESIGN.md` - Core hierarchical architecture
- `PROJECT_MANAGER_DESIGN.md` - PM role and responsibilities
- `LOCAL_TESTING_STRATEGY.md` - Testing infrastructure
- `WORKFLOW_ORCHESTRATION_REFACTOR.md` - Runner architecture
