"""
Creative Specialist - Professional product photographer and image editor.

Domain Ownership ("How We Present"):
- Studio-quality image processing for e-commerce
- Multi-product extraction with professional isolation
- Marketplace-ready hero shots (Amazon, Shopify, Instagram quality)
- Lifestyle and contextual scene generation
- Asset management (create asset records after processing)

Architecture:
- SubAgent spec dict for PM delegation
- Owns image_studio tool (Gemini 3 Pro Image)
- Has inspect_schema (scoped to assets/product_images) for schema discovery
- Has write_data (scoped to assets) for persisting processed images
- Has read_data (scoped to assets + product images) for reference
- Uses view_image tool to see images from storage_path

Storage Architecture:
- Generated images are uploaded to pending/{thread_id}/ immediately
- On write_data with HITL approval, images are moved to products/
- All tools use storage_path (relative path) - URL is derived where needed

Professional Standards:
- Pure white backgrounds for hero shots
- Studio lighting with proper shadows
- Color-accurate, sharpened, enhanced output
- 70-85% product coverage, centered composition
"""

from typing import TYPE_CHECKING, Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools import create_view_image_tool
from autifyme_agents.tools.image_studio import create_image_studio_tool

if TYPE_CHECKING:
    from autifyme_agents.core.ports import StorageInterface

# Creative Specialist uses Gemini 3 Pro for multimodal reasoning (can see images)
CREATIVE_SPECIALIST_MODEL = "gemini-2.5-flash"

# Tables accessible by Creative Specialist
CREATIVE_READ_TABLES = [
    "assets",           # Read existing assets
    "product_assets",   # Read product-asset links (product_id -> asset_id)
    "products",         # Read products to resolve family_id -> product_ids
]

CREATIVE_WRITE_TABLES = [
    "assets",           # Create asset records for processed images
]


def create_creative_specialist(
    model: str | BaseChatModel | None = None,
    storage: "StorageInterface | None" = None,
) -> dict[str, Any]:
    """Create Creative Specialist SubAgent spec.

    The specialist uses view_image tool to see images from storage_path.
    PM passes storage_path in task description, specialist calls view_image to see it.

    Args:
        model: Optional LLM override. Defaults to Gemini 3 Pro (multimodal).
        storage: Optional storage client for image persistence to Supabase.

    Returns:
        SubAgent spec dict: {name, description, tools, system_prompt, model}
    """
    system_prompt = load_prompt("specialists/creative_specialist_lean.prompt")

    tools: list[Any] = [
        create_view_image_tool(),  # Quick inspection without processing
        create_image_studio_tool(storage=storage),  # Professional image processing with persistence
    ]

    # Add scoped data tools if storage is provided
    if storage is not None:
        from autifyme_agents.tools.data_engine import (
            create_inspect_schema_tool,
            create_read_data_tool,
            create_write_data_tool,
        )
        # Schema discovery for write_data - understand table structure before writing
        tools.append(create_inspect_schema_tool(storage, tables=CREATIVE_READ_TABLES))
        # Scoped read access to asset-related tables
        tools.append(create_read_data_tool(storage, tables=CREATIVE_READ_TABLES))
        # Scoped write access to assets table only
        tools.append(create_write_data_tool(storage, tables=CREATIVE_WRITE_TABLES))

    description = (
        "Creative Specialist - professional product photographer creating studio-quality images. "
        "Produces: marketplace-ready hero shots (pure white background, studio lighting, color-accurate), "
        "multi-product extraction with clean isolation, lifestyle shots with contextual scenes. "
        "IMAGE SOURCES (two options): "
        "(1) Include storage_path directly in task - specialist SEES images, OR "
        "(2) Provide product_id or product_family_id - specialist queries to find asset URLs. "
        "Has read_data access to: products (resolve family->products), product_assets (product->asset links), assets (get storage_url). "
        "Returns: processed images with storage_path (in pending/). "
        "Creates asset records via write_data (HITL approval required)."
    )

    # Use provided model or default to Gemini 3 Pro (multimodal)
    specialist_model = model if model is not None else get_llm(
        provider="google",
        model=CREATIVE_SPECIALIST_MODEL,
        temperature=1.0,
    )

    spec: dict[str, Any] = {
        "name": "creative_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        "model": specialist_model,
        "interrupt_on": {"write_data": True},  # HITL approval before write_data execution
    }

    return spec
