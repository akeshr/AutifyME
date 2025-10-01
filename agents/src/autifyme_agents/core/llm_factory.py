from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

def get_llm(provider: str = "openai", model: str = "gpt-4o", temperature: float = 0.0) -> BaseChatModel:
    """
    Factory function to instantiate and return a language model client.

    This centralized factory ensures that all parts of the application
    use consistently configured LLMs and allows for easy implementation
    of cross-cutting features like prompt caching.

    Args:
        provider: The LLM provider to use ('openai' or 'anthropic').
        model: The specific model name to use.
        temperature: The sampling temperature for the model.

    Returns:
        An instance of a BaseChatModel.

    Raises:
        ValueError: If an unsupported provider is requested.
    """
    if provider == "openai":
        return ChatOpenAI(model=model, temperature=temperature)
    elif provider == "anthropic":
        # Enable prompt caching for cost and latency benefits, as documented
        # in our LANGCHAIN_V1_FEATURES.md.
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            enable_prompt_caching=True
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
