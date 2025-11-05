"""
Tenant-aware MongoDB client that automatically injects tenant context
"""
import logging
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorCollection
from contextvars import ContextVar

from src.domain.value_objects.tenant_id import TenantContext
from src.infrastructure.database.mongodb.collection_manager import get_collection_manager

logger = logging.getLogger(__name__)

# Context variable to store tenant context per request
tenant_context_var: ContextVar[Optional[TenantContext]] = ContextVar('tenant_context', default=None)


class TenantAwareClient:
    """
    MongoDB client wrapper that ensures tenant isolation
    """
    
    @staticmethod
    def set_context(context: TenantContext):
        """Set tenant context for current request"""
        tenant_context_var.set(context)
    
    @staticmethod
    def get_context() -> Optional[TenantContext]:
        """Get current tenant context"""
        return tenant_context_var.get()
    
    @staticmethod
    def clear_context():
        """Clear tenant context"""
        tenant_context_var.set(None)
    
    @staticmethod
    def require_context() -> TenantContext:
        """Get tenant context or raise error"""
        context = tenant_context_var.get()
        if context is None:
            raise RuntimeError("No tenant context set. Use TenantMiddleware.")
        return context
    
    @staticmethod
    async def get_collection(collection_name: str) -> AsyncIOMotorCollection:
        """
        Get tenant-specific collection based on current context
        """
        context = TenantAwareClient.require_context()
        collection_manager = get_collection_manager()
        
        return await collection_manager.get_tenant_collection(
            context.tenant_id,
            collection_name
        )
    
    @staticmethod
    def inject_tenant_filter(query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject tenant_id into query filter
        """
        context = TenantAwareClient.require_context()
        return {**query, "tenant_id": context.tenant_id}
    
    @staticmethod
    def inject_tenant_document(document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject tenant_id into document
        """
        context = TenantAwareClient.require_context()
        return {**document, "tenant_id": context.tenant_id}
    
    @staticmethod
    async def find_one(
        collection_name: str,
        query: Dict[str, Any],
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Find single document with automatic tenant filtering
        """
        collection = await TenantAwareClient.get_collection(collection_name)
        query = TenantAwareClient.inject_tenant_filter(query)
        return await collection.find_one(query, **kwargs)
    
    @staticmethod
    async def find_many(
        collection_name: str,
        query: Dict[str, Any],
        limit: int = 100,
        skip: int = 0,
        sort: Optional[List[tuple]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Find multiple documents with automatic tenant filtering
        """
        collection = await TenantAwareClient.get_collection(collection_name)
        query = TenantAwareClient.inject_tenant_filter(query)
        
        cursor = collection.find(query, **kwargs)
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def insert_one(
        collection_name: str,
        document: Dict[str, Any]
    ) -> str:
        """
        Insert document with automatic tenant_id injection
        """
        collection = await TenantAwareClient.get_collection(collection_name)
        document = TenantAwareClient.inject_tenant_document(document)
        
        result = await collection.insert_one(document)
        return str(result.inserted_id)
    
    @staticmethod
    async def insert_many(
        collection_name: str,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Insert multiple documents with automatic tenant_id injection
        """
        collection = await TenantAwareClient.get_collection(collection_name)
        documents = [TenantAwareClient.inject_tenant_document(doc) for doc in documents]
        
        result = await collection.insert_many(documents)
        return [str(id) for id in result.inserted_ids]
    
    @staticmethod
    async def update_one(
        collection_name: str,
        query: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False
    ) -> bool:
        """
        Update single document with automatic tenant filtering
        """
        collection = await TenantAwareClient.get_collection(collection_name)
        query = TenantAwareClient.inject_tenant_filter(query)
        
        result = await collection.update_one(query, update, upsert=upsert)
        return result.modified_count > 0
    
    @staticmethod
    async def update_many(
        collection_name: str,
        query: Dict[str, Any],
        update: Dict[str, Any]
    ) -> int:
        """
        Update multiple documents with automatic tenant filtering
        """
        collection = await TenantAwareClient.get_collection(collection_name)
        query = TenantAwareClient.inject_tenant_filter(query)
        
        result = await collection.update_many(query, update)
        return result.modified_count
    
    @staticmethod
    async def delete_one(
        collection_name: str,
        query: Dict[str, Any]
    ) -> bool:
        """
        Delete single document with automatic tenant filtering
        """
        collection = await TenantAwareClient.get_collection(collection_name)
        query = TenantAwareClient.inject_tenant_filter(query)
        
        result = await collection.delete_one(query)
        return result.deleted_count > 0
    
    @staticmethod
    async def delete_many(
        collection_name: str,
        query: Dict[str, Any]
    ) -> int:
        """
        Delete multiple documents with automatic tenant filtering
        """
        collection = await TenantAwareClient.get_collection(collection_name)
        query = TenantAwareClient.inject_tenant_filter(query)
        
        result = await collection.delete_many(query)
        return result.deleted_count
    
    @staticmethod
    async def count_documents(
        collection_name: str,
        query: Dict[str, Any]
    ) -> int:
        """
        Count documents with automatic tenant filtering
        """
        collection = await TenantAwareClient.get_collection(collection_name)
        query = TenantAwareClient.inject_tenant_filter(query)
        
        return await collection.count_documents(query)


