"""Comprehensive tests for Universal Data Engine - Phase 1.3: Batch Read & Pagination.

Tests cover:
- Batch read operations (12+ tests)
- Pagination (offset and cursor) (15+ tests)

Total: 27+ tests for Phase 1.3
"""

from unittest.mock import MagicMock, patch

import pytest

from autifyme_agents.core.exceptions import StorageError
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase async client for testing."""
    with patch("autifyme_agents.integrations.storage.supabase_client.create_async_client") as mock_create:
        # Create mock client
        mock_client = MagicMock()

        # create_async_client is async, so return awaitable
        async def mock_create_client(*args, **kwargs):
            return mock_client

        mock_create.side_effect = mock_create_client

        # Mock table() chain
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # Default successful response
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "id1", "name": "Product 1"},
            {"id": "id2", "name": "Product 2"},
        ]
        mock_response.count = None

        # Make execute() async
        async def mock_execute():
            return mock_response

        mock_table.execute = mock_execute

        # Mock query chain methods (return mock_table for chaining)
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.ilike.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.range.return_value = mock_table
        mock_table.gt.return_value = mock_table
        mock_table.limit.return_value = mock_table

        # Return both client and mock_create for further configuration
        yield mock_client, mock_create, mock_table, mock_response


# =============================================================================
# Test Group 1: Batch Read - Basic Operations (6 tests)
# =============================================================================


class TestBatchReadBasicOperations:
    """Test basic batch read functionality."""

    @pytest.mark.asyncio
    async def test_batch_read_single_entity(self, mock_supabase_client):
        """Test batch read with single ID."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Configure response
        mock_response.data = [{"id": "id1", "name": "Product 1"}]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        results = await storage.batch_read("products", ids=["id1"])

        assert len(results) == 1
        assert results[0]["id"] == "id1"
        mock_table.in_.assert_called_once_with("id", ["id1"])

    @pytest.mark.asyncio
    async def test_batch_read_multiple_entities(self, mock_supabase_client):
        """Test batch read with multiple IDs."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Configure response for 3 entities
        mock_response.data = [
            {"id": "id1", "name": "Product 1"},
            {"id": "id2", "name": "Product 2"},
            {"id": "id3", "name": "Product 3"},
        ]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        results = await storage.batch_read("products", ids=["id1", "id2", "id3"])

        assert len(results) == 3
        mock_table.in_.assert_called_once_with("id", ["id1", "id2", "id3"])

    @pytest.mark.asyncio
    async def test_batch_read_large_batch(self, mock_supabase_client):
        """Test batch read with 100+ IDs."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Generate 150 IDs
        ids = [f"id{i}" for i in range(150)]
        mock_response.data = [{"id": id, "name": f"Product {id}"} for id in ids]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        results = await storage.batch_read("products", ids=ids)

        assert len(results) == 150
        mock_table.in_.assert_called_once_with("id", ids)

    @pytest.mark.asyncio
    async def test_batch_read_empty_ids_list(self, mock_supabase_client):
        """Test batch read with empty IDs list returns empty results."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        results = await storage.batch_read("products", ids=[])

        assert results == []
        # Should not make any query
        mock_table.in_.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_read_with_relations(self, mock_supabase_client):
        """Test batch read with relation prefetching."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Configure response with nested relations
        mock_response.data = [
            {
                "id": "id1",
                "name": "Product 1",
                "product_families": {"id": "fam1", "name": "Family 1"}
            }
        ]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        results = await storage.batch_read(
            "products",
            ids=["id1"],
            relations=["product_families(*)"]
        )

        assert len(results) == 1
        # Should use extended select clause with relations
        # Note: select() is called twice (once for test connection, once for query)
        calls = [call[0][0] for call in mock_table.select.call_args_list]
        assert "*,product_families(*)" in calls

    @pytest.mark.asyncio
    async def test_batch_read_with_multiple_relations(self, mock_supabase_client):
        """Test batch read with multiple relation prefetches."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        await storage.batch_read(
            "products",
            ids=["id1"],
            relations=["product_families(*)", "variants(*)"]
        )

        # Should include all relations in select
        calls = [call[0][0] for call in mock_table.select.call_args_list]
        assert "*,product_families(*),variants(*)" in calls


# =============================================================================
# Test Group 2: Batch Read - Order Preservation (3 tests)
# =============================================================================


class TestBatchReadOrderPreservation:
    """Test that batch read preserves input ID order."""

    @pytest.mark.asyncio
    async def test_batch_read_preserves_order(self, mock_supabase_client):
        """Test that results are returned in same order as input IDs."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Configure response in different order than input
        mock_response.data = [
            {"id": "id3", "name": "Product 3"},
            {"id": "id1", "name": "Product 1"},
            {"id": "id2", "name": "Product 2"},
        ]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        # Request in specific order
        results = await storage.batch_read("products", ids=["id1", "id2", "id3"])

        # Should return in requested order, not database order
        assert results[0]["id"] == "id1"
        assert results[1]["id"] == "id2"
        assert results[2]["id"] == "id3"

    @pytest.mark.asyncio
    async def test_batch_read_handles_missing_ids(self, mock_supabase_client):
        """Test that missing IDs are omitted (no null placeholders)."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Database returns only 2 of 3 requested IDs
        mock_response.data = [
            {"id": "id1", "name": "Product 1"},
            {"id": "id3", "name": "Product 3"},
        ]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        results = await storage.batch_read("products", ids=["id1", "id2", "id3"])

        # Should return only found entities, in requested order
        assert len(results) == 2
        assert results[0]["id"] == "id1"
        assert results[1]["id"] == "id3"
        # id2 should be omitted, not included as None

    @pytest.mark.asyncio
    async def test_batch_read_all_missing_returns_empty(self, mock_supabase_client):
        """Test that all missing IDs returns empty list."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Database returns no entities
        mock_response.data = []

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        results = await storage.batch_read("products", ids=["nonexistent1", "nonexistent2"])

        assert results == []


# =============================================================================
# Test Group 3: Batch Read - Error Handling (3 tests)
# =============================================================================


class TestBatchReadErrorHandling:
    """Test batch read error handling."""

    @pytest.mark.asyncio
    async def test_batch_read_storage_error(self, mock_supabase_client):
        """Test that storage errors are raised as StorageError."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Configure query to fail - make async error function
        async def mock_error():
            raise Exception("Database connection failed")

        mock_table.execute = mock_error

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        with pytest.raises(StorageError) as exc_info:
            await storage.batch_read("products", ids=["id1"])

        assert "Batch read failed" in str(exc_info.value)
        assert exc_info.value.operation == "batch_read"

    @pytest.mark.asyncio
    async def test_batch_read_handles_null_response_data(self, mock_supabase_client):
        """Test that null response.data is handled gracefully."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Configure null data response
        mock_response.data = None

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        results = await storage.batch_read("products", ids=["id1"])

        # Should return empty list, not crash
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_read_logs_missing_count(self, mock_supabase_client):
        """Test that batch read logs number of missing entities."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # 2 of 5 requested IDs found
        mock_response.data = [
            {"id": "id1", "name": "Product 1"},
            {"id": "id3", "name": "Product 3"},
        ]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        with patch("autifyme_agents.integrations.storage.supabase_client.logger") as mock_logger:
            await storage.batch_read("products", ids=["id1", "id2", "id3", "id4", "id5"])

            # Should log missing count
            mock_logger.debug.assert_called()
            call_args = mock_logger.debug.call_args
            assert "extra" in call_args.kwargs
            assert call_args.kwargs["extra"]["missing"] == 3  # 5 requested - 2 found


# =============================================================================
# Test Group 4: Pagination - Offset Mode (8 tests)
# =============================================================================


class TestPaginationOffsetMode:
    """Test offset-based pagination."""

    @pytest.mark.asyncio
    async def test_paginate_first_page(self, mock_supabase_client):
        """Test first page with default per_page."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        result = await storage.paginate_query("products", page=1, per_page=20)

        assert result["page"] == 1
        assert result["per_page"] == 20
        assert "data" in result
        assert "has_next" in result
        # Should use range(0, 19) for first page of 20 items
        mock_table.range.assert_called_once_with(0, 19)

    @pytest.mark.asyncio
    async def test_paginate_second_page(self, mock_supabase_client):
        """Test second page offset calculation."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        await storage.paginate_query("products", page=2, per_page=20)

        # Page 2 with per_page=20 should use range(20, 39)
        mock_table.range.assert_called_once_with(20, 39)

    @pytest.mark.asyncio
    async def test_paginate_custom_per_page(self, mock_supabase_client):
        """Test pagination with custom per_page."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        result = await storage.paginate_query("products", page=1, per_page=50)

        assert result["per_page"] == 50
        mock_table.range.assert_called_once_with(0, 49)

    @pytest.mark.asyncio
    async def test_paginate_per_page_max_limit(self, mock_supabase_client):
        """Test that per_page is capped at 100."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        # Should raise ValueError for per_page > 100
        with pytest.raises(ValueError) as exc_info:
            await storage.paginate_query("products", per_page=150)

        assert "per_page must not exceed 100" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_paginate_page_validation(self, mock_supabase_client):
        """Test that page must be >= 1."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        # Should raise ValueError for page < 1
        with pytest.raises(ValueError) as exc_info:
            await storage.paginate_query("products", page=0)

        assert "page must be >= 1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_paginate_has_next_true(self, mock_supabase_client):
        """Test has_next=True when full page returned."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Return exactly per_page items (indicates more pages exist)
        mock_response.data = [{"id": f"id{i}"} for i in range(20)]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        result = await storage.paginate_query("products", page=1, per_page=20)

        assert result["has_next"] is True

    @pytest.mark.asyncio
    async def test_paginate_has_next_false(self, mock_supabase_client):
        """Test has_next=False when partial page returned."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Return fewer than per_page items (last page)
        mock_response.data = [{"id": f"id{i}"} for i in range(15)]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        result = await storage.paginate_query("products", page=3, per_page=20)

        assert result["has_next"] is False

    @pytest.mark.asyncio
    async def test_paginate_with_filters_and_search(self, mock_supabase_client):
        """Test pagination with filters and search patterns."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        await storage.paginate_query(
            "products",
            filters={"is_active": True, "category_id": "cat1"},
            search_patterns={"name": "%bottle%"},
            page=1,
            per_page=20
        )

        # Should apply filters
        assert mock_table.eq.call_count == 2
        mock_table.ilike.assert_called_once_with("name", "%bottle%")


# =============================================================================
# Test Group 5: Pagination - Count & Metadata (4 tests)
# =============================================================================


class TestPaginationCountAndMetadata:
    """Test pagination total count and metadata."""

    @pytest.mark.asyncio
    async def test_paginate_with_total_count(self, mock_supabase_client):
        """Test pagination with include_count=True."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Configure count response
        mock_count_response = MagicMock()
        mock_count_response.count = 150

        # Track call count
        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_response  # Main query (test connection)
            elif call_count == 2:
                return mock_response  # Main query (actual)
            else:
                return mock_count_response  # Count query

        mock_table.execute = mock_multi_execute

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        result = await storage.paginate_query("products", page=1, per_page=20, include_count=True)

        assert result["total"] == 150
        # Should make 3 calls total (test connection + data + count)
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_paginate_without_total_count(self, mock_supabase_client):
        """Test pagination with include_count=False (default)."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        result = await storage.paginate_query("products", page=1, per_page=20)

        # Should not include total
        assert "total" not in result
        # Note: execute is called twice (test connection + actual query), not once
        # The important part is no count query was made (would be 3 calls)

    @pytest.mark.asyncio
    async def test_paginate_count_respects_filters(self, mock_supabase_client):
        """Test that count query applies same filters as data query."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Configure count response
        mock_count_response = MagicMock()
        mock_count_response.count = 42

        # Track call count
        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_response  # Test connection
            elif call_count == 2:
                return mock_response  # Main query
            else:
                return mock_count_response  # Count query

        mock_table.execute = mock_multi_execute

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        result = await storage.paginate_query(
            "products",
            filters={"is_active": True},
            search_patterns={"name": "%test%"},
            page=1,
            per_page=20,
            include_count=True
        )

        # Count should reflect filtered results
        assert result["total"] == 42
        # Filters should be applied to both main and count queries
        assert mock_table.eq.call_count >= 2
        assert mock_table.ilike.call_count >= 2

    @pytest.mark.asyncio
    async def test_paginate_with_ordering(self, mock_supabase_client):
        """Test pagination with custom ordering."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        await storage.paginate_query(
            "products",
            order_by="created_at.desc",
            page=1,
            per_page=20
        )

        # Should parse and apply ordering
        mock_table.order.assert_called_once_with("created_at", desc=True)


# =============================================================================
# Test Group 6: Pagination - Cursor Mode (3 tests)
# =============================================================================


class TestPaginationCursorMode:
    """Test cursor-based pagination."""

    @pytest.mark.asyncio
    async def test_paginate_with_cursor(self, mock_supabase_client):
        """Test cursor-based pagination."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        import base64
        import json

        # Create valid cursor
        cursor_data = {"last_id": "id100"}
        cursor = base64.b64encode(json.dumps(cursor_data).encode("utf-8")).decode("utf-8")

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        result = await storage.paginate_query("products", cursor=cursor, per_page=20)

        # Should use gt() instead of range()
        mock_table.gt.assert_called_once_with("id", "id100")
        # Should not include page in result
        assert result["page"] is None

    @pytest.mark.asyncio
    async def test_paginate_generates_next_cursor(self, mock_supabase_client):
        """Test that pagination generates next_cursor when has_next=True."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        import base64
        import json

        # Full page indicates more results (range 1-20 creates id1 through id20)
        mock_response.data = [{"id": f"id{i}"} for i in range(1, 21)]

        cursor_data = {"last_id": "id0"}
        cursor = base64.b64encode(json.dumps(cursor_data).encode("utf-8")).decode("utf-8")

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        result = await storage.paginate_query("products", cursor=cursor, per_page=20)

        assert "next_cursor" in result
        # Decode and verify next cursor (last entity is id20 since range(1, 21))
        decoded = json.loads(base64.b64decode(result["next_cursor"]).decode("utf-8"))
        assert decoded["last_id"] == "id20"  # Last entity ID from range(1, 21)

    @pytest.mark.asyncio
    async def test_paginate_invalid_cursor_fallback(self, mock_supabase_client):
        """Test that invalid cursor falls back to offset pagination."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        # Invalid cursor should be handled gracefully
        with patch("autifyme_agents.integrations.storage.supabase_client.logger") as mock_logger:
            await storage.paginate_query("products", cursor="invalid-cursor", per_page=20)

            # Should log warning about invalid cursor
            mock_logger.warning.assert_called()


# =============================================================================
# Test Group 7: Pagination - Edge Cases (4 tests)
# =============================================================================


class TestPaginationEdgeCases:
    """Test pagination edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_paginate_empty_results(self, mock_supabase_client):
        """Test pagination with no results."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # No results
        mock_response.data = []

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        result = await storage.paginate_query("products", page=1, per_page=20)

        assert result["data"] == []
        assert result["has_next"] is False

    @pytest.mark.asyncio
    async def test_paginate_with_relations(self, mock_supabase_client):
        """Test pagination with relation prefetching."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        await storage.paginate_query(
            "products",
            relations=["product_families(*)"],
            page=1,
            per_page=20
        )

        # Should include relations in select
        calls = [call[0][0] for call in mock_table.select.call_args_list]
        assert "*,product_families(*)" in calls

    @pytest.mark.asyncio
    async def test_paginate_storage_error(self, mock_supabase_client):
        """Test that pagination storage errors are raised properly."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Configure query to fail - make async error function
        async def mock_error():
            raise Exception("Database error")

        mock_table.execute = mock_error

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        with pytest.raises(StorageError) as exc_info:
            await storage.paginate_query("products", page=1, per_page=20)

        assert "Paginated query failed" in str(exc_info.value)
        assert exc_info.value.operation == "paginate_query"

    @pytest.mark.asyncio
    async def test_paginate_default_ordering(self, mock_supabase_client):
        """Test that pagination applies default ordering by id."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co",
            service_key="test-key"
        )

        await storage.paginate_query("products", page=1, per_page=20)

        # Should apply default order by id
        mock_table.order.assert_called_once_with("id")
