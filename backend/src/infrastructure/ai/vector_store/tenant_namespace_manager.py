"""
Tenant-aware Pinecone vector store manager
Provides isolated vector storage for each tenant
"""
import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
import hashlib

from src.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

class TenantNamespaceManager:
    """
    Manages vector embeddings with tenant isolation using Pinecone
    
    Each tenant gets their own namespace in Pinecone
    """
    
    def __init__(self):
        settings = get_settings()
        
        # Initialize Pinecone
        self.pc = Pinecone(
            api_key=settings.pinecone_api_key if hasattr(settings, 'pinecone_api_key') else ""
        )
        
        self.index_name = "ai-logistics-platform"
        self.dimension = 1536  # OpenAI ada-002 embedding dimension
        
        # Create index if it doesn't exist
        self._ensure_index_exists()
        
        # Get index
        self.index = self.pc.Index(self.index_name)
        
        logger.info(f"Pinecone initialized with index: {self.index_name}")
    
    def _ensure_index_exists(self):
        """Create index if it doesn't exist"""
        try:
            existing_indexes = [idx['name'] for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {self.index_name}")
                
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
                
                logger.info("Index created successfully")
        
        except Exception as e:
            logger.error(f"Error ensuring index exists: {e}")
    
    def _get_namespace(self, tenant_id: str) -> str:
        """Get Pinecone namespace for tenant"""
        # Pinecone namespaces must be alphanumeric
        return f"tenant_{tenant_id.replace('-', '_')}"
    
    async def upsert_vectors(
        self,
        tenant_id: str,
        vectors: List[Dict[str, Any]]
    ):
        """
        Upsert vectors for a tenant
        
        Args:
            tenant_id: Tenant identifier
            vectors: List of vectors with format:
                [{"id": "vec1", "values": [...], "metadata": {...}}]
        """
        try:
            namespace = self._get_namespace(tenant_id)
            
            logger.info(f"Upserting {len(vectors)} vectors for tenant: {tenant_id}")
            
            # Upsert to Pinecone in tenant's namespace
            self.index.upsert(
                vectors=vectors,
                namespace=namespace
            )
            
            logger.info("Vectors upserted successfully")
        
        except Exception as e:
            logger.error(f"Error upserting vectors: {e}")
            raise
    
    async def query_vectors(
        self,
        tenant_id: str,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query vectors for a tenant
        
        Args:
            tenant_id: Tenant identifier
            query_vector: Query embedding
            top_k: Number of results
            filter: Metadata filter
            include_metadata: Include metadata in results
            
        Returns:
            List of matching vectors with scores
        """
        try:
            namespace = self._get_namespace(tenant_id)
            
            logger.info(f"Querying vectors for tenant: {tenant_id}")
            
            # Query Pinecone
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=filter,
                include_metadata=include_metadata
            )
            
            matches = results.get('matches', [])
            logger.info(f"Found {len(matches)} matches")
            
            return matches
        
        except Exception as e:
            logger.error(f"Error querying vectors: {e}")
            return []
    
    async def delete_vectors(
        self,
        tenant_id: str,
        ids: List[str]
    ):
        """
        Delete specific vectors for a tenant
        
        Args:
            tenant_id: Tenant identifier
            ids: Vector IDs to delete
        """
        try:
            namespace = self._get_namespace(tenant_id)
            
            logger.info(f"Deleting {len(ids)} vectors for tenant: {tenant_id}")
            
            # Delete from Pinecone
            self.index.delete(
                ids=ids,
                namespace=namespace
            )
            
            logger.info("Vectors deleted successfully")
        
        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")
    
    async def delete_all_vectors(
        self,
        tenant_id: str
    ):
        """
        Delete all vectors for a tenant
        
        Args:
            tenant_id: Tenant identifier
        """
        try:
            namespace = self._get_namespace(tenant_id)
            
            logger.info(f"Deleting all vectors for tenant: {tenant_id}")
            
            # Delete entire namespace
            self.index.delete(
                delete_all=True,
                namespace=namespace
            )
            
            logger.info("All vectors deleted successfully")
        
        except Exception as e:
            logger.error(f"Error deleting all vectors: {e}")
    
    async def store_api_documentation(
        self,
        tenant_id: str,
        partner_id: str,
        documentation_chunks: List[Dict[str, str]],
        embeddings: List[List[float]]
    ):
        """
        Store API documentation embeddings
        
        Args:
            tenant_id: Tenant identifier
            partner_id: Partner identifier
            documentation_chunks: List of doc chunks with {"id", "text"}
            embeddings: Corresponding embeddings
        """
        try:
            logger.info(f"Storing {len(documentation_chunks)} doc chunks for partner: {partner_id}")
            
            # Prepare vectors
            vectors = []
            for chunk, embedding in zip(documentation_chunks, embeddings):
                vector_id = self._generate_vector_id(partner_id, chunk["id"])
                
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "partner_id": partner_id,
                        "text": chunk["text"],
                        "chunk_id": chunk["id"],
                        "type": "documentation"
                    }
                })
            
            # Upsert vectors
            await self.upsert_vectors(tenant_id, vectors)
            
            logger.info("Documentation stored successfully")
        
        except Exception as e:
            logger.error(f"Error storing documentation: {e}")
            raise
    
    async def search_documentation(
        self,
        tenant_id: str,
        partner_id: str,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search API documentation
        
        Args:
            tenant_id: Tenant identifier
            partner_id: Partner identifier
            query_embedding: Query embedding
            top_k: Number of results
            
        Returns:
            List of relevant documentation chunks
        """
        try:
            logger.info(f"Searching documentation for partner: {partner_id}")
            
            # Query with partner filter
            results = await self.query_vectors(
                tenant_id=tenant_id,
                query_vector=query_embedding,
                top_k=top_k,
                filter={
                    "partner_id": partner_id,
                    "type": "documentation"
                }
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Error searching documentation: {e}")
            return []


# Global instance
_vector_store: Optional[TenantNamespaceManager] = None


def get_vector_store() -> TenantNamespaceManager:
    """Get global vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = TenantNamespaceManager()
    return _vector_store


