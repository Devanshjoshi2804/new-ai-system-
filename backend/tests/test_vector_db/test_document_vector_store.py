"""
Tests for DocumentVectorStore
"""
import pytest
import os
import tempfile
import shutil
import chromadb
from src.infrastructure.ai.vector_store.document_vector_store import DocumentVectorStore
from src.infrastructure.ai.vector_store.document_chunker import DocumentChunker


@pytest.fixture
def temp_vector_db_dir():
    """Create a temporary directory for vector DB"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except:
        pass


@pytest.fixture
def vector_store(temp_vector_db_dir):
    """Create a DocumentVectorStore instance"""
    # Reset any existing ChromaDB instances
    try:
        chromadb.api.client.SharedSystemClient.clear()
    except:
        pass
    
    store = DocumentVectorStore(
        collection_name="test_docs",
        persist_directory=temp_vector_db_dir,
        embedding_model="all-MiniLM-L6-v2"
    )
    yield store
    
    # Cleanup
    try:
        del store.client
    except:
        pass


@pytest.fixture
def sample_api_doc():
    """Sample API documentation text"""
    return """
    API Documentation
    
    POST /api/create
    Creates a new resource
    
    Required fields:
    - name (string): Resource name
    - status (string): Must be 'open' or 'closed'
    - vendorCode (string): Vendor identifier
    
    Example request:
    {
        "name": "Test Resource",
        "status": "open",
        "vendorCode": "VENDOR123"
    }
    
    Response: 200 OK
    {
        "id": "123",
        "name": "Test Resource",
        "status": "open"
    }
    
    GET /api/list
    Lists all resources
    
    Query parameters:
    - page (integer): Page number
    - limit (integer): Items per page
    
    Response: 200 OK
    [
        {"id": "123", "name": "Resource 1"},
        {"id": "456", "name": "Resource 2"}
    ]
    """


class TestDocumentChunker:
    """Test DocumentChunker functionality"""
    
    def test_chunk_by_api_sections(self, sample_api_doc):
        """Test chunking by API sections"""
        chunker = DocumentChunker(max_chunk_size=500, overlap=50)
        chunks = chunker.chunk_by_api_sections(sample_api_doc, "test_doc_1")
        
        assert len(chunks) > 0
        assert all(chunk.text for chunk in chunks)
        assert all(chunk.chunk_id.startswith("test_doc_1") for chunk in chunks)
    
    def test_extract_metadata(self, sample_api_doc):
        """Test metadata extraction"""
        chunker = DocumentChunker()
        metadata = chunker.extract_metadata(sample_api_doc, None)
        
        # Should detect fields
        assert isinstance(metadata, dict)
        
    def test_chunk_by_semantic_blocks(self, sample_api_doc):
        """Test semantic chunking"""
        chunker = DocumentChunker(max_chunk_size=200, overlap=50)
        chunks = chunker.chunk_by_semantic_blocks(sample_api_doc, "test_doc_2")
        
        assert len(chunks) > 0
        assert all(len(chunk.text) <= 250 for chunk in chunks)  # Allow some overflow


class TestDocumentVectorStore:
    """Test DocumentVectorStore functionality"""
    
    def test_store_documentation(self, vector_store, sample_api_doc):
        """Test storing documentation"""
        result = vector_store.store_documentation(
            doc_id="test_doc_1",
            doc_text=sample_api_doc,
            metadata={"source": "test"}
        )
        
        assert result['success'] is True
        assert result['chunks_count'] > 0
        assert result['doc_id'] == "test_doc_1"
    
    def test_query_documentation(self, vector_store, sample_api_doc):
        """Test querying documentation"""
        # First store
        vector_store.store_documentation(
            doc_id="test_doc_1",
            doc_text=sample_api_doc
        )
        
        # Then query
        results = vector_store.query(
            doc_id="test_doc_1",
            query_text="How do I create a resource?",
            top_k=3
        )
        
        assert len(results) > 0
        assert all('text' in r for r in results)
        assert any('create' in r['text'].lower() for r in results)
    
    def test_get_endpoint_context(self, vector_store, sample_api_doc):
        """Test getting endpoint-specific context"""
        # Store documentation
        vector_store.store_documentation(
            doc_id="test_doc_1",
            doc_text=sample_api_doc
        )
        
        # Get context for specific endpoint
        context = vector_store.get_endpoint_context(
            doc_id="test_doc_1",
            endpoint_path="/api/create",
            method="POST"
        )
        
        assert len(context) > 0
        assert 'create' in context.lower() or 'post' in context.lower()
    
    def test_find_field_info(self, vector_store, sample_api_doc):
        """Test finding field information"""
        # Store documentation
        vector_store.store_documentation(
            doc_id="test_doc_1",
            doc_text=sample_api_doc
        )
        
        # Find info about 'status' field
        results = vector_store.find_field_info(
            doc_id="test_doc_1",
            field_name="status"
        )
        
        assert len(results) > 0
        assert any('status' in r['text'].lower() for r in results)
    
    def test_get_stats(self, vector_store, sample_api_doc):
        """Test getting statistics"""
        # Store documentation
        vector_store.store_documentation(
            doc_id="test_doc_1",
            doc_text=sample_api_doc
        )
        
        # Get stats
        stats = vector_store.get_stats("test_doc_1")
        
        assert stats['exists'] is True
        assert stats['chunks_count'] > 0
        assert stats['doc_id'] == "test_doc_1"
    
    def test_clear_collection(self, vector_store, sample_api_doc):
        """Test clearing a collection"""
        # Store documentation
        vector_store.store_documentation(
            doc_id="test_doc_1",
            doc_text=sample_api_doc
        )
        
        # Clear it
        success = vector_store.clear_collection("test_doc_1")
        assert success is True
        
        # Verify it's gone
        stats = vector_store.get_stats("test_doc_1")
        assert stats['exists'] is False or stats['chunks_count'] == 0
    
    def test_health_check(self, vector_store):
        """Test health check"""
        health = vector_store.health_check()
        
        assert health['status'] == 'healthy'
        assert 'collections_count' in health
        assert 'embedding_model' in health


class TestVectorDBIntegration:
    """Integration tests for Vector DB"""
    
    def test_full_workflow(self, vector_store, sample_api_doc):
        """Test complete workflow: store, query, update, delete"""
        doc_id = "integration_test_doc"
        
        # 1. Store documentation
        store_result = vector_store.store_documentation(
            doc_id=doc_id,
            doc_text=sample_api_doc,
            metadata={"test": "integration"}
        )
        assert store_result['success'] is True
        
        # 2. Query for relevant information
        results = vector_store.query(
            doc_id=doc_id,
            query_text="What fields are required for creating?",
            top_k=2
        )
        assert len(results) > 0
        
        # 3. Get endpoint context
        context = vector_store.get_endpoint_context(
            doc_id=doc_id,
            endpoint_path="/api/create",
            method="POST"
        )
        assert len(context) > 0
        
        # 4. Get field information
        field_info = vector_store.find_field_info(
            doc_id=doc_id,
            field_name="vendorCode"
        )
        assert len(field_info) > 0
        
        # 5. Get examples
        examples = vector_store.get_examples(doc_id=doc_id)
        assert isinstance(examples, list)
        
        # 6. Get stats
        stats = vector_store.get_stats(doc_id)
        assert stats['exists'] is True
        
        # 7. Clear collection
        success = vector_store.clear_collection(doc_id)
        assert success is True
        
        # 8. Verify deletion
        stats_after = vector_store.get_stats(doc_id)
        assert stats_after['exists'] is False or stats_after['chunks_count'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
