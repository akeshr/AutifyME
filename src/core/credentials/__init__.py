"""
Credential Management Module

Centralized, secure credential handling following architecture decisions.
Never logs sensitive data, provides proper validation and rotation.
"""

from .credential_manager import (
    CredentialManager,
    CredentialError,
    get_credential_manager,
    store_openai_key,
    store_anthropic_key,
    store_supabase_credentials,
    validate_openai_key,
    validate_anthropic_key,
    validate_google_key,
    DEFAULT_VALIDATORS
)
from .service_credentials import (
    # Service classes
    Supabase,
    PostgreSQL,
    MongoDB,
    OpenAI,
    Anthropic,
    Google,
    GoogleDrive,
    AWS,
    
    # Service getters
    supabase,
    postgresql,
    mongodb,
    openai,
    anthropic,
    google,
    google_drive,
    aws,
    
    # Type aliases
    DatabaseService,
    AIService,
    StorageService,
    
    # Utilities
    refresh_all
)

__all__ = [
    # Credential Manager
    "CredentialManager",
    "CredentialError", 
    "get_credential_manager",
    "store_openai_key",
    "store_anthropic_key", 
    "store_supabase_credentials",
    "validate_openai_key",
    "validate_anthropic_key",
    "validate_google_key",
    "DEFAULT_VALIDATORS",
    
    # Service Classes
    "Supabase",
    "PostgreSQL", 
    "MongoDB",
    "OpenAI",
    "Anthropic",
    "Google",
    "GoogleDrive",
    "AWS",
    
    # Service Getters
    "supabase",
    "postgresql",
    "mongodb", 
    "openai",
    "anthropic",
    "google",
    "google_drive",
    "aws",
    
    # Type Aliases
    "DatabaseService",
    "AIService", 
    "StorageService",
    
    # Utilities
    "refresh_all"
]