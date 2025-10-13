"""Cataloging tools exposed to department heads and the Project Manager.

This module mirrors the tool wiring inside `cataloging_department` but
exposes standalone factories so the Project Manager can reuse the same
specialists without duplicating logic. Each tool automatically injects
the single-tenant company context via middleware, keeping with our
Context Engineering strategy.
"""

from __future__ import annotations

from langchain.tools import tool, ToolException

from autifyme_agents.core.middleware import create_company_context_middleware
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.schemas.models import Product
from autifyme_agents.specialists.cataloging_specialist import create_cataloging_specialist


def create_image_analysis_tool(storage: StorageInterface):
    """Create the image analysis specialist tool with middleware injection."""

    if storage is None:
        raise ValueError("storage adapter must be provided and implement StorageInterface")

    from autifyme_agents.specialists.image_analysis_specialist import image_analysis_specialist_invoke

    middleware = create_company_context_middleware(storage)

    @tool("image_analysis_specialist")
    @middleware
    def image_analysis_specialist_tool(
        image_url: str | None = None,
        image_bytes: bytes | None = None,
        mime_type: str | None = None,
        *,
        company_profile,
        config=None,
    ) -> ImageAnalysisResult:
        """Analyze product imagery to produce structured visual insights.

        Accepts either image_url OR image_bytes+mime_type (preferred for serverless).
        Using image_bytes avoids /tmp filesystem issues on serverless platforms.
        """

        return image_analysis_specialist_invoke(
            image_url=image_url,
            image_bytes=image_bytes,
            mime_type=mime_type,
            company_profile=company_profile,
            config=config,
        )

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
    ) -> Product:
        """Transform user instructions (and optional image insights) into a structured Product model.

        Returns the Product directly so the department can access fields like name, price, sizes, colors
        to call save_product with individual field values.
        """

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
            return product  # Return Product directly, not wrapped in CatalogingResult
        except Exception as exc:
            raise ToolException(
                f"Cataloging specialist failed: {str(exc)}"
            ) from exc

    return cataloging_specialist_tool

