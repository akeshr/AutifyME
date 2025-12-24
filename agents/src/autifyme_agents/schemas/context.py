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
    - Type-safe access in nodes/tools via get_runtime().context
    - Cleaner tool signatures (no company_profile parameter needed)
    - Consistent across entire agent hierarchy

    Note: For specialists (SubAgents), context is injected via prompt
    formatting at creation time, not via runtime context.

    Usage:
        # In agent creation:
        agent = create_deep_agent(
            model=llm,
            tools=tools,
            context_schema=CompanyContext
        )

        # In node/tool implementation:
        from langgraph.runtime import get_runtime
        runtime = get_runtime()
        company = runtime.context  # Type: CompanyContext

        # For specialists (prompt-based injection):
        system_prompt = prompt_template.format(
            company_name=company_profile.name,
            currency_symbol=company_profile.currency_symbol,
            ...
        )
    """

    # Core identification
    company_id: str
    company_name: str

    # Brand guidelines
    brand_voice: str
    target_audience: str
    style_preferences: list[str]
    industry: str | None

    # Visual identity (for creative specialist)
    primary_color: str  # e.g., "#d32f2f"
    secondary_color: str  # e.g., "#000000"
    accent_color: str | None
    font_family: str  # e.g., "sans-serif"
    logo_asset_path: str | None  # Storage path to company logo

    # Catalog defaults (for catalog specialist)
    default_currency: str  # e.g., "INR", "USD"
    currency_symbol: str  # e.g., "₹", "$"
    default_price_list_id: str | None  # UUID of default price list

    # SKU naming (for catalog specialist)
    sku_prefix: str | None  # e.g., "PAV" for Pavisha
    sku_separator: str  # e.g., "-"
    sku_uppercase: bool  # Whether SKUs should be uppercase
