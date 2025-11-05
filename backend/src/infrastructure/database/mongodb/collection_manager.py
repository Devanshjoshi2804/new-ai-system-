"""
Dynamic collection manager for per-tenant data isolation
"""
import logging
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

logger = logging.getLogger(__name__)


class CollectionManager:
    """Manages dynamic creation and access of tenant-specific collections"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self._created_collections: set = set()
    
    def get_tenant_collection_name(self, tenant_id: str, collection_name: str) -> str:
        """
        Generate tenant-specific collection name
        Format: tenant_{tenant_id}_{collection_name}
        """
        return f"tenant_{tenant_id}_{collection_name}"
    
    async def get_tenant_collection(
        self,
        tenant_id: str,
        collection_name: str,
        create_if_not_exists: bool = True
    ) -> AsyncIOMotorCollection:
        """
        Get tenant-specific collection, creating if needed
        """
        tenant_collection_name = self.get_tenant_collection_name(tenant_id, collection_name)
        
        # Check if collection exists
        existing_collections = await self.database.list_collection_names()
        
        if tenant_collection_name not in existing_collections and create_if_not_exists:
            await self.create_tenant_collection(tenant_id, collection_name)
        
        return self.database[tenant_collection_name]
    
    async def create_tenant_collection(
        self,
        tenant_id: str,
        collection_name: str,
        indexes: Optional[List[tuple]] = None
    ) -> AsyncIOMotorCollection:
        """
        Create a new tenant-specific collection with indexes
        """
        tenant_collection_name = self.get_tenant_collection_name(tenant_id, collection_name)
        
        # Create collection
        collection = self.database[tenant_collection_name]
        
        # Create default indexes
        default_indexes = [
            ("tenant_id", 1),
            ("created_at", -1),
        ]
        
        # Add custom indexes
        if indexes:
            default_indexes.extend(indexes)
        
        # Create indexes
        for index_spec in default_indexes:
            if isinstance(index_spec, tuple):
                await collection.create_index([index_spec])
            else:
                await collection.create_index(index_spec)
        
        self._created_collections.add(tenant_collection_name)
        logger.info(f"Created tenant collection: {tenant_collection_name}")
        
        return collection
    
    async def delete_tenant_collections(self, tenant_id: str) -> int:
        """
        Delete all collections for a specific tenant
        WARNING: This is destructive!
        """
        collection_names = await self.database.list_collection_names()
        prefix = f"tenant_{tenant_id}_"
        
        deleted_count = 0
        for col_name in collection_names:
            if col_name.startswith(prefix):
                await self.database.drop_collection(col_name)
                deleted_count += 1
                logger.warning(f"Deleted tenant collection: {col_name}")
        
        return deleted_count
    
    async def list_tenant_collections(self, tenant_id: str) -> List[str]:
        """
        List all collections for a specific tenant
        """
        collection_names = await self.database.list_collection_names()
        prefix = f"tenant_{tenant_id}_"
        
        return [name for name in collection_names if name.startswith(prefix)]
    
    async def collection_exists(self, tenant_id: str, collection_name: str) -> bool:
        """
        Check if tenant collection exists
        """
        tenant_collection_name = self.get_tenant_collection_name(tenant_id, collection_name)
        existing_collections = await self.database.list_collection_names()
        return tenant_collection_name in existing_collections
    
    async def init_tenant_workspace(self, tenant_id: str):
        """
        Initialize all required collections for a new tenant
        """
        required_collections = [
            ("bookings", [("booking_id", 1), ("status", 1)]),
            ("shipments", [("awb_number", 1), ("status", 1)]),
            ("conversations", [("user_id", 1), ("session_id", 1)]),
            ("ai_memory", [("user_id", 1), ("memory_type", 1)]),
            ("api_cache", [("cache_key", 1), ("expires_at", 1)]),
            ("webhooks", [("event_type", 1), ("processed", 1)]),
            ("analytics", [("event_type", 1), ("timestamp", -1)]),
        ]
        
        for collection_name, indexes in required_collections:
            await self.create_tenant_collection(tenant_id, collection_name, indexes)
        
        logger.info(f"Initialized workspace for tenant: {tenant_id}")


# Global instance
_collection_manager: Optional[CollectionManager] = None


def init_collection_manager(database: AsyncIOMotorDatabase):
    """Initialize global collection manager"""
    global _collection_manager
    _collection_manager = CollectionManager(database)


def get_collection_manager() -> CollectionManager:
    """Get global collection manager"""
    if _collection_manager is None:
        raise RuntimeError("Collection manager not initialized")
    return _collection_manager


