# DeepAgents Compatibility Note

**Issue**: DeepAgents 0.0.11rc1 has API bug incompatible with LangChain v1
**Solution**: Use stable DeepAgents 0.0.11

## Fix Applied

**File**: `pyproject.toml` line 16

```toml
"deepagents==0.0.11",  # Use stable, not 0.0.11rc1
```

## In Codespace

```bash
cd agents
rm -rf .venv
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e ".[dev]"

# Verify
uv pip show deepagents  # Should show: Version: 0.0.11
```

## Why

- LangChain v1 alpha changes API frequently
- 0.0.11rc1 has regression with `create_agent()` parameter names
- 0.0.11 stable works correctly with LangChain 1.0.0a12+
