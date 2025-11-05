"""
Simple MongoDB Documentation Repository
Uses Motor directly without Beanie
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from src.infrastructure.database.mongodb.simple_repository import SimpleMongoRepository
from src.infrastructure.ai.vector_store.document_vector_store import DocumentVectorStore
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class MongoDBDocumentationRepository:
    """MongoDB Documentation Repository using Motor directly"""
    
    def __init__(self, enable_vector_db: bool = True):
        self.repo = SimpleMongoRepository('api_documentation')
        self.enable_vector_db = enable_vector_db
        self.vector_store = None
        
        # Initialize Vector DB if enabled
        if enable_vector_db:
            try:
                self.vector_store = DocumentVectorStore(
                    collection_name=settings.vector_db_collection_prefix,
                    persist_directory=settings.vector_db_persist_dir,
                    embedding_model=settings.embedding_model
                )
                logger.info("[OK] Vector DB initialized successfully")
            except Exception as e:
                logger.warning(f"[WARN]  Vector DB initialization failed: {e}. Continuing without Vector DB.")
                self.vector_store = None
    
    async def create(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new documentation record"""
        # Generate ID if not provided
        if 'id' not in doc_data:
            doc_data['id'] = str(uuid.uuid4())
        
        # Set defaults
        doc_data.setdefault('parsing_status', 'pending')
        doc_data.setdefault('parsing_progress', 0)
        doc_data.setdefault('extracted_endpoints_count', 0)
        doc_data.setdefault('metadata', {})
        
        # Insert into MongoDB
        doc_id = await self.repo.insert_one(doc_data)
        
        # Return the created document
        return await self.get_by_id(doc_data['id'])
    
    async def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get documentation by ID"""
        return await self.repo.find_one({'id': doc_id})
    
    async def get_by_partner_id(self, partner_id: str) -> List[Dict[str, Any]]:
        """Get all documentation for a partner"""
        return await self.repo.find_many({'partner_id': partner_id})
    
    async def update(self, doc_id: str, update_data: Dict[str, Any]) -> bool:
        """Update documentation"""
        return await self.repo.update_one({'id': doc_id}, update_data)
    
    async def update_parsing_status(self, doc_id: str, status: str, progress: int = 0, error: str = None) -> bool:
        """Update parsing status"""
        update_data = {
            'parsing_status': status,
            'parsing_progress': progress
        }
        if error:
            update_data['parsing_error'] = error
        return await self.repo.update_one({'id': doc_id}, update_data)
    
    async def update_parsed_data(self, doc_id: str, api_spec: Dict[str, Any], endpoints_count: int) -> bool:
        """Update parsed API specification"""
        result = await self.repo.update_one(
            {'id': doc_id},
            {
                'api_spec': api_spec,
                'extracted_endpoints_count': endpoints_count,
                'parsing_status': 'completed',
                'parsing_progress': 100,
                'parsed_at': datetime.utcnow()
            }
        )
        
        # Store in Vector DB if available
        if result and self.vector_store:
            try:
                # Get the full document
                doc = await self.get_by_id(doc_id)
                if doc and doc.get('extracted_text'):
                    logger.info(f"[DOC] Storing documentation in Vector DB for doc_id: {doc_id}")
                    
                    # Store in vector DB
                    vector_result = self.vector_store.store_documentation(
                        doc_id=doc_id,
                        doc_text=doc['extracted_text'],
                        metadata={
                            'partner_id': doc.get('partner_id'),
                            'filename': doc.get('filename'),
                            'endpoints_count': endpoints_count
                        }
                    )
                    
                    # Update MongoDB with vector DB stats
                    await self.repo.update_one(
                        {'id': doc_id},
                        {
                            'vector_db_stored': True,
                            'vector_db_chunks': vector_result.get('chunks_count', 0),
                            'vector_db_chars': vector_result.get('total_chars', 0)
                        }
                    )
                    
                    logger.info(f"[OK] Stored {vector_result.get('chunks_count', 0)} chunks in Vector DB")
            except Exception as e:
                logger.error(f"[ERROR] Failed to store in Vector DB: {e}")
        
        return result
    
    async def delete(self, doc_id: str) -> bool:
        """Delete documentation"""
        # Delete from Vector DB first
        if self.vector_store:
            try:
                self.vector_store.delete_document(doc_id)
                logger.info(f"[OK] Deleted from Vector DB: {doc_id}")
            except Exception as e:
                logger.warning(f"[WARN]  Failed to delete from Vector DB: {e}")
        
        return await self.repo.delete_one({'id': doc_id})
    
    async def count_by_partner(self, partner_id: str) -> int:
        """Count documentation for a partner"""
        return await self.repo.count({'partner_id': partner_id})
    
    def get_vector_store(self) -> Optional[DocumentVectorStore]:
        """Get the vector store instance"""
        return self.vector_store
    
    def get_vector_db_stats(self, doc_id: Optional[str] = None) -> Dict[str, Any]:
        """Get Vector DB statistics"""
        if not self.vector_store:
            return {"error": "Vector DB not available"}
        
        try:
            return self.vector_store.get_stats(doc_id)
        except Exception as e:
            logger.error(f"Error getting Vector DB stats: {e}")
            return {"error": str(e)}


