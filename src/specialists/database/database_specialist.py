"""
Database Specialist - Domain expertise for database operations

Following architecture decisions: Specialists provide domain expertise using generic tools.
This specialist knows HOW to use database tools for specific business operations.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from src.core.config import get_config
from src.core.models.base import APIResponse
from src.core.models.audit import AuditEntry, CostEntry, PerformanceMetric
from src.core.models.workflow import WorkflowState, ApprovalRequest
from src.core.models.cataloging import ProductDraft, CatalogEntry, DuplicateCheckResult
from src.core.credentials import DatabaseService
from src.tools.database import (
    create_record, read_record, update_record, delete_record,
    list_records, upsert_record, execute_rpc, count_records, search_records
)

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


class DatabaseSpecialist:
    """
    Database domain specialist using generic database tools
    
    Provides intelligent database operations by combining generic CRUD tools
    with domain knowledge about data relationships and business logic.
    """
    
    def __init__(self, database: DatabaseService, ai_model: str = "gpt-3.5-turbo"):
        self.database = database
        self.llm = ChatOpenAI(
            model=ai_model,
            temperature=0.1
        )
        
        # Create the specialist prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Database Specialist with expertise in data operations.
            
            You have access to generic database tools (CRUD operations) and you know how to:
            1. Design efficient queries for business needs
            2. Handle data relationships and constraints
            3. Ensure data consistency and integrity
            4. Optimize database operations for performance
            5. Handle multi-tenancy (always filter by business_id)
            6. Maintain audit trails for all operations
            
            Always:
            - Filter by business_id for multi-tenancy
            - Log important operations for audit trails
            - Handle errors gracefully with meaningful messages
            - Use appropriate indexes and query patterns
            - Validate data before operations
            
            Available tools: create_record, read_record, update_record, delete_record, 
            list_records, upsert_record, execute_rpc, count_records, search_records
            """),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Database tools available to the specialist (with database service pre-injected)
        self.tools = [
            self._create_langchain_tool("create_record", lambda table, data: create_record(self.database, table, data)),
            self._create_langchain_tool("read_record", lambda table, record_id, id_column="id": read_record(self.database, table, record_id, id_column)),
            self._create_langchain_tool("update_record", lambda table, record_id, data, id_column="id": update_record(self.database, table, record_id, data, id_column)),
            self._create_langchain_tool("delete_record", lambda table, record_id, id_column="id": delete_record(self.database, table, record_id, id_column)),
            self._create_langchain_tool("list_records", lambda table, filters=None, limit=None, offset=None, order_by=None: list_records(self.database, table, filters, limit, offset, order_by)),
            self._create_langchain_tool("upsert_record", lambda table, data, conflict_columns: upsert_record(self.database, table, data, conflict_columns)),
            self._create_langchain_tool("execute_rpc", lambda function_name, params: execute_rpc(self.database, function_name, params)),
            self._create_langchain_tool("count_records", lambda table, filters=None: count_records(self.database, table, filters)),
            self._create_langchain_tool("search_records", lambda table, search_column, search_term, limit=None: search_records(self.database, table, search_column, search_term, limit))
        ]
        
        # Create the agent
        self.agent = create_openai_functions_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)
    
    def _create_langchain_tool(self, name: str, func: callable):
        """Convert async function to LangChain tool"""
        from langchain.tools import Tool
        
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(func(*args, **kwargs))
        
        return Tool(
            name=name,
            description=f"Database tool: {name}",
            func=sync_wrapper
        )
    
    
    async def execute_query(self, query: str) -> Dict[str, Any]:
        """
        Execute a database operation using natural language
        
        Args:
            query: Natural language description of the database operation
            
        Returns:
            Result of the database operation
        """
        try:
            result = await self.agent_executor.ainvoke({"input": query})
            return {
                "success": True,
                "data": result.get("output"),
                "message": "Database operation completed successfully"
            }
        except Exception as e:
            logger.error(f"Database specialist query failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Database specialist operation failed"
            }
    
    # High-level business operations using the tools
    async def save_workflow_state(self, workflow_state: WorkflowState) -> Dict[str, Any]:
        """Save workflow state using database tools"""
        query = f"""
        Save workflow state to database:
        - Table: workflow_states
        - Data: {workflow_state.dict()}
        - Use upsert with conflict on workflow_id
        """
        return await self.execute_query(query)
    
    async def get_workflow_by_id(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow by ID using database tools"""
        query = f"""
        Get workflow from database:
        - Table: workflow_states
        - Find record with workflow_id = {workflow_id}
        """
        return await self.execute_query(query)
    
    async def save_product_draft(self, product_draft: ProductDraft) -> Dict[str, Any]:
        """Save product draft using database tools"""
        query = f"""
        Save product draft to database:
        - Table: product_drafts
        - Data: {product_draft.dict()}
        - Create new record
        """
        return await self.execute_query(query)
    
    async def check_duplicate_products(self, business_id: str, product_name: str) -> Dict[str, Any]:
        """Check for duplicate products using database tools"""
        query = f"""
        Check for duplicate products:
        - Table: catalog_entries
        - Search for similar product names in business_id = {business_id}
        - Product name to check: {product_name}
        - Use text search with similarity
        """
        return await self.execute_query(query)