"""
Google Live API - Native Audio Streaming

This module provides infrastructure for real-time voice conversations using Gemini's Live API.
The Live API enables low-latency, bidirectional audio streaming with native voice capabilities.

Architecture:
- WebSocket-based streaming (not HTTP request/response)
- Bidirectional: Send audio streams, receive audio responses
- Native audio processing (no text-to-speech conversion)
- Supports 30+ voices across 24+ languages

Key Capabilities:
- Affective dialog: Responds to tone of voice and emotion
- Proactive audio: Knows when to speak and when to listen
- Multilingual: Mix languages within same conversation
- Audio-video understanding: Can analyze video streams

Models:
- gemini-2.5-flash-native-audio-preview-09-2025: Latest native audio model

Note: Live API requires specialized integration. This module provides foundation structure.
For full implementation, use Google's official Live API client library.
"""

import os
from typing import AsyncIterator, Callable, Literal

try:
    import google.genai as genai
    from google.genai.live import AsyncSession
except ImportError:
    raise ImportError(
        "google-generativeai package with Live API support required. "
        "Install with: uv pip install google-generativeai[live]"
    )


class GeminiLiveSession:
    """
    Client for real-time voice conversations using Gemini Live API.

    This is a foundation implementation. For production use, refer to:
    https://ai.google.dev/gemini-api/docs/live

    Usage:
        session = GeminiLiveSession(
            model="gemini-2.5-flash-native-audio-preview-09-2025",
            voice="Kore"
        )

        async def audio_handler(audio_chunk: bytes):
            # Process received audio
            play_audio(audio_chunk)

        await session.start(audio_callback=audio_handler)
        await session.send_audio(microphone_audio_bytes)
        await session.send_text("What do you see in this image?")
        await session.close()
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash-native-audio-preview-09-2025",
        voice: str = "Kore",
        api_key: str | None = None,
        system_instruction: str | None = None,
    ):
        """
        Initialize Gemini Live API session.

        Args:
            model: Live API model to use
            voice: Voice name (30+ options: Kore, Enceladus, Puck, etc.)
            api_key: Google API key. If None, reads from GOOGLE_API_KEY environment variable.
            system_instruction: Optional system instructions for assistant behavior
        """
        self.model = model
        self.voice = voice
        self.system_instruction = system_instruction
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable or api_key parameter required"
            )

        # Configure client
        genai.configure(api_key=self.api_key)
        self.client = genai.Client()
        self._session: AsyncSession | None = None

    async def start(
        self,
        audio_callback: Callable[[bytes], None] | None = None,
        text_callback: Callable[[str], None] | None = None,
    ) -> None:
        """
        Start Live API session with WebSocket connection.

        Args:
            audio_callback: Function to call with received audio chunks
            text_callback: Function to call with received text responses
        """
        config = {
            "model": self.model,
            "generation_config": {
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {"prebuilt_voice_config": {"voice_name": self.voice}}
                },
            },
        }

        if self.system_instruction:
            config["system_instruction"] = self.system_instruction

        # Create session
        self._session = await self.client.live.connect(**config)

        # Register callbacks
        if audio_callback:
            self._session.on_audio(audio_callback)
        if text_callback:
            self._session.on_text(text_callback)

    async def send_audio(self, audio_bytes: bytes) -> None:
        """
        Send audio stream to Live API.

        Args:
            audio_bytes: Audio data (PCM 16-bit, 16kHz recommended)
        """
        if not self._session:
            raise RuntimeError("Session not started. Call start() first.")
        await self._session.send_audio(audio_bytes)

    async def send_text(self, text: str) -> None:
        """
        Send text message to Live API.

        Args:
            text: Text message to send
        """
        if not self._session:
            raise RuntimeError("Session not started. Call start() first.")
        await self._session.send_text(text)

    async def send_video(self, video_frame: bytes, mime_type: str = "image/jpeg") -> None:
        """
        Send video frame to Live API for visual understanding.

        Args:
            video_frame: Video frame bytes (JPEG or PNG)
            mime_type: MIME type of frame ('image/jpeg' or 'image/png')
        """
        if not self._session:
            raise RuntimeError("Session not started. Call start() first.")
        await self._session.send_video(video_frame, mime_type=mime_type)

    async def close(self) -> None:
        """Close Live API session and WebSocket connection."""
        if self._session:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()


def get_live_session(
    model: str = "gemini-2.5-flash-native-audio-preview-09-2025",
    voice: str = "Kore",
    api_key: str | None = None,
    system_instruction: str | None = None,
) -> GeminiLiveSession:
    """
    Factory function to create Gemini Live API session.

    Args:
        model: Live API model identifier
        voice: Voice name (Kore, Puck, Enceladus, etc.)
        api_key: Google API key. If None, reads from GOOGLE_API_KEY env var.
        system_instruction: System instructions for assistant behavior

    Returns:
        Configured GeminiLiveSession instance

    Example:
        async def handle_audio(audio: bytes):
            play_audio_to_speaker(audio)

        session = get_live_session(voice="Kore")
        await session.start(audio_callback=handle_audio)

        # Send microphone audio
        mic_audio = record_audio_from_microphone()
        await session.send_audio(mic_audio)

        # Or send text
        await session.send_text("Tell me a joke")

        await session.close()

    Note:
        This is a foundation implementation. For production use cases,
        refer to official Google Live API documentation and examples.
    """
    return GeminiLiveSession(
        model=model,
        voice=voice,
        api_key=api_key,
        system_instruction=system_instruction,
    )
