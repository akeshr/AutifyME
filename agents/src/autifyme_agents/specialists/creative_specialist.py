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
- Has inspect_schema (scoped to assets/product_assets) for schema discovery
- Has write_data (scoped to assets) for persisting processed images
- Has read_data (scoped to assets + product_assets) for reference
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
from autifyme_agents.tools.protocol_loader import create_load_protocol_tool

if TYPE_CHECKING:
    from autifyme_agents.core.ports import StorageInterface
    from autifyme_agents.schemas.models import CompanyProfile

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
    company_profile: "CompanyProfile",
    model: str | BaseChatModel | None = None,
    storage: "StorageInterface | None" = None,
) -> dict[str, Any]:
    """Create Creative Specialist SubAgent spec.

    The specialist uses view_image tool to see images from storage_path.
    PM passes storage_path in task description, specialist calls view_image to see it.

    Args:
        model: Optional LLM override. Defaults to Gemini 3 Flash (multimodal).
        storage: Optional storage client for image persistence to Supabase.
        company_profile: Company context for brand colors, logo, etc.

    Returns:
        SubAgent spec dict: {name, description, tools, system_prompt, model}
    """
    if company_profile is None:
        raise ValueError("company_profile is required for Creative Specialist (single-tenant)")

    # Load and format prompt with company context
    prompt_template = load_prompt("specialists/creative_specialist_lean.prompt")
    vi = company_profile.visual_identity

    system_prompt = prompt_template.format(
        company_name=company_profile.name,
        industry=company_profile.industry or "Product Manufacturing",
        primary_color=vi.primary_color,
        secondary_color=vi.secondary_color,
        accent_color=vi.accent_color or "None",
        font_family=vi.font_family,
        logo_asset_path=vi.logo_asset_path or "Not configured",
    )

    # Tools - load_protocol first for protocol-driven reasoning
    tools: list[Any] = [
        create_load_protocol_tool(),  # Protocol loading for domain grounding
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
        "ROLE: Specialist (execution) - World-class visual artist\n"
        "MISSION: Transform raw product photos into portfolio-worthy visual assets.\n\n"
        "OPERATING MODE: ASSESS -> ENVISION -> PROPOSE -> EXECUTE -> CRITIQUE -> ITERATE\n"
        "- ASSESS: View image, see current state AND potential\n"
        "- ENVISION: Form creative vision before touching tools\n"
        "- PROPOSE: Proactively suggest beyond the brief\n"
        "- EXECUTE: Apply 12-spec creative palette\n"
        "- CRITIQUE: Score against excellence rubric (all 8+ to ship)\n"
        "- ITERATE: Fix weak dimensions, never ship mediocre\n\n"
        "OWNERSHIP:\n"
        "- Visual asset creation: extraction, enhancement, hero shots, lifestyle scenes\n"
        "- Visual QA with quality scoring (composition, lighting, material, edges)\n"
        "- Asset records with HITL approval\n\n"
        "TOOLS:\n"
        "- load_protocol (domain expertise when needed)\n"
        "- view_image (ALWAYS before and after processing)\n"
        "- image_studio (12-spec creative palette)\n"
        "- If storage: inspect_schema, read_data, write_data (HITL for writes)\n\n"
        "GUARDRAILS:\n"
        "- No catalog CRUD; delegate to catalog_specialist for product records"
    )
    # Use provided model or default to Gemini 3 Flash (multimodal)
    # Medium thinking: creative tasks are structured (HITL safety net), don't need deep reasoning
    specialist_model = model if model is not None else get_llm(
        provider="google",
        model=CREATIVE_SPECIALIST_MODEL,
        thinking_level="medium",  # Balanced: creative quality + speed (HITL provides safety)
    )

    middleware = [
        *create_execution_limits(model_call_limit=50, tool_call_limit=30),
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
