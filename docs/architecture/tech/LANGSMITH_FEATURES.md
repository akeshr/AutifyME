# LangSmith - Observability & Evaluation Platform

**Created:** October 7, 2025
**Installed SDK:** `langsmith` (via environment, version tracked in pyproject.toml)
**Platform Type:** Cloud-based SaaS (free tier available)
**Already Integrated:** ✅ Active in AutifyME codebase

**Reference Materials:**
- Platform: https://smith.langchain.com
- Documentation: https://docs.smith.langchain.com
- Cookbook: https://github.com/langchain-ai/langsmith-cookbook

---

## Executive Summary

LangSmith is LangChain's **unified observability and evaluation platform** for LLM applications. Think Datadog/New Relic for AI agents—tracing, debugging, testing, and monitoring in one platform.

**Core Value Proposition:**
Production LLM applications are non-deterministic black boxes. LangSmith makes them transparent, testable, and improvable through:
1. **Observability:** See every LLM call, tool invocation, agent decision
2. **Evaluation:** Test prompt versions, measure quality, prevent regressions
3. **Monitoring:** Track costs, latency, errors, user feedback in production
4. **Prompt Engineering:** Version, collaborate, A/B test prompts without code changes

**Framework Agnostic:** Works with LangChain, OpenAI, Anthropic, or any LLM stack (via OpenTelemetry).

**AutifyME Status:** Already integrated for trace collection. Ready to leverage evaluation and monitoring features.

---

## 🔍 Observability & Tracing

### Automatic Tracing

**Every LLM call auto-traced when LangSmith SDK is configured.**

**What's Captured:**
- **Inputs:** User messages, system prompts, context
- **Outputs:** LLM responses, tool results, structured outputs
- **Metadata:** Model name, temperature, token counts, latency, cost
- **Hierarchy:** Parent-child relationships (agent → tool → LLM)

**Trace Structure:**
- **Run:** Single operation (LLM call, tool invocation, agent step)
- **Trace:** Complete execution tree from user input to final output
- **Thread:** Series of related traces (conversation history)

### Real-Time Streaming

Traces stream continuously during execution—no waiting for completion. Token events appear near real-time in dashboard.

**Why This Matters:**
- Debug live WhatsApp cataloging sessions
- See what PM is deciding in real-time
- Catch infinite loops before they drain credits

### Trace Search & Filtering

**Query traces by:**
- Time range, user ID, thread ID
- Model used, latency thresholds, cost ranges
- Error status, feedback scores
- Custom metadata tags

**Why This Matters:**
- Find all failed cataloging attempts from last week
- Identify slow image analysis calls
- Track high-cost PM decisions

### Trace Replay & Comparison

**Replay:**
Re-run failed traces with different inputs/prompts without modifying code.

**Comparison:**
Diff two traces side-by-side to see what changed (different prompts, models, parameters).

**Why This Matters:**
- Reproduce bugs in isolation
- Test prompt improvements on historical failures
- Compare agent behavior before/after code changes

---

## 📊 Evaluation & Testing

### Datasets

**Collections of test examples for evaluation.**

**Structure:**
- **Input:** Variables passed to your application (e.g., user message, image URL)
- **Reference Output (optional):** Expected result for evaluator comparison
- **Metadata:** Tags, notes, source information

**Dataset Sources:**
- Manual creation in UI
- Exported from production traces
- Imported from CSV/JSON
- Programmatically via SDK

**Why This Matters:**
- Build cataloging test suite from real WhatsApp interactions
- Regression testing: ensure prompt changes don't break existing flows
- Benchmark: compare PM strategies on same decision scenarios

### Evaluators

**Functions that score LLM outputs.**

**Types:**

**1. LLM-as-Judge:**
Use an LLM to evaluate outputs (correctness, tone, relevance, harmfulness).

**Built-in Evaluators:**
- Correctness, Relevance, Helpfulness
- Toxicity, Bias, Hallucination detection
- Custom criteria (via prompt)

**2. Custom Code:**
Python/TypeScript functions for deterministic checks.

**Constraints:**
- **Allowed libraries:** numpy, pandas, jsonschema, scipy, sklearn only
- **No network access:** Cannot make external API calls
- **Inline functions:** Must be self-contained (no imports of user modules)

**Examples:**
- Structure validation (Pydantic schema compliance)
- Statistical properties (response length, keyword presence)
- Business rules (price within range, category valid)

**3. Human Annotators:**
Subject-matter experts score outputs via annotation queues.

**4. Pairwise Evaluations:**
Compare two outputs side-by-side to determine which is better.

**Use Cases:**
- A/B testing prompt variations
- Model comparison (GPT-5 vs Claude)
- Ranking multiple candidate responses

**5. Self-Improving Evaluators:**
LLM evaluators that improve based on feedback and corrections.

**Pattern:**
Collect human feedback on evaluator judgments, fine-tune evaluator prompts or models to align with human preferences over time.

**Why This Matters:**
- Validate product data quality (structured output compliance)
- Check brand voice alignment (LLM-as-judge on tone)
- Measure approval accuracy (human annotators review agent decisions)
- Compare prompt versions objectively (pairwise evaluation)
- Evaluator quality improves automatically from production feedback

### Offline Evaluation

**Run evaluations on datasets before deployment.**

**Two Modes:**

**1. Prompt Playground (No Code):**
Test prompt variations over dataset examples, compare scores across versions, iterate in UI without code changes.

**2. SDK (Programmatic):**
Run evaluations in CI/CD pipelines, integrate with pytest, automate regression testing.

**Experiment Tracking:**
Each evaluation creates an experiment entry with scores, comparisons, and versioning.

**Why This Matters:**
- Test new PM prompts on historical decision scenarios
- Validate cataloging specialist improvements before production
- CI/CD gate: fail build if evaluation scores drop

### Online Evaluation

**Run evaluations on live production traces.**

**Use Cases:**
- Monitor output quality continuously
- Flag toxic/hallucinated responses immediately
- Trigger alerts on quality degradation

**Automation:**
Configure rules to automatically evaluate traces matching criteria (e.g., all cataloging runs with images).

**Why This Matters:**
- Detect quality issues before users complain
- Monitor brand voice consistency in production
- Track hallucination rates in product descriptions

---

## 🛠️ Prompt Engineering

### Prompt Hub

**Version control for prompts with collaboration features.**

**Features:**
- **Versioning:** Commit prompts, track history, rollback changes
- **Collaboration:** Team members propose improvements via Prompt Canvas
- **Tagging:** Production, staging, experimental tags
- **Webhooks:** Trigger CD pipeline on prompt commit

**Benefits:**
- Prompts versioned alongside code (Git-like workflow)
- Non-engineers can improve prompts via UI
- A/B test prompt versions without deployments

### Prompt Playground

**Interactive environment for prompt experimentation.**

**Capabilities:**
- Test prompts with different models (GPT-5, Claude, etc.)
- Run over dataset examples (no code needed)
- Compare outputs side-by-side
- Add evaluators and see scores in real-time
- Save successful variations to Hub

**Why This Matters:**
- Iterate on PM instructions without redeployment
- Test cataloging prompts on edge cases quickly
- Compare Claude vs. GPT-5 for specialist tasks

### Prompt Comparison

**Side-by-side comparison of prompt versions.**

Visualize how different prompts perform on same inputs with metrics (latency, cost, quality scores).

**Why This Matters:**
- Validate improvements before rolling out
- Choose between multiple prompt strategies objectively
- Share results with team for decision-making

---

## 📈 Production Monitoring

### Dashboards & Metrics

**Live dashboards tracking:**
- **Cost:** Token usage, API costs by model/endpoint
- **Latency:** p50/p95/p99 response times, time-to-first-token
- **Quality:** User feedback scores, evaluator scores, error rates
- **Volume:** Requests per minute, users, threads

**Custom Dashboards:**
Filter by time range, user segments, workflow types.

**Why This Matters:**
- Track WhatsApp cataloging costs per product
- Monitor PM decision latency
- Identify slow image analysis calls

### Alerts & Notifications

**Configure alerts for:**
- High error rates (> 5% failures)
- Cost spikes (daily budget exceeded)
- Latency degradation (p95 > threshold)
- Quality drops (feedback scores declining)

**Notification Channels:**
- Email, Slack, webhook

**Why This Matters:**
- Get paged when cataloging workflow breaks
- Alert on runaway PM costs
- Catch quality regressions early

### User Feedback

**Capture thumbs up/down from users.**

**Integration:**
SDK method to attach feedback to any run (not just top-level trace, but specific tool calls or agent steps).

**Feedback Types:**
- Binary (thumbs up/down)
- Score (1-5 stars)
- Comment (text feedback)
- Correction (user-provided fix)

**Why This Matters:**
- WhatsApp users flag bad product categorizations
- Track approval rejection reasons
- Build datasets from user-flagged issues

---

## 🤝 Collaboration Features

### Annotation Queues

**Streamlined review process for runs.**

**Workflow:**
1. Flag runs for annotation (manually or via automation rules)
2. Annotators review in dedicated queue UI
3. Leave feedback, notes, or add to datasets
4. Track annotation progress

**Use Cases:**
- Review runs with negative user feedback
- Quality assurance sampling (10% of cataloging runs)
- Build training datasets from production traces

### Threads & Sessions

**Group related traces into conversations.**

**Thread View:**
See entire back-and-forth conversation in single view (WhatsApp chat history), navigate through messages and AI responses, inspect state at each turn.

**Why This Matters:**
- Debug multi-turn cataloging conversations
- See how PM adapted plan over multiple user inputs
- Understand context that led to specific decisions

### Team Features

- **Shared workspaces:** Entire team sees same traces, datasets, prompts
- **Access control:** Read-only, annotator, admin roles
- **Comments:** Leave notes on specific traces or experiments
- **Prompt Canvas:** Non-engineers propose prompt improvements

---

## 🔧 Automation & Integration

### Rules & Automations

**Trigger actions when traces match criteria.**

**Supported Actions:**
1. **Add to Dataset:** Auto-curate test examples from production
2. **Add to Annotation Queue:** Flag for human review
3. **Trigger Webhook:** Send trace data to external system
4. **Extend Retention:** Keep important traces longer

**Example Rules:**
- "Add to dataset: all cataloging runs with user feedback < 3"
- "Add to queue: all PM decisions with cost > $0.50"
- "Webhook: all failed tool calls to PagerDuty"

**Why This Matters:**
- Automatically build test suites from production failures
- Route edge cases to human reviewers
- Integrate with incident management systems

### Webhooks

**HTTP POST on configured events:**
- New traces matching rules
- Prompt commits
- Alert triggers

**Payload:**
Includes full trace data, feedback, metadata.

**Why This Matters:**
- Trigger retraining pipelines on quality drops
- Update dashboards in external BI tools
- Custom alerting logic in your infrastructure

### SDK Integration

**@traceable Decorator:**
Trace any Python function (not just LangChain code).

**Custom Metadata:**
Attach tags, user IDs, session IDs to traces.

**OpenTelemetry Support:**
Send spans via standard OpenTelemetry client—works with Datadog, Grafana, Jaeger.

**Why This Matters:**
- Trace non-LangChain code (custom business logic)
- Correlate LangSmith traces with infrastructure metrics
- Unified observability across AI and traditional services

---

## 💰 Cost Tracking

**Granular cost visibility:**
- Per trace, per user, per workflow
- Model-specific costs (GPT-5 vs. Claude)
- Tool execution costs (API calls)

**Cost Attribution:**
Tag traces with customer IDs, departments, features for chargeback reporting.

**Cost Optimization:**
Identify expensive operations, compare model costs, detect waste (redundant calls, inefficient prompts).

**Why This Matters:**
- Track cataloging costs per customer
- Optimize PM orchestration (cheaper models for simple decisions)
- Budget alerts before overspending

---

## 📚 LangSmith Cookbook

**Official collection of recipes and best practices.**

**Key Recipes:**
- **Automated Few-Shot Bootstrapping:** Curate best examples based on performance
- **Iterative Prompt Optimization:** Use feedback to improve prompts automatically
- **RAG Evaluation with RAGAS:** Measure retriever and generator quality
- **Streaming with Feedback:** Collect user input during streaming responses

**Repository:** https://github.com/langchain-ai/langsmith-cookbook

**Why This Matters:**
- Battle-tested patterns for common use cases
- Avoid reinventing evaluation strategies
- Learn from community best practices

---

## 🎯 AutifyME Usage Strategy

### Current Usage (Minimal)
- ✅ Tracing enabled (LANGSMITH_API_KEY set)
- ✅ Traces collected for cataloging workflow
- ❌ No evaluation datasets
- ❌ No monitoring dashboards configured
- ❌ No user feedback collection

### Week 1-2: Validation & Debugging
**Goal:** Use tracing to validate cataloging workflow and debug issues.

**Actions:**
- Review traces for each WhatsApp cataloging session
- Identify failed tool calls and errors
- Trace PM decisions to understand routing logic
- Use replay to reproduce bugs

### Month 1: Evaluation Setup
**Goal:** Build evaluation datasets and regression tests.

**Actions:**
- Export successful cataloging traces → dataset
- Create evaluators for product data quality (Pydantic validation)
- Run baseline evaluation on current prompts
- Set up CI/CD gate: fail build if scores drop

### Month 2: Production Monitoring
**Goal:** Monitor production performance and quality.

**Actions:**
- Configure dashboards for cost, latency, error rates
- Set alerts for high error rates and cost spikes
- Enable user feedback (thumbs up/down) in WhatsApp flow
- Create annotation queue for negative feedback

### Month 3: Prompt Optimization
**Goal:** Iteratively improve prompts based on production data.

**Actions:**
- Commit all prompts to Hub
- Run A/B tests on prompt variations
- Use LLM-as-judge to score brand voice consistency
- Optimize PM instructions based on decision quality

---

## 📊 Key Metrics to Track

### Cataloging Workflow
- **Success Rate:** % of products cataloged without approval rejection
- **Quality Score:** Evaluator score on structured output compliance
- **Latency:** Time from image upload to approval request
- **Cost:** Average cost per product cataloged

### Project Manager
- **Decision Quality:** % of decisions requiring human override
- **Routing Accuracy:** Did PM route to correct department?
- **Cost Efficiency:** Total cost vs. alternative strategies
- **Latency:** Time to first department invocation

### Overall System
- **Error Rate:** % of traces with errors
- **User Satisfaction:** Average user feedback score
- **Token Usage:** Total tokens consumed per day/week/month
- **Model Distribution:** Usage across GPT-5, Claude, etc.

---

## 🚀 Advanced Features (Future)

### LangGraph Platform Integration
LangSmith is tightly integrated with LangGraph Platform (managed agent hosting).

**Features:**
- Auto-tracing of deployed agents
- HITL approval UIs built-in
- Production monitoring out-of-box

**Note:** Not using LangGraph Platform (need single-tenant deployments), but can benefit from LangSmith's LangGraph-specific features.

### Continuous Evaluation
Set up evaluators that run automatically on production traffic (not just datasets).

**Pattern:**
Every Nth trace gets evaluated in real-time, scores tracked over time, alerts on degradation.

### Feedback-Driven Prompt Optimization
Use negative feedback to automatically identify problematic prompt sections, suggest improvements via LLM, test variations on affected examples.

---

## 💡 Best Practices

### Tracing
- Tag traces with user IDs, session IDs, workflow types for filtering
- Use custom metadata for business context (customer tier, product category)
- Keep trace names descriptive (not just "agent" but "cataloging_department_agent")

### Evaluation
- Start with simple evaluators (structure validation) before complex (LLM-as-judge)
- Build datasets incrementally from production (don't try to create perfect test suite upfront)
- Run evaluations in CI/CD to catch regressions early

### Monitoring
- Set conservative alert thresholds initially (avoid alert fatigue)
- Track leading indicators (latency, error rate) not just lagging (user complaints)
- Review dashboards weekly to spot trends

### Prompt Engineering
- Commit prompts to Hub before major experiments (easy to rollback)
- Use Playground for quick iterations, SDK for final testing
- Document prompt changes (why this version, what improved)

---

## 🔗 Integration with AutifyME Stack

**LangChain Integration:**
Native first-class support—all LangChain agents auto-traced.

**LangGraph Integration:**
Traces show graph structure (nodes, edges), checkpoint metadata included, interrupt points visible.

**DeepAgents Integration:**
Planning steps, sub-agent invocations, filesystem operations all traced.

**OpenAI/Anthropic:**
Works via LangChain integration or direct SDK tracing.

**Supabase/PostgreSQL:**
No direct integration, but can correlate traces with DB operations via custom metadata.

---

## 📚 Key Resources

- **Platform:** https://smith.langchain.com
- **Documentation:** https://docs.smith.langchain.com
- **Cookbook:** https://github.com/langchain-ai/langsmith-cookbook
- **SDK Reference:** https://docs.smith.langchain.com/reference/sdk
- **Community Forum:** https://forum.langchain.com

---

## 🎯 Next Steps

**Immediate (This Week):**
1. Review existing cataloging traces to understand workflow
2. Identify and debug any failed runs
3. Document trace patterns for future reference

**Short-Term (Month 1):**
1. Export 20-30 successful cataloging traces to dataset
2. Create Pydantic evaluator for product data structure
3. Run baseline evaluation on current prompts

**Medium-Term (Month 2-3):**
1. Set up production monitoring dashboards
2. Configure cost and error rate alerts
3. Integrate user feedback from WhatsApp
4. Commit prompts to Hub and start A/B testing

---

**Last Updated:** 2025-10-07
**Author:** AutifyME Team
**Status:** Integrated & Ready for Advanced Features
