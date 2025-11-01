"""
OpenAI Tool Schema Patcher - Monkey-patches LangChain for OpenAI compatibility.

OpenAI's function calling API requires all object schemas to explicitly set
"additionalProperties": false when using strict mode (which is often the default).

DeepAgents' filesystem tools (ls, read_file, write_file, edit_file) and other
LangChain tools don't include this field, causing BadRequestError.

This module monkey-patches LangChain's convert_to_openai_tool function to
automatically add the required field to all tool schemas.

Usage:
    # Import at app startup to apply patch
    from autifyme_agents.core import openai_schema_patcher  # Auto-patches on import

    # Or manually
    from autifyme_agents.core.openai_schema_patcher import apply_openai_schema_patch
    apply_openai_schema_patch()

References:
    - https://platform.openai.com/docs/guides/function-calling
    - https://github.com/langchain-ai/langchain/issues/26232
"""

from typing import Any
import logging

logger = logging.getLogger(__name__)


def add_additional_properties_false(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively add 'additionalProperties': false to all object schemas.

    OpenAI requires this field in strict mode for all object-type properties.
    Modifies the schema in-place and returns it for chaining.

    Args:
        schema: JSON schema dict (potentially nested)

    Returns:
        The same schema dict with additionalProperties added

    Example:
        >>> schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        >>> add_additional_properties_false(schema)
        {"type": "object", "properties": {...}, "additionalProperties": false}
    """
    if isinstance(schema, dict):
        # If this is an object schema, add additionalProperties: false
        if schema.get('type') == 'object':
            schema['additionalProperties'] = False

        # Recursively process all nested dicts
        for key, value in schema.items():
            if isinstance(value, dict):
                add_additional_properties_false(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        add_additional_properties_false(item)

    return schema


# =============================================================================
# Monkey-Patch LangChain's convert_to_openai_tool
# =============================================================================

_PATCH_APPLIED = False
_ORIGINAL_CONVERT_TO_OPENAI_TOOL = None


def apply_openai_schema_patch() -> None:
    """
    Monkey-patch LangChain's convert_to_openai_tool to add additionalProperties: false.

    This patches the function that converts LangChain tools to OpenAI's function
    calling format. All tools will automatically get the required field added.

    This function is idempotent - calling it multiple times is safe.

    Side Effects:
        Modifies langchain_core.utils.function_calling.convert_to_openai_tool

    Example:
        >>> apply_openai_schema_patch()  # Apply once at startup
        >>> # Now all tools work with OpenAI
    """
    global _PATCH_APPLIED, _ORIGINAL_CONVERT_TO_OPENAI_TOOL

    if _PATCH_APPLIED:
        logger.debug("OpenAI schema patch already applied, skipping")
        return

    try:
        from langchain_core.utils import function_calling

        # Store original function
        _ORIGINAL_CONVERT_TO_OPENAI_TOOL = function_calling.convert_to_openai_tool

        def patched_convert_to_openai_tool(tool: Any, *, strict: bool | None = None) -> dict:
            """
            Patched version of convert_to_openai_tool that adds additionalProperties: false.

            Calls the original function, then recursively adds the required field
            to all object schemas in the tool definition.
            """
            # Call original conversion
            openai_tool = _ORIGINAL_CONVERT_TO_OPENAI_TOOL(tool, strict=strict)

            # Patch the parameters schema if it exists
            if "function" in openai_tool and "parameters" in openai_tool["function"]:
                add_additional_properties_false(openai_tool["function"]["parameters"])

            return openai_tool

        # Apply the patch
        function_calling.convert_to_openai_tool = patched_convert_to_openai_tool

        _PATCH_APPLIED = True
        logger.info("✅ OpenAI schema patch applied successfully - all tools now compatible with OpenAI strict mode")

    except ImportError as e:
        logger.warning(f"Could not apply OpenAI schema patch: {e}")
    except Exception as e:
        logger.error(f"Error applying OpenAI schema patch: {e}", exc_info=True)


def remove_openai_schema_patch() -> None:
    """
    Remove the monkey-patch and restore original convert_to_openai_tool.

    Useful for testing or if the patch causes issues.
    """
    global _PATCH_APPLIED, _ORIGINAL_CONVERT_TO_OPENAI_TOOL

    if not _PATCH_APPLIED:
        logger.debug("OpenAI schema patch not applied, nothing to remove")
        return

    try:
        from langchain_core.utils import function_calling

        if _ORIGINAL_CONVERT_TO_OPENAI_TOOL is not None:
            function_calling.convert_to_openai_tool = _ORIGINAL_CONVERT_TO_OPENAI_TOOL
            _PATCH_APPLIED = False
            logger.info("OpenAI schema patch removed, original function restored")

    except Exception as e:
        logger.error(f"Error removing OpenAI schema patch: {e}", exc_info=True)


# =============================================================================
# Auto-apply patch on module import
# =============================================================================

# Apply patch automatically when this module is imported
# This ensures all tools work with OpenAI without manual intervention
apply_openai_schema_patch()
