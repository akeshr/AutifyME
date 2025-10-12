"""Message Intent Interpretation Schemas - Generic HITL Framework.

Structured outputs for MessageIntentSpecialist to interpret raw platform messages
in context of ongoing conversations, pending interrupts, and workflows.

Key Principle: Specialist constructs Commands. No hardcoded literals.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class MediaReference(BaseModel):
    """Reference to downloaded media file."""

    media_type: str = Field(description="Media type (image, video, audio, document, etc)")
    local_path: str = Field(description="Local filesystem path to downloaded media")
    original_id: str = Field(description="Platform-specific media ID")
    mime_type: str | None = None
    size_bytes: int | None = None


class CommandSpec(BaseModel):
    """Command specification for resuming interrupted workflows.

    Specialist constructs this based on interrupt context and user intent.
    Runner blindly executes it as Command(resume={interrupt_id: resume_value}).
    """

    interrupt_id: str = Field(description="ID of the interrupt to resume")
    resume_value: dict[str, Any] = Field(
        description="Value to pass to interrupt handler (e.g., {'type': 'accept'} or {'type': 'edit', 'updated_args': {...}})"
    )


class MessageInterpretation(BaseModel):
    """Generic interpretation of raw user message in conversational context.

    Specialist has full intelligence to:
    - Detect ANY user intent (not limited to predefined literals)
    - Construct Commands for resuming ANY interrupted workflow
    - Handle clarifications, new requests, edits, cancellations

    Runner is a blind executor - just follows specialist's instructions.
    """

    intent: str = Field(
        description="Detected user intent - specialist decides freely (e.g., 'resume_workflow', 'new_cataloging_request', 'clarification', 'greeting', etc)"
    )

    reasoning: str = Field(
        description="Explanation of interpretation for observability and debugging"
    )

    # Generic HITL resumption - specialist constructs Command
    command: CommandSpec | None = Field(
        default=None,
        description="Command to resume workflow if intent is 'resume_workflow'. Specialist constructs exact resume_value based on interrupt structure and user response."
    )

    # New request data
    request_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted data for new requests (product_text, form fields, etc). Structure depends on workflow."
    )

    # Media attachments
    media: list[MediaReference] = Field(
        default_factory=list,
        description="Downloaded media files if present in message"
    )

    # Clarification response
    clarification_response: str | None = Field(
        default=None,
        description="Response to send user for clarification requests (specialist composes this)"
    )

    # Metadata
    platform: str = Field(description="Source platform (whatsapp, telegram, etc)")
    raw_text: str | None = Field(default=None, description="Original user text")
    has_media: bool = Field(default=False, description="Whether message includes media")

    # Context flags
    had_pending_interrupt: bool = Field(
        default=False,
        description="Whether there was a pending interrupt in conversation context"
    )


class RawPlatformMessage(BaseModel):
    """Raw message from messaging platform before interpretation.

    This is what Runner forwards to PM, who then passes to MessageIntentSpecialist.
    Generic structure supports ANY messaging platform.
    """

    platform: str = Field(
        description="Source messaging platform (whatsapp, telegram, sms, email, web, slack, discord, etc)"
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
