"""Cataloging tools exposed to department heads and the Project Manager.

This module mirrors the tool wiring inside `cataloging_department` but
exposes standalone factories so the Project Manager can reuse the same
specialists without duplicating logic. Each tool automatically injects
the single-tenant company context via middleware, keeping with our
Context Engineering strategy.
"""

from __future__ import annotations

from langchain_core.tools import tool, ToolException

from autifyme_agents.core.middleware import create_company_context_middleware
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.schemas.models import CatalogingResult, Product
from autifyme_agents.specialists.cataloging_specialist import create_cataloging_specialist
from autifyme_agents.specialists.image_analysis_specialist import create_image_analysis_specialist


def create_image_analysis_tool(storage: StorageInterface):
    """Create the image analysis specialist tool with middleware injection."""

    if storage is None:
        raise ValueError("storage adapter must be provided and implement StorageInterface")

    middleware = create_company_context_middleware(storage)
    specialist = create_image_analysis_specialist()

    @tool("image_analysis_specialist")
    @middleware
    def image_analysis_specialist_tool(
        image_url: str,
        *,
        company_profile,
        config=None,
    ) -> ImageAnalysisResult:
        """Analyze product imagery to produce structured visual insights."""

        payload = {
            "input": {
                "image_url": image_url,
                "company_profile": company_profile,
            }
        }
        return specialist.invoke(payload, config=config)

    return image_analysis_specialist_tool


def create_cataloging_specialist_tool(storage: StorageInterface):
    """Create the cataloging specialist tool with middleware injection."""

    if storage is None:
        raise ValueError("storage adapter must be provided and implement StorageInterface")

    middleware = create_company_context_middleware(storage)
    specialist = create_cataloging_specialist()

    @tool("cataloging_specialist")
    @middleware
    def cataloging_specialist_tool(
        user_message: str,
        image_analysis: dict | None = None,
        *,
        company_profile,
        config=None,
    ) -> CatalogingResult:
        """Transform user instructions (and optional image insights) into a catalog-ready product summary."""

        parsed = None
        if image_analysis is not None:
            parsed = ImageAnalysisResult.model_validate(image_analysis).model_dump(mode="json")

        payload = {
            "input": {
                "user_message": user_message,
                "image_analysis": parsed,
            }
        }

        try:
            product: Product = specialist.invoke(payload, config=config)
            return CatalogingResult(
                stage="draft",
                success=True,
                product_id=product.id,
                product_name=product.name,
                message="Draft product ready for approval",
                data={"draft": product.model_dump()},
            )
        except Exception as exc:
            raise ToolException(
                f"Cataloging specialist failed: {str(exc)}"
            ) from exc

    return cataloging_specialist_tool

