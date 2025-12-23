"""Image Studio Tool - Pydantic Schemas.

Structured schemas with flexible string fields for full creative expression.
Each field provides guidance through examples without restricting values.

Architecture Philosophy:
- Structure guides completeness: Fields remind specialists to consider all aspects
- Flexibility enables creativity: String fields accept any value, not just enums
- Examples inspire: Rich descriptions show what works without limiting options
- Intelligence-First: Model reasons about images based on labels and instructions
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# Image Input - Labeled images for flexible multi-image workflows
# =============================================================================


class ImageInput(BaseModel):
    """Labeled image input for flexible multi-image workflows.

    Each image has a label that the specialist references in their instructions.
    The model receives all images and uses the labels to understand their role.

    Examples:
        ImageInput(path="inbox/product.jpg", label="product")
        ImageInput(path="inbox/style_ref.jpg", label="lighting_reference")
        ImageInput(path="pending/extracted.png", label="background_style")
    """

    path: str = Field(
        description=(
            "Storage path from download_media or image_studio output. "
            "Example: 'inbox/photo.jpg' or 'pending/output.png'"
        )
    )
    label: str = Field(
        description=(
            "Label for this image - referenced in your instructions. "
            "Examples: 'product', 'style_reference', 'lighting_ref', 'background', "
            "'product_variant_1', 'scene_mood', 'texture_sample', 'composition_guide'"
        )
    )


# =============================================================================
# Input Specification Models - Flexible String Fields
# =============================================================================


class BackgroundSpec(BaseModel):
    """Background configuration for edit/generate operations.

    Guides the specialist to think about background treatment without
    restricting to predefined values.
    """

    treatment: str = Field(
        default="solid white",
        description=(
            "How to handle the background. "
            "Examples: 'solid white', 'solid #F5F5F5', 'transparent', "
            "'gradient from warm cream to pure white', 'soft blur of original', "
            "'remove completely', 'replace with marble texture', "
            "'generate modern kitchen scene', 'outdoor cafe setting at golden hour'"
        )
    )
    color: str | None = Field(
        default=None,
        description=(
            "Primary background color if applicable. "
            "Examples: '#FFFFFF', 'pure white', 'warm cream', 'soft gray', "
            "'charcoal', 'brand blue #1E3A8A', 'transparent'"
        )
    )
    scene_description: str | None = Field(
        default=None,
        description=(
            "For scene/environment backgrounds - describe in detail. "
            "Examples: 'modern minimalist kitchen with white marble counters', "
            "'cozy cafe corner with morning light streaming through window', "
            "'professional studio with gradient gray seamless backdrop'"
        )
    )
    custom: str | None = Field(
        default=None,
        description=(
            "Any additional background instructions not covered above. "
            "Use for creative OOTB ideas, special effects, unique treatments."
        )
    )


class LightingSpec(BaseModel):
    """Lighting configuration for professional product photography.

    Lighting is everything in product photography. This structure ensures
    the specialist considers all dimensions of light.
    """

    type: str = Field(
        default="studio",
        description=(
            "Lighting style/setup. "
            "Examples: 'soft studio', 'dramatic side light', 'natural window light', "
            "'hard directional', 'diffused overhead', 'rim lighting with fill', "
            "'split lighting', 'Rembrandt', 'butterfly/paramount', 'loop lighting'"
        )
    )
    direction: str = Field(
        default="45 degrees camera-left",
        description=(
            "Where light comes from relative to product. "
            "Examples: '45 degrees camera-left', 'directly above', 'behind for rim', "
            "'soft frontal fill', 'side lighting from right', 'low angle dramatic', "
            "'window light from left at 10 oclock position'"
        )
    )
    quality: str = Field(
        default="soft",
        description=(
            "Light quality/character. "
            "Examples: 'soft diffused', 'hard specular', 'medium contrast', "
            "'wraparound soft', 'crisp with defined shadows', 'dreamy ethereal'"
        )
    )
    color_temperature: str = Field(
        default="neutral daylight",
        description=(
            "Color temperature/mood. "
            "Examples: 'neutral daylight 5500K', 'warm golden 3200K', 'cool blue', "
            "'warm tungsten', 'mixed warm key cool fill', 'sunset orange'"
        )
    )
    shadows: str = Field(
        default="soft natural",
        description=(
            "Shadow treatment. "
            "Examples: 'soft natural falloff', 'no shadows (flat lit)', "
            "'hard dramatic shadows', 'subtle contact shadow only', "
            "'deep shadows for mood', 'minimal fill to retain dimension'"
        )
    )
    special_requirements: str | None = Field(
        default=None,
        description=(
            "Special lighting needs for specific materials. "
            "Examples: 'rim light for glass edge definition', "
            "'controlled specular for metal surfaces', "
            "'soft gradient reflection for glossy packaging', "
            "'avoid hot spots on reflective label'"
        )
    )
    custom: str | None = Field(
        default=None,
        description=(
            "Any additional lighting instructions not covered above. "
            "Use for creative OOTB ideas, experimental setups, unique effects."
        )
    )


class CompositionSpec(BaseModel):
    """Product framing and composition settings.

    Composition determines visual impact. This structure ensures
    the specialist specifies precise framing requirements.
    """

    product_coverage: str = Field(
        default="80% frame",
        description=(
            "How much of the frame the product should occupy. "
            "Examples: '80% frame', '60% with breathing room', 'tight crop 90%', "
            "'small in scene 30%', 'hero dominant 85%', 'product fills frame edge-to-edge'"
        )
    )
    position: str = Field(
        default="centered",
        description=(
            "Product placement within frame. "
            "Examples: 'centered', 'rule of thirds left', 'bottom third for hero angle', "
            "'offset right with negative space left', 'golden ratio placement', "
            "'anchored bottom center'"
        )
    )
    camera_angle: str = Field(
        default="eye level",
        description=(
            "Camera angle relative to product. "
            "Examples: 'eye level straight on', '45 degree hero angle', "
            "'top-down flat lay', 'low angle looking up (powerful)', "
            "'slight 3/4 view', 'dramatic low angle', 'overhead at 30 degrees'"
        )
    )
    negative_space: str | None = Field(
        default=None,
        description=(
            "Intentional empty space usage. "
            "Examples: 'generous top for text overlay', 'balanced all sides', "
            "'tight crop minimal negative space', 'right side clear for copy', "
            "'breathing room around product'"
        )
    )
    crop_instruction: str | None = Field(
        default=None,
        description=(
            "Specific cropping instructions. "
            "Examples: 'crop to product bounds with 10% padding', "
            "'maintain original framing', 'crop tighter removing excess background', "
            "'square crop centered on label'"
        )
    )
    custom: str | None = Field(
        default=None,
        description=(
            "Any additional composition instructions not covered above. "
            "Use for creative OOTB ideas, unconventional framing, artistic choices."
        )
    )


class EnhancementSpec(BaseModel):
    """Image enhancement settings.

    Post-processing adjustments for professional output quality.
    """

    sharpness: str = Field(
        default="medium",
        description=(
            "Sharpening level. "
            "Examples: 'none', 'subtle', 'medium', 'high', "
            "'tack sharp on product soft on background', "
            "'crisp label details', 'natural without oversharpening'"
        )
    )
    contrast: str = Field(
        default="subtle",
        description=(
            "Contrast adjustment. "
            "Examples: 'none', 'subtle lift', 'medium punch', 'high dramatic', "
            "'flat for editing flexibility', 'S-curve for pop'"
        )
    )
    color_treatment: str = Field(
        default="accurate to source",
        description=(
            "Color handling. FIDELITY WARNING: Product colors must match source. "
            "Examples: 'accurate to source - no grading' (DEFAULT for products), "
            "'true-to-product color accuracy critical', 'preserve exact source colors'. "
            "Scene-only options (NOT for product colors): 'warm ambient', 'cool tones'"
        )
    )
    detail_enhancement: str | None = Field(
        default=None,
        description=(
            "Specific detail improvements. "
            "Examples: 'enhance label text legibility', 'bring out texture detail', "
            "'recover shadow detail', 'denoise smooth areas', "
            "'upscale to 4K maintaining sharpness'"
        )
    )
    cleanup: str | None = Field(
        default=None,
        description=(
            "Cleanup/retouching needs. "
            "Examples: 'remove dust and scratches', 'clean up reflections', "
            "'remove blemishes on product surface', 'none - keep authentic'"
        )
    )
    custom: str | None = Field(
        default=None,
        description=(
            "Any additional enhancement instructions not covered above. "
            "Use for creative OOTB ideas, special filters, artistic treatments."
        )
    )


class SceneSpec(BaseModel):
    """Lifestyle scene settings for generate operation.

    For creating contextual product photography in realistic environments.
    """

    environment: str = Field(
        description=(
            "Scene environment/setting. "
            "Examples: 'modern minimalist kitchen', 'cozy living room', "
            "'professional office desk', 'outdoor garden patio', "
            "'upscale restaurant table', 'clean bathroom vanity', "
            "'rustic farmhouse kitchen', 'bright yoga studio', "
            "'industrial warehouse loft', 'boutique retail display'"
        )
    )
    style: str = Field(
        default="modern",
        description=(
            "Visual style of the scene. "
            "Examples: 'modern minimalist', 'warm rustic', 'sleek contemporary', "
            "'cozy traditional', 'industrial chic', 'Scandinavian clean', "
            "'luxurious elegant', 'casual lifestyle', 'editorial magazine'"
        )
    )
    mood: str = Field(
        default="professional",
        description=(
            "Emotional mood/atmosphere. "
            "Examples: 'professional and clean', 'warm and inviting', "
            "'fresh and energetic', 'calm and serene', 'luxurious and aspirational', "
            "'casual and approachable', 'dramatic and bold'"
        )
    )
    time_of_day: str = Field(
        default="natural daylight",
        description=(
            "Time and lighting context. "
            "Examples: 'bright morning light', 'soft afternoon', 'golden hour warmth', "
            "'moody evening', 'crisp midday', 'dawn freshness', 'twilight ambiance'"
        )
    )
    props_and_context: str | None = Field(
        default=None,
        description=(
            "Contextual elements around the product. "
            "Examples: 'fresh herbs and cutting board nearby', "
            "'coffee cup and open book', 'folded towels and candle', "
            "'laptop and notebook', 'none - product only'"
        )
    )
    custom: str | None = Field(
        default=None,
        description=(
            "Any additional scene instructions not covered above. "
            "Use for creative OOTB ideas, unique environments, fantasy settings."
        )
    )


class ProductPlacementSpec(BaseModel):
    """Product placement in generated scenes.

    How the product sits within the scene environment.
    """

    position: str = Field(
        default="centered hero",
        description=(
            "Where product is placed in scene. "
            "Examples: 'centered hero position', 'on countertop left third', "
            "'in hand being used', 'on shelf display', 'floating hero', "
            "'on table foreground', 'pedestal center stage'"
        )
    )
    scale: str = Field(
        default="dominant",
        description=(
            "How prominent product appears in scene. "
            "Examples: 'dominant - clearly the hero', 'balanced with environment', "
            "'contextual - part of the scene', 'actual realistic size', "
            "'slightly larger than life for impact'"
        )
    )
    surface: str | None = Field(
        default=None,
        description=(
            "What product sits on. "
            "Examples: 'white marble countertop', 'rustic wood table', "
            "'floating/no surface', 'clean glass shelf', 'natural stone', "
            "'fabric draped surface', 'reflective surface for mirror effect'"
        )
    )
    interaction: str | None = Field(
        default=None,
        description=(
            "How product interacts with scene. "
            "Examples: 'casting natural shadow', 'reflection on surface', "
            "'being held by hand', 'leaning against prop', "
            "'surrounded by ingredients', 'isolated on pedestal'"
        )
    )
    custom: str | None = Field(
        default=None,
        description=(
            "Any additional placement instructions not covered above. "
            "Use for creative OOTB ideas, unique positioning, artistic arrangements."
        )
    )


class FidelitySpec(BaseModel):
    """CRITICAL: Product IDENTITY preservation requirements.

    Use this spec WHENEVER working with source product images. This ensures
    the output preserves the product's IDENTITY while fixing photography problems.

    Key distinction:
    - Product Identity (preserve): What makes this THE product - design, colors, shape, features
    - Photography Artifacts (fix): Bad lighting, blur, color cast, poor angles

    Identity > Enhancement. Always.
    """

    preserve_colors: str = Field(
        default="true product colors (fix any color cast from bad lighting)",
        description=(
            "Product color preservation. Fix photography artifacts, preserve actual colors. "
            "Examples: 'true product colors - remove yellow cast from tungsten lighting', "
            "'actual amber honey color - source may have color cast', "
            "'real dusty rose - don't shift to vibrant pink', "
            "'correct white balance to show true product colors'"
        )
    )
    preserve_artwork: str | None = Field(
        default=None,
        description=(
            "Artwork/graphics/prints design that MUST be reproduced exactly. "
            "Sharpen if blurry, but preserve the actual design. "
            "Examples: 'cartoon bee mascot - same pose, same expression, same details', "
            "'honeycomb geometric pattern - exact design even if source is blurry', "
            "'brand logo with text - sharpen but same design'"
        )
    )
    preserve_text: str | None = Field(
        default=None,
        description=(
            "Text/labels that MUST match actual product labeling. "
            "Sharpen if blurry, but same font, same words, same layout. "
            "Examples: 'Wildflower Honey 500ml - sharpen but exact wording and font', "
            "'brand name typography - reveal clearly, same design', "
            "'nutritional info - legible and accurate to actual label'"
        )
    )
    preserve_texture: str | None = Field(
        default=None,
        description=(
            "Surface textures that ARE the product identity. "
            "Enhance visibility, but same texture/pattern. "
            "Examples: 'honeycomb embossed pattern - sharpen, same design', "
            "'matte frosted finish - don't add gloss', 'brushed metal - same grain direction'"
        )
    )
    preserve_shape: str = Field(
        default="actual product shape (fix any camera distortion)",
        description=(
            "Product shape/silhouette - the actual shape, not photo distortion. "
            "Examples: 'true jar shape - fix wide-angle distortion', "
            "'actual proportions - correct any lens barrel distortion', "
            "'real bottle silhouette - this shape IS the brand'"
        )
    )
    hero_features: str | None = Field(
        default=None,
        description=(
            "The 1-3 features that DEFINE this product's identity. "
            "These MUST be visible, sharp, and true to actual product. "
            "Examples: 'honeycomb texture pattern - this IS the brand differentiator', "
            "'wooden dipper and amber honey color - signature look', "
            "'brushed steel finish and minimalist logo - premium identity'"
        )
    )
    fidelity_notes: str | None = Field(
        default=None,
        description=(
            "Additional fidelity requirements or concerns. "
            "Examples: 'customer complained about color drift in past - be extra careful', "
            "'label text is small - must remain legible', 'texture is subtle - preserve without enhancement'"
        )
    )


class ExtractionSpec(BaseModel):
    """Extract specific product(s) from multi-product image.

    For working with group photos containing multiple products/variants.
    """

    target_description: str = Field(
        description=(
            "Describe which product to extract. Be specific. "
            "Examples: 'the red 500ml variant on the left', "
            "'the smaller jar in the foreground', 'the glass bottle (not plastic)', "
            "'all three variants separately', 'just the main hero product in center'"
        )
    )
    position_hint: str | None = Field(
        default=None,
        description=(
            "Where target product is located. "
            "Examples: 'left side of frame', 'center foreground', 'right background', "
            "'the largest one', 'second from left', 'the one being held'"
        )
    )
    isolation: str = Field(
        default="complete isolation",
        description=(
            "How to isolate the product. "
            "Examples: 'complete isolation - remove everything else', "
            "'soft isolation with subtle shadow', 'keep reflection but remove background', "
            "'extract with context preserved'"
        )
    )
    edge_treatment: str = Field(
        default="clean professional",
        description=(
            "How to handle extraction edges. "
            "Examples: 'surgical clean edges', 'natural soft edges', "
            "'slight feathering for natural look', 'hard precise cutout', "
            "'preserve hair/fiber detail'"
        )
    )
    custom: str | None = Field(
        default=None,
        description=(
            "Any additional extraction instructions not covered above. "
            "Use for complex multi-product scenarios, special masking needs."
        )
    )


class FocusSpec(BaseModel):
    """Focus and depth of field specification.

    Control what's sharp and what falls off.
    """

    focus_point: str = Field(
        default="product center",
        description=(
            "Where to focus. "
            "Examples: 'product center', 'front label', 'closest edge to camera', "
            "'product logo', 'entire product sharp', 'cap/lid detail'"
        )
    )
    depth_of_field: str = Field(
        default="product sharp background soft",
        description=(
            "Depth of field treatment. "
            "Examples: 'shallow - product sharp, background creamy bokeh', "
            "'deep - everything sharp', 'medium - product and immediate area sharp', "
            "'very shallow - only label sharp', 'natural falloff front to back'"
        )
    )
    falloff: str | None = Field(
        default=None,
        description=(
            "How sharpness falls off. "
            "Examples: 'gradual natural falloff', 'sharp subject soft everything else', "
            "'front edge sharp, back edge soft', 'no falloff - everything tack sharp'"
        )
    )
    custom: str | None = Field(
        default=None,
        description=(
            "Any additional focus instructions not covered above. "
            "Use for creative OOTB ideas, tilt-shift effects, selective focus."
        )
    )


class MaterialTreatmentSpec(BaseModel):
    """Material-specific rendering instructions.

    Critical for accurate product representation. Different materials
    need different treatment for photorealistic results.
    """

    primary_material: str = Field(
        description=(
            "Main product material. "
            "Examples: 'clear glass', 'frosted glass', 'matte plastic', "
            "'glossy plastic', 'brushed metal', 'polished metal', "
            "'fabric/textile', 'ceramic', 'wood', 'paper/cardboard', 'leather'"
        )
    )
    rendering_notes: str = Field(
        description=(
            "How to treat this material for realism. "
            "Examples: "
            "'Glass: internal caustics, edge refraction, transparency depth, controlled specular', "
            "'Metal: gradient reflections, micro-texture, surface sheen without blowouts', "
            "'Matte plastic: subtle surface texture, diffuse reflection, no hot spots', "
            "'Fabric: weave texture visible, natural drape shadows, soft edges'"
        )
    )
    preserve_details: str | None = Field(
        default=None,
        description=(
            "Specific details to preserve. "
            "Examples: 'label legibility critical', 'embossed logo must be visible', "
            "'color accuracy of product essential', 'texture detail on cap'"
        )
    )
    custom: str | None = Field(
        default=None,
        description=(
            "Any additional material treatment instructions not covered above. "
            "Use for unusual materials, mixed materials, creative interpretations."
        )
    )


class CustomSpec(BaseModel):
    """Fully open-ended creative specification.

    For OOTB (out of the box) creative ideas that don't fit any structured spec.
    Use any key-value pairs you need - complete creative freedom.

    Examples:
        CustomSpec(
            instruction="Create a dreamy double-exposure effect",
            style_reference="Annie Leibovitz portrait lighting",
            color_palette="muted earth tones with pops of teal",
            texture_overlay="subtle film grain",
            artistic_intent="evoke nostalgia and warmth"
        )

        CustomSpec(
            special_effect="product emerging from liquid splash",
            motion_blur="slight motion blur on background",
            surreal_element="impossible shadow angles"
        )
    """

    instruction: str | None = Field(
        default=None,
        description="Primary custom instruction - the main creative idea"
    )
    style_reference: str | None = Field(
        default=None,
        description="Reference to a style, photographer, or aesthetic"
    )
    color_palette: str | None = Field(
        default=None,
        description="Custom color treatment beyond standard specs"
    )
    texture_overlay: str | None = Field(
        default=None,
        description="Texture or grain effects"
    )
    special_effect: str | None = Field(
        default=None,
        description="Special visual effects or treatments"
    )
    artistic_intent: str | None = Field(
        default=None,
        description="The emotional or conceptual goal"
    )
    extra: dict[str, str] | None = Field(
        default=None,
        description=(
            "Any additional key-value pairs for complete creative freedom. "
            "Use this for anything not covered by other fields."
        )
    )


class OutputSpec(BaseModel):
    """Output configuration for generated/edited images.

    API-level parameters that don't affect creative direction.
    """

    format: Literal["PNG", "JPEG", "WEBP"] = "PNG"
    size: Literal["1K", "2K", "4K"] = "2K"
    aspect_ratio: Literal["1:1", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "original"] = "1:1"
    filename: str | None = Field(
        default=None,
        description=(
            "Output filename (without extension). IMPORTANT: Specify this to know the "
            "exact path for view_image and write_data. "
            "Examples: 'mug_hero', 'tumbler_v2', 'product_lifestyle'. "
            "If not specified, auto-generated UUID is used."
        )
    )


# =============================================================================
# Main Input Schema
# =============================================================================


class ImageStudioInput(BaseModel):
    """Unified input schema for Image Studio tool.

    Architecture: Intelligence-First with structured guidance

    - Labeled images: Each image has a label you reference in instructions
    - Structured specs: Guide completeness, accept any string value
    - Model reasons about what to do from specs and labels
    - Creative freedom: custom fields + creative_direction for OOTB ideas

    IMAGES (REQUIRED - minimum 1):
    At least one labeled image required. Reference labels in your specs/instructions.
    The model sees all images and uses labels to understand their role.

    SPECS - Use what applies:
    - extraction: Target product in multi-product images
    - background: Background treatment
    - lighting: Light setup
    - composition: Framing and cropping
    - enhancement: Post-processing
    - scene: Lifestyle environment (for scene generation)
    - placement: Product in scene (for scene generation)
    - focus: Depth of field
    - material_treatment: Material-specific rendering
    - custom_spec: Fully open-ended OOTB ideas
    - creative_direction: Free-form notes

    EXAMPLES:

    1. Extract product with background removal:
    ```python
    ImageStudioInput(
        images=[
            ImageInput(path="inbox/group.jpg", label="source")
        ],
        extraction=ExtractionSpec(
            target_description="the 500ml glass jar on the left in [source]",
            position_hint="left side of frame",
            isolation="complete isolation",
            edge_treatment="surgical clean edges"
        ),
        background=BackgroundSpec(treatment="transparent"),
        material_treatment=MaterialTreatmentSpec(
            primary_material="clear glass",
            rendering_notes="preserve glass edge refraction, internal caustics"
        ),
        composition=CompositionSpec(product_coverage="85% frame", position="centered"),
        output=OutputSpec(format="PNG", size="2K")
    )
    ```

    2. Lifestyle scene with style reference:
    ```python
    ImageStudioInput(
        images=[
            ImageInput(path="inbox/product.jpg", label="product"),
            ImageInput(path="inbox/mood.jpg", label="lighting_ref")
        ],
        scene=SceneSpec(
            environment="modern minimalist kitchen",
            style="match warm tones from [lighting_ref]",
            mood="fresh morning energy",
            time_of_day="bright morning light through window"
        ),
        placement=ProductPlacementSpec(
            position="place [product] on marble counter, left third",
            scale="hero dominant but natural size",
            surface="white marble"
        ),
        lighting=LightingSpec(
            type="natural window light matching [lighting_ref]",
            direction="from left side",
            color_temperature="warm morning 5000K"
        ),
        output=OutputSpec(aspect_ratio="4:3", size="2K")
    )
    ```

    3. Multi-product composition:
    ```python
    ImageStudioInput(
        images=[
            ImageInput(path="inbox/jar1.jpg", label="product_main"),
            ImageInput(path="inbox/jar2.jpg", label="product_variant"),
            ImageInput(path="inbox/background.jpg", label="scene_ref")
        ],
        scene=SceneSpec(
            environment="use [scene_ref] as background style",
            props_and_context="arrange [product_main] center, [product_variant] offset right"
        ),
        composition=CompositionSpec(
            product_coverage="60% frame for family shot",
            position="[product_main] center hero, [product_variant] supporting"
        ),
        creative_direction="Family product shot - main variant hero, second variant supporting"
    )
    ```
    """

    # ==========================================================================
    # Images - Labeled for flexible multi-image workflows
    # ==========================================================================

    images: list[ImageInput] = Field(
        min_length=1,
        description=(
            "REQUIRED: At least 1 labeled image (max 15). Each image has a label "
            "you reference in your specs/instructions. "
            "Example: [ImageInput(path='inbox/photo.jpg', label='product')]"
        )
    )

    # ==========================================================================
    # Structured Specs - Use what applies, leave others as None
    # ==========================================================================

    background: BackgroundSpec | None = Field(
        default=None,
        description="Background treatment specification"
    )

    lighting: LightingSpec | None = Field(
        default=None,
        description="Lighting configuration"
    )

    composition: CompositionSpec | None = Field(
        default=None,
        description="Framing and composition settings"
    )

    enhancement: EnhancementSpec | None = Field(
        default=None,
        description="Image enhancement/retouching settings"
    )

    scene: SceneSpec | None = Field(
        default=None,
        description="Lifestyle scene settings (for generate)"
    )

    placement: ProductPlacementSpec | None = Field(
        default=None,
        description="Product placement in scene (for generate)"
    )

    extraction: ExtractionSpec | None = Field(
        default=None,
        description="Product extraction settings (for multi-product images)"
    )

    focus: FocusSpec | None = Field(
        default=None,
        description="Focus and depth of field settings"
    )

    material_treatment: MaterialTreatmentSpec | None = Field(
        default=None,
        description="Material-specific rendering instructions"
    )

    fidelity: FidelitySpec | None = Field(
        default=None,
        description=(
            "CRITICAL: Product fidelity preservation requirements. "
            "Use when working with source product images to ensure output "
            "preserves essential features (colors, artwork, text, texture, shape). "
            "Fidelity > Enhancement. Always include when extracting or processing products."
        )
    )

    custom_spec: CustomSpec | None = Field(
        default=None,
        description="Fully open-ended creative spec for OOTB ideas"
    )

    # ==========================================================================
    # Free-form Creative Direction
    # ==========================================================================

    creative_direction: str | None = Field(
        default=None,
        description=(
            "Additional creative notes beyond structured parameters. "
            "Use for: overall vision, specific artistic direction, "
            "references to styles/photographers, anything not covered above."
        )
    )

    # ==========================================================================
    # Output Configuration
    # ==========================================================================

    output: OutputSpec = Field(default_factory=OutputSpec)


# =============================================================================
# Output Schemas
# =============================================================================


class ImageMetadata(BaseModel):
    """Metadata for generated/edited images."""

    width: int
    height: int
    format: str
    size_bytes: int
    aspect_ratio: str


class OutputVariant(BaseModel):
    """Single output variant (master, thumbnail, social).

    Use storage_path for all references. URL is derived where needed.
    """

    variant: str
    path: str = Field(description="Local path (ephemeral)")
    preview_path: str = Field(description="Local preview path (ephemeral)")
    metadata: ImageMetadata
    description: str | None = Field(default=None)
    storage_path: str | None = Field(
        default=None,
        description="Storage path (e.g., 'pending/output.png'). Use in view_image, write_data."
    )


class ImageStudioOutput(BaseModel):
    """Unified output schema for Image Studio tool."""

    success: bool

    # Generated/processed images
    outputs: list[OutputVariant] = Field(default_factory=list)

    # For asset creation (suggested data for WriteIntent)
    suggested_asset_data: str | None = Field(
        default=None,
        description="JSON string with pre-populated asset record for WriteIntent"
    )

    # Warnings, errors, and guidance
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    error_code: str | None = None
    next_steps: list[str] = Field(
        default_factory=list,
        description="Suggested next operations based on results"
    )


# =============================================================================
# Error Codes
# =============================================================================


class ImageStudioErrorCode:
    """Standard error codes for Image Studio operations."""

    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    CORRUPT_FILE = "CORRUPT_FILE"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    API_ERROR = "API_ERROR"
    CONTENT_POLICY = "CONTENT_POLICY"
    INVALID_INPUT = "INVALID_INPUT"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
