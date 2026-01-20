from typing import Any

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """
    Manages application settings and secrets.

    This class automatically loads variables from the environment or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Allow and ignore extra environment variables
    )

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    DATABASE_URL: str  # PostgreSQL connection for LangGraph checkpointer
    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_BUSINESS_ACCOUNT_ID: str | None = None
    WHATSAPP_ACCESS_TOKEN: str | None = None
    WHATSAPP_API_VERSION: str = "v23.0"
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str | None = None
    AGENT_RECURSION_LIMIT: int = 50

    # Message Batching (Smart Skip for Multi-Image Handling)
    # Debounce: 5s catches WhatsApp forwards (3-4s gaps between forwarded items)
    MESSAGE_BATCH_DEBOUNCE_SECONDS: float = 5.0  # Debounce window duration
    MESSAGE_BATCH_RECENT_WINDOW_SECONDS: int = 7  # Recent activity detection window
    MESSAGE_BATCH_MAX_SIZE: int = 10  # Max messages per batch (safety limit)

    # Research & Web Tools
    TAVILY_API_KEY: str | None = None  # Web search & content extraction (Phase 2G)

    # Phase 2 Feature Flags (Enable advanced capabilities when ready)
    ENABLE_SEMANTIC_SEARCH: bool = False  # Taxonomy: Embeddings-based category search
    ENABLE_GOOGLE_TAXONOMY_API: bool = False  # Taxonomy: Google Product Taxonomy integration
    ENABLE_LLM_INDUSTRY_CLASSIFICATION: bool = False  # Taxonomy: LLM-based NAICS classification
    ENABLE_COMPETITIVE_PRICING_API: bool = False  # Market Intelligence: Competitive pricing data
    ENABLE_LLM_USE_CASE_GENERATION: bool = (
        False  # Market Intelligence: Custom use cases per industry
    )
    ENABLE_LLM_BULLET_GENERATION: bool = False  # Content SEO: Brand-aligned bullet points


# Create a single, globally accessible instance of the settings.
# Other parts of our application will import this `settings` object.
settings = Settings()


# =============================================================================
# DeepAgents Configuration
# =============================================================================

_deepagents_configured = False


def configure_deepagents() -> None:
    """Configure DeepAgents middleware settings.

    Disables large output eviction to files. By default, DeepAgents writes
    tool outputs > 20k tokens to files and returns a 10-line preview. This
    breaks:
    - view_image: Multimodal content can't be reconstructed from file
    - load_protocol: Protocols must be in context for agent reasoning

    Call this early in your application startup, before creating any agents.
    Safe to call multiple times (idempotent).
    """
    global _deepagents_configured
    if _deepagents_configured:
        return

    from deepagents.middleware import filesystem

    # Store original __init__
    original_init = filesystem.FilesystemMiddleware.__init__

    def patched_init(
        self: Any,
        *,
        backend: Any = None,
        system_prompt: str | None = None,
        custom_tool_descriptions: dict[str, str] | None = None,
        tool_token_limit_before_evict: int | None = None,  # Changed default: None = disabled
    ) -> None:
        original_init(
            self,
            backend=backend,
            system_prompt=system_prompt,
            custom_tool_descriptions=custom_tool_descriptions,
            tool_token_limit_before_evict=tool_token_limit_before_evict,
        )

    # Apply patch
    filesystem.FilesystemMiddleware.__init__ = patched_init

    _deepagents_configured = True
