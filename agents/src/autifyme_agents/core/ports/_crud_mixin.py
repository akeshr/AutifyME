"""CRUD operations mixin for query and write operations."""

from abc import ABC, abstractmethod
from typing import Any, Literal, overload


class CRUDMixin(ABC):
    """Core CRUD operations: query, insert, update, delete, upsert, patch."""

    # ========================================================================
    # Query Operations
    # ========================================================================

    @abstractmethod
    async def query_entities(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query entities with optional filters, relations, and search.

        Args:
            table: Table name
            filters: WHERE conditions as dict (e.g., {"is_active": True})
            columns: Columns to select (default: all columns)
            relations: Related tables to include (e.g., ["categories(*)", "variant_axes(*)"])
            search_patterns: Case-insensitive LIKE patterns. Supports:
                - Single pattern (AND): {"name": "%bottle%"}
                - Multiple patterns (OR): {"name": ["%bottle%", "%jar%"]}
            limit: Maximum rows to return

        Returns:
            List of matching rows as dicts (always a list, never int)
        """
        pass

    @abstractmethod
    async def count_entities(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
    ) -> int:
        """
        Count entities matching filters.

        Args:
            table: Table name
            filters: WHERE conditions as dict
            search_patterns: Case-insensitive LIKE patterns

        Returns:
            Count of matching rows (always an int, never a list)
        """
        pass

    @abstractmethod
    async def check_existing_values(
        self,
        table: str,
        column: str,
        values: list[Any],
        exclude_ids: list[Any] | None = None,
    ) -> list[Any]:
        """
        Batch check which values exist in a column.

        Eliminates N+1 queries for uniqueness validation.

        Args:
            table: Table name
            column: Column to check
            values: List of values to check for existence
            exclude_ids: Optional list of record IDs to exclude from check

        Returns:
            List of values that already exist in the table
        """
        pass

    @overload
    async def query_advanced(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
        count_only: Literal[True] = ...,
        limit: int | None = None,
    ) -> int: ...

    @overload
    async def query_advanced(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
        count_only: Literal[False] = ...,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def query_advanced(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
        count_only: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]] | int:
        """
        Advanced query with relations, pattern matching, and counting.

        Args:
            table: Table name
            filters: Exact match filters
            columns: Columns to select (default: all)
            relations: Related tables to include (PostgREST syntax)
            search_patterns: Case-insensitive LIKE patterns
            count_only: If True, return count instead of rows
            limit: Maximum rows to return

        Returns:
            List of matching rows (as dicts) if count_only=False, else int count
        """
        pass

    @abstractmethod
    async def query_aggregate(
        self,
        table: str,
        aggregates: dict[str, str],
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
        group_by: list[str] | None = None,
        having: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query with aggregations (count, sum, avg, min, max) and GROUP BY.

        Args:
            table: Table name
            aggregates: Aggregation operations as {alias: "function(column)"}
            filters: Exact match filters applied before aggregation
            search_patterns: ILIKE patterns applied before aggregation
            group_by: Columns to group by
            having: Filters on aggregated results

        Returns:
            List of aggregated results with group_by columns and aggregate aliases
        """
        pass

    @abstractmethod
    async def batch_read(
        self,
        table: str,
        ids: list[str],
        relations: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch multiple entities by ID in single query (batch operation).

        Args:
            table: Table name
            ids: List of entity IDs to fetch
            relations: Optional relations to prefetch

        Returns:
            List of entities matching the IDs, in the same order as input IDs.
        """
        pass

    @abstractmethod
    async def paginate_query(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
        relations: list[str] | None = None,
        order_by: str | None = None,
        page: int = 1,
        per_page: int = 20,
        cursor: str | None = None,
        include_count: bool = False,
    ) -> dict[str, Any]:
        """
        Paginate query results with offset or cursor-based pagination.

        Args:
            table: Table name
            filters: Exact match filters
            search_patterns: ILIKE patterns
            relations: Relations to include
            order_by: Sort specification (e.g., "created_at.desc")
            page: Page number (1-indexed, for offset pagination)
            per_page: Items per page (default 20, max 100)
            cursor: Cursor token for cursor-based pagination
            include_count: Whether to include total count

        Returns:
            Dict with pagination metadata and results
        """
        pass

    # ========================================================================
    # Write Operations
    # ========================================================================

    @abstractmethod
    async def insert_entity(
        self,
        table: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Insert single entity.

        Args:
            table: Table name
            data: Entity data to insert

        Returns:
            Inserted row with generated fields (id, created_at, etc.)
        """
        pass

    @abstractmethod
    async def insert_entities(
        self,
        table: str,
        data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Batch insert multiple entities in single query.

        Args:
            table: Table name
            data: List of entity data to insert

        Returns:
            List of inserted rows with generated fields
        """
        pass

    @abstractmethod
    async def update_entities(
        self,
        table: str,
        filters: dict[str, Any],
        updates: dict[str, Any],
    ) -> int:
        """
        Update entities matching filters.

        Args:
            table: Table name
            filters: WHERE conditions as dict
            updates: Fields to update

        Returns:
            Count of updated rows
        """
        pass

    @abstractmethod
    async def delete_entities(
        self,
        table: str,
        filters: dict[str, Any],
        soft_delete: bool = True,
    ) -> int:
        """
        Delete entities matching filters.

        Args:
            table: Table name
            filters: WHERE conditions as dict
            soft_delete: If True, sets is_active=False. If False, hard delete.

        Returns:
            Count of deleted/deactivated rows
        """
        pass

    # ========================================================================
    # Upsert & Patch Operations
    # ========================================================================

    @abstractmethod
    async def upsert_entity(
        self,
        table: str,
        data: dict[str, Any],
        conflict_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Insert or update entity (upsert) with conflict resolution.

        Args:
            table: Table name
            data: Entity data (must include fields for conflict detection)
            conflict_fields: Fields to check for conflicts (e.g., ["sku_code"])

        Returns:
            Final entity state after upsert
        """
        pass

    @abstractmethod
    async def bulk_upsert(
        self,
        table: str,
        data: list[dict[str, Any]],
        conflict_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Batch upsert multiple entities with conflict resolution.

        Args:
            table: Table name
            data: List of entity data
            conflict_fields: Fields to check for conflicts

        Returns:
            List of final entity states after upserts
        """
        pass

    @abstractmethod
    async def patch_entity(
        self,
        table: str,
        id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Partially update entity (PATCH semantics).

        Args:
            table: Table name
            id: Entity ID to update
            updates: Fields to update (omitted fields unchanged)

        Returns:
            Complete updated entity (all fields)
        """
        pass
