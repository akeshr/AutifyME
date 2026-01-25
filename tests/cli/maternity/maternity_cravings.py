"""Maternity Photo - Fun Cravings Concept V2.

Let model COPY face from images - don't describe features.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents" / "src"))

from dotenv import load_dotenv
load_dotenv()

from autifyme_agents.tools.image_studio.tool import _image_studio_impl


def generate_cravings_concept():
    print("\n" + "="*60)
    print("GENERATING: Fun Cravings Concept V2")
    print("="*60)

    # ALL 4 source images
    images = [
        {"path": r"C:\Abhi\personal\images\Wife (1).jpeg", "label": "ref1"},
        {"path": r"C:\Abhi\personal\images\Wife (2).jpeg", "label": "ref2"},
        {"path": r"C:\Abhi\personal\images\Wife (3).jpeg", "label": "ref3"},
        {"path": r"C:\Abhi\personal\images\Wife (4).jpeg", "label": "ref4"},
    ]

    custom_spec = {
        "instruction": """Create a fun pregnancy cravings maternity photo.

===== CRITICAL: COPY HER FACE EXACTLY FROM IMAGES =====
Look at [ref1], [ref2], [ref3], [ref4] - this is the SAME woman.
COPY her EXACT face into the generated image.
- Her exact face shape
- Her exact nose
- Her exact eyes
- Her exact lips
- Her exact skin tone (she is FAIR - light complexion, do NOT darken)

The output face MUST match the face in [ref2] (closeup).
Do NOT generate a different person. COPY her face.

===== ADD BABY BUMP =====
Keep her exact body, just add pregnant belly naturally.

===== SCENE =====
- Sitting cross-legged on white fluffy rug
- Yellow off-shoulder crop top showing bump
- Yellow headband
- Teal/turquoise loose pants
- Cute face painted on belly (winking, tongue out)
- Holding chocolate ice cream bar
- Lay's chips, popcorn bowl, yellow flowers around her
- Warm studio bokeh background

EXPRESSION: Natural gentle smile - NOT laughing, NOT exaggerated.
Just a soft, natural, pleasant smile like in [ref2].
Keep expression calm and natural.""",
        "style_reference": "Fun pregnancy cravings photoshoot",
        "artistic_intent": "Playful celebration - but face MUST match source images exactly"
    }

    fidelity = {
        "preserve_colors": "Her EXACT skin tone from [ref2] - she is FAIR/LIGHT, do NOT darken",
        "preserve_shape": "COPY her exact face from [ref2] - same person",
        "hero_features": "Her face from images - must be recognizable as same person",
        "fidelity_notes": "Face must match [ref2]. Fair skin. Do not create different person."
    }

    output = {
        "format": "PNG",
        "size": "2K",
        "aspect_ratio": "1:1",
        "filename": "maternity_cravings_v3"
    }

    result = _image_studio_impl(
        images=images,
        fidelity=fidelity,
        custom_spec=custom_spec,
        output=output,
        temperature=0.2,  # Lowest for maximum accuracy
    )

    # Handle result
    import shutil, json
    dest_dir = Path(r"C:\Abhi\personal\images")

    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict) and item.get("type") == "text":
                print("\nSUCCESS!")
                text = item.get("text", "")
                if "local_path" in text:
                    try:
                        data = json.loads(text[text.find("{"):])
                        src = Path(data['local_path'])
                        if src.exists():
                            shutil.copy(src, dest_dir / "maternity_cravings_v3.png")
                            print(f"Saved: {dest_dir / 'maternity_cravings_v3.png'}")
                    except Exception as e:
                        print(f"Error: {e}")
    else:
        print(f"Result: {result}")


if __name__ == "__main__":
    generate_cravings_concept()
