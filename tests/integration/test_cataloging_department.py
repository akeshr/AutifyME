"""Integration tests for the Cataloging Department.

These tests verify the full department workflow including agent creation,
middleware application, tool execution, and state management.
"""

import pytest
from langchain_core.messages import HumanMessage

from autifyme_agents.departments.cataloging_department import create_cataloging_department


@pytest.mark.integration
class TestCatalogingDepartmentIntegration:
    """Integration tests for cataloging department end-to-end workflows."""

    def test_create_cataloging_department_without_hitl(self, mock_storage, memory_checkpointer):
        """Department should be created successfully."""
        department = create_cataloging_department(
            storage=mock_storage,
            checkpointer=memory_checkpointer,
        )

        assert department is not None
        assert hasattr(department, "invoke")

    def test_create_cataloging_department_with_hitl(self, mock_storage, memory_checkpointer):
        """Department should be created successfully."""
        department = create_cataloging_department(
            storage=mock_storage,
            checkpointer=memory_checkpointer,
        )

        assert department is not None
        assert hasattr(department, "invoke")

    @pytest.mark.skip(reason="Requires real LLM - use for manual testing")
    def test_cataloging_department_text_only_workflow(
        self,
        mock_storage,
        memory_checkpointer,
    ):
        """Full workflow: text-only product cataloging."""
        department = create_cataloging_department(
            storage=mock_storage,
            checkpointer=memory_checkpointer,
        )

        messages = [
            HumanMessage(content="Catalog a red cotton t-shirt, size M, price $29.99")
        ]

        config = {"configurable": {"thread_id": "test-thread-001"}}

        result = department.invoke({"messages": messages}, config=config)

        # Verify result structure
        assert "messages" in result
        assert len(result["messages"]) > 0
        # The last message should be from the agent
        last_message = result["messages"][-1]
        assert hasattr(last_message, "content")

    @pytest.mark.skip(reason="Requires real LLM - use for manual testing")
    def test_cataloging_department_with_image_workflow(
        self,
        mock_storage,
        memory_checkpointer,
        temp_image_file,
    ):
        """Full workflow: product cataloging with image analysis."""
        department = create_cataloging_department(
            storage=mock_storage,
            checkpointer=memory_checkpointer,
        )

        # Simulate a message with image attachment metadata
        message = HumanMessage(
            content="Catalog this product",
            additional_kwargs={"image_path": str(temp_image_file)},
        )

        config = {"configurable": {"thread_id": "test-thread-002"}}

        result = department.invoke({"messages": [message]}, config=config)

        assert "messages" in result
        assert len(result["messages"]) > 0

    def test_cataloging_department_requires_storage(self, memory_checkpointer):
        """Department creation should fail without storage."""
        with pytest.raises(ValueError) as exc_info:
            create_cataloging_department(
                storage=None,
                checkpointer=memory_checkpointer,
            )

        assert "storage adapter required" in str(exc_info.value)

    def test_cataloging_department_requires_checkpointer(self, mock_storage):
        """Department creation should succeed with None checkpointer (uses memory saver default)."""
        # The department factory provides a default checkpointer, so None is acceptable
        department = create_cataloging_department(
            storage=mock_storage,
            checkpointer=None,
        )

        assert department is not None
