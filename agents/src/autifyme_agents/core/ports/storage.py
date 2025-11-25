"""StorageInterface - Main port interface composing all mixins.

This module defines the abstract interface (the "Port") for all storage operations.
Any concrete storage implementation (like Supabase, DynamoDB, etc.) must inherit
from StorageInterface and implement all its abstract methods.

The interface is split into focused mixins for organization:
- CRUDMixin: Query and write operations
- ValidationMixin: Dry-run and constraint checking
- AnalyticsMixin: Workflow outcomes and schema intelligence
- WebhookMixin: Idempotency for duplicate message detection
- LifecycleMixin: Transaction and cleanup operations
"""

from ._analytics_mixin import AnalyticsMixin
from ._crud_mixin import CRUDMixin
from ._lifecycle_mixin import LifecycleMixin
from ._validation_mixin import ValidationMixin
from ._webhook_mixin import WebhookMixin


class StorageInterface(
    CRUDMixin,
    ValidationMixin,
    AnalyticsMixin,
    WebhookMixin,
    LifecycleMixin,
):
    """
    Abstract interface (the "Port") for all storage operations.

    Composed of focused mixins:
    - CRUDMixin: query_entities, insert_entity, update_entities, etc.
    - ValidationMixin: validate_entity_data, check_constraint_violations
    - AnalyticsMixin: get_company_profile, workflow_outcome tracking, schema stats
    - WebhookMixin: check_and_mark_message_processed
    - LifecycleMixin: transaction, cleanup

    Implementations:
    - SupabaseStorageClient (integrations/storage/supabase_client.py)
    """

    pass
