"""Message Intent Interpretation Schemas.

Structured outputs for MessageIntentSpecialist to interpret raw platform messages
in context of ongoing conversations and pending approvals.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class MediaReference(BaseModel):
    """Reference to downloaded media file."""

    media_type: Literal["image", "video", "audio", "document"]
    local_path: str = Field(description="Local filesystem path to downloaded media")
    original_id: str = Field(description="Platform-specific media ID")
    mime_type: str | None = None
    size_bytes: int | None = None


class MessageInterpretation(BaseModel):
    """Structured interpretation of raw user message in conversational context.

    The MessageIntentSpecialist analyzes the raw message plus conversation history
    to determine user intent and extract relevant information.
    """

    intent: Literal[
        "new_cataloging_request",      # User wants to catalog new product
        "approval_response",            # User responding to pending approval
        "approval_modification",        # User wants to edit pending draft
        "clarification_request",        # User asking about pending approval
        "workflow_abandonment",         # User starting new workflow during pending approval
        "insufficient_information",     # User provided partial info, needs more
        "off_topic",                    # Unrelated to current workflow
        "greeting",                     # Simple greeting/acknowledgment
    ] = Field(description="Detected user intent based on context")

    reasoning: str = Field(
        description="Explanation of why this intent was chosen (for observability)"
    )

    # For new_cataloging_request
    product_text: str | None = Field(
        default=None,
        description="User's product description text if provided"
    )
    media: list[MediaReference] = Field(
        default_factory=list,
        description="Downloaded media files if present"
    )

    # For approval_response
    approval_decision: Literal["approve", "reject"] | None = Field(
        default=None,
        description="User's approval decision if intent is approval_response"
    )

    # For approval_modification
    requested_edits: dict[str, str] | None = Field(
        default=None,
        description="Fields user wants to modify in pending draft"
    )

    # For insufficient_information
    missing_information: list[str] = Field(
        default_factory=list,
        description="What additional information is needed from user"
    )

    # For clarification_request
    clarification_subject: str | None = Field(
        default=None,
        description="What aspect of pending approval user is asking about"
    )

    # For workflow_abandonment
    abandoned_previous: bool = Field(
        default=False,
        description="Whether this message abandons a pending workflow"
    )

    # Platform metadata
    platform: str = Field(description="Source platform (whatsapp, telegram, etc)")
    raw_text: str | None = Field(default=None, description="Original user text")
    has_media: bool = Field(default=False, description="Whether message includes media")


class RawPlatformMessage(BaseModel):
    """Raw message from messaging platform before interpretation.

    This is what Runner forwards to PM, who then passes to MessageIntentSpecialist.
    """

    platform: Literal["whatsapp", "telegram", "sms", "email", "web"] = Field(
        description="Source messaging platform"
    )
    sender: str = Field(description="Platform-specific sender ID")
    text: str | None = Field(default=None, description="Message text content")
    media_id: str | None = Field(
        default=None,
        description="Platform-specific media attachment ID"
    )
    timestamp: str = Field(description="ISO timestamp of message receipt")
    reply_to_message_id: str | None = Field(
        default=None,
        description="If reply, the message ID being replied to"
    )
