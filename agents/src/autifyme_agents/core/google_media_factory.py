"""
Google Media Factory - Veo 3.1 Video Generation

This module provides infrastructure for generating videos using Google's Veo 3.1 models.
Veo 3.1 is a separate API from the standard Gemini models and requires the google.genai client.

Architecture:
- Uses async long-running operations (poll until done)
- Supports text-to-video, image-to-video, and video extension
- Output: 720p or 1080p video at 24fps with native audio
- Duration: 4-8 seconds, extendable up to 148 seconds

Models:
- veo-3.1-generate-preview: Standard quality, higher fidelity
- veo-3.1-fast-generate-preview: Faster generation, optimized for speed

Pricing:
- Fast: $0.15/second
- Standard: $0.40/second
"""

import asyncio
import os
from typing import Literal

try:
    import google.genai as genai
except ImportError:
    raise ImportError(
        "google-generativeai package required for Veo 3.1. "
        "Install with: uv pip install google-generativeai"
    ) from None


class VeoVideoGenerator:
    """
    Client for generating videos using Veo 3.1 models.

    Usage:
        generator = VeoVideoGenerator(model="veo-3.1-fast-generate-preview")
        video_bytes = await generator.generate_video(
            prompt="A cat playing piano in a jazz club",
            duration=8,
            resolution="1080p"
        )
    """

    def __init__(
        self,
        model: Literal[
            "veo-3.1-generate-preview", "veo-3.1-fast-generate-preview"
        ] = "veo-3.1-fast-generate-preview",
        api_key: str | None = None,
    ):
        """
        Initialize Veo video generator.

        Args:
            model: Veo model variant to use ('veo-3.1-generate-preview' or 'veo-3.1-fast-generate-preview')
            api_key: Google API key. If None, reads from GOOGLE_API_KEY environment variable.
        """
        self.model = model
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable or api_key parameter required"
            )

        # Configure client
        genai.configure(api_key=self.api_key)
        self.client = genai.Client()

    async def generate_video(
        self,
        prompt: str,
        duration: Literal[4, 6, 8] = 8,
        resolution: Literal["720p", "1080p"] = "1080p",
        aspect_ratio: str = "16:9",
        reference_images: list[str] | None = None,
        poll_interval: float = 5.0,
        timeout: float = 300.0,
    ) -> bytes:
        """
        Generate video from text prompt using Veo 3.1.

        Args:
            prompt: Text description of video to generate
            duration: Video duration in seconds (4, 6, or 8)
            resolution: Output resolution ('720p' or '1080p')
            aspect_ratio: Video aspect ratio (e.g., '16:9', '9:16', '1:1')
            reference_images: Optional list of up to 3 reference image paths/URLs
            poll_interval: Seconds between operation status checks
            timeout: Maximum seconds to wait for video generation

        Returns:
            Video bytes (MP4 format with native audio)

        Raises:
            TimeoutError: If generation exceeds timeout
            ValueError: If generation fails
        """
        # Build generation request
        request_params = {
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
        }

        if reference_images:
            if len(reference_images) > 3:
                raise ValueError("Maximum 3 reference images allowed")
            request_params["reference_images"] = reference_images

        # Start video generation (async operation)
        operation = await self.client.models.generate_video(
            model=self.model, **request_params
        )

        # Poll until done
        elapsed = 0.0
        while not operation.done:
            if elapsed >= timeout:
                raise TimeoutError(
                    f"Video generation exceeded timeout of {timeout}s"
                )
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            operation = await self.client.operations.get(operation.name)

        # Check for errors
        if operation.error:
            raise ValueError(
                f"Video generation failed: {operation.error.message}"
            )

        # Extract video bytes from result
        video_data = operation.result.video
        return video_data

    async def extend_video(
        self,
        video_bytes: bytes,
        extension_prompt: str | None = None,
        additional_duration: Literal[4, 6, 8] = 8,
        poll_interval: float = 5.0,
        timeout: float = 300.0,
    ) -> bytes:
        """
        Extend an existing video (up to 148 seconds total).

        Args:
            video_bytes: Original video bytes to extend
            extension_prompt: Optional prompt for extension behavior
            additional_duration: Seconds to add (4, 6, or 8)
            poll_interval: Seconds between operation status checks
            timeout: Maximum seconds to wait for video generation

        Returns:
            Extended video bytes

        Raises:
            TimeoutError: If generation exceeds timeout
            ValueError: If extension fails
        """
        request_params = {
            "video": video_bytes,
            "duration": additional_duration,
        }

        if extension_prompt:
            request_params["prompt"] = extension_prompt

        # Start video extension (async operation)
        operation = await self.client.models.extend_video(
            model=self.model, **request_params
        )

        # Poll until done
        elapsed = 0.0
        while not operation.done:
            if elapsed >= timeout:
                raise TimeoutError(
                    f"Video extension exceeded timeout of {timeout}s"
                )
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            operation = await self.client.operations.get(operation.name)

        # Check for errors
        if operation.error:
            raise ValueError(
                f"Video extension failed: {operation.error.message}"
            )

        # Extract extended video bytes
        video_data = operation.result.video
        return video_data


def get_video_generator(
    model: Literal[
        "veo-3.1-generate-preview", "veo-3.1-fast-generate-preview"
    ] = "veo-3.1-fast-generate-preview",
    api_key: str | None = None,
) -> VeoVideoGenerator:
    """
    Factory function to create Veo video generator.

    Args:
        model: Veo model variant ('veo-3.1-generate-preview' for quality,
               'veo-3.1-fast-generate-preview' for speed)
        api_key: Google API key. If None, reads from GOOGLE_API_KEY env var.

    Returns:
        Configured VeoVideoGenerator instance

    Example:
        generator = get_video_generator(model="veo-3.1-fast-generate-preview")
        video = await generator.generate_video(
            prompt="A sunset over mountains",
            duration=8,
            resolution="1080p"
        )
        with open("output.mp4", "wb") as f:
            f.write(video)
    """
    return VeoVideoGenerator(model=model, api_key=api_key)
