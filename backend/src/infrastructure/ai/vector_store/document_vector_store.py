"""
Vector Database service for API documentation storage and retrieval
Uses ChromaDB for semantic search and context retrieval
"""
import os
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from .document_chunker import DocumentChunker, DocumentChunk
from src.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class DocumentVectorStore:
    """
    Vector database for storing and querying API documentation
    Provides semantic search for intelligent test adaptation
    """
    
    def __init__(
        self,
        collection_name: str = None,
        persist_directory: str = None,
        embedding_model: str = None
    ):
        """
        Initialize Vector Store
        
        Args:
            collection_name: Name of the collection (defaults to settings)
            persist_directory: Directory to persist data (defaults to settings)
            embedding_model: Sentence transformer model (defaults to settings)
        """
        settings = get_settings()
        
        self.collection_name = collection_name or settings.vector_db_collection_prefix
        self.persist_directory = persist_directory or settings.vector_db_persist_dir
        self.embedding_model = embedding_model or settings.embedding_model
        
        # Create persist directory if it doesn't exist
        os.makedirs(self.persist_directory, exist_ok=True)
        
        logger.info(f"[INIT] Initializing ChromaDB client at: {self.persist_directory}")
        
        # Initialize ChromaDB client
        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False
                )
            )
            logger.info("[OK] ChromaDB client initialized")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize ChromaDB client: {e}")
            raise
        
        # Initialize embedding function
        try:
            logger.info(f"[LOAD] Loading embedding model: {self.embedding_model}")
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model
            )
            logger.info(f"[OK] Embedding model loaded: {self.embedding_model}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to load embedding model: {e}")
            logger.error("[IDEA] Make sure sentence-transformers is installed: pip install sentence-transformers")
            raise
        
        # Initialize chunker
        self.chunker = DocumentChunker(
            max_chunk_size=settings.vector_db_chunk_size,
            overlap=settings.vector_db_chunk_overlap
        )
        
        # Get or create collection
        self.collection = None
        self.top_k = settings.vector_db_top_k
        
        logger.info(f"[OK] DocumentVectorStore fully initialized")
    
    def _get_collection(self, doc_id: str):
        """Get or create collection for a document"""
        collection_name = f"{self.collection_name}_{doc_id}"
        
        try:
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Retrieved existing collection: {collection_name}")
        except Exception:
            collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"doc_id": doc_id}
            )
            logger.info(f"Created new collection: {collection_name}")
        
        return collection
    
    def store_documentation(
        self,
        doc_id: str,
        doc_text: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Store documentation in vector database
        
        Args:
            doc_id: Unique document identifier
            doc_text: Full documentation text
            metadata: Additional metadata
            
        Returns:
            Dictionary with storage stats
        """
        try:
            logger.info(f"Storing documentation for doc_id: {doc_id}")
            
            # Get collection for this document
            collection = self._get_collection(doc_id)
            
            # Chunk the documentation
            chunks = self.chunker.chunk_by_api_sections(doc_text, doc_id)
            
            if not chunks:
                logger.warning(f"No chunks created for doc_id: {doc_id}")
                return {
                    "success": False,
                    "error": "No chunks created",
                    "chunks_count": 0
                }
            
            # Prepare data for ChromaDB
            documents = [chunk.text for chunk in chunks]
            ids = [chunk.chunk_id for chunk in chunks]
            metadatas = []
            
            for chunk in chunks:
                chunk_metadata = chunk.metadata.copy()
                if metadata:
                    chunk_metadata.update(metadata)
                # Convert all values to strings (ChromaDB requirement)
                chunk_metadata = {
                    k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                    for k, v in chunk_metadata.items()
                }
                metadatas.append(chunk_metadata)
            
            # Store in ChromaDB
            collection.add(
                documents=documents,
                ids=ids,
                metadatas=metadatas
            )
            
            logger.info(f"Stored {len(chunks)} chunks for doc_id: {doc_id}")
            
            return {
                "success": True,
                "doc_id": doc_id,
                "chunks_count": len(chunks),
                "collection_name": collection.name,
                "total_chars": sum(len(chunk.text) for chunk in chunks)
            }
            
        except Exception as e:
            logger.error(f"Error storing documentation: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "chunks_count": 0
            }
    
    def query(
        self,
        doc_id: str,
        query_text: str,
        top_k: int = None,
        filter_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Query vector database for relevant chunks
        
        Args:
            doc_id: Document identifier
            query_text: Query string
            top_k: Number of results to return
            filter_metadata: Metadata filters
            
        Returns:
            List of relevant chunks with scores
        """
        try:
            collection = self._get_collection(doc_id)
            top_k = top_k or self.top_k
            
            # Query ChromaDB
            results = collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=filter_metadata
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'text': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else None,
                        'id': results['ids'][0][i] if results['ids'] else None
                    })
            
            logger.info(f"Query returned {len(formatted_results)} results for doc_id: {doc_id}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error querying vector database: {str(e)}", exc_info=True)
            return []
    
    def get_endpoint_context(
        self,
        doc_id: str,
        endpoint_path: str,
        method: str = None
    ) -> str:
        """
        Get relevant context for a specific API endpoint
        
        Args:
            doc_id: Document identifier
            endpoint_path: API endpoint path (e.g., "/api/create")
            method: HTTP method (e.g., "POST")
            
        Returns:
            Concatenated context string
        """
        try:
            # Build query
            query = f"{method} {endpoint_path}" if method else endpoint_path
            
            # Build metadata filter
            filter_metadata = {}
            if method:
                filter_metadata['method'] = method
            
            # Query for relevant chunks
            results = self.query(
                doc_id=doc_id,
                query_text=query,
                top_k=self.top_k,
                filter_metadata=filter_metadata if filter_metadata else None
            )
            
            # Concatenate results
            context = "\n\n---\n\n".join([r['text'] for r in results])
            
            logger.info(
                f"Retrieved endpoint context: {len(context)} chars for {method} {endpoint_path}"
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting endpoint context: {str(e)}", exc_info=True)
            return ""
    
    def find_field_info(
        self,
        doc_id: str,
        field_name: str,
        endpoint: str = None
    ) -> List[Dict[str, Any]]:
        """
        Find information about a specific field
        
        Args:
            doc_id: Document identifier
            field_name: Field name to search for
            endpoint: Optional endpoint filter
            
        Returns:
            List of relevant chunks mentioning the field
        """
        try:
            query = f"field {field_name} required optional type validation"
            
            results = self.query(
                doc_id=doc_id,
                query_text=query,
                top_k=5
            )
            
            # Filter results that actually mention the field
            filtered = [
                r for r in results
                if field_name.lower() in r['text'].lower()
            ]
            
            logger.info(f"Found {len(filtered)} chunks mentioning field: {field_name}")
            return filtered
            
        except Exception as e:
            logger.error(f"Error finding field info: {str(e)}", exc_info=True)
            return []
    
    def get_examples(self, doc_id: str, endpoint: str = None) -> List[str]:
        """
        Extract examples from documentation
        
        Args:
            doc_id: Document identifier
            endpoint: Optional endpoint filter
            
        Returns:
            List of example texts
        """
        try:
            query = "example sample request response payload"
            
            results = self.query(
                doc_id=doc_id,
                query_text=query,
                top_k=5
            )
            
            # Filter for chunks with examples
            examples = [
                r['text'] for r in results
                if r['metadata'].get('has_examples') == 'True'
            ]
            
            logger.info(f"Found {len(examples)} example chunks")
            return examples
            
        except Exception as e:
            logger.error(f"Error getting examples: {str(e)}", exc_info=True)
            return []
    
    def get_error_context(
        self,
        doc_id: str,
        error_message: str,
        endpoint: str = None
    ) -> str:
        """
        Get context relevant to an error message
        
        Args:
            doc_id: Document identifier
            error_message: Error message to analyze
            endpoint: Optional endpoint filter
            
        Returns:
            Relevant context string
        """
        try:
            # Query with error message
            results = self.query(
                doc_id=doc_id,
                query_text=error_message,
                top_k=self.top_k
            )
            
            context = "\n\n---\n\n".join([r['text'] for r in results])
            
            logger.info(f"Retrieved error context: {len(context)} chars")
            return context
            
        except Exception as e:
            logger.error(f"Error getting error context: {str(e)}", exc_info=True)
            return ""
    
    def get_stats(self, doc_id: str) -> Dict[str, Any]:
        """
        Get statistics for a document's vector storage
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Dictionary with stats
        """
        try:
            collection = self._get_collection(doc_id)
            count = collection.count()
            
            return {
                "doc_id": doc_id,
                "collection_name": collection.name,
                "chunks_count": count,
                "embedding_model": self.embedding_model,
                "exists": count > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}", exc_info=True)
            return {
                "doc_id": doc_id,
                "exists": False,
                "error": str(e)
            }
    
    def clear_collection(self, doc_id: str) -> bool:
        """
        Clear all data for a document
        
        Args:
            doc_id: Document identifier
            
        Returns:
            True if successful
        """
        try:
            collection_name = f"{self.collection_name}_{doc_id}"
            self.client.delete_collection(name=collection_name)
            logger.info(f"Cleared collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing collection: {str(e)}", exc_info=True)
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of vector database
        
        Returns:
            Health status dictionary
        """
        try:
            # Try to list collections
            collections = self.client.list_collections()
            
            return {
                "status": "healthy",
                "collections_count": len(collections),
                "persist_directory": self.persist_directory,
                "embedding_model": self.embedding_model
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}", exc_info=True)
            return {
                "status": "unhealthy",
                "error": str(e)
            }

