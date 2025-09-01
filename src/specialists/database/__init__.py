"""
Database Specialist Module

Centralized database operations following architecture decisions.
All database interactions should go through the DatabaseSpecialist.
"""

from .database_specialist import (
    DatabaseSpecialist,
    DatabaseError,
    get_database_specialist,
    log_audit,
    log_cost
)

__all__ = [
    "DatabaseSpecialist",
    "DatabaseError", 
    "get_database_specialist",
    "log_audit",
    "log_cost"
]