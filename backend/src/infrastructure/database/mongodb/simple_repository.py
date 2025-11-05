"""
Simple MongoDB Repository without Beanie
Direct Motor usage for maximum compatibility
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from src.infrastructure.database.mongodb.connection import MongoDBConnection

logger = logging.getLogger(__name__)


class SimpleMongoRepository:
    """Simple MongoDB repository using Motor directly"""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
    
    @property
    def collection(self):
        """Get collection from database"""
        db = MongoDBConnection.get_database()
        return db[self.collection_name]
    
    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document (BUG #9 FIX: Remove _id confusion)"""
        try:
            doc = await self.collection.find_one(query)
            if doc and '_id' in doc:
                del doc['_id']  # Remove to avoid ID confusion
            return doc
        except Exception as e:
            logger.error(f"Error finding document in {self.collection_name}: {e}")
            return None
    
    async def find_many(self, query: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Find multiple documents (BUG #9 FIX: Remove _id confusion)"""
        try:
            cursor = self.collection.find(query).limit(limit)
            docs = await cursor.to_list(length=limit)
            for doc in docs:
                if '_id' in doc:
                    del doc['_id']  # Remove to avoid ID confusion
            return docs
        except Exception as e:
            logger.error(f"Error finding documents in {self.collection_name}: {e}")
            return []
    
    async def insert_one(self, document: Dict[str, Any]) -> Optional[str]:
        """Insert a single document (BUG #9 FIX: Use UUID for 'id' field)"""
        try:
            # BUG #9 FIXED: Always add 'id' field (UUID) as primary identifier
            if 'id' not in document:
                import uuid
                document['id'] = str(uuid.uuid4())
            
            # Add timestamps
            document['createdAt'] = datetime.utcnow()
            document['updatedAt'] = datetime.utcnow()
            
            result = await self.collection.insert_one(document)
            logger.info(f"Inserted document with id={document['id']}")
            return document['id']  # Return UUID, not ObjectId
            
        except Exception as e:
            logger.error(f"Error inserting document in {self.collection_name}: {e}")
            return None
    
    async def insert_many(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Insert multiple documents"""
        try:
            # Add timestamps to all documents
            now = datetime.utcnow()
            for doc in documents:
                doc['createdAt'] = now
                doc['updatedAt'] = now
            
            result = await self.collection.insert_many(documents)
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            logger.error(f"Error inserting documents in {self.collection_name}: {e}")
            return []
    
    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """Update a single document"""
        try:
            # Add updated timestamp
            if '$set' not in update:
                update = {'$set': update}
            update['$set']['updatedAt'] = datetime.utcnow()
            
            result = await self.collection.update_one(query, update)
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating document in {self.collection_name}: {e}")
            return False
    
    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """Update multiple documents"""
        try:
            # Add updated timestamp
            if '$set' not in update:
                update = {'$set': update}
            update['$set']['updatedAt'] = datetime.utcnow()
            
            result = await self.collection.update_many(query, update)
            return result.modified_count
        except Exception as e:
            logger.error(f"Error updating documents in {self.collection_name}: {e}")
            return 0
    
    async def delete_one(self, query: Dict[str, Any]) -> bool:
        """Delete a single document"""
        try:
            result = await self.collection.delete_one(query)
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting document in {self.collection_name}: {e}")
            return False
    
    async def delete_many(self, query: Dict[str, Any]) -> int:
        """Delete multiple documents"""
        try:
            result = await self.collection.delete_many(query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting documents in {self.collection_name}: {e}")
            return 0
    
    async def count(self, query: Dict[str, Any] = None) -> int:
        """Count documents matching query"""
        try:
            if query is None:
                query = {}
            return await self.collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error counting documents in {self.collection_name}: {e}")
            return 0
    
    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run aggregation pipeline"""
        try:
            cursor = self.collection.aggregate(pipeline)
            docs = await cursor.to_list(length=None)
            for doc in docs:
                if '_id' in doc and isinstance(doc['_id'], ObjectId):
                    doc['_id'] = str(doc['_id'])
            return docs
        except Exception as e:
            logger.error(f"Error running aggregation in {self.collection_name}: {e}")
            return []


# Pre-configured repositories for common collections
class ClientsRepository(SimpleMongoRepository):
    """Repository for clients collection"""
    def __init__(self):
        super().__init__('clients')


class DocketsRepository(SimpleMongoRepository):
    """Repository for dockets collection"""
    def __init__(self):
        super().__init__('dockets')


class VehiclesRepository(SimpleMongoRepository):
    """Repository for vehicles collection"""
    def __init__(self):
        super().__init__('vehicles')


class InvoicesRepository(SimpleMongoRepository):
    """Repository for invoices collection"""
    def __init__(self):
        super().__init__('invoices')


class TripsRepository(SimpleMongoRepository):
    """Repository for trips collection"""
    def __init__(self):
        super().__init__('trips')


class SuppliersRepository(SimpleMongoRepository):
    """Repository for suppliers collection"""
    def __init__(self):
        super().__init__('suppliers')


class UsersRepository(SimpleMongoRepository):
    """Repository for users collection"""
    def __init__(self):
        super().__init__('users')


