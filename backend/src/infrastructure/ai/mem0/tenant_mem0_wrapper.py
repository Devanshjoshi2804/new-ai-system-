"""
Tenant-aware Mem0 wrapper
Provides isolated AI memory for each tenant
"""
import logging
from typing import List, Dict, Any, Optional
from mem0 import MemoryClient

from src.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class TenantMem0Wrapper:
    """
    Manages AI memory with tenant isolation using Mem0
    
    Each tenant gets their own isolated memory namespace
    """
    
    def __init__(self):
        settings = get_settings()
        
        # Initialize Mem0 client
        # Note: Mem0 requires an API key - configure in settings
        self.client = MemoryClient(
            api_key=settings.mem0_api_key if hasattr(settings, 'mem0_api_key') else None
        )
        
        self._namespace_prefix = "tenant"
    
    def _get_namespace(self, tenant_id: str) -> str:
        """Get memory namespace for tenant"""
        return f"{self._namespace_prefix}:{tenant_id}"
    
    async def add(
        self,
        messages: List[Dict[str, str]],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add memory (async version for Knowledge Graph compatibility)
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: User identifier
            metadata: Additional metadata
            
        Returns:
            Result dict with memory ID
        """
        try:
            logger.info(f"Adding memory for user: {user_id}")
            
            if metadata is None:
                metadata = {}
            
            # Add to Mem0
            result = self.client.add(
                messages=messages,
                user_id=user_id,
                metadata=metadata
            )
            
            logger.info(f"Memory added: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return {"id": ""}
    
    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories (async version for Knowledge Graph compatibility)
        
        Args:
            query: Search query
            user_id: User identifier
            limit: Maximum results
            
        Returns:
            List of relevant memories
        """
        try:
            logger.info(f"Searching memory for user: {user_id}, query: {query}")
            
            # Search Mem0
            results = self.client.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
            
            logger.info(f"Found {len(results)} memories")
            return results
        
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []
    
    async def get_all(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories (async version for Knowledge Graph compatibility)
        
        Args:
            user_id: User identifier
            
        Returns:
            List of all memories
        """
        try:
            logger.info(f"Getting all memories for user: {user_id}")
            
            # Get from Mem0
            results = self.client.get_all(user_id=user_id)
            
            logger.info(f"Retrieved {len(results)} memories")
            return results
        
        except Exception as e:
            logger.error(f"Error getting memories: {e}")
            return []
    
    async def add_memory(
        self,
        tenant_id: str,
        messages: List[str],
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add memory for a tenant (legacy method)
        
        Args:
            tenant_id: Tenant identifier
            messages: Conversation messages to remember
            user_id: Optional user identifier within tenant
            metadata: Additional metadata
            
        Returns:
            Memory ID
        """
        try:
            logger.info(f"Adding memory for tenant: {tenant_id}")
            
            # Build user identifier with namespace
            user_identifier = f"{self._get_namespace(tenant_id)}"
            if user_id:
                user_identifier += f":{user_id}"
            
            # Add metadata
            if metadata is None:
                metadata = {}
            metadata["tenant_id"] = tenant_id
            
            # Convert string messages to dict format
            message_dicts = [{"role": "user", "content": msg} for msg in messages]
            
            # Add to Mem0
            result = await self.add(
                messages=message_dicts,
                user_id=user_identifier,
                metadata=metadata
            )
            
            return result.get("id", "")
        
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return ""
    
    async def search_memory(
        self,
        tenant_id: str,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories for a tenant (legacy method)
        
        Args:
            tenant_id: Tenant identifier
            query: Search query
            user_id: Optional user identifier
            limit: Maximum results
            
        Returns:
            List of relevant memories
        """
        try:
            # Build user identifier
            user_identifier = f"{self._get_namespace(tenant_id)}"
            if user_id:
                user_identifier += f":{user_id}"
            
            # Search
            return await self.search(
                query=query,
                user_id=user_identifier,
                limit=limit
            )
        
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []
    
    async def get_all_memories(
        self,
        tenant_id: str,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all memories for a tenant (legacy method)
        
        Args:
            tenant_id: Tenant identifier
            user_id: Optional user identifier
            
        Returns:
            List of all memories
        """
        try:
            # Build user identifier
            user_identifier = f"{self._get_namespace(tenant_id)}"
            if user_id:
                user_identifier += f":{user_id}"
            
            # Get all
            return await self.get_all(user_id=user_identifier)
        
        except Exception as e:
            logger.error(f"Error getting memories: {e}")
            return []
    
    async def delete_memory(
        self,
        tenant_id: str,
        memory_id: str
    ) -> bool:
        """
        Delete a specific memory
        
        Args:
            tenant_id: Tenant identifier
            memory_id: Memory ID to delete
            
        Returns:
            Success status
        """
        try:
            logger.info(f"Deleting memory: {memory_id} for tenant: {tenant_id}")
            
            # Delete from Mem0
            self.client.delete(memory_id=memory_id)
            
            logger.info("Memory deleted successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return False
    
    async def delete_all_memories(
        self,
        tenant_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Delete all memories for a tenant
        
        Args:
            tenant_id: Tenant identifier
            user_id: Optional user identifier
            
        Returns:
            Success status
        """
        try:
            logger.info(f"Deleting all memories for tenant: {tenant_id}")
            
            # Build user identifier
            user_identifier = f"{self._get_namespace(tenant_id)}"
            if user_id:
                user_identifier += f":{user_id}"
            
            # Delete from Mem0
            self.client.delete_all(user_id=user_identifier)
            
            logger.info("All memories deleted successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting memories: {e}")
            return False


class PartnerKnowledgeBase:
    """
    Partner-specific knowledge base
    Stores learned information about each partner's API
    """
    
    def __init__(self, memory_manager: TenantMem0Wrapper):
        self.memory = memory_manager
    
    async def store_api_knowledge(
        self,
        partner_id: str,
        endpoint_path: str,
        knowledge: Dict[str, Any]
    ):
        """
        Store knowledge about an API endpoint
        
        Args:
            partner_id: Partner identifier
            endpoint_path: API endpoint path
            knowledge: Knowledge to store (successful calls, error patterns, etc.)
        """
        try:
            # Format as message
            message = f"API Endpoint {endpoint_path}: {knowledge}"
            
            # Store in memory
            await self.memory.add_memory(
                tenant_id=partner_id,
                messages=[message],
                user_id="api_knowledge",
                metadata={
                    "type": "api_knowledge",
                    "endpoint": endpoint_path,
                    **knowledge
                }
            )
        
        except Exception as e:
            logger.error(f"Error storing API knowledge: {e}")
    
    async def get_api_knowledge(
        self,
        partner_id: str,
        endpoint_path: str
    ) -> List[Dict[str, Any]]:
        """
        Get stored knowledge about an API endpoint
        
        Args:
            partner_id: Partner identifier
            endpoint_path: API endpoint path
            
        Returns:
            List of relevant knowledge
        """
        try:
            # Search memory
            results = await self.memory.search_memory(
                tenant_id=partner_id,
                query=f"API endpoint {endpoint_path}",
                user_id="api_knowledge",
                limit=5
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Error getting API knowledge: {e}")
            return []


# Global instances
_memory_manager: Optional[TenantMem0Wrapper] = None
_knowledge_base: Optional[PartnerKnowledgeBase] = None


def get_memory_manager() -> TenantMem0Wrapper:
    """Get global memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = TenantMem0Wrapper()
    return _memory_manager


def get_knowledge_base() -> PartnerKnowledgeBase:
    """Get global knowledge base instance"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = PartnerKnowledgeBase(get_memory_manager())
    return _knowledge_base

