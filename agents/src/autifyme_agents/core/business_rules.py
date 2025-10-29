"""Business rule handlers for schema-driven operations.

Implements pluggable business logic validation and triggers that execute
during database operations. Handlers are registered by rule type and
invoked based on schema metadata.

Key Handlers:
- validate_sku_uniqueness: Prevent duplicate SKU codes
- validate_required_fields: Schema-driven field validation (redundant with SchemaValidator)
- calculate_cascade_impact: Accurate DELETE impact with relationship traversal
"""

import logging
from typing import Any, Callable

from langchain_core.tools import ToolException

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.registry import BusinessRule, BusinessRuleTrigger, SchemaRegistry

logger = logging.getLogger(__name__)


# =============================================================================
# Business Rule Handler Registry
# =============================================================================


class BusinessRuleHandlers:
    """
    Registry of business rule handlers.

    Handlers are functions that execute business logic during database operations.
    Each handler is registered by rule_type and invoked based on trigger timing.
    """

    def __init__(self, storage: StorageInterface, schema: SchemaRegistry):
        """
        Initialize handler registry with storage and schema access.

        Args:
            storage: Storage interface for database queries
            schema: Schema registry for metadata access
        """
        self.storage = storage
        self.schema = schema
        self._handlers: dict[str, Callable] = {}

        # Register core handlers
        self._register_core_handlers()

    def _register_core_handlers(self) -> None:
        """Register built-in business rule handlers."""
        self.register("validate_sku_uniqueness", self._validate_sku_uniqueness)
        self.register("validate_required_fields", self._validate_required_fields)
        self.register("calculate_cascade_impact", self._calculate_cascade_impact)

    def register(self, rule_type: str, handler: Callable) -> None:
        """
        Register a business rule handler.

        Args:
            rule_type: Unique identifier for the rule
            handler: Callable that executes the rule logic
        """
        self._handlers[rule_type] = handler
        logger.debug(f"Registered business rule handler: {rule_type}")

    def execute_rule(
        self,
        rule: BusinessRule,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a business rule with given context.

        Args:
            rule: BusinessRule metadata from schema
            context: Execution context (operation, entities, etc.)

        Returns:
            Result dict with validation status and data

        Raises:
            ToolException: If validation fails
        """
        if not rule.enabled:
            logger.debug(f"Skipping disabled rule: {rule.rule_type}")
            return {"status": "skipped", "rule": rule.rule_type}

        handler = self._handlers.get(rule.handler)
        if not handler:
            logger.warning(
                f"Business rule handler not found: {rule.handler} for rule {rule.rule_type}"
            )
            return {"status": "handler_not_found", "rule": rule.rule_type}

        try:
            logger.info(
                f"Executing business rule: {rule.rule_type}",
                extra={"trigger": rule.trigger, "handler": rule.handler}
            )

            result = handler(rule, context)

            logger.info(
                f"Business rule completed: {rule.rule_type}",
                extra={"status": result.get("status")}
            )

            return result

        except Exception as e:
            logger.error(
                f"Business rule execution failed: {rule.rule_type}",
                exc_info=True,
                extra={"error": str(e)}
            )
            raise ToolException(
                f"Business rule '{rule.rule_type}' failed: {str(e)}"
            ) from e

    def execute_rules_for_trigger(
        self,
        table_name: str,
        trigger: BusinessRuleTrigger,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Execute all business rules for a specific trigger point.

        Args:
            table_name: Target table name
            trigger: When to execute (before_insert, after_update, etc.)
            context: Execution context

        Returns:
            List of rule execution results
        """
        table_schema = self.schema.get_table(table_name)
        results = []

        for rule in table_schema.business_rules:
            if rule.trigger == trigger:
                result = self.execute_rule(rule, context)
                results.append(result)

        return results

    # =========================================================================
    # Core Business Rule Handlers
    # =========================================================================

    def _validate_sku_uniqueness(
        self, rule: BusinessRule, context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validate that SKU codes are unique across products table.

        Prevents duplicate SKUs which would cause catalog corruption.

        Args:
            rule: BusinessRule metadata
            context: {"operation": Operation, "entities": [...]}

        Returns:
            {"status": "valid"} or raises ToolException

        Raises:
            ToolException: If duplicate SKU detected
        """
        operation = context.get("operation")
        if not operation or operation.op_type != "insert":
            return {"status": "skipped", "reason": "not_insert_operation"}

        entities = context.get("entities", [])
        if not entities:
            return {"status": "valid", "reason": "no_entities"}

        # Extract SKU codes from entities
        sku_codes = []
        for entity in entities:
            sku = entity.get("sku_code")
            if sku:
                sku_codes.append(sku)

        if not sku_codes:
            return {"status": "valid", "reason": "no_sku_codes"}

        # Query database for existing SKUs
        try:
            client = self.storage._ensure_client()
            existing_products = []

            for sku in sku_codes:
                result = client.table("products").select("sku_code").eq("sku_code", sku).execute()
                if result.data and len(result.data) > 0:
                    existing_products.append(sku)

            if existing_products:
                raise ToolException(
                    f"Duplicate SKU codes detected: {existing_products}. "
                    f"SKU codes must be unique across all products."
                )

            return {
                "status": "valid",
                "validated_skus": sku_codes,
                "checked_count": len(sku_codes),
            }

        except ToolException:
            raise
        except Exception as e:
            logger.error("SKU uniqueness check failed", exc_info=True)
            # Don't fail operation if check fails (graceful degradation)
            return {"status": "check_failed", "error": str(e)}

    def _validate_required_fields(
        self, rule: BusinessRule, context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validate required fields against schema.

        Note: This is redundant with SchemaValidator but provides
        additional context-aware validation.

        Args:
            rule: BusinessRule metadata
            context: {"table": str, "entities": [...]}

        Returns:
            {"status": "valid"} or raises ToolException

        Raises:
            ToolException: If required fields missing
        """
        table_name = context.get("table")
        entities = context.get("entities", [])

        if not table_name or not entities:
            return {"status": "skipped", "reason": "missing_context"}

        table_schema = self.schema.get_table(table_name)
        required_columns = table_schema.get_required_columns()

        validation_errors = []
        for i, entity in enumerate(entities):
            missing = [col for col in required_columns if col not in entity]
            if missing:
                validation_errors.append(f"Entity {i}: missing required fields {missing}")

        if validation_errors:
            raise ToolException(
                f"Required field validation failed for {table_name}: {validation_errors}"
            )

        return {
            "status": "valid",
            "validated_entities": len(entities),
            "required_columns": required_columns,
        }

    def _calculate_cascade_impact(
        self, rule: BusinessRule, context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Calculate cascade impact for DELETE operations.

        Traverses foreign key relationships to count affected records
        across related tables.

        Args:
            rule: BusinessRule metadata
            context: {"operation": Operation, "table": str, "filter": {...}}

        Returns:
            {"status": "calculated", "impact": {...}}

        Raises:
            ToolException: If impact calculation fails
        """
        operation = context.get("operation")
        if not operation or operation.op_type != "delete":
            return {"status": "skipped", "reason": "not_delete_operation"}

        table_name = context.get("table")
        delete_filter = context.get("filter", {})

        if not table_name:
            return {"status": "skipped", "reason": "missing_table"}

        try:
            table_schema = self.schema.get_table(table_name)

            # Find child relationships (tables that reference this table)
            impact = {table_name: 0}

            # Query records to be deleted
            client = self.storage._ensure_client()
            query = client.table(table_name).select("*")

            for key, value in delete_filter.items():
                query = query.eq(key, value)

            result = query.execute()
            records_to_delete = result.data if result.data else []
            impact[table_name] = len(records_to_delete)

            # Check cascade relationships
            for other_table_name, other_table in self.schema.tables.items():
                if other_table_name == table_name:
                    continue

                # Find relationships where other table references this table
                for rel in other_table.relationships:
                    if rel.target_table == table_name and rel.cascade_delete:
                        # Count affected records in child table
                        child_count = 0
                        for record in records_to_delete:
                            record_id = record.get("id")
                            if record_id:
                                child_query = client.table(other_table_name).select("id").eq(
                                    rel.foreign_key, record_id
                                )
                                child_result = child_query.execute()
                                if child_result.data:
                                    child_count += len(child_result.data)

                        if child_count > 0:
                            impact[other_table_name] = child_count

            return {
                "status": "calculated",
                "impact": impact,
                "total_affected": sum(impact.values()),
                "is_destructive": sum(impact.values()) > 0,
            }

        except Exception as e:
            logger.error("Cascade impact calculation failed", exc_info=True)
            # Return partial result rather than failing
            return {
                "status": "calculation_failed",
                "error": str(e),
                "impact": {table_name: "unknown"},
            }
