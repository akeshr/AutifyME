# AutifyME Agentic System Design

**Created:** September 29, 2025
**Purpose:** Canonical agent hierarchy and context engineering patterns

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

- **Hierarchy & Delegation:** Instead of a single monolithic agent, the system is a hierarchy of specialized agents. Higher-level agents delegate tasks to lower-level agents, providing clear separation of concerns.
- **Separation of Concerns:** Each agent has a single, well-defined responsibility. This makes them easier to build, test, debug, and reuse.
- **Managed Context:** By breaking down problems and delegating, we ensure that each agent only receives the context necessary for its specific task. This avoids overwhelming agents with unnecessary information, leading to better performance and reliability.
- **Stateful & Event-Driven:** Agents operate within state machines (graphs) and react to changes in state, allowing for complex, long-running, and interruptible (e.g., for HITL) workflows.

---

## 3. Proposed Architecture: The 2-Level Model

We model our system after a streamlined organizational structure. A central **Project Manager** acts as the orchestrator, delegating tasks directly to **Specialist** agents who use **Tools** to accomplish their work.

### The Agent Hierarchy

```
[User Request]
      │
      ▼
┌─────────────────────────┐
│ Project Manager Agent   │ (Planner & Orchestrator)
└─────────────────────────┘
      │
      ├─► [Cataloging Specialist] ─► [image_analysis_tool, save_product]
      ├─► [Customer Service Specialist] ─► [get_order_status, send_message]
      └─► [Inventory Specialist] ─► [check_stock, update_inventory]

```

**Key Simplification:** We've eliminated the Department layer for direct delegation and clearer responsibility chains.

### Component Responsibilities

1.  **Project Manager Agent (The Orchestrator):**
    - **Purpose:** The single entry point for all user requests. Its job is to understand goals, classify intent, and delegate to the appropriate specialist.
    - **Function:** It analyzes the user's request and routes it to the specialist best suited for the task. It manages the state of the overall interaction and coordinates multi-specialist workflows when needed.
    - **Implementation:** A DeepAgent (LangGraph) that creates subagents for specialists. It orchestrates the flow between specialists when a workflow requires multiple steps.

2.  **Specialist Agents (The Experts):**
    - **Purpose:** To handle a specific business domain (e.g., Cataloging, Customer Service, Inventory Management).
    - **Function:** Receives a focused task from the Project Manager, uses domain-specific tools to accomplish it, and returns structured results.
    - **Example:** The `CatalogingSpecialist` receives a product cataloging request, uses `image_analysis_tool` to analyze product images, synthesizes a Product model, and calls `save_product` to persist it (with HITL approval).

3.  **Tools (The Utilities):**
    - **Purpose:** The lowest level of the hierarchy. These are deterministic Python functions that interact with the outside world.
    - **Function:** They perform a single, reliable action, like making a database call, calling a Vision API, or sending a message. They do not contain any LLM logic.
    - **Example:** `image_analysis_tool(image_path)` → `ImageAnalysisResult`, `save_product(name, price, ...)` → `CatalogingResult`.

### Agent Implementation Strategy: 2-Level DeepAgents

**Architectural Decision:** PM delegates directly to specialists via DeepAgents SubAgents pattern.

**Implementation Layers:**

1.  **Project Manager (DeepAgents):**
    - **Framework:** `deepagents.create_deep_agent`
    - **Tools:** None (specialists have the tools)
    - **Subagents:** Specialists as SubAgents
    - **Features:** Intent classification, specialist delegation, workflow coordination
    - **Delegation:** Via automatic subagent invocation

2.  **Specialists (DeepAgents SubAgents):**
    - **Framework:** `deepagents.create_agent` (creates agent for SubAgent attachment)
    - **Tools:** Domain-specific utilities (e.g., `image_analysis_tool`, `save_product`, `check_inventory`)
    - **Tool Configs:** HITL configuration via `tool_configs` parameter
    - **Features:** Tool usage, structured outputs, domain expertise
    - **Pattern:** Specialist agent created with `create_agent()`, then attached to PM as SubAgent

3.  **Tools (Pure Python Functions):**
    - **Framework:** `@tool` decorator
    - **Examples:** `save_product`, `image_analysis_tool`, `download_media`
    - **Features:** Type-safe args (Pydantic), retry logic, error handling

### PM → Specialist Delegation Pattern

Specialists exposed as **SubAgents** under PM:

```python
# Create specialist agent with tools
def create_cataloging_specialist(storage: StorageInterface) -> Any:
    specialist = create_agent(
        model=get_llm(model="gpt-4.1-mini", temperature=0),
        system_prompt=load_prompt("specialists/cataloging_specialist.prompt"),
        tools=[
            image_analysis_tool,
            create_save_product_tool(storage),
        ],
        tool_configs={
            "save_product": ToolConfig(
                allow_accept=True,
                allow_edit=True,
                allow_respond=True,
                description="Review product before saving"
            )
        },
        response_format=Product,  # Optional structured output
    )
    return specialist

# PM delegates to specialists via SubAgents
project_manager = create_deep_agent(
    tools=[],  # PM has no tools
    system_prompt=load_prompt("project_manager.prompt"),
    subagents=[
        create_cataloging_specialist(storage),
        # Future specialists...
    ],
    model=llm,
    checkpointer=checkpointer,
    store=store,
    use_longterm_memory=True,
    context_schema=CompanyContext,
)
```

**Benefits:**
- Direct delegation (no intermediate Department layer)
- Clean separation: PM orchestrates, specialists execute
- Type-safe communication via structured outputs
- Unified observability via LangSmith tracing
- HITL configured at specialist tool level

---

## 4. Advanced Concepts: Handling Complex Workflows

This architecture is designed to handle complex, real-world business processes that may require coordination of multiple specialists.

### Multi-Specialist Orchestration

For user requests that require multiple specialists (e.g., "Launch a new product campaign"), the **Project Manager Agent** takes charge:

1.  **Decomposition:** It breaks the high-level goal into a series of smaller, actionable tasks.
2.  **Dependency Mapping:** It identifies which specialists are needed and in what order.
3.  **Sequential/Parallel Execution:** It orchestrates execution, delegating to specialists sequentially when dependencies exist, or in parallel when tasks are independent.
4.  **State Management:** It tracks overall workflow state and coordinates handoffs between specialists.

**Example Flow:**
```
User: "Launch our new product"
PM: Analyzes request → needs cataloging + marketing
  1. Delegate to CatalogingSpecialist (catalog product details)
  2. Wait for completion
  3. Delegate to MarketingSpecialist (create campaign with product data)
  4. Return combined results to user
```

### Parallel Task Execution

DeepAgents and LangGraph natively support parallel execution when tasks don't depend on each other:

-   **Future Enhancement:** When PM determines tasks can run in parallel (e.g., catalog product + check inventory), it can initiate both specialists simultaneously, reducing total workflow time.

### Cross-Specialist Data Sharing

Specialists communicate via the PM's orchestration:

1.  **Data Request:** A specialist completes its task and returns structured data.
2.  **PM Coordination:** PM receives the result and determines next step.
3.  **Context Passing:** PM delegates to the next specialist, passing relevant data from previous specialist.
4.  **Isolation:** Each specialist only receives the specific inputs it needs, not the entire workflow history.

This ensures clean data dependencies and prevents context pollution.

---

## 5. Example Workflow: "Catalog a new product"

1.  **User Request (WhatsApp):** User sends message "Catalog this jar, Rs 500" with image attachment.
2.  **Runner Processing:**
    - Downloads image to local filesystem
    - Builds semantic message description
    - Invokes PM with structured payload
3.  **Project Manager** receives request:
    - Classifies intent: cataloging request
    - Identifies needed specialist: `cataloging_specialist`
    - Delegates to specialist with full context
4.  **Cataloging Specialist** executes:
    - Calls `image_analysis_tool(image_path)` → `ImageAnalysisResult`
    - Synthesizes Product model from user text + image insights
    - Calls `save_product(name, price, ...)` → **HITL interrupt**
5.  **HITL Flow:**
    - Framework triggers interrupt (via `tool_configs`)
    - Runner detects interrupt, extracts draft product
    - Sends approval request to user via WhatsApp
    - User reviews and approves/edits/rejects
    - Runner resumes workflow with Command
6.  **save_product Tool** executes:
    - Persists product to Supabase
    - Returns `CatalogingResult`
7.  **Specialist** completes:
    - Returns success message to PM
8.  **PM** relays result:
    - Sends confirmation to user
    - Workflow complete

---

## 6. Resilience & Safeguards

To build a production-grade system, the architecture must be resilient to failures and unexpected behavior.

### Error Handling & Recovery

We leverage **DeepAgents/LangChain error handling** for consistent, production-grade error management:

-   **Critical Operations:** For database writes or irreversible actions, tools raise `ToolException` to provide structured feedback.
-   **Self-Healing Operations:** Agents can retry transient failures automatically via tool retry decorators.
-   **Centralized Classification:** All external API errors flow through `classify_api_error()` for consistent retry vs fail-fast decisions.

```python
from autifyme_agents.core.exceptions import classify_api_error, ExternalAPIError

@tool
@retry(stop=stop_after_attempt(3), retry=retry_if_exception_type(ExternalAPIError))
def save_product(**kwargs) -> CatalogingResult:
    try:
        product = Product(**kwargs)
        return storage.save_product(product)
    except Exception as e:
        # Centralized error classification
        raise classify_api_error(e, "save_product", "Supabase", StorageError)
```

### State Persistence & Resumption

-   **Stateful Workflows:** All agent workflows are stateful. Complete state of every in-progress workflow is persisted to PostgreSQL (LangGraph checkpoints).
-   **Resume on Failure:** Each workflow has a unique thread_id. In the event of system crash or restart, workflows can resume from their last checkpoint.
-   **HITL State:** Interrupt state managed entirely by LangGraph checkpoints - no custom database tables needed.

### Infinite Loop Prevention

-   **Maximum Step Count:** Each workflow has a configurable recursion_limit (passed to LangGraph). If exceeded, workflow pauses and flags for review.
-   **Prompt-Based Safeguards:** PM and specialist prompts include explicit instructions to detect lack of progress and report blockers rather than retrying failed approaches.

### Human-in-the-Loop (HITL) Integration

We use **DeepAgents native `tool_configs`** for approval workflows:

```python
specialist = create_agent(
    tools=[save_product],
    tool_configs={
        "save_product": ToolConfig(
            allow_accept=True,    # User can approve as-is
            allow_edit=True,      # User can modify before saving
            allow_respond=True,   # User can reject with feedback
            description="Review product before saving"
        )
    }
)
```

-   **Workflow:** Specialist calls tool with tool_config → framework triggers interrupt → runner detects interrupt → sends approval request → user responds → runner resumes with Command
-   **Benefits:** Built-in state management, automatic checkpointing, type-safe resume commands, no custom "paused" state needed

---

## 7. Agent Evaluation & Quality Assurance

To ensure agents perform tasks to a high standard, a **dual evaluation strategy** is implemented: **offline evaluation** for retrospective analysis and **online evaluation** for real-time quality gates.

**Critical Distinction:** These are complementary approaches. LangSmith handles offline evaluation, but does NOT replace the need for in-workflow Reviewer specialists (future enhancement).

### Offline Evaluation (LangSmith - Retrospective)

**Purpose:** Prevent regressions, compare versions, monitor quality trends over time.

**When:** CI/CD pipelines, nightly runs, A/B testing, historical analysis.

**How:**
-   **Golden Datasets:** Create and maintain datasets in LangSmith containing representative inputs and expected outputs for key workflows.
-   **Custom Evaluators:** Define custom evaluator functions (Python code) that score agent outputs against business criteria.
-   **Automated Testing:** Changes to agents trigger evaluation runs in CI/CD. Modified agent runs against golden dataset, outputs scored, change rejected if quality drops below threshold.

### Online Evaluation (Reviewer Specialists - Future)

**Purpose:** Ensure quality in real-time, before expensive operations or irreversible actions.

**When:** During production workflows, before publishing, before database writes.

**How:**
-   **Reviewer as a Specialist:** Quality assurance handled by specialist agents (e.g., `ReviewerAgent`, `ComplianceAgent`) that run as part of the workflow.
-   **Critique & Refinement Loops:** PM incorporates review step into plan. After specialist produces output, reviewer critiques it in real-time.
-   **Conditional Logic:** Based on reviewer output, PM decides: proceed, refine with feedback, or escalate to human.

**Note:** Reviewer specialists are a future enhancement. Current implementation relies on HITL approval for quality gates.

---

## 8. Context Engineering Strategy

To ensure our system is efficient, cost-effective, and avoids performance degradation from "context rot," we adhere to the principles of **Effective Context Engineering**.

**Guiding Principle:** Find the smallest possible set of high-signal tokens that maximize the likelihood of the desired outcome.

### Our Implementation Patterns:

1.  **Minimal Context via Delegation (The "Need to Know" Basis):**
    -   **What:** The hierarchical agent design is our primary tool for context management. A `Specialist` agent receives *only* the specific inputs required for its task, not the entire PM history.
    -   **Why:** This prevents context pollution, keeps prompts clean, and allows each agent to operate in a focused environment, drastically reducing token usage and improving reliability.

2.  **Token-Efficient Tools:**
    -   **What:** Every tool must have a single, well-defined purpose and return concise, structured data (Pydantic models). We avoid generic, overlapping, or "chatty" tools.
    -   **Why:** This ensures agents can make clear decisions about which tool to use and receive predictable, token-efficient results.

3.  **Just-in-Time Context Retrieval (DeepAgents Store):**
    -   **What:** Instead of front-loading static context (like company profile) into the main prompt, we use DeepAgents `store` parameter to inject it at the moment of execution.
    -   **Why:** This keeps the primary agent's "working memory" free to focus on the dynamic task at hand, reducing token count for every LLM call.

4.  **Strategies for Long-Horizon Tasks:**
    -   **What:** For workflows that may exceed context window, we employ explicit state management:
        -   **Structured State:** LangGraph state machines track workflow progress
        -   **Checkpointing:** State persisted after each step
        -   **Compaction (Future):** Summarize conversation history, keeping key decisions and discarding intermediate tool calls
    -   **Why:** This allows agents to maintain coherence and achieve goals over extended periods without being constrained by the context window limit.

---

## 9. Prompt Management Strategy

To ensure our prompts are stable, version-controlled, and testable, while also allowing for rapid experimentation, we adopt a hybrid prompt management strategy.

**Guiding Principle:** The production application MUST NOT have a runtime dependency on an external service (like LangSmith Hub) to load its core prompts.

### Our Implementation Patterns:

1.  **Git as the Source of Truth (Production):**
    -   **What:** All production-ready prompts are stored as plain text files (e.g., `.prompt`) within the `agents/src/autifyme_agents/prompts/` directory. These are committed directly to our Git repository.
    -   **How:** The application uses `core.prompt_loader.load_prompt()` to read these files from the local filesystem at runtime.
    -   **Why:** This guarantees maximum stability and resilience. Prompts are versioned alongside the code that uses them and go through the same review and CI/CD process.

2.  **LangSmith Hub as the Experimentation Platform (Development):**
    -   **What:** The LangSmith Hub is used as a playground and versioning system for developing and improving prompts.
    -   **How:** We maintain a utility script (`scripts/sync_prompts.py`) to push local prompts to the Hub and pull updated versions back down.
    -   **Why:** This provides a powerful, collaborative environment for A/B testing, evaluating prompt performance against datasets, and iterating on prompt design.

### The Development Workflow:

1.  **Create:** A new prompt is created locally and committed to Git.
2.  **Push:** The developer pushes the prompt to LangSmith Hub using the sync script.
3.  **Experiment:** The team iterates on the prompt within the LangSmith UI, creating new versions.
4.  **Validate:** The new versions are tested against evaluation datasets in LangSmith.
5.  **Pull & Commit:** Once a superior version is identified, its content is pulled back down, overwriting the local `.prompt` file, and the change is committed to Git to be deployed to production.

---

## 10. Key Architectural Decisions

### Why 2-Level (Not 3-Level)?

**Previous Architecture:** PM → Department → Specialist → Tools

**Current Architecture:** PM → Specialist → Tools

**Rationale:**
- **Simplicity:** Department layer added complexity without clear value for single-domain workflows
- **Direct Responsibility:** Specialists directly responsible for their domain, reducing coordination overhead
- **Easier to Reason About:** Fewer layers means clearer delegation chains and simpler debugging
- **Scalability:** When multi-domain workflows are needed, PM can orchestrate multiple specialists directly
- **Performance:** One fewer delegation hop reduces latency and token usage

**Trade-offs:**
- PM must handle more orchestration logic
- Multi-specialist workflows require PM-level coordination
- Less modular for complex domain hierarchies

**When to Reconsider:** If we add multiple related specialists that need domain-level coordination (e.g., 5+ marketing specialists), we may reintroduce a Department pattern for that specific domain.

### Why SubAgents (Not Tools)?

Specialists are SubAgents, not tools, because:
- **Proper Hierarchical Delegation:** PM delegates to specialists as agents, not function calls
- **Structured Communication:** Specialists can return complex Pydantic models, not just strings
- **Observability:** LangSmith traces show clear PM → Specialist delegation, not just tool calls
- **Separation of Concerns:** PM orchestrates, specialists execute, tools are utilities

**Tools** are reserved for deterministic operations (database calls, API calls, file operations), not synthesis or decision-making.

---

## 11. Implementation Summary

**Current State (v2.0.0 - November 2025):**
- PM delegates directly to specialists via DeepAgents SubAgents
- 7 production specialists + 4 experimental specialists
- Universal Data Engine (inspect_schema, read_data, write_data)
- Intelligent PM paradigm (understands, enriches, delegates)
- Multimodal image analysis on PM level
- Base context loaded at startup (catalog summary, taxonomy tree)

**File Structure:**
```
agents/src/autifyme_agents/
├── workflows/
│   ├── project_manager.py              # PM construction (create_deep_agent)
│   ├── approval_analyzer.py            # Approval classification
│   ├── outcome_tracker.py              # Workflow outcome tracking
│   ├── channels/                       # Platform adapters (WhatsApp)
│   ├── handlers/                       # Workflow handlers
│   └── orchestration/
│       └── runner_v2.py                # Main workflow orchestration
├── specialists/
│   ├── cataloging_specialist.py        # Legacy cataloging
│   ├── product_architecture_specialist.py
│   ├── taxonomy_specialist.py
│   ├── market_intelligence_specialist.py
│   ├── visual_assets_specialist.py
│   ├── content_seo_specialist.py
│   ├── marketing_content_specialist.py
│   └── experimental/                   # Ad copy, audience, campaign, platform
├── tools/
│   ├── image_analysis_tool.py          # Vision API wrapper
│   ├── platform_tools.py               # Platform media tools
│   ├── research_tools.py               # Web research
│   └── data_engine/                    # Universal Data Engine
│       ├── inspect_schema.py           # Schema discovery
│       ├── read_data.py                # Query operations
│       ├── write_data.py               # Mutation operations
│       └── aggregate_data.py           # Aggregation queries
├── prompts/
│   ├── project_manager_intelligent.prompt
│   ├── approval_analyzer.prompt
│   └── specialists/                    # 9 specialist prompts
├── schemas/
│   ├── specialist_outputs/             # Structured output models
│   └── registry/                       # Schema metadata
└── integrations/
    └── storage/                        # Supabase adapter
```

**Specialists:**
| Specialist | Domain | Status |
|------------|--------|--------|
| Product Architecture | Family/variant structure | Production |
| Taxonomy | Category classification | Production |
| Market Intelligence | Pricing/competition analysis | Production |
| Visual Assets | Image organization/quality | Production |
| Content SEO | Product descriptions/SEO | Production |
| Marketing Content | Campaign narratives/CTAs | Production |
| Cataloging | Legacy simple cataloging | Production |

---

**Last Updated:** November 25, 2025
**Version:** 2-Level Architecture v2.0.0
