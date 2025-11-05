"""
MongoDB Test Execution Repository
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from .connection import MongoDBConnection

logger = logging.getLogger(__name__)


class MongoDBTestExecutionRepository:
    """Repository for test execution records"""
    
    def __init__(self):
        """Initialize repository"""
        self.db: AsyncIOMotorDatabase = MongoDBConnection.get_database()
        self.collection = self.db['test_executions']
    
    async def create(self, test_execution_data: Dict[str, Any]) -> str:
        """
        Create a new test execution record
        
        Args:
            test_execution_data: Test execution data
            
        Returns:
            Created test execution ID
        """
        try:
            # Ensure required fields
            if 'id' not in test_execution_data:
                import uuid
                test_execution_data['id'] = str(uuid.uuid4())
            
            if 'created_at' not in test_execution_data:
                test_execution_data['created_at'] = datetime.utcnow()
            
            if 'updated_at' not in test_execution_data:
                test_execution_data['updated_at'] = datetime.utcnow()
            
            result = await self.collection.insert_one(test_execution_data)
            logger.info(f"Created test execution: {test_execution_data['id']}")
            
            return test_execution_data['id']
            
        except Exception as e:
            logger.error(f"Failed to create test execution: {e}")
            raise
    
    async def get_by_id(self, test_execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get test execution by ID (BUG #9 FIX: Only use 'id' field)
        
        Args:
            test_execution_id: Test execution ID (UUID string)
            
        Returns:
            Test execution data or None
        """
        try:
            # BUG #9 FIXED: Only query by 'id' field (UUID), not _id (ObjectId)
            test_execution = await self.collection.find_one({"id": test_execution_id})
            
            if test_execution and '_id' in test_execution:
                del test_execution['_id']
            
            return test_execution
            
        except Exception as e:
            logger.error(f"Failed to get test execution {test_execution_id}: {e}")
            return None
    
    async def update(self, test_execution_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update test execution (BUG #11 FIX: Atomic updates prevent race conditions)
        
        Args:
            test_execution_id: Test execution ID (UUID string)
            update_data: Data to update
            
        Returns:
            True if updated successfully
        """
        try:
            # BUG #11 FIXED: Use find_one_and_update for atomic operation
            update_data['updated_at'] = datetime.utcnow()
            
            result = await self.collection.find_one_and_update(
                {"id": test_execution_id},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                logger.debug(f"Updated test execution: {test_execution_id}")
                return True
            else:
                logger.warning(f"Test execution not found: {test_execution_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update test execution {test_execution_id}: {e}")
            return False
    
    async def list_by_partner(
        self,
        partner_id: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List test executions for a partner
        
        Args:
            partner_id: Partner ID
            limit: Maximum number of results
            skip: Number of results to skip
            
        Returns:
            List of test executions
        """
        try:
            cursor = self.collection.find(
                {"partner_id": partner_id}
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            test_executions = await cursor.to_list(length=limit)
            return test_executions
            
        except Exception as e:
            logger.error(f"Failed to list test executions for partner {partner_id}: {e}")
            return []
    
    async def delete(self, test_execution_id: str) -> bool:
        """
        Delete test execution
        
        Args:
            test_execution_id: Test execution ID
            
        Returns:
            True if deleted successfully
        """
        try:
            # Try to delete by id field first
            result = await self.collection.delete_one({"id": test_execution_id})
            
            if result.deleted_count == 0:
                # Try by _id (ObjectId) as fallback
                from bson import ObjectId
                try:
                    result = await self.collection.delete_one({"_id": ObjectId(test_execution_id)})
                except:
                    pass
            
            if result.deleted_count > 0:
                logger.info(f"Deleted test execution: {test_execution_id}")
                return True
            else:
                logger.warning(f"Test execution not found: {test_execution_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete test execution {test_execution_id}: {e}")
            return False


