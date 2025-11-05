"""
Database Models Package

Note: This project uses Motor (pure MongoDB) with repository pattern.
Models here are Pydantic schemas, not Beanie Documents.
Use repositories in src.infrastructure.database.mongodb for database operations.
"""
from .test_execution_model import TestExecution, APITestResult

__all__ = [
    'TestExecution',
    'APITestResult',
]


