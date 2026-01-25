"""Maternity Photo - MOM Typography Concept.

Recreates the reference: Subject between two M letters spelling MOM,
black dress, white background, dramatic hair/scarf flowing, joyful upward gaze.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents" / "src"))

from dotenv import load_dotenv
load_dotenv()

from autifyme_agents.tools.image_studio.tool import _image_studio_impl


def generate_mom_concept():
    """Generate MOM typography maternity concept."""
    print("\n" + "="*60)
    print("GENERATING: MOM Typography Concept")
    print("="*60)

    # Use all source images for maximum identity preservation
    images = [
        {"path": r"C:\Abhi\personal\images\Wife (2).jpeg", "label": "face_ref"},  # Close-up face
        {"path": r"C:\Abhi\personal\images\Wife (4).jpeg", "label": "body_ref"},  # Full body
        {"path": r"C:\Abhi\personal\images\Wife (1).jpeg", "label": "pose_ref"},  # Additional reference
    ]

    custom_spec = {
        "instruction": """Create a creative MOM typography maternity portrait:

        CRITICAL IDENTITY PRESERVATION:
        - Face: MUST match [face_ref] EXACTLY - same facial structure, nose, eyes, lips, skin tone
        - Body: MUST match [body_ref] proportions accurately
        - This is a real person - the result must be recognizable as her

        CREATIVE CONCEPT:
        1. TYPOGRAPHY: Large serif "M" letters on either side of the subject
           - Left side: Large black "M"
           - Right side: Large black "M"
           - Subject stands between them, her pregnant silhouette forms the "O"
           - Together spells "MOM"

        2. POSE (copy exactly from reference):
           - Profile view facing left
           - Back gracefully arched, bump prominent
           - Head tilted up, looking upward with joy
           - Both hands on lower back/hips
           - One foot slightly forward, relaxed stance
           - Expression: Joyful, radiant smile, eyes looking up

        3. ATTIRE:
           - Black fitted maxi dress
           - Form-fitting to show bump clearly
           - Sleeveless or thin straps
           - Floor-length
           - Simple, elegant

        4. DRAMATIC ELEMENT:
           - Long black scarf or fabric flowing dramatically behind
           - Catches wind, creates dynamic movement
           - Extends from shoulder area flowing to the right
           - Creates visual drama against white background

        5. HAIR:
           - Long dark hair flowing back with the wind/movement
           - Natural, dynamic, adds to the movement feel

        6. BACKGROUND:
           - Pure white, clean, minimalist
           - High contrast black and white aesthetic
           - No shadows or gradients - pure white

        7. STYLE:
           - Black and white photograph
           - High contrast
           - Clean, graphic, typography-inspired
           - Editorial/artistic

        The overall feel should be joyful, celebratory, dynamic - a creative take on maternity photography.""",
        "style_reference": "Creative typography maternity photography, high contrast B&W editorial",
        "artistic_intent": "Joyful celebration of motherhood with creative MOM typography concept"
    }

    # Fidelity - CRITICAL for accurate face/body
    fidelity = {
        "preserve_colors": "Exact skin tone from [face_ref] - will be in B&W but luminosity must match",
        "preserve_shape": "Facial structure MUST match [face_ref] exactly - nose, eyes, lips, face shape",
        "preserve_texture": "Skin texture, hair texture from source",
        "hero_features": "Her exact face, her smile, her body proportions from [body_ref]",
        "fidelity_notes": "This is a real person - she must be immediately recognizable. Face is the most critical element."
    }

    lighting = {
        "type": "flat studio lighting for clean B&W",
        "direction": "even, frontal fill",
        "quality": "soft, even, no harsh shadows",
        "color_temperature": "neutral - B&W output",
        "shadows": "minimal to none - clean white background",
        "special_requirements": "high contrast for graphic B&W effect"
    }

    background = {
        "treatment": "solid_color",
        "color": "pure white #FFFFFF",
        "custom": "completely clean white, no gradients, no shadows"
    }

    composition = {
        "product_coverage": "80% frame height",
        "position": "centered, with space for M letters on sides",
        "camera_angle": "eye level, profile view",
        "negative_space": "white space on sides for typography",
        "custom": "full body visible, room for M letters flanking subject"
    }

    enhancement = {
        "sharpness": "high, crisp",
        "contrast": "high for graphic B&W",
        "color_treatment": "BLACK AND WHITE - high contrast monochrome",
        "detail_enhancement": "face sharp and detailed"
    }

    output = {
        "format": "PNG",
        "size": "2K",
        "aspect_ratio": "1:1",  # Square for the MOM composition
        "filename": "maternity_mom_concept_v1"
    }

    print("Generating with maximum identity preservation...")

    result = _image_studio_impl(
        images=images,
        lighting=lighting,
        background=background,
        composition=composition,
        fidelity=fidelity,
        enhancement=enhancement,
        custom_spec=custom_spec,
        output=output,
        temperature=0.6,  # Lower for more accurate reproduction
    )

    # Print and copy result
    _handle_result(result)
    return result


def _handle_result(result):
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

                            # Copy to user folder
                            if local_path:
                                src = Path(local_path)
                                if src.exists():
                                    dst = dest_dir / src.name
                                    shutil.copy(src, dst)
                                    print(f"Copied to: {dst}")
                    except Exception as e:
                        print(f"Parse error: {e}")
    else:
        if result.get("success"):
            print("\nSUCCESS!")
            local_path = result.get('local_path')
            print(f"Generated: {local_path}")
        else:
            print(f"\nFAILED: {result.get('error')}")


if __name__ == "__main__":
    generate_mom_concept()
    print("\n" + "="*60)
    print("GENERATION COMPLETE!")
    print("="*60)
