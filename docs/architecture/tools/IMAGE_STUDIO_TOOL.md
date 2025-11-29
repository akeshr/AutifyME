# Image Studio Tool Design

**Created:** November 29, 2025
**Status:** Design Complete - Ready for Implementation
**Related:** [SPECIALIST_BUILD_UP_PLAN.md](../workflows/SPECIALIST_BUILD_UP_PLAN.md)

---

## Overview

Unified, atomic image tool that handles all image operations: analysis, generation, enhancement, and composition. Outputs to temp folder - does NOT perform database operations. Specialists use existing DB tools (with HITL) to persist approved assets.

**Design Principles:**
- **Atomic:** Single tool for all image operations
- **Powerful:** Rich Pydantic schemas enable sophisticated outputs
- **Stateless:** No database operations, returns temp paths
- **LLM-friendly:** StructuredTool pattern with full schema introspection
- **Consistent:** Follows data engine tool patterns (factory function, args_schema)

---

## Architecture

```
image_studio (pure processing)
    |
    v
Returns: temp paths + metadata + suggested_asset_data
    |
    v
Specialist self-reviews output
    |
    v
Specialist calls create_record on assets (existing HITL)
    |
    v
User approves -> storage adapter moves temp -> permanent
```

### Separation of Concerns

| Component | Responsibility |
|-----------|---------------|
| **image_studio** | Process/generate images, save to temp, return paths |
| **Specialist** | Self-review, decide quality, call DB tools |
| **create_record** | HITL approval, storage move on commit |
| **PM** | Route feedback to specialist with context |

---

## Job Types

```python
class ImageJobType(str, Enum):
    ANALYZE = "analyze"           # Extract visual attributes
    PRODUCT_SHOT = "product_shot" # Clean catalog image
    LIFESTYLE = "lifestyle"       # AI-generated scene
    COMPOSITE = "composite"       # Layer-based composition
    ENHANCE = "enhance"           # Quality improvement
    RESIZE = "resize"             # Format/dimension conversion
```

---

## Output Schema

```python
class ImageStudioOutput(BaseModel):
    """Single generated/processed image."""
    name: str                    # From OutputSpec.name
    temp_path: str               # Local temp path
    preview_path: str            # Smaller preview for HITL display
    format: str
    dimensions: tuple[int, int]
    size_bytes: int
    operations_applied: list[str]

    # Pre-built for create_record
    suggested_asset_data: dict


class ImageStudioResult(BaseModel):
    """Complete result from image_studio tool."""
    success: bool
    job_type: str

    # For ANALYZE job
    analysis: ImageAnalysisResult | None = None

    # For generation jobs
    outputs: list[ImageStudioOutput] | None = None

    # For regeneration
    job_spec_used: dict

    # Metadata
    processing_time_ms: int
    llm_provider_used: str | None = None
    error: str | None = None
```

---

## Tool Implementation

Uses `StructuredTool` pattern (consistent with data engine tools) for rich schema introspection by LLMs.

### Input Schema (Discriminated Union)

```python
from typing import Annotated, Literal, Union
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, model_validator


class ImageStudioInput(BaseModel):
    """Input schema for image_studio tool - discriminated union by job_type."""

    model_config = {"extra": "forbid"}

    job_type: Literal["analyze", "product_shot", "lifestyle", "composite", "enhance", "resize"] = Field(
        ...,
        description=(
            "Type of image operation:\n"
            "- analyze: Extract visual attributes (colors, materials, style)\n"
            "- product_shot: Generate clean catalog image (white bg, professional)\n"
            "- lifestyle: AI-generate contextual scene with product\n"
            "- composite: Layer-based composition (banners, social)\n"
            "- enhance: Quality improvement (denoise, sharpen, upscale)\n"
            "- resize: Format/dimension conversion only"
        )
    )

    # Common fields (all jobs except composite)
    source: ImageSource | None = Field(
        None,
        description="Source image location. Required for all jobs except composite."
    )

    # Product shot specific
    product_context: dict | None = Field(
        None,
        description="Product info from analysis: name, category, features. Improves generation quality."
    )
    background: BackgroundSpec | None = Field(
        None,
        description="Background settings for product_shot. Defaults to white solid."
    )
    framing: FramingSpec | None = Field(
        None,
        description="How to frame product in output image."
    )

    # Lifestyle specific
    scene: SceneSpec | None = Field(
        None,
        description="Scene settings for lifestyle generation: environment, lighting, mood."
    )
    product_placement: PlacementSpec | None = Field(
        None,
        description="Where/how to place product in lifestyle scene."
    )

    # Composite specific
    layers: list[LayerSpec] | None = Field(
        None,
        description="Layer definitions for composite job."
    )

    # Enhance specific
    operations: list[Literal["denoise", "sharpen", "color_correct", "upscale"]] | None = Field(
        None,
        description="Enhancement operations to apply. Order matters."
    )

    # Common output config
    enhancements: EnhancementSpec | None = Field(
        None,
        description="Image enhancement settings (lighting, sharpness, color)."
    )
    outputs: list[OutputSpec] = Field(
        default_factory=lambda: [OutputSpec(name="master", format="PNG")],
        description="Output specifications. Defaults to single PNG master."
    )

    @model_validator(mode="after")
    def validate_job_requirements(self) -> "ImageStudioInput":
        """Validate required fields per job_type."""
        if self.job_type == "composite":
            if not self.layers:
                raise ValueError("composite job requires 'layers'")
        elif self.job_type != "composite":
            if not self.source:
                raise ValueError(f"{self.job_type} job requires 'source'")

        if self.job_type == "lifestyle" and not self.scene:
            raise ValueError("lifestyle job requires 'scene'")

        if self.job_type == "enhance" and not self.operations:
            raise ValueError("enhance job requires 'operations'")

        return self
```

### Supporting Schemas (Nested Pydantic Models)

```python
class ImageSource(BaseModel):
    """Where to get the source image."""
    type: Literal["local_path", "url", "asset_id"] = Field(
        ..., description="Source type: local_path (temp file), url (download), asset_id (from DB)"
    )
    value: str = Field(..., description="Path, URL, or asset UUID")


class BackgroundSpec(BaseModel):
    """Background configuration for product shots."""
    type: Literal["solid", "gradient", "transparent"] = Field(
        default="solid", description="Background type"
    )
    color: str = Field(default="#FFFFFF", description="Hex color for solid/gradient start")
    gradient_end: str | None = Field(None, description="Hex color for gradient end")


class FramingSpec(BaseModel):
    """How to frame product in output."""
    product_coverage_percent: int = Field(
        default=80, ge=50, le=95,
        description="How much of frame product should fill (50-95%)"
    )
    padding_percent: int = Field(
        default=10, ge=5, le=30,
        description="Padding around product (5-30%)"
    )
    alignment: Literal["center", "bottom", "top"] = Field(
        default="center", description="Product alignment in frame"
    )


class SceneSpec(BaseModel):
    """Scene configuration for lifestyle images."""
    environment: str = Field(
        ..., description="Scene description: 'modern kitchen', 'outdoor cafe', 'office desk'"
    )
    lighting: Literal["natural", "studio", "dramatic", "warm", "cool"] = Field(
        default="natural", description="Lighting style"
    )
    mood: str | None = Field(None, description="Mood keywords: 'cozy', 'professional', 'vibrant'")
    style: Literal["photorealistic", "lifestyle", "editorial"] = Field(
        default="photorealistic", description="Visual style"
    )


class PlacementSpec(BaseModel):
    """Product placement in lifestyle scene."""
    position: Literal["center", "foreground", "background", "left", "right"] = Field(
        default="center", description="Where in scene"
    )
    scale: Literal["dominant", "balanced", "subtle"] = Field(
        default="balanced", description="How prominent the product appears"
    )
    interaction: str | None = Field(
        None, description="How product interacts with scene: 'on table', 'held by person'"
    )


class LayerSpec(BaseModel):
    """Layer definition for composite images."""
    type: Literal["background", "product", "text", "overlay"] = Field(
        ..., description="Layer type"
    )
    source: ImageSource | None = Field(None, description="Image source for this layer")
    position: tuple[int, int] | None = Field(None, description="X, Y position in pixels")
    size: tuple[int, int] | None = Field(None, description="Width, height in pixels")
    text: str | None = Field(None, description="Text content for text layers")
    font: str | None = Field(None, description="Font family for text layers")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0, description="Layer opacity")


class EnhancementSpec(BaseModel):
    """Image enhancement settings."""
    lighting: Literal["studio", "natural", "dramatic", "preserve"] = Field(
        default="studio", description="Lighting adjustment"
    )
    sharpness: Literal["low", "medium", "high", "very_high"] = Field(
        default="high", description="Sharpness level"
    )
    color_correction: bool | Literal["preserve_original"] = Field(
        default=True, description="Auto color correction or preserve original"
    )
    brightness: float = Field(default=1.0, ge=0.5, le=1.5, description="Brightness multiplier")


class OutputSpec(BaseModel):
    """Output specification for generated images."""
    name: str = Field(
        default="master", description="Output name: 'master', 'thumbnail', 'social'"
    )
    format: Literal["PNG", "JPEG", "WEBP"] = Field(
        default="PNG", description="Output format"
    )
    dimensions: tuple[int, int] | None = Field(
        None, description="Width x Height. None = preserve original aspect"
    )
    quality: int = Field(default=90, ge=1, le=100, description="Quality for lossy formats")
```

### Tool Factory

```python
def create_image_studio_tool() -> StructuredTool:
    """Create image_studio tool with full schema for LLM introspection.

    Returns:
        StructuredTool with rich Pydantic schema for image operations.
    """

    async def _image_studio_impl(
        job_type: str,
        source: ImageSource | None = None,
        product_context: dict | None = None,
        background: BackgroundSpec | None = None,
        framing: FramingSpec | None = None,
        scene: SceneSpec | None = None,
        product_placement: PlacementSpec | None = None,
        layers: list[LayerSpec] | None = None,
        operations: list[str] | None = None,
        enhancements: EnhancementSpec | None = None,
        outputs: list[OutputSpec] | None = None,
    ) -> dict:
        """Route to job-specific handlers."""
        # Implementation routes based on job_type
        pass

    return StructuredTool.from_function(
        coroutine=_image_studio_impl,
        name="image_studio",
        description=(
            "Unified image tool: analyze, generate, transform.\n\n"
            "ATOMIC & POWERFUL: One tool for all image operations.\n"
            "STATELESS: Outputs to temp folder, does NOT persist to database.\n\n"
            "WORKFLOW:\n"
            "1. Call this tool to process/generate images\n"
            "2. Self-review output using analyze job if needed\n"
            "3. Call create_record on assets table (HITL triggers)\n"
            "4. On approval, storage adapter moves temp -> permanent"
        ),
        args_schema=ImageStudioInput,
    )
```

---

## Specialist Self-Review Pattern

Specialists validate output quality before triggering user approval:

```
Generate -> Self-Review -> Fix if needed -> HITL when confident
```

### Review Flow

```python
async def handle_image_generation(context: dict) -> dict:
    """Specialist logic with self-review."""

    # 1. Generate product shot
    result = await image_studio({
        "job_type": "product_shot",
        "source": {"type": "local_path", "value": context["source_path"]},
        "outputs": [{"name": "master", "format": "PNG", "dimensions": [2000, 2000]}]
    })

    # 2. Self-review: Analyze the output
    review = await image_studio({
        "job_type": "analyze",
        "source": {"type": "local_path", "value": result["outputs"][0]["temp_path"]}
    })

    # 3. Evaluate quality
    evaluation = evaluate_output(
        source_analysis=context.get("source_analysis"),
        output_analysis=review["analysis"],
        user_request=context["user_request"]
    )

    # 4. Iterate if issues (max 2 attempts)
    if not evaluation["passes"] and evaluation["iteration"] < 2:
        adjusted_spec = adjust_for_issues(result["job_spec_used"], evaluation["issues"])
        return await regenerate(context, adjusted_spec)

    # 5. Confident - trigger HITL
    return {
        "action": "create_asset",
        "data": result["outputs"][0]["suggested_asset_data"],
        "preview_path": result["outputs"][0]["preview_path"],
        "review_context": evaluation
    }
```

### Quality Evaluation Criteria

| Check | Issue | Confidence Impact |
|-------|-------|-------------------|
| Product visibility | product_not_visible | -0.4 |
| Background cleanliness | background_not_clean | -0.3 |
| Color preservation | color_mismatch | -0.2 |
| Quality artifacts | blur/distortion | -0.3 |

### Auto-Fix Adjustments

| Issue | Adjustment |
|-------|------------|
| background_not_clean | removal_strength = "aggressive" |
| quality_artifacts | enhancements.intensity = "subtle" |
| color_mismatch | color_correction = "preserve_original" |
| product_not_visible | product_coverage_percent = 70 |

---

## HITL Integration

### Enhanced create_record Payload

```python
create_record(
    table="assets",
    data={
        "name": "Product Master Shot",
        "asset_type": "PRODUCT_IMAGE",
        "mime_type": "image/png",
        "temp_path": "/tmp/image_studio/abc123.png",  # Storage adapter handles move
        "width": 2000,
        "height": 2000,
        # ... other fields
    },

    # For HITL display
    preview_image_path="/tmp/image_studio/abc123_preview.jpg",

    # Review context for user
    review_context={
        "confidence": 0.85,
        "checks_passed": ["Product visible", "Background clean", "Colors preserved"],
        "iterations": 1,
        "specialist_note": "Generated clean product shot with white background."
    }
)
```

### User Presentation

```
PM: "Here's the product image I've prepared:

[Sends preview image]

I've verified:
- Product visible and centered
- Clean white background
- Original colors preserved
- No quality issues

Reply 'approve' to save, or describe changes needed."
```

---

## Feedback Iteration

Since specialists are stateless, PM provides full context for regeneration:

### PM -> Specialist (on feedback)

```python
{
    "task": "regenerate_image",
    "source_path": "/tmp/raw.jpg",
    "original_job_spec": {...},  # PM stored from previous result
    "user_feedback": "make background cream",
    "product_context": {...}     # From initial analysis
}
```

### Specialist Feedback Processing

```python
def process_feedback(feedback: str, original_spec: dict) -> dict:
    """Parse user feedback and adjust job spec."""

    adjustments = {
        "brighter": {"enhancements.brightness": 1.2},
        "darker": {"enhancements.brightness": 0.8},
        "cream background": {"background.color": "#FFFDD0"},
        "transparent background": {"background.type": "transparent"},
        "crop tighter": {"framing.product_coverage_percent": 90},
        "more padding": {"framing.padding_percent": 20},
        "sharper": {"enhancements.sharpness": "very_high"},
    }

    # LLM can parse complex feedback to spec changes
    # Simple keyword matching for common cases

    return apply_adjustments(original_spec, adjustments, feedback)
```

---

## Storage Flow

### Temp Storage (During Processing)

```
/tmp/image_studio/
    {job_id}/
        {output_name}.{format}       # Full resolution
        {output_name}_preview.jpg    # HITL preview (max 800px)
```

### Permanent Storage (After Approval)

Storage adapter handles move on create_record commit:

```python
class StorageAdapter:
    async def create_record(self, table: str, data: dict) -> dict:
        if table == "assets" and "temp_path" in data:
            # Move from temp to permanent storage
            permanent_url = await self.upload_to_storage(
                local_path=data["temp_path"],
                destination=f"assets/{uuid4()}/{data.get('name', 'asset')}"
            )
            data["storage_url"] = permanent_url
            del data["temp_path"]

        return await self._execute_insert(table, data)
```

---

## LLM Provider Integration

Uses llm_factory with **Gemini 3 Pro** for best quality:

### Primary LLM Configuration

```python
from autifyme_agents.core.llm_factory import get_llm

# Image Generation - Gemini 3 Pro Image (Nano Banana Pro)
# RECOMMENDED: Studio-quality 2K/4K resolution output
llm_generation = get_llm(
    provider="google",
    model="gemini-3-pro-image-preview",
    temperature=0.7,  # Creative variation
    response_modalities=["TEXT", "IMAGE"],  # Enable image output
)

# Image Analysis - Gemini 3 Pro
# Best reasoning for quality assessment and self-review
llm_analysis = get_llm(
    provider="google",
    model="gemini-3-pro-preview",
    temperature=0.3,  # Deterministic analysis
)
```

### Fallback Options

```python
# Fallback: Gemini 2.5 Flash Image (faster, lower cost)
llm_generation_fallback = get_llm(
    provider="google",
    model="gemini-2.5-flash-image-preview",
    temperature=0.7,
    response_modalities=["TEXT", "IMAGE"],
)

# External APIs for specific operations
# Background removal - Replicate (rembg)
# Enhancement - Replicate (Real-ESRGAN)
# These don't use llm_factory - direct API calls
```

### Model Selection Matrix

| Job Type | Primary Model | Fallback | Rationale |
|----------|---------------|----------|-----------|
| analyze | gemini-3-pro-preview | gemini-2.5-flash | Best reasoning for quality assessment |
| product_shot | gemini-3-pro-image-preview | gemini-2.5-flash-image | Studio-quality output |
| lifestyle | gemini-3-pro-image-preview | gemini-2.5-flash-image | Creative scene generation |
| enhance | Replicate (Real-ESRGAN) | - | Specialized upscaling |
| composite | PIL/Pillow | - | Deterministic layering |

---

## Implementation Tasks

1. [ ] Define Pydantic models for all job specs
2. [ ] Implement job routing and validation
3. [ ] Integrate analysis (merge existing image_analysis_tool)
4. [ ] Integrate background removal API
5. [ ] Integrate enhancement APIs
6. [ ] Implement lifestyle generation
7. [ ] Implement composite layering
8. [ ] Add temp file management with cleanup
9. [ ] Add preview generation (resize for HITL)
10. [ ] Update storage adapter for temp -> permanent move
11. [ ] Add review_context to HITL payload
12. [ ] Test self-review pattern
13. [ ] Test feedback iteration

---

## API Options

| Capability | Primary | Fallback | Notes |
|------------|---------|----------|-------|
| Image Generation | Gemini 3 Pro Image | Gemini 2.5 Flash Image | Native multimodal |
| Image Analysis | Gemini 3 Pro | Gemini 2.5 Flash | Vision + reasoning |
| Background Removal | Replicate (rembg) | Remove.bg | Specialized |
| Enhancement | Replicate (Real-ESRGAN) | Topaz | Upscaling |
| Composition | PIL/Pillow | ImageMagick | Deterministic |

---

**Version History:**
- v1.2.0 (2025-11-29): Added Gemini 3 Pro configuration, model selection matrix
- v1.1.0 (2025-11-29): Refactored to StructuredTool pattern with rich Pydantic schemas
- v1.0.0 (2025-11-29): Initial design document
