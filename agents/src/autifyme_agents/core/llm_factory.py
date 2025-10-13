from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.chat_models import BaseChatModel


def get_llm(
    provider: str = "openai",
    model: str = "gpt-4.1-mini-2025-04-14",
    temperature: float = 0.0,
    tags: list[str] | None = None,
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

    Returns:
        An instance of a BaseChatModel.

    Raises:
        ValueError: If an unsupported provider is requested.
    """
    llm: BaseChatModel

    if provider == "openai":
        llm = ChatOpenAI(model=model, temperature=temperature)
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
