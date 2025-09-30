import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
# This is useful for local development.
load_dotenv()

class Settings(BaseSettings):
    """
    Manages application settings and secrets.
    
    This class automatically loads variables from the environment or a .env file.
    """
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str

    class Config:
        # This tells Pydantic to look for a .env file
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create a single, globally accessible instance of the settings.
# Other parts of our application will import this `settings` object.
settings = Settings()
