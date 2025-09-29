# AutifyME Agentic System Design

This document outlines the architectural pattern for the multi-agent system that powers AutifyME. The design prioritizes scalability, reusability, and effective context management.

---

## 1. Core Principles

- **Hierarchy & Delegation:** Instead of a single monolithic agent, the system is a hierarchy of specialized agents. Higher-level agents delegate tasks to lower-level agents, mirroring a well-structured organization.
- **Separation of Concerns:** Each agent has a single, well-defined responsibility. This makes them easier to build, test, debug, and reuse.
- **Managed Context:** By breaking down problems and delegating, we ensure that each agent only receives the context necessary for its specific task. This avoids overwhelming a single agent with an entire business's state, leading to better performance and reliability.
- **Stateful & Event-Driven:** Agents operate within state machines (graphs) and react to changes in state, allowing for complex, long-running, and interruptible (e.g., for HITL) workflows.

---

## 2. Proposed Architecture: The "Department" Model

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
    - **Function:** It receives a high-level goal from the Chief of Staff. It then breaks that goal down into a multi-step plan and delegates each step to one or more Specialist Agents. It orchestrates the specialists, gathers their results, and ensures the overall goal is met.
    - **Example:** The `MarketingDeptAgent` receives the goal "run a campaign." It plans the steps: 1) write copy, 2) generate images, 3) post to platforms. It then delegates step 1 to the `CopywriterAgent`, step 2 to the `VisualDesignerAgent`, and so on.

3.  **Specialist Agents (The Doers):**
    - **Purpose:** To execute a very specific, well-defined task. These are our reusable workhorses.
    - **Function:** A Specialist Agent takes a clear instruction from a Department Head and uses a set of deterministic **Tools** to accomplish it. A Specialist Agent might use an LLM for its task (e.g., the `CopywriterAgent` uses an LLM to write text), but its scope is narrow.
    - **Example:** The `SEOAuditAgent` receives a URL from the `WebsiteDeptAgent`. It uses a `LighthouseTool` and a `CrawlTool` to perform an audit and returns a structured report.

4.  **Tools (The Utilities):**
    - **Purpose:** The lowest level of the hierarchy. These are deterministic Python functions that interact with the outside world.
    - **Function:** They perform a single, reliable action, like making a database call, sending an email, or calling a third-party API. They do not contain any LLM logic.
    - **Example:** `create_invoice_in_supabase(customer_id, amount)`.

---

## 3. Advanced Concepts: Handling Complex Workflows

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

## 4. Example Workflow: "Launch a new product: the 'Auto-Widget'"

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

## 5. Resilience & Safeguards

To build a production-grade system, the architecture must be resilient to failures and unexpected behavior. The following patterns will be implemented to ensure robustness.

### Error Handling & Recovery

-   **Tool-Level Retries:** All external tool calls (e.g., API requests, database operations) will be wrapped in a "circuit breaker" and retry mechanism (e.g., 3 attempts with exponential backoff). If a tool fails permanently, it will raise a structured exception.
-   **Agent-Level Exception Handling:** When an agent's sub-task fails, the managing agent (e.g., a `Department Head`) will "catch" the exception. Its internal logic will then decide on a course of action, which could be:
    1.  Retrying the sub-task.
    2.  Delegating to a different, remedial tool or agent.
    3.  Pausing the entire workflow and escalating to a human for intervention.

### State Persistence & Resumption

-   **Stateful Workflows:** All agent workflows are stateful. The complete state of every in-progress workflow will be persisted to the Supabase database after each step (checkpointing).
-   **Resume on Failure:** Each workflow will have a unique ID. In the event of a system crash or restart, a recovery mechanism will scan for "in-progress" workflows and resume them from their last saved state. This is critical for supporting long-running tasks.

### Infinite Loop Prevention

-   **Maximum Step Count:** Each workflow will have a configurable maximum number of steps (e.g., 50). If a workflow exceeds this limit, it will be automatically paused and flagged for human review to prevent runaway execution.
-   **Prompt-Based Safeguards:** The core prompts for manager-level agents (`Project Manager`, `Department Head`) will include explicit instructions to detect and report a lack of progress or cyclical logic, rather than retrying a failed approach indefinitely.

### Human-in-the-Loop (HITL) Integration

-   **"Paused" State:** The agent state machine will include a dedicated `paused_for_human_input` status.
-   **HITL Workflow:**
    1.  When a workflow reaches a predefined HITL gate (e.g., budget approval), the agent graph transitions to the "paused" state.
    2.  A `HumanNotificationTool` is triggered to alert the user that their input is required.
    3.  The user provides input via an interface (e.g., the Streamlit app).
    4.  This interaction calls a `ProvideHumanInputTool`, which updates the agent's state with the user's decision.
    5.  The agent graph transitions out of the "paused" state and resumes the workflow with the new information.

---

## 6. Agent Evaluation & Quality Assurance

To ensure agents perform tasks to a high standard, a dual evaluation strategy will be implemented: offline evaluation for development and online evaluation as a live QA gate.

### Offline Evaluation (CI/CD for Agents)

This process prevents regressions and ensures that changes to an agent's logic or prompts improve its performance.

-   **Golden Datasets:** For key specialist agents, we will create and maintain "golden datasets" in LangSmith. These datasets will contain a representative set of inputs and the criteria for a successful output.
-   **Evaluator Agents:** We will create dedicated `EvaluatorAgent`s. These agents do not perform production tasks; they critique the output of other agents. An evaluator takes an agent's output and scores it against a rubric (e.g., tone, accuracy, format).
-   **Automated Testing:** As part of a CI/CD pipeline, any change to an agent will trigger an automated evaluation run. The modified agent will be run against its golden dataset, and its outputs will be scored by the corresponding `EvaluatorAgent`. If the quality score drops below a defined threshold, the change is automatically rejected.

### Online Evaluation (In-flight QA Gates)

This process provides real-time quality control for live, novel tasks within a production workflow.

-   **QA as a Specialist:** Quality assurance is treated as a task performed by a specialist agent (e.g., a `ReviewerAgent`, `ComplianceAgent`).
-   **Critique & Refinement Loops:** A `Department Head` agent can incorporate a QA step into its plan. For example, after a `CopywriterAgent` produces a draft, the `MarketingDeptAgent` can delegate a review of that draft to a `ReviewerAgent`.
-   **Conditional Logic:** Based on the output of the `ReviewerAgent` (e.g., a score or a list of issues), the `Department Head` can decide its next step:
    -   **If Approved:** Proceed with the workflow.
    -   **If Rejected:** Send the work back to the original specialist agent along with the reviewer's feedback for another attempt. This creates a powerful "critique and refinement" loop that iteratively improves the quality of the final output.
