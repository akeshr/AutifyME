"""Image analysis specialist using create_agent for consistency.

Replaces simple chain with full agent for observability and middleware support.
"""

import base64
import re
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

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
        response_format=ToolStrategy(
            schema=ImageAnalysisResult,
            handle_errors=True  # v1.0: Self-healing structured outputs
        ),
        checkpointer=checkpointer,
        name="ImageAnalysisSpecialist",
    )

    return agent


def image_analysis_specialist_invoke(
    image_url: str | None = None,
    image_bytes: bytes | None = None,
    mime_type: str | None = None,
    company_profile: CompanyProfile | dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
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

    structured_response: ImageAnalysisResult = result["structured_response"]
    return structured_response


def create_image_analysis_specialist_graph(
    company_profile: CompanyProfile | dict[str, Any] | None = None,
) -> RunnableLambda[dict[str, Any], dict[str, Any]]:
    """Create image analysis specialist as CustomSubAgent graph.

    This creates a Runnable graph that bridges the gap between:
    - Department delegation (passes file path string in message)
    - Vision model requirements (needs bytes or data URI)

    The graph:
    1. Extracts file path from delegation message
    2. Reads bytes from REAL OS filesystem (Python open())
    3. Invokes specialist with bytes (no virtual filesystem)
    4. Returns structured result in LangGraph state format

    Args:
        company_profile: Company context for brand-aware analysis

    Returns:
        RunnableLambda suitable for DeepAgents CustomSubAgent["graph"]

    Example:
        >>> # In cataloging_department.py
        >>> subagents = [{
        ...     "name": "image_analysis_specialist",
        ...     "description": "Analyze product images...",
        ...     "graph": create_image_analysis_specialist_graph(company_profile)
        ... }]
    """

    def analyze_image_from_state(state: dict[str, Any]) -> dict[str, Any]:
        """Process image analysis from department delegation state.

        Extracts file path from delegation message, reads bytes from real OS filesystem,
        and invokes vision analysis.

        Args:
            state: LangGraph state with messages containing file path in delegation text

        Returns:
            Updated state with analysis result

        Raises:
            ValueError: If no file path found in delegation message
            FileNotFoundError: If file path doesn't exist on filesystem
        """
        # Extract delegation message
        messages = state.get("messages", [])
        if not messages:
            raise ValueError("No messages in state - cannot extract file path")

        # Get last human message content
        last_message = messages[-1]
        content = last_message.content if hasattr(last_message, "content") else str(last_message)

        # Extract file path from delegation text
        # Supports both Unix (/tmp/...) and Windows (C:\tmp\...) paths
        patterns = [
            r'/tmp/media_downloads/[^\s]+\.(jpg|jpeg|png|gif|webp)',  # Unix specific
            r'[A-Za-z]:[/\\]tmp[/\\]media_downloads[/\\][^\s]+\.(jpg|jpeg|png|gif|webp)',  # Windows specific
            r'/tmp/[^\s]+\.(jpg|jpeg|png|gif|webp)',  # Unix generic
            r'[A-Za-z]:[/\\]tmp[/\\][^\s]+\.(jpg|jpeg|png|gif|webp)',  # Windows generic
            r'[A-Za-z]:[/\\][^\s]+\.(jpg|jpeg|png|gif|webp)',  # Windows any path
        ]

        match = None
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                break

        if not match:
            raise ValueError(
                f"No image file path found in delegation message. "
                f"Expected file path like '/tmp/media_downloads/xyz.jpg' or 'C:\\tmp\\xyz.jpg'. "
                f"Got: {content[:200]}"
            )

        file_path = match.group(0)

        # Read bytes from REAL OS filesystem (not DeepAgents virtual state["files"])
        # This is efficient: bytes only live in memory during vision API call
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Image file not found on filesystem: {file_path}. "
                f"Ensure download_whatsapp_media completed successfully."
            )

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

        # Invoke specialist function with bytes
        # Bytes are converted to base64 data URI internally, then sent to vision model
        # No state bloat - bytes discarded after API call
        result = image_analysis_specialist_invoke(
            image_bytes=image_bytes,
            mime_type=mime_type,
            company_profile=company_profile
        )

        # Return result in LangGraph state format
        # DeepAgents expects either:
        # - messages: list of new messages
        # - structured_response: Pydantic model
        return {
            "messages": [
                AIMessage(
                    content=f"Analyzed product image at {file_path}. "
                    f"Visual description: {result.visual_description[:100]}..."
                )
            ],
            "structured_response": result,
        }

    # Wrap function as Runnable for DeepAgents compatibility
    return RunnableLambda(analyze_image_from_state)
