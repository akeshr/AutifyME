"""Message schemas for cross-platform communication.

Canonical message format for PM and workflow orchestration. These schemas
normalize platform-specific payloads (WhatsApp, Telegram, Email, etc.) into
a unified format that PM can understand without platform-specific logic.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MediaReference(BaseModel):
    """Platform-agnostic media reference.

    Represents a media attachment (image, video, audio, document) with
    platform-specific download strategy encoded. This allows PM to route
    based on media metadata without handling platform-specific download logic.
    """

    # Identity
    media_id: str = Field(..., description="Platform-specific media identifier")
    media_type: Literal["image", "video", "audio", "document", "voice"] = Field(
        ..., description="Type of media"
    )
    mime_type: str = Field(..., description="MIME type (e.g., 'image/jpeg', 'video/mp4')")

    # Access Strategy
    platform: Literal["whatsapp", "telegram", "email", "web", "sms", "slack", "api"] = Field(
        ..., description="Source platform"
    )
    download_strategy: Literal["eager", "lazy", "none"] = Field(
        ...,
        description=(
            "Download strategy: "
            "'eager' = download immediately (URLs expire), "
            "'lazy' = download on-demand (URLs persist), "
            "'none' = already on filesystem"
        ),
    )
    local_path: Path | None = Field(
        None, description="Local file path (set if already downloaded or uploaded directly)"
    )
    platform_url: str | None = Field(None, description="Platform-specific URL (may expire)")

    # Metadata
    size_bytes: int | None = Field(None, description="File size in bytes")
    caption: str | None = Field(None, description="User-provided caption for media")
    filename: str | None = Field(None, description="Original filename")
    expires_at: datetime | None = Field(
        None, description="URL expiration timestamp (for eager platforms like WhatsApp)"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class IncomingMessage(BaseModel):
    """Canonical message format for PM consumption.

    Normalizes all platform-specific message formats into a unified schema.
    PM receives this semantic representation and classifies intent without
    needing platform-specific knowledge.
    """

    # Core Content
    text: str | None = Field(None, description="User's text message (if any)")
    media: list[MediaReference] = Field(
        default_factory=list, description="Media attachments (if any)"
    )

    # Context
    platform: str = Field(..., description="Source platform (e.g., 'whatsapp', 'email')")
    sender_id: str = Field(..., description="Platform-specific user identifier")
    thread_id: str = Field(..., description="Conversation thread ID (for checkpointer)")
    timestamp: datetime = Field(..., description="Message timestamp")

    # Advanced Context (optional)
    reply_to_message_id: str | None = Field(
        None, description="Message ID if replying to previous message"
    )
    forwarded_from: str | None = Field(None, description="Original sender if forwarded")
    conversation_history: list[dict[str, Any]] | None = Field(
        None, description="Recent messages for context (optional)"
    )

    # Platform-Specific Extras
    platform_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Platform-specific fields (e.g., WhatsApp message type)"
    )

    def has_media(self) -> bool:
        """Check if message contains media attachments."""
        return len(self.media) > 0

    def has_text(self) -> bool:
        """Check if message contains text content."""
        return self.text is not None and len(self.text.strip()) > 0

    def is_empty(self) -> bool:
        """Check if message is empty (no text, no media)."""
        return not self.has_text() and not self.has_media()

    def media_summary(self) -> str:
        """Human-readable summary of attached media.

        Returns:
            Summary like "2 image(s), 1 video(s)" or "No media"
        """
        if not self.media:
            return "No media"

        counts: dict[str, int] = {}
        for m in self.media:
            counts[m.media_type] = counts.get(m.media_type, 0) + 1

        parts = [f"{count} {mtype}(s)" for mtype, count in counts.items()]
        return ", ".join(parts)

    def to_semantic_description(self) -> str:
        """Convert to semantic description for PM processing.

        Returns:
            Human-readable description of message for LLM processing
        """
        parts = []

        if self.has_text():
            parts.append(f"User message: {self.text}")

        if self.has_media():
            parts.append(f"Media: {self.media_summary()}")
            # Add media details for each attachment
            for i, media in enumerate(self.media, 1):
                details = f"  - Media {i}: {media.media_type}"
                if media.local_path:
                    details += f" (path: {media.local_path})"
                if media.caption:
                    details += f' - caption: "{media.caption}"'
                parts.append(details)

        if not parts:
            parts.append("(Empty message)")

        return "\n".join(parts)

    # Pydantic V2 handles datetime serialization automatically
    model_config = ConfigDict()
