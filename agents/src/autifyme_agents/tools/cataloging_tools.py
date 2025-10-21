"""Cataloging tools exposed to department heads and the Project Manager.

NOTE: This module is currently UNUSED in production code (not imported anywhere).
It was intended for PM tool delegation but the current architecture uses
departments which invoke specialists directly, not via these standalone tools.

Consider removing in future cleanup if PM integration doesn't materialize.
"""

from __future__ import annotations

from typing import Any

from langchain.tools import ToolException, tool

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.schemas.models import CompanyProfile, Product
from autifyme_agents.specialists.cataloging_specialist import create_cataloging_specialist


def create_image_analysis_tool(storage: StorageInterface) -> Any:
    """Create the image analysis specialist tool.

    NOTE: Company profile must be fetched and passed explicitly by caller.
    No automatic middleware injection - caller is responsible for context.
    """

    if storage is None:
        raise ValueError("storage adapter must be provided and implement StorageInterface")

    from autifyme_agents.specialists.image_analysis_specialist import (
        image_analysis_specialist_invoke,
    )

    @tool("image_analysis_specialist")
    def image_analysis_specialist_tool(
        image_url: str | None = None,
        image_bytes: bytes | None = None,
        mime_type: str | None = None,
        company_profile: CompanyProfile | None = None,
        config: dict[str, Any] | None = None,
    ) -> ImageAnalysisResult:
        """Analyze product imagery to produce structured visual insights.

        Accepts either image_url OR image_bytes+mime_type (preferred for serverless).
        Using image_bytes avoids /tmp filesystem issues on serverless platforms.

        Args:
            image_url: URL to image (if not using bytes)
            image_bytes: Raw image bytes (preferred)
            mime_type: MIME type of image (required with image_bytes)
            company_profile: Company context (required - fetch via storage.get_company_profile())
            config: Optional LangChain config
        """
        if company_profile is None:
            # Fetch if not provided (fallback for backward compatibility)
            company_profile = storage.get_company_profile()

        return image_analysis_specialist_invoke(
            image_url=image_url,
            image_bytes=image_bytes,
            mime_type=mime_type,
            company_profile=company_profile,
            config=config,
        )

    return image_analysis_specialist_tool


def create_cataloging_specialist_tool(storage: StorageInterface) -> Any:
    """Create the cataloging specialist tool.

    NOTE: Company profile must be fetched and passed explicitly by caller.
    No automatic middleware injection - caller is responsible for context.
    """

    if storage is None:
        raise ValueError("storage adapter must be provided and implement StorageInterface")

    specialist = create_cataloging_specialist()

    @tool("cataloging_specialist")
    def cataloging_specialist_tool(
        user_message: str,
        image_analysis: dict[str, Any] | None = None,
        company_profile: CompanyProfile | None = None,
        config: dict[str, Any] | None = None,
    ) -> Product:
        """Transform user instructions (and optional image insights) into a structured Product model.

        Returns the Product directly so the department can access fields like name, price, sizes, colors
        to call save_product with individual field values.

        Args:
            user_message: User's product description
            image_analysis: Optional visual analysis results
            company_profile: Company context (required - fetch via storage.get_company_profile())
            config: Optional LangChain config
        """
        if company_profile is None:
            # Fetch if not provided (fallback for backward compatibility)
            company_profile = storage.get_company_profile()

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

