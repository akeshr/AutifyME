"""Maternity Photo - Seashell Venus Concept.

Venus rising from the sea - giant seashell backdrop, beach sunset, white flowing gown.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents" / "src"))

from dotenv import load_dotenv
load_dotenv()

from autifyme_agents.tools.image_studio.tool import _image_studio_impl


def generate_shell_concept():
    """Generate seashell Venus maternity concept."""
    print("\n" + "="*60)
    print("GENERATING: Seashell Venus Concept")
    print("="*60)

    # ALL 4 source images
    images = [
        {"path": r"C:\Abhi\personal\images\Wife (1).jpeg", "label": "full_body_1"},
        {"path": r"C:\Abhi\personal\images\Wife (2).jpeg", "label": "face_closeup"},
        {"path": r"C:\Abhi\personal\images\Wife (3).jpeg", "label": "outdoor_ref"},
        {"path": r"C:\Abhi\personal\images\Wife (4).jpeg", "label": "full_body_2"},
    ]

    custom_spec = {
        "instruction": """Create a stunning "Venus Rising" seashell maternity portrait.

===== CRITICAL: MUST LOOK LIKE HER =====
Study ALL source images carefully:
- [face_closeup]: Her EXACT facial features - nose, eyes, lips, jawline
- [full_body_1], [full_body_2]: Her body proportions
- [outdoor_ref]: Her natural appearance

The result MUST be recognizable as THIS SPECIFIC WOMAN.
FAIR/LIGHT Indian skin complexion - do NOT darken.

===== CONCEPT: VENUS RISING FROM THE SEA =====

BACKDROP - GIANT SEASHELL:
- Large open seashell (scallop/clam shape) standing upright behind her
- Shell is OPEN like butterfly wings framing her
- Shell color: soft pink/peach with golden edges, translucent glow
- Shell catches the sunset light, glowing from within
- She stands IN FRONT of the shell, centered

SETTING - BEACH AT SUNSET:
- Ocean beach with gentle waves at her feet
- Sunset sky: pink, peach, coral, soft orange gradients
- Golden hour lighting from behind
- Waves softly touching the shore around her feet
- Dreamy, ethereal atmosphere

ATTIRE - WHITE FLOWING GOWN:
- Elegant white/ivory strapless maternity gown
- Empire waist highlighting the bump
- Long flowing chiffon skirt pooling at her feet
- Fabric catching the breeze slightly
- Ethereal, goddess-like

POSE:
- PROFILE VIEW facing left
- Hands gently cradling her pregnant bump
- Serene, peaceful expression
- Looking slightly down at her belly OR gazing at horizon
- Elegant posture

HAIR:
- Elegant updo (soft bun or twisted style)
- Some loose tendrils framing face
- Classic, timeless

JEWELRY (Minimal, Elegant):
- Pearl earrings (drops or studs)
- Optional: delicate pearl bracelet
- Wedding ring visible

LIGHTING:
- Backlit by sunset through the shell
- Warm golden/pink rim light on her silhouette
- Soft glow on her face from reflected light
- Ethereal, dreamy quality

MOOD:
- Goddess-like, ethereal
- Celebrating the miracle of new life
- Venus/Botticelli inspired
- Magical, dreamlike""",
        "style_reference": "Botticelli Birth of Venus, fantasy maternity, ethereal goddess photography",
        "artistic_intent": "Venus rising - new life emerging, divine feminine beauty"
    }

    fidelity = {
        "preserve_colors": "FAIR/LIGHT Indian skin - match [face_closeup] exactly, do NOT darken",
        "preserve_shape": "Her EXACT facial features from [face_closeup]",
        "hero_features": "Her face, fair skin, pearl earrings, elegant updo, wedding ring",
        "fidelity_notes": "Must be recognizable as the same person in source photos"
    }

    scene = {
        "environment": "ocean beach at sunset with giant open seashell behind subject",
        "style": "ethereal, fantasy, goddess-like, Botticelli inspired",
        "mood": "magical, serene, divine feminine",
        "time_of_day": "golden hour sunset - pink, peach, coral sky"
    }

    lighting = {
        "type": "natural sunset backlight",
        "direction": "behind subject, through the shell",
        "quality": "soft, golden, ethereal glow",
        "color_temperature": "warm golden/pink sunset tones",
        "shadows": "soft, minimal, rim-lit silhouette effect"
    }

    composition = {
        "product_coverage": "85% frame height",
        "position": "centered, shell framing her from behind",
        "camera_angle": "eye level, profile view",
        "negative_space": "shell wings spread on either side"
    }

    output = {
        "format": "PNG",
        "size": "2K",
        "aspect_ratio": "3:4",
        "filename": "maternity_shell_venus"
    }

    print("Generating seashell Venus concept...")

    result = _image_studio_impl(
        images=images,
        scene=scene,
        lighting=lighting,
        composition=composition,
        fidelity=fidelity,
        custom_spec=custom_spec,
        output=output,
        temperature=0.5,
    )

    _handle_result(result, "maternity_shell_venus.png")
    return result


def _handle_result(result, filename):
    import shutil, json
    from pathlib import Path

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
                            shutil.copy(src, dest_dir / filename)
                            print(f"Saved: {dest_dir / filename}")
                    except Exception as e:
                        print(f"Error: {e}")
    else:
        if result.get("success"):
            print(f"SUCCESS: {result.get('local_path')}")
        else:
            print(f"FAILED: {result.get('error')}")


if __name__ == "__main__":
    generate_shell_concept()
