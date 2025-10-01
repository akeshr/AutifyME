import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
# This is useful for local development.
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


# Create a single, globally accessible instance of the settings.
# Other parts of our application will import this `settings` object.
settings = Settings()
