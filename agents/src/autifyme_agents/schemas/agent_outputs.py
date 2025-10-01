"""Structured output schemas for agent responses."""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from uuid import UUID


class AgentOutput(BaseModel):
    """Base model for all agent outputs with consistent success flag."""
    success: bool = Field(..., description="Indicates whether the operation was successful.")
    message: Optional[str] = Field(None, description="Details about the outcome.")


class ProductCatalogedOutput(AgentOutput):
    """Output schema for successful product cataloging."""
    success: Literal[True] = Field(True, description="Always True for successful cataloging.")
    product_id: UUID = Field(..., description="The unique identifier of the saved product.")
    message: str = Field("Product has been successfully saved to the catalog.")


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
    identified_colors: List[str] = Field(
        default_factory=list,
        description="Dominant colors in the product."
    )
    style_tags: List[str] = Field(
        default_factory=list,
        description="Style keywords (e.g., 'vintage', 'modern', 'minimalist')."
    )
