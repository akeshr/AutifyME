# Deploy Check

Pre-deployment validation checklist.

## Usage

```
/deploy-check
```

## Task

Run comprehensive pre-deployment checks to ensure code quality and readiness.

### 1. Run Linting

```bash
cd agents
echo "=== Running Ruff Linter ==="
uv run ruff check src/

# Check if any issues
if [ $? -eq 0 ]; then
    echo "✅ Linting passed"
else
    echo "❌ Linting failed - fix issues before deploying"
    exit 1
fi
```

### 2. Run Tests

```bash
cd agents
echo "=== Running Test Suite ==="
uv run pytest --cov=autifyme_agents --cov-report=term-missing -v

# Check test results
if [ $? -eq 0 ]; then
    echo "✅ Tests passed"
else
    echo "❌ Tests failed - fix failing tests before deploying"
    exit 1
fi
```

### 3. Check Architecture Compliance

Run architectural validation:
- DeepAgents patterns used correctly
- HITL resume at correct level
- Hexagonal architecture maintained
- No context leakage

```bash
cd agents
echo "=== Checking Architecture ==="

# Check for missing planning tools
if grep -r "write_todos" src/autifyme_agents/workflows/ > /dev/null && \
   grep -r "write_todos" src/autifyme_agents/departments/ > /dev/null; then
    echo "✅ Planning tools present"
else
    echo "⚠️  Missing planning tools in PM or departments"
fi

# Check HITL resume pattern
if grep -A 10 "def resume_workflow" src/autifyme_agents/workflows/orchestration/interrupt_coordinator.py | \
   grep "pm_factory" > /dev/null; then
    echo "✅ HITL resume uses PM level"
else
    echo "❌ HITL resume pattern incorrect"
fi

# Check for context leakage
if ! grep -r "company_profile.*:" src/autifyme_agents/tools/ | grep "def " > /dev/null; then
    echo "✅ No context leakage in tools"
else
    echo "⚠️  Tools may have context leakage"
fi
```

### 4. Verify Environment Variables

```bash
cd agents
echo "=== Checking Environment Variables ==="

uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.core.config import settings

required_vars = [
    'SUPABASE_URL',
    'SUPABASE_ANON_KEY',
    'DATABASE_URL',
    'OPENAI_API_KEY',
    'WHATSAPP_PHONE_NUMBER_ID',
    'WHATSAPP_ACCESS_TOKEN',
]

missing = []
for var in required_vars:
    value = getattr(settings, var, None)
    if not value:
        missing.append(var)
        print(f'❌ Missing: {var}')
    else:
        print(f'✅ Set: {var}')

if missing:
    print(f'\n❌ {len(missing)} required variables missing')
    exit(1)
else:
    print('\n✅ All required variables set')
"
```

### 5. Check for TODOs and FIXMEs

```bash
cd agents
echo "=== Checking for TODOs/FIXMEs ==="

# Find TODOs
TODO_COUNT=$(grep -r "TODO\|FIXME" src/ --include="*.py" | wc -l)

if [ "$TODO_COUNT" -gt 0 ]; then
    echo "⚠️  Found $TODO_COUNT TODOs/FIXMEs:"
    grep -r "TODO\|FIXME" src/ --include="*.py" -n | head -10
    echo "Review these before deploying"
else
    echo "✅ No TODOs/FIXMEs found"
fi
```

### 6. Check Dependencies

```bash
cd agents
echo "=== Checking Dependencies ==="

# Check for unused imports
UNUSED=$(uv run ruff check --select F401 src/ 2>&1 | grep "imported but unused" | wc -l)

if [ "$UNUSED" -gt 0 ]; then
    echo "⚠️  Found $UNUSED unused imports"
    uv run ruff check --select F401 src/ | head -10
else
    echo "✅ No unused imports"
fi

# Check critical dependencies
uv run python -c "
import langchain
import langgraph
import deepagents

print(f'langchain: {langchain.__version__}')
print(f'langgraph: {langgraph.__version__}')
print(f'deepagents: {deepagents.__version__}')
"
```

### 7. Test Database Connections

```bash
cd agents
echo "=== Testing Database Connections ==="

uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')

# Test Supabase
try:
    from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
    storage = SupabaseStorageClient()
    profile = storage.get_company_profile()
    print(f'✅ Supabase connected (company: {profile.name})')
except Exception as e:
    print(f'❌ Supabase error: {str(e)[:100]}')
    exit(1)

# Test PostgreSQL
try:
    from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
    checkpointer = get_checkpointer()
    print('✅ PostgreSQL connected')
except Exception as e:
    print(f'❌ PostgreSQL error: {str(e)[:100]}')
    exit(1)
"
```

### 8. Check API Access

```bash
cd agents
echo "=== Testing API Access ==="

uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')

# Test OpenAI
try:
    from openai import OpenAI
    client = OpenAI()
    models = client.models.list()
    print('✅ OpenAI API accessible')
except Exception as e:
    print(f'❌ OpenAI error: {str(e)[:100]}')
    exit(1)

# Test LangSmith
try:
    from langsmith import Client
    client = Client()
    # Try a simple operation
    runs = list(client.list_runs(limit=1))
    print('✅ LangSmith API accessible')
except Exception as e:
    print(f'⚠️  LangSmith error: {str(e)[:100]}')
    # Not critical, continue
"
```

### 9. Check Git Status

```bash
echo "=== Checking Git Status ==="

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Uncommitted changes:"
    git status --short
    echo "Commit changes before deploying"
else
    echo "✅ Working directory clean"
fi

# Check branch
BRANCH=$(git branch --show-current)
echo "Current branch: $BRANCH"

if [ "$BRANCH" != "main" ]; then
    echo "⚠️  Not on main branch"
fi
```

### 10. Generate Checklist Report

```markdown
## Pre-Deployment Checklist

### Code Quality
- [ ] ✅/❌ Linting passed (ruff)
- [ ] ✅/❌ Tests passed (pytest)
- [ ] ✅/❌ Coverage >70%

### Architecture
- [ ] ✅/❌ DeepAgents patterns correct
- [ ] ✅/❌ HITL resume at PM level
- [ ] ✅/❌ No context leakage
- [ ] ✅/❌ Hexagonal architecture maintained

### Configuration
- [ ] ✅/❌ All environment variables set
- [ ] ✅/❌ Supabase connected
- [ ] ✅/❌ PostgreSQL connected
- [ ] ✅/❌ OpenAI API accessible

### Code Hygiene
- [ ] ⚠️/✅ TODOs reviewed: [count]
- [ ] ✅/❌ No unused imports
- [ ] ✅/❌ Dependencies up to date

### Git
- [ ] ✅/❌ Working directory clean
- [ ] ✅/❌ On correct branch
- [ ] ✅/❌ Changes committed
- [ ] ✅/❌ Tests pass in CI

### Blockers
[List any issues that must be fixed before deploy]

### Warnings
[List any non-critical issues to monitor]

---

**Deploy Status**: ✅ Ready / ⚠️ With Caution / ❌ Not Ready

**Recommendation**: [Deploy / Fix issues first / Review warnings]
```

## Quick Deploy Check

For rapid validation:
```bash
cd agents && \
uv run ruff check src/ && \
uv run pytest -q && \
echo "✅ Quick checks passed - ready to deploy"
```

## Notes

- Run full check before merging to main
- Quick check sufficient for hotfixes
- Always test in staging first
- Monitor logs after deployment
