"""
LLM Factory for Multi-Provider Support

Creates LangChain LLM instances based on configuration.
Supports OpenAI, Anthropic, Google, and local models with automatic fallbacks.
"""

import os
from typing import Optional, Any
from langchain.llms.base import BaseLLM
from langchain.chat_models.base import BaseChatModel

from .config import LLMConfig, LLMProvider, get_config
from .credentials.credential_manager import get_credential_manager


class LLMFactory:
    """
    Factory class for creating LLM instances based on configuration
    
    Supports multiple providers with automatic fallback and cost optimization.
    """
    
    @staticmethod
    def create_llm(config: LLMConfig) -> BaseChatModel:
        """
        Create LLM instance based on configuration
        
        Args:
            config: LLM configuration specifying provider and model
            
        Returns:
            Configured LangChain LLM instance
            
        Raises:
            ValueError: If provider is not supported or API key is missing
        """
        # Get API key from credential manager
        credential_manager = get_credential_manager()
        
        # Map provider to credential manager method
        provider_key_map = {
            LLMProvider.OPENAI: "openai",
            LLMProvider.ANTHROPIC: "anthropic", 
            LLMProvider.GOOGLE: "google"
        }
        
        api_key = None
        if config.provider in provider_key_map:
            api_key = credential_manager.get_credential(provider_key_map[config.provider])
        
        if not api_key and config.provider != LLMProvider.OLLAMA:
            raise ValueError(f"API key not found for provider: {config.provider}. Check credential manager.")
        
        # Create LLM based on provider
        if config.provider == LLMProvider.OPENAI:
            return LLMFactory._create_openai_llm(config, api_key)
        
        elif config.provider == LLMProvider.ANTHROPIC:
            return LLMFactory._create_anthropic_llm(config, api_key)
        
        elif config.provider == LLMProvider.GOOGLE:
            return LLMFactory._create_google_llm(config, api_key)
        
        elif config.provider == LLMProvider.OLLAMA:
            return LLMFactory._create_ollama_llm(config)
        
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
    
    @staticmethod
    def _create_openai_llm(config: LLMConfig, api_key: str) -> BaseChatModel:
        """Create OpenAI LLM instance"""
        try:
            from langchain_openai import ChatOpenAI
            
            model_kwargs = {}
            if config.supports_functions:
                model_kwargs["response_format"] = {"type": "json_object"}
            
            return ChatOpenAI(
                model=config.model_name,
                api_key=api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                model_kwargs=model_kwargs
            )
        except ImportError:
            raise ValueError("langchain-openai package not installed. Run: uv pip install langchain-openai")
    
    @staticmethod
    def _create_anthropic_llm(config: LLMConfig, api_key: str) -> BaseChatModel:
        """Create Anthropic Claude LLM instance"""
        try:
            from langchain_anthropic import ChatAnthropic
            
            return ChatAnthropic(
                model=config.model_name,
                api_key=api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
        except ImportError:
            raise ValueError("langchain-anthropic package not installed. Run: uv pip install langchain-anthropic")
    
    @staticmethod
    def _create_google_llm(config: LLMConfig, api_key: str) -> BaseChatModel:
        """Create Google Gemini LLM instance"""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            return ChatGoogleGenerativeAI(
                model=config.model_name,
                google_api_key=api_key,
                temperature=config.temperature,
                max_output_tokens=config.max_tokens
            )
        except ImportError:
            raise ValueError("langchain-google-genai package not installed. Run: uv pip install langchain-google-genai")
    
    @staticmethod
    def _create_ollama_llm(config: LLMConfig) -> BaseChatModel:
        """Create local Ollama LLM instance"""
        try:
            from langchain_community.llms import Ollama
            
            return Ollama(
                model=config.model_name,
                temperature=config.temperature
            )
        except ImportError:
            raise ValueError("langchain-community package not installed. Run: uv pip install langchain-community")
    
    @staticmethod
    def create_with_fallback(task_complexity: "ModelTier" = None, requires_vision: bool = False) -> BaseChatModel:
        """
        Create LLM with automatic fallback to available providers
        
        Args:
            task_complexity: Required model tier (FAST, BALANCED, PREMIUM)
            requires_vision: Whether vision capabilities are needed
            
        Returns:
            Best available LLM instance
            
        Raises:
            RuntimeError: If no suitable LLM can be created
        """
        from .config import ModelTier
        
        if task_complexity is None:
            task_complexity = ModelTier.BALANCED
        
        config = get_config()
        
        # Try to get preferred model
        llm_config = config.get_model_for_task(task_complexity, requires_vision)
        
        if llm_config:
            try:
                return LLMFactory.create_llm(llm_config)
            except Exception as e:
                print(f"Failed to create preferred LLM {llm_config.provider}: {e}")
        
        # Try fallback providers
        for provider in config.fallback_providers:
            fallback_models = [
                m for m in config.llm_configs.get(task_complexity, [])
                if m.provider == provider
            ]
            
            if requires_vision:
                fallback_models = [m for m in fallback_models if m.supports_vision]
            
            for model_config in fallback_models:
                try:
                    return LLMFactory.create_llm(model_config)
                except Exception as e:
                    print(f"Fallback LLM {model_config.provider} failed: {e}")
                    continue
        
        raise RuntimeError("No suitable LLM provider available. Check API keys and configuration.")


class ConfigurableLLMMixin:
    """
    Mixin class for agents and specialists to use configurable LLMs
    
    Usage:
    class MySpecialist(ConfigurableLLMMixin):
        def __init__(self):
            self.llm = self.get_llm_for_task(ModelTier.FAST)
    """
    
    def get_llm_for_task(self, complexity: "ModelTier" = None, requires_vision: bool = False) -> BaseChatModel:
        """Get LLM instance for specific task requirements"""
        return LLMFactory.create_with_fallback(complexity, requires_vision)
    
    def get_cost_optimized_llm(self) -> BaseChatModel:
        """Get the cheapest available LLM for simple tasks"""
        from .config import ModelTier
        return self.get_llm_for_task(ModelTier.FAST)
    
    def get_premium_llm(self, requires_vision: bool = False) -> BaseChatModel:
        """Get the best available LLM for complex tasks"""
        from .config import ModelTier
        return self.get_llm_for_task(ModelTier.PREMIUM, requires_vision)


# Convenience functions for common use cases
def get_fast_llm() -> BaseChatModel:
    """Get fast, cost-effective LLM for simple tasks"""
    from .config import ModelTier
    return LLMFactory.create_with_fallback(ModelTier.FAST)


def get_balanced_llm() -> BaseChatModel:
    """Get balanced LLM for most tasks"""
    from .config import ModelTier
    return LLMFactory.create_with_fallback(ModelTier.BALANCED)


def get_premium_llm(requires_vision: bool = False) -> BaseChatModel:
    """Get premium LLM for complex tasks"""
    from .config import ModelTier
    return LLMFactory.create_with_fallback(ModelTier.PREMIUM, requires_vision)


# Example usage and testing
if __name__ == "__main__":
    # Test different providers
    try:
        # Test fast model
        fast_llm = get_fast_llm()
        print(f"Fast LLM created: {type(fast_llm).__name__}")
        
        # Test balanced model
        balanced_llm = get_balanced_llm()
        print(f"Balanced LLM created: {type(balanced_llm).__name__}")
        
        # Test vision model
        vision_llm = get_premium_llm(requires_vision=True)
        print(f"Vision LLM created: {type(vision_llm).__name__}")
        
    except Exception as e:
        print(f"LLM creation failed: {e}")
        print("Make sure to set appropriate API keys in environment variables")