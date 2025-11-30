# Image Studio Tool - Q&A Session

**Created:** November 30, 2025
**Updated:** November 30, 2025
**Status:** All Q&A Resolved - Ready for Implementation
**Purpose:** Document all findings, scenarios, and design decisions

---

## Design Decisions

### Q1: Atomic vs Unified Tool - RESOLVED

**Decision:** Single unified tool with structured Pydantic schema.

**Rationale:**
- Gemini 3 Pro Image (Nano Banana Pro) handles all operations via one model
- Structured JSON input (not string instructions) maintains atomicity at the interface level
- One powerful LLM = One powerful tool
- Specialist orchestrates by constructing appropriate input schema

### Q2: Tool Interface - RESOLVED

**Decision:** Fully structured Pydantic schema with photography/technical attributes.

**NO string instructions.** All parameters are typed fields:
- `BackgroundSpec` - background configuration
- `LightingSpec` - lighting configuration
- `FramingSpec` - product framing
- `EnhancementSpec` - image enhancements
- `SceneSpec` - lifestyle scene settings
- `ProductPlacement` - product placement in scene
- `AnalysisAttributes` - what to extract
- `OutputSpec` - output configuration

### Q3-Q4: MVP Scope - RESOLVED

**Decision:** All operations in MVP (analyze, edit, generate).

**Rationale:** Gemini 3 Pro Image handles all operations via one model. No need to defer - single API call regardless of operation type.

| Operation | MVP | Use Case |
|-----------|-----|----------|
| `analyze` | Yes | Extract product attributes, quality check |
| `edit` | Yes | Background removal, enhancement, cleanup |
| `generate` | Yes | Lifestyle shots, scene placement |

### Q5-Q7: API/Model - RESOLVED

**Decision:** Gemini 3 Pro Image (Nano Banana Pro) for all operations.

**Model ID:** `gemini-3-pro-image-preview`

**Why single model:**
- One API handles analyze + edit + generate
- No need for multiple providers (Remove.bg, Replicate, etc.)
- Simpler integration, single API key
- State-of-the-art: 1K/2K/4K output, text rendering, up to 14 reference images
- Character consistency across generations

**LLM Factory Usage:**
```python
llm = get_llm(
    provider="google",
    model="gemini-3-pro-image-preview",
    response_modalities=["TEXT", "IMAGE"],  # Enable image output
)

# Retrieve image from response:
# response.additional_kwargs["image"]  # base64 encoded
```

**Important - Thought Signatures:**
Gemini 3 requires returning "Thought Signatures" in multi-turn conversations. The LLM factory handles this automatically via LangChain's message history.

---

## Finalized Schema

### Input Schema

```python
class ImageOperation(str, Enum):
    ANALYZE = "analyze"      # Extract visual attributes
    GENERATE = "generate"    # Create new image (lifestyle)
    EDIT = "edit"            # Modify existing image

class BackgroundSpec(BaseModel):
    type: Literal["solid", "gradient", "transparent", "blur", "scene"] = "solid"
    color: str = "#FFFFFF"
    gradient_end: str | None = None
    blur_strength: Literal["light", "medium", "heavy"] | None = None

class LightingSpec(BaseModel):
    type: Literal["studio", "natural", "dramatic", "soft", "hard"] = "studio"
    direction: Literal["front", "side", "back", "top", "ambient"] = "front"
    intensity: Literal["low", "medium", "high"] = "medium"
    color_temperature: Literal["warm", "neutral", "cool"] = "neutral"

class FramingSpec(BaseModel):
    product_coverage_percent: int = Field(default=80, ge=50, le=95)
    padding_percent: int = Field(default=10, ge=5, le=30)
    alignment: Literal["center", "bottom", "top", "left", "right"] = "center"
    angle: Literal["front", "45deg", "side", "top-down", "hero"] = "front"

class EnhancementSpec(BaseModel):
    sharpness: Literal["none", "subtle", "medium", "high"] = "medium"
    contrast: Literal["none", "subtle", "medium", "high"] = "subtle"
    saturation: Literal["none", "subtle", "medium", "high"] = "none"
    denoise: bool = False
    upscale: Literal["none", "2x", "4x"] = "none"
    color_correction: bool = True

class SceneSpec(BaseModel):
    environment: Literal[
        "kitchen", "living_room", "office", "outdoor",
        "restaurant", "retail", "warehouse", "studio"
    ]
    style: Literal["modern", "traditional", "minimalist", "rustic", "industrial"] = "modern"
    mood: Literal["professional", "cozy", "vibrant", "elegant", "casual"] = "professional"
    time_of_day: Literal["morning", "afternoon", "evening", "night"] = "afternoon"

class ProductPlacement(BaseModel):
    position: Literal["center", "foreground", "left", "right", "table", "shelf"] = "center"
    scale: Literal["dominant", "balanced", "subtle"] = "balanced"
    surface: Literal["table", "counter", "floor", "shelf", "hand", "floating"] | None = None

class AnalysisAttributes(BaseModel):
    colors: bool = True
    materials: bool = True
    dimensions: bool = True
    condition: bool = True
    brand_text: bool = True
    product_category: bool = True
    quality_score: bool = True
    background_type: bool = True
    custom_attributes: list[str] = Field(default_factory=list)

class OutputSpec(BaseModel):
    format: Literal["PNG", "JPEG", "WEBP"] = "PNG"
    size: Literal["1K", "2K", "4K"] = "2K"
    aspect_ratio: Literal["1:1", "3:4", "4:3", "9:16", "16:9"] = "1:1"
    quality: int = Field(default=90, ge=1, le=100)
    variants: list[Literal["master", "thumbnail", "social"]] = Field(
        default_factory=lambda: ["master"]
    )

class ImageStudioInput(BaseModel):
    operation: ImageOperation
    source_image: str | None = None
    reference_images: list[str] = Field(default_factory=list)

    # Operation-specific specs
    background: BackgroundSpec | None = None
    lighting: LightingSpec | None = None
    framing: FramingSpec | None = None
    enhancement: EnhancementSpec | None = None
    scene: SceneSpec | None = None
    placement: ProductPlacement | None = None
    analysis: AnalysisAttributes | None = None

    output: OutputSpec = Field(default_factory=OutputSpec)
```

### Output Schema

```python
class ImageMetadata(BaseModel):
    width: int
    height: int
    format: str
    size_bytes: int
    aspect_ratio: str

class AnalysisResult(BaseModel):
    colors: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    dimensions: str | None = None
    condition: str | None = None
    brand_text: list[str] = Field(default_factory=list)
    product_category: str | None = None
    background_type: str | None = None
    quality_score: float = Field(ge=0.0, le=1.0, default=0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    custom_attributes: dict = Field(default_factory=dict)

    # Multi-product detection
    product_count: int = 1
    multi_product_warning: str | None = None

class OutputVariant(BaseModel):
    variant: str  # "master", "thumbnail", "social"
    path: str
    preview_path: str
    metadata: ImageMetadata

class ImageStudioOutput(BaseModel):
    success: bool
    operation: ImageOperation

    # For generate/edit operations
    outputs: list[OutputVariant] = Field(default_factory=list)

    # For analyze operation
    analysis: AnalysisResult | None = None

    # For asset creation
    suggested_asset_data: dict | None = None

    # Warnings and errors
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    error_code: str | None = None
```

---

## Scenarios Validation

### Product Onboarding Scenarios

| # | Scenario | Schema Input | Status |
|---|----------|--------------|--------|
| 1 | Phone photo, good quality | `operation=analyze, analysis=AnalysisAttributes()` | OK |
| 2 | Phone photo, messy background | `operation=edit, background=BackgroundSpec(type="solid"), enhancement=EnhancementSpec()` | OK |
| 3 | Phone photo, low quality | `operation=edit, enhancement=EnhancementSpec(denoise=True, sharpness="high", upscale="2x")` | OK |
| 4 | Multiple products in frame | `operation=analyze` -> `AnalysisResult.product_count > 1` | OK |
| 5 | No image provided | Skip tool | OK |
| 6 | Need thumbnails | `output=OutputSpec(variants=["master", "thumbnail"])` | OK |
| 7 | User feedback: "brighter" | `operation=edit, lighting=LightingSpec(intensity="high")` | OK |
| 8 | Need lifestyle shot | `operation=generate, scene=SceneSpec(...), placement=ProductPlacement(...)` | OK |

### Error Scenarios

| # | Scenario | Output Handling |
|---|----------|-----------------|
| E1 | File not found | `success=False, error="File not found", error_code="FILE_NOT_FOUND"` |
| E2 | Corrupt image | `success=False, error="Corrupt image", error_code="CORRUPT_FILE"` |
| E3 | Too small (<200px) | `success=True, warnings=["Image resolution low (180x180)"]` |
| E4 | Too large (>20MB) | Auto-resize, `warnings=["Auto-resized from 25MB"]` |
| E5 | API rate limit | `success=False, error_code="RATE_LIMIT"` |
| E6 | API timeout | `success=False, error_code="TIMEOUT"` |
| E7 | Background removal fails | `success=True, warnings=["Background removal partial"]` |
| E8 | No product detected | `analysis.confidence < 0.5, warnings=["No clear product detected"]` |

---

## Remaining Questions

### Category 4: Self-Review Pattern - RESOLVED

- [x] **Q8:** How does specialist decide quality?

  **Decision:** Option A - Specialist uses `analyze` on output + LLM reasoning.

  **Flow:**
  ```
  1. Generate/Edit image
  2. Analyze output -> get quality_score, warnings
  3. If quality_score < 0.7 OR critical warnings -> retry with adjusted params
  4. If quality_score >= 0.7 -> proceed to HITL
  ```

  **Quality Thresholds:**
  - `quality_score >= 0.7` = Good enough for HITL
  - `quality_score >= 0.5 < 0.7` = Retry with adjustments
  - `quality_score < 0.5` = Warn user, ask for better source

- [x] **Q9:** Max iterations = 2

  **Decision:** Max 2 retry attempts, then proceed to HITL with warnings.

  **Rationale:** Avoid infinite loops. After 2 retries, let user decide.

### Category 5: File Management - RESOLVED

- [x] **Q10:** Temp storage location?

  **Decision:** Same directory as WhatsApp media downloads.

  ```python
  # From whatsapp_media_client.py - reuse existing pattern
  if platform.system() == "Windows":
      MEDIA_DIR = Path(tempfile.gettempdir()) / "media_downloads"
  else:
      MEDIA_DIR = Path("/tmp/media_downloads")
  ```

  **Naming convention:** `{timestamp}_{operation}_{uuid}.{ext}`
  - Example: `20251130_143022_edit_abc123.png`

  **Rationale:** Consistency with existing WhatsApp media flow. Same directory, same cleanup expectations.

- [x] **Q11:** Cleanup strategy?

  **Decision:** Hybrid approach aligned with existing HITL flow.

  | Event | Action |
  |-------|--------|
  | HITL Approval | Delete temp after Supabase upload |
  | HITL Rejection | Leave for OS temp cleanup |
  | Timeout (24h) | OS temp cleanup handles |
  | Error during processing | Leave for OS cleanup |

  **Rationale:** No custom cleanup daemon. Consistent with WhatsApp media handling. Temp directories are ephemeral by design.

### Category 6: Integration - RESOLVED

- [x] **Q12:** Does write_data support temp_path -> permanent upload?

  **Decision:** Not yet - extend storage client.

  **Current state:** `SupabaseStorageClient` handles database operations only. File upload to Supabase Storage not implemented.

  **Required extension:**
  ```python
  # Add to SupabaseStorageClient
  async def upload_asset(
      self,
      temp_path: Path,
      bucket: str = "assets",
      folder: str = "products",
  ) -> str:
      """Upload file to Supabase Storage, return public URL."""
      # Uses: self._client.storage.from_(bucket).upload(...)
  ```

  **Integration with write_data:**
  - WriteIntent includes `temp_file_path` for asset records
  - On HITL approval, upload file first, then insert asset record with storage URL
  - Atomic: if upload fails, don't create asset record

- [x] **Q13:** How is preview image displayed in HITL?

  **Decision:** Images MUST be sent to user as part of HITL request.

  **Critical:** User cannot approve/reject what they cannot see. Generated images are sent alongside the approval message.

  **Flow:**
  ```
  1. Image Studio generates output -> saves to temp_path
  2. Specialist includes temp_path in WriteIntent.asset_previews
  3. HITL middleware builds approval request
  4. Channel adapter SENDS images to user:
     - WhatsApp: Send image message(s) BEFORE approval prompt
     - Web: Include base64 images in approval payload
  5. User SEES images, then approves/rejects/comments
  6. Comments like "make it brighter" trigger retry with adjusted params
  ```

  **WriteIntent extension:**
  ```python
  class WriteIntent(BaseModel):
      # ... existing fields ...
      asset_previews: list[str] = Field(default_factory=list)  # temp paths to display
  ```

  **WhatsApp HITL Message Sequence:**
  ```
  [Image 1: product_enhanced.png]
  [Image 2: lifestyle_kitchen.png]

  "Here's what I've prepared:
   1. Enhanced product photo (white background)
   2. Lifestyle shot (kitchen setting)

   Reply:
   - 'approve' to save these
   - 'reject' to discard
   - Or describe changes (e.g., 'make background warmer')"
  ```

### Category 7: Limits & Fallbacks - RESOLVED

- [x] **Q14:** Rate limiting strategy?

  **Decision:** Tool-level rate limiting + respect Gemini API limits.

  **Configuration:**
  ```python
  IMAGE_STUDIO_RATE_LIMIT = {
      "requests_per_minute": 10,  # Conservative default
      "burst_limit": 3,           # Max concurrent
      "retry_after_seconds": 30,  # On 429
  }
  ```

  **Implementation:**
  - Token bucket at tool factory level
  - Queue overflow returns structured error:
    ```python
    {"success": False, "error_code": "RATE_LIMIT", "retry_after": 30}
    ```
  - Gemini API has ~10 RPM per model (varies by tier)

- [x] **Q15:** Fallback when API fails?

  **Decision:** Graceful degradation - never block product creation.

  | Failure Type | Response |
  |--------------|----------|
  | Transient (timeout, 5xx) | Return error with `retry_after`, specialist decides |
  | Rate limit (429) | Return error with `retry_after` from API |
  | Persistent (auth, quota) | Return error, flag in warnings, proceed without image |
  | Content policy | Return error with explanation, proceed without image |

  **Critical principle:** Image processing is enhancement, not requirement.
  - Product can be created without processed image
  - Original image preserved as fallback
  - Specialist adds warning to WriteIntent if image processing failed

---

## Implementation Checklist

- [x] Update LLM factory with Gemini 3 Pro Image (`gemini-3-pro-image-preview`)
- [x] Create Pydantic schemas in `tools/image_studio/schemas.py`
- [x] Implement tool factory `create_image_studio_tool()`
- [x] Implement operation handlers (analyze, edit, generate)
- [x] Add temp file management (uses same dir as WhatsApp media)
- [x] Add to Catalog Specialist
- [x] Extend storage client with `upload_asset` (for HITL approval flow)
- [ ] Test end-to-end scenarios

---

**Completed:** Nov 30, 2025

**Remaining:**
1. Extend storage client with `upload_asset` for Supabase Storage
2. Test end-to-end product onboarding with real images
