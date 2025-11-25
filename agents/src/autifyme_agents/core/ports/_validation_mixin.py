"""Validation mixin for dry-run and constraint checking."""

from abc import ABC, abstractmethod
from typing import Any, Literal


class ValidationMixin(ABC):
    """Dry-run validation and constraint checking operations."""

    @abstractmethod
    async def validate_entity_data(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        operation: Literal["insert", "update", "upsert", "delete"],
    ) -> dict[str, Any]:
        """
        Validate entity data against schema without executing operation.

        Performs comprehensive validation checks:
        - Schema conformance (field types, required fields)
        - Data type validation
        - Field length constraints
        - Enum value validation

        Args:
            table: Table name
            data: Entity data (single dict or list of dicts)
            operation: Operation type being validated

        Returns:
            Validation result dict:
            {
                "valid": bool,
                "errors": [{"field": str, "error": str, "severity": "error"}],
                "warnings": [{"field": str, "warning": str, "severity": "warning"}],
                "entity_count": int,
            }
        """
        pass

    @abstractmethod
    async def check_constraint_violations(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        operation: Literal["insert", "update", "upsert"],
        exclude_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Check for constraint violations before write operation.

        Validates against database constraints:
        - Uniqueness constraints (duplicate detection)
        - Foreign key constraints (referential integrity)
        - Check constraints (value ranges, patterns)

        Args:
            table: Table name
            data: Entity data (single dict or list of dicts)
            operation: Operation type
            exclude_ids: IDs to exclude from uniqueness check (for updates)

        Returns:
            Constraint check result:
            {
                "safe_to_proceed": bool,
                "violations": [
                    {
                        "type": "uniqueness"|"foreign_key",
                        "field": str,
                        "value": Any,
                        "message": str,
                        "conflicting_id": str|None
                    }
                ],
                "warnings": [{"type": str, "message": str}],
                "checked_constraints": [str]
            }
        """
        pass

    @abstractmethod
    async def preview_write_impact(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        operation: Literal["update", "delete"] = "update",
        sample_size: int = 5,
    ) -> dict[str, Any]:
        """
        Preview impact of update/delete operation before execution.

        Calculates operation impact without executing:
        - Number of entities affected
        - Sample of entities that would change
        - Estimated execution time
        - Potential risks and warnings

        Args:
            table: Table name
            filters: Filter conditions
            operation: Operation type ("update" or "delete")
            sample_size: Number of sample entities to return

        Returns:
            Impact preview:
            {
                "affected_count": int,
                "sample_entities": [dict],
                "estimated_duration_ms": int,
                "warnings": [{"type": str, "message": str}],
                "safe_to_proceed": bool,
            }
        """
        pass
