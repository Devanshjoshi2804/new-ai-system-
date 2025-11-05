"""
Simple Testing REST Endpoint
Clean, working API testing with RAG and intelligent retry
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
import logging
from datetime import datetime

from ...application.ai.simple_testing import (
    extract_document,
    chunk_text,
    analyze_endpoints,
    test_all_endpoints
)
from ...infrastructure.database.mongodb.connection import MongoDBConnection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simple-testing", tags=["Simple Testing"])


# Request/Response Models
class TestRequest(BaseModel):
    """Request to start simple API testing"""
    partner_id: str = Field(..., description="Partner ID")
    documentation_id: str = Field(..., description="Documentation ID from MongoDB")
    base_url: Optional[str] = Field(None, description="Optional base URL override")

class TestResult(BaseModel):
    """Individual test result"""
    endpoint: str
    url: Optional[str] = None
    status_code: int
    success: bool
    attempts: int
    final_payload: Dict[str, Any]
    response: Optional[Union[Dict[str, Any], str]] = None  # Can be Dict (JSON) or str (HTML error)
    error: Optional[str] = None

class TestResponse(BaseModel):
    """Complete test results"""
    status: str
    total_tests: int
    passed: int
    failed: int
    pass_rate: float
    execution_time: float
    base_url: str
    results: List[TestResult]
    started_at: str
    completed_at: str


@router.post("/test", response_model=TestResponse)
async def run_simple_test(request: TestRequest):
    """
    Run simple, effective API testing
    
    Process:
    1. Get document from MongoDB
    2. Extract text (PDF/JSON)
    3. Chunk for RAG
    4. Analyze endpoints with AI
    5. Test all endpoints with smart retry
    6. Return comprehensive results
    
    This is the SIMPLE, WORKING approach!
    """
    started_at = datetime.now()
    
    try:
        logger.info(f"[START] Starting simple testing for partner {request.partner_id}")
        
        # Step 1: Get document from MongoDB
        db = MongoDBConnection.get_database()
        doc_collection = db['api_documentation']
        
        doc = await doc_collection.find_one({"id": request.documentation_id})
        if not doc:
            raise HTTPException(status_code=404, detail=f"Documentation {request.documentation_id} not found")
        
        # Get file path or content
        if 'file_path' in doc:
            doc_path = doc['file_path']
        else:
            raise HTTPException(status_code=400, detail="Document has no file_path")
        
        # Get filename from metadata
        filename = doc.get('metadata', {}).get('filename', 'unknown')
        logger.info(f"[FILE] Found document: {filename}")
        
        # Check if document already has analyzed API spec
        api_spec = doc.get('api_spec')
        if api_spec and api_spec.get('endpoints'):
            logger.info(f"[OK] Using pre-analyzed API spec with {len(api_spec['endpoints'])} endpoints")
            endpoints = api_spec['endpoints']
            detected_base_url = api_spec.get('baseUrl', '')
            
            # Still need to extract and chunk text for RAG context
            full_text = await extract_document(doc_path)
            chunks = await chunk_text(full_text)
        else:
            logger.info(f"[INFO] No pre-analyzed spec found, analyzing document...")
            # Step 2: Extract text
            full_text = await extract_document(doc_path)
            
            # Step 3: Chunk text
            chunks = await chunk_text(full_text)
            
            # Step 4: Analyze endpoints
            detected_base_url, endpoints = await analyze_endpoints(full_text)
        
        final_base_url = request.base_url or detected_base_url
        
        if not final_base_url:
            raise HTTPException(status_code=400, detail="Could not detect base URL. Please provide it.")
        
        if not endpoints:
            raise HTTPException(status_code=400, detail="No endpoints found in documentation")
        
        logger.info(f"[SEARCH] Found {len(endpoints)} endpoints, base URL: {final_base_url}")
        
        # Step 5: Test all endpoints
        test_results = await test_all_endpoints(final_base_url, endpoints, chunks)
        
        # Calculate stats
        completed_at = datetime.now()
        execution_time = (completed_at - started_at).total_seconds()
        
        total_tests = len(test_results)
        passed = sum(1 for r in test_results if r.get('success'))
        failed = total_tests - passed
        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"[OK] Testing complete: {passed}/{total_tests} passed ({pass_rate:.1f}%)")
        
        return TestResponse(
            status="completed",
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            pass_rate=pass_rate,
            execution_time=execution_time,
            base_url=final_base_url,
            results=[TestResult(**r) for r in test_results],
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Testing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check for simple testing service"""
    return {
        "status": "healthy",
        "service": "simple_testing",
        "approach": "RAG + AI + Smart Retry",
        "features": [
            "PDF/JSON extraction",
            "AI endpoint analysis",
            "RAG-based context retrieval",
            "Intelligent payload generation",
            "Smart error fixing with retry",
            "Flow DB for context propagation"
        ]
    }


