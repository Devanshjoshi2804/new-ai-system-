"""
Vector DB Management API Endpoints
Provides endpoints for managing and querying the Vector Database
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.infrastructure.ai.vector_store import DocumentVectorStore
from src.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vector-db", tags=["Vector DB"])

# Initialize Vector DB
settings = get_settings()
vector_store = None

try:
    logger.info("[INIT] Initializing Vector DB...")
    vector_store = DocumentVectorStore(
        collection_name=settings.vector_db_collection_prefix,
        persist_directory=settings.vector_db_persist_dir,
        embedding_model=settings.embedding_model
    )
    logger.info("[OK] Vector DB initialized successfully for API endpoints")
except ImportError as e:
    logger.warning(f"[WARN]  Vector DB dependencies not available: {e}")
    logger.warning("[WARN]  Install with: pip install sentence-transformers chromadb")
except Exception as e:
    logger.error(f"[ERROR] Failed to initialize Vector DB: {e}", exc_info=True)
    logger.warning("[WARN]  Vector DB endpoints will return graceful degraded responses")


class StoreDocumentRequest(BaseModel):
    """Request model for storing documentation"""
    doc_id: str
    doc_text: str
    metadata: Optional[dict] = None


class QueryRequest(BaseModel):
    """Request model for querying Vector DB"""
    doc_id: str
    query_text: str
    top_k: Optional[int] = 3
    filter_metadata: Optional[dict] = None


@router.post("/store")
async def store_documentation(request: StoreDocumentRequest):
    """
    Store documentation in Vector DB
    
    Args:
        request: Store document request with doc_id, text, and metadata
        
    Returns:
        Storage result with stats
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector DB not available")
    
    try:
        logger.info(f"Storing documentation for doc_id: {request.doc_id}")
        
        result = vector_store.store_documentation(
            doc_id=request.doc_id,
            doc_text=request.doc_text,
            metadata=request.metadata or {}
        )
        
        if not result.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store documentation: {result.get('error')}"
            )
        
        return {
            "success": True,
            "message": f"Stored {result['chunks_count']} chunks",
            "stats": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing documentation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_vector_db(request: QueryRequest):
    """
    Query Vector DB for relevant chunks
    
    Args:
        request: Query request with doc_id and query text
        
    Returns:
        List of relevant chunks
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector DB not available")
    
    try:
        logger.info(f"Querying Vector DB for doc_id: {request.doc_id}")
        
        results = vector_store.query(
            doc_id=request.doc_id,
            query_text=request.query_text,
            top_k=request.top_k,
            filter_metadata=request.filter_metadata
        )
        
        return {
            "success": True,
            "results_count": len(results),
            "results": results,
            "total_chars": sum(len(r['text']) for r in results)
        }
        
    except Exception as e:
        logger.error(f"Error querying Vector DB: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{doc_id}")
async def get_stats(doc_id: str):
    """
    Get Vector DB statistics for a document
    
    Args:
        doc_id: Document identifier
        
    Returns:
        Statistics dictionary
    """
    if not vector_store:
        # Return graceful response instead of error
        logger.warning(f"Vector DB not initialized, returning empty stats for {doc_id}")
        return {
            "available": False,
            "message": "Vector DB not initialized (sentence-transformers may not be installed)",
            "doc_id": doc_id,
            "total_chunks": 0,
            "total_documents": 0
        }
    
    try:
        stats = vector_store.get_stats(doc_id)
        return {
            "available": True,
            **stats
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        # Return graceful response instead of error
        return {
            "available": False,
            "message": f"Error retrieving stats: {str(e)}",
            "doc_id": doc_id,
            "total_chunks": 0,
            "total_documents": 0
        }


@router.delete("/{doc_id}")
async def clear_collection(doc_id: str):
    """
    Clear Vector DB collection for a document
    
    Args:
        doc_id: Document identifier
        
    Returns:
        Success status
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector DB not available")
    
    try:
        success = vector_store.clear_collection(doc_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to clear collection")
        
        return {
            "success": True,
            "message": f"Cleared collection for doc_id: {doc_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Check Vector DB health status
    
    Returns:
        Health status dictionary
    """
    if not vector_store:
        return {
            "status": "unavailable",
            "error": "Vector DB not initialized"
        }
    
    try:
        health = vector_store.health_check()
        return health
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/endpoint-context/{doc_id}")
async def get_endpoint_context(
    doc_id: str,
    endpoint_path: str = Query(..., description="API endpoint path"),
    method: Optional[str] = Query(None, description="HTTP method")
):
    """
    Get focused context for a specific endpoint
    
    Args:
        doc_id: Document identifier
        endpoint_path: API endpoint path
        method: Optional HTTP method
        
    Returns:
        Relevant context string
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector DB not available")
    
    try:
        context = vector_store.get_endpoint_context(
            doc_id=doc_id,
            endpoint_path=endpoint_path,
            method=method
        )
        
        return {
            "success": True,
            "endpoint": f"{method} {endpoint_path}" if method else endpoint_path,
            "context": context,
            "context_length": len(context)
        }
        
    except Exception as e:
        logger.error(f"Error getting endpoint context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/field-info/{doc_id}")
async def get_field_info(
    doc_id: str,
    field_name: str = Query(..., description="Field name to search for"),
    endpoint: Optional[str] = Query(None, description="Optional endpoint filter")
):
    """
    Find information about a specific field
    
    Args:
        doc_id: Document identifier
        field_name: Field name to search for
        endpoint: Optional endpoint filter
        
    Returns:
        List of relevant chunks mentioning the field
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector DB not available")
    
    try:
        results = vector_store.find_field_info(
            doc_id=doc_id,
            field_name=field_name,
            endpoint=endpoint
        )
        
        return {
            "success": True,
            "field_name": field_name,
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error finding field info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/examples/{doc_id}")
async def get_examples(
    doc_id: str,
    endpoint: Optional[str] = Query(None, description="Optional endpoint filter")
):
    """
    Extract examples from documentation
    
    Args:
        doc_id: Document identifier
        endpoint: Optional endpoint filter
        
    Returns:
        List of example texts
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector DB not available")
    
    try:
        examples = vector_store.get_examples(
            doc_id=doc_id,
            endpoint=endpoint
        )
        
        return {
            "success": True,
            "examples_count": len(examples),
            "examples": examples
        }
        
    except Exception as e:
        logger.error(f"Error getting examples: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

