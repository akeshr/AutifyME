# Analyze LangSmith Traces

Analyze one or more LangSmith trace IDs to identify issues and patterns.

## Usage

```
/analyze-traces <trace-id-1> [trace-id-2] [trace-id-3] ...
```

## Task

You are analyzing LangSmith traces for the AutifyME agentic workflow system. For each trace ID provided:

1. **Dump the trace**:
   - Run: `timeout 120 uv run python --env-path ../.env scripts/dump_langsmith_thread.py --run-id <trace-id> > ../trace_<trace-id>.txt`
   - Save output to project root with trace ID in filename

2. **Analyze each trace** for common issues:
   - **HITL Errors**: GeneratorExit, interrupt handling failures, resume issues
   - **Image Specialist Issues**: Hallucinations, wrong image analysis, local file path problems
   - **Tool Coordination**: Missing planning tools, parallel tool calls without dependencies
   - **PM Delegation**: Errors like "invoked agent of type X, only allowed types are ['general-purpose']"
   - **Tool Call Errors**: Missing tool calls, incorrect arguments, invalid tool names
   - **State Issues**: Checkpoint errors, orphaned state, invalid chat history

3. **Extract key information**:
   - User input (text + media)
   - Workflow status (success/error/interrupted)
   - Tool calls made (image_analysis_specialist, cataloging_specialist, save_product)
   - Actual vs expected behavior
   - Error messages and stack traces

4. **Present findings**:
   ```markdown
   # Trace Analysis Summary

   ## Trace 1: <trace-id>

   **Status**: [Error/Success/Interrupted]
   **Issue**: [Brief description]

   **User Input**:
   - Text: "..."
   - Media: [image/video/none]

   **Tool Calls**:
   - image_analysis_specialist: [called/not called] - [result/error]
   - cataloging_specialist: [called/not called] - [result/error]
   - save_product: [called/not called] - [result/error]

   **Root Cause**:
   [Detailed explanation]

   **Evidence**:
   [Relevant trace excerpts]

   **Recommendation**:
   [Fix to apply]

   ---

   ## Trace 2: <trace-id>
   ...

   ---

   ## Cross-Trace Patterns

   [Common issues across multiple traces]
   ```

5. **Focus on architectural issues**:
   - Are DeepAgents planning tools being used?
   - Is HITL resume happening at correct level (PM vs department)?
   - Are tool results being passed correctly between steps?
   - Are local file paths being converted to base64 for Vision API?

## Important

- Run dumps in parallel if multiple traces (use separate Bash calls)
- Read each trace file completely before analysis
- Compare traces to identify systemic vs one-off issues
- Reference specific line numbers when citing evidence
- Suggest concrete fixes aligned with DeepAgents best practices
