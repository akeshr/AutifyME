"""
Write Intent schemas for Universal Data Engine.

Streamlined multi-operation write intent as specified in
UNIVERSAL_DATA_ENGINE_DESIGN.md (lines 722-745).

Key improvements over legacy OperationIntent:
- Simpler structure (no ChangeSpecification wrapper)
- Named dependencies (instead of numeric indices)
- Unified @name.field reference syntax
- Auto-generated execution plan (no manual specification)
- Flat operations list (easier to construct)
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AssetUpload(BaseModel):
    """
    File upload specification for WriteIntent.

    Processed BEFORE database operations. The uploaded file's public URL
    can be referenced in operations using @name.public_url syntax.

    Use storage_path from image_studio output. The HITL handler auto-derives
    the full public URL for WhatsApp preview.

    Example:
        asset_uploads=[
            AssetUpload(
                storage_path="pending/whatsapp_123_919/20251130_edit_abc123.png",
                returns="product_image",
                caption="PET Jar 500ml Clear - product photo",
                target_folder="products"
            )
        ]

    Operations reference:
        operations=[
            Operation(
                action="create",
                table="assets",
                data={
                    "file_url": "@product_image.public_url",
                    "file_type": "image/png",
                    "file_size": "@product_image.size_bytes"
                },
                returns="asset"
            )
        ]
    """

    model_config = {"extra": "forbid"}

    # Primary: Supabase storage path (from image_studio/download_media)
    storage_path: str | None = Field(
        default=None,
        description=(
            "Path within Supabase bucket (from image_studio/download_media outputs).\n"
            "Example: 'pending/whatsapp_123_919/20251130_edit_abc123.png'\n"
            "Executor MOVES file from pending/ to target_folder upon HITL approval.\n"
            "HITL handler auto-derives full public URL for WhatsApp preview."
        ),
    )

    # Fallback: Local file path (for external file uploads only)
    temp_path: str | None = Field(
        default=None,
        description=(
            "Local file path for external uploads not already in Supabase.\n"
            "Use storage_path for image_studio/download_media outputs instead."
        ),
    )

    returns: str = Field(
        ...,
        description=(
            "Name to assign to upload result.\n"
            "Operations can reference: @name.public_url, @name.storage_path, "
            "@name.size_bytes, @name.content_type, @name.caption"
        ),
    )

    caption: str = Field(
        default="",
        description=(
            "Human-readable caption for HITL image preview.\n"
            "Describe what this specific image shows.\n"
            "Example: 'PET Jar 500ml Clear - product photo'\n"
            "Keep under 200 chars. Sent with image in WhatsApp."
        ),
    )

    bucket: str = Field(
        default="assets",
        description="Storage bucket name (default: 'assets')",
    )

    # For temp_path: folder to upload into
    folder: str = Field(
        default="products",
        description="Folder within bucket for upload (default: 'products')",
    )

    # For storage_path: folder to move into
    target_folder: str = Field(
        default="products",
        description="Target folder for move operation (default: 'products')",
    )

    @field_validator("storage_path", "temp_path", mode="after")
    @classmethod
    def validate_path_provided(cls, v: str | None, info: Any) -> str | None:
        """Validate that at least one path is provided."""
        # This runs for each field, actual validation in model_validator
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate that exactly one of temp_path or storage_path is provided."""
        if self.temp_path is None and self.storage_path is None:
            raise ValueError("Either temp_path or storage_path must be provided")
        if self.temp_path is not None and self.storage_path is not None:
            raise ValueError("Cannot provide both temp_path and storage_path")


class Operation(BaseModel):
    """
    Single operation within a WriteIntent.

    Supports create, update, delete, upsert operations on a single table.
    """

    model_config = {"extra": "forbid"}

    action: Literal["create", "update", "delete", "upsert"] = Field(
        ...,
        description=(
            "Operation action:\n"
            "- create: Insert new record(s)\n"
            "- update: Update existing record(s)\n"
            "- delete: Delete record(s)\n"
            "- upsert: Insert or update (idempotent)"
        ),
    )

    table: str = Field(
        ...,
        description="Table name (e.g., 'products', 'product_families')",
    )

    data: dict[str, Any] | list[dict[str, Any]] | None = Field(
        None,
        description=(
            "Data to write. Single dict or list of dicts.\n"
            "Required for: create, upsert.\n"
            "Optional for: update (uses updates field instead).\n"
            "Can contain @name.field references to previous operations."
        ),
    )

    filters: dict[str, Any] | None = Field(
        None,
        description=(
            "Filter conditions for update/delete operations.\n"
            "Example: {'is_active': False}, {'status': 'draft'}.\n"
            "Required for: update, delete."
        ),
    )

    updates: dict[str, Any] | None = Field(
        None,
        description=(
            "Field updates for update operation.\n"
            "Example: {'status': 'published', 'updated_at': 'now()'}.\n"
            "Used with filters to update multiple records."
        ),
    )

    dependencies: list[str] = Field(
        default_factory=list,
        description=(
            "Named dependencies - operations that must complete before this one.\n"
            "References operation names from 'returns' field.\n"
            "Example: ['family', 'size_axis'] means this operation depends on "
            "operations that return 'family' and 'size_axis'.\n"
            "Engine automatically orders operations using topological sort."
        ),
    )

    returns: str | None = Field(
        None,
        description=(
            "Name to assign to result of this operation.\n"
            "Used by subsequent operations to reference this operation's result.\n"
            "Example: 'family' allows later operations to use '@family.id'"
        ),
    )

    on_conflict: Literal["error", "skip", "update"] = Field(
        default="error",
        description=(
            "Conflict resolution strategy for upsert/create:\n"
            "- error: Fail on duplicate (default)\n"
            "- skip: Skip duplicate, continue\n"
            "- update: Update existing record"
        ),
    )

    conflict_fields: list[str] | None = Field(
        None,
        description=(
            "Fields to check for conflicts in upsert operation.\n"
            "Example: ['sku_code'], ['tenant_id', 'slug'].\n"
            "Required for upsert when on_conflict != 'error'."
        ),
    )

    cascade: bool = Field(
        default=False,
        description=(
            "For delete operations: also delete dependent entities.\n"
            "Example: Deleting product_family also deletes products, variants."
        ),
    )

    soft_delete: bool = Field(
        default=True,
        description=(
            "For delete operations: mark as deleted instead of removing.\n"
            "Sets is_active=False, deleted_at=now() instead of DELETE."
        ),
    )


class WriteIntent(BaseModel):
    """
    Multi-operation write intent - streamlined structure.

    Replaces legacy OperationIntent with simpler, more powerful design:
    - Named dependencies (not numeric indices)
    - Auto-generated execution plan (not manual)
    - Unified @name.field reference syntax
    - Flat operations list (no ChangeSpecification nesting)
    - Asset uploads processed before database operations
    - LLM-generated hitl_summary for human approval
    """

    model_config = {"extra": "forbid"}

    goal: str = Field(
        ...,
        description=(
            "Human-readable goal of this write intent.\n"
            "Example: 'Create PET Bottles product family with Size and Color variants'"
        ),
    )

    reasoning: str = Field(
        ...,
        description=(
            "REQUIRED: Reasoning and context for this operation.\n"
            "Includes: classification rationale, duplicate check results, "
            "research findings, warnings, assumptions."
        ),
    )

    hitl_summary: str = Field(
        ...,
        description=(
            "REQUIRED: Human-readable approval summary for HITL (<1500 chars).\n"
            "Write for the BUSINESS USER who will approve/reject.\n\n"
            "MUST include:\n"
            "- What will be created/updated (plain language)\n"
            "- Key impacts (counts, SKUs, prices)\n"
            "- Any warnings or assumptions\n"
            "- End with: 'Reply *approve* to proceed or *reject* to cancel'\n\n"
            "Example:\n"
            "'Creating PET Jars family with 2 size variants.\n\n"
            "Products: JAR-PET-500ML (Rs 30), JAR-PET-1L (Rs 50)\n"
            "Images: 2 product photos attached\n\n"
            "This will add 1 product family and 2 new SKUs.\n\n"
            "Reply *approve* to proceed or *reject* to cancel.'"
        ),
    )

    asset_uploads: list[AssetUpload] = Field(
        default_factory=list,
        description=(
            "Files to upload BEFORE database operations.\n"
            "Each upload's result can be referenced in operations:\n"
            "- @name.public_url: Public URL of uploaded file\n"
            "- @name.storage_path: Path within storage bucket\n"
            "- @name.size_bytes: File size in bytes\n"
            "- @name.content_type: MIME type\n"
            "- @name.caption: Human-readable caption for alt text\n"
            "Uploads execute atomically: if any fails, no DB operations run."
        ),
    )

    operations: list[Operation] = Field(
        ...,
        description=(
            "List of operations to execute atomically.\n"
            "Engine automatically orders by dependencies (topological sort).\n"
            "All operations execute in single transaction with automatic rollback."
        ),
    )

    impact: dict[str, Any] = Field(
        ...,
        description=(
            "Simplified impact analysis.\n"
            "Format: {\n"
            "  'creates': {'table_name': count, ...},\n"
            "  'updates': {'table_name': count, ...},\n"
            "  'deletes': {'table_name': count, ...},\n"
            "  'asset_uploads': count,\n"
            "  'warnings': ['warning1', 'warning2'],\n"
            "  'examples': ['example SKU 1', 'example SKU 2']\n"
            "}"
        ),
    )

    @field_validator("operations")
    @classmethod
    def validate_operations_not_empty(cls, v: list[Operation]) -> list[Operation]:
        """Ensure operations list is not empty."""
        if not v:
            raise ValueError("operations list cannot be empty")
        return v

    @field_validator("impact")
    @classmethod
    def validate_impact_structure(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate impact has required keys."""
        if "creates" not in v and "updates" not in v and "deletes" not in v:
            raise ValueError(
                "impact must contain at least one of: creates, updates, deletes"
            )
        return v
