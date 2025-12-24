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
        extra="ignore"  # Allow and ignore extra environment variables
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
    MESSAGE_BATCH_DEBOUNCE_SECONDS: float = 3.0  # Debounce window duration
    MESSAGE_BATCH_RECENT_WINDOW_SECONDS: int = 5  # Recent activity detection window
    MESSAGE_BATCH_MAX_SIZE: int = 10  # Max messages per batch (safety limit)

    # Research & Web Tools
    TAVILY_API_KEY: str | None = None  # Web search & content extraction (Phase 2G)

    # Phase 2 Feature Flags (Enable advanced capabilities when ready)
    ENABLE_SEMANTIC_SEARCH: bool = False  # Taxonomy: Embeddings-based category search
    ENABLE_GOOGLE_TAXONOMY_API: bool = False  # Taxonomy: Google Product Taxonomy integration
    ENABLE_LLM_INDUSTRY_CLASSIFICATION: bool = False  # Taxonomy: LLM-based NAICS classification
    ENABLE_COMPETITIVE_PRICING_API: bool = False  # Market Intelligence: Competitive pricing data
    ENABLE_LLM_USE_CASE_GENERATION: bool = False  # Market Intelligence: Custom use cases per industry
    ENABLE_LLM_BULLET_GENERATION: bool = False  # Content SEO: Brand-aligned bullet points


# Create a single, globally accessible instance of the settings.
# Other parts of our application will import this `settings` object.
settings = Settings()
