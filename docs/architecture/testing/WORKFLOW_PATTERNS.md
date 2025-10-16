# Workflow Patterns - Common Testing Workflows

**Date**: 2025-01-16
**Status**: 🔬 DESIGN
**Purpose**: Detailed workflow examples for common testing scenarios

---

## Executive Summary

This document provides detailed workflow patterns for Claude (Jarvis) when orchestrating testing activities. Each pattern includes: user request, Claude's reasoning process, tool sequence, decision points, and reporting format.

**Patterns Covered**:
1. Single Scenario Analysis
2. Multi-Scenario Batch Testing
3. Improvement Validation
4. Continuous Iteration
5. Issue Investigation
6. Production Failure Reproduction
7. Regression Testing
8. Performance Analysis

---

## Pattern 1: Single Scenario Analysis

**Use Case**: Test one scenario, identify issues, propose fixes

**User Request**: "Jarvis, test cataloging_with_image and find any issues"

### Claude's Workflow

**Phase 1: Execute**
```python
# Claude's reasoning: "I'll execute the scenario first to see if it passes"
result = execute_scenario("cataloging_with_image", "auto_approve")

# Claude checks result
if result.success:
    # "Scenario passed! Let me do quick validation..."
    proceed_to_validation()
else:
    # "Scenario failed. Let me analyze the failure..."
    proceed_to_analysis()
```

**Phase 2: Lightweight Analysis**
```python
# Claude's reasoning: "Let me get the trace structure to see what failed"
structure = get_trace_structure(result.trace_id)

# Claude analyzes structure
# "I can see from the structure that only save_product failed (run_5).
#  All upstream components (PM, Department, Specialists) succeeded.
#  This tells me the issue is isolated to save_product."

# Claude decides: Focus on save_product and its input source
target_runs = ["save_product_5", "cataloging_specialist_4"]
```

**Phase 3: Focused Investigation**
```python
# Claude's reasoning: "Let me analyze the failure details"
failure = analyze_failure_chain("save_product_5")

# Claude reads failure
# "Error: ValidationError: price must be float, got <class 'str'>
#  Root cause hypothesis: Cataloging specialist returned wrong type
#  I should validate the specialist's output to confirm."

# Claude validates
validation = validate_structured_output("cataloging_specialist_4", "Product")

# "Confirmed! The specialist returned:
#  {\"price\": \"79.99\"} (string)
#  Expected: {\"price\": 79.99} (float)
#  This is a prompt issue - the specialist prompt doesn't emphasize type requirements."
```

**Phase 4: Database Validation**
```python
# Claude's reasoning: "Let me also check if any DB record was created"
db_check = quick_db_check("cataloging_with_image")

# "As expected, no product record exists (count: 0) because save_product failed."
```

**Phase 5: Report to User**
```
Claude presents finding report (see REPORTING TEMPLATES in main doc)
```

**User Response**: "Yes, generate the improvement"

**Phase 6: Generate Improvement**
```python
current_prompt = read_file("agents/src/.../cataloging_specialist.prompt")

improvement = generate_prompt_improvement(
    issue_description="Specialist returns price as string instead of float",
    current_prompt=current_prompt,
    trace_examples=["cataloging_specialist_4"]
)

# Claude presents improvement with diff and reasoning
```

**User Response**: "Apply it and retest"

**Phase 7: Apply & Validate**
```python
result = apply_improvement("prompt", target_file, improvement.proposed_prompt)

# "✅ Applied. Backup created: ...prompt.backup.20250116_143022"

# Re-test
new_result = execute_scenario("cataloging_with_image", "auto_approve")

# "✅ Success! Scenario now passes."

# Validate DB record
record = get_product_record(scenario_id="cataloging_with_image")

# "✅ Product record created with correct types:
#  - price: 79.99 (float) ✓
#  - All fields populated ✓"

# Compare metrics
comparison = compare_execution_metrics(result, new_result)

# Present final report with validation results
```

**Token Usage**: ~2,500 tokens
**Time**: ~3 minutes
**Outcome**: Issue identified, fix applied, validated

---

## Pattern 2: Multi-Scenario Batch Testing

**Use Case**: Test multiple scenarios systematically

**User Request**: "Test all cataloging scenarios and report issues"

### Claude's Workflow

**Phase 1: Load Scenarios**
```python
# Claude's reasoning: "Let me get all cataloging scenarios"
scenarios = load_scenario_list("cataloging_*")

# "Found 5 cataloging scenarios:
#  - cataloging_with_image
#  - cataloging_text_only
#  - cataloging_with_caption
#  - image_with_clear_caption
#  - image_no_caption"
```

**Phase 2: Execute All Scenarios**
```python
results = {}
for scenario_id in scenarios:
    # Claude reports progress
    # f"Testing {scenario_id} ({i+1}/{len(scenarios)})..."

    result = execute_scenario(scenario_id, "auto_approve")
    results[scenario_id] = result

    # Quick analysis
    if not result.success:
        # "❌ {scenario_id} failed: {result.error}"
        structure = get_trace_structure(result.trace_id)
        # Store failure details for later analysis
    else:
        # "✅ {scenario_id} passed"
        # Quick DB validation
        db_check = quick_db_check(scenario_id)
```

**Phase 3: Aggregate Findings**
```python
# Claude analyzes all results
passed = [s for s, r in results.items() if r.success]
failed = [s for s, r in results.items() if not r.success]

# "Results:
#  ✅ Passed: 3/5 (cataloging_text_only, image_with_clear_caption, image_no_caption)
#  ❌ Failed: 2/5 (cataloging_with_image, cataloging_with_caption)"

# Claude identifies patterns
# "Both failures show ValidationError for 'price must be float'.
#  This appears to be a systematic issue affecting image-based cataloging."
```

**Phase 4: Deep Analysis of Failures**
```python
# Claude focuses on first failure
failure1 = analyze_failure_chain(results["cataloging_with_image"].trace_id)
failure2 = analyze_failure_chain(results["cataloging_with_caption"].trace_id)

# "Both failures have the same root cause:
#  Cataloging specialist returns price as string.
#  This is a single prompt issue affecting multiple scenarios."
```

**Phase 5: Report Summary**
```
Claude presents batch report:

## BATCH TESTING SUMMARY
Scenarios Tested: 5
Passed: 3 (60%)
Failed: 2 (40%)

### CRITICAL ISSUE IDENTIFIED
**Title**: Cataloging Specialist Type Error
**Affected Scenarios**: cataloging_with_image, cataloging_with_caption
**Root Cause**: Specialist prompt doesn't emphasize numeric type requirements
**Impact**: 40% of cataloging scenarios fail

### PASSING SCENARIOS
✅ cataloging_text_only
✅ image_with_clear_caption
✅ image_no_caption

### RECOMMENDATION
Fix the cataloging specialist prompt to emphasize type coercion.
This single fix will resolve both failing scenarios.

**Shall I generate the prompt improvement?**
```

**User**: "Yes, and retest all scenarios after fix"

**Phase 6: Apply Fix & Retest**
```python
# Generate and apply improvement
improvement = generate_prompt_improvement(...)
apply_improvement(...)

# Retest all scenarios
for scenario_id in scenarios:
    new_result = execute_scenario(scenario_id, "auto_approve")
    # Compare before/after

# Final report:
# "✅ ALL 5 SCENARIOS NOW PASS
#  Success rate: 60% → 100%
#  Single prompt fix resolved 2 failing scenarios"
```

---

## Pattern 3: Improvement Validation

**Use Case**: Validate a fix works and doesn't cause regressions

**User Request**: "Apply the prompt fix and validate it works across all affected scenarios"

### Claude's Workflow

**Phase 1: Apply Improvement**
```python
result = apply_improvement(
    improvement_type="prompt",
    target_file="agents/src/.../cataloging_specialist.prompt",
    changes=improvement.proposed_prompt
)

# "✅ Applied. Backup: ...prompt.backup.20250116_143022"
```

**Phase 2: Retest Affected Scenarios**
```python
# Claude identifies affected scenarios
affected = improvement.affected_scenarios  # ["cataloging_with_image", "cataloging_with_caption"]

before_results = {}
after_results = {}

for scenario_id in affected:
    # "Testing {scenario_id} with new prompt..."
    after_result = execute_scenario(scenario_id, "auto_approve")
    after_results[scenario_id] = after_result

    # Compare
    comparison = compare_execution_metrics(
        baseline=before_results[scenario_id],
        new=after_result
    )

    if comparison.improved:
        # "✅ {scenario_id}: Improved"
    elif comparison.recommendation == "REVERT":
        # "❌ {scenario_id}: Degraded - REVERT recommended"
```

**Phase 3: Regression Check**
```python
# Claude tests passing scenarios to ensure no regression
passing = ["cataloging_text_only", "image_with_clear_caption"]

for scenario_id in passing:
    # "Regression check: {scenario_id}..."
    result = execute_scenario(scenario_id, "auto_approve")

    if not result.success:
        # "⚠️ REGRESSION DETECTED: {scenario_id} now fails"
```

**Phase 4: Validation Report**
```
## IMPROVEMENT VALIDATION REPORT

### Applied Change
**Type**: Prompt improvement
**File**: cataloging_specialist.prompt
**Backup**: ...backup.20250116_143022

### Affected Scenarios Results
✅ cataloging_with_image: FIXED (0% → 100% success)
✅ cataloging_with_caption: FIXED (0% → 100% success)

### Regression Check
✅ cataloging_text_only: STABLE (100% → 100%)
✅ image_with_clear_caption: STABLE (100% → 100%)
✅ image_no_caption: STABLE (100% → 100%)

### Metrics Comparison
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Success Rate | 60% | 100% | +40% |
| Avg Latency | 2.1s | 2.0s | -0.1s |
| Avg Cost | $0.08 | $0.08 | $0.00 |

### Decision: **KEEP**
- No regressions detected
- All affected scenarios fixed
- Performance stable

**Should I generate regression tests for these fixes?**
```

---

## Pattern 4: Continuous Iteration

**Use Case**: Keep testing and improving until all scenarios pass

**User Request**: "Keep testing scenarios and fixing issues until everything passes"

### Claude's Workflow

```python
# Initialize
scenarios = load_scenario_list("*")
improvement_history = []
iteration = 0

while True:
    iteration += 1
    print(f"\n=== ITERATION #{iteration} ===")

    # Select next scenario
    next_scenario = select_next_scenario(
        queue=scenarios,
        history=improvement_history,
        strategy="failure_rate"
    )

    print(f"Testing: {next_scenario}")

    # Execute
    result = execute_scenario(next_scenario, "auto_approve")

    if result.success:
        # Quick validation
        db_check = quick_db_check(next_scenario)

        if db_check.matches_expected:
            print(f"✅ {next_scenario} passed")
            # Remove from queue
            scenarios.remove(next_scenario)
        else:
            print(f"⚠️ {next_scenario} passed but DB issue")
            # Investigate
            analyze_db_issue(next_scenario)
    else:
        print(f"❌ {next_scenario} failed")

        # Analyze failure
        structure = get_trace_structure(result.trace_id)
        failure = analyze_failure_chain(structure.failed_runs[0])

        print(f"Root cause: {failure.root_cause_hypothesis}")

        # Generate improvement
        improvement = generate_improvement_for_issue(failure)

        # Present to user
        print(f"\nProposed fix:\n{improvement.reasoning}")
        user_input = input("Apply? (yes/no): ")

        if user_input.lower() == "yes":
            # Apply
            apply_result = apply_improvement(...)

            # Validate
            new_result = execute_scenario(next_scenario, "auto_approve")
            comparison = compare_execution_metrics(result, new_result)

            if comparison.improved:
                print(f"✅ Fix validated")
                improvement_history.append({
                    "scenario": next_scenario,
                    "improvement": improvement,
                    "result": "success"
                })
            else:
                print(f"❌ Fix didn't help - reverting")
                # Revert
        else:
            print("Skipping this scenario")

    # Check if done
    if len(scenarios) == 0:
        print("\n🎉 ALL SCENARIOS PASSING!")
        break

    # Progress report
    print(f"\nProgress: {len(improvement_history)} improvements applied")
    print(f"Remaining: {len(scenarios)} scenarios")

    user_input = input("\nContinue? (yes/no): ")
    if user_input.lower() != "yes":
        break
```

**Final Report**:
```
## CONTINUOUS ITERATION SESSION COMPLETE

**Duration**: 2 hours
**Iterations**: 12
**Scenarios Tested**: 15
**Issues Found**: 8
**Improvements Applied**: 6
**Success Rate**: 53% → 100%

### TOP IMPROVEMENTS
1. ✅ Cataloging specialist type coercion (fixed 3 scenarios)
2. ✅ PM intent classification (fixed 2 scenarios)
3. ✅ Image URL extraction (fixed 1 scenario)

### METRICS
- Avg latency: 2.3s → 1.9s (-17%)
- Avg cost: $0.12 → $0.09 (-25%)
- All scenarios now passing

**System quality significantly improved!**
```

---

## Pattern 5: Issue Investigation

**Use Case**: Deep dive into specific failure

**User Request**: "Why did multi_turn_clarification fail? Give me a detailed analysis."

### Claude's Workflow

**Phase 1: Execute (if needed)**
```python
# If not already executed
result = execute_scenario("multi_turn_clarification", "auto_approve")
```

**Phase 2: Deep Analysis**
```python
# Level 0
structure = get_trace_structure(result.trace_id)

# "This is a multi-turn scenario with 3 conversation turns.
#  Turn 1: PM responds (success)
#  Turn 2: Department processes (success)
#  Turn 3: save_product fails (ValidationError)"

# Level 1
failure = analyze_failure_chain(structure.failed_runs[0])

# "The failure happened in turn 3.
#  Error: ValidationError: price must be float
#  But this is interesting - turns 1 and 2 succeeded.
#  Let me check if context was preserved correctly."

# Check conversation history
outcome = get_scenario_outcome(result.thread_id)
messages = outcome.message_history

# "I can see the conversation flow:
#  Turn 1: User: 'Catalog this product'
#  Turn 2: PM: 'What's the price?'
#  Turn 3: User: '79 dollars'
#
#  The issue: When the user provided price in turn 3, the context
#  from turn 1 (image) may not have been passed to the specialist."

# Level 2 (deep dive)
details = get_full_run_details("cataloging_specialist_run")

# "Looking at the specialist's inputs:
#  {\"user_message\": \"79 dollars\"}
#
#  Missing: image_analysis from turn 1!
#
#  This is an architecture issue - multi-turn context preservation."
```

**Phase 3: Root Cause Report**
```
## DEEP ANALYSIS: multi_turn_clarification

### Symptom
Scenario fails at turn 3 with ValidationError

### Surface Cause
Cataloging specialist returns price as string

### Deeper Issue
Multi-turn context not preserved - image analysis from turn 1 lost by turn 3

### Root Cause
**Architecture Issue**: Department doesn't maintain multi-turn context.
When user provides missing info in subsequent turn, previous context (image analysis)
is not included in specialist call.

### Evidence
1. Turn 1: Image provided, analyzed
2. Turn 2: PM asks for price (image_analysis stored in state)
3. Turn 3: User provides price, but specialist called WITHOUT image_analysis

Specialist inputs (turn 3):
```json
{"user_message": "79 dollars"}
```

Expected:
```json
{
  "user_message": "79 dollars",
  "image_analysis": {... from turn 1 ...}
}
```

### Impact
- Multi-turn clarification workflows broken
- Affects all scenarios where user provides info across multiple messages

### Recommended Fix
Update department logic to:
1. Check state for existing context (image_analysis, previous fields)
2. Include existing context when calling specialists
3. Accumulate product fields across turns

**This is not a prompt issue - requires code changes to department.**
```

---

## Pattern 6: Production Failure Reproduction

**Use Case**: Reproduce and debug production failure

**User Request**: "Production user reported cataloging failure with ID #12345. Reproduce and fix."

### Claude's Workflow

**Phase 1: Fetch Production Data**
```python
# Fetch production trace
production_trace_id = fetch_production_trace_id(incident_id="12345")

# Get production trace structure
structure = get_trace_structure(production_trace_id)

# "Production trace shows:
#  - User message: 'catalog sneakers blue $85'
#  - Image attached: <media_id>
#  - Failure at: save_product (ValidationError)"
```

**Phase 2: Reproduce Locally**
```python
# Recreate scenario
result = execute_scenario(
    "catalog sneakers blue $85",
    media_path="<downloaded_production_image>"
)

# "✅ Reproduced locally - same ValidationError"
```

**Phase 3: Analyze**
```python
# Follow Pattern 1 (Single Scenario Analysis)
# Identify root cause...
```

**Phase 4: Fix & Validate**
```python
# Generate fix, apply, retest
# ...

# Validate against production data
# "Fix validated - production scenario now passes"
```

---

## Decision Points

### When to Use Each Pattern

| Pattern | Use When | Duration | Complexity |
|---------|----------|----------|------------|
| Single Scenario | Testing one scenario | 2-5 min | Low |
| Batch Testing | Testing category of scenarios | 10-30 min | Medium |
| Improvement Validation | After applying fix | 3-10 min | Low |
| Continuous Iteration | Systematic quality improvement | 1-4 hours | High |
| Issue Investigation | Deep dive on complex failure | 10-30 min | High |
| Production Reproduction | Debugging production issue | 5-20 min | Medium |

---

## Best Practices

### For Claude

1. **Always explain reasoning** - Show what you found, why drilling down
2. **Use hierarchical analysis** - Start lightweight, drill selectively
3. **Report progress** - For multi-scenario, report after each
4. **Present evidence** - Back findings with trace data, DB state
5. **Offer clear recommendations** - KEEP/REVERT/ITERATE

### For Users

1. **Be specific** - "Test cataloging_with_image" vs "Test everything"
2. **Guide priorities** - Tell Claude which scenarios matter most
3. **Approve incrementally** - Review each fix before applying
4. **Use batch for efficiency** - Test related scenarios together
5. **Track improvement history** - Review what's been fixed

---

**Last Updated**: 2025-01-16
**Next Review**: After Phase 1 implementation
