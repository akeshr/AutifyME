from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from pydantic import Field

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
    WHATSAPP_PHONE_NUMBER_ID: str | None = Field(default=None, env="WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_BUSINESS_ACCOUNT_ID: str | None = Field(default=None, env="WHATSAPP_BUSINESS_ACCOUNT_ID")
    WHATSAPP_ACCESS_TOKEN: str | None = Field(default=None, env="WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_API_VERSION: str = Field(default="v20.0", env="WHATSAPP_API_VERSION")
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str | None = Field(default=None, env="WHATSAPP_WEBHOOK_VERIFY_TOKEN")
    AGENT_RECURSION_LIMIT: int = Field(default=15, env="AGENT_RECURSION_LIMIT")


# Create a single, globally accessible instance of the settings.
# Other parts of our application will import this `settings` object.
settings = Settings()