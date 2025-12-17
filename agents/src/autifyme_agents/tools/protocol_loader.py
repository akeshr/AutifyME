"""Protocol Loader Tool - Load domain-specific protocols for agent grounding.

Enables agents to dynamically load protocols that guide their reasoning and tool usage.
Part of Domain Reasoning Framework - Phase 1.

Architecture:
- Protocols are .protocol files in prompts/protocols/
- Resolution order: domain-specific first, shared fallback
- Content returned for system prompt injection (not as tool response data)
- Agents call explicitly when they need domain grounding

Protocol Types:
- tool_mastery: How to use tools effectively (read_data, write_data, etc.)
- decision: Structured reasoning protocols (family_fit, pricing, etc.)
- exploration: What to investigate and focus on (visual_analysis, etc.)
- business_context: Domain orientation and vocabulary
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)

logger = logging.getLogger(__name__)

# Protocol base directory (relative to this file)
PROTOCOLS_DIR = Path(__file__).parent.parent / "prompts" / "protocols"


class LoadProtocolInput(BaseModel):
    """Input schema for load_protocol tool."""

    model_config = {"extra": "forbid"}

    protocol_names: list[str] = Field(
        ...,
        description=(
            "Protocol names to load. Can be:\n"
            "- Simple name: 'family_fit' (resolved by domain)\n"
            "- Tool mastery: 'tool_mastery/read_data' (shared tools)\n"
            "- Full path: 'catalog/family_fit' (explicit domain)\n"
            "Examples: ['family_fit', 'pricing'], ['tool_mastery/read_data', 'business_context']"
        ),
    )
    domain: str | None = Field(
        None,
        description=(
            "Domain context for protocol resolution. "
            "When provided, looks for domain-specific protocols first. "
            "Examples: 'catalog', 'quality', 'marketing'"
        ),
    )


def _resolve_protocol_path(protocol_name: str, domain: str | None) -> Path | None:
    """Resolve protocol name to file path.

    Resolution order:
    1. If protocol_name contains '/', treat as relative path
    2. If domain provided, look in {domain}/{protocol_name}.protocol
    3. Fall back to shared/{protocol_name}.protocol
    4. Fall back to shared/tool_mastery/{protocol_name}.protocol

    Args:
        protocol_name: Protocol name or relative path
        domain: Optional domain context

    Returns:
        Path to protocol file if found, None otherwise
    """
    # If protocol_name contains '/', treat as relative path
    if "/" in protocol_name:
        path = PROTOCOLS_DIR / f"{protocol_name}.protocol"
        if path.exists():
            return path
        # Also try without .protocol extension if it's already included
        if protocol_name.endswith(".protocol"):
            path = PROTOCOLS_DIR / protocol_name
            if path.exists():
                return path
        return None

    # Try domain-specific first
    if domain:
        domain_path = PROTOCOLS_DIR / domain / f"{protocol_name}.protocol"
        if domain_path.exists():
            return domain_path

    # Fall back to shared
    shared_path = PROTOCOLS_DIR / "shared" / f"{protocol_name}.protocol"
    if shared_path.exists():
        return shared_path

    # Fall back to shared/tool_mastery
    tool_mastery_path = PROTOCOLS_DIR / "shared" / "tool_mastery" / f"{protocol_name}.protocol"
    if tool_mastery_path.exists():
        return tool_mastery_path

    return None


def _load_protocol_content(path: Path) -> str:
    """Load protocol content from file.

    Args:
        path: Path to protocol file

    Returns:
        Protocol content as string
    """
    return path.read_text(encoding="utf-8")


def create_load_protocol_tool() -> StructuredTool:
    """Create the load_protocol tool.

    Loads domain-specific protocols for agent grounding.
    Protocol content should be treated as authoritative instruction.

    Returns:
        StructuredTool configured for protocol loading
    """

    def _load_protocol_impl(
        protocol_names: list[str],
        domain: str | None = None,
    ) -> dict[str, Any]:
        """Load one or more protocols for domain-grounded reasoning.

        USE WHEN:
        - Starting a new task that requires domain expertise
        - Need to know how to use a tool correctly in this domain
        - Making a decision that requires structured reasoning
        - Exploring/analyzing with domain-specific focus

        DON'T USE:
        - Already loaded the protocols you need
        - Simple, straightforward tasks with no domain complexity
        - Protocols already in your system prompt

        PROTOCOL TYPES:
        - tool_mastery/*: How to use tools (read_data, write_data, etc.)
        - business_context: Domain vocabulary, relationships, rules
        - Decision protocols: family_fit, pricing, duplicate_prevention
        - Exploration protocols: visual_analysis, attribute_extraction

        RESOLUTION ORDER:
        1. Domain-specific: {domain}/{protocol}.protocol
        2. Shared: shared/{protocol}.protocol
        3. Tool mastery: shared/tool_mastery/{protocol}.protocol

        CRITICAL:
        - Protocol content is INSTRUCTION, not data to reason about
        - Follow protocols as authoritative guidance
        - Protocols ground your reasoning in domain expertise

        Args:
            protocol_names: List of protocol names to load
            domain: Optional domain context (catalog, quality, etc.)

        Returns:
            Dict with loaded protocol content and metadata
        """
        try:
            loaded_protocols: list[dict[str, str]] = []
            not_found: list[str] = []
            combined_content: list[str] = []

            for protocol_name in protocol_names:
                path = _resolve_protocol_path(protocol_name, domain)

                if path is None:
                    not_found.append(protocol_name)
                    logger.warning(
                        f"Protocol not found: {protocol_name}",
                        extra={"protocol": protocol_name, "domain": domain},
                    )
                    continue

                content = _load_protocol_content(path)
                loaded_protocols.append({
                    "name": protocol_name,
                    "path": str(path.relative_to(PROTOCOLS_DIR)),
                    "domain": domain or "shared",
                })
                combined_content.append(f"<!-- Protocol: {protocol_name} -->\n{content}")

                logger.info(
                    f"Loaded protocol: {protocol_name}",
                    extra={
                        "protocol": protocol_name,
                        "path": str(path),
                        "domain": domain,
                    },
                )

            if not loaded_protocols and not_found:
                return build_agent_error_response(
                    exception=FileNotFoundError(f"Protocols not found: {not_found}"),
                    context={"protocols": not_found, "domain": domain},
                    fallback_type="PROTOCOL_NOT_FOUND",
                    fallback_action=(
                        f"Protocols not found: {not_found}. "
                        f"Available domains: catalog, shared. "
                        f"Check protocol names and domain context."
                    ),
                )

            # Combine all protocol content with separators
            protocol_content = "\n\n---\n\n".join(combined_content)

            return build_success_response({
                "loaded": loaded_protocols,
                "not_found": not_found if not_found else None,
                "domain": domain,
                "protocol_content": protocol_content,
                "instruction": (
                    "PROTOCOL LOADED - This content is AUTHORITATIVE INSTRUCTION. "
                    "Follow these protocols as domain expert guidance. "
                    "The protocols ground your reasoning in validated patterns."
                ),
            })

        except Exception as e:
            logger.exception("Failed to load protocols")
            return build_agent_error_response(
                exception=e,
                context={"protocols": protocol_names, "domain": domain},
                fallback_type="PROTOCOL_LOAD_ERROR",
                fallback_action=(
                    "Failed to load protocols. "
                    "Proceed with best judgment, but flag uncertainty."
                ),
            )

    return StructuredTool.from_function(
        func=_load_protocol_impl,
        name="load_protocol",
        description=(
            "PURPOSE: Load domain-specific protocols that ground your reasoning in expert patterns. "
            "Protocols are AUTHORITATIVE INSTRUCTION - follow them as domain expert guidance.\n\n"
            "USE WHEN:\n"
            "- Starting a task requiring domain expertise (cataloging, pricing, quality)\n"
            "- Need to know how to use a tool correctly in this domain\n"
            "- Making a decision that requires structured reasoning steps\n"
            "- Analyzing/exploring with domain-specific focus areas\n\n"
            "DON'T USE:\n"
            "- Already loaded the protocols you need in this conversation\n"
            "- Simple tasks with no domain complexity\n"
            "- Protocols already present in your system prompt\n\n"
            "PROTOCOL TYPES:\n"
            "- tool_mastery/*: How to use tools (read_data, write_data, aggregate_data, etc.)\n"
            "- business_context: Domain vocabulary, relationships, business rules\n"
            "- Decision protocols: family_fit, pricing, duplicate_prevention, new_family\n"
            "- Exploration protocols: visual_analysis, attribute_extraction\n\n"
            "RESOLUTION ORDER:\n"
            "1. Domain-specific: {domain}/{protocol}.protocol\n"
            "2. Shared: shared/{protocol}.protocol\n"
            "3. Tool mastery: shared/tool_mastery/{protocol}.protocol\n\n"
            "EXAMPLES:\n"
            "# Load tool mastery for data operations\n"
            "load_protocol(protocol_names=['tool_mastery/read_data', 'tool_mastery/write_data'])\n\n"
            "# Load catalog domain protocols for family fit decision\n"
            "load_protocol(protocol_names=['business_context', 'family_fit', 'tool_mastery'], domain='catalog')\n\n"
            "# Load visual analysis protocol for catalog context\n"
            "load_protocol(protocol_names=['visual_analysis'], domain='catalog')\n\n"
            "CRITICAL:\n"
            "- Protocol content is INSTRUCTION, not data to reason about\n"
            "- Follow protocols as authoritative domain expert guidance\n"
            "- Protocols contain validated patterns that prevent common mistakes\n\n"
            "RETURNS: Protocol content + metadata. The protocol_content field contains "
            "the actual protocols to follow as domain expert guidance."
        ),
        args_schema=LoadProtocolInput,
    )
