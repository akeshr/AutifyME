# AutifyME 2-Level Architecture: Strategic Design Document

**Status:** ⚠️ LIFE-CRITICAL IMPLEMENTATION  
**Date:** October 22, 2025  
**Purpose:** Complete architectural context for Claude Code implementation  
**Scope:** Full Business OS (14+ workflows), starting with Cataloging MVP

---

## I. EXECUTIVE STRATEGIC VISION

### System Identity
AutifyME is an **Agentic Business Operating System**, not a single-purpose tool. This architecture must support:
- Marketing (campaigns, content, social, SEO)
- CRM (customer lifecycle, segmentation)  
- Operations (inventory, suppliers, billing, shipping)
- Website (CMS, deployment, domains)
- HR (payroll, recruitment, compliance)
- Finance, Analytics, Support, Product Development
- **14+ domains, 20+ specialists total**

### Critical Reality
**User requests invoke 3-5 specialists maximum, never all 20 simultaneously.**  
This selective invocation pattern fundamentally shapes architectural decisions.

---

## II. ARCHITECTURAL TRANSFORMATION RATIONALE

### Current State (3-Level Hierarchy)
```
User Request
    ↓
PM (Project Manager) - Pure orchestrator, no tools
    ↓
Department (e.g., Cataloging) - Domain coordinator, some tools
    ↓
Specialists (e.g., image_analysis) - Context-light transformers
    ↓
Tools - Actual work execution
```

**Problems Identified:**
1. **Context Degradation:** "Telephone game" effect—each layer paraphrases/translates, losing nuance
2. **Capability Blindness:** PM cannot see specialist capabilities directly, only department abstractions
3. **Planning Handicap:** PM cannot create intelligent multi-specialist plans when capabilities are hidden
4. **Architectural Overhead:** Department layer adds coordination cost without proportional value
5. **Debugging Complexity:** Three layers to trace through for issue resolution

### Target State (2-Level Hierarchy)
```
User Request
    ↓
PM (Intelligent Orchestrator) - Planning + coordination, minimal tools
    ↓ ↓ ↓ (parallel/sequential based on plan)
Specialist A   Specialist B   Specialist C
    ↓              ↓              ↓
Tools          Tools          Tools
```

**Benefits Achieved:**
1. **Direct Capability Awareness:** PM sees all specialist capabilities, descriptions, tool sets
2. **Context Preservation:** Single delegation hop, no translation layers
3. **Intelligent Planning:** PM uses DeepAgents pattern for parallel/sequential orchestration
4. **Tool-Heavy Architecture:** Most work happens in tools (deterministic), specialists only for synthesis/reasoning
5. **Simplified Debugging:** Two-layer trace path
6. **Natural Scalability:** Selective invocation means 20+ specialists doesn't overwhelm PM

---

## III. FOUNDATIONAL DESIGN PRINCIPLES

### Principle 1: Agent vs Tool Decision Framework

**AGENTS (Rare):**
- Synthesis across multiple inputs
- Reasoning with uncertainty
- Planning multi-step processes
- Natural language interpretation
- **Example:** Cataloging specialist synthesizes image analysis + taxonomy into product description

**TOOLS (Common):**
- API calls (vision, classification, search)
- Database operations (read/write)
- File I/O
- Deterministic transformations
- **Example:** save_product tool writes to database after human approval

**Decision Rule:** If operation is deterministic or pure I/O → Tool. If requires LLM reasoning → Agent.

### Principle 2: PM's Strategic Role

**PM is NOT:**
- A domain expert
- A direct executor of business logic
- A repository for domain-specific tools

**PM IS:**
- **Intelligence orchestrator** with full capability map
- **Planning engine** using DeepAgents for complex workflows
- **Context preservationist** maintaining user intent across delegations
- **Execution coordinator** managing parallel vs sequential task flows

**PM Tools (Minimal):**
- `write_todos` - Create structured plans
- `task_complete` - Signal workflow completion
- `communicate` - Direct user communication
- **NO domain-specific tools** (image analysis, database writes, etc.)

### Principle 3: Specialist Design Pattern

**Each Specialist:**
- **Focused domain:** Single responsibility (cataloging, SEO, copywriting)
- **Tool set:** 3-7 tools maximum (prevents decision fatigue)
- **Clear description:** PM-facing explanation of capabilities + when to use
- **Structured output:** Pydantic models for type safety
- **Stateless:** Each invocation is independent, context comes from PM

**Specialist Structure:**
```
Name: cataloging_specialist
Description: "Creates product catalog entries from images and data. 
             Use when: user provides product image/info needing structured catalog entry.
             Capabilities: Image analysis, taxonomy classification, description generation, 
             price validation, HITL approval workflow."
Tools: [image_analysis_tool, taxonomy_tool, save_product_tool, validate_price_tool]
Output: CatalogingResult (structured)
```

### Principle 4: Tool Design Pattern

**Every Tool:**
- **Single responsibility:** One operation, well-defined
- **Clear interface:** Pydantic input models, type-safe
- **Comprehensive docs:** Describes what it does, when it fails, what it returns
- **Error handling:** Raises descriptive exceptions, never silent failures
- **HITL integration:** Tools requiring human approval implement interrupt pattern

**Tool Structure:**
```
Name: save_product_tool
Purpose: Persist product to database after human approval
Input: ProductData (name, category, price, description, image_url, company_id)
Output: ProductID or HumanInterrupt
Errors: ValidationError, DatabaseError
HITL: Yes - shows product preview, awaits approval/rejection
```

### Principle 5: Intelligent Planning & Execution

**DeepAgents Pattern:**
- PM receives complex request
- Analyzes available specialists
- Creates execution plan: `[step1, step2, step3...]`
- Determines dependencies: which steps are parallel, which sequential
- Executes plan using `write_todos`
- Monitors progress, adapts if specialists fail

**Execution Modes:**

**Parallel (Independent Steps):**
```
User: "Analyze this product image and find 3 competitor products"

PM Plan:
- Step 1: cataloging_specialist analyzes image (extract attributes)
- Step 2: competitor_research_specialist searches market (run parallel to step 1)
- Step 3: comparison_specialist synthesizes findings (sequential, needs 1+2)
```

**Sequential (Dependent Steps):**
```
User: "Create catalog entry, then generate SEO description"

PM Plan:
- Step 1: cataloging_specialist creates entry (needs approval)
- Step 2: seo_specialist optimizes description (needs completed catalog entry from step 1)
```

**Adaptive (Dynamic Planning):**
```
User: "Launch marketing campaign for new product"

PM analyzes:
- Product exists? → Use existing catalog data
- Product missing? → Invoke cataloging first, then marketing
- Budget approved? → Proceed to ad creation
- Budget pending? → Pause at finance_approval_specialist

PM adapts plan based on intermediate results.
```

---

## IV. COMPONENT SPECIFICATIONS

### 4.1 Project Manager (PM) Agent

**Identity:** System-wide orchestrator with complete capability awareness

**Responsibilities:**
1. Interpret user intent from natural language
2. Map intent to specialist capabilities
3. Create execution plans (parallel/sequential)
4. Delegate to specialists with full context
5. Monitor progress, handle failures
6. Communicate results to user

**Knowledge Requirements:**
- All specialist descriptions (capabilities, tools, when to use)
- All tool descriptions (for understanding specialist capabilities)
- Workflow patterns (common request → specialist mappings)
- Failure recovery strategies

**Decision Framework:**
- Simple request (1 specialist) → Direct delegation
- Complex request (multiple specialists) → Use `write_todos` for planning
- Ambiguous request → Clarify with user before delegation
- Failed specialist → Retry with different approach or inform user

**Context Management:**
- Preserve original user request through all delegations
- Include relevant prior outcomes when delegating
- Never paraphrase specialist responses, forward verbatim when reporting to user

**Anti-Patterns:**
- ❌ Executing domain logic (leave to specialists)
- ❌ Calling domain tools directly (only coordination tools)
- ❌ Making assumptions about specialist outputs (trust structured responses)
- ❌ Hiding specialist failures (transparent error reporting)

### 4.2 Specialist Agents (Template)

**Generic Pattern for All Specialists:**

**Structure:**
- Name: `{domain}_specialist`
- Description: PM-facing capability summary
- Tools: 3-7 domain-specific tools
- Output: Structured Pydantic model
- Prompt: Execution instructions

**Prompt Template:**
```
You are the {Domain} Specialist for AutifyME Business OS.

ROLE: Execute {specific task} using provided tools.

CAPABILITIES:
- Capability 1 (via tool_a)
- Capability 2 (via tool_b)
- Capability 3 (via tool_c)

EXECUTION PATTERN:
1. Analyze input from PM
2. Determine required tools
3. Execute tool sequence
4. Synthesize results
5. Return structured output

CONSTRAINTS:
- Stay within domain boundaries
- Use only assigned tools
- Return typed responses (never plain text)
- Handle tool errors gracefully
- Never make assumptions beyond input data

OUTPUT FORMAT: {OutputModel}
```

**Example: Cataloging Specialist**
```
Name: cataloging_specialist
Description: "Creates structured product catalog entries. Use when user provides 
             product images/data needing: image analysis, category classification, 
             description generation, pricing validation, database persistence."
             
Tools:
- image_analysis_tool: Extracts attributes from product images
- taxonomy_tool: Classifies products into category hierarchy  
- validate_price_tool: Checks price reasonableness for category
- save_product_tool: Persists to database with HITL approval

Output: CatalogingResult {
  product_id: str
  product_name: str
  category: str
  price: Decimal
  description: str
  attributes: Dict[str, Any]
  status: "approved" | "rejected"
}
```

**Example: SEO Specialist**
```
Name: seo_specialist  
Description: "Optimizes content for search engines. Use when user needs: 
             keyword research, meta description generation, title optimization, 
             content scoring."
             
Tools:
- keyword_research_tool: Finds relevant search terms
- meta_generator_tool: Creates SEO-optimized metadata
- content_analyzer_tool: Scores content for SEO quality
- competitor_analysis_tool: Analyzes ranking competitors

Output: SEOResult {
  keywords: List[str]
  meta_title: str
  meta_description: str
  seo_score: int
  recommendations: List[str]
}
```

### 4.3 Tool Specifications (Template)

**Generic Tool Pattern:**

```
Name: {action}_{domain}_tool
Purpose: One-sentence description of what it does
Category: [API_CALL | DATABASE | FILE_IO | INTEGRATION | HITL]

Input Schema:
- param1: Type (description, constraints)
- param2: Type (description, constraints)

Output Schema:
- field1: Type (description)
- field2: Type (description)

Error Conditions:
- ErrorType1: When it occurs, how to handle
- ErrorType2: When it occurs, how to handle

HITL Pattern: [Yes/No]
If Yes:
  - Interrupt trigger: When approval needed
  - Display format: What user sees
  - Approval options: approve/reject/modify
  - Rejection flow: What happens on reject
```

**Example: Image Analysis Tool**
```
Name: image_analysis_tool
Purpose: Extract product attributes from uploaded image using Vision API
Category: API_CALL

Input Schema:
- image_url: str (public HTTPS URL or base64 data URI)
- analysis_type: Literal["product_attributes", "quality_check", "category_hint"]

Output Schema:
- attributes: Dict[str, str] (color, material, style, condition)
- confidence: float (0.0-1.0)
- category_suggestions: List[str]
- quality_score: int (1-10)

Error Conditions:
- InvalidImageError: Image URL inaccessible or corrupt
- VisionAPIError: External API failure (retry with exponential backoff)
- LowConfidenceError: Analysis confidence < threshold (prompt for manual input)

HITL Pattern: No (automated analysis)
```

**Example: Save Product Tool (HITL)**
```
Name: save_product_tool
Purpose: Persist product catalog entry after human approval
Category: HITL + DATABASE

Input Schema:
- product_data: ProductData {
    name: str
    category: str  
    price: Decimal
    description: str
    attributes: Dict
    image_url: str
    company_id: int
  }

Output Schema:
- product_id: int (if approved)
- status: Literal["approved", "rejected", "modified"]
- rejection_reason: Optional[str]

Error Conditions:
- ValidationError: Product data fails business rules
- DatabaseError: Persistence failure (rollback transaction)
- DuplicateError: Product already exists (merge conflict)

HITL Pattern: Yes
  Interrupt Trigger: Before database write
  Display Format: Product card with image, name, price, category, description
  Approval Options: 
    - "approve" → Persist to database
    - "reject" → Abort workflow, log reason
    - "modify: {field}={value}" → Update field, re-display
  Rejection Flow: Return error status to specialist, specialist reports to PM
```

---

## V. WORKFLOW ORCHESTRATION ARCHITECTURE

### 5.1 Request Flow Pattern

**Simple Request (Single Specialist):**
```
1. User: "Analyze this product image" [uploads image]
2. PM:
   - Recognizes: cataloging domain
   - Delegates: cataloging_specialist(image_url, context="user uploaded product image")
3. Cataloging Specialist:
   - Calls: image_analysis_tool(image_url)
   - Calls: taxonomy_tool(attributes)
   - Calls: save_product_tool(product_data) → HITL interrupt
4. Human: "approve"
5. Tool: Persists to database, returns product_id
6. Specialist: Returns CatalogingResult to PM
7. PM: Communicates success to user
```

**Complex Request (Multiple Specialists, Parallel):**
```
1. User: "Analyze product and find 3 competitors"
2. PM:
   - Recognizes: cataloging + competitor_research
   - Creates plan via write_todos:
     ["cataloging_specialist: analyze product image",
      "competitor_research_specialist: find 3 similar products in market",
      "comparison_specialist: create feature comparison (needs results from steps 1+2)"]
3. Execution:
   - Step 1 & 2 run in parallel (independent)
   - Step 3 waits for 1 & 2 completion (sequential)
4. PM: Synthesizes final comparison report for user
```

**Complex Request (Multiple Specialists, Sequential):**
```
1. User: "Catalog this product, then create Facebook ad campaign"
2. PM:
   - Recognizes: cataloging → marketing (dependent)
   - Creates plan:
     ["cataloging_specialist: create catalog entry (with approval)",
      "marketing_specialist: create Facebook ad using catalog data from step 1"]
3. Execution:
   - Step 1 runs, hits HITL interrupt
   - Human approves
   - Step 1 completes with product_id
   - Step 2 starts, receives product_id as context
   - Step 2 creates ad campaign
4. PM: Reports campaign details to user
```

### 5.2 Error Handling Strategy

**Tool-Level Errors:**
- Tool fails → Raises exception to specialist
- Specialist catches → Logs error, returns error status to PM
- PM decides: retry with different tool, use fallback specialist, or inform user

**Specialist-Level Errors:**
- Specialist cannot complete task → Returns error status to PM
- PM analyzes: Is this recoverable? Try different specialist? Request more info from user?
- PM communicates issue transparently to user

**PM-Level Errors:**
- Cannot map request to specialists → Ask user for clarification
- Planning fails → Simplify request or break into smaller tasks
- Catastrophic failure → Graceful degradation, preserve state, inform user

**HITL Rejection:**
- User rejects → Tool returns rejection status
- Specialist receives rejection → Reports to PM
- PM options: Retry with modifications, cancel workflow, request user guidance

### 5.3 State Management

**Checkpoint Pattern:**
- Each agent invocation creates checkpoint
- HITL interrupts pause workflow, save state
- User response resumes from checkpoint
- State includes: full message history, pending tool calls, context

**Context Preservation:**
- PM maintains original user request throughout workflow
- Each specialist receives relevant context from PM
- Specialist outputs flow back to PM unchanged (no paraphrasing)
- Final user communication includes synthesized results

**Stateless Specialists:**
- No memory between invocations
- Each call is fresh context from PM
- Enables parallel execution without race conditions
- Simplifies debugging (no hidden state)

---

## VI. MIGRATION STRATEGY

### Phase 1: Pattern Documentation (Complete)
- ✅ This document (architectural context)
- Create: Prompt engineering guide
- Create: Tool design standards  
- Create: Specialist template library
- Create: Testing framework specification

### Phase 2: Core Transformation
**2.1 PM Redesign:**
- Remove department delegation logic
- Add specialist capability registry
- Implement direct delegation pattern
- Integrate DeepAgents planning

**2.2 Flatten Cataloging:**
- Convert image_analysis_specialist → image_analysis_tool
- Elevate cataloging_specialist to PM level
- Refactor tools for specialist access
- Update prompt for autonomous execution

**2.3 Tool Migration:**
- Audit all existing tools
- Separate agent logic → deterministic tools
- Implement HITL pattern consistently
- Add comprehensive error handling

**2.4 Testing Infrastructure:**
- Unit tests for each tool
- Integration tests for specialist workflows
- E2E tests for PM orchestration
- HITL flow validation

### Phase 3: Expansion Blueprint
**When adding new domains (Marketing, Operations, etc.):**

1. **Define Specialist:**
   - Name, description, capabilities
   - Tool requirements (3-7 max)
   - Output model
   - Example workflows

2. **Implement Tools:**
   - Follow tool pattern template
   - Add HITL where needed
   - Comprehensive error handling
   - Unit test coverage

3. **Register with PM:**
   - Add to capability registry
   - Update PM prompt with specialist description
   - Add example workflows for common requests

4. **Validate:**
   - Test specialist in isolation
   - Test PM delegation to specialist
   - Test parallel execution with other specialists
   - Test error/failure scenarios

---

## VII. SUCCESS CRITERIA

### Architectural Validation
- ✅ PM can list all specialist capabilities
- ✅ PM creates intelligent multi-step plans
- ✅ Context preserved across delegations (no information loss)
- ✅ Parallel execution works for independent tasks
- ✅ Sequential execution works for dependent tasks
- ✅ HITL interrupts/resumes work correctly
- ✅ Error handling graceful at all levels

### Performance Metrics
- Token efficiency: < 50% increase vs 3-level (expect decrease)
- Latency: Comparable or better (fewer hops)
- Success rate: ≥ 90% for cataloging workflows
- HITL approval rate: Track human satisfaction
- Error recovery: < 5% catastrophic failures

### Developer Experience
- New specialist addition: < 1 day
- Tool creation: < 2 hours
- Debugging time: 50% reduction (fewer layers)
- Test coverage: > 80%

### User Experience
- Request understanding: ≥ 95% accuracy
- Task completion: ≥ 90% first-attempt success
- Transparency: User sees progress, understands failures
- HITL flow: Intuitive approval process

---

## VIII. ANTI-PATTERNS & GUARDRAILS

### What NOT to Do

**❌ PM Domain Expertise:**
- PM should never have cataloging-specific logic
- PM should never call image_analysis_tool directly
- PM delegates, doesn't execute domain work

**❌ Specialist Overreach:**
- Specialists don't coordinate with each other directly
- Specialists don't call PM tools (write_todos, etc.)
- Specialists stay within domain boundaries

**❌ Tool Complexity:**
- Tools don't contain LLM reasoning
- Tools don't make multi-step decisions
- Tools do one thing, well-defined

**❌ Context Leakage:**
- Don't paraphrase specialist outputs
- Don't lose user's original request
- Don't assume context from previous conversations (stateless)

**❌ Silent Failures:**
- Every error must surface to appropriate level
- No swallowed exceptions
- No "try and hope" patterns

### Guardrails

**Tool Count per Specialist:** 3-7 maximum
- Below 3: Too narrow, might need consolidation
- Above 7: Decision fatigue, split into multiple specialists

**Specialist Count Total:** 20-30 maximum
- Beyond this, PM capability awareness degrades
- Consider sub-domains or capability clustering

**Planning Depth:** 2-3 levels maximum
- User request → PM plan → Specialist execution
- Avoid planning within plans (complexity explosion)

**Context Window:** Monitor total tokens
- PM + Specialist prompts + Tools < 50K tokens total
- Prune old conversation history aggressively

---

## IX. IMPLEMENTATION CONTEXT FOR CLAUDE CODE

### What You're Implementing

**Not a simple refactor** - This is architectural transformation:
- Removing entire layer (departments)
- Redistributing responsibilities
- Changing delegation patterns
- Rewriting agent prompts
- Converting agents to tools
- Implementing planning system

### Where to Focus

**Critical Path:**
1. PM redesign (capability awareness + planning)
2. Cataloging specialist flattening (MVP domain)
3. Tool extraction (image_analysis agent → tool)
4. HITL validation (ensure interrupts work)
5. Testing (prove nothing broke)

**Secondary Path:**
6. Documentation (prompts, tools, specialists)
7. Monitoring (logs, metrics, debugging)
8. Expansion blueprint (next domains)

### What to Preserve

**Don't Break:**
- HITL interrupt/resume pattern (critical for approvals)
- Checkpoint system (state management)
- Storage layer (database, file system)
- Channel system (user communication)
- Authentication/authorization

**Carefully Migrate:**
- Existing tools (audit, don't blindly move)
- Test suites (update assertions, not delete)
- Configuration (environment, secrets)

### Validation Checkpoints

**After PM Redesign:**
- Can PM list all specialists?
- Can PM create multi-step plan using write_todos?
- Does PM delegate correctly to cataloging_specialist?

**After Cataloging Flatten:**
- Does cataloging workflow complete end-to-end?
- Does HITL interrupt trigger correctly?
- Does user approval resume workflow?
- Is product saved to database?

**After Tool Migration:**
- Do all tools have proper error handling?
- Are all tools documented?
- Do tools return structured outputs?

**Before Production:**
- All tests passing (unit, integration, E2E)
- Performance acceptable (latency, tokens)
- Error handling verified (simulate failures)
- HITL flows validated (real user testing)

---

## X. PHILOSOPHICAL FOUNDATION

### Why This Architecture Matters

**Intelligence at the Right Layer:**
- PM: Strategic intelligence (what to do, when)
- Specialists: Tactical intelligence (how to do it)
- Tools: Zero intelligence (just do it)

**Transparency:**
- User sees capabilities clearly
- Developer understands flow easily
- Debugging follows logical path

**Scalability:**
- Adding specialists: Update registry, implement tools, test
- Adding tools: Implement, assign to specialist, document
- Adding workflows: Compose existing specialists

**Adaptability:**
- New domains: Follow specialist template
- New tools: Follow tool pattern
- New requirements: Extend, don't rewrite

### The Agentic Vision

AutifyME isn't software—it's **intelligent business infrastructure**:
- Understands natural language intent
- Plans multi-step workflows autonomously  
- Executes with human oversight (HITL)
- Adapts to context dynamically
- Scales across business domains

This 2-level architecture makes that vision achievable by balancing:
- **Autonomy** (agents plan and execute)
- **Control** (humans approve critical actions)
- **Intelligence** (LLMs where reasoning needed)
- **Efficiency** (tools where determinism works)

**This is life-critical because**: AutifyME's success depends on being genuinely intelligent, not just a fancy API wrapper. Users must feel they have a **business partner**, not a tool. That requires architectural precision.

---

**END OF STRATEGIC ARCHITECTURE DOCUMENT**

Claude Code: Use this as your north star. Every implementation decision should trace back to these principles. When uncertain, refer to the anti-patterns and guardrails. When planning changes, validate against success criteria.

This is the blueprint. Make it real.
