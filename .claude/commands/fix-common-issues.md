# Fix Common Issues

Auto-apply fixes for known issues.

## Usage

```
/fix-common-issues [issue-type]
```

**Types**: `planning-tools`, `hitl-resume`, `base64`, `imports`, `all`

## Task

Automatically apply fixes for common architectural issues.

### 1. Add Missing Planning Tools

**Issue**: PM or departments missing `write_todos`.

**Fix**:
```bash
cd agents

# Fix PM
echo "Adding write_todos to PM..."

# Check if already present
if ! grep -q "from deepagents.tools import write_todos" src/autifyme_agents/workflows/project_manager.py; then
    # Add import
    sed -i.bak '/from deepagents import create_deep_agent/a\
from deepagents.tools import write_todos' src/autifyme_agents/workflows/project_manager.py

    # Add to tools list (requires manual review of context)
    echo "⚠️  Import added - review tools list manually"
fi

# Fix departments
if ! grep -q "from deepagents.tools import write_todos" src/autifyme_agents/departments/cataloging_department.py; then
    sed -i.bak '/from deepagents import create_deep_agent/a\
from deepagents.tools import write_todos' src/autifyme_agents/departments/cataloging_department.py

    echo "⚠️  Import added - add to tools list manually"
fi

echo "✅ Planning tool imports added"
```

### 2. Fix HITL Resume Pattern

**Issue**: HITL resume creates fresh department instead of resuming PM.

**Current (wrong)**:
```python
def resume_workflow(...):
    dept = create_cataloging_department(...)
    dept.stream(command, config={"thread_id": thread_id, "checkpoint_ns": "..."})
```

**Fixed (correct)**:
```python
def resume_workflow(..., pm_factory: Callable):
    pm = pm_factory()
    pm.stream(command, config={"thread_id": thread_id})
```

**Auto-fix**:
```bash
cd agents

# Check if wrong pattern exists
if grep -A 20 "def resume_workflow" src/autifyme_agents/workflows/orchestration/interrupt_coordinator.py | \
   grep "create_cataloging_department" > /dev/null; then

    echo "⚠️  Found incorrect HITL resume pattern"
    echo "Manual fix required - see interrupt_coordinator.py"
    echo ""
    echo "Change from:"
    echo "  dept = create_department(...)"
    echo "  dept.stream(command, ...)"
    echo ""
    echo "To:"
    echo "  pm = pm_factory()"
    echo "  pm.stream(command, config={'configurable': {'thread_id': thread_id}})"
else
    echo "✅ HITL resume pattern correct"
fi
```

### 3. Fix Base64 Conversion

**Issue**: Local file paths passed to Vision API without conversion.

**Fix**:
```bash
cd agents

# Check if conversion function exists
if ! grep -q "_encode_image_to_data_uri" src/autifyme_agents/specialists/image_analysis_specialist.py; then

    echo "Adding base64 conversion function..."

    # Create backup
    cp src/autifyme_agents/specialists/image_analysis_specialist.py \
       src/autifyme_agents/specialists/image_analysis_specialist.py.bak

    # Add function (simplified - manual review recommended)
    cat << 'EOF' >> /tmp/base64_function.py
def _encode_image_to_data_uri(image_path: str) -> str:
    """Convert local image to base64 data URI."""
    import base64
    from pathlib import Path

    path = Path(image_path)
    ext = path.suffix.lower()
    mime_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
    }.get(ext, 'image/jpeg')

    with open(path, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')

    return f"data:{mime_type};base64,{encoded}"
EOF

    echo "⚠️  Function template created in /tmp/base64_function.py"
    echo "   Add to image_analysis_specialist.py manually"
else
    echo "✅ Base64 conversion function exists"
fi

# Check if conversion is used
if ! grep -q "if image_url and not image_url.startswith" src/autifyme_agents/specialists/image_analysis_specialist.py; then
    echo "⚠️  Add conversion check before Vision API call:"
    echo "   if image_url and not image_url.startswith(('http://', 'https://', 'data:')):"
    echo "       image_url = _encode_image_to_data_uri(image_url)"
fi
```

### 4. Fix Unused Imports

**Issue**: Unused imports creating clutter.

**Auto-fix**:
```bash
cd agents
echo "Fixing unused imports..."

uv run ruff check --select F401 --fix src/

if [ $? -eq 0 ]; then
    echo "✅ Unused imports removed"
else
    echo "❌ Some imports couldn't be auto-fixed"
fi
```

### 5. Fix Context Leakage

**Issue**: Tools accepting company_profile as parameter.

**Check**:
```bash
cd agents

echo "Checking for context leakage in tools..."

# Find tools with company_profile parameter
LEAKY_TOOLS=$(grep -r "def.*company_profile.*:" src/autifyme_agents/tools/ | grep -v "__init__")

if [ -n "$LEAKY_TOOLS" ]; then
    echo "⚠️  Found tools with context leakage:"
    echo "$LEAKY_TOOLS"
    echo ""
    echo "Fix: Remove company_profile parameter, use middleware instead"
else
    echo "✅ No context leakage in tools"
fi
```

### 6. Fix Tool Exception Pattern

**Issue**: Tools raising generic exceptions instead of ToolException.

**Check and suggest**:
```bash
cd agents

echo "Checking tool error handling..."

# Find tools without ToolException
for file in src/autifyme_agents/tools/*.py; do
    if grep -q "raise.*Error\|raise.*Exception" "$file" && \
       ! grep -q "ToolException" "$file"; then
        echo "⚠️  $file may need ToolException"
    fi
done

echo ""
echo "Fix: Import and use ToolException"
echo "  from langchain.agents.exceptions import ToolException"
echo "  raise ToolException('Error message')"
```

### 7. Fix Prompt Hardcoding

**Issue**: Prompts hardcoded instead of loaded from files.

**Check**:
```bash
cd agents

echo "Checking for hardcoded prompts..."

# Find multiline strings that look like prompts
HARDCODED=$(grep -r "\"\"\"You are" src/autifyme_agents/workflows/ src/autifyme_agents/departments/)

if [ -n "$HARDCODED" ]; then
    echo "⚠️  Found potential hardcoded prompts:"
    echo "$HARDCODED"
    echo ""
    echo "Fix: Move to prompts/ directory and use load_prompt()"
else
    echo "✅ No hardcoded prompts found"
fi
```

### 8. Generate Fix Report

```markdown
## Common Issues Fix Report

### ✅ Fixed Automatically

#### Unused Imports
- Removed [count] unused imports
- Files affected: [list]

### ⚠️  Requires Manual Review

#### Planning Tools
- Added imports to:
  - [ ] project_manager.py
  - [ ] cataloging_department.py
- **Action**: Add to tools list manually

#### HITL Resume Pattern
- **File**: interrupt_coordinator.py
- **Issue**: Creates fresh department
- **Fix**: Use pm_factory to resume at PM level
- **Status**: Manual fix required

#### Base64 Conversion
- **File**: image_analysis_specialist.py
- **Issue**: Missing conversion for local files
- **Template**: Created in /tmp/base64_function.py
- **Status**: Add function and usage

### ❌ Issues Detected (Not Fixed)

#### Context Leakage
**Files**: [list]
- Tools accept company_profile directly
- Fix: Remove parameter, use middleware

#### Tool Exceptions
**Files**: [list]
- Tools raise generic exceptions
- Fix: Use ToolException from langchain.agents

#### Hardcoded Prompts
**Files**: [list]
- Prompts embedded in code
- Fix: Move to prompts/ directory

### Next Steps

1. Review and complete manual fixes
2. Test changes thoroughly
3. Run /deploy-check before merging
4. Update documentation if patterns changed

---

**Fixes Applied**: [count]
**Manual Fixes Needed**: [count]
**Issues Detected**: [count]
```

## Notes

- Always review auto-fixes before committing
- Test after applying fixes
- Some issues require manual intervention
- Run linting after fixes
- Update tests if behavior changes
