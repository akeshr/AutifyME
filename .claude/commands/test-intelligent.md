# Test Intelligent

Execute autonomous testing with AI-powered monitoring.

## Task

Run `intelligent_execute_scenario()` with user-provided scenario and media. AI (gpt-4.1-nano) acts as real user: reads PM messages, responds contextually (answer questions, approve/reject), and triggers debug mode when PM violates architecture (doesn't call save_product_family, gets stuck, repeats).

When debug triggered: analyze trace with `get_trace_overview()` and `get_llm_trace_tree()`, identify root cause (prompt issues, tool configuration, architectural violations), fix, and re-test.

Print execution result (success/failure, trace URL, debug reason if failed) and guide user to trace analysis if issues found.
