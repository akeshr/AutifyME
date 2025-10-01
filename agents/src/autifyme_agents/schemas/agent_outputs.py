from pydantic import BaseModel, Field, Literal
from typing import Optional
from uuid import UUID

class AgentOutput(BaseModel):
    """Base model for all agent outputs, ensuring a consistent success flag."""
    success: bool = Field(..., description="Indicates whether the operation was successful.")
    message: Optional[str] = Field(None, description="A message providing details about the outcome.")

class ProductCatalogedOutput(AgentOutput):
    """
    Output schema for when a product has been successfully saved.
    """
    success: bool = Field(True, Literal=True)
    product_id: UUID = Field(..., description="The unique identifier of the saved product.")
    message: str = Field("Product has been successfully saved to the catalog.", description="Confirmation message.")

class ErrorOutput(AgentOutput):
    """
    Output schema for reporting an error.
    """
    success: bool = Field(False, Literal=True)
    error_type: str = Field(..., description="The type of error that occurred (e.g., 'Validation Error', 'API Failure').")
    message: str = Field(..., description="A detailed message describing the error.")
