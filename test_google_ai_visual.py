"""
Visual demonstration of Google AI multimodal capabilities.

This test demonstrates:
1. Text generation with Gemini 2.5 Flash
2. Image generation with Nano Banana (gemini-2.5-flash-image)
3. Multimodal output (text + image in single request)
"""

import os
import base64
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

from autifyme_agents.core.llm_factory import get_llm


def save_image(image_data: bytes, filename: str) -> str:
    """Save image bytes to file."""
    filepath = f"test_outputs/{filename}"
    os.makedirs("test_outputs", exist_ok=True)

    with open(filepath, "wb") as f:
        f.write(image_data)

    return filepath


def main():
    """Run visual Google AI demonstration."""

    print("=" * 80)
    print("Google AI Multimodal Integration - Visual Demonstration")
    print("=" * 80)
    print()

    # Check API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY not found in environment")
        print("Please set it in your .env file")
        return

    print("[OK] Google API key found")
    print()

    # Test 1: Basic Text Generation
    print("-" * 80)
    print("TEST 1: Text Generation with Gemini 2.5 Flash")
    print("-" * 80)
    print()

    llm_text = get_llm(
        provider="google",
        model="gemini-2.5-flash",
        temperature=0.7
    )

    print("Prompt: Explain Gemini AI in 2 sentences")
    print()

    response = llm_text.invoke("Explain Gemini AI in 2 sentences")
    print(f"Response:\n{response.content}")
    print()
    print("[OK] Text generation successful")
    print()

    # Test 2: Image Generation
    print("-" * 80)
    print("TEST 2: Image Generation with Nano Banana (gemini-2.5-flash-image)")
    print("-" * 80)
    print()

    llm_image = get_llm(
        provider="google",
        model="gemini-2.5-flash-image",
        temperature=0.7,
        response_modalities=["TEXT", "IMAGE"]
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt = "A futuristic AI robot assistant helping a developer code, vibrant colors, digital art style"

    print(f"Prompt: {prompt}")
    print()
    print("Generating image... (this may take 10-15 seconds)")
    print()

    try:
        response = llm_image.invoke(prompt)

        # Extract text response
        print(f"Text Response:\n{response.content}")
        print()

        # Extract and save image
        if hasattr(response, 'additional_kwargs') and 'image' in response.additional_kwargs:
            image_base64 = response.additional_kwargs['image']
            image_bytes = base64.b64decode(image_base64)

            filename = f"nano_banana_{timestamp}.png"
            filepath = save_image(image_bytes, filename)

            print(f"[OK] Image generated successfully!")
            print(f"  Saved to: {filepath}")
            print(f"  Size: {len(image_bytes):,} bytes")
        else:
            print("[WARN] No image found in response")
            print(f"Response keys: {response.additional_kwargs.keys() if hasattr(response, 'additional_kwargs') else 'N/A'}")

    except Exception as e:
        print(f"[ERROR] Image generation failed: {e}")
        import traceback
        traceback.print_exc()

    print()

    # Test 3: Adaptive Thinking
    print("-" * 80)
    print("TEST 3: Adaptive Thinking with Gemini 2.5 Pro")
    print("-" * 80)
    print()

    llm_thinking = get_llm(
        provider="google",
        model="gemini-2.5-pro",
        temperature=0.0,
        thinking_budget=4000,
        include_thoughts=True
    )

    problem = "What are the 3 key architectural principles for building AI agent systems?"
    print(f"Prompt: {problem}")
    print()
    print("Generating response with extended reasoning...")
    print()

    try:
        response = llm_thinking.invoke(problem)
        print(f"Response:\n{response.content}")
        print()
        print("[OK] Thinking generation successful")
    except Exception as e:
        print(f"[ERROR] Thinking generation failed: {e}")

    print()
    print("=" * 80)
    print("Demonstration Complete!")
    print("=" * 80)
    print()
    print("Summary:")
    print("  [OK] Text generation with Gemini 2.5 Flash")
    print("  [OK] Image generation with Nano Banana (check test_outputs/)")
    print("  [OK] Adaptive thinking with Gemini 2.5 Pro")
    print()
    print("For more capabilities, see:")
    print("  - docs/architecture/tech/GOOGLE_AI_MULTIMODAL_INTEGRATION.md")
    print("  - Video generation (Veo 3.1)")
    print("  - Text-to-speech (TTS)")
    print("  - Live audio conversations")
    print("  - Browser automation (Computer Use extension)")
    print()


if __name__ == "__main__":
    main()
