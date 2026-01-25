"""Maternity Photo Generation Test.

Uses image_studio tool to generate ethereal garden maternity photography.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents" / "src"))

from dotenv import load_dotenv
load_dotenv()

from autifyme_agents.tools.image_studio.tool import _image_studio_impl


def generate_maternity_photo():
    """Generate ethereal garden maternity photo."""

    # Source images - using best ones for face + body
    images = [
        {"path": r"C:\Abhi\personal\images\Wife (2).jpeg", "label": "face_ref"},  # Close-up for face identity
        {"path": r"C:\Abhi\personal\images\Wife (4).jpeg", "label": "source"},    # Full body reference
    ]

    # Scene: Ethereal garden at golden hour
    scene = {
        "environment": "dreamy wildflower meadow with soft morning mist, lavender and white flowers",
        "style": "ethereal, romantic, fine art maternity photography",
        "mood": "serene, glowing, maternal radiance",
        "time_of_day": "golden hour, warm backlit sunlight filtering through soft morning mist",
        "props_and_context": "flowing chiffon fabric catching the breeze, scattered flower petals"
    }

    # Lighting: Soft golden hour with rim lighting
    lighting = {
        "type": "natural golden hour with soft rim lighting",
        "direction": "backlit from behind with gentle fill from front",
        "quality": "soft, diffused, dreamy with lens flare allowed",
        "color_temperature": "warm golden 4500K",
        "shadows": "soft natural shadows, no harsh contrasts",
        "special_requirements": "ethereal glow around subject, soft skin lighting"
    }

    # Composition: Full body maternity pose
    composition = {
        "product_coverage": "70% frame with breathing room",
        "position": "centered, slightly offset to golden ratio",
        "camera_angle": "eye level to slightly low angle for elegance",
        "negative_space": "generous top and sides for dreamy atmosphere",
        "custom": "elegant maternity pose with hands cradling baby bump"
    }

    # Fidelity: Preserve facial identity exactly
    fidelity = {
        "preserve_colors": "exact skin tone and complexion from [face_ref]",
        "preserve_shape": "facial features must match [face_ref] exactly",
        "hero_features": "facial identity, warm Indian skin tone, long dark hair",
        "fidelity_notes": "This is a real person - face must be recognizable and identical to source"
    }

    # Enhancement: Dreamy but sharp where it matters
    enhancement = {
        "sharpness": "face sharp, body soft focus, background dreamy blur",
        "contrast": "soft low contrast for ethereal feel",
        "color_treatment": "warm golden tones, slight desaturation for fine art look",
        "detail_enhancement": "enhance skin glow, soft radiance"
    }

    # Custom creative direction for maternity transformation
    custom_spec = {
        "instruction": """Transform [source] into world-class maternity photography:

        1. SUBJECT: The woman in [source] and [face_ref] - preserve her exact facial identity
        2. MATERNITY: Show her with a beautiful, natural-looking 7-8 month pregnancy bump
        3. ATTIRE: Replace current clothes with a flowing ethereal maternity gown:
           - Soft champagne/cream colored chiffon or tulle
           - Off-shoulder or one-shoulder elegant draping
           - Fabric flowing and catching the light
           - Gown highlighting the baby bump beautifully
        4. POSE: Elegant maternity pose - hands gently cradling the bump, serene expression
        5. HAIR: Her natural long dark hair flowing softly in the breeze
        6. SETTING: Place her in the dreamy wildflower meadow scene

        This should look like a $3000 professional maternity photoshoot.""",
        "style_reference": "Annie Leibovitz maternity portraits, Vanity Fair editorial style",
        "artistic_intent": "Celebrate the beauty of motherhood with ethereal, magazine-worthy imagery"
    }

    # Focus: Face sharp, dreamy elsewhere
    focus = {
        "focus_point": "face and eyes",
        "depth_of_field": "medium shallow - face sharp, body slightly soft, background creamy bokeh",
        "falloff": "natural gradual falloff from face to background"
    }

    # Output: High quality portrait orientation
    output = {
        "format": "PNG",
        "size": "2K",
        "aspect_ratio": "3:4",  # Portrait orientation for maternity
        "filename": "maternity_ethereal_garden_v1"
    }

    print("Generating ethereal garden maternity photo...")
    print("This may take 30-60 seconds...")

    result = _image_studio_impl(
        images=images,
        scene=scene,
        lighting=lighting,
        composition=composition,
        fidelity=fidelity,
        enhancement=enhancement,
        custom_spec=custom_spec,
        focus=focus,
        output=output,
        temperature=0.8,  # Slightly higher for creative freedom
    )

    # Handle multimodal response
    if isinstance(result, list):
        # Multimodal response - extract text part
        for item in result:
            if isinstance(item, dict) and item.get("type") == "text":
                print("\n" + "="*50)
                print("GENERATION RESULT:")
                print("="*50)
                print(item.get("text", ""))
        print("\nImage generated and returned for visual verification.")
    else:
        # Standard dict response
        print("\n" + "="*50)
        print("GENERATION RESULT:")
        print("="*50)
        if result.get("success"):
            print(f"SUCCESS!")
            if "local_path" in result:
                print(f"Local path: {result['local_path']}")
            if "storage_path" in result:
                print(f"Storage path: {result['storage_path']}")
        else:
            print(f"FAILED: {result.get('error')}")
            print(f"Error code: {result.get('error_code')}")
            if result.get("next_steps"):
                print("Next steps:", result.get("next_steps"))

    return result


if __name__ == "__main__":
    generate_maternity_photo()
