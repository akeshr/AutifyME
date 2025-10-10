"""
Custom exception hierarchy for AutifyME agents.

Following LangChain v1 patterns: exceptions should be specific, descriptive,
and carry enough context for proper error handling and user feedback.

Design Philosophy:
- Exceptions are for exceptional situations (not control flow)
- Include actionable error messages
- Preserve original exceptions for debugging
- Domain-specific exceptions help error handling at different layers
"""

from typing import Any


class AutifyMEError(Exception):
    """
    Base exception for all AutifyME-specific errors.
    
    All custom exceptions in the system inherit from this, making it easy
    to catch AutifyME errors specifically while letting system errors propagate.
    """
    pass


# ============================================================================
# Tool & Integration Errors
# ============================================================================

class ToolExecutionError(AutifyMEError):
    """
    Raised when a tool fails to execute successfully.
    
    This is the base class for all tool-related errors. Tools should catch
    external API errors and raise this (or a subclass) with context.
    """
    
    def __init__(self, message: str, tool_name: str, original_error: Exception | None = None):
        """
        Initialize with context about the tool failure.
        
        Args:
            message: Human-readable error description
            tool_name: Name of the tool that failed
            original_error: The underlying exception that caused this failure
        """
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(f"[{tool_name}] {message}")


class StorageError(ToolExecutionError):
    """Raised when database/storage operations fail."""
    
    def __init__(self, message: str, operation: str, original_error: Exception | None = None):
        """
        Initialize with storage operation context.
        
        Args:
            message: Error description
            operation: The storage operation that failed (e.g., "save_product", "get_company_profile")
            original_error: The underlying exception
        """
        self.operation = operation
        super().__init__(message, tool_name=f"storage.{operation}", original_error=original_error)


class ImageAnalysisError(ToolExecutionError):
    """Raised when image analysis (Vision API) fails."""
    
    def __init__(self, message: str, image_url: str, original_error: Exception | None = None):
        """
        Initialize with image analysis context.
        
        Args:
            message: Error description
            image_url: The image URL that failed to analyze
            original_error: The underlying exception
        """
        self.image_url = image_url
        super().__init__(message, tool_name="analyze_product_image", original_error=original_error)


class ExternalAPIError(ToolExecutionError):
    """Raised when external API calls fail (network, timeout, rate limit, etc.)."""
    
    def __init__(
        self, 
        message: str, 
        tool_name: str,
        api_name: str,
        status_code: int | None = None,
        is_retryable: bool = True,
        original_error: Exception | None = None
    ):
        """
        Initialize with external API error context.
        
        Args:
            message: Error description
            tool_name: Name of the tool making the API call
            api_name: Name of the external API (e.g., "Supabase", "OpenAI Vision")
            status_code: HTTP status code if applicable
            is_retryable: Whether this error is transient and can be retried
            original_error: The underlying exception
        """
        self.api_name = api_name
        self.status_code = status_code
        self.is_retryable = is_retryable
        
        status_info = f" (HTTP {status_code})" if status_code else ""
        retry_info = " [RETRYABLE]" if is_retryable else " [NOT RETRYABLE]"
        full_message = f"{api_name} API error{status_info}: {message}{retry_info}"
        
        super().__init__(full_message, tool_name=tool_name, original_error=original_error)


# ============================================================================
# Validation & Data Errors
# ============================================================================

class ValidationError(AutifyMEError):
    """
    Raised when input validation fails.
    
    This indicates the input data doesn't meet requirements (schema, business rules, etc.).
    These are typically non-retryable and require user correction.
    """
    
    def __init__(self, message: str, field: str | None = None, value: Any = None):
        """
        Initialize with validation error context.
        
        Args:
            message: Error description
            field: The field that failed validation
            value: The invalid value (be careful with sensitive data!)
        """
        self.field = field
        self.value = value
        
        field_info = f" (field: {field})" if field else ""
        super().__init__(f"Validation failed{field_info}: {message}")


class DataNotFoundError(AutifyMEError):
    """
    Raised when required data is not found.
    
    Example: Company profile not found, product not found, etc.
    """
    
    def __init__(self, resource_type: str, identifier: str):
        """
        Initialize with data not found context.
        
        Args:
            resource_type: Type of resource that wasn't found (e.g., "Company", "Product")
            identifier: The identifier used in the lookup (e.g., company_id, product_id)
        """
        self.resource_type = resource_type
        self.identifier = identifier
        super().__init__(f"{resource_type} not found: {identifier}")


# ============================================================================
# Configuration & System Errors
# ============================================================================

class ConfigurationError(AutifyMEError):
    """
    Raised when configuration is missing or invalid.
    
    Example: Missing API keys, invalid database connection strings, etc.
    These typically indicate deployment/environment issues.
    """
    
    def __init__(self, message: str, config_key: str | None = None):
        """
        Initialize with configuration error context.
        
        Args:
            message: Error description
            config_key: The configuration key that's missing or invalid
        """
        self.config_key = config_key
        key_info = f" (key: {config_key})" if config_key else ""
        super().__init__(f"Configuration error{key_info}: {message}")


# ============================================================================
# Agent & Workflow Errors
# ============================================================================

class AgentExecutionError(AutifyMEError):
    """
    Raised when an agent encounters an unrecoverable error during execution.
    
    This is typically raised by agent-level logic, not individual tools.
    """
    
    def __init__(self, message: str, agent_name: str, original_error: Exception | None = None):
        """
        Initialize with agent execution context.
        
        Args:
            message: Error description
            agent_name: Name of the agent that failed
            original_error: The underlying exception
        """
        self.agent_name = agent_name
        self.original_error = original_error
        super().__init__(f"[{agent_name}] {message}")


class WorkflowInterruptedError(AutifyMEError):
    """
    Raised when a workflow is interrupted (HITL approval denied, timeout, etc.).
    
    This is not always an error condition - it can be a normal part of HITL workflows.
    """
    
    def __init__(self, message: str, workflow_id: str, reason: str):
        """
        Initialize with workflow interruption context.
        
        Args:
            message: Error description
            workflow_id: ID of the interrupted workflow
            reason: Reason for interruption (e.g., "approval_denied", "timeout")
        """
        self.workflow_id = workflow_id
        self.reason = reason
        super().__init__(f"Workflow {workflow_id} interrupted ({reason}): {message}")

