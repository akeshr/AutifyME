"""Maternity Photo - MOM Concept V3.

FIXES from V2:
- Use ALL 4 source images for better identity
- Pearl earrings + elegant necklace (NO Apple Watch)
- M letters at BELLY HEIGHT (not near face)
- Bump centered as the "O" in MOM
- Must look like the REAL person
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents" / "src"))

from dotenv import load_dotenv
load_dotenv()

from autifyme_agents.tools.image_studio.tool import _image_studio_impl


def generate_mom_concept_v3():
    """Generate MOM concept V3 with correct composition and jewelry."""
    print("\n" + "="*60)
    print("GENERATING: MOM Concept V3 - Correct Composition")
    print("="*60)

    # ALL 4 source images for maximum identity preservation
    images = [
        {"path": r"C:\Abhi\personal\images\Wife (1).jpeg", "label": "full_body_1"},
        {"path": r"C:\Abhi\personal\images\Wife (2).jpeg", "label": "face_closeup"},
        {"path": r"C:\Abhi\personal\images\Wife (3).jpeg", "label": "outdoor_ref"},
        {"path": r"C:\Abhi\personal\images\Wife (4).jpeg", "label": "full_body_2"},
    ]

    custom_spec = {
        "instruction": """Create MOM typography maternity portrait.

===== MOST CRITICAL: MUST LOOK LIKE HER =====
This is a REAL person. Study ALL source images:
- [face_closeup]: Her EXACT face - nose, eyes, lips, jawline, skin tone
- [full_body_1], [full_body_2]: Her body shape and proportions
- [outdoor_ref]: Her appearance in natural light

The result MUST be immediately recognizable as THIS SPECIFIC WOMAN.
Copy her facial features EXACTLY from the source images.

===== CRITICAL: SKIN TONE =====
FAIR/LIGHT Indian complexion - visible in [face_closeup].
Do NOT darken. She has fair skin with warm undertones.

===== CRITICAL: COMPOSITION - M LETTERS AT BELLY LEVEL =====
THIS IS THE KEY TO THE MOM CONCEPT:

Visual layout (MUST follow exactly):
```
            [HEAD - looking up joyfully]
            [NECK/SHOULDERS]
            [CHEST]
       M    [PREGNANT BELLY]    M
            [HIPS]
            [LEGS]
            [FEET visible]
```

- Two large serif "M" letters positioned at WAIST/BELLY HEIGHT
- Her pregnant BELLY is CENTERED between the two M letters
- The belly forms the "O" - so together it spells M-O-M
- M letters should be roughly at her hip/waist level
- NOT near her face - the letters frame her BELLY, not her head
- Full body shot showing head to feet

===== JEWELRY: ELEGANT PEARLS (NO APPLE WATCH) =====
For this elegant portrait:
1. PEARL EARRINGS - Classic pearl studs or small elegant pearl drops
2. PEARL NECKLACE or DELICATE PENDANT - Elegant strand or thin chain with pendant
3. WEDDING RING - Elegant on finger
4. MANICURED NAILS - Polished, elegant

NO APPLE WATCH - doesn't fit this timeless elegant aesthetic.
Think: Classic elegance, pearls, timeless beauty like Audrey Hepburn.

===== POSE =====
- PROFILE VIEW facing LEFT
- Back gracefully ARCHED to emphasize the bump
- Head tilted UP, looking upward with genuine JOY
- RADIANT SMILE - happy, celebrating
- Hands on lower back OR one hand cradling bump from below
- Elegant stance, one foot slightly forward

===== ATTIRE =====
- Black fitted sleeveless/strapless maxi dress
- Form-fitting to show bump silhouette CLEARLY
- Floor-length, elegant, simple
- The bump should be very visible in profile

===== FLOWING ELEMENT =====
- Long black dupatta/scarf flowing behind her
- Dynamic wind-blown effect
- Creates movement and drama
- Flows from shoulder area towards the right

===== BACKGROUND & STYLE =====
- Pure WHITE background
- BLACK AND WHITE high contrast
- Clean, graphic, editorial
- Magazine-quality typography art""",
        "style_reference": "Elegant maternity with pearls, timeless classic beauty, Annie Leibovitz portraits",
        "artistic_intent": "The M letters FRAME HER BELLY (not face) - belly is the O in MOM"
    }

    # Strong identity fidelity
    fidelity = {
        "preserve_colors": "FAIR/LIGHT skin from [face_closeup] - do NOT darken",
        "preserve_shape": "Her EXACT face from [face_closeup] - nose, eyes, lips, jawline must match",
        "preserve_texture": "Her skin texture, hair texture from sources",
        "hero_features": "Her exact face, pearl earrings, pearl/delicate necklace, ring, manicured nails, pink lipstick",
        "fidelity_notes": "Must be recognizable as the SAME person in the source photos. Fair complexion."
    }

    # Composition spec - emphasize belly-centered M letters
    composition = {
        "product_coverage": "90% frame height - full body head to feet",
        "position": "centered, with M letters flanking at BELLY/WAIST height",
        "camera_angle": "eye level, PROFILE view",
        "negative_space": "M letters on sides at waist level, white above and below",
        "custom": "CRITICAL: M letters at BELLY height, NOT near face. Belly is centered between Ms."
    }

    lighting = {
        "type": "bright even studio",
        "direction": "soft frontal fill",
        "quality": "soft, flattering for fair skin",
        "shadows": "minimal - clean white background"
    }

    background = {
        "treatment": "solid_color",
        "color": "pure white"
    }

    enhancement = {
        "sharpness": "high on face and jewelry",
        "contrast": "high for B&W graphic effect",
        "color_treatment": "BLACK AND WHITE - preserve fair skin luminosity"
    }

    output = {
        "format": "PNG",
        "size": "2K",
        "aspect_ratio": "4:5",  # Portrait ratio for full body
        "filename": "maternity_mom_v3"
    }

    print("Generating with ALL 4 images, pearl jewelry, correct M placement...")

    result = _image_studio_impl(
        images=images,
        composition=composition,
        lighting=lighting,
        background=background,
        fidelity=fidelity,
        enhancement=enhancement,
        custom_spec=custom_spec,
        output=output,
        temperature=0.4,  # Lower for better identity preservation
    )

    _handle_result(result, "maternity_mom_v3.png")
    return result


def _handle_result(result, filename):
    """Handle and copy result."""
    import shutil
    import os
    import json

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
    generate_mom_concept_v3()
    print("\nDONE!")
