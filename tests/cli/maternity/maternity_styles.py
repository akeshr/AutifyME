"""Maternity Photo Generation - Multiple Styles.

Generates maternity photos in different trending styles:
1. Fine Art Silhouette - dramatic backlighting
2. Studio Elegant - clean, high-fashion
3. Black & White Fine Art - timeless emotional
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents" / "src"))

from dotenv import load_dotenv
load_dotenv()

from autifyme_agents.tools.image_studio.tool import _image_studio_impl


def generate_silhouette():
    """Fine Art Silhouette - dramatic backlighting."""
    print("\n" + "="*60)
    print("GENERATING: Fine Art Silhouette")
    print("="*60)

    images = [
        {"path": r"C:\Abhi\personal\images\Wife (2).jpeg", "label": "face_ref"},
        {"path": r"C:\Abhi\personal\images\Wife (4).jpeg", "label": "source"},
    ]

    custom_spec = {
        "instruction": """Create a dramatic fine art silhouette maternity portrait:

        1. SUBJECT: The woman from [source] and [face_ref] - preserve facial identity in profile
        2. MATERNITY: Show beautiful 7-8 month pregnancy bump as the focal point
        3. TECHNIQUE: Dramatic backlighting creating silhouette effect
           - Strong backlight from behind (window or studio light)
           - Subject in profile or 3/4 view
           - Pregnancy bump prominently highlighted by rim light
           - Face partially visible with rim lighting on features
        4. ATTIRE: Flowing sheer fabric or fitted silhouette-revealing dress
           - Can be body-con showing bump clearly
           - Or sheer fabric with light passing through
        5. SETTING: Simple - studio with bright backlight or window
        6. MOOD: Artistic, powerful, celebrating the pregnant form

        Think: Annie Leibovitz, fine art pregnancy portraits, Vogue editorial.""",
        "style_reference": "Fine art silhouette photography, dramatic rim lighting",
        "artistic_intent": "Celebrate the pregnant silhouette as art"
    }

    lighting = {
        "type": "dramatic backlit silhouette",
        "direction": "strong backlight from directly behind",
        "quality": "hard edge light creating rim/halo effect",
        "color_temperature": "warm golden or cool white depending on mood",
        "shadows": "subject mostly in shadow, edges lit",
        "special_requirements": "rim light defining pregnancy bump curve"
    }

    composition = {
        "product_coverage": "80% frame",
        "position": "centered or rule of thirds",
        "camera_angle": "profile view or 3/4 to show bump silhouette",
        "negative_space": "clean background for silhouette to stand out"
    }

    fidelity = {
        "preserve_colors": "skin tone visible in lit areas",
        "preserve_shape": "facial profile must match [face_ref]",
        "hero_features": "pregnancy bump curve, profile silhouette",
        "fidelity_notes": "Face recognizable even in partial silhouette"
    }

    output = {
        "format": "PNG",
        "size": "2K",
        "aspect_ratio": "3:4",
        "filename": "maternity_silhouette_v1"
    }

    result = _image_studio_impl(
        images=images,
        lighting=lighting,
        composition=composition,
        fidelity=fidelity,
        custom_spec=custom_spec,
        output=output,
        temperature=0.8,
    )

    _print_result(result, "Silhouette")
    return result


def generate_studio_elegant():
    """Studio Elegant - high-fashion magazine style."""
    print("\n" + "="*60)
    print("GENERATING: Studio Elegant")
    print("="*60)

    images = [
        {"path": r"C:\Abhi\personal\images\Wife (2).jpeg", "label": "face_ref"},
        {"path": r"C:\Abhi\personal\images\Wife (4).jpeg", "label": "source"},
    ]

    custom_spec = {
        "instruction": """Create a high-fashion studio maternity portrait:

        1. SUBJECT: The woman from [source] and [face_ref] - preserve exact facial identity
        2. MATERNITY: Elegant 7-8 month pregnancy bump
        3. SETTING: Clean professional studio
           - Seamless gradient background (warm gray to cream or subtle color)
           - Professional studio lighting setup
           - Magazine cover quality
        4. ATTIRE: High-fashion maternity look
           - Elegant fitted maternity dress OR
           - Luxurious draped fabric (silk, satin) OR
           - Chic minimalist - simple elegant piece
           - Colors: deep jewel tone (emerald, sapphire, burgundy) OR classic black OR cream
        5. STYLING:
           - Hair styled elegantly (can be flowing or pulled back)
           - Minimal jewelry
           - Confident, empowered pose
        6. MOOD: Powerful, elegant, magazine editorial

        Think: Vanity Fair portrait, Harper's Bazaar cover, Vogue maternity editorial.""",
        "style_reference": "Vanity Fair portraits, Annie Leibovitz studio work",
        "artistic_intent": "Powerful, confident celebration of pregnancy"
    }

    lighting = {
        "type": "professional studio 3-point with beauty dish",
        "direction": "key light 45 degrees camera-left, fill from front",
        "quality": "soft but controlled, sculpting the form",
        "color_temperature": "neutral to slightly warm",
        "shadows": "soft shadows for dimension, controlled",
        "special_requirements": "flattering skin lighting, catch lights in eyes"
    }

    background = {
        "treatment": "gradient",
        "color": "warm gray to cream OR subtle deep color",
        "custom": "professional studio seamless backdrop"
    }

    composition = {
        "product_coverage": "70-80% frame",
        "position": "centered, powerful stance",
        "camera_angle": "eye level to slightly low for power",
        "negative_space": "balanced for magazine cover potential"
    }

    fidelity = {
        "preserve_colors": "exact skin tone from [face_ref]",
        "preserve_shape": "facial features must match [face_ref] exactly",
        "hero_features": "face, confident expression, elegant form",
        "fidelity_notes": "Must be recognizable - this is a portrait"
    }

    enhancement = {
        "sharpness": "high on face, crisp throughout",
        "contrast": "medium for punch",
        "color_treatment": "rich, saturated, editorial quality",
        "detail_enhancement": "flawless skin, professional retouching look"
    }

    output = {
        "format": "PNG",
        "size": "2K",
        "aspect_ratio": "3:4",
        "filename": "maternity_studio_elegant_v1"
    }

    result = _image_studio_impl(
        images=images,
        lighting=lighting,
        background=background,
        composition=composition,
        fidelity=fidelity,
        enhancement=enhancement,
        custom_spec=custom_spec,
        output=output,
        temperature=0.8,
    )

    _print_result(result, "Studio Elegant")
    return result


def generate_bw_fine_art():
    """Black & White Fine Art - timeless emotional."""
    print("\n" + "="*60)
    print("GENERATING: Black & White Fine Art")
    print("="*60)

    images = [
        {"path": r"C:\Abhi\personal\images\Wife (2).jpeg", "label": "face_ref"},
        {"path": r"C:\Abhi\personal\images\Wife (4).jpeg", "label": "source"},
    ]

    custom_spec = {
        "instruction": """Create a timeless black and white fine art maternity portrait:

        1. SUBJECT: The woman from [source] and [face_ref] - preserve facial identity
        2. MATERNITY: Beautiful 7-8 month pregnancy bump
        3. STYLE: Classic black and white fine art
           - Dramatic monochrome
           - Rich tonal range from deep blacks to pure whites
           - Emphasis on form, light, and emotion
        4. ATTIRE: Simple, minimalist
           - Can be draped fabric, simple dress, or tasteful implied
           - Focus on the form and emotion, not the clothes
           - White or light fabric works beautifully for B&W
        5. LIGHTING: Dramatic, sculptural
           - Single strong light source creating dimension
           - Rembrandt or split lighting
           - Strong shadows defining form
        6. POSE: Intimate, emotional
           - Can be more artistic/abstract
           - Emphasis on the connection to pregnancy
           - Serene, introspective expression
        7. MOOD: Timeless, emotional, fine art gallery worthy

        Think: Classic maternity art photography, museum-quality print.""",
        "style_reference": "Ansel Adams tonal quality, classic fine art portraiture",
        "artistic_intent": "Timeless emotional art celebrating motherhood"
    }

    lighting = {
        "type": "dramatic single source Rembrandt",
        "direction": "45 degrees from one side",
        "quality": "medium soft with defined shadows",
        "color_temperature": "n/a - black and white",
        "shadows": "deep, sculpting, defining form",
        "special_requirements": "full tonal range for B&W conversion"
    }

    composition = {
        "product_coverage": "75% frame",
        "position": "centered or slightly offset",
        "camera_angle": "eye level or slightly low",
        "negative_space": "dark or light void for artistic effect"
    }

    fidelity = {
        "preserve_colors": "n/a - B&W but preserve skin luminosity",
        "preserve_shape": "facial features must match [face_ref]",
        "hero_features": "facial expression, pregnancy form, emotional connection",
        "fidelity_notes": "Face must be recognizable in monochrome"
    }

    enhancement = {
        "sharpness": "medium-high, fine art print quality",
        "contrast": "high for dramatic B&W",
        "color_treatment": "BLACK AND WHITE - rich monochrome, full tonal range",
        "detail_enhancement": "skin texture visible but flattering"
    }

    output = {
        "format": "PNG",
        "size": "2K",
        "aspect_ratio": "3:4",
        "filename": "maternity_bw_fineart_v1"
    }

    result = _image_studio_impl(
        images=images,
        lighting=lighting,
        composition=composition,
        fidelity=fidelity,
        enhancement=enhancement,
        custom_spec=custom_spec,
        output=output,
        temperature=0.8,
    )

    _print_result(result, "B&W Fine Art")
    return result


def _print_result(result, style_name):
    """Print result summary."""
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict) and item.get("type") == "text":
                print(f"\n{style_name} - SUCCESS")
                text = item.get("text", "")
                # Extract path from JSON
                if "local_path" in text:
                    import json
                    try:
                        # Find the JSON part
                        json_start = text.find("{")
                        if json_start != -1:
                            data = json.loads(text[json_start:])
                            print(f"Path: {data.get('local_path')}")
                    except:
                        pass
    else:
        if result.get("success"):
            print(f"\n{style_name} - SUCCESS")
            print(f"Path: {result.get('local_path')}")
        else:
            print(f"\n{style_name} - FAILED: {result.get('error')}")


def copy_results():
    """Copy generated images to user folder."""
    import shutil
    import os

    temp_dir = Path(os.environ.get("TEMP", "/tmp")) / "media_downloads"
    dest_dir = Path(r"C:\Abhi\personal\images")

    files_to_copy = [
        "maternity_silhouette_v1.png",
        "maternity_studio_elegant_v1.png",
        "maternity_bw_fineart_v1.png"
    ]

    print("\n" + "="*60)
    print("COPYING FILES TO USER FOLDER")
    print("="*60)

    for filename in files_to_copy:
        src = temp_dir / filename
        if src.exists():
            dst = dest_dir / filename
            shutil.copy(src, dst)
            print(f"Copied: {filename}")
        else:
            print(f"Not found: {filename}")


if __name__ == "__main__":
    # Generate all three styles
    generate_silhouette()
    generate_studio_elegant()
    generate_bw_fine_art()

    # Copy results
    copy_results()

    print("\n" + "="*60)
    print("ALL GENERATIONS COMPLETE!")
    print("="*60)
    print("Check C:\\Abhi\\personal\\images\\ for results")
