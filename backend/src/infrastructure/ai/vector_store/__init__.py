"""Vector store infrastructure"""
from .flow_vector_store import FlowVectorStore

# Optional imports (may fail if dependencies not installed)
try:
    from .tenant_namespace_manager import TenantNamespaceManager, get_vector_store
    from .document_vector_store import DocumentVectorStore
    from .document_chunker import DocumentChunker, DocumentChunk
    
    __all__ = [
        "TenantNamespaceManager",
        "get_vector_store",
        "DocumentVectorStore",
        "DocumentChunker",
        "DocumentChunk",
        "FlowVectorStore"
    ]
except ImportError as e:
    # If Pinecone or other dependencies not installed
    __all__ = ["FlowVectorStore"]

