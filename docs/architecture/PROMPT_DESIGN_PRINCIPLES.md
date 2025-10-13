# Prompt Design Principles for Agentic Intelligence

**Last Updated**: 2025-10-13
**Status**: Living Document

---

## Philosophy

Agents are intelligent reasoning systems, not script executors. Prompts should **empower thinking**, not **restrict behavior**.

---

## Core Principles

### 1. **Guide, Don't Command**

❌ **Wrong**: "Do X, then Y, then Z. ALWAYS do this. NEVER do that."
✅ **Right**: "You have tools X, Y, Z. Use your judgment to accomplish the goal."

**Why**: Agents need autonomy to handle unforeseen scenarios. Commands create brittleness.

**Example**:
```markdown
# Bad Prompt
**Step 1:** Extract name
**Step 2:** Extract price
**IMPORTANT:** Always include description
**CRITICAL:** Never omit fields

# Good Prompt
## Your Role
Extract product information from user input.
Consider what details matter for a complete listing.
Use your judgment about what to include.
```

---

### 2. **Principles Over Rules**

❌ **Wrong**: List 50 if-then rules for every scenario
✅ **Right**: Explain the underlying principles and let agents reason

**Why**: Principles generalize. Rules don't scale to new situations.

**Example**:
```markdown
# Bad Prompt
- If user says "approved", set status to approved
- If user says "yes", set status to approved
- If user says "looks good", set status to approved
- If user says "ok", set status to approved
[...50 more rules]

# Good Prompt
## Understanding Approval
Users affirm decisions in many ways.
Look for positive sentiment and confirmation intent.
Use your judgment about whether they're approving.
```

---

### 3. **Explain the "Why", Not Just the "What"**

❌ **Wrong**: "Extract these fields: name, price, description"
✅ **Right**: "Customers need clear product info to make purchase decisions. Extract details that serve this purpose."

**Why**: Understanding purpose enables intelligent adaptation.

**Example**:
```markdown
# Bad Prompt
Return JSON with exactly these fields: name, description, price.

# Good Prompt
## Your Purpose
Create product listings that help customers make informed purchases.
Include details that matter for discovery and decision-making.
```

---

### 4. **Show Thinking, Not Just Output**

❌ **Wrong**: "Return structured JSON"
✅ **Right**: "Reason about the product, then structure your insights"

**Why**: Encourages deeper analysis and better decisions.

**Example**:
```markdown
# Bad Prompt
Extract product data into Product schema.

# Good Prompt
## How You Think
1. What product is this?
2. What makes it distinctive?
3. What details matter for selling?
4. How would you describe it compellingly?

Now structure your insights into the Product model.
```

---

### 5. **Context Awareness Over Explicit Instructions**

❌ **Wrong**: Embed all knowledge in prompt
✅ **Right**: Give agents context and let them query/reason

**Why**: Agents can access knowledge dynamically. Static prompts become outdated.

**Example**:
```markdown
# Bad Prompt
Colors must be one of: red, blue, green, yellow, orange, purple, pink, black, white, gray, brown...

# Good Prompt
## Understanding Colors
Describe colors accurately and specifically.
"Navy blue" is better than "blue".
"Charcoal gray" is better than "gray".
Use your visual understanding.
```

---

### 6. **Flexibility for Future Scenarios**

❌ **Wrong**: Design for current use case only
✅ **Right**: Design for the problem space, not just today's requirements

**Why**: New workflows emerge. Agents should adapt without prompt rewrites.

**Example**:
```markdown
# Bad Prompt (cataloging-specific)
Extract product name, price, and description for cataloging.

# Good Prompt (general product understanding)
Understand products from various information sources.
Extract and synthesize details that create complete product records.
Adapt to whatever information is available.
```

---

### 7. **Trust Agent Intelligence**

❌ **Wrong**: "WAIT for result. IMPORTANT: Don't do X. CRITICAL: Must do Y."
✅ **Right**: "Coordinate intelligently. Consider dependencies."

**Why**: Over-warning signals distrust. Agents perform better when trusted.

**Example**:
```markdown
# Bad Prompt
1. Call image_analysis_specialist
2. **WAIT for result before proceeding**
3. **IMPORTANT:** Pass ACTUAL result to next tool
4. **CRITICAL:** Do NOT pass None

# Good Prompt
Visual analysis informs cataloging.
Get image insights before synthesizing the product listing.
```

---

### 8. **Examples Show Reasoning, Not Just Answers**

❌ **Wrong**: Input → Output pairs
✅ **Right**: Input → Thinking Process → Output

**Why**: Agents learn reasoning patterns, not memorized mappings.

**Example**:
```markdown
# Bad Example
Input: "jar for 10rs"
Output: {"name": "Jar", "price": 10}

# Good Example
User: "catalog this jar for 10rs"
Image: Clear glass, cylindrical, ~250ml

Your Reasoning:
User wants to catalog a jar. Price stated: 10rs.
Image shows glass storage jar, approximately 250ml capacity.
I'll create a complete listing synthesizing both sources.

Output: Product with name "Glass Storage Jar 250ml",
        description blending visual and text details,
        price: 10
```

---

## Red Flags in Prompts

Watch for these anti-patterns:

- **ALL CAPS WARNINGS**: Signals micromanagement
- **"ALWAYS/NEVER" absolutes**: Removes judgment
- **Step-by-step recipes**: Makes agents brittle
- **"EXACTLY according to schema"**: Over-constrains
- **Long lists of if-then rules**: Doesn't scale
- **Repeated emphasis (IMPORTANT, CRITICAL, etc.)**: Shows lack of trust

---

## Prompt Structure Template

```markdown
# [Agent Name]

[One-line purpose statement]

## Your Role

[What the agent is responsible for - the problem space, not just tasks]

## What You Consider

[Key factors to reason about]
- [Domain knowledge needed]
- [Context available]
- [Constraints that matter]

## How You Think

[Reasoning framework - the thought process]
1. [Understand the problem]
2. [Consider options]
3. [Make judgment calls]
4. [Execute with intelligence]

## Your Tools

[Available capabilities with purpose, not just mechanics]

## Output Structure

[Expected format with philosophical guidance]
- [Field]: [Purpose and reasoning]

**Philosophy**: [Guiding principle for decisions]

## Example Reasoning

[Show thinking process, not just I/O]

**Scenario**: [Realistic situation]
**Your Thinking**: [Internal reasoning]
**Execution**: [How you'd approach it]

---

**Context Available**: [What's automatically injected]

Now [verb that empowers] [using intelligence/judgment].
```

---

## Validation Checklist

Before finalizing a prompt, ask:

- [ ] Does it empower the agent to think, or command it to execute?
- [ ] Are principles clear, or buried in rules?
- [ ] Does it explain "why", not just "what"?
- [ ] Will this work for scenarios we haven't imagined yet?
- [ ] Would a smart human understand the intent and adapt?
- [ ] Are examples showing reasoning, not just answers?
- [ ] Is it trust-based, not fear-based?

---

## Evolution

Prompts should evolve as:
- New workflows emerge
- Agents demonstrate capabilities
- Architecture patterns mature

**Update prompts when you add new capabilities, not when existing ones fail.**

If an agent isn't doing what you want, first ask: "Am I restricting its intelligence?" before adding more rules.

---

## See Also

- `AGENTS_DESIGN.md` - Hierarchical architecture
- `LANGCHAIN_V1_FEATURES.md` - Technical implementation
- Individual agent prompts in `agents/prompts/`
