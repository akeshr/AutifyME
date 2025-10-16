# Improvement Methodology - Fix Generation Strategies

**Date**: 2025-01-16
**Status**: 🔬 DESIGN
**Purpose**: Systematic approaches to generating and validating improvements

---

## Executive Summary

This document provides systematic methodologies for generating improvements (prompt changes, code fixes, architecture adjustments) based on identified issues. Each methodology includes: issue identification, root cause patterns, fix generation strategies, validation criteria, and risk assessment.

**Issue Categories**:
1. **Prompt Issues** (40% of issues) - Missing instructions, ambiguous wording, type emphasis
2. **Code Issues** (30% of issues) - Bugs, missing error handling, type coercion
3. **Architecture Issues** (20% of issues) - Context leakage, wrong delegation, state management
4. **Data Quality Issues** (10% of issues) - Schema violations, missing fields

**Fix Types**:
- Prompt improvements
- Code fixes
- Architecture adjustments
- Configuration changes

---

## Prompt Issues

### Issue Pattern 1: Missing Type Emphasis

**Symptoms**:
- ValidationError: "field must be X, got Y"
- Specialist returns wrong types (string instead of float)
- Pydantic schema violations

**Root Cause**:
Prompt doesn't emphasize that numeric fields must be actual numbers, not strings.

**Fix Template**:
```markdown
Add to specialist prompt:

## Output Type Requirements

CRITICAL: Ensure all fields match their Pydantic type specifications:

### Numeric Fields
- **price**: MUST be float (numeric), not string
  - ❌ Incorrect: "79.99" (quoted)
  - ✅ Correct: 79.99 (no quotes)
  - Convert: "Rs 79" → 79.0

- **quantity**: MUST be int, not string
  - ❌ Incorrect: "5"
  - ✅ Correct: 5

### List Fields
- **sizes**: MUST be list of strings, even if single item
  - ❌ Incorrect: "M" (single string)
  - ✅ Correct: ["M"] (list)

- **colors**: MUST be list of strings
  - ❌ Incorrect: "blue"
  - ✅ Correct: ["blue"]

### Optional Fields
- If field not mentioned, return None (not empty string)
  - ❌ Incorrect: {"description": ""}
  - ✅ Correct: {"description": None}

## Examples
```json
{
  "name": "Canvas Sneakers",
  "price": 79.99,          // float, not "79.99"
  "sizes": ["7", "8", "9"], // list, not "7,8,9"
  "colors": ["white"],      // list, not "white"
  "description": None       // None if not provided
}
```
```

**Expected Impact**:
- Eliminate type validation errors
- All Pydantic schemas pass validation
- Success rate: +30-50%

**Confidence**: 0.9 (high)
**Risk**: Low (prompt-only, doesn't affect logic)

---

### Issue Pattern 2: Missing Clarification Instructions

**Symptoms**:
- Specialist proceeds with incomplete data
- Missing required fields
- PM doesn't ask for clarification

**Root Cause**:
Prompt doesn't instruct component to ask for missing information.

**Fix Template**:
```markdown
Add to prompt:

## Handling Missing Information

If critical fields are MISSING or UNCLEAR:

1. **Identify** what's missing
   - Required fields: name, price (at minimum)
   - Nice-to-have: description, colors, sizes

2. **Ask for clarification** - be specific
   - ❌ Bad: "I need more information"
   - ✅ Good: "What's the price for this product?"
   - ✅ Good: "What sizes are available?"

3. **Don't proceed** without required fields
   - DO NOT guess or assume
   - DO NOT use placeholder values
   - DO NOT call save_product with incomplete data

4. **Format clarification requests** clearly
   - State what you have
   - State what you need
   - Ask one question at a time

## Example

User input: "Catalog this" (with image of sneakers)

❌ Incorrect response:
```json
{"name": "Sneakers", "price": null}  // Missing price!
```

✅ Correct response:
"I can see these are white canvas sneakers. What's the price for them?"
```

**Expected Impact**:
- Reduce incomplete submissions
- Better user experience (clear asks)
- Success rate: +10-20%

**Confidence**: 0.85
**Risk**: Low (improves UX)

---

### Issue Pattern 3: Context Engineering Missing

**Symptoms**:
- Excessive token usage (10K+ for simple call)
- Full conversation history passed to specialist
- Slow performance

**Root Cause**:
Department passes all context to specialists instead of extracting relevant parts.

**Fix Template**:
```markdown
Add to department prompt:

## Specialist Delegation Strategy

When delegating to specialists, practice CONTEXT ENGINEERING:

### What to Pass
✅ **User's current message** - the actual request
✅ **Relevant extracted data** - image analysis if available
✅ **Critical context only** - product name if multi-turn

### What NOT to Pass
❌ Full conversation history (all 50 messages)
❌ System messages or internal state
❌ PM's reasoning or planning
❌ Previous specialist outputs (unless needed)

### Examples

❌ Incorrect (passing everything):
```python
specialist(messages=state["messages"])  # All history!
```

✅ Correct (extracting relevant parts):
```python
specialist(
    user_message=extract_user_message(state["messages"][-1]),
    image_analysis=state.get("image_analysis")  # If available
)
```

### Multi-Turn Context
If user provides additional info across multiple messages:
- Maintain product_draft in state
- Pass accumulated fields + new message
- Don't re-send full history

```python
specialist(
    user_message=current_message,
    existing_product=state.get("product_draft"),  # Accumulated so far
    image_analysis=state.get("image_analysis")
)
```
```

**Expected Impact**:
- Token usage: -60-80%
- Latency: -30-50%
- Cost: -60-80%

**Confidence**: 0.95
**Risk**: Medium (requires careful extraction logic)

---

## Code Issues

### Issue Pattern 1: Missing Error Handling

**Symptoms**:
- Tool crashes with unhandled exception
- No fallback behavior
- User sees generic error

**Root Cause**:
Tool doesn't handle expected errors (type coercion, validation, network).

**Fix Template**:
```python
# Before (fragile)
def save_product(price: float, **kwargs):
    product = Product(price=price, **kwargs)
    storage.save_product(product)
    return CatalogingResult(success=True, ...)

# After (robust)
def save_product(price: float, **kwargs):
    try:
        # Type coercion for common mistakes
        if isinstance(price, str):
            # Remove currency symbols
            price = price.replace('$', '').replace('Rs', '').replace(',', '')
            try:
                price = float(price)
            except ValueError:
                raise ToolException(f"Invalid price format: {price}. Expected number like 79.99")

        # Validate types
        if not isinstance(price, (int, float)):
            raise ToolException(f"Price must be numeric, got {type(price).__name__}")

        # Create product (Pydantic validation)
        product = Product(price=price, **kwargs)

        # Save to storage
        saved = storage.save_product(product)

        return CatalogingResult(
            stage="saved",
            success=True,
            product_id=saved.id,
            message=f"Product '{saved.name}' saved successfully"
        )

    except ValidationError as e:
        # Pydantic validation failed
        errors = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
        raise ToolException(f"Product validation failed: {errors}")

    except StorageException as e:
        # Database error
        raise ToolException(f"Failed to save product: {str(e)}")

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in save_product: {e}", exc_info=True)
        raise ToolException(f"Unexpected error: {str(e)}")
```

**Expected Impact**:
- Graceful error handling
- Clear error messages to user
- No crashes, better recovery

**Confidence**: 0.9
**Risk**: Low (defensive programming)

---

### Issue Pattern 2: Missing Field Extraction

**Symptoms**:
- Field not saved to database (e.g., image_urls)
- Data lost in transformation
- DB record incomplete

**Root Cause**:
Department doesn't extract field from specialist output before calling tool.

**Fix Template**:
```python
# Before (missing extraction)
def execute_cataloging_workflow(user_message, image_path):
    # Analyze image
    img_result = image_analysis_specialist(image_path=image_path)

    # Get product details
    product = cataloging_specialist(
        user_message=user_message,
        image_analysis=img_result
    )

    # Save product
    save_product(**product.model_dump())  # ❌ image_urls not in product!

# After (extract and include)
def execute_cataloging_workflow(user_message, image_path):
    # Analyze image
    img_result = image_analysis_specialist(image_path=image_path)

    # Get product details
    product = cataloging_specialist(
        user_message=user_message,
        image_analysis=img_result
    )

    # Prepare save data
    product_data = product.model_dump()

    # ✅ Extract image_urls from source
    if image_path:
        product_data['image_urls'] = [image_path]  # Add image URL

    # Save product with all fields
    save_product(**product_data)
```

**Expected Impact**:
- All fields saved correctly
- No data loss
- DB records complete

**Confidence**: 0.95
**Risk**: Low (data preservation)

---

## Architecture Issues

### Issue Pattern 1: Context Leakage

**Symptoms**:
- Excessive token usage
- Slow performance
- Specialist receives full conversation history

**Root Cause**:
Department passes entire state to specialists instead of minimal context.

**Fix Template**:

See "Context Engineering Missing" in Prompt Issues section above.

This is typically a **hybrid fix**: Prompt + Code
1. Prompt: Instruct department to extract context
2. Code: Ensure extraction logic exists

**Expected Impact**:
- Token usage: -60-80%
- Performance improvement

**Confidence**: 0.9
**Risk**: Medium (requires testing extraction)

---

### Issue Pattern 2: Multi-Turn Context Loss

**Symptoms**:
- Multi-turn clarification fails
- Context from turn 1 lost by turn 3
- User must repeat information

**Root Cause**:
Department doesn't maintain accumulated context across turns.

**Fix Template**:
```python
# Before (context lost)
def handle_message(state, user_message):
    if "image_analysis" in state:
        # Have image from previous turn
        product = cataloging_specialist(user_message=user_message)  # ❌ Lost image_analysis!
    else:
        # ...

# After (context preserved)
def handle_message(state, user_message):
    # Gather all available context
    context = {}

    # Check for image_analysis from previous turn
    if "image_analysis" in state:
        context["image_analysis"] = state["image_analysis"]

    # Check for partial product from previous turn
    if "product_draft" in state:
        context["existing_product"] = state["product_draft"]

    # Call specialist with accumulated context
    product = cataloging_specialist(
        user_message=user_message,
        **context  # ✅ Pass all relevant context
    )

    # Update draft in state for next turn
    state["product_draft"] = product
```

**Expected Impact**:
- Multi-turn workflows work correctly
- Better UX (no repetition)

**Confidence**: 0.85
**Risk**: Medium (state management complexity)

---

## Validation Criteria

### When to Apply Improvements

**Apply if ALL true**:
- ✅ Confidence > 0.7
- ✅ Risk level: low or medium
- ✅ No breaking changes
- ✅ Affects localized component

**Require user review if ANY true**:
- ⚠️ Confidence < 0.7
- ⚠️ Risk level: high
- ⚠️ Touches multiple components
- ⚠️ Changes architecture

**Always require approval**:
- ❗ Code changes (all)
- ❗ Architecture changes (all)
- ❗ Database schema changes

**Can auto-apply** (if user configured):
- ✅ Prompt improvements (confidence > 0.8, isolated prompts)
- ✅ Documentation updates
- ✅ Test additions

---

## Validation Process

### Step 1: Apply Improvement
```python
result = apply_improvement(type, file, changes, backup=True)
```

### Step 2: Retest
```python
new_result = execute_scenario(scenario_id, "auto_approve")
```

### Step 3: Compare Metrics
```python
comparison = compare_execution_metrics(baseline, new_result)
```

### Step 4: Decision
```python
if comparison.improved and comparison.success_rate_delta > 0:
    decision = "KEEP"
elif comparison.success_rate_delta < 0:
    decision = "REVERT"  # Regression
else:
    decision = "ITERATE"  # No clear improvement
```

### Step 5: Regression Check
```python
# Test passing scenarios to ensure no regression
for passing_scenario in passing_scenarios:
    result = execute_scenario(passing_scenario)
    if not result.success:
        decision = "REVERT"  # Broke passing scenario
```

---

## Risk Assessment

### Risk Levels

**Low Risk**:
- Prompt-only changes
- Adding instructions (not removing)
- Adding error handling
- Documentation updates

**Medium Risk**:
- Prompt changes that remove instructions
- Code logic changes (single component)
- Adding new fields
- Context extraction logic

**High Risk**:
- Multi-component changes
- Architecture modifications
- State management changes
- Database schema changes
- Breaking API changes

---

## Best Practices

### For Improvement Generation

1. **Analyze root cause thoroughly** - Don't fix symptoms
2. **Use examples from traces** - Show what went wrong
3. **Explain reasoning clearly** - Why this fixes the issue
4. **Estimate impact** - What should improve?
5. **Assess risk honestly** - Don't underestimate

### For Validation

1. **Always retest** - Never assume fix works
2. **Check regressions** - Test passing scenarios
3. **Compare metrics** - Success rate, latency, cost
4. **Validate DB state** - Check records created
5. **Keep backups** - Always create before applying

### For Users

1. **Review confidence scores** - Question low confidence
2. **Read reasoning** - Understand why proposed
3. **Check risk level** - High risk needs careful review
4. **Test incrementally** - Apply one fix at a time
5. **Track history** - Learn what works

---

**Last Updated**: 2025-01-16
**Next Review**: After Phase 1 implementation
