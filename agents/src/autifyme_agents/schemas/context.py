"""Context schemas for type-safe context injection into agents.

v1.0 introduces `context_schema` parameter to create_agent/create_deep_agent,
enabling typed context (company profile, tenant settings) to be injected
outside of messages, reducing token usage and improving type safety.
"""

from typing_extensions import TypedDict


class CompanyContext(TypedDict, total=False):
    """Typed context for company/tenant information.

    Used with context_schema parameter to inject company profile data
    into agents and tools without passing through messages.

    Benefits:
    - Reduces token usage (context not in message history)
    - Type-safe access in tools via Runtime.get().context
    - Cleaner tool signatures (no company_profile parameter needed)
    - Consistent across entire agent hierarchy

    Usage:
        # In agent creation:
        agent = create_deep_agent(
            model=llm,
            tools=tools,
            context_schema=CompanyContext
        )

        # In tool implementation:
        from langgraph.runtime import Runtime
        runtime = Runtime.get()
        company = runtime.context  # Type: CompanyContext
    """

    # Core identification
    company_id: str
    company_name: str

    # Brand guidelines
    brand_voice: str
    target_audience: str
    style_preferences: list[str]
    industry: str | None
