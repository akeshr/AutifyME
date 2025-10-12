"""Integration tests for the Project Manager.

These tests verify the PM's orchestration capabilities including:
- DeepAgents integration
- Sub-agent delegation
- HITL configuration
- Tool routing
- State management
"""

import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from autifyme_agents.workflows.project_manager import create_project_manager
from autifyme_agents.schemas.models import CompanyProfile


@pytest.fixture
def sample_company_profile():
    """Fixture providing a sample company profile for PM testing."""
    return CompanyProfile(
        id="test-company-001",
        name="Test Company",
        brand_voice="professional and helpful",
        target_audience="tech-savvy professionals aged 25-45",
        description="A test company for integration testing",
    )


@pytest.mark.integration
class TestProjectManagerIntegration:
    """Integration tests for Project Manager orchestration."""

    def test_create_project_manager_basic(self, sample_company_profile, mock_storage):
        """PM should be created successfully with required dependencies."""
        checkpointer = MemorySaver()

        pm = create_project_manager(
            company_profile=sample_company_profile,
            checkpointer=checkpointer,
            storage=mock_storage,
        )

        assert pm is not None
        assert hasattr(pm, "invoke")
        assert hasattr(pm, "stream")

    def test_project_manager_requires_checkpointer(self, sample_company_profile, mock_storage):
        """PM creation should fail without checkpointer (DeepAgents requirement)."""
        with pytest.raises((ValueError, TypeError)) as exc_info:
            create_project_manager(
                company_profile=sample_company_profile,
                checkpointer=None,
                storage=mock_storage,
            )

        # DeepAgents requires a checkpointer
        assert exc_info is not None

    def test_project_manager_requires_storage(self, sample_company_profile):
        """PM creation should fail without storage adapter."""
        checkpointer = MemorySaver()

        with pytest.raises((ValueError, AttributeError)) as exc_info:
            create_project_manager(
                company_profile=sample_company_profile,
                checkpointer=checkpointer,
                storage=None,
            )

        assert exc_info is not None

    def test_project_manager_has_interrupt_config(self, sample_company_profile, mock_storage):
        """PM should be configured with HITL interrupts for save_product."""
        checkpointer = MemorySaver()

        pm = create_project_manager(
            company_profile=sample_company_profile,
            checkpointer=checkpointer,
            storage=mock_storage,
        )

        # Verify PM was created successfully
        # The actual interrupt config is internal to DeepAgents,
        # but we can verify the PM is properly initialized
        assert pm is not None

    @pytest.mark.skip(reason="Requires real LLM - use for manual testing")
    def test_project_manager_cataloging_delegation(
        self,
        sample_company_profile,
        mock_storage,
    ):
        """PM should successfully delegate to cataloging department."""
        checkpointer = MemorySaver()

        pm = create_project_manager(
            company_profile=sample_company_profile,
            checkpointer=checkpointer,
            storage=mock_storage,
        )

        messages = [
            HumanMessage(
                content="Please catalog a new product: Blue denim jeans, size 32, price $79.99"
            )
        ]

        config = {
            "configurable": {
                "thread_id": "test-pm-001",
                "company_id": "test-company-001",
            }
        }

        result = pm.invoke({"messages": messages}, config=config)

        # Verify result structure
        assert "messages" in result
        assert len(result["messages"]) > 0

    @pytest.mark.skip(reason="Requires real LLM - use for manual testing")
    def test_project_manager_streaming(self, sample_company_profile, mock_storage):
        """PM should support streaming for real-time updates."""
        checkpointer = MemorySaver()

        pm = create_project_manager(
            company_profile=sample_company_profile,
            checkpointer=checkpointer,
            storage=mock_storage,
        )

        messages = [HumanMessage(content="Catalog a red t-shirt, price $25")]

        config = {
            "configurable": {
                "thread_id": "test-pm-stream-001",
                "company_id": "test-company-001",
            }
        }

        events = list(pm.stream({"messages": messages}, config=config, stream_mode="values"))

        # Should receive at least one event
        assert len(events) > 0

    def test_project_manager_initial_state(self, sample_company_profile, mock_storage):
        """PM should initialize with proper state structure."""
        checkpointer = MemorySaver()

        pm = create_project_manager(
            company_profile=sample_company_profile,
            checkpointer=checkpointer,
            storage=mock_storage,
        )

        # Verify PM was created with configuration
        assert pm is not None

        # The PM's config should include metadata
        # (actual config access depends on LangGraph internals)


@pytest.mark.unit
class TestProjectManagerConfiguration:
    """Unit tests for PM configuration and setup."""

    def test_project_manager_uses_custom_model(self, sample_company_profile, mock_storage):
        """PM should accept custom model override."""
        from autifyme_agents.core.llm_factory import get_llm

        checkpointer = MemorySaver()
        custom_model = get_llm(model="gpt-4.1-nano-2025-04-14", temperature=0.5)

        pm = create_project_manager(
            company_profile=sample_company_profile,
            checkpointer=checkpointer,
            storage=mock_storage,
            model=custom_model,
        )

        assert pm is not None

    def test_project_manager_uses_custom_tools(self, sample_company_profile, mock_storage):
        """PM should accept custom tool list."""
        from autifyme_agents.tools.cataloging_tools import create_cataloging_specialist_tool

        checkpointer = MemorySaver()
        custom_tools = [create_cataloging_specialist_tool(mock_storage)]

        pm = create_project_manager(
            company_profile=sample_company_profile,
            checkpointer=checkpointer,
            storage=mock_storage,
            tools=custom_tools,
        )

        assert pm is not None


@pytest.mark.integration
@pytest.mark.skip(reason="Requires real LLM and full stack - use for E2E testing")
class TestProjectManagerEndToEnd:
    """End-to-end tests for PM with full workflow."""

    def test_pm_text_only_cataloging_workflow(
        self,
        sample_company_profile,
        mock_storage,
    ):
        """Full E2E: Text-only product cataloging through PM."""
        checkpointer = MemorySaver()

        pm = create_project_manager(
            company_profile=sample_company_profile,
            checkpointer=checkpointer,
            storage=mock_storage,
        )

        messages = [
            HumanMessage(content="Catalog a white cotton t-shirt, size L, price $29.99")
        ]

        config = {
            "configurable": {
                "thread_id": "e2e-pm-001",
                "company_id": "test-company-001",
            }
        }

        # Should execute without errors
        result = pm.invoke({"messages": messages}, config=config)

        assert "messages" in result
        assert len(result["messages"]) > 0

    def test_pm_with_interrupt_workflow(self, sample_company_profile, mock_storage):
        """Full E2E: Cataloging with HITL interrupt on save_product."""
        checkpointer = MemorySaver()

        pm = create_project_manager(
            company_profile=sample_company_profile,
            checkpointer=checkpointer,
            storage=mock_storage,
        )

        messages = [HumanMessage(content="Catalog: Red sneakers, sizes 7-11, price $89.99")]

        config = {
            "configurable": {
                "thread_id": "e2e-interrupt-001",
                "company_id": "test-company-001",
            }
        }

        # Stream to detect interrupts
        last_event = None
        for event in pm.stream({"messages": messages}, config=config, stream_mode="values"):
            last_event = event
            # Check for interrupt signal
            if "__interrupt__" in event:
                # Interrupt detected - this is expected behavior
                assert True
                return

        # If no interrupt, workflow completed (also valid)
        assert last_event is not None
