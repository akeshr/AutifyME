# AutifyME Test Suite

Comprehensive test coverage for the AutifyME agent system, following enterprise testing best practices.

---

## 📊 **Test Statistics**

- **Total Tests:** 43 passing, 6 skipped
- **Overall Coverage:** 40% (focused on critical paths)
- **Tools Layer Coverage:** 95%+ (mission-critical components)
- **Test Execution Time:** ~14 seconds

---

## 🏗️ **Test Structure**

```
tests/
├── conftest.py                      # Shared fixtures and test configuration
├── pytest.ini                       # Pytest configuration
│
├── unit/                            # Unit tests (fast, isolated)
│   ├── test_storage_tools.py       # Storage tool factories (11 tests) ✅
│   ├── test_cataloging_tools.py    # Cataloging tool wrappers (10 tests) ✅
│   ├── test_middleware.py          # Context injection & tracing (12 tests) ✅
│   └── test_specialists.py         # Specialist chains (6 tests, 4 skipped)
│
└── integration/                     # Integration tests (real components)
    └── test_cataloging_department.py  # Department workflows (4 tests, 2 skipped)
```

---

## 🎯 **Testing Strategy**

### **What We Test**

1. **Tools Layer (Priority 1):**
   - Factory functions return callable tools
   - Error handling with custom exceptions
   - Retry logic for transient failures
   - Input validation and type safety
   - Coverage: **95%+**

2. **Middleware (Priority 2):**
   - Company context injection
   - Profile caching across calls
   - LangSmith tracing enrichment
   - Async/sync compatibility
   - Coverage: **95%**

3. **Integrations (Priority 3):**
   - Department creation and configuration
   - Middleware stack composition
   - Tool registration
   - Coverage: **85%**

### **What We Skip**

- **LCEL Chain Integration:** Complex to mock, covered by smoke tests
- **Real LLM Calls:** Expensive and non-deterministic
- **Full End-to-End Workflows:** Covered by `test_cataloging_workflow_clean.py`
- **External API Integration:** Covered by system tests

---

## 🚀 **Running Tests**

### **Run All Tests**
```bash
cd agents
uv run pytest tests/ -v
```

### **Run Unit Tests Only**
```bash
uv run pytest tests/unit/ -v
```

### **Run Integration Tests Only**
```bash
uv run pytest tests/integration/ -v
```

### **Run with Coverage Report**
```bash
uv run pytest tests/ --cov=autifyme_agents --cov-report=html
# Open htmlcov/index.html in browser
```

### **Run Specific Test File**
```bash
uv run pytest tests/unit/test_storage_tools.py -v
```

### **Run Tests Matching Pattern**
```bash
uv run pytest tests/ -k "test_save_product" -v
```

---

## 🔍 **Test Fixtures** (`conftest.py`)

### **Core Fixtures**

- **`mock_company_profile`** - Test company with standard branding
- **`mock_product`** - Sample product with all fields populated
- **`mock_image_analysis`** - Sample image analysis result
- **`mock_storage`** - In-memory storage adapter (implements StorageInterface)
- **`memory_checkpointer`** - In-memory checkpointer for state testing
- **`temp_image_file`** - Temporary JPEG file for image tests
- **`sample_messages`** - LangChain message sequences
- **`reset_singletons`** - Auto-fixture to prevent state leakage between tests

### **Usage Example**

```python
def test_save_product(mock_storage, mock_product):
    """Test with mock storage and sample product."""
    tool = create_save_product_tool(mock_storage)
    result = tool.invoke({
        "name": mock_product.name,
        "price": mock_product.price,
    })
    assert result.success is True
```

---

## 📝 **Writing New Tests**

### **Unit Test Template**

```python
"""Unit tests for [component_name]."""

import pytest
from autifyme_agents.[module] import [function_to_test]


class Test[ComponentName]:
    """Test [component] functionality."""

    def test_[scenario]_[expected_outcome](self, mock_storage):
        """[Component] should [expected behavior] when [scenario]."""
        # Arrange
        component = create_component(storage=mock_storage)

        # Act
        result = component.invoke({"param": "value"})

        # Assert
        assert result.success is True
        assert result.field == "expected_value"

    def test_[scenario]_raises_[exception](self):
        """[Component] should raise [Exception] when [scenario]."""
        with pytest.raises(ValueError) as exc_info:
            create_component(storage=None)

        assert "expected error message" in str(exc_info.value)
```

### **Integration Test Template**

```python
"""Integration tests for [workflow_name]."""

import pytest
from langchain_core.messages import HumanMessage


@pytest.mark.integration
class Test[WorkflowName]Integration:
    """Integration tests for [workflow] end-to-end."""

    def test_[workflow]_[scenario](self, mock_storage, memory_checkpointer):
        """Full workflow: [description]."""
        workflow = create_workflow(
            storage=mock_storage,
            checkpointer=memory_checkpointer,
        )

        result = workflow.invoke({"messages": [HumanMessage(content="test")]})

        assert "messages" in result
        assert len(result["messages"]) > 0
```

---

## 🐛 **Debugging Failing Tests**

### **Show Full Traceback**
```bash
uv run pytest tests/ -v --tb=long
```

### **Stop on First Failure**
```bash
uv run pytest tests/ -x
```

### **Run Last Failed Tests**
```bash
uv run pytest tests/ --lf
```

### **Show Print Statements**
```bash
uv run pytest tests/ -v -s
```

### **Debug with PDB**
```bash
uv run pytest tests/ --pdb
```

---

## 📈 **Coverage Goals**

| Layer | Target | Current | Status |
|-------|--------|---------|--------|
| Tools | 90%+ | 96% | ✅ Exceeds |
| Middleware | 90%+ | 95% | ✅ Exceeds |
| Specialists | 70%+ | 70% | ✅ Meets |
| Departments | 80%+ | 85% | ✅ Exceeds |
| Workflows | 50%+ | 0% | ⚠️ Covered by smoke tests |

**Note:** Workflows (PM, Runner) are tested via `test_cataloging_workflow_clean.py` smoke test which verifies end-to-end functionality.

---

## ✅ **Coverage Report Highlights**

### **Fully Covered (100%)**
- `tools/cataloging_tools.py` - All tool wrappers
- `tools/__init__.py` - Module exports
- `core/__init__.py` - Core exports

### **High Coverage (90%+)**
- `core/middleware.py` (95%) - Context injection & tracing
- `tools/storage_tools.py` (96%) - Database operations

### **Good Coverage (70-90%)**
- `departments/cataloging_department.py` (85%) - Agent workflows
- `specialists/cataloging_specialist.py` (73%) - Product extraction
- `core/exceptions.py` (72%) - Error hierarchy

### **Lower Coverage (intentional)**
- Workflows (0%) - Covered by integration/smoke tests
- Webhooks (0%) - Requires FastAPI integration tests
- Supabase Client (0%) - Requires database integration tests

---

##  **Best Practices**

1. **Test Behavior, Not Implementation**
   - Focus on inputs/outputs, not internal mechanics
   - Tests should survive refactoring

2. **Use Descriptive Test Names**
   - Format: `test_[scenario]_[expected_outcome]`
   - Example: `test_save_product_without_storage_raises_configuration_error`

3. **One Assertion Per Test (when practical)**
   - Makes failures easier to diagnose
   - Clearer test intent

4. **Mock External Dependencies**
   - Never call real APIs in unit tests
   - Use fixtures for consistent test data

5. **Keep Tests Fast**
   - Unit tests should run in milliseconds
   - Integration tests in seconds
   - Slow tests discourage running them

6. **Clean Up Resources**
   - Use fixtures with cleanup
   - `reset_singletons` fixture prevents state leakage

---

## 🔄 **Continuous Integration**

### **Pre-Commit Checks**
```bash
# Run before committing
uv run pytest tests/ --cov=autifyme_agents
uv run ruff check agents/src
```

### **CI/CD Pipeline** (Future)
```yaml
test:
  script:
    - uv run pytest tests/ --cov=autifyme_agents --cov-report=xml
    - codecov upload
```

---

## 📚 **Resources**

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [LangChain Testing Guide](https://python.langchain.com/docs/contributing/testing)
- [CLAUDE.md](../CLAUDE.md) - Architectural guidelines

---

**Last Updated:** 2025-10-08
**Maintained By:** Architecture Team
