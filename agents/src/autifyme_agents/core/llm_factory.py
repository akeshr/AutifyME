from langchain.chat_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI


def get_llm(
    provider: str = "openai",
    model: str = "gpt-5-mini-2025-08-07",
    temperature: float = 0.0,
    tags: list[str] | None = None,
    reasoning_effort: str = "minimal",
    verbosity: str = "low",
) -> BaseChatModel:
    """
    Factory function to instantiate and return a language model client.

    This centralized factory ensures that all parts of the application
    use consistently configured LLMs.

    Args:
        provider: The LLM provider to use ('openai' or 'anthropic').
        model: The specific model name to use.
        temperature: The sampling temperature for the model.
        tags: A list of tags to add to the LangSmith run trace.
        reasoning_effort: Reasoning effort for GPT-5 models ('minimal', 'low', 'medium', 'high').
        verbosity: Output verbosity for GPT-5 models ('low', 'medium', 'high').

    Returns:
        An instance of a BaseChatModel.

    Raises:
        ValueError: If an unsupported provider is requested.
    """
    llm: BaseChatModel

    if provider == "openai":
        # GPT-5 models support reasoning_effort and verbosity parameters
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            reasoning_effort=reasoning_effort,  # type: ignore[call-arg]
            verbosity=verbosity,  # type: ignore[call-arg]
        )
    elif provider == "anthropic":
        # Enable prompt caching for cost and latency benefits
        llm = ChatAnthropic(  # type: ignore[call-arg]
            model=model,
            temperature=temperature,
            model_kwargs={
                "extra_headers": {"anthropic-beta": "prompt-caching-2024-07-31"}
            },
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    return llm
