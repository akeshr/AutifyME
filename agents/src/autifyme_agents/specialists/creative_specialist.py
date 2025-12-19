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
from autifyme_agents.middleware import create_execution_limits
from autifyme_agents.tools import create_view_image_tool
from autifyme_agents.tools.image_studio import create_image_studio_tool

if TYPE_CHECKING:
    from autifyme_agents.core.ports import StorageInterface

# Creative Specialist uses Gemini 3 Flash for multimodal reasoning (can see images)
CREATIVE_SPECIALIST_MODEL = "gemini-3-flash-preview"

# Tables accessible by Creative Specialist
CREATIVE_READ_TABLES = [
    "assets",           # Read existing assets
    "product_assets",   # Read product-asset links (product_id -> asset_id)
    "products",         # Read products to resolve family_id -> product_ids
    "product_families", # Read product families for context
    "campaign_assets",  # Read campaign creative assets
    "campaigns",        # Read campaigns for asset context
]

CREATIVE_WRITE_TABLES = [
    "assets",           # Create asset records for processed images
    "campaign_assets",  # Create campaign creative assets
]


def create_creative_specialist(
    model: str | BaseChatModel | None = None,
    storage: "StorageInterface | None" = None,
) -> dict[str, Any]:
    """Create Creative Specialist SubAgent spec.

    The specialist uses view_image tool to see images from storage_path.
    PM passes storage_path in task description, specialist calls view_image to see it.

    Args:
        model: Optional LLM override. Defaults to Gemini 3 Flash (multimodal).
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
        "ROLE: Specialist (execution)\n"
        "MISSION: Turn raw product photos into marketplace-ready visuals (and optionally persist asset records).\n\n"
        "OWNERSHIP:\n"
        "- Image processing & generation: extraction, cleanup, enhancement, hero shots, lifestyle creatives\n"
        "- Visual QA on outputs (before downstream catalog linking)\n\n"
        "INPUTS I NEED:\n"
        "- Source image storage_path(s) (typically inbox/...)\n"
        "- Creative intent (hero vs lifestyle), output aspect ratio/format if constrained\n\n"
        "OUTPUTS I PRODUCE:\n"
        "- Processed image outputs with paths (always local temp path; storage_path in pending/ when storage is configured)\n"
        "- Notes on what was changed + any visual risks/uncertainties\n"
        "- If long: write a production note to the thread directory and return the file path\n\n"
        "HITL LOOP (when write_data is enabled):\n"
        "- Propose write_data intents for DB changes and wait for approval\n"
        "- On rejection, you will receive user feedback (often prefixed [HITL_FEEDBACK]); revise and resubmit\n\n"
        "TOOLS I USE:\n"
        "- view_image, image_studio\n"
        "- If storage is provided: inspect_schema, read_data, write_data (scoped to creative/asset tables; HITL for writes)\n\n"
        "GUARDRAILS:\n"
        "- No product/pricing/taxonomy CRUD; if a catalog change is needed, delegate to catalog_specialist"
    )
    # Use provided model or default to Gemini 3 Flash (multimodal)
    # Medium thinking: creative tasks are structured (HITL safety net), don't need deep reasoning
    specialist_model = model if model is not None else get_llm(
        provider="google",
        model=CREATIVE_SPECIALIST_MODEL,
        thinking_level="medium",  # Balanced: creative quality + speed (HITL provides safety)
    )

    middleware = [
        *create_execution_limits(model_call_limit=15, tool_call_limit=10),
    ]

    spec: dict[str, Any] = {
        "name": "creative_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        "model": specialist_model,
        "middleware": middleware,
        "interrupt_on": {"write_data": True},  # HITL approval before write_data execution
    }

    return spec
