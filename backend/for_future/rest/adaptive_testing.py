"""
Adaptive Testing Endpoint
Intelligent testing that learns and adapts until success
"""
import logging
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.application.ai.testing.intelligent_adaptive_executor import IntelligentAdaptiveExecutor
from src.infrastructure.database.mongodb.documentation_repository import MongoDBDocumentationRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/adaptive-testing", tags=["Adaptive Testing"])


class StartAdaptiveTestingRequest(BaseModel):
    """Request to start adaptive testing"""
    partner_id: str
    documentation_id: str
    max_attempts_per_endpoint: int = 20  # Configurable!
    tenant_id: Optional[str] = "default"


class AdaptiveTestingResponse(BaseModel):
    """Response for adaptive testing"""
    success: bool
    test_id: str
    message: str
    error: Optional[str] = None


# In-memory storage for test results
test_results_store: Dict[str, Dict[str, Any]] = {}


@router.post("/start", response_model=AdaptiveTestingResponse)
async def start_adaptive_testing(
    request: StartAdaptiveTestingRequest,
    background_tasks: BackgroundTasks
):
    """
    Start adaptive testing with NO LIMITS
    
    This endpoint:
    1. Loads API documentation and analysis
    2. Creates intelligent adaptive executor
    3. Tests each endpoint until success (up to max_attempts_per_endpoint)
    4. Uses AI to learn from errors and adapt payloads
    5. Streams real-time progress via WebSocket
    6. Returns test_id for tracking
    
    Features:
    - No arbitrary test case limits
    - AI learns from every response
    - Adapts payloads dynamically
    - Keeps trying until success
    - Real-time streaming to terminal
    """
    try:
        logger.info(f"🧠 Starting adaptive testing for partner: {request.partner_id}")
        
        # Load documentation and analysis
        doc_repo = MongoDBDocumentationRepository(enable_vector_db=True)
        doc = await doc_repo.get_by_id(request.documentation_id)
        
        if not doc:
            raise HTTPException(status_code=404, detail="Documentation not found")
        
        # Get API specification from doc
        api_spec = doc.get('api_specification', {})
        if not api_spec:
            raise HTTPException(status_code=400, detail="No API specification found")
        
        # Generate test ID
        test_id = str(uuid.uuid4())
        
        # Get endpoints and auth config
        endpoints = api_spec.get('endpoints', [])
        auth_config = api_spec.get('auth_config', {})
        base_url = api_spec.get('base_url', '')
        documentation_text = api_spec.get('raw_text', '')
        
        if not endpoints:
            raise HTTPException(status_code=400, detail="No endpoints found in documentation")
        
        # Get Vector DB instance
        vector_store = doc_repo.get_vector_store()
        using_vector_db = vector_store is not None
        
        logger.info(f"✅ Found {len(endpoints)} endpoints to test")
        logger.info(f"🎯 Max attempts per endpoint: {request.max_attempts_per_endpoint}")
        logger.info(f"📚 Vector DB: {'Enabled' if using_vector_db else 'Disabled'}")
        
        # Start adaptive testing in background
        background_tasks.add_task(
            run_adaptive_testing_background,
            test_id=test_id,
            endpoints=endpoints,
            base_url=base_url,
            auth_config=auth_config,
            documentation_text=documentation_text,
            max_attempts=request.max_attempts_per_endpoint,
            vector_store=vector_store
        )
        
        vector_db_msg = " with Vector DB" if using_vector_db else ""
        
        return AdaptiveTestingResponse(
            success=True,
            test_id=test_id,
            message=f"Adaptive testing started{vector_db_msg} with {len(endpoints)} endpoints. "
                    f"Will try up to {request.max_attempts_per_endpoint} times per endpoint. "
                    f"Watch progress in real-time via WebSocket!"
        )
    
    except Exception as e:
        logger.error(f"❌ Error starting adaptive testing: {e}", exc_info=True)
        return AdaptiveTestingResponse(
            success=False,
            test_id="",
            message="Failed to start adaptive testing",
            error=str(e)
        )


async def run_adaptive_testing_background(
    test_id: str,
    endpoints: List[Dict[str, Any]],
    base_url: str,
    auth_config: Dict[str, Any],
    documentation_text: str,
    max_attempts: int,
    vector_store=None
):
    """Run adaptive testing in background"""
    try:
        logger.info(f"🚀 Starting background adaptive testing: {test_id}")
        logger.info(f"📚 Vector DB: {'Enabled' if vector_store else 'Disabled'}")
        
        # Create executor
        executor = IntelligentAdaptiveExecutor(
            test_id=test_id,
            max_attempts_per_endpoint=max_attempts,
            vector_store=vector_store
        )
        
        # Execute adaptive testing
        results = await executor.test_until_success(
            endpoints=endpoints,
            base_url=base_url,
            auth_config=auth_config,
            documentation_text=documentation_text
        )
        
        # Store results
        test_results_store[test_id] = results
        
        logger.info(f"✅ Adaptive testing complete: {test_id}")
        logger.info(f"📊 Success rate: {results['successful']}/{results['total_endpoints']}")
    
    except Exception as e:
        logger.error(f"❌ Background adaptive testing error: {e}", exc_info=True)
        test_results_store[test_id] = {
            'success': False,
            'error': str(e)
        }


@router.get("/results/{test_id}")
async def get_adaptive_test_results(test_id: str) -> Dict[str, Any]:
    """
    Get results of adaptive testing
    
    Args:
        test_id: Test execution ID
        
    Returns:
        Test results
    """
    if test_id not in test_results_store:
        raise HTTPException(status_code=404, detail="Test results not found")
    
    return test_results_store[test_id]


@router.get("/status/{test_id}")
async def get_adaptive_test_status(test_id: str) -> Dict[str, Any]:
    """
    Get status of adaptive testing
    
    Args:
        test_id: Test execution ID
        
    Returns:
        Test status
    """
    from src.infrastructure.realtime.test_stream import get_event_stream
    
    stream = get_event_stream()
    
    return {
        'test_id': test_id,
        'active': test_id in stream.streams,
        'subscriber_count': stream.get_subscriber_count(test_id),
        'buffered_events': len(stream.buffers.get(test_id, [])),
        'results_available': test_id in test_results_store
    }


@router.delete("/results/{test_id}")
async def delete_adaptive_test_results(test_id: str) -> Dict[str, Any]:
    """
    Delete test results
    
    Args:
        test_id: Test execution ID
        
    Returns:
        Success status
    """
    if test_id in test_results_store:
        del test_results_store[test_id]
        return {'success': True, 'message': 'Results deleted'}
    else:
        raise HTTPException(status_code=404, detail="Test results not found")
