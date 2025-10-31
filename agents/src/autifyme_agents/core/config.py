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
    WHATSAPP_API_VERSION: str = "v20.0"
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str | None = None
    AGENT_RECURSION_LIMIT: int = 50


# Create a single, globally accessible instance of the settings.
# Other parts of our application will import this `settings` object.
settings = Settings()
