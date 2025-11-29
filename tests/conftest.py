"""Shared pytest fixtures for AutifyME tests.

This module provides reusable fixtures for mocking storage, company profiles,
and other dependencies across the test suite.
"""

from __future__ import annotations

import os
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest


# =============================================================================
# Disable LangChain/LangSmith tracing for tests
# =============================================================================
# Set environment variables before any LangChain imports to disable tracing
# This prevents rate limit errors and speeds up test execution
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.schemas.models import CompanyProfile, Product


@pytest.fixture
def mock_company_profile() -> CompanyProfile:
    """Return a test company profile with standard values."""
    return CompanyProfile(
        id="test-company-001",
        name="Test Retail Co",
        brand_voice="Professional, friendly, and informative",
        target_audience="Budget-conscious millennial shoppers",
        style_preferences=["minimalist", "modern", "sustainable"],
        industry="Fashion & Apparel",
    )


@pytest.fixture
def mock_product() -> Product:
    """Return a test product with standard values."""
    return Product(
        id=uuid.UUID("12345678-1234-1234-1234-123456789012"),
        name="Classic Canvas Sneakers",
        description="Comfortable and stylish canvas sneakers perfect for everyday wear",
        price=79.99,
        sizes=["7", "8", "9", "10", "11"],
        colors=["white", "navy", "beige"],
        image_urls=["https://example.com/image1.jpg"],
    )


@pytest.fixture
def mock_image_analysis() -> ImageAnalysisResult:
    """Return a test image analysis result."""
    return ImageAnalysisResult(
        visual_description="A pair of white canvas sneakers with rubber soles",
        identified_colors=["white", "beige"],
        style_tags=["casual", "minimalist", "modern"],
    )


@pytest.fixture
def mock_storage(mock_company_profile: CompanyProfile, mock_product: Product) -> StorageInterface:
    """Return a mock storage adapter with standard test data.

    The mock automatically returns test data for standard operations:
    - get_company_profile() -> mock_company_profile
    - save_product() -> mock_product (with updated fields)
    - get_pending_approval() -> None (no pending approvals)
    """

    class MockStorageClient(StorageInterface):
        def __init__(self):
            self.saved_products: list[Product] = []
            self.pending_approvals: dict[str, Any] = {}

        def get_company_profile(self) -> CompanyProfile:
            return mock_company_profile

        def save_product(self, product: Product) -> Product:
            # Simulate database save (generate ID if not present)
            if product.id is None:
                product.id = uuid.uuid4()
            self.saved_products.append(product)
            return product

        def get_product(self, product_id: uuid.UUID) -> Product | None:
            for p in self.saved_products:
                if p.id == product_id:
                    return p
            return None

        def list_products(self, limit: int = 100, offset: int = 0) -> list[Product]:
            return self.saved_products[offset : offset + limit]

        def save_pending_approval(
            self,
            thread_id: str,
            interrupt_id: str,
            checkpoint_id: str,
            tool_call: dict[str, Any],
            draft_summary: str,
            ai_message: dict[str, Any] | None = None,
            image_path: str | None = None,
            agent_source: str = "cataloging_department",
            checkpoint_ns: str | None = None,
        ) -> str:
            approval_id = str(uuid.uuid4())
            self.pending_approvals[thread_id] = {
                "id": approval_id,
                "interrupt_id": interrupt_id,
                "checkpoint_id": checkpoint_id,
                "tool_call": tool_call,
                "draft_summary": draft_summary,
                "ai_message": ai_message,
                "image_path": image_path,
                "agent_source": agent_source,
                "checkpoint_ns": checkpoint_ns,
            }
            return approval_id

        def get_pending_approval(self, thread_id: str) -> dict[str, Any] | None:
            return self.pending_approvals.get(thread_id)

        def delete_pending_approval(self, thread_id: str) -> bool:
            return self.pending_approvals.pop(thread_id, None) is not None

        def save_workflow_outcome(self, outcome: dict[str, Any]) -> str:
            """Mock implementation for saving workflow outcomes."""
            return str(uuid.uuid4())

        def get_workflow_outcomes(
            self,
            *,
            time_window: timedelta | None = None,
            intent: str | None = None,
            department: str | None = None,
            success: bool | None = None,
            limit: int = 100,
        ) -> list[dict[str, Any]]:
            """Mock implementation for getting workflow outcomes."""
            return []

        def get_recent_failures(
            self,
            time_window: timedelta,
            limit: int = 10,
        ) -> list[dict[str, Any]]:
            """Mock implementation for getting recent failures."""
            return []

        def get_success_rates(
            self,
            time_window: timedelta | None = None,
        ) -> list[dict[str, Any]]:
            """Mock implementation for getting success rates."""
            return [{"department": "overall", "success_rate_pct": 95.0}]

        def get_edge_cases(
            self,
            time_window: timedelta | None = None,
            max_occurrence_count: int = 3,
            limit: int = 20,
        ) -> list[dict[str, Any]]:
            """Mock implementation for getting edge cases."""
            return []

        def check_and_mark_message_processed(
            self,
            message_id: str,
            sender_id: str,
            thread_id: str,
            received_at: Any,
        ) -> bool:
            """Mock implementation for webhook idempotency check.

            Returns False (not duplicate) for all messages in tests.
            """
            return False

        def cleanup(self) -> None:
            """Mock implementation for cleanup.

            No resources to clean up in test mock.
            """
            pass

    return MockStorageClient()


@pytest.fixture
def memory_checkpointer():
    """Return an in-memory checkpointer for testing."""
    return MemorySaver()


@pytest.fixture
def sample_messages():
    """Return sample LangChain messages for testing."""
    return [
        HumanMessage(content="Please catalog a new t-shirt, price $29.99"),
        AIMessage(
            content="I'll catalog that product for you.",
            tool_calls=[
                {
                    "id": "call_123",
                    "name": "cataloging_specialist",
                    "args": {"user_message": "Please catalog a new t-shirt, price $29.99"},
                }
            ],
        ),
        ToolMessage(
            content='{"name": "Classic T-Shirt", "price": 29.99}',
            tool_call_id="call_123",
        ),
    ]


@pytest.fixture
def temp_image_file(tmp_path: Path) -> Path:
    """Create a temporary test image file."""
    image_path = tmp_path / "test_product.jpg"
    # Create a minimal valid JPEG file (1x1 pixel)
    jpeg_data = bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000ffdb00430001010101010101"
        "01010101010101010101010101010101010101010101010101010101010101"
        "01010101010101010101010101ffc00011080001000103012200021101031101"
        "ffda000c03010002110311003f00f3b4ffd900"
    )
    image_path.write_bytes(jpeg_data)
    return image_path


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests to prevent state leakage.

    This ensures each test starts with a clean slate and doesn't inherit
    state from previous tests.
    """
    # Import here to avoid circular dependencies
    from autifyme_agents.integrations.storage import postgres_saver_factory

    # Reset checkpointer singleton
    postgres_saver_factory._checkpointer_instance = None
    postgres_saver_factory._checkpointer_cm = None

    yield

    # Cleanup after test
    postgres_saver_factory._checkpointer_instance = None
    postgres_saver_factory._checkpointer_cm = None
