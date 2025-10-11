"""Unit tests for middleware utilities.

Tests the company context injection middleware and LangSmith tracing middleware.
"""

import pytest
from unittest.mock import Mock

from autifyme_agents.core.middleware import (
    CompanyContextMiddleware,
    create_company_context_middleware,
    langsmith_tracing_middleware,
)
from autifyme_agents.schemas.models import CompanyProfile


class TestCompanyContextMiddleware:
    """Test CompanyContextMiddleware class for LangChain v1 agents."""

    def test_create_middleware_requires_storage(self):
        """Middleware should raise error if storage is None."""
        with pytest.raises(ValueError) as exc_info:
            CompanyContextMiddleware(storage=None)

        assert "storage adapter is required" in str(exc_info.value)

    def test_middleware_before_model_caches_profile(self, mock_storage, mock_company_profile):
        """Middleware should cache company profile on first call."""
        middleware = CompanyContextMiddleware(storage=mock_storage)

        # Profile should not be cached yet
        assert middleware._profile_cache is None

        # Call before_model
        result = middleware.before_model(state={}, runtime=Mock())

        # Profile should now be cached
        assert middleware._profile_cache is not None
        assert middleware._profile_cache.id == mock_company_profile.id
        assert middleware._profile_cache.name == mock_company_profile.name

        # Verify it returns None (LangChain v1 middleware pattern)
        assert result is None

    def test_middleware_caches_profile_across_calls(self, mock_storage):
        """Middleware should only fetch profile once."""
        middleware = CompanyContextMiddleware(storage=mock_storage)

        # Make mock storage track call count
        original_get = mock_storage.get_company_profile
        call_count = 0

        def tracked_get():
            nonlocal call_count
            call_count += 1
            return original_get()

        mock_storage.get_company_profile = tracked_get

        # First call
        middleware.before_model(state={}, runtime=Mock())
        assert call_count == 1

        # Second call - should use cache
        middleware.before_model(state={}, runtime=Mock())
        assert call_count == 1  # No additional call


class TestCompanyContextDecoratorMiddleware:
    """Test decorator-based company context middleware."""

    def test_create_decorator_middleware_requires_storage(self):
        """Decorator factory should raise error if storage is None."""
        with pytest.raises(ValueError) as exc_info:
            create_company_context_middleware(storage=None)

        assert "storage adapter is required" in str(exc_info.value)

    def test_decorator_injects_company_profile_sync(self, mock_storage, mock_company_profile):
        """Decorator should inject company_profile into sync function kwargs."""
        middleware = create_company_context_middleware(mock_storage)

        @middleware
        def test_tool(*, company_profile=None):
            return company_profile

        result = test_tool()

        assert isinstance(result, CompanyProfile)
        assert result.id == mock_company_profile.id

    @pytest.mark.asyncio
    async def test_decorator_injects_company_profile_async(self, mock_storage, mock_company_profile):
        """Decorator should inject company_profile into async function kwargs."""
        middleware = create_company_context_middleware(mock_storage)

        @middleware
        async def async_test_tool(*, company_profile=None):
            return company_profile

        result = await async_test_tool()

        assert isinstance(result, CompanyProfile)
        assert result.id == mock_company_profile.id

    def test_decorator_preserves_existing_profile(self, mock_storage):
        """Decorator should not override if profile already provided."""
        middleware = create_company_context_middleware(mock_storage)

        custom_profile = CompanyProfile(
            id="custom",
            name="Custom Co",
            brand_voice="Custom voice",
            target_audience="Custom audience",
        )

        @middleware
        def test_tool(*, company_profile=None):
            return company_profile

        result = test_tool(company_profile=custom_profile)

        assert result.id == "custom"
        assert result.name == "Custom Co"


class TestLangSmithTracingMiddleware:
    """Test LangSmith tracing middleware decorator."""

    def test_tracing_middleware_adds_metadata_sync(self):
        """Middleware should add workflow metadata to config."""
        @langsmith_tracing_middleware("cataloging")
        def test_tool(*, config=None):
            return config

        config = test_tool(config={})

        assert "metadata" in config
        assert config["metadata"]["workflow"] == "cataloging"
        assert config["metadata"]["tool_name"] == "test_tool"

    def test_tracing_middleware_adds_tags_sync(self):
        """Middleware should add workflow tags."""
        @langsmith_tracing_middleware("cataloging")
        def test_tool(*, config=None):
            return config

        config = test_tool(config={})

        assert "tags" in config
        assert "workflow:cataloging" in config["tags"]

    def test_tracing_middleware_adds_run_name_sync(self):
        """Middleware should prefix run_name with workflow."""
        @langsmith_tracing_middleware("cataloging")
        def test_tool(*, config=None):
            return config

        config = test_tool(config={})

        assert "run_name" in config
        assert config["run_name"] == "cataloging-test_tool"

    @pytest.mark.asyncio
    async def test_tracing_middleware_works_async(self):
        """Middleware should work with async functions."""
        @langsmith_tracing_middleware("cataloging")
        async def async_test_tool(*, config=None):
            return config

        config = await async_test_tool(config={})

        assert config["metadata"]["workflow"] == "cataloging"
        assert "workflow:cataloging" in config["tags"]

    def test_tracing_middleware_preserves_existing_metadata(self):
        """Middleware should merge with existing config."""
        @langsmith_tracing_middleware("cataloging")
        def test_tool(*, config=None):
            return config

        existing_config = {
            "metadata": {"custom_field": "custom_value"},
            "tags": ["existing-tag"],
        }

        config = test_tool(config=existing_config)

        # Should preserve existing metadata
        assert config["metadata"]["custom_field"] == "custom_value"
        # Should add workflow metadata
        assert config["metadata"]["workflow"] == "cataloging"
        # Should preserve existing tags
        assert "existing-tag" in config["tags"]
        # Should add workflow tag
        assert "workflow:cataloging" in config["tags"]
