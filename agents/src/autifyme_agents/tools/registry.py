"""Tool registry for Project Manager and department sub-agents.

This module enforces the Context Engineering principle by exposing
department-specific tool bundles and corresponding instructions. It
also centralizes HITL interrupt configuration so the Project Manager
can honour approval workflows without custom logic scattered across
call sites.
"""

from __future__ import annotations

from langchain.agents.middleware.human_in_the_loop import ToolConfig

from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.tools.cataloging_tools import (
    create_cataloging_specialist_tool,
    create_image_analysis_tool,
)
from autifyme_agents.tools.storage_tools import (
    create_get_company_profile_tool,
    create_save_product_tool,
)


def get_cataloging_tool_objects(storage: StorageInterface) -> list:
    """Return instantiated tools for the cataloging department."""

    if storage is None:
        raise ValueError("storage adapter must implement StorageInterface")

    cataloging_specialist = create_cataloging_specialist_tool(storage)
    analyze_image = create_image_analysis_tool(storage)
    save_product = create_save_product_tool(storage)
    get_company_profile = create_get_company_profile_tool(storage)

    return [
        cataloging_specialist,
        analyze_image,
        save_product,
        get_company_profile,
    ]


def get_cataloging_tool_names() -> list[str]:
    return [
        "cataloging_specialist",
        "image_analysis_specialist",
        "save_product",
        "get_company_profile",
    ]


def get_cataloging_instructions(company_profile: CompanyProfile) -> str:
    prompt = load_prompt("departments/cataloging_department.prompt")

    strategic_priorities = getattr(company_profile, "strategic_priorities", None)
    priorities_text = ", ".join(strategic_priorities) if strategic_priorities else "n/a"

    return prompt.format(
        company_name=company_profile.name,
        brand_voice=company_profile.brand_voice,
        target_audience=company_profile.target_audience,
        strategic_priorities=priorities_text,
    )


def get_interrupt_config() -> dict[str, ToolConfig]:
    return {
        "save_product": {
            "allow_accept": True,
            "allow_edit": True,
            "allow_respond": True,
            "description": "Approve or modify the product before it is persisted to storage.",
        }
    }


