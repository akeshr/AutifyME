# LangSmith Integration Strategy

**Date:** September 30, 2025  
**Purpose:** Define how to leverage LangSmith for observability, evaluation, and monitoring while maintaining architectural independence

---

## Executive Summary

LangSmith is a **production-grade observability platform** for LLM applications. We use it for what it does best (monitoring, offline evaluation, cost tracking) while maintaining independence for core functionality (prompts, real-time quality gates, runtime execution).

### What LangSmith Provides

1. **Observability:** Automatic tracing of all LLM calls and agent workflows
2. **Cost Tracking:** Token usage and cost attribution per workflow
3. **Offline Evaluation:** Dataset-based testing and regression detection
4. **Monitoring:** Real-time dashboards and alerts
5. **Debugging:** Detailed traces with replay capabilities
6. **Experimentation:** Playground for testing prompt variations

---

## ⚠️ Critical Distinction: Offline vs Online Evaluation

### Offline Evaluation (LangSmith)
- **When:** After workflow completes
- **Purpose:** Regression testing, A/B testing, quality monitoring
- **How:** Datasets + Custom evaluator functions
- **Where:** CI/CD, nightly runs, historical analysis

### Online Evaluation (Reviewer Agents)
- **When:** During workflow execution (real-time)
- **Purpose:** Quality gates, refinement loops, blocking bad output
- **How:** Reviewer agents that critique and provide feedback
- **Where:** Production workflows, before expensive/irreversible actions

**Key Point:** LangSmith does NOT replace the need for in-workflow Reviewer agents. Both are required.

---

## Architecture Integration Points

### 1. What LangSmith Eliminates

✅ **Fully Eliminated:**
- Custom cost tracking system
- Custom monitoring dashboards
- Custom offline evaluation framework
- Custom debugging infrastructure

### 2. What We Still Build

⚠️ **Required Components:**
- `prompts/` directory with LangChain PromptTemplate definitions (Git-versioned)
- `ReviewerAgent` specialist for real-time quality gates
- Refinement loop logic (approve/refine/escalate)
- Error handling and retry logic
- Lightweight application logging

### 3. What Gets Simplified

🔄 **Simplified Components:**
- Logging: Lightweight, LangSmith-aware with correlation IDs
- Testing: Unit tests for code, LangSmith for agent evaluation
- QA: Custom evaluator functions (used by LangSmith)

---

## Design Principles

### 1. Trace Everything with `@traceable`

Every meaningful function should be traced for complete visibility.

```python
from langsmith import traceable

@traceable(
    name="Extract Product Info from Image",
    tags=["cataloging", "image-analysis"],
    metadata={"department": "cataloging", "specialist": "image-analyzer"}
)
def extract_product_info(image_url: str, company_context: dict) -> dict:
    """Extract product information from an image."""
    # Implementation
    pass
```

**Why:** Complete workflow visibility without custom logging infrastructure.

---

### 2. Rich Metadata for Filtering

Use metadata and tags to organize traces for analysis.

```python
@traceable(
    tags=["department:cataloging", "agent:specialist"],
    metadata={
        "workflow_id": workflow_id,
        "company_id": company_id,  # For future multi-tenancy
        "agent_type": "specialist"
    }
)
def analyze_product_image(image_url: str) -> dict:
    # Implementation
    pass
```

**Why:** Enables powerful filtering in LangSmith dashboards (e.g., "show all cataloging workflows with errors").

---

### 3. Prompts in Code, Not LangSmith

Store prompts as LangChain PromptTemplates in code, use LangSmith Playground for experimentation only.

```python
# prompts/templates.py
from langchain.prompts import ChatPromptTemplate

PRODUCT_DESCRIPTION_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "You are an expert product copywriter for {brand_name}."),
    ("human", """Create a compelling product description based on:
Product Data: {product_data}
Brand Voice: {brand_voice}
Target Audience: {target_audience}""")
])

# Usage in agent
@traceable(name="Create Product Description")
def create_product_description(product_data: dict, company_profile: dict) -> str:
    formatted_prompt = PRODUCT_DESCRIPTION_TEMPLATE.format_messages(
        brand_name=company_profile["name"],
        product_data=product_data,
        brand_voice=company_profile["brand_voice"],
        target_audience=company_profile["target_audience"]
    )
    return llm.invoke(formatted_prompt)
```

**Why:**
- Git version control and code review
- No runtime dependency on external service
- Offline capability and resilience
- LangSmith Playground still available for experimentation

---

### 4. Offline Evaluation with Custom Functions

Define business-specific evaluation criteria as Python functions.

```python
# core/evaluators.py

def brand_voice_evaluator(run_input: dict, run_output: dict) -> dict:
    """Evaluates if product description matches company brand voice."""
    description = run_output.get("description", "")
    brand_voice = run_input.get("brand_voice", "")
    
    # Use LLM or rules to score
    score = evaluate_brand_voice_match(description, brand_voice)
    
    return {
        "score": score,
        "feedback": f"Brand voice alignment: {score:.2f}"
    }

# Register with LangSmith for CI/CD evaluation
from langsmith import Client

client = Client()
client.evaluate(
    cataloging_workflow,
    data="product-cataloging-golden-dataset",
    evaluators=[brand_voice_evaluator, accuracy_evaluator, completeness_evaluator]
)
```

**Why:** Automated quality checks in CI/CD without manual testing.

---

### 5. Online Evaluation with Reviewer Agents

Real-time quality gates during production workflows.

```python
@traceable(name="Catalog Product with QA")
def catalog_product_with_qa(images: list, text: str) -> dict:
    max_attempts = 3
    
    for attempt in range(max_attempts):
        # Specialist creates draft
        draft = image_specialist.extract_product_info(images)
        
        # Reviewer agent evaluates IN REAL-TIME
        review = reviewer_agent.review(
            output=draft,
            criteria=["brand_voice", "accuracy", "completeness"],
            context=company_profile
        )
        
        if review.approved:
            return save_product(draft)  # Quality gate passed
        else:
            # Refinement loop with feedback
            draft = image_specialist.refine_with_feedback(
                draft=draft,
                feedback=review.feedback
            )
    
    # Max attempts - escalate to human
    return request_human_approval(draft, review)
```

**Why:** Ensure quality NOW, before proceeding to next step or publishing.

---

## Implementation Guidelines

### Setup (Required First)

1. **Environment Configuration (.env):**
   ```bash
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=<your_key>
   LANGCHAIN_PROJECT=autifyme-dev
   LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
   ```

2. **Install LangSmith SDK:**
   ```bash
   uv pip install langsmith --python agents/venv/Scripts/python.exe
   ```

3. **Verify Setup:**
   ```python
   from langsmith import traceable
   
   @traceable(name="Hello World")
   def test_tracing():
       return "LangSmith is working!"
   
   test_tracing()
   # Check LangSmith dashboard for trace
   ```

### Naming Conventions

Use hierarchical naming for traces:
- `project_manager.analyze_intent`
- `cataloging_dept.process_images`
- `image_specialist.extract_features`
- `reviewer.check_quality`

### Tagging Strategy

Consistent tags enable powerful analysis:
- `department:<name>` - Which department owns this
- `agent:<type>` - project_manager | department_head | specialist | reviewer
- `workflow:<name>` - Which high-level workflow
- `status:<state>` - draft | review | approved | failed

---

## Monitoring & Alerting

### Key Metrics to Track

Create dashboards in LangSmith for:
1. **Cost:** Token usage and costs per workflow, per agent
2. **Performance:** Latency P50, P95, P99
3. **Quality:** Success rate, error rate, approval rate
4. **Volume:** Workflows per hour, products cataloged per day

### Alert Thresholds

Set alerts for:
- Error rate > 5%
- P95 latency > 30 seconds
- Hourly cost > budget threshold
- Quality score drop > 20%

---

## Best Practices

### 1. Correlation IDs

Link application logs with LangSmith traces:

```python
import logging
from langsmith import get_current_run_tree

logger = logging.getLogger(__name__)

@traceable
def process_workflow(data: dict):
    run_tree = get_current_run_tree()
    correlation_id = run_tree.trace_id if run_tree else "no-trace"
    
    logger.info(f"Processing workflow [trace_id={correlation_id}]")
    # Implementation
```

### 2. Feedback Collection

Collect feedback at multiple levels:
- User thumbs up/down on final output
- Automated evaluator scores on intermediates
- Reviewer agent feedback on drafts

### 3. Cost-Aware Development

Use LangSmith's cost tracking to:
- Identify expensive workflows
- Optimize model selection (GPT-4 vs GPT-3.5)
- Set and monitor budget alerts

### 4. A/B Testing

When improving agents:
1. Create new prompt version in code (e.g., `TEMPLATE_V2`)
2. Use feature flag to control which version is active
3. Tag traces with prompt version in metadata
4. Compare metrics in LangSmith dashboard
5. Roll out winner or roll back

---

## Integration Checklist

### Phase 1: Core Setup
- [ ] Create LangSmith account and project
- [ ] Add environment variables to `.env`
- [ ] Install LangSmith SDK
- [ ] Verify tracing with hello world
- [ ] Create `core/langsmith_config.py`

### Phase 2: Instrumentation
- [ ] Add `@traceable` to all agent functions
- [ ] Add metadata and tags to traces
- [ ] Implement correlation IDs in logging
- [ ] Test end-to-end tracing

### Phase 3: Evaluation
- [ ] Create `core/evaluators.py` with custom functions
- [ ] Create golden dataset from production samples
- [ ] Set up CI/CD evaluation runs
- [ ] Configure evaluation dashboards

### Phase 4: Monitoring
- [ ] Create production dashboards (cost, performance, quality)
- [ ] Set up alerts for critical metrics
- [ ] Implement feedback collection
- [ ] Document runbooks for alerts

---

## Key Takeaways

1. **LangSmith handles offline evaluation** - Use it for CI/CD, monitoring, and retrospective analysis
2. **Build Reviewer agents for online evaluation** - Real-time quality gates are not replaced by LangSmith
3. **Prompts live in code** - Git-versioned, LangSmith for experimentation only
4. **Trace everything** - Complete visibility without custom infrastructure
5. **No runtime dependencies** - System works without LangSmith (graceful degradation)

---

**For detailed architecture context, see:**
- `AGENTS_DESIGN.md` - Agent hierarchy and quality assurance strategy
- `PROJECT_STRUCTURE.md` - File organization and component details
- `ARCHITECTURE_REVIEW.md` - Architecture validation and implementation roadmap