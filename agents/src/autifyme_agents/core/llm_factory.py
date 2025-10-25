from langchain.chat_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI


def get_llm(
    provider: str = "openai",
    model: str = "gpt-4.1-mini",
    temperature: float = 0.0,
    tags: list[str] | None = None,
    reasoning_effort: str = "low",
    verbosity: str = "low",
    timeout: float | None = None,
) -> BaseChatModel:
    """
    Factory function to instantiate and return a language model client.

    This centralized factory ensures that all parts of the application
    use consistently configured LLMs with automatic prompt caching.

    Args:
        provider: The LLM provider to use ('openai' or 'anthropic').
        model: The specific model name to use.
            OpenAI models: 'gpt-4.1-mini', 'gpt-4.1', 'gpt-4.1-nano', 'gpt-5-mini-2025-08-07'
            Anthropic models: 'claude-3-5-sonnet-20241022'
        temperature: The sampling temperature for the model.
        tags: A list of tags to add to the LangSmith run trace.
        reasoning_effort: Reasoning effort for GPT-5/o1/o3 models ('minimal', 'low', 'medium', 'high').
            Only applies to GPT-5, o1, o3 models. GPT-4.1 does NOT support these parameters.
            GPT-5 models support all values including 'minimal' for fastest response.
            o1/o3 models support 'low', 'medium', 'high' (no 'minimal').
        verbosity: Output verbosity for GPT-5/o1/o3 models ('low', 'medium', 'high').
            Only applies to GPT-5, o1, o3 models. GPT-4.1 does NOT support these parameters.
            Controls answer length - low for concise, high for comprehensive.
        timeout: Request timeout in seconds. If None, uses provider default.

    Returns:
        An instance of a BaseChatModel.

    Raises:
        ValueError: If an unsupported provider is requested.

    Notes:
        **Automatic Prompt Caching (OpenAI):**
        - GPT-4.1: 75% discount on cached tokens (best caching) ✅ RECOMMENDED
        - GPT-5: 50% discount (known caching bugs as of Jan 2025)
        - GPT-4o, o1: 50% discount on cached tokens
        - Activates automatically for 1024+ token prompts
        - Cache lifetime: 5-10 min inactivity, max 1 hour
        - Caches in 128-token increments after initial 1024
        - Check API response for cached_tokens in usage.prompt_tokens_details

        **Prompt Caching (Anthropic):**
        - Requires extra_headers with anthropic-beta header
        - Cache breakpoints marked with cache_control in prompts
        - Check LangSmith traces for cache_read_input_tokens metrics
    """
    llm: BaseChatModel

    if provider == "openai":
        # Check if model supports reasoning_effort and verbosity parameters
        # Only GPT-5, o1, o3 models support these. GPT-4.1 does NOT.
        supports_reasoning_params = any(m in model for m in ["gpt-5", "o1", "o3"])

        if supports_reasoning_params:
            # GPT-5/o1/o3 models with reasoning parameters
            # Prompt caching is AUTOMATIC for 1024+ token prompts (no config needed)
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                verbosity=verbosity,
                timeout=timeout,
            )
        else:
            # GPT-4.1 and other models (standard configuration)
            # Prompt caching is AUTOMATIC for 1024+ token prompts (no config needed)
            # GPT-4.1 has BEST caching: 75% discount vs 50% for GPT-5
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                timeout=timeout,
            )
    elif provider == "anthropic":
        # Enable prompt caching for cost and latency benefits
        llm = ChatAnthropic(
            model=model,
            temperature=temperature,
            timeout=timeout,
            model_kwargs={
                "extra_headers": {"anthropic-beta": "prompt-caching-2024-07-31"}
            },
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    return llm
