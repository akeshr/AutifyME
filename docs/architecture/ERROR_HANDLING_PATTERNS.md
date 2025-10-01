# Error Handling Patterns - LangChain v1

**Last Updated:** October 1, 2025  
**Status:** Production Implementation Guide

---

## Executive Summary

This document captures the **official LangChain v1 error handling patterns** discovered through research of the framework's source code and documentation. These patterns are now implemented in AutifyME and represent production-grade best practices.

**Key Principle:** Error handling in LangChain v1 is **layered** - tools handle errors at the lowest level, retry logic manages transient failures, and agents handle errors through reasoning.

---

## The LangChain v1 Error Handling Philosophy

### **What Changed from v0 to v1:**

1. **No More Infinite Loops**: v0 would retry failed tools indefinitely. v1 raises exceptions by default.
2. **Structured Exceptions**: Custom exception classes with context (not generic `Exception`)
3. **Tool-Level Responsibility**: Tools are responsible for catching and classifying their own errors
4. **Agent Self-Correction**: Agents see error messages and can reason about recovery

### **The Three-Layer Pattern:**

```
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Agent Reasoning                                │
│ - Sees tool errors as messages                          │
│ - Can retry with different args, use alt tools, report  │
└─────────────────────────────────────────────────────────┘
                        ▲
                        │ (error message)
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Retry Logic (tenacity)                         │
│ - Automatic retry for transient failures                │
│ - Exponential backoff                                   │
│ - Only retry specific exception types                   │
└─────────────────────────────────────────────────────────┘
                        ▲
                        │ (exception)
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Tool Error Handling                            │
│ - Catch external API errors                             │
│ - Classify: retryable vs. permanent                     │
│ - Raise custom exceptions with context                  │
└─────────────────────────────────────────────────────────┘
```

---

## Pattern 1: Custom Exception Hierarchy

### **Why:**
- Standard `Exception` doesn't carry enough context
- Different errors need different handling strategies
- Enables selective retry logic

### **Implementation:**

```python
# core/exceptions.py

class AutifyMEError(Exception):
    """Base for all custom errors"""
    pass

class ToolExecutionError(AutifyMEError):
    """Base for tool failures"""
    def __init__(self, message: str, tool_name: str, original_error: Exception | None = None):
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(f"[{tool_name}] {message}")

class ExternalAPIError(ToolExecutionError):
    """Transient API errors (network, timeout, rate limit)"""
    def __init__(self, ..., is_retryable: bool = True):
        self.is_retryable = is_retryable
        ...

class StorageError(ToolExecutionError):
    """Permanent storage errors (validation, not found)"""
    pass
```

### **Benefits:**
- ✅ Context-rich error messages
- ✅ Selective exception catching (`except ExternalAPIError`)
- ✅ Preserves original exception for debugging
- ✅ Easy to add new error types

---

## Pattern 2: Tool-Level Error Classification

### **Why:**
- Tools know their own failure modes
- Different errors require different responses
- Enables intelligent retry logic

### **Implementation:**

```python
from langchain_core.tools import tool
from autifyme_agents.core.exceptions import ExternalAPIError, StorageError

@tool
def save_product(**kwargs) -> Product:
    """Save product with error handling."""
    try:
        return _storage_client.save_product(Product(**kwargs))
    except Exception as e:
        # Classify the error
        if "timeout" in str(e).lower() or "connection" in str(e).lower():
            # Transient network error - can retry
            raise ExternalAPIError(
                message=str(e),
                tool_name="save_product",
                api_name="Supabase",
                is_retryable=True,  # KEY: Marks as retryable
                original_error=e
            )
        else:
            # Permanent error (validation, schema, etc.) - don't retry
            raise StorageError(
                message=f"Failed to save product: {str(e)}",
                operation="save_product",
                original_error=e
            )
```

### **Error Classification Guide:**

| Error Type | Is Retryable? | Examples |
|------------|---------------|----------|
| Network timeout | ✅ Yes | `ConnectionTimeout`, `ReadTimeout` |
| Rate limit | ✅ Yes | `429 Too Many Requests` |
| Server error | ✅ Yes | `500 Internal Server Error`, `503 Service Unavailable` |
| Validation error | ❌ No | `400 Bad Request`, Pydantic `ValidationError` |
| Not found | ❌ No | `404 Not Found`, `NoResultFound` |
| Authentication | ❌ No | `401 Unauthorized`, `403 Forbidden` |

---

## Pattern 3: Automatic Retry with Tenacity

### **Why:**
- Transient failures (network glitches) are common
- Manual retry logic is error-prone
- Exponential backoff prevents API hammering

### **Implementation:**

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

logger = logging.getLogger(__name__)

@tool
@retry(
    stop=stop_after_attempt(3),                     # Max 3 attempts
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 2s, 4s, 8s
    retry=retry_if_exception_type(ExternalAPIError),     # Only retry this type
    before_sleep=before_sleep_log(logger, logging.WARNING),  # Log before retry
    reraise=True                                     # Re-raise after all attempts fail
)
def save_product(**kwargs) -> Product:
    """Tool with automatic retry."""
    ...
```

### **Retry Configuration Explained:**

```python
stop=stop_after_attempt(3)
# Attempt 1: Immediate
# Attempt 2: After 2s
# Attempt 3: After 4s
# Total: 3 attempts over ~6 seconds

wait=wait_exponential(multiplier=1, min=2, max=10)
# Wait time: min(max, 2^attempt * multiplier)
# Attempt 1 → 0: 0s (immediate)
# Attempt 2 → 1: 2s
# Attempt 3 → 2: 4s

retry=retry_if_exception_type(ExternalAPIError)
# ONLY retry ExternalAPIError
# Other exceptions (StorageError, ValidationError) fail immediately
```

### **Benefits:**
- ✅ Handles transient failures automatically
- ✅ Exponential backoff prevents API abuse
- ✅ Selective retry (only for retryable errors)
- ✅ Logging shows retry attempts
- ✅ Configurable per tool

---

## Pattern 4: Agent-Level Error Handling

### **Why:**
- Agents can reason about errors
- Enables self-correction strategies
- Provides graceful degradation

### **Implementation:**

```python
# departments/cataloging_department.py

def create_cataloging_department() -> Runnable:
    """
    Error Handling Strategy:
        Layer 1 (Tools): Catch API errors, raise custom exceptions
        Layer 2 (Retry): Automatic retry on ExternalAPIError
        Layer 3 (Agent): See error message, decide recovery strategy
    """
    tools = [
        analyze_product_image,  # Has retry logic
        save_product,           # Has retry logic + custom exceptions
        get_company_profile,    # Has retry logic + custom exceptions
    ]
    
    agent = create_agent(llm, tools, prompt=prompt)
    return agent
```

### **What Happens When a Tool Fails:**

1. **Tool raises exception** (e.g., `StorageError`)
2. **LangChain catches it** and converts to a `ToolMessage`
3. **Agent sees the error message** in conversation history
4. **Agent can:**
   - Retry the tool with different arguments
   - Try an alternative approach
   - Ask the user for help
   - Report the failure gracefully

**Example Flow:**

```
User: "Save this product: Name='', Price=0"
  ↓
Agent calls: save_product(name='', price=0)
  ↓
Tool raises: ValidationError("Product name cannot be empty")
  ↓
Agent sees: ToolMessage(content="Error: Product name cannot be empty")
  ↓
Agent responds: "I cannot save a product with an empty name. Please provide a valid product name."
```

---

## Pattern 5: ToolNode Error Handling (Advanced)

### **When to Use:**
- Building custom LangGraph graphs (not using `create_agent`)
- Need fine-grained control over tool execution
- Want to customize error message format

### **Implementation:**

```python
from langgraph.prebuilt import ToolNode

# Wrap tools in ToolNode with error handling
tool_node = ToolNode(
    tools=[save_product, get_company_profile],
    name="storage_tools",
    handle_tool_errors=True  # Catch all errors, return as ToolMessages
)

# Or with custom error handler
def custom_error_handler(e: Exception) -> str:
    return f"Custom error: {type(e).__name__}: {str(e)}"

tool_node = ToolNode(
    tools=[...],
    handle_tool_errors=custom_error_handler
)
```

### **ToolNode Error Handling Options:**

```python
handle_tool_errors=True
# Default: Catch all errors, return standard error message

handle_tool_errors="Custom error message for all failures"
# String: Catch all errors, return this message

handle_tool_errors=custom_error_handler
# Callable: Catch all errors, call function to generate message

handle_tool_errors=(ValueError, KeyError)
# Tuple: Only catch these exception types

handle_tool_errors=False
# Disable: Let exceptions propagate (crashes agent)
```

### **Note:**
`create_agent()` doesn't support passing `ToolNode` directly in the current version. Use tool-level error handling instead.

---

## Pattern 6: Fallback Strategies

### **Why:**
- Provides alternative paths when primary approach fails
- Increases system resilience
- Enables graceful degradation

### **Implementation:**

```python
from langchain_core.runnables import Runnable

# Create primary and fallback chains
primary_chain = llm_with_tools | tool_executor
fallback_chain = better_llm | alternative_tool_executor

# Add fallback
resilient_chain = primary_chain.with_fallbacks(
    [fallback_chain],
    exceptions_to_handle=(ExternalAPIError,)  # Only fallback on these errors
)
```

### **Use Cases:**

1. **Model Fallback**: Primary LLM fails → Use backup LLM
2. **Tool Fallback**: Vision API fails → Use alternative image analysis service
3. **Strategy Fallback**: Structured extraction fails → Use unstructured parsing

---

## Best Practices

### **✅ DO:**

1. **Create domain-specific exceptions** with context
2. **Classify errors as retryable vs. permanent**
3. **Use automatic retry for transient failures**
4. **Log errors with context** (tool name, request ID, etc.)
5. **Preserve original exceptions** for debugging
6. **Test error handling** with simulated failures

### **❌ DON'T:**

1. **Don't use generic `Exception`** - too broad, no context
2. **Don't retry validation errors** - they'll never succeed
3. **Don't use infinite retries** - can cause cascading failures
4. **Don't swallow exceptions** - always log or propagate
5. **Don't add error handling to agent prompts** - let tools handle it
6. **Don't bypass retry logic** - it's there for a reason

---

## Testing Error Handling

### **Simulated Failure Testing:**

```python
# Test transient failures
def test_retry_on_timeout():
    """Verify retry logic works for timeouts."""
    with mock.patch('_storage_client.save_product') as mock_save:
        # First 2 calls timeout, 3rd succeeds
        mock_save.side_effect = [
            ConnectionTimeout("Timeout 1"),
            ConnectionTimeout("Timeout 2"),
            Product(id="123", name="Test")
        ]
        
        result = save_product(name="Test", price=10.0)
        assert result.id == "123"
        assert mock_save.call_count == 3  # Retried 2 times

# Test permanent failures
def test_no_retry_on_validation():
    """Verify validation errors don't retry."""
    with mock.patch('_storage_client.save_product') as mock_save:
        mock_save.side_effect = ValidationError("Invalid data")
        
        with pytest.raises(StorageError):
            save_product(name="", price=-1)
        
        assert mock_save.call_count == 1  # No retry
```

---

## Migration from v0 to v1

### **Breaking Changes:**

| v0 Behavior | v1 Behavior | Migration |
|-------------|-------------|-----------|
| Infinite retries | Raises exception | Add explicit retry logic |
| Generic exceptions | Custom exceptions | Create exception hierarchy |
| Tool-level try/except | Structured error handling | Classify and raise custom exceptions |
| No context | Rich context | Include tool name, error type, original error |

### **Migration Checklist:**

- [ ] Create custom exception hierarchy
- [ ] Add error classification to all tools
- [ ] Add retry decorators for transient failures
- [ ] Update agent creation (no more `handle_errors` parameter)
- [ ] Test with simulated failures
- [ ] Update documentation

---

## Real-World Examples

### **Example 1: Storage Tool with Full Error Handling**

```python
@tool
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(ExternalAPIError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def save_product(**kwargs) -> Product:
    """Save product with comprehensive error handling."""
    # Configuration check
    if _storage_client is None:
        raise ConfigurationError(
            "Storage client not initialized",
            config_key="storage_client"
        )
    
    try:
        product = Product(**kwargs)
        return _storage_client.save_product(product)
    
    except ValidationError as e:
        # Pydantic validation failed - permanent error
        raise ValidationError(
            f"Invalid product data: {str(e)}",
            field=e.errors()[0]['loc'][0] if e.errors() else None,
            value=kwargs
        )
    
    except Exception as e:
        # Classify unknown errors
        error_str = str(e).lower()
        
        if any(term in error_str for term in ["timeout", "connection", "network"]):
            # Transient network error - retryable
            raise ExternalAPIError(
                message=str(e),
                tool_name="save_product",
                api_name="Supabase",
                status_code=getattr(e, 'status_code', None),
                is_retryable=True,
                original_error=e
            )
        
        # Permanent error - don't retry
        raise StorageError(
            message=f"Failed to save product: {str(e)}",
            operation="save_product",
            original_error=e
        )
```

---

## Resources

### **Official Documentation:**
- [LangChain v1 Release Notes](https://docs.langchain.com/oss/python/releases/langchain-v1)
- [LangChain Error Codes](https://python.langchain.com/docs/troubleshooting/errors/)
- [LangGraph ToolNode API](https://langchain-ai.github.io/langgraph/reference/prebuilt/#toolnode)

### **Internal Documentation:**
- [`LANGCHAIN_V1_FEATURES.md`](./LANGCHAIN_V1_FEATURES.md) - Full v1 feature guide
- [`IMPLEMENTATION_STATUS.md`](../../IMPLEMENTATION_STATUS.md) - Current implementation status
- [`core/exceptions.py`](../../agents/src/autifyme_agents/core/exceptions.py) - Exception hierarchy

### **External Resources:**
- [Tenacity Documentation](https://tenacity.readthedocs.io/)
- [Pydantic Error Handling](https://docs.pydantic.dev/latest/errors/errors/)

---

**Last Updated:** October 1, 2025  
**Next Review:** After implementing error handling in all tools

