"""
Vector Store Cleanup Manager (BUG #15 FIX)
Prevents ChromaDB memory leaks by cleaning up old embeddings
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class VectorStoreCleanup:
    """
    Manages ChromaDB cleanup to prevent memory leaks
    BUG #15 FIX: Regular cleanup of old/unused embeddings
    """
    
    def __init__(self, vector_store, cleanup_interval_hours: int = 24):
        """
        Initialize cleanup manager
        
        Args:
            vector_store: Vector store instance
            cleanup_interval_hours: Hours between cleanup runs
        """
        self.vector_store = vector_store
        self.cleanup_interval = cleanup_interval_hours * 3600  # Convert to seconds
        self.last_cleanup = None
        self.total_cleaned = 0
        
        logger.info(f"VectorStoreCleanup initialized (interval={cleanup_interval_hours}h)")
    
    async def cleanup_old_embeddings(self, days_old: int = 7) -> int:
        """
        Clean up embeddings older than N days
        
        Args:
            days_old: Delete embeddings older than this many days
            
        Returns:
            Number of embeddings deleted
        """
        try:
            logger.info(f"🧹 Starting cleanup of embeddings older than {days_old} days...")
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            deleted_count = 0
            
            # Get all collections
            if hasattr(self.vector_store, 'client'):
                collections = self.vector_store.client.list_collections()
                
                for collection in collections:
                    # Get metadata for each document
                    results = collection.get(include=['metadatas'])
                    
                    # Find old documents
                    ids_to_delete = []
                    for i, metadata in enumerate(results.get('metadatas', [])):
                        created_at = metadata.get('created_at')
                        if created_at:
                            doc_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            if doc_date < cutoff_date:
                                ids_to_delete.append(results['ids'][i])
                    
                    # Delete old documents
                    if ids_to_delete:
                        collection.delete(ids=ids_to_delete)
                        deleted_count += len(ids_to_delete)
                        logger.info(f"🗑️  Deleted {len(ids_to_delete)} old embeddings from {collection.name}")
            
            self.total_cleaned += deleted_count
            self.last_cleanup = datetime.utcnow()
            
            logger.info(f"✅ Cleanup complete: {deleted_count} embeddings deleted")
            return deleted_count
        
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}", exc_info=True)
            return 0
    
    async def cleanup_by_doc_id(self, doc_id: str) -> bool:
        """
        Clean up all embeddings for a specific document
        
        Args:
            doc_id: Document ID to clean up
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"🧹 Cleaning up embeddings for doc_id={doc_id}")
            
            if hasattr(self.vector_store, 'client'):
                collections = self.vector_store.client.list_collections()
                deleted_total = 0
                
                for collection in collections:
                    # Find documents with this doc_id
                    results = collection.get(
                        where={"doc_id": doc_id},
                        include=['metadatas']
                    )
                    
                    if results['ids']:
                        collection.delete(ids=results['ids'])
                        deleted_total += len(results['ids'])
                        logger.info(f"🗑️  Deleted {len(results['ids'])} embeddings for {doc_id}")
                
                self.total_cleaned += deleted_total
                logger.info(f"✅ Cleaned up {deleted_total} embeddings for doc_id={doc_id}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"❌ Cleanup failed for {doc_id}: {e}")
            return False
    
    async def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get current ChromaDB memory usage
        
        Returns:
            Memory usage statistics
        """
        try:
            if hasattr(self.vector_store, 'client'):
                collections = self.vector_store.client.list_collections()
                
                total_embeddings = 0
                collection_stats = []
                
                for collection in collections:
                    count = collection.count()
                    total_embeddings += count
                    
                    collection_stats.append({
                        "name": collection.name,
                        "count": count
                    })
                
                # Estimate memory (rough: ~1KB per embedding)
                estimated_mb = (total_embeddings * 1024) / (1024 * 1024)
                
                return {
                    "total_embeddings": total_embeddings,
                    "estimated_memory_mb": round(estimated_mb, 2),
                    "collections": collection_stats,
                    "last_cleanup": self.last_cleanup.isoformat() if self.last_cleanup else None,
                    "total_cleaned": self.total_cleaned
                }
            
            return {"error": "No vector store client available"}
        
        except Exception as e:
            logger.error(f"❌ Failed to get memory usage: {e}")
            return {"error": str(e)}
    
    async def auto_cleanup_loop(self):
        """
        Run automatic cleanup loop in background
        BUG #15 FIX: Periodic cleanup to prevent memory buildup
        """
        logger.info(f"🔄 Starting auto-cleanup loop (every {self.cleanup_interval/3600}h)")
        
        while True:
            try:
                # Wait for interval
                await asyncio.sleep(self.cleanup_interval)
                
                # Run cleanup
                logger.info("🧹 Running scheduled cleanup...")
                deleted = await self.cleanup_old_embeddings(days_old=7)
                
                # Log memory usage
                usage = await self.get_memory_usage()
                logger.info(f"📊 Memory usage: {usage.get('estimated_memory_mb', 0)} MB")
            
            except Exception as e:
                logger.error(f"❌ Auto-cleanup error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    def start_auto_cleanup(self):
        """Start auto-cleanup in background"""
        asyncio.create_task(self.auto_cleanup_loop())
        logger.info("✅ Auto-cleanup started")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics"""
        return {
            "cleanup_interval_hours": self.cleanup_interval / 3600,
            "last_cleanup": self.last_cleanup.isoformat() if self.last_cleanup else None,
            "total_cleaned": self.total_cleaned
        }


async def cleanup_vector_db(vector_store, days_old: int = 7) -> int:
    """
    Standalone function to cleanup vector database
    
    Args:
        vector_store: Vector store instance
        days_old: Delete embeddings older than this
        
    Returns:
        Number of embeddings deleted
    """
    cleanup = VectorStoreCleanup(vector_store)
    return await cleanup.cleanup_old_embeddings(days_old)
