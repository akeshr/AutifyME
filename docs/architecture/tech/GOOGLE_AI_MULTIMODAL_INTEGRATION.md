# Google AI Multimodal Integration

**Status:** ✅ Implemented
**Date:** 2025-10-30
**Owner:** Infrastructure

---

## Executive Summary

Complete infrastructure for Google AI's multimodal capabilities across text, image generation, text-to-speech, video generation, real-time voice, and browser automation. Supports all Gemini 2.5/2.0 models plus specialized media models (Nano Banana, Veo 3.1, Live API, Computer Use).

---

## Architecture

### Four-Layer Integration

**Layer 1: LLM Factory** (Standard Chat Models)
- **Module:** `autifyme_agents.core.llm_factory.get_llm(provider="google")`
- **Use Cases:** Text generation, image generation (Nano Banana), text-to-speech
- **Client:** `ChatGoogleGenerativeAI` (LangChain)

**Layer 2: Media Factory** (Video Generation)
- **Module:** `autifyme_agents.core.google_media_factory.get_video_generator()`
- **Use Cases:** Text-to-video, image-to-video, video extension (Veo 3.1)
- **Client:** `google.genai` async operations

**Layer 3: Live API** (Real-Time Voice)
- **Module:** `autifyme_agents.core.google_live_api.get_live_session()`
- **Use Cases:** Real-time voice conversations, audio-video understanding
- **Client:** `google.genai` WebSocket streaming

**Layer 4: Computer Use** (Browser Automation) - **Optional Extension**
- **Module:** `extensions/google_computer_use` (separate install)
- **Use Cases:** Web scraping, form automation, UI testing, agentic workflows
- **Client:** `google.genai` with ActionExecutor (Playwright)
- **Note:** Heavy dependencies (~600MB total) - install only when needed

---

## Supported Models

### Text Generation Models (LLM Factory)

| Model | Context | Output | Features | Cost |
|-------|---------|--------|----------|------|
| **gemini-2.5-pro** | 1M | 65K | Adaptive thinking, SOTA reasoning | Premium |
| **gemini-2.5-flash** | 1M | 65K | Best price-performance, thinking | Standard |
| **gemini-2.5-flash-lite** | 1M | 65K | Fastest, cost-optimized | Budget |
| **gemini-2.0-flash** | 1M | - | Native tool use | Standard |
| **gemini-2.0-flash-lite** | 1M | - | Cost-efficient 2.0 | Budget |

### Image Generation (Nano Banana)

| Model | Purpose | Cost |
|-------|---------|------|
| **gemini-2.5-flash-image** | Stable image gen/edit | $0.039/image |
| **gemini-2.5-flash-image-preview** | Preview with latest features | $0.039/image |

**Capabilities:** Generate, edit, blend images; character consistency; multimodal prompts

### Text-to-Speech (TTS)

| Model | Languages | Voices |
|-------|-----------|--------|
| **gemini-2.5-pro-preview-tts** | 24 | 30+ |
| **gemini-2.5-flash-preview-tts** | 24 | 30+ |

**Output:** PCM 24kHz audio, single or multi-speaker

### Video Generation (Veo 3.1)

| Model | Speed | Quality | Cost |
|-------|-------|---------|------|
| **veo-3.1-fast-generate-preview** | Faster | Standard | $0.15/sec |
| **veo-3.1-generate-preview** | Slower | Premium | $0.40/sec |

**Output:** 720p/1080p @ 24fps, 4-8 sec (extend to 148 sec), native audio

### Native Audio (Live API)

| Model | Purpose |
|-------|---------|
| **gemini-2.5-flash-native-audio-preview-09-2025** | Real-time voice conversations |

**Features:** Affective dialog, proactive audio, multilingual, audio-video understanding

### Computer Use (Browser Automation)

| Model | Context | Output | Actions | Benchmark |
|-------|---------|--------|---------|-----------|
| **gemini-2.5-computer-use-preview-10-2025** | 128K | 64K | 12 UI actions | 70% accuracy (Online-Mind2Web) |

**Capabilities:** Screenshot-based visual understanding, structured UI actions (click, type, scroll, navigate), built-in safety checks, optimized for web browsers and Android UIs

**Actions:** click_at, type_text_at, scroll_document, scroll_at, navigate, hover_at, go_back, go_forward, search, key_combination, drag_and_drop, wait_5_seconds

---

## Usage Examples

### 1. Text Generation (Standard)

```python
from autifyme_agents.core.llm_factory import get_llm

# Basic text generation
llm = get_llm(
    provider="google",
    model="gemini-2.5-flash",
    temperature=0.7
)

response = llm.invoke("Explain quantum computing in simple terms")
print(response.content)

# With adaptive thinking
llm_thinking = get_llm(
    provider="google",
    model="gemini-2.5-pro",
    temperature=0.0,
    thinking_budget=8000,  # More reasoning tokens
    include_thoughts=True  # Show chain-of-thought
)

response = llm_thinking.invoke("Solve this complex math problem: ...")
print(response.content)
```

### 2. Image Generation (Nano Banana)

```python
from autifyme_agents.core.llm_factory import get_llm
import base64

# Create image generation model
llm_image = get_llm(
    provider="google",
    model="gemini-2.5-flash-image-preview",
    temperature=0.7,
    response_modalities=["TEXT", "IMAGE"]  # Request both text and image
)

# Generate image
response = llm_image.invoke(
    "A futuristic cityscape at sunset with flying cars"
)

# Extract image from response
if "image" in response.additional_kwargs:
    image_base64 = response.additional_kwargs["image"]
    image_bytes = base64.b64decode(image_base64)

    with open("generated_image.png", "wb") as f:
        f.write(image_bytes)

    print(f"Text: {response.content}")
    print(f"Image saved to: generated_image.png")
```

### 3. Text-to-Speech (TTS)

```python
from autifyme_agents.core.llm_factory import get_llm
import base64

# Create TTS model
llm_tts = get_llm(
    provider="google",
    model="gemini-2.5-flash-preview-tts",
    temperature=0.7,
    response_modalities=["AUDIO"]  # Audio output only
)

# Generate speech
response = llm_tts.invoke(
    "Welcome to AutifyME! I'm your AI assistant, ready to help."
)

# Extract audio from response
if "audio" in response.additional_kwargs:
    audio_base64 = response.additional_kwargs["audio"]
    audio_bytes = base64.b64decode(audio_base64)

    with open("welcome.wav", "wb") as f:
        f.write(audio_bytes)

    print("Audio saved to: welcome.wav")
```

### 4. Video Generation (Veo 3.1)

```python
from autifyme_agents.core.google_media_factory import get_video_generator
import asyncio

async def generate_video_example():
    # Create video generator
    generator = get_video_generator(
        model="veo-3.1-fast-generate-preview"  # Faster, lower cost
    )

    # Generate video from text prompt
    video_bytes = await generator.generate_video(
        prompt="A cat playing piano in a jazz club, cinematic lighting, 4K quality",
        duration=8,  # 4, 6, or 8 seconds
        resolution="1080p",  # "720p" or "1080p"
        aspect_ratio="16:9"
    )

    # Save video
    with open("cat_piano.mp4", "wb") as f:
        f.write(video_bytes)

    print("Video saved to: cat_piano.mp4")

    # Extend video
    extended_video = await generator.extend_video(
        video_bytes=video_bytes,
        extension_prompt="The cat finishes the song and bows",
        additional_duration=8
    )

    with open("cat_piano_extended.mp4", "wb") as f:
        f.write(extended_video)

    print("Extended video saved to: cat_piano_extended.mp4")

# Run async function
asyncio.run(generate_video_example())
```

### 5. Real-Time Voice (Live API)

```python
from autifyme_agents.core.google_live_api import get_live_session
import asyncio

async def voice_conversation_example():
    # Audio callback handler
    async def handle_audio(audio_chunk: bytes):
        # In production: play to speaker
        print(f"Received audio chunk: {len(audio_chunk)} bytes")
        # play_to_speaker(audio_chunk)

    # Create Live API session
    session = get_live_session(
        model="gemini-2.5-flash-native-audio-preview-09-2025",
        voice="Kore",  # Choose from 30+ voices
        system_instruction="You are a helpful AI assistant. Be concise and friendly."
    )

    # Start session with callback
    await session.start(audio_callback=handle_audio)

    # Send text message
    await session.send_text("Tell me a short joke")

    # Or send microphone audio
    # mic_audio = record_from_microphone()
    # await session.send_audio(mic_audio)

    # Wait for response
    await asyncio.sleep(5)

    # Close session
    await session.close()

# Run async function
asyncio.run(voice_conversation_example())
```

### 6. Browser Automation (Computer Use) - Optional Extension

**Installation Required:**
```bash
# Install Computer Use extension (heavy dependencies: Playwright ~200MB + Chromium ~400MB)
cd extensions/google_computer_use
uv pip install -e ".[playwright]"
playwright install chromium
```

```python
from google_computer_use import get_computer_use_agent
from google_computer_use.playwright_executor import PlaywrightExecutor
import asyncio

async def browser_automation_example():
    # Initialize Playwright executor
    executor = PlaywrightExecutor(
        viewport_width=1440,
        viewport_height=900,
        headless=False  # Show browser for debugging
    )
    await executor.initialize()

    # Create Computer Use agent
    agent = get_computer_use_agent(
        action_executor=executor,
        system_instruction="You are a careful browser automation agent. "
                          "Verify information before submitting forms.",
        auto_confirm=False  # Require approval for high-risk actions
    )

    # Execute browser automation task
    result = await agent.execute_task(
        goal="Go to Google, search for 'Gemini API documentation', "
             "and click the first result",
        max_steps=15,
        initial_url="https://google.com"
    )

    # Check result
    if result["success"]:
        print(f"Task completed in {result['steps_taken']} steps")
        print(f"Final URL: {result['final_state'].url}")
        print(f"Page title: {result['final_state'].title}")

        # View action history
        for action in result["actions"]:
            print(f"Action: {action.action_type} - {action.reasoning}")
    else:
        print(f"Task failed: {result['error']}")

    # Cleanup
    await executor.cleanup()

# Run async function
asyncio.run(browser_automation_example())
```

---

## Configuration Parameters

### LLM Factory (Google Provider)

```python
get_llm(
    provider="google",
    model="gemini-2.5-flash",           # Model selection
    temperature=0.7,                     # 0.0-2.0 (vs 0.0-1.0 for others)
    timeout=30.0,                        # Request timeout

    # Sampling parameters
    top_p=0.95,                          # Nucleus sampling (0.0-1.0)
    top_k=40,                            # Top-k sampling (must be positive)
    max_output_tokens=4096,              # Max response length (up to 65K)

    # Thinking parameters (2.5 models)
    thinking_budget=8000,                # Reasoning token budget
    include_thoughts=True,               # Include chain-of-thought

    # Multimodal parameters
    response_modalities=["TEXT", "IMAGE"],  # Output types
    response_mime_type="application/json",  # Structured output

    # Safety controls
    safety_settings={
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        # ... other categories
    }
)
```

### Video Generator

```python
get_video_generator(
    model="veo-3.1-fast-generate-preview",  # or "veo-3.1-generate-preview"
    api_key="your_api_key"                  # Optional, uses GOOGLE_API_KEY env var
)

# Generation parameters
await generator.generate_video(
    prompt="Video description",
    duration=8,                             # 4, 6, or 8 seconds
    resolution="1080p",                     # "720p" or "1080p"
    aspect_ratio="16:9",                    # Any aspect ratio
    reference_images=[...],                 # Up to 3 reference images
    poll_interval=5.0,                      # Check status every N seconds
    timeout=300.0                           # Max wait time
)
```

### Live Session

```python
get_live_session(
    model="gemini-2.5-flash-native-audio-preview-09-2025",
    voice="Kore",                           # 30+ voices available
    api_key="your_api_key",
    system_instruction="Behavior prompt"
)
```

---

## Cost Optimization

### Model Selection Strategy

**Text Generation:**
- **Development/Testing:** `gemini-2.5-flash-lite` (lowest cost)
- **Production (standard):** `gemini-2.5-flash` (best price-performance)
- **Production (complex):** `gemini-2.5-pro` (SOTA reasoning)

**Image Generation:**
- **Always:** `gemini-2.5-flash-image` ($0.039/image = 1290 output tokens)

**Video Generation:**
- **Rapid prototyping:** `veo-3.1-fast-generate-preview` ($0.15/sec)
- **Final production:** `veo-3.1-generate-preview` ($0.40/sec, higher quality)

**Voice:**
- **Batch TTS:** Use TTS models via LLM factory (static audio)
- **Real-time conversations:** Use Live API (native audio, interactive)

### Caching Best Practices

**Context Caching (Gemini 2.5):**
- Use `cached_content` parameter for repeated context
- All 2.5 models support 1M token context
- Cache lifetime: 5-10 min inactivity, max 1 hour

**Thinking Budget:**
- Low complexity: 2000-4000 tokens
- Medium complexity: 4000-8000 tokens
- High complexity: 8000-16000 tokens

---

## Integration Checklist

### Prerequisites

**Core Dependencies (Required):**
```bash
# Install packages for text, image, TTS, video, and live audio
uv pip install langchain-google-genai
uv pip install google-generativeai  # For Veo and Live API

# Set environment variable
export GOOGLE_API_KEY=your_api_key_here
```

**Computer Use Extension (Optional):**
```bash
# Only install when browser automation is needed (~600MB dependencies)
cd extensions/google_computer_use
uv pip install -e ".[playwright]"
playwright install chromium

# See extensions/google_computer_use/README.md for details
```

### Implementation Steps

**1. Text/Image/TTS → Use LLM Factory**
```python
from autifyme_agents.core.llm_factory import get_llm
llm = get_llm(provider="google", model="gemini-2.5-flash")
```

**2. Video Generation → Use Media Factory**
```python
from autifyme_agents.core.google_media_factory import get_video_generator
generator = get_video_generator()
```

**3. Real-Time Voice → Use Live API**
```python
from autifyme_agents.core.google_live_api import get_live_session
session = get_live_session()
```

**4. Browser Automation → Use Computer Use Extension (Optional)**
```bash
# First install extension (heavy dependencies ~600MB)
cd extensions/google_computer_use
uv pip install -e ".[playwright]"
playwright install chromium
```

```python
from google_computer_use import get_computer_use_agent
from google_computer_use.playwright_executor import PlaywrightExecutor

executor = PlaywrightExecutor()
await executor.initialize()
agent = get_computer_use_agent(action_executor=executor)
```

### Testing

```bash
# Run test file (modify as needed)
uv run python temp_test_nano_banana.py
uv run python temp_test_gemini.py
```

---

## Limitations & Future Work

### Not Supported via Current Implementation

**Gemini Nano:**
- On-device model (Android/mobile only via ML Kit)
- No cloud API access available

**Advanced Live API Features:**
- Requires full WebSocket implementation for production
- Current module provides foundation structure only

### Future Enhancements

1. **Voice Selection UI:** Helper to preview 30+ available voices
2. **Video Reference Images:** Support for style transfer and frame-specific generation
3. **Context Caching:** Explicit caching parameter support in factory
4. **Batch Processing:** Bulk image/video generation with queue management
5. **Streaming Responses:** Support for streaming text/audio/video chunks

---

## Reference Links

- [Gemini API Docs](https://ai.google.dev/gemini-api/docs)
- [Veo 3.1 Video Generation](https://ai.google.dev/gemini-api/docs/video)
- [Live API Native Audio](https://ai.google.dev/gemini-api/docs/live)
- [TTS Models](https://ai.google.dev/gemini-api/docs/speech-generation)
- [LangChain Gemini Integration](https://python.langchain.com/docs/integrations/chat/google_generative_ai/)

---

## Quick Reference

### All Available Models

```python
# Text Generation
"gemini-2.5-pro"
"gemini-2.5-flash"
"gemini-2.5-flash-lite"
"gemini-2.0-flash"
"gemini-2.0-flash-lite"

# Image Generation (Nano Banana)
"gemini-2.5-flash-image"
"gemini-2.5-flash-image-preview"

# Text-to-Speech
"gemini-2.5-pro-preview-tts"
"gemini-2.5-flash-preview-tts"

# Video Generation
"veo-3.1-generate-preview"
"veo-3.1-fast-generate-preview"

# Native Audio (Live API)
"gemini-2.5-flash-native-audio-preview-09-2025"

# Computer Use (Browser Automation)
"gemini-2.5-computer-use-preview-10-2025"
```

### Response Modalities

```python
["TEXT"]           # Text only (default)
["IMAGE"]          # Image only
["AUDIO"]          # Audio only
["TEXT", "IMAGE"]  # Text + image
["TEXT", "AUDIO"]  # Text + audio
```

### Computer Use Actions

```python
# 12 UI action types
click_at, type_text_at, scroll_document, scroll_at,
navigate, hover_at, go_back, go_forward, search,
key_combination, drag_and_drop, wait_5_seconds
```
