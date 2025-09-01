"""
Configuration management for AutifyME

Handles LLM provider configuration, cost optimization, and model routing.
Supports multiple AI providers with fallback strategies.
"""

import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"  # For local models


class ModelTier(Enum):
    """Model performance tiers for cost optimization"""
    FAST = "fast"        # Cheap, quick models for simple tasks
    BALANCED = "balanced" # Mid-tier models for most tasks
    PREMIUM = "premium"   # Expensive, high-quality models for complex tasks


class LLMConfig(BaseModel):
    """Configuration for a specific LLM"""
    provider: LLMProvider
    model_name: str
    api_key_env: str = Field(description="Environment variable name for API key")
    max_tokens: int = 4000
    temperature: float = 0.1
    cost_per_1k_tokens: float = Field(description="Cost in USD per 1000 tokens")
    tier: ModelTier = ModelTier.BALANCED
    supports_functions: bool = True
    supports_vision: bool = False


class AutifyMEConfig(BaseModel):
    """Main configuration for AutifyME system"""
    
    # LLM configurations by tier
    llm_configs: Dict[ModelTier, List[LLMConfig]] = Field(default_factory=dict)
    
    # Default provider preferences
    preferred_provider: LLMProvider = LLMProvider.OPENAI
    fallback_providers: List[LLMProvider] = Field(default_factory=lambda: [LLMProvider.ANTHROPIC, LLMProvider.GOOGLE])
    
    # Cost controls
    daily_budget_usd: float = 50.0
    max_tokens_per_request: int = 4000
    enable_caching: bool = True
    cache_ttl_hours: int = 24
    
    # Database settings
    supabase_url: str = Field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_key: str = Field(default_factory=lambda: os.getenv("SUPABASE_KEY", ""))
    
    # Storage settings
    google_drive_credentials_path: str = Field(default_factory=lambda: os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", ""))
    
    # Workflow settings
    max_concurrent_workflows: int = 5
    workflow_timeout_minutes: int = 30
    
    @classmethod
    def load_default_config(cls) -> "AutifyMEConfig":
        """Load default configuration with all supported models"""
        
        # Define model configurations
        fast_models = [
            LLMConfig(
                provider=LLMProvider.OPENAI,
                model_name="gpt-4o-mini",
                api_key_env="OPENAI_API_KEY",
                cost_per_1k_tokens=0.00015,
                tier=ModelTier.FAST,
                max_tokens=4000
            ),
            LLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model_name="claude-3-haiku-20240307",
                api_key_env="ANTHROPIC_API_KEY",
                cost_per_1k_tokens=0.00025,
                tier=ModelTier.FAST,
                max_tokens=4000
            )
        ]
        
        balanced_models = [
            LLMConfig(
                provider=LLMProvider.OPENAI,
                model_name="gpt-4o",
                api_key_env="OPENAI_API_KEY",
                cost_per_1k_tokens=0.005,
                tier=ModelTier.BALANCED,
                supports_vision=True
            ),
            LLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model_name="claude-3-sonnet-20240229",
                api_key_env="ANTHROPIC_API_KEY",
                cost_per_1k_tokens=0.003,
                tier=ModelTier.BALANCED,
                supports_vision=True
            )
        ]
        
        premium_models = [
            LLMConfig(
                provider=LLMProvider.OPENAI,
                model_name="gpt-4-turbo",
                api_key_env="OPENAI_API_KEY",
                cost_per_1k_tokens=0.01,
                tier=ModelTier.PREMIUM,
                supports_vision=True
            ),
            LLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model_name="claude-3-opus-20240229",
                api_key_env="ANTHROPIC_API_KEY",
                cost_per_1k_tokens=0.015,
                tier=ModelTier.PREMIUM,
                supports_vision=True
            )
        ]
        
        return cls(
            llm_configs={
                ModelTier.FAST: fast_models,
                ModelTier.BALANCED: balanced_models,
                ModelTier.PREMIUM: premium_models
            }
        )
    
    def get_model_for_task(self, task_complexity: ModelTier = ModelTier.BALANCED, 
                          requires_vision: bool = False) -> Optional[LLMConfig]:
        """
        Get the best model for a specific task based on requirements
        
        Args:
            task_complexity: Required model tier
            requires_vision: Whether vision capabilities are needed
            
        Returns:
            Best available model configuration
        """
        available_models = self.llm_configs.get(task_complexity, [])
        
        # Filter by requirements
        if requires_vision:
            available_models = [m for m in available_models if m.supports_vision]
        
        # Sort by preference and cost
        preferred_models = [m for m in available_models if m.provider == self.preferred_provider]
        if preferred_models:
            return min(preferred_models, key=lambda x: x.cost_per_1k_tokens)
        
        # Fallback to any available model
        if available_models:
            return min(available_models, key=lambda x: x.cost_per_1k_tokens)
        
        return None


# Global configuration instance
config = AutifyMEConfig.load_default_config()


def get_config() -> AutifyMEConfig:
    """Get the global configuration instance"""
    return config


def update_config(**kwargs) -> None:
    """Update global configuration"""
    global config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)