"""
Database Tools Module

Generic database tools for CRUD operations and data management.
These are deterministic functions used by database specialists.
All functions take service credentials as first parameter.
"""

from .crud_tools import (
    create_record,
    read_record,
    update_record,
    delete_record,
    list_records,
    upsert_record,
    execute_rpc,
    count_records,
    search_records
)

__all__ = [
    "create_record",
    "read_record", 
    "update_record",
    "delete_record",
    "list_records",
    "upsert_record",
    "execute_rpc",
    "count_records",
    "search_records"
]