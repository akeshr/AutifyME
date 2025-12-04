# Evaluate Trace

Evaluate a LangSmith trace and improve the workflow.

## Arguments

- `$ARGUMENTS` - LangSmith trace ID (required)

## Task

1. **Invoke the workflow-evaluation skill** to load evaluation context
2. **Analyze the trace** using helpers:
   - `show_tree(trace_id)` for structure
   - `show_llm_calls(trace_id)` for LLM decisions
   - Dig deeper with `show_llm_detail(run_id)` if needed
3. **Evaluate** each LLM call across 6 dimensions (reasoning, decision, tools, context, output, compliance)
4. **Identify root cause** - trace from symptom to actual cause
5. **Fix it** - if prompt change needed, invoke `prompt-engineering` skill first
6. **Verify** - re-run and compare traces

Print findings and recommendations. If actionable fix identified, propose the specific change.
