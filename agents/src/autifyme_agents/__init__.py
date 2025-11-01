"""AutifyME Agents - Autonomous agentic organization for e-commerce automation.

This package auto-applies the OpenAI schema patch on import to ensure all tools
are compatible with OpenAI's strict mode requirement for additionalProperties: false.
"""

# Import patcher to auto-apply monkey-patch for OpenAI compatibility
# This must happen early before any tools are converted to OpenAI format
from autifyme_agents.core import openai_schema_patcher  # noqa: F401

__all__ = ["openai_schema_patcher"]
