from typing import Any, Literal

from langchain.chat_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import HarmBlockThreshold, HarmCategory, Modality
from langchain_openai import ChatOpenAI

from autifyme_agents.core.gemini_retry import GeminiWithRetry


def get_llm(
    provider: str = "google",
    model: str = "gemini-2.5-pro",
    temperature: float = 0.1,
    tags: list[str] | None = None,
    reasoning_effort: str = "low",
    verbosity: str = "low",
    timeout: float | None = 120.0,
    # Google Gemini specific parameters
    top_p: float | None = None,
    top_k: int | None = None,
    max_output_tokens: int | None = None,
    thinking_budget: int | None = None,
    include_thoughts: bool = False,
    safety_settings: dict[HarmCategory, HarmBlockThreshold] | None = None,
    response_modalities: list[Literal["TEXT", "IMAGE", "AUDIO"]] | None = None,
    response_mime_type: str | None = None,
    # Gemini 3 Image Generation parameters
    image_aspect_ratio: Literal[
        "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
    ] | None = None,
    image_size: Literal["1K", "2K", "4K"] | None = None,
    # Retry configuration for Gemini blank response handling
    max_retries: int = 5,
    retry_base_delay: float = 1.0,
) -> BaseChatModel:
    """
    Factory function to instantiate and return a language model client.

    This centralized factory ensures that all parts of the application
    use consistently configured LLMs with automatic prompt caching.

    Args:
        provider: The LLM provider to use ('openai', 'anthropic', or 'google').
        model: The specific model name to use.
            OpenAI models: 'gpt-4.1-mini', 'gpt-4.1', 'gpt-4.1-nano', 'gpt-5-mini-2025-08-07'
            Anthropic models: 'claude-3-5-sonnet-20241022'
            Google Gemini models:
                - 3.0 Series (Latest): 'gemini-3-pro', 'gemini-3-flash'
                - 2.5 Series: 'gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.5-flash-lite'
                - 2.0 Series: 'gemini-2.0-flash', 'gemini-2.0-flash-lite'
                - Preview variants: 'gemini-2.5-pro-preview-06-05', 'gemini-2.5-flash-preview-09-2025', etc.
                - Image Generation (Nano Banana Pro): 'gemini-3-pro-image-preview' (RECOMMENDED)
                - Image Generation (Legacy): 'gemini-2.5-flash-image' (retiring Oct 2025)
                - Text-to-Speech: 'gemini-2.5-pro-preview-tts', 'gemini-2.5-flash-preview-tts'
                - Computer Use: 'gemini-2.5-computer-use-preview-10-2025'
                - Note: Computer Use, Video (Veo), and Live API require separate integration modules
        temperature: The sampling temperature for the model (0.0-2.0 for Gemini, 0.0-1.0 for others).
        tags: A list of tags to add to the LangSmith run trace.
        reasoning_effort: Reasoning effort for GPT-5/o1/o3 models ('minimal', 'low', 'medium', 'high').
            Only applies to GPT-5, o1, o3 models. GPT-4.1 does NOT support these parameters.
            GPT-5 models support all values including 'minimal' for fastest response.
            o1/o3 models support 'low', 'medium', 'high' (no 'minimal').
        verbosity: Output verbosity for GPT-5/o1/o3 models ('low', 'medium', 'high').
            Only applies to GPT-5, o1, o3 models. GPT-4.1 does NOT support these parameters.
            Controls answer length - low for concise, high for comprehensive.
        timeout: Request timeout in seconds (default: 120.0).
            Ensures API calls fail cleanly rather than hanging indefinitely.

        Google Gemini specific parameters:
        top_p: Nucleus sampling parameter (0.0-1.0). Consider smallest set of tokens with probability sum >= top_p.
        top_k: Top-k sampling parameter. Consider top_k most probable tokens. Must be positive.
        max_output_tokens: Maximum tokens in response. Must be > 0. Default varies by model.
            Gemini 2.5 models support up to 65K output tokens.
        thinking_budget: Thinking budget in tokens for Gemini 2.5 models with adaptive thinking.
            Default: 0 (disabled) for Flash/Flash-Lite models to optimize speed/cost.
            Set to higher values (e.g., 4096, 8192) for complex reasoning tasks.
            Note: Pro models have minimum of 128 tokens (cannot fully disable).
        include_thoughts: Whether to include chain-of-thought reasoning in response.
            Default: False (hidden). Set True to see model's reasoning process.
        safety_settings: Dict mapping HarmCategory to HarmBlockThreshold for content filtering.
            Categories: DANGEROUS_CONTENT, HATE_SPEECH, HARASSMENT, SEXUALLY_EXPLICIT.
            Thresholds: BLOCK_NONE, BLOCK_LOW_AND_ABOVE, BLOCK_MEDIUM_AND_ABOVE, BLOCK_ONLY_HIGH.
        response_modalities: List of output modalities for multimodal generation.
            Options: ["TEXT"], ["IMAGE"], ["AUDIO"], ["TEXT", "IMAGE"], ["TEXT", "AUDIO"]
            Use with image generation models (Nano Banana) for image outputs.
            Use with TTS models for audio outputs.
            Default: ["TEXT"] for text-only generation.
        response_mime_type: MIME type for structured outputs (e.g., "application/json").
            Used to enforce specific output formats.
        image_aspect_ratio: Aspect ratio for Gemini 3 image generation.
            Options: "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
            Default: "1:1" for square images.
        image_size: Output size for Gemini 3 image generation.
            Options: "1K", "2K", "4K"
            Default: "2K" for balanced quality/performance.
        max_retries: Maximum retry attempts for Gemini blank responses (default: 3).
            Gemini occasionally returns blank responses; this handles automatic retry.
        retry_base_delay: Base delay in seconds for exponential backoff (default: 1.0).
            Actual delay = base * 2^(attempt-1) + jitter.

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

        **Context Caching (Google Gemini):**
        - 2.5 Pro/Flash/Flash-Lite: 1M input tokens, 65K output tokens
        - 2.0 Flash/Flash-Lite: 1M token context window
        - Use cached_content parameter for context caching
        - Supports multimodal inputs (text, images, audio, video)
        - Gemini 2.5 models feature adaptive thinking for complex reasoning
        - Safety settings control content filtering across 4 harm categories
        - Knowledge cutoff: January 2025 (2.5 series), August 2024 (2.0 series)

        **Image Generation (Nano Banana Pro - Gemini 3):**
        - Model: gemini-3-pro-image-preview (RECOMMENDED)
        - Legacy: gemini-2.5-flash-image (retiring Oct 2025)
        - Set response_modalities=["TEXT", "IMAGE"] or ["IMAGE"]
        - Capabilities: Generate, edit, analyze; 1K/2K/4K output; up to 14 reference images
        - Character consistency across generations; advanced text rendering
        - Thought Signatures: Gemini 3 returns encrypted thought signatures for multi-turn
        - Retrieve images from response.content[0]["image_url"]["url"] as data URI (base64)

        **Text-to-Speech (TTS):**
        - Models: gemini-2.5-pro-preview-tts, gemini-2.5-flash-preview-tts
        - Set response_modalities=["AUDIO"] or ["TEXT", "AUDIO"]
        - 30 voices across 24 languages
        - Single or multi-speaker support
        - Retrieve audio from response.additional_kwargs["audio"] as base64 PCM

        **Not Supported via ChatGoogleGenerativeAI:**
        - Computer Use (Browser Automation): Optional extension in extensions/google_computer_use
          (Heavy dependencies: Playwright ~200MB + Chromium ~400MB)
          Model: gemini-2.5-computer-use-preview-10-2025, 70% accuracy benchmark
          Install when needed: cd extensions/google_computer_use && uv pip install -e ".[playwright]"
        - Video Generation (Veo 3.1): Requires google_media_factory with async operations
        - Native Audio Streaming (Live API): Requires google_live_api with WebSocket client
        - Gemini Nano: On-device only (Android/mobile via ML Kit), no cloud API
    """
    llm: BaseChatModel

    if provider == "openai":
        # Check if model supports reasoning_effort and verbosity parameters
        # Only GPT-5, o1, o3 models support these. GPT-4.1 does NOT.
        supports_reasoning_params = any(m in model for m in ["gpt-5", "o1", "o3"])

        if supports_reasoning_params:
            # GPT-5/o1/o3 models with reasoning parameters
            # Prompt caching is AUTOMATIC for 1024+ token prompts (no config needed)
            llm = ChatOpenAI(  # type: ignore[call-arg]
                model=model,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                verbosity=verbosity,
                timeout=timeout,
                max_retries=max_retries,
            )
        else:
            # GPT-4.1 and other models (standard configuration)
            # Prompt caching is AUTOMATIC for 1024+ token prompts (no config needed)
            # GPT-4.1 has BEST caching: 75% discount vs 50% for GPT-5
            llm = ChatOpenAI(  # type: ignore[call-arg]
                model=model,
                temperature=temperature,
                timeout=timeout,
                max_retries=max_retries,
            )
    elif provider == "anthropic":
        # Enable prompt caching for cost and latency benefits
        llm = ChatAnthropic(
            model=model,
            temperature=temperature,
            timeout=timeout,  # type: ignore[call-arg]
            max_retries=max_retries,
            model_kwargs={
                "extra_headers": {"anthropic-beta": "prompt-caching-2024-07-31"}
            },
        )
    elif provider == "google":
        # Google Gemini models with full parameter support
        # Supports all Gemini 2.5 and 2.0 models with multimodal capabilities

        # Build kwargs dict with only provided parameters
        gemini_kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
        }

        # CRITICAL: Disable thinking by default for Flash/Flash-Lite models
        # Gemini 2.5 has adaptive thinking enabled by default which wastes time/money
        # Set thinking_budget=0 to disable (only works for Flash/Flash-Lite, not Pro)
        if thinking_budget is None:
            thinking_budget = 512

        # Add optional parameters only if provided
        if timeout is not None:
            gemini_kwargs["timeout"] = timeout
            # Also set request_timeout for GeminiWithRetry's enforced timeout
            # (Gemini's native timeout is broken, so we enforce it ourselves)
            gemini_kwargs["request_timeout"] = timeout
        if top_p is not None:
            gemini_kwargs["top_p"] = top_p
        if top_k is not None:
            gemini_kwargs["top_k"] = top_k
        if max_output_tokens is not None:
            gemini_kwargs["max_output_tokens"] = max_output_tokens
        if thinking_budget is not None:
            gemini_kwargs["thinking_budget"] = thinking_budget
        if include_thoughts:
            gemini_kwargs["include_thoughts"] = include_thoughts
        if safety_settings is not None:
            gemini_kwargs["safety_settings"] = safety_settings
        if response_modalities is not None:
            # Convert string modalities to enum values
            modality_map = {
                "TEXT": Modality.TEXT,
                "IMAGE": Modality.IMAGE,
                "AUDIO": Modality.AUDIO,
            }
            converted_modalities = [modality_map[m] for m in response_modalities]
            gemini_kwargs["response_modalities"] = converted_modalities
        if response_mime_type is not None:
            gemini_kwargs["response_mime_type"] = response_mime_type

        # Gemini 3 Image Generation configuration
        # Build image_config for generation_config if image params provided
        if image_aspect_ratio is not None or image_size is not None:
            image_config: dict[str, Any] = {}
            if image_aspect_ratio is not None:
                image_config["aspectRatio"] = image_aspect_ratio
            if image_size is not None:
                image_config["imageSize"] = image_size
            # Pass through model_kwargs for generation_config.imageConfig
            if "model_kwargs" not in gemini_kwargs:
                gemini_kwargs["model_kwargs"] = {}
            model_kwargs = gemini_kwargs["model_kwargs"]
            if isinstance(model_kwargs, dict):
                model_kwargs["generation_config"] = {"imageConfig": image_config}

        # Add retry configuration for blank response handling
        gemini_kwargs["max_retries"] = max_retries
        gemini_kwargs["retry_base_delay"] = retry_base_delay

        llm = GeminiWithRetry(**gemini_kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    return llm
