"""
Factory for creating configured components

Handles dependency injection and configuration management.
Components get their dependencies injected rather than pulling from global config.
"""

from typing import Optional, Dict, Any
from src.core.config import get_config
from src.core.credentials import supabase, openai, anthropic, DatabaseService
from src.specialists.database import DatabaseSpecialist


class ComponentFactory:
    """
    Factory for creating properly configured components
    
    Handles credential injection and configuration management.
    Components are created with their dependencies, not global config references.
    """
    
    def __init__(self):
        self.config = get_config()
    
    def get_database_service(self) -> DatabaseService:
        """Get database service"""
        return supabase()
    
    def create_database_specialist(self, ai_model: Optional[str] = None) -> DatabaseSpecialist:
        """Create a database specialist with proper dependencies"""
        database = self.get_database_service()
        model = ai_model or self.config.ai.simple_model
        
        return DatabaseSpecialist(
            database=database,
            ai_model=model
        )
    
    def create_openai_client(self, model_tier: str = "balanced"):
        """Create OpenAI client with proper credentials"""
        from langchain_openai import ChatOpenAI
        
        ai_service = openai()
        model = self.config.ai.simple_model if model_tier == "fast" else self.config.ai.complex_model
        return ChatOpenAI(api_key=ai_service.api_key, model=model, temperature=0.1)
    
    def create_anthropic_client(self, model_tier: str = "balanced"):
        """Create Anthropic client with proper credentials"""
        from langchain_anthropic import ChatAnthropic
        
        ai_service = anthropic()
        model = "claude-3-haiku-20240307" if model_tier == "fast" else "claude-3-sonnet-20240229"
        return ChatAnthropic(api_key=ai_service.api_key, model=model, temperature=0.1)


# Global factory instance
_factory: Optional[ComponentFactory] = None


def get_factory() -> ComponentFactory:
    """Get the global component factory"""
    global _factory
    if _factory is None:
        _factory = ComponentFactory()
    return _factory


# Convenience functions for common components
def create_database_specialist(ai_model: Optional[str] = None) -> DatabaseSpecialist:
    """Create a database specialist with default configuration"""
    return get_factory().create_database_specialist(ai_model)


def get_factory_database_service() -> DatabaseService:
    """Get database service via factory (alternative to direct service access)"""
    return get_factory().get_database_service()


def create_openai_client(model_tier: str = "balanced"):
    """Create OpenAI client with proper credentials"""
    return get_factory().create_openai_client(model_tier)


def create_anthropic_client(model_tier: str = "balanced"):
    """Create Anthropic client with proper credentials"""
    return get_factory().create_anthropic_client(model_tier)