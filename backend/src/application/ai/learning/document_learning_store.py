"""
Document Learning Store - Learn from test failures and successes
Store corrections and improvements for each documentation ID
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ....infrastructure.database.mongodb.connection import MongoDBConnection

logger = logging.getLogger(__name__)


class DocumentLearningStore:
    """
    Store and retrieve learned corrections for API documentation
    
    After 20-30 test runs, the system should KNOW:
    - Correct parameter names for each endpoint
    - Required vs optional fields
    - Valid value examples
    - Common error patterns and fixes
    """
    
    def __init__(self):
        self.db = MongoDBConnection.get_database()
        self.collection = self.db['document_learnings']
    
    async def store_parameter_correction(
        self,
        doc_id: str,
        endpoint_path: str,
        method: str,
        wrong_parameter: str,
        correct_parameter: str,
        error_message: str,
        source: str = "test_failure"
    ):
        """
        Store a parameter correction learned from a test failure
        
        Args:
            doc_id: Documentation ID
            endpoint_path: API endpoint path
            method: HTTP method
            wrong_parameter: The parameter name that was wrong
            correct_parameter: The correct parameter name
            error_message: The error message that revealed the issue
            source: How we learned this (test_failure, manual_correction, etc.)
        """
        try:
            learning_key = f"{doc_id}:{method}:{endpoint_path}:{correct_parameter}"
            
            learning = {
                "doc_id": doc_id,
                "endpoint_path": endpoint_path,
                "method": method,
                "learning_type": "parameter_correction",
                "wrong_parameter": wrong_parameter,
                "correct_parameter": correct_parameter,
                "error_message": error_message,
                "source": source,
                "learned_at": datetime.utcnow(),
                "confidence": 1.0,
                "usage_count": 0,
                "success_count": 0
            }
            
            # Upsert - if exists, increment confidence
            await self.collection.update_one(
                {"learning_key": learning_key},
                {
                    "$set": learning,
                    "$inc": {"confidence": 0.1}
                },
                upsert=True
            )
            
            logger.info(f"[DOC] Learned: {endpoint_path} requires '{correct_parameter}' not '{wrong_parameter}'")
            
        except Exception as e:
            logger.error(f"Failed to store parameter correction: {e}")
    
    async def get_learned_parameters(
        self,
        doc_id: str,
        endpoint_path: str,
        method: str
    ) -> List[Dict[str, Any]]:
        """
        Get learned parameter corrections for an endpoint
        
        Returns:
            List of learned corrections with confidence scores
        """
        try:
            cursor = self.collection.find({
                "doc_id": doc_id,
                "endpoint_path": endpoint_path,
                "method": method,
                "learning_type": "parameter_correction"
            }).sort("confidence", -1)
            
            learnings = await cursor.to_list(length=100)
            
            if learnings:
                logger.info(f"[INFO] Found {len(learnings)} learned corrections for {method} {endpoint_path}")
            
            return learnings
            
        except Exception as e:
            logger.error(f"Failed to get learned parameters: {e}")
            return []
    
    async def store_successful_payload(
        self,
        doc_id: str,
        endpoint_path: str,
        method: str,
        payload: Dict[str, Any],
        response_status: int
    ):
        """
        Store a payload that resulted in a successful API call
        
        Args:
            doc_id: Documentation ID
            endpoint_path: API endpoint path
            method: HTTP method
            payload: The payload that worked
            response_status: Response status code (200, 201, etc.)
        """
        try:
            learning_key = f"{doc_id}:{method}:{endpoint_path}:successful_payload"
            
            # Prepare base learning document (without fields that will be updated separately)
            learning_base = {
                "learning_key": learning_key,
                "doc_id": doc_id,
                "endpoint_path": endpoint_path,
                "method": method,
                "learning_type": "successful_payload",
                "confidence": 1.0,
                "usage_count": 0
            }
            
            # Fields that change with each success
            learning_updates = {
                "payload": payload,
                "response_status": response_status,
                "learned_at": datetime.utcnow()
            }
            
            # Store as example - use $setOnInsert for initial values, $inc for counter
            await self.collection.update_one(
                {"learning_key": learning_key},
                {
                    "$setOnInsert": learning_base,  # Only set these on first insert
                    "$inc": {"success_count": 1},  # Increment counter
                    "$set": learning_updates  # Always update these
                },
                upsert=True
            )
            
            logger.info(f"[OK] Stored successful payload for {method} {endpoint_path}")
            
        except Exception as e:
            logger.error(f"Failed to store successful payload: {e}")
    
    async def get_successful_payloads(
        self,
        doc_id: str,
        endpoint_path: str,
        method: str
    ) -> List[Dict[str, Any]]:
        """
        Get previously successful payloads for an endpoint
        
        Returns:
            List of payloads that worked in the past
        """
        try:
            cursor = self.collection.find({
                "doc_id": doc_id,
                "endpoint_path": endpoint_path,
                "method": method,
                "learning_type": "successful_payload"
            }).sort("success_count", -1)
            
            learnings = await cursor.to_list(length=10)
            
            if learnings:
                logger.info(f"[OK] Found {len(learnings)} successful payloads for {method} {endpoint_path}")
            
            return learnings
            
        except Exception as e:
            logger.error(f"Failed to get successful payloads: {e}")
            return []
    
    async def learn_from_error(
        self,
        doc_id: str,
        endpoint_path: str,
        method: str,
        sent_payload: Dict[str, Any],
        error_response: Dict[str, Any]
    ):
        """
        Automatically learn from API error responses
        
        Analyzes error messages to extract:
        - Missing required fields
        - Wrong parameter names
        - Invalid value formats
        
        Args:
            doc_id: Documentation ID
            endpoint_path: API endpoint path
            method: HTTP method
            sent_payload: What we sent
            error_response: The error response we got
        """
        try:
            errors = error_response.get('errors', [])
            if isinstance(errors, str):
                errors = [errors]
            
            message = error_response.get('message', '')
            
            for error in errors:
                error_str = str(error).lower()
                
                # Pattern 1: "field_name must be a string"
                # Pattern 2: "field_name should not be empty"
                # Pattern 3: "field_name is required"
                import re
                
                # Extract missing field names
                missing_field_patterns = [
                    r'(\w+)\s+must\s+be',
                    r'(\w+)\s+should\s+not\s+be\s+empty',
                    r'(\w+)\s+is\s+required',
                    r'missing\s+required\s+field[:\s]+(\w+)'
                ]
                
                for pattern in missing_field_patterns:
                    match = re.search(pattern, error_str)
                    if match:
                        correct_parameter = match.group(1)
                        
                        # Find what we sent instead (if anything)
                        wrong_parameter = self._find_similar_param_in_payload(
                            correct_parameter,
                            sent_payload
                        )
                        
                        await self.store_parameter_correction(
                            doc_id=doc_id,
                            endpoint_path=endpoint_path,
                            method=method,
                            wrong_parameter=wrong_parameter or "missing",
                            correct_parameter=correct_parameter,
                            error_message=error_str,
                            source="auto_learned_from_error"
                        )
                        
                        logger.info(f"[INFO] Auto-learned: {endpoint_path} requires '{correct_parameter}'")
            
        except Exception as e:
            logger.error(f"Failed to learn from error: {e}")
    
    def _find_similar_param_in_payload(
        self,
        correct_param: str,
        payload: Dict[str, Any]
    ) -> Optional[str]:
        """Find a parameter in the payload that might be a mismatch"""
        correct_lower = correct_param.lower()
        
        for key in payload.keys():
            key_lower = key.lower()
            
            # Exact match (different case)
            if key_lower == correct_lower:
                return key
            
            # Partial match (contains)
            if correct_lower in key_lower or key_lower in correct_lower:
                return key
        
        return None
    
    async def get_learning_stats(self, doc_id: str) -> Dict[str, Any]:
        """Get statistics about what we've learned for a document"""
        try:
            total_learnings = await self.collection.count_documents({"doc_id": doc_id})
            
            parameter_corrections = await self.collection.count_documents({
                "doc_id": doc_id,
                "learning_type": "parameter_correction"
            })
            
            successful_payloads = await self.collection.count_documents({
                "doc_id": doc_id,
                "learning_type": "successful_payload"
            })
            
            return {
                "doc_id": doc_id,
                "total_learnings": total_learnings,
                "parameter_corrections": parameter_corrections,
                "successful_payloads": successful_payloads
            }
            
        except Exception as e:
            logger.error(f"Failed to get learning stats: {e}")
            return {}


