"""
Database CRUD Tools - Execution Layer

Generic, deterministic database operations that can be used by any specialist.
These are pure functions that take service credentials as parameters.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging

from src.core.credentials import DatabaseService

logger = logging.getLogger(__name__)


async def create_record(database: DatabaseService, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new record in specified table
    
    Args:
        database: Database service instance
        table: Table name
        data: Record data
        
    Returns:
        Created record or error info
    """
    try:
        client = database.create_client()
        result = client.table(table).insert(data).execute()
        
        if result.data:
            return {
                "success": True,
                "data": result.data[0],
                "message": f"Record created in {table}"
            }
        else:
            return {
                "success": False,
                "error": "No data returned from insert",
                "message": f"Failed to create record in {table}"
            }
            
    except Exception as e:
        logger.error(f"Failed to create record in {table}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Database error creating record in {table}"
        }


async def read_record(database: DatabaseService, table: str, record_id: str, id_column: str = "id") -> Dict[str, Any]:
    """
    Read a single record by ID
    
    Args:
        database: Database service instance
        table: Table name
        record_id: Record identifier
        id_column: ID column name (default: "id")
        
    Returns:
        Record data or error info
    """
    try:
        client = database.create_client()
        result = client.table(table).select("*").eq(id_column, record_id).execute()
        
        if result.data:
            return {
                "success": True,
                "data": result.data[0],
                "message": f"Record found in {table}"
            }
        else:
            return {
                "success": False,
                "error": "Record not found",
                "message": f"No record found in {table} with {id_column}={record_id}"
            }
            
    except Exception as e:
        logger.error(f"Failed to read record from {table}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Database error reading record from {table}"
        }


async def update_record(database: DatabaseService, table: str, record_id: str, data: Dict[str, Any], 
                       id_column: str = "id") -> Dict[str, Any]:
    """
    Update a record by ID
    
    Args:
        database: Database service instance
        table: Table name
        record_id: Record identifier
        data: Updated data
        id_column: ID column name (default: "id")
        
    Returns:
        Updated record or error info
    """
    try:
        client = database.create_client()
        result = client.table(table).update(data).eq(id_column, record_id).execute()
        
        if result.data:
            return {
                "success": True,
                "data": result.data[0],
                "message": f"Record updated in {table}"
            }
        else:
            return {
                "success": False,
                "error": "No record updated",
                "message": f"No record found to update in {table} with {id_column}={record_id}"
            }
            
    except Exception as e:
        logger.error(f"Failed to update record in {table}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Database error updating record in {table}"
        }


async def delete_record(database: DatabaseService, table: str, record_id: str, id_column: str = "id") -> Dict[str, Any]:
    """
    Delete a record by ID
    
    Args:
        database: Database service instance
        table: Table name
        record_id: Record identifier
        id_column: ID column name (default: "id")
        
    Returns:
        Success status or error info
    """
    try:
        client = database.create_client()
        result = client.table(table).delete().eq(id_column, record_id).execute()
        
        return {
            "success": True,
            "data": result.data,
            "message": f"Record deleted from {table}"
        }
            
    except Exception as e:
        logger.error(f"Failed to delete record from {table}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Database error deleting record from {table}"
        }


async def list_records(database: DatabaseService, table: str, filters: Optional[Dict[str, Any]] = None,
                      limit: Optional[int] = None, offset: Optional[int] = None,
                      order_by: Optional[str] = None) -> Dict[str, Any]:
    """
    List records with optional filtering and pagination
    
    Args:
        database: Database service instance
        table: Table name
        filters: Optional filters (column: value pairs)
        limit: Maximum number of records
        offset: Number of records to skip
        order_by: Column to order by
        
    Returns:
        List of records or error info
    """
    try:
        client = database.create_client()
        query = client.table(table).select("*")
        
        # Apply filters
        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)
        
        # Apply ordering
        if order_by:
            query = query.order(order_by)
        
        # Apply pagination
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        result = query.execute()
        
        return {
            "success": True,
            "data": result.data,
            "count": len(result.data),
            "message": f"Retrieved records from {table}"
        }
            
    except Exception as e:
        logger.error(f"Failed to list records from {table}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Database error listing records from {table}"
        }


async def upsert_record(database: DatabaseService, table: str, data: Dict[str, Any], 
                       conflict_columns: List[str]) -> Dict[str, Any]:
    """
    Insert or update record based on conflict columns
    
    Args:
        database: Database service instance
        table: Table name
        data: Record data
        conflict_columns: Columns to check for conflicts
        
    Returns:
        Upserted record or error info
    """
    try:
        client = database.create_client()
        result = client.table(table).upsert(
            data, 
            on_conflict=",".join(conflict_columns)
        ).execute()
        
        if result.data:
            return {
                "success": True,
                "data": result.data[0],
                "message": f"Record upserted in {table}"
            }
        else:
            return {
                "success": False,
                "error": "No data returned from upsert",
                "message": f"Failed to upsert record in {table}"
            }
            
    except Exception as e:
        logger.error(f"Failed to upsert record in {table}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Database error upserting record in {table}"
        }


async def execute_rpc(database: DatabaseService, function_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a stored procedure/function
    
    Args:
        database: Database service instance
        function_name: Name of the database function
        params: Function parameters
        
    Returns:
        Function result or error info
    """
    try:
        client = database.create_client()
        result = client.rpc(function_name, params).execute()
        
        return {
            "success": True,
            "data": result.data,
            "message": f"Executed function {function_name}"
        }
            
    except Exception as e:
        logger.error(f"Failed to execute RPC {function_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Database error executing function {function_name}"
        }


async def count_records(database: DatabaseService, table: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Count records in table with optional filters
    
    Args:
        database: Database service instance
        table: Table name
        filters: Optional filters (column: value pairs)
        
    Returns:
        Record count or error info
    """
    try:
        client = database.create_client()
        query = client.table(table).select("*", count="exact")
        
        # Apply filters
        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)
        
        result = query.execute()
        
        return {
            "success": True,
            "count": result.count,
            "message": f"Counted records in {table}"
        }
            
    except Exception as e:
        logger.error(f"Failed to count records in {table}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Database error counting records in {table}"
        }


async def search_records(database: DatabaseService, table: str, search_column: str, search_term: str,
                        limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Search records using text search
    
    Args:
        database: Database service instance
        table: Table name
        search_column: Column to search in
        search_term: Search term
        limit: Maximum number of results
        
    Returns:
        Search results or error info
    """
    try:
        client = database.create_client()
        query = client.table(table).select("*").ilike(search_column, f"%{search_term}%")
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        
        return {
            "success": True,
            "data": result.data,
            "count": len(result.data),
            "message": f"Search completed in {table}"
        }
            
    except Exception as e:
        logger.error(f"Failed to search records in {table}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Database error searching records in {table}"
        }