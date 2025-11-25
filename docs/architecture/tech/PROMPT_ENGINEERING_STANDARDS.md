# Prompt Engineering Standards for AutifyME Agents

**Created:** October 14, 2025
**Status:** ✅ Canonical Reference
**Purpose:** Production-grade prompt design standards for hierarchical agentic system

---

## Executive Summary

This document defines prompt engineering standards for all agents in the AutifyME system. Based on Anthropic's research, Claude best practices, and LangChain v1 patterns, these standards ensure prompts are:
- **Minimal:** Smallest set of high-signal tokens
- **Flexible:** Right altitude for each hierarchy level
- **Maintainable:** No code, no hardcoded workflows
- **Scalable:** Reusable across departments and workflows

**Critical Rule:** Prompts define **what to think**, not **what code to write**.

---

## Table of Contents

1. [Core Principles](#1-core-principles)
2. [Prompt Structure Template](#2-prompt-structure-template)
3. [Hierarchy-Specific Guidance](#3-hierarchy-specific-guidance)
4. [Examples Strategy](#4-examples-strategy)
5. [Anti-Patterns](#5-anti-patterns)
6. [Validation Checklist](#6-validation-checklist)
7. [References](#7-references)

---

## 1. Core Principles

### 1.1 The Guiding Principle

> **"Find the smallest possible set of high-signal tokens that maximize the likelihood of your desired outcome."**
> — Anthropic Engineering

Every prompt should answer:
- What is this agent's **role** in the hierarchy?
- What **decisions** must it make?
- What **outputs** are expected?
- How should it **think** about edge cases?

Avoid answering "what code should it write" or "what exact steps to execute."

---

### 1.2 The Right Altitude

**Altitude** = level of abstraction vs specificity

| Too Low | Right Altitude | Too High |
|---------|---------------|----------|
| "Call `download_whatsapp_media()` then check if result is None" | "Download media if present before delegating" | "Handle media" |
| Python code snippets | Decision principles + examples | Vague instructions |
| Step-by-step implementation | Reasoning framework | Generic platitudes |

**For AutifyME (2-Level Architecture):**
- **PM:** High altitude (multi-domain orchestration principles)
- **Specialists:** Low-medium altitude (focused domain execution with tools)

---

### 1.3 Simple, Direct Language

- Use **active voice**: "Analyze the request" not "The request should be analyzed"
- Use **imperative mood**: "Delegate to departments" not "You should delegate"
- Avoid jargon unless domain-specific
- Be concise: one idea per sentence

**Example:**
- ❌ "It is important that you should be analyzing the user's intent before you proceed with delegation"
- ✅ "Analyze user intent before delegating"

---

### 1.4 No Code in Prompts

**Why:** Code is brittle, verbose, and confuses the agent's role.

**Instead of:**
```python
if state.get("pending_interrupts"):
    intent = "resume_workflow"
else:
    intent = classify_intent(message)
```

**Write:**
```xml
<instruction>
Check if workflow is interrupted (pending approvals exist):
- If yes: Intent is resume_workflow
- If no: Classify based on message content
</instruction>
```

**Exceptions:**
- Pydantic model names (outputs): ✅ `Return ImageAnalysisResult`
- Tool names: ✅ `Use download_whatsapp_media tool`
- Data structures in examples: ✅ Showing expected JSON shape

---

## 2. Prompt Structure Template

### 2.1 Standard XML Structure

Claude is trained on XML-tagged data. Use this structure:

```xml
<background_information>
  ## Your Role
  [Who you are in the hierarchy]

  ## Company Context
  [How brand/audience context is available]

  ## Your Position in Hierarchy
  [Who delegates to you, who you delegate to]
</background_information>

<available_tools>
  ## Tools You Have
  - tool_name: Purpose and when to use
  - another_tool: Purpose and when to use

  ## Available Sub-Agents (if applicable)
  - department_name: What they handle
</available_tools>

<instructions>
  ## Core Responsibilities
  [What decisions you make, what outcomes you produce]

  ## Decision-Making Framework
  [How to think about different scenarios]

  ## Quality Standards
  [What "good" looks like for your outputs]

  ## Escalation & Errors
  [When to ask for help, how to handle failures]
</instructions>

<examples>
  ## Example 1: [Scenario Name]
  <example>
    <user_input>[Realistic input]</user_input>
    <your_reasoning>[Your thought process]</your_reasoning>
    <your_action>[What you do - tools called, delegation]</your_action>
    <expected_output>[What you return]</expected_output>
  </example>

  ## Example 2: [Different Scenario]
  [Same structure...]
</examples>

<output_format>
  ## Expected Structure
  Return: [Pydantic model name or structure]

  ## Validation
  Before returning, verify:
  - [ ] Checklist item 1
  - [ ] Checklist item 2
</output_format>
```

---

### 2.2 Section Guidelines

**`<background_information>`:**
- Establish context and role identity
- Reference company context availability (middleware-injected)
- Keep to 3-5 sentences maximum

**`<available_tools>`:**
- List tools with **purpose**, not implementation
- Group by category if >5 tools
- Include when/why to use each

**`<instructions>`:**
- Decision principles, not step-by-step code
- Use bullet lists for clarity
- Include quality standards and error handling

**`<examples>`:**
- 2-4 canonical examples covering diverse scenarios
- Show reasoning process, not just I/O
- Avoid edge cases (bloat)

**`<output_format>`:**
- Specify Pydantic models for structured outputs
- Include validation checklist
- Mention any HITL considerations

---

## 3. Hierarchy-Specific Guidance

### 3.1 Project Manager (Orchestrator)

**Altitude:** High - Cross-domain planning and coordination

**Focus:**
- Intent classification across ALL domains
- Specialist delegation (direct, no intermediate layer)
- Workflow resumption (HITL)
- Context synthesis for delegation

**Avoid:**
- Workflow-specific implementation details
- Hardcoded specialist logic
- Tool implementation instructions

**Template Sections:**
```xml
<background_information>
  You are the Project Manager for {company_name}, the central orchestrator
  for all business workflows. You delegate directly to domain specialists
  to accomplish user goals.
</background_information>

<available_tools>
  ## Specialist Delegation (SubAgents)
  - cataloging_specialist: Product catalog management
  - marketing_specialist: Campaigns and content (future)
  - operations_specialist: Billing, shipping, inventory (future)

  ## Coordination Tools
  - write_todos: Track multi-step workflows
  - download_whatsapp_media: Fetch media before delegation
</available_tools>

<instructions>
  ## Your Core Responsibilities

  1. **Analyze Intent**: Understand what the user wants to accomplish
  2. **Delegate Work**: Route to appropriate specialist with full context
  3. **Handle Interrupts**: Resume workflows when approvals return
  4. **Synthesize Results**: Relay outcomes back to users

  ## Decision Framework

  **For New Requests:**
  - Classify domain (cataloging, marketing, operations, etc.)
  - Extract relevant data from message
  - Download media if present
  - Delegate to appropriate specialist with complete context

  **For Interrupted Workflows:**
  - Identify pending approvals
  - Interpret user's response (approve/edit/reject)
  - Construct resume command with batch responses

  ## Quality Standards

  - Provide complete context to specialists (no references)
  - One approval point per delegation (avoid parallel interrupts)
  - Clear status updates to users
</instructions>

<examples>
  [Show examples across MULTIPLE domains, not just cataloging]
</examples>
```

---

### 3.2 Specialists (Domain Experts with Tools)

**Altitude:** Low-Medium - Domain execution with tools

**Focus:**
- Domain-specific workflow execution
- Tool usage (image_analysis, save_product, etc.)
- Structured outputs (Pydantic models)
- Quality validation before returning

**Avoid:**
- Cross-domain logic (PM's job)
- Hardcoded workflows (be adaptive)
- Multi-specialist coordination (no other specialists exist)

**Template Sections:**
```xml
<background_information>
  You are the [Domain] Specialist. You transform [input] into [output]
  using your available tools.

  Context available:
  - Brand Voice: {brand_voice}
  - Target Audience: {target_audience}
  - Company Profile: Injected via middleware
</background_information>

<available_tools>
  - tool_a: [Purpose and when to use]
  - tool_b: [Purpose and when to use]
  - save_[entity]: [Persistence tool - HITL enabled]
</available_tools>

<instructions>
  ## Your Workflow
  [Decision framework for using tools adaptively]

  ## Quality Standards
  [What "good" output looks like]

  ## Critical Rules
  [Anti-hallucination, fidelity to input, validation before persistence]
</instructions>

<examples>
  [2-3 examples showing tool usage and reasoning]
</examples>

<output_format>
  Return: [ResultModelName] with success status, message, and data

  Validation checklist:
  - [ ] [Check 1]
  - [ ] [Check 2]
</output_format>
```

---

## 4. Examples Strategy

### 4.1 Canonical Examples > Edge Cases

**Anthropic Principle:** "For an LLM, examples are the 'pictures' worth a thousand words."

**Do:**
- Show 2-4 **diverse** scenarios covering common patterns
- Include reasoning process (thought → action → output)
- Use realistic inputs/outputs
- Demonstrate decision-making principles

**Don't:**
- List 20 edge cases
- Show only happy path
- Provide examples without reasoning
- Use contrived/artificial scenarios

---

### 4.2 Example Structure

```xml
<example scenario="New product with image">
  <user_input>
    Platform: WhatsApp
    Text: "catalog this jar 500ml 30rs"
    Media: [image_id: xyz123]
  </user_input>

  <your_reasoning>
    - Intent: New cataloging request (has product keywords + media)
    - Data: Product description + image attachment
    - Action: Download media first, then delegate to cataloging_department
    - Context: Provide both text and image path for complete analysis
  </your_reasoning>

  <your_action>
    1. download_whatsapp_media(media_id="xyz123") → returns local path
    2. task(
         description="Catalog product: jar 500ml 30rs. Image: [path]",
         subagent_type="cataloging_department"
       )
  </your_action>

  <expected_output>
    Delegate to department, await their structured result, relay to user
  </expected_output>
</example>
```

---

### 4.3 Coverage Matrix

For PM prompts, ensure examples cover:
- ✅ Single-domain workflows (delegate to one specialist)
- ✅ Interrupted workflow resumption
- ✅ Different input modalities (text, image, voice)
- ✅ Multiple domains (not just cataloging)

For Specialist prompts:
- ✅ Simple workflow (single tool usage)
- ✅ Complex workflow (multiple tool calls with dependencies)
- ✅ Missing data (clarification needed)
- ✅ Standard input
- ✅ Ambiguous input (reasoning through uncertainty)

---

## 5. Anti-Patterns

### 5.1 Code Snippets in Prompts

❌ **Bad:**
```
When you receive a request, execute this logic:
```python
if state.get("pending_interrupts"):
    responses = []
    for interrupt in state["pending_interrupts"]:
        responses.append({"type": "accept", "args": None})
    return Command(resume=responses)
```

✅ **Good:**
```xml
<instruction priority="high">
When pending approvals exist:
1. Identify all awaiting decisions
2. Interpret user's response for each approval
3. Construct batch response matching approval order
4. Output as COMMAND structure for runner
</instruction>

<example scenario="Batch approval">
  <context>Two products awaiting approval</context>
  <user_says>"approve both"</user_says>
  <your_reasoning>
    User approves all pending items.
    Create accept response for each.
  </your_reasoning>
  <your_output>
    COMMAND: {
      "resume": [
        {"type": "accept", "args": null},
        {"type": "accept", "args": null}
      ]
    }
  </your_output>
</example>
```

**Why better:** Shows the pattern through reasoning + example, not implementation code.

---

### 5.2 Workflow-Specific Instructions

❌ **Bad (PM prompt):**
```
You handle product cataloging. When users send product images:
1. Download from WhatsApp
2. Analyze the image
3. Create product listing
4. Get approval
5. Save to database
```

✅ **Good:**
```
You orchestrate all business workflows by delegating to domain specialists:
- Cataloging Specialist: Product catalog management
- Marketing Specialist: Campaigns and content (future)
- Operations Specialist: Billing, shipping, inventory (future)

For each request:
1. Classify domain and intent
2. Extract relevant data
3. Delegate to appropriate specialist with complete context
4. Handle any approval workflows
5. Synthesize and relay results
```

**Why better:** Generic orchestrator, not hardcoded to one workflow.

---

### 5.3 Implementation Instructions

❌ **Bad:**
```
Use the `download_whatsapp_media()` function. It takes a media_id parameter
and returns a local file path. Make sure to check if the return value is None
before proceeding.
```

✅ **Good:**
```xml
<available_tools>
  - download_whatsapp_media: Downloads media from WhatsApp using media ID.
    Use when user sends images/videos/documents. Returns local file path.
</available_tools>

<instruction>
  Download media before delegating to departments that need visual analysis.
</instruction>
```

**Why better:** States purpose and when to use, not implementation details.

---

### 5.4 Over-Specification (Wrong Altitude)

❌ **Bad:**
```
Step 1: Check if state has pending_interrupts
Step 2: If yes, extract the list
Step 3: Read the last human message
Step 4: For each interrupt in the list:
  Step 4a: Determine if user approved
  Step 4b: If "yes" or "approve", create accept response
  Step 4c: If mentions specific changes, create edit response
  ...
```

✅ **Good:**
```xml
<instruction>
  Interrupted workflows require resumption:
  - Detect: Check for pending approvals in state
  - Interpret: Map user's message to approval decisions
  - Respond: Create structured resume command
</instruction>

<example>[Show concrete example with reasoning]</example>
```

**Why better:** Right altitude for orchestrator. Details shown via example, not pseudo-code.

---

### 5.5 Insufficient Examples

❌ **Bad:**
```
Example:
User: "catalog product"
Agent: [catalogs product]
```

✅ **Good:**
```xml
<example scenario="New product with partial data">
  <user_input>
    "catalog: t-shirt, size M"
    [No price, no image]
  </user_input>

  <your_reasoning>
    - Intent: New cataloging request
    - Data: Category (t-shirt), size (M)
    - Missing: Price (critical), image (helpful)
    - Decision: Ask for price before proceeding
  </your_reasoning>

  <your_action>
    Respond: "I can catalog that t-shirt in size M. What's the price?"
  </your_action>
</example>
```

**Why better:** Shows reasoning, handles realistic scenario, demonstrates decision-making.

---

## 6. Validation Checklist

Before committing any prompt, verify:

### 6.1 Structure
- [ ] Uses XML tags for sections
- [ ] Has all required sections (background, tools, instructions, examples, output)
- [ ] Sections are ordered logically
- [ ] Clear visual hierarchy

### 6.2 Content
- [ ] No Python/code snippets (except model names)
- [ ] No workflow-specific hardcoding (generic for level)
- [ ] Right altitude for hierarchy position
- [ ] Simple, direct language (active voice, imperative)
- [ ] Minimal tokens (no redundancy)

### 6.3 Examples
- [ ] 2-4 canonical examples (not edge cases)
- [ ] Diverse scenarios covered
- [ ] Includes reasoning process
- [ ] Shows decision-making principles
- [ ] Realistic inputs/outputs

### 6.4 Alignment
- [ ] Matches agent's role in `AGENTS_DESIGN.md`
- [ ] Follows hierarchy context discipline
- [ ] Reusable across similar scenarios
- [ ] Supports future workflows (not just current MVP)

### 6.5 Technical
- [ ] References correct Pydantic models
- [ ] Tool names match implementations
- [ ] HITL patterns align with middleware
- [ ] Context injection points noted (middleware-provided)

---

## 7. References

### 7.1 Source Material

**Anthropic Engineering:**
- [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  - "Right altitude" principle
  - "Minimal high-signal tokens" principle
  - Sub-agent context management

**Claude Documentation:**
- [Prompt Engineering Overview](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview)
  - XML structure recommendations
  - Examples strategy
  - Prefilling patterns

**LangChain Patterns:**
- Structured outputs (`with_structured_output`)
- HITL with `interrupt_before`
- Agent prompt contracts (`{messages}`, `{agent_scratchpad}`)

---

### 7.2 Internal Architecture Docs

Prompts must align with:
- **[AGENTS_DESIGN.md](./AGENTS_DESIGN.md)** - Hierarchy roles, context engineering
- **[PROJECT_MANAGER_DESIGN.md](./PROJECT_MANAGER_DESIGN.md)** - PM-specific patterns
- **[LANGCHAIN_V1_FEATURES.md](./LANGCHAIN_V1_FEATURES.md)** - Technical patterns

---

### 7.3 Research Keywords for Future Updates

When searching for updated best practices:
- "Anthropic prompt engineering 2025"
- "Claude structured outputs best practices"
- "LangChain agent prompt design"
- "Multi-agent system prompts"
- "Context engineering AI agents"

---

## Appendix: Migration Checklist

### Refactoring Existing Prompts

When updating a prompt to these standards:

1. **Audit Current Prompt:**
   - [ ] Identify code snippets → Convert to principles + examples
   - [ ] Find workflow-specific logic → Generalize
   - [ ] Check altitude → Adjust for hierarchy level
   - [ ] Count lines → Target 50-70% reduction

2. **Restructure:**
   - [ ] Add XML section tags
   - [ ] Separate background, tools, instructions, examples, output
   - [ ] Reorder for logical flow

3. **Rewrite Instructions:**
   - [ ] Remove implementation details
   - [ ] Add decision principles
   - [ ] Simplify language
   - [ ] Add quality standards

4. **Replace Code with Examples:**
   - [ ] For each code block, create 1 example showing the pattern
   - [ ] Include reasoning in examples
   - [ ] Cover diverse scenarios (2-4 examples total)

5. **Validate:**
   - [ ] Run through checklist (Section 6)
   - [ ] Test with REPL or local CLI
   - [ ] Compare trace quality before/after
   - [ ] Measure token reduction

6. **Document:**
   - [ ] Update prompt version/date header
   - [ ] Note major changes in git commit
   - [ ] Link to this standards doc in prompt comments

---

**Last Updated:** January 2025
**Next Review:** When adopting Claude 4.0 or LangChain 2.0
**Maintained By:** Architecture team

