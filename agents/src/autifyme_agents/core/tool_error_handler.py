"""Centralized tool error handling for agent-friendly error responses.

Converts exceptions to structured dict responses that enable agents to reason
about errors and retry intelligently, rather than crashing workflows.

Design Philosophy:
- Tools NEVER raise exceptions (ToolException breaks agent reasoning)
- Tools ALWAYS return {"success": bool, ...} dicts
- Error responses include actionable guidance for agents
- Consistent error format across all tools
"""

from typing import Any

# Error type classification rules
ERROR_PATTERNS = {
    # Access control errors (check before generic table errors)
    "access denied": {
        "type": "ACCESS_DENIED",
        "action": "Access denied. You don't have permission for this operation. Request access from administrator.",
    },
    "permission": {
        "type": "ACCESS_DENIED",
        "action": "Permission denied. Verify you have required access rights.",
    },

    # Database/Storage errors
    "table": {
        "type": "TABLE_ERROR",
        "action": "Database table access failed. Verify table name or contact administrator.",
    },
    "relation": {
        "type": "INVALID_RELATION",
        "action": "Verify relation syntax. Use PostgREST format. Check schema for foreign keys.",
    },
    "column": {
        "type": "INVALID_COLUMN",
        "action": "Verify column names match schema. Query schema first for available columns.",
    },
    "foreign key": {
        "type": "MISSING_REFERENCE",
        "action": "Ensure referenced entities exist. Create parent entities first.",
    },
    "unique constraint": {
        "type": "CONSTRAINT_VIOLATION",
        "action": "Check for duplicate values in unique fields. Query existing data first.",
    },
    "syntax": {
        "type": "INVALID_SYNTAX",
        "action": "Check query syntax. Verify filter format, search patterns, and relations.",
    },

    # Network/API errors
    "timeout": {
        "type": "CONNECTION_ERROR",
        "action": "Network timeout. Retry query. If persistent, inform user.",
    },
    "connection": {
        "type": "CONNECTION_ERROR",
        "action": "Network connectivity issue. Retry operation. Check internet connection.",
    },
    "rate limit": {
        "type": "RATE_LIMIT_ERROR",
        "action": "API rate limit exceeded. Wait briefly and retry. Consider batch processing.",
    },
    "429": {
        "type": "RATE_LIMIT_ERROR",
        "action": "Too many requests. Wait and retry. Implement backoff strategy.",
    },

    # Permission/Access errors
    "permission": {
        "type": "ACCESS_ERROR",
        "action": "Insufficient permissions. Contact administrator or use alternative approach.",
    },
    "access": {
        "type": "ACCESS_ERROR",
        "action": "Access denied. Verify credentials or contact administrator.",
    },
    "auth": {
        "type": "ACCESS_ERROR",
        "action": "Authentication failed. Check API credentials or refresh token.",
    },

    # File/Image errors
    "not found": {
        "type": "NOT_FOUND",
        "action": "Resource not found. Verify path/identifier. Check if resource exists.",
    },
    "file not found": {
        "type": "FILE_NOT_FOUND",
        "action": "File does not exist. Verify file path. Check if file was created/downloaded.",
    },
    "invalid": {
        "type": "INVALID_INPUT",
        "action": "Invalid input format or value. Verify input matches expected format.",
    },
    "corrupt": {
        "type": "INVALID_FILE",
        "action": "File corrupted or unsupported. Request file again. Verify file integrity.",
    },

    # API-specific errors
    "openai": {
        "type": "API_ERROR",
        "action": "OpenAI API error. Retry request. If persistent, contact administrator.",
    },
    "supabase": {
        "type": "API_ERROR",
        "action": "Supabase API error. Retry request. Check database status.",
    },
    "quota": {
        "type": "QUOTA_EXCEEDED",
        "action": "API quota exceeded. Wait for quota reset or contact administrator.",
    },
}


def build_agent_error_response(
    exception: Exception,
    context: dict[str, Any],
    fallback_type: str = "OPERATION_ERROR",
    fallback_action: str = "Operation failed. Retry with different parameters or inform user.",
) -> dict[str, Any]:
    """Convert exception to agent-friendly structured error response.

    Classifies error type, builds actionable message, and returns consistent dict
    format that enables agents to reason about errors and adapt behavior.

    Args:
        exception: The caught exception
        context: Context dict with tool-specific fields (e.g., {"table": "products", "image_path": "/tmp/img.jpg"})
        fallback_type: Error type to use if pattern matching fails
        fallback_action: Action guidance if pattern matching fails

    Returns:
        Dict with structured error response:
        {
            "success": False,
            "error": "ERROR_TYPE: Description\\n\\nError: {exception}\\n\\nAgent Action: {guidance}",
            "error_type": "ERROR_TYPE",
            **context  # Preserves tool-specific context fields
        }

    Example:
        try:
            result = await storage.query_advanced(table="products")
        except Exception as e:
            return build_agent_error_response(
                exception=e,
                context={"table": "products", "filters": {...}}
            )
    """
    error_msg = str(exception).lower()

    # Find matching error pattern
    error_type = fallback_type
    agent_action = fallback_action

    for pattern, config in ERROR_PATTERNS.items():
        if pattern in error_msg:
            error_type = config["type"]
            agent_action = config["action"]
            break

    # Build actionable error message
    actionable_msg = (
        f"{error_type}: {str(exception)}\n\n"
        f"Agent Action: {agent_action}"
    )

    # Return structured response
    return {
        "success": False,
        "error": actionable_msg,
        "error_type": error_type,
        **context,  # Include tool-specific context (table, image_path, etc.)
    }


def build_success_response(data: dict[str, Any]) -> dict[str, Any]:
    """Build consistent success response for tools.

    Args:
        data: Tool-specific result data

    Returns:
        Dict with success flag and data:
        {
            "success": True,
            **data
        }

    Example:
        return build_success_response({
            "rows": query_results,
            "count": len(query_results)
        })
    """
    return {
        "success": True,
        **data,
    }
