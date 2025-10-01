# Output Transformation Pattern

**Problem:** LangGraph returns `{"messages": [...]}`, Project Manager needs just the final output.  
**Solution:** Pipe through `RunnableLambda` to extract `messages[-1].content`

## Implementation

```python
from langchain_core.runnables import RunnableLambda

def create_department(checkpointer):
    agent_graph = create_agent(llm, tools, prompt, checkpointer)
    
    def extract_final_output(state: dict) -> dict:
        if "messages" not in state:
            return state  # Pass through streaming chunks
        return {"output": state["messages"][-1].content}
    
    # IMPORTANT: Pipe first, THEN configure (for LangSmith naming)
    piped = agent_graph | RunnableLambda(extract_final_output)
    return piped.with_config({"run_name": "DepartmentName", ...})
```

## Key Points

- `.with_config()` **must** come after piping (preserves name in LangSmith)
- Handle streaming by passing through non-message chunks
- Full state preserved in checkpointer (multi-turn works)
- Pipe pattern integrates with LangSmith tracing

**Example:** `agents/src/autifyme_agents/departments/cataloging_department.py`
