# Catalog Specialist - Image Studio Contract

**Created:** November 29, 2025
**Status:** Specification for Phase 5 Integration
**Related:**
- [IMAGE_STUDIO_TOOL.md](./IMAGE_STUDIO_TOOL.md)
- [SPECIALIST_BUILD_UP_PLAN.md](../workflows/SPECIALIST_BUILD_UP_PLAN.md)

---

## Overview

This document defines the contract between the Catalog Specialist (Phase 3A) and the Image Studio tool (Phase 5). It establishes clear ownership, responsibilities, and interaction patterns.

---

## Ownership Model

### Catalog Specialist Owns

| Responsibility | Description |
|----------------|-------------|
| Product imagery decisions | When to generate, what type, quality requirements |
| Asset lifecycle | Create, link, organize assets in catalog |
| Self-review loop | Evaluate Image Studio output, iterate if needed |
| HITL presentation | Present assets to user for approval |
| Feedback routing | Receive user feedback, re-invoke Image Studio |

### Image Studio Tool Provides

| Capability | Description |
|------------|-------------|
| Image processing | Background removal, enhancement, resize |
| Image generation | Product shots, lifestyle scenes, composites |
| Image analysis | Extract visual attributes, quality assessment |
| Temp file management | Output to temp paths, cleanup |

---

## Interaction Pattern

### Workflow

```
User sends product image
    |
    v
PM receives, routes to Catalog Specialist
    |
    v
Catalog Specialist:
    1. image_studio(job_type="analyze") -> understand source image
    2. image_studio(job_type="product_shot") -> generate catalog image
    3. image_studio(job_type="analyze") -> self-review output
    4. If quality issues: iterate (max 2 attempts)
    5. write_data(table="assets", ...) -> HITL approval
    |
    v
User approves -> asset persisted, linked to product
    |
    (or)
    v
User provides feedback -> Catalog Specialist re-invokes Image Studio
```

### Self-Review Pattern

```python
# Catalog Specialist pseudo-code
async def process_product_image(source_path: str, product_context: dict):
    # 1. Analyze source
    source_analysis = await image_studio(
        job_type="analyze",
        source={"type": "local_path", "value": source_path}
    )

    # 2. Generate product shot
    generation_result = await image_studio(
        job_type="product_shot",
        source={"type": "local_path", "value": source_path},
        product_context=product_context,
        background={"type": "solid", "color": "#FFFFFF"},
        outputs=[{"name": "master", "format": "PNG", "dimensions": [2000, 2000]}]
    )

    # 3. Self-review
    review = await image_studio(
        job_type="analyze",
        source={"type": "local_path", "value": generation_result.outputs[0].temp_path}
    )

    # 4. Evaluate quality
    evaluation = evaluate_quality(source_analysis, review, product_context)

    if not evaluation.passes and evaluation.iteration < 2:
        # Iterate with adjusted parameters
        return await regenerate_with_adjustments(evaluation.issues)

    # 5. Submit for HITL approval
    return await write_data(
        table="assets",
        data={
            "name": f"{product_context['name']} - Hero",
            "storage_url": generation_result.outputs[0].temp_path,
            "mime_type": "image/png",
            "asset_type": "PRODUCT_IMAGE",
            "width": 2000,
            "height": 2000,
            "status": "ACTIVE"
        },
        preview_image_path=generation_result.outputs[0].preview_path,
        review_context=evaluation.to_dict()
    )
```

---

## Image Studio Input/Output Contract

### Job Types Catalog Specialist Will Use

| Job Type | Purpose | When Used |
|----------|---------|-----------|
| `analyze` | Extract visual attributes | Source understanding, self-review |
| `product_shot` | Clean catalog image | Product imagery generation |
| `lifestyle` | Contextual scene | Marketing-style images |
| `enhance` | Quality improvement | Low-quality source images |

### Input Contract

```python
# Catalog Specialist provides:
ImageStudioInput(
    job_type="product_shot",
    source=ImageSource(type="local_path", value="/tmp/raw.jpg"),
    product_context={
        "name": "PET Bottle 500ml",
        "category": "Containers",
        "material": "PET",
        "colors": ["clear", "blue cap"]
    },
    background=BackgroundSpec(type="solid", color="#FFFFFF"),
    framing=FramingSpec(product_coverage_percent=80, alignment="center"),
    outputs=[OutputSpec(name="master", format="PNG", dimensions=(2000, 2000))]
)
```

### Output Contract

```python
# Image Studio returns:
ImageStudioResult(
    success=True,
    job_type="product_shot",
    outputs=[
        ImageStudioOutput(
            name="master",
            temp_path="/tmp/image_studio/abc123/master.png",
            preview_path="/tmp/image_studio/abc123/master_preview.jpg",
            format="PNG",
            dimensions=(2000, 2000),
            size_bytes=1234567,
            operations_applied=["background_removal", "framing", "enhancement"],
            suggested_asset_data={
                "name": "PET Bottle 500ml - Hero",
                "asset_type": "PRODUCT_IMAGE",
                "mime_type": "image/png",
                "width": 2000,
                "height": 2000
            }
        )
    ],
    job_spec_used={...},  # For feedback iteration
    processing_time_ms=2500,
    llm_provider_used="replicate"
)
```

---

## Feedback Iteration Contract

### PM -> Catalog Specialist (on user feedback)

```python
{
    "task": "regenerate_image",
    "source_path": "/tmp/raw.jpg",
    "original_job_spec": {...},  # PM stored from previous result
    "user_feedback": "make background cream instead of white",
    "product_context": {...}
}
```

### Catalog Specialist Adjustment Logic

| User Feedback | Spec Adjustment |
|---------------|-----------------|
| "cream/beige background" | `background.color = "#FFFDD0"` |
| "transparent background" | `background.type = "transparent"` |
| "brighter" | `enhancements.brightness = 1.2` |
| "crop tighter" | `framing.product_coverage_percent = 90` |
| "more padding" | `framing.padding_percent = 20` |
| "sharper" | `enhancements.sharpness = "very_high"` |

---

## Quality Evaluation Criteria

Catalog Specialist evaluates Image Studio output using:

| Check | Source | Issue | Action |
|-------|--------|-------|--------|
| Product visible | analyze output | `product_not_visible` | Reduce coverage %, retry |
| Background clean | analyze output | `background_not_clean` | Increase removal_strength |
| Colors preserved | compare source vs output | `color_mismatch` | Set color_correction = preserve |
| No artifacts | analyze output | `quality_artifacts` | Reduce enhancement intensity |
| Correct framing | analyze output | `poor_framing` | Adjust framing params |

### Confidence Scoring

```python
base_confidence = 1.0

# Deductions
if product_not_visible: base_confidence -= 0.4
if background_not_clean: base_confidence -= 0.3
if color_mismatch: base_confidence -= 0.2
if quality_artifacts: base_confidence -= 0.3

# Threshold
if base_confidence >= 0.7:
    # Submit for HITL
else:
    # Iterate (if attempts < 2)
```

---

## HITL Presentation Contract

### Asset Creation Payload

```python
write_data(
    table="assets",
    data={
        "name": "PET Bottle 500ml - Hero",
        "storage_url": "/tmp/image_studio/abc123/master.png",  # Temp path
        "mime_type": "image/png",
        "asset_type": "PRODUCT_IMAGE",
        "width": 2000,
        "height": 2000,
        "is_ai_generated": True,
        "generation_prompt": "product_shot with white background",
        "status": "ACTIVE"
    },
    # HITL display context
    preview_image_path="/tmp/image_studio/abc123/master_preview.jpg",
    review_context={
        "confidence": 0.85,
        "checks_passed": ["product_visible", "background_clean", "colors_preserved"],
        "checks_failed": [],
        "iterations": 1,
        "specialist_note": "Generated clean product shot with white background. Self-review passed."
    }
)
```

### User-Facing Message

```
Here's the product image I've prepared:

[Preview Image]

Quality checks passed:
- Product clearly visible and centered
- Clean white background
- Original colors preserved

Confidence: 85%

Reply 'approve' to save, or describe any changes needed.
```

---

## Storage Flow

### On HITL Approval

```
Catalog Specialist calls write_data
    |
    v
HITL middleware pauses, presents to user
    |
    v
User approves
    |
    v
Storage adapter:
    1. Moves temp_path -> permanent storage
    2. Updates storage_url to permanent URL
    3. Cleans up temp files
    4. Inserts asset record
    |
    v
Catalog Specialist receives success
    |
    v
Catalog Specialist creates product_assets link
```

---

## Error Handling

| Error | Catalog Specialist Response |
|-------|----------------------------|
| Image Studio failure | Report to PM, request alternate image |
| Max iterations reached | Present best attempt with low confidence warning |
| Source image unusable | Flag to PM, request better source |
| Storage upload failure | Retry once, then report error |

---

## Implementation Checklist (Phase 5)

- [ ] Image Studio tool implementation complete
- [ ] Catalog Specialist prompt updated with image_studio instructions
- [ ] Self-review pattern tested
- [ ] Feedback iteration tested
- [ ] HITL preview_image_path support added
- [ ] Storage adapter temp->permanent move implemented
- [ ] review_context displayed in HITL UI
- [ ] Error handling paths verified

---

**Version History:**
- v1.0.0 (2025-11-29): Initial contract specification
