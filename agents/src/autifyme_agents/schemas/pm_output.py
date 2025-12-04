"""Structured output schema for Project Manager responses.

Enables PM to return multimodal responses (text + images) in a type-safe format.
Used with ToolStrategy to enforce structured output from DeepAgents.

Architecture:
- PM uses response_format=ToolStrategy(schema=PMOutput)
- Result contains structured_response key with typed PMOutput
- WorkflowRunner processes images and message separately
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImageAttachment(BaseModel):
    """Image to send to user as part of PM response.

    Used for previews, comparisons, exports - any image that doesn't require
    database persistence (WriteIntent handles persistence flows).
    """

    path: str = Field(
        ...,
        description="Image source: storage_path (e.g., 'pending/thread_id/image.png') or local path",
    )
    caption: str | None = Field(
        default=None,
        description="Optional caption to send with the image",
    )


class PMOutput(BaseModel):
    """Structured output for PM responses to user.

    Supports three response patterns:
    1. Text only: message filled, images=None
    2. Text + images: message + images filled (images sent first)
    3. Feedback loop: await_feedback=True pauses for user response

    Note: For database operations, PM delegates to Catalog Specialist
    which triggers WriteIntent flow (separate from this schema).
    """

    message: str = Field(
        ...,
        description="Text message to send to user. Always required.",
    )
    images: list[ImageAttachment] | None = Field(
        default=None,
        description=(
            "Images to send before the message. Include when showing processed images, "
            "comparisons, or exports. Each image is sent as a separate message."
        ),
    )
    await_feedback: bool = Field(
        default=False,
        description=(
            "Set to True when PM needs user response before continuing. "
            "Use for preview confirmations, iterative refinement loops, or choices."
        ),
    )
