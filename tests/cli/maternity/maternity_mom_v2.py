"""Maternity Photo - MOM Concept V2.

Fixed: Accurate skin tone (fairer), accessories (Apple Watch, ring), manicured nails.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents" / "src"))

from dotenv import load_dotenv
load_dotenv()

from autifyme_agents.tools.image_studio.tool import _image_studio_impl


def generate_mom_concept_v2():
    """Generate MOM concept with accurate details."""
    print("\n" + "="*60)
    print("GENERATING: MOM Concept V2 - Accurate Details")
    print("="*60)

    # Use ALL 4 source images for maximum identity preservation
    images = [
        {"path": r"C:\Abhi\personal\images\Wife (1).jpeg", "label": "full_body_1"},
        {"path": r"C:\Abhi\personal\images\Wife (2).jpeg", "label": "face_closeup"},
        {"path": r"C:\Abhi\personal\images\Wife (3).jpeg", "label": "outdoor_natural"},
        {"path": r"C:\Abhi\personal\images\Wife (4).jpeg", "label": "full_body_2"},
    ]

    custom_spec = {
        "instruction": """Create a MOM typography maternity portrait with ACCURATE personal details:

        ===== CRITICAL: SKIN TONE =====
        She has FAIR/LIGHT Indian skin complexion - NOT dark.
        Look at [face_ref] carefully - her skin is fair, light-toned with warm undertones.
        DO NOT make her darker than she appears in the source images.
        Match the EXACT skin luminosity from [face_ref].

        ===== CRITICAL: JEWELRY & ACCESSORIES (Minimal, Classy, Elegant) =====
        She MUST be wearing MINIMAL but ELEGANT jewelry:
        1. APPLE WATCH - Purple/lavender Apple Watch on LEFT wrist (her signature piece from [face_ref])
        2. DELICATE RING - Elegant wedding/engagement ring, subtle sparkle
        3. EARRINGS - Small elegant studs or delicate drops - MINIMAL, not heavy
        4. OPTIONAL: Delicate thin necklace or pendant (subtle, elegant)
        5. LIPSTICK - Pink/rose colored lipstick (visible in [face_ref])

        JEWELRY STYLE: Think Cartier minimal, Tiffany elegance - understated luxury
        NOT heavy Indian jewelry - keep it refined, modern, classy

        ===== CRITICAL: NAILS =====
        - Manicured nails, well-groomed
        - Hands must show polished/manicured fingernails

        ===== CREATIVE CONCEPT =====
        1. TYPOGRAPHY: Large serif "M" letters flanking her
           - Left: Large black "M"
           - Right: Large black "M"
           - She stands between them, forming "MOM"

        2. POSE:
           - Profile view facing left
           - Back gracefully arched, bump prominent
           - Head tilted up, looking upward with JOY
           - Hands on lower back (showing ring and watch)
           - Radiant, genuine smile
           - Expression of pure happiness

        3. ATTIRE:
           - Black fitted sleeveless maxi dress
           - Form-fitting showing bump clearly
           - Floor-length, elegant

        4. FLOWING ELEMENT:
           - Long black scarf/dupatta flowing dramatically behind
           - Creates dynamic movement
           - Wind-blown effect

        5. HAIR:
           - Her natural long dark hair
           - Flowing back with movement

        6. BACKGROUND:
           - Pure white, high contrast B&W

        ===== FACE IDENTITY =====
        Her exact facial features from [face_ref]:
        - Her specific nose shape
        - Her eye shape and brows
        - Her lip shape with pink lipstick
        - Her face structure and jawline
        - Her fair skin complexion
        - Her natural beauty marks if any""",
        "style_reference": "Creative typography maternity, high contrast B&W editorial",
        "artistic_intent": "Joyful celebration with accurate personal identity"
    }

    # STRONG fidelity emphasis on skin tone and accessories
    fidelity = {
        "preserve_colors": """CRITICAL - FAIR SKIN TONE:
        She has LIGHT/FAIR Indian complexion as seen in [face_ref].
        Do NOT darken her skin. Match exact luminosity from source.
        In B&W this means LIGHTER skin tones, not dark.""",
        "preserve_shape": "Exact facial structure from [face_ref] - nose, eyes, lips, face shape, jawline",
        "preserve_texture": "Her skin texture, hair texture - smooth fair skin",
        "hero_features": """MUST INCLUDE:
        1. Her FAIR skin tone (light Indian complexion)
        2. Purple/lavender APPLE WATCH on left wrist
        3. RING on finger
        4. Pink LIPSTICK
        5. MANICURED nails
        6. Her exact face from [face_ref]""",
        "fidelity_notes": """She is FAIRER skinned than typical - do not default to darker skin.
        Her accessories (Apple Watch, ring) are part of her identity.
        Nails should appear well-manicured."""
    }

    lighting = {
        "type": "bright, even studio lighting",
        "direction": "frontal fill, soft and even",
        "quality": "soft, flattering, brings out fair skin luminosity",
        "color_temperature": "neutral white",
        "shadows": "minimal - clean white background",
        "special_requirements": "lighting should emphasize her FAIR complexion, not darken"
    }

    background = {
        "treatment": "solid_color",
        "color": "pure white #FFFFFF",
        "custom": "completely clean white, high contrast"
    }

    composition = {
        "product_coverage": "85% frame height",
        "position": "centered between M letters",
        "camera_angle": "eye level, profile view showing face and hands",
        "negative_space": "white space for M typography",
        "custom": "hands visible to show watch and ring, full body"
    }

    enhancement = {
        "sharpness": "high - face and accessories crisp",
        "contrast": "high for graphic B&W",
        "color_treatment": "BLACK AND WHITE - but preserve FAIR skin luminosity (lighter tones)",
        "detail_enhancement": "accessories (watch, ring, nails) clearly visible and detailed"
    }

    output = {
        "format": "PNG",
        "size": "2K",
        "aspect_ratio": "1:1",
        "filename": "maternity_mom_concept_v2"
    }

    print("Generating with accurate skin tone and accessories...")

    result = _image_studio_impl(
        images=images,
        lighting=lighting,
        background=background,
        composition=composition,
        fidelity=fidelity,
        enhancement=enhancement,
        custom_spec=custom_spec,
        output=output,
        temperature=0.5,  # Lower for accuracy
    )

    _handle_result(result, "maternity_mom_concept_v2.png")
    return result


def _handle_result(result, filename):
    """Handle and copy result."""
    import shutil
    import os
    import json

    temp_dir = Path(os.environ.get("TEMP", "/tmp")) / "media_downloads"
    dest_dir = Path(r"C:\Abhi\personal\images")

    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict) and item.get("type") == "text":
                print("\nSUCCESS!")
                text = item.get("text", "")
                if "local_path" in text:
                    try:
                        json_start = text.find("{")
                        if json_start != -1:
                            data = json.loads(text[json_start:])
                            local_path = data.get('local_path')
                            print(f"Generated: {local_path}")
                            if local_path:
                                src = Path(local_path)
                                if src.exists():
                                    dst = dest_dir / filename
                                    shutil.copy(src, dst)
                                    print(f"Copied to: {dst}")
                    except Exception as e:
                        print(f"Parse error: {e}")
    else:
        if result.get("success"):
            print("\nSUCCESS!")
            print(f"Generated: {result.get('local_path')}")
        else:
            print(f"\nFAILED: {result.get('error')}")


if __name__ == "__main__":
    generate_mom_concept_v2()
    print("\nDONE!")
