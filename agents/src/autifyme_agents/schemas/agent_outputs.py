"""Structured output schemas for agent responses."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from autifyme_agents.schemas.models import CatalogingResult


class AgentOutput(BaseModel):
    """Base model for all agent outputs with consistent success flag."""
    success: bool = Field(..., description="Indicates whether the operation was successful.")
    message: str | None = Field(None, description="Details about the outcome.")


class ProductCatalogedOutput(AgentOutput):
    """Output schema for successful product cataloging."""
    success: Literal[True] = Field(True, description="Always True for successful cataloging.")
    product_id: UUID = Field(..., description="The unique identifier of the saved product.")
    message: str = Field("Product has been successfully saved to the catalog.")
    product: dict[str, Any] = Field(..., description="The full product record saved to the catalog.")


class ErrorOutput(AgentOutput):
    """Output schema for reporting errors."""
    success: Literal[False] = Field(False, description="Always False for errors.")
    error_type: str = Field(..., description="The type of error (e.g., 'Validation Error', 'API Failure').")
    message: str = Field(..., description="Detailed error message.")


class ImageAnalysisResult(BaseModel):
    """
    Structured output for image analysis specialist.

    Used with .with_structured_output() to ensure LLM returns valid data.
    """
    visual_description: str = Field(
        ...,
        description="Detailed, objective product description suitable for e-commerce.",
        min_length=20
    )
    identified_colors: list[str] = Field(
        default_factory=list,
        description="Dominant colors in the product."
    )
    style_tags: list[str] = Field(
        default_factory=list,
        description="Style keywords (e.g., 'vintage', 'modern', 'minimalist')."
    )


class CatalogingToolOutput(BaseModel):
    """Structured message emitted by the save_product tool."""

    tool_name: Literal["save_product"] = Field(..., description="Name of the tool producing the output.")
    result: CatalogingResult = Field(..., description="Serialized cataloging result payload.")
