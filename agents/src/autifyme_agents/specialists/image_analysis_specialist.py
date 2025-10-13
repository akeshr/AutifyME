"""Image analysis specialist using create_agent for consistency.

Replaces simple chain with full agent for observability and middleware support.
"""

import base64
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.schemas.models import CompanyProfile


def _encode_bytes_to_data_uri(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Convert image bytes to base64 data URI for vision models.

    This is serverless-safe - works directly with bytes in memory without filesystem access.

    Args:
        image_bytes: Raw image bytes
        mime_type: MIME type (e.g., "image/jpeg", "image/png")

    Returns:
        Base64 data URI (e.g., "data:image/jpeg;base64,...")
    """
    encoded = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:{mime_type};base64,{encoded}"


def _encode_image_to_data_uri(image_path: str) -> str:
    """Convert local image file to base64 data URI for vision models.

    DEPRECATED: Use _encode_bytes_to_data_uri for serverless compatibility.
    This function is kept for backward compatibility with local testing only.

    Args:
        image_path: Path to local image file

    Returns:
        Base64 data URI (e.g., "data:image/jpeg;base64,...")

    Raises:
        FileNotFoundError: If image file doesn't exist
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Determine MIME type from extension
    ext = path.suffix.lower()
    mime_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }.get(ext, 'image/jpeg')

    with open(path, 'rb') as f:
        image_bytes = f.read()

    return _encode_bytes_to_data_uri(image_bytes, mime_type)


def create_image_analysis_specialist(
    model: BaseChatModel | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Create image analysis specialist as full agent with structured output.

    Uses create_agent for architectural consistency and observability.

    Args:
        model: Optional LLM override (defaults to vision model)
        checkpointer: Optional checkpointer for stateful specialist

    Returns:
        Agent that analyzes images and returns ImageAnalysisResult
    """

    # Use vision-capable model
    llm = model or get_llm(provider="openai", model="gpt-4.1-mini-2025-04-14")
    system_prompt = load_prompt("specialists/image_analysis_specialist.prompt")

    # ✅ Use create_agent with response_format
    agent = create_agent(
        model=llm,
        tools=[],  # Pure vision extraction, no tools
        system_prompt=system_prompt,
        response_format=ImageAnalysisResult,  # Structured output
        checkpointer=checkpointer,
        name="ImageAnalysisSpecialist",
    )

    return agent


def image_analysis_specialist_invoke(
    image_url: str | None = None,
    image_bytes: bytes | None = None,
    mime_type: str | None = None,
    company_profile: "CompanyProfile | dict | None" = None,
    config: dict | None = None,
) -> ImageAnalysisResult:
    """Invoke image analysis specialist with serverless-safe interface.

    Args:
        image_url: HTTPS URL or data URI (optional if image_bytes provided)
        image_bytes: Raw image bytes - PREFERRED for serverless (bypasses /tmp)
        mime_type: MIME type when using image_bytes (e.g., "image/jpeg")
        company_profile: Company context for brand-aware analysis
        config: Runtime config

    Returns:
        Structured image analysis result

    Raises:
        ValueError: If neither image_url nor image_bytes provided
    """
    # Serverless-first approach: prefer bytes over file paths
    if image_bytes:
        # Use bytes directly - serverless-safe, no /tmp dependency
        if not mime_type:
            mime_type = "image/jpeg"  # Default
        image_url = _encode_bytes_to_data_uri(image_bytes, mime_type)

    elif image_url:
        # Convert local file paths to base64 (for local testing only)
        if not image_url.startswith(('http://', 'https://', 'data:')):
            image_url = _encode_image_to_data_uri(image_url)
    else:
        raise ValueError("Either image_url or image_bytes must be provided")

    agent = create_image_analysis_specialist()

    # Build vision input - handle both Pydantic model (production) and dict (tests)
    if company_profile:
        if isinstance(company_profile, CompanyProfile):
            brand_voice = company_profile.brand_voice
            target_audience = company_profile.target_audience
        else:
            # Dict interface for backward compatibility with tests
            brand_voice = company_profile.get("brand_voice", "professional")
            target_audience = company_profile.get("target_audience", "general")
    else:
        brand_voice = "professional"
        target_audience = "general"

    content = f"""Analyze this product image in the context of our brand.

Brand Voice: {brand_voice}
Target Audience: {target_audience}

Extract all visual product attributes including colors, materials, sizes, style, and features."""

    messages = [
        {
            "role": "human",
            "content": [
                {"type": "text", "text": content},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]

    # Invoke agent
    result = agent.invoke({"messages": messages}, config=config or {})

    return result["response"]  # ImageAnalysisResult model
