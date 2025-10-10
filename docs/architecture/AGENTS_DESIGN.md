# AutifyME Agentic System Design

This document outlines the architectural pattern for the multi-agent system that powers AutifyME. The design prioritizes scalability, reusability, and effective context management within a single-tenant deployment model. It describes the enduring architecture; current implementation status or roadmap commentary lives in workflow-specific documents.

---

## 1. Product Delivery Model: Single-Tenant Managed Service

The AutifyME product will be delivered as a **Single-Tenant Managed Service**. This means that each client (company) will receive their own completely isolated and dedicated instance of the entire application stack (database, agent service, etc.).

-   **Architectural Implications:**
    -   **Data Isolation:** Data is physically segregated at the infrastructure level, providing the highest level of security and privacy.
    -   **Simplified Logic:** The application code does not need to handle multi-tenancy. There is no `company_id` required in our data models, as the entire application instance serves a single company.
    -   **Context Management:** The "company profile" and other contextual data will be loaded at application startup, as it is constant for the lifetime of the instance.

---

## 2. Core Principles

- **Hierarchy & Delegation:** Instead of a single monolithic agent, the system is a hierarchy of specialized agents. Higher-level agents delegate tasks to lower-level agents, mirroring a well-structured organization.
- **Separation of Concerns:** Each agent has a single, well-defined responsibility. This makes them easier to build, test, debug, and reuse.
- **Managed Context:** By breaking down problems and delegating, we ensure that each agent only receives the context necessary for its specific task. This avoids overwhelming a single agent with an entire business's state, leading to better performance and reliability.
- **Stateful & Event-Driven:** Agents operate within state machines (graphs) and react to changes in state, allowing for complex, long-running, and interruptible (e.g., for HITL) workflows.

---

## 3. Proposed Architecture: The "Department" Model

We will model our system after a company's organizational structure. A central routing agent acts as a "Project Manager," decomposing complex goals and directing tasks to the appropriate "Department," which in turn manages "Specialist" agents to get the work done.

### The Agent Hierarchy

```
[User Request]
      │
      ▼
┌─────────────────────────┐
│ Project Manager Agent   │ (Planner & Orchestrator)
└─────────────────────────┘
      │
      ├─► [Marketing Dept] ─► [Copywriter Agent, SEO Agent, ...]
      ├─► [Operations Dept] ─► [Billing Agent, Shipping Agent, ...]
      └─► [Website Dept] ─► [Content Update Agent, Redesign Agent, ...]

```

### Component Responsibilities

1.  **Project Manager Agent (The Orchestrator):**
    - **Purpose:** The single entry point for all user requests. Its job is to understand complex goals, create a multi-step, multi-department execution plan, and orchestrate the workflow.
    - **Function:** It analyzes the user's request and decomposes it into a graph of dependent tasks. It then routes these tasks to the appropriate Department Head Agents and manages the state of the overall project, kicking off new tasks as dependencies are met.
    - **Implementation:** A LangGraph graph that creates a sub-graph of tasks. It is responsible for orchestrating the flow between other agents.

2.  **Department Head Agents (The Managers):**
    - **Purpose:** To manage a specific business domain (e.g., Marketing, Operations, Website).
    - **Function:** It receives a high-level goal from the Project Manager. It then breaks that goal down into a multi-step plan and delegates each step to one or more Specialist Agents. It orchestrates the specialists, gathers their results, and ensures the overall goal is met.
    - **Example:** The `MarketingDeptAgent` receives the goal "run a campaign." It plans the steps: 1) write copy, 2) generate images, 3) post to platforms. It then delegates step 1 to the `CopywriterAgent`, step 2 to the `VisualDesignerAgent`, and so on.

3.  **Specialist Agents (The Doers):**
    - **Purpose:** To execute a very specific, well-defined task. These are our reusable workhorses.
    - **Function:** A Specialist Agent takes a clear instruction from a Department Head and uses a set of deterministic **Tools** to accomplish it. A Specialist Agent might use an LLM for its task (e.g., the `CopywriterAgent` uses an LLM to write text), but its scope is narrow.
    - **Example:** The `SEOAuditAgent` receives a URL from the `WebsiteDeptAgent`. It uses a `LighthouseTool` and a `CrawlTool` to perform an audit and returns a structured report.

4.  **Tools (The Utilities):**
    - **Purpose:** The lowest level of the hierarchy. These are deterministic Python functions that interact with the outside world.
    - **Function:** They perform a single, reliable action, like making a database call, sending an email, or calling a third-party API. They do not contain any LLM logic.
    - **Example:** `create_invoice_in_supabase(customer_id, amount)`.

### Agent Implementation Strategy: DeepAgents vs. Standard Agents

**Architectural Decision:** We employ a tiered implementation strategy that reserves DeepAgents complexity for orchestration while keeping execution layers simpler.

**Implementation Layers:**

1.  **Project Manager (DeepAgents):**
    - **Framework:** `deepagents.create_deep_agent`
    - **Rationale:** Requires advanced planning, sub-task decomposition, cross-department coordination, and complex state management
    - **Features Used:**
      - Planning middleware (task decomposition, dependency tracking)
      - Filesystem middleware (persistent scratchpad for long-running workflows)
      - Sub-agent delegation (routing to departments)
      - Built-in HITL configuration for high-risk operations
    - **Complexity Justification:** The PM handles the most complex orchestration logic in the system and needs DeepAgents' advanced capabilities

2.  **Department Heads (Standard LangChain Agents):**
    - **Framework:** `langchain.agents.create_agent`
    - **Rationale:** Focused domain orchestration with well-defined specialist tools
    - **Features Used:**
      - Standard ReAct agent pattern
      - Middleware (HITL, company context, tracing)
      - Structured outputs for PM communication
    - **Why Not DeepAgents:** Department scope is narrower and doesn't require the full planning/sub-agent complexity that DeepAgents provides

3.  **Specialists (Standard LangChain Chains):**
    - **Framework:** `RunnableLambda` + `with_structured_output`
    - **Rationale:** Deterministic, single-purpose transformations
    - **Features Used:**
      - Structured LLM outputs (Pydantic models)
      - Simple prompt → LLM → validation chains
    - **Why Not Agents:** Specialists don't need tool-calling or planning—just input transformation

4.  **Tools (Pure Python Functions):**
    - **Framework:** `@tool` decorator
    - **Rationale:** Deterministic operations with zero LLM logic
    - **Features Used:**
      - Type-safe arguments (Pydantic schemas)
      - Error handling with custom exceptions
      - Retry logic for external APIs

**PM → Department Delegation Pattern:**

Departments are exposed to the PM as **tools**, not DeepAgents sub-agents:

```python
# Project Manager sees departments as tools
@tool("cataloging_department")
def invoke_cataloging_department(user_message: str, image_url: str | None = None) -> CatalogingResult:
    """Catalog a product from user input and optional image."""
    # Internally, this tool invokes the cataloging department agent
    dept_agent = create_cataloging_department(storage=storage, checkpointer=checkpointer)
    return dept_agent.invoke({"messages": [HumanMessage(content=user_message)]})
```

This approach:
- **Simplifies architecture**: Departments don't need DeepAgents' planning/sub-agent machinery
- **Maintains hierarchy**: PM delegates via tools (standard LangChain pattern)
- **Preserves flexibility**: Departments can be swapped/upgraded without changing PM
- **Reduces complexity**: Fewer moving parts, easier debugging
- **Stays aligned with LangChain v1**: Standard `create_agent` is stable and well-documented

**When to Re-evaluate:**

If a department grows to require multi-step planning across sub-domains (e.g., Marketing needs to coordinate Social, Email, and SEO sub-departments), consider promoting it to DeepAgents. For now, our domain scopes are well-bounded and don't require this level of orchestration.

### Specialist Classification: Simple vs. Complex

Specialists exhibit two distinct patterns based on their orchestration needs:

**Simple Specialists (Transformation-Only):**
- **Nature:** Single LLM invocation transforming input to structured output
- **Implementation:** `@tool` function or `RunnableLambda` chain with `with_structured_output`
- **Characteristics:** No dynamic decision-making, no tool orchestration, deterministic flow
- **Examples:** Image analysis (vision model → structured data), entity extraction, sentiment scoring
- **Salesforce Analogy:** Like an Apex `@InvocableMethod` that processes input and returns output without querying multiple objects or calling external services

**Complex Specialists (Multi-Tool Orchestration):**
- **Nature:** Agents that orchestrate multiple tools with dynamic decision-making
- **Implementation:** `create_agent` with tool list
- **Characteristics:** ReAct reasoning loop, conditional tool selection based on intermediate results, multi-step workflows
- **Examples:** SEO auditor (crawl → performance analysis → ranking checks → synthesis), invoice generator (fetch customer → calculate tax → generate PDF → email), research synthesizer (search → scrape → analyze → summarize)
- **Salesforce Analogy:** Like a complex Apex service class with `@future` calls, multiple DML operations, and conditional external API callouts—orchestrates multiple operations with governor limit awareness

**Decision Criteria:**

The distinction hinges on **orchestration complexity**, not output complexity:
- If the specialist can complete its task with one LLM call (possibly with structured output), it's simple
- If the specialist must decide which tools to invoke based on runtime conditions or intermediate results, it's complex

**Architectural Consistency:**

Both types are exposed to departments as tools. Complex specialists wrap their internal agent runtime within a `@tool` interface, maintaining the hierarchy's clean abstraction layers. This preserves the department's view: "I have tools that do specific jobs," whether those tools are simple transforms or mini-orchestrators.

**Current Implementation Status:**
- ✅ Simple specialists: Image analysis, cataloging (current implementations align)
- 🔜 Complex specialists: SEO audit, invoice generation (future workflows will require agent implementation)

---

## 4. Advanced Concepts: Handling Complex Workflows

This architecture is designed to handle complex, real-world business processes that require the coordination of multiple teams and can be optimized for speed.

### Multi-Department Orchestration

For any user request that cannot be handled by a single department (e.g., "Launch a new product"), the **Project Manager Agent** takes charge.

1.  **Decomposition:** It breaks the high-level goal into a series of smaller, actionable tasks.
2.  **Dependency Mapping:** It identifies the dependencies between these tasks, forming a Directed Acyclic Graph (DAG).
3.  **Departmental Assignment:** It assigns each task to the appropriate department.
4.  **Managed Execution:** It orchestrates the execution of this graph, sending tasks to departments only when their prerequisite tasks are complete. This ensures that a website landing page is created *before* the marketing team tries to run ads to it.

### Parallel Task Execution

LangGraph natively supports the parallel execution of tasks that do not have dependencies on each other. This is leveraged at two levels:

-   **Inter-Department Parallelism:** The **Project Manager Agent** can initiate tasks in multiple departments simultaneously if the plan allows for it. For a product launch, it can task the `Operations Dept` with checking inventory at the same time it tasks the `Website Dept` with building a landing page.
-   **Intra-Department Parallelism:** A **Department Head Agent** can also run its own internal tasks in parallel. For example, the `MarketingDeptAgent` can delegate "generate ad copy" to the `CopywriterAgent` and "generate ad creative" to the `VisualDesignerAgent` at the same time. This significantly reduces the time it takes to complete a workflow.

### Cross-Department Data Sharing

A core principle of this architecture is that agents do not communicate directly with agents in other departments. This would create tight coupling and make the system brittle. Instead, data is shared by passing it up and down the hierarchy.

1.  **Data Request:** An agent identifies a need for data from another domain.
2.  **Ascend to Common Manager:** The request flows up the hierarchy to the first agent that manages both the requesting and the providing department (this is usually the **Project Manager Agent**).
3.  **Delegate and Fetch:** The managing agent creates a task to fetch the required data and delegates it to the appropriate department.
4.  **Descend with Context:** Once the data is returned to the manager, it initiates the original task, passing the fetched data in as part of the context.

This ensures that data dependencies are explicitly managed, tracked, and kept clean. A specialist agent only ever receives the precise information it needs to do its job.

---

## 5. Example Workflow: "Launch a new product: the 'Auto-Widget'"

1.  **User Request:** "Launch our new product, the 'Auto-Widget'."
2.  **Project Manager Agent** receives the request. It creates a plan (DAG):
    - a. `[Operations]` Ensure product is in inventory.
    - b. `[Website]` Build product landing page.
    - c. `[Marketing]` Draft announcement blog post. (Depends on b)
    - d. `[Marketing]` Launch social media campaign. (Depends on c)
3.  **Parallel Execution:** The `Project Manager` initiates tasks (a) and (b) simultaneously by sending them to the `Operations` and `Website` departments, respectively.
4.  **Orchestration:**
    - The `Operations Dept` completes its task.
    - The `Website Dept` completes the landing page and returns the URL. The `Project Manager` now knows that dependency (b) is met.
5.  **Handoff:** The `Project Manager` initiates task (c), sending the goal and the new URL to the `Marketing Dept`.
6.  The `Marketing Dept` proceeds with its internal plan (e.g., SEO research, copywriting, image generation, which can also be parallelized) and eventually completes the blog post.
7.  This process continues until the entire project graph is complete.

---

## 6. Resilience & Safeguards

To build a production-grade system, the architecture must be resilient to failures and unexpected behavior. The following patterns will be implemented to ensure robustness.

### Error Handling & Recovery

We leverage **LangChain v1's built-in error handling** for consistent, production-grade error management:

-   **Critical Operations:** For database writes or irreversible actions, we can configure agents to fail fast by setting `handle_errors=False`.
-   **Self-Healing Operations:** For most operations, we'll use `handle_errors=True`, which enables the agent's self-correction capabilities. The LLM can learn from tool errors and adjust its approach.
-   **Best-Effort Operations:** For optional tasks, `handle_errors=True` is also suitable, as the agent can log the error and decide to continue with the main workflow.

```python
from langchain.agents import create_agent

agent = create_agent(
    model=llm,
    tools=tools,
    handle_errors=True  # v1: Enables self-correction
)
```

-   **Tool Exception Pattern:** Tools raise `ToolException` (not generic exceptions) to prevent infinite retry loops and provide structured error feedback to agents.

**Reference:** See [LANGCHAIN_V1_FEATURES.md](./LANGCHAIN_V1_FEATURES.md#enhanced-error-handling--resilience) for details.

### State Persistence & Resumption

-   **Stateful Workflows:** All agent workflows are stateful. The complete state of every in-progress workflow will be persisted to the Supabase database after each step (checkpointing).
-   **Resume on Failure:** Each workflow will have a unique ID. In the event of a system crash or restart, a recovery mechanism will scan for "in-progress" workflows and resume them from their last saved state. This is critical for supporting long-running tasks.

### Infinite Loop Prevention

-   **Maximum Step Count:** Each workflow will have a configurable maximum number of steps (e.g., 50). If a workflow exceeds this limit, it will be automatically paused and flagged for human review to prevent runaway execution. We enforce this today by passing `recursion_limit` in the WhatsApp runner before invoking the cataloging department.
-   **Prompt-Based Safeguards:** The core prompts for manager-level agents (`Project Manager`, `Department Head`) will include explicit instructions to detect and report a lack of progress or cyclical logic, rather than retrying a failed approach indefinitely.

### Human-in-the-Loop (HITL) Integration

We use **LangChain v1's native `interrupt_before`** for approval workflows:

```python
from langchain.agents import create_agent

agent = create_agent(
    model=llm,
    tools=tools,
    interrupt_before=["save_product", "publish_website", "send_invoice"]  # v1: Auto-pause
)
```

-   **Workflow:** Agent plans to call an interrupt-enabled tool → execution pauses → state persisted → user notified → user approves/edits/rejects → execution resumes
-   **Benefits:** Built-in state management, automatic checkpointing, type-safe resume commands, no custom "paused" state needed

**Reference:** See [LANGCHAIN_V1_FEATURES.md](./LANGCHAIN_V1_FEATURES.md#4-langgraph-runtime-integration) for HITL patterns.

---

## 7. Agent Evaluation & Quality Assurance

To ensure agents perform tasks to a high standard, a **dual evaluation strategy** is implemented: **offline evaluation** for retrospective analysis and continuous improvement, and **online evaluation** for real-time quality gates in production workflows.

**Critical Distinction:** These are complementary approaches. LangSmith handles offline evaluation, but does NOT replace the need for in-workflow Reviewer agents.

### Offline Evaluation (LangSmith - Retrospective)

**Purpose:** Prevent regressions, compare versions, monitor quality trends over time.

**When:** CI/CD pipelines, nightly runs, A/B testing, historical analysis.

**How:**
-   **Golden Datasets:** Create and maintain datasets in LangSmith containing representative inputs and expected outputs for key workflows.
-   **Custom Evaluators:** Define custom evaluator functions (Python code) that score agent outputs against business criteria (e.g., brand voice, accuracy, completeness). These are NOT separate agents; they are functions registered with LangSmith.
-   **Automated Testing:** Any change to an agent triggers an evaluation run in CI/CD. The modified agent runs against its golden dataset, outputs are scored by evaluators, and the change is rejected if quality drops below threshold.
-   **A/B Testing:** Deploy new agent versions to a subset of traffic and compare performance in LangSmith dashboards.

**Example:**
```python
from langsmith import Client

# Define custom evaluator function
def brand_voice_evaluator(run_input: dict, run_output: dict) -> dict:
    """Evaluates if output matches company brand voice."""
    # Use LLM or rules to score
    score = evaluate_brand_voice(run_output["description"], company_profile)
    return {"score": score, "feedback": "..."}

# Run evaluation in CI/CD
client = Client()
client.evaluate(
    cataloging_workflow,
    data="product-cataloging-golden",
    evaluators=[brand_voice_evaluator, accuracy_evaluator]
)
```

### Online Evaluation (Reviewer Agents - Real-Time)

**Purpose:** Ensure quality NOW, before proceeding to next step. Enable self-correction and refinement loops.

**When:** During production workflows, before expensive operations, before publishing, before irreversible actions.

**How:**
-   **Reviewer as a Specialist:** Quality assurance is treated as a task performed by a specialist agent (e.g., `ReviewerAgent`, `CriticAgent`, `ComplianceAgent`). These are real agents that run as part of the workflow.
-   **Critique & Refinement Loops:** A `Department Head` agent incorporates a review step into its plan. After a specialist produces output, a `ReviewerAgent` critiques it in real-time.
-   **Conditional Logic:** Based on the reviewer's output (score, approved/rejected, feedback), the department head decides:
    -   **If Approved:** Proceed with the workflow.
    -   **If Needs Refinement:** Send back to specialist with feedback for another attempt (up to max attempts).
    -   **If Rejected:** Escalate to human or block the action.

**Example:**
```python
@traceable(name="Create Product Description with Review Loop")
def create_product_with_qa(product_data: dict) -> dict:
    max_attempts = 3
    
    for attempt in range(max_attempts):
        # Specialist creates draft
        draft = copywriter_specialist.create_description(product_data)
        
        # Reviewer agent evaluates IN REAL-TIME
        review = reviewer_agent.review(
            output=draft,
            criteria=["brand_voice", "accuracy", "completeness"],
            context=company_profile
        )
        
        if review.approved:
            return draft  # Quality gate passed
        else:
            # Feed critique back to specialist
            product_data["previous_attempt"] = draft
            product_data["feedback"] = review.feedback
    
    # Max attempts reached - escalate to human
    return escalate_to_human(draft, review)
```

### How They Work Together

1.  **In Production:** Reviewer agents provide real-time quality gates
2.  **LangSmith Traces:** Every workflow (including reviewer feedback) is traced
3.  **Offline Analysis:** LangSmith evaluators analyze patterns and trends
4.  **Continuous Improvement:** Identify issues, update prompts/logic, A/B test
5.  **Deployment:** Roll out improvements based on offline evaluation data

### Implementation Guidelines

**Reviewer Agents:**
-   Create a generic `ReviewerAgent` specialist that can be reused across departments
-   Use structured output (Pydantic) for review results: `ReviewResult(score: float, approved: bool, feedback: str)`
-   Always set max attempts to prevent infinite loops
-   Log all reviews for analysis in LangSmith

**LangSmith Evaluators:**
-   Define evaluators as pure Python functions (not agents)
-   Store in `core/evaluators.py`
-   Register with LangSmith for automated runs
-   Use for regression testing, A/B testing, and monitoring

---

## 8. Context Engineering Strategy

To ensure our system is efficient, cost-effective, and avoids performance degradation from "context rot," we will adhere to the principles of **Effective Context Engineering**. This is a core architectural pillar.

**Guiding Principle:** Find the smallest possible set of high-signal tokens that maximize the likelihood of the desired outcome.

### Our Implementation Patterns:

1.  **Minimal Context via Sub-Agents (The "Need to Know" Basis):**
    -   **What:** The hierarchical agent design is our primary tool for context management. A `Specialist` agent receives *only* the specific inputs required for its task, not the entire history from the `Project Manager`.
    -   **Why:** This prevents context pollution, keeps prompts clean, and allows each agent to operate in a focused environment, drastically reducing token usage and improving reliability.

2.  **Token-Efficient Tools:**
    -   **What:** Every tool must have a single, well-defined purpose and return concise, structured data (Pydantic models). We will avoid creating generic, overlapping, or "chatty" tools.
    -   **Why:** This ensures agents can make clear decisions about which tool to use and receive predictable, token-efficient results, preventing the context window from being filled with verbose, low-signal information.

3.  **Just-in-Time Context Retrieval (Middleware):**
    -   **What:** Instead of front-loading static context (like the company profile) into the main prompt, we will use middleware to inject it into a tool's arguments at the moment of execution.
    -   **Why:** This keeps the primary agent's "working memory" free to focus on the dynamic task at hand, reducing the token count for every single LLM call in the workflow.

4.  **Strategies for Long-Horizon Tasks:**
    -   **What:** For workflows that may exceed the context window, we will employ explicit state management techniques.
        -   **Structured Note-Taking:** Provide agents with tools to write to and read from an external memory (e.g., a `scratchpad` table in Supabase).
        -   **Compaction:** Implement steps in our LangGraph workflows to periodically summarize the conversation history, keeping key decisions and discarding intermediate tool calls.
    -   **Why:** This allows agents to maintain coherence and achieve goals over extended periods without being constrained by the context window limit.

---

## 9. Prompt Management Strategy

To ensure our prompts are stable, version-controlled, and testable, while also allowing for rapid experimentation, we will adopt a hybrid prompt management strategy.

**Guiding Principle:** The production application MUST NOT have a runtime dependency on an external service (like LangSmith Hub) to load its core prompts.

### Our Implementation Patterns:

1.  **Git as the Source of Truth (Production):**
    -   **What:** All production-ready prompts are stored as plain text files (e.g., `.prompt`) within the `agents/src/autifyme_agents/prompts/` directory. These are committed directly to our Git repository.
    -   **How:** The application uses the `core.prompt_loader.load_prompt()` function to read these files from the local filesystem at runtime.
    -   **Why:** This guarantees maximum stability and resilience. The application can start and run without any external network dependency for its core instructions. Prompts are versioned alongside the code that uses them and go through the same review and CI/CD process.

2.  **LangSmith Hub as the Experimentation Platform (Development):**
    -   **What:** The LangSmith Hub is used as a playground and versioning system for developing and improving prompts.
    -   **How:** We will maintain a utility script (`scripts/sync_prompts.py`) to push local prompts to the Hub and pull updated versions back down.
    -   **Why:** This provides a powerful, collaborative environment for A/B testing, evaluating prompt performance against datasets, and iterating on prompt design without requiring code changes for every tweak.

### The Development Workflow:

1.  **Create:** A new prompt is created locally and committed to Git.
2.  **Push:** The developer pushes the prompt to LangSmith Hub using the sync script.
3.  **Experiment:** The team iterates on the prompt within the LangSmith UI, creating new versions.
4.  **Validate:** The new versions are tested against evaluation datasets in LangSmith.
5.  **Pull & Commit:** Once a superior version is identified, its content is pulled back down, overwriting the local `.prompt` file, and the change is committed to Git to be deployed to production.
