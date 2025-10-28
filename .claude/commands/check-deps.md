# Check Deps

Validate dependency versions and compatibility.

## Task

Check for unused imports (auto-fixable with ruff), verify critical version constraints (langchain v1, langgraph v1, deepagents, pydantic v2), detect version conflicts, identify reimplemented features that could use built-in library features (write_todos, checkpointer, ToolException, etc), test critical imports, check for security issues, and verify DeepAgents feature adoption.

Generate dependency report with installed versions (with alpha/RC warnings), issues found, recommendations (remove unused, replace custom code, pin versions, verify APIs), and missed opportunities for using framework features.