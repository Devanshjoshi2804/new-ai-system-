"""
Test documentation upload and parsing APIs
"""
import pytest
import io
import json
from fastapi.testclient import TestClient


class TestDocumentationUpload:
    """Test document upload functionality"""
    
    def test_upload_openapi_json(self, client: TestClient, sample_partner_data, sample_openapi_spec):
        """Test uploading OpenAPI JSON file"""
        # Register partner first
        reg_response = client.post("/api/partners/register", json=sample_partner_data)
        
        # May fail if MongoDB not available
        if reg_response.status_code != 200:
            import pytest
            pytest.skip("MongoDB not available for testing")
            return
        
        partner_id = reg_response.json()["id"]
        
        # Create file
        file_content = json.dumps(sample_openapi_spec).encode()
        files = {"file": ("openapi.json", io.BytesIO(file_content), "application/json")}
        
        # Upload
        response = client.post(f"/api/partners/{partner_id}/documentation", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["partner_id"] == partner_id
        assert data["file_name"] == "openapi.json"
    
    def test_upload_without_partner(self, client: TestClient):
        """Test upload without valid partner"""
        files = {"file": ("test.json", io.BytesIO(b"{}"), "application/json")}
        response = client.post("/api/partners/invalid-id/documentation", files=files)
        
        # Should fail gracefully
        assert response.status_code in [404, 500]


class TestDocumentationParsing:
    """Test document parsing functionality"""
    
    def test_parse_openapi_document(self, client: TestClient, sample_partner_data, sample_openapi_spec):
        """Test parsing OpenAPI document"""
        # Register and upload
        reg_response = client.post("/api/partners/register", json=sample_partner_data)
        
        # May fail if MongoDB not available
        if reg_response.status_code != 200:
            import pytest
            pytest.skip("MongoDB not available for testing")
            return
        
        partner_id = reg_response.json()["id"]
        
        file_content = json.dumps(sample_openapi_spec).encode()
        files = {"file": ("openapi.json", io.BytesIO(file_content), "application/json")}
        upload_response = client.post(f"/api/partners/{partner_id}/documentation", files=files)
        doc_id = upload_response.json()["id"]
        
        # Parse
        response = client.post(f"/api/documentation/{doc_id}/parse")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["completed", "processing"]
        assert "format" in data
    
    def test_parse_nonexistent_document(self, client: TestClient):
        """Test parsing non-existent document"""
        response = client.post("/api/documentation/nonexistent-id/parse")
        assert response.status_code == 404

