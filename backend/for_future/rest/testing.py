"""
REST API endpoints for API testing functionality
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from ...application.use_cases.partners.test_partner_integration import (
    test_partner_integration,
    get_test_execution_progress,
    get_test_execution_results
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/testing", tags=["testing"])


class StartTestingRequest(BaseModel):
    """Request to start API testing"""
    partner_id: str = Field(..., description="Partner ID")
    documentation_id: str = Field(..., description="Documentation ID")
    tenant_id: Optional[str] = Field(None, description="Tenant ID")


class StartTestingResponse(BaseModel):
    """Response after starting testing"""
    test_execution_id: str = Field(..., description="Test execution ID")
    status: str = Field(..., description="Initial status")
    message: str = Field(..., description="Status message")


class TestingProgressResponse(BaseModel):
    """Real-time testing progress"""
    test_execution_id: str
    status: str
    current_phase: str
    current_endpoint: Optional[str]
    tested_endpoints: int
    total_endpoints: int
    passed_tests: int
    failed_tests: int
    is_complete: bool
    error_message: Optional[str] = None


@router.post("/start", response_model=StartTestingResponse)
async def start_api_testing(
    request: StartTestingRequest,
    background_tasks: BackgroundTasks
):
    """
    Start automated API testing for a partner integration
    
    This endpoint triggers the complete AI-powered testing workflow:
    1. Analyzes API dependencies
    2. Creates specialized test agents
    3. Generates comprehensive test cases
    4. Executes tests with retry logic
    5. Stores results
    
    Testing runs in the background and progress can be monitored via
    the /testing/{test_execution_id}/progress endpoint.
    """
    try:
        logger.info(f"Starting API testing for partner {request.partner_id}")
        
        # Get API documentation using Motor-based repository
        from ...infrastructure.database.mongodb.documentation_repository import MongoDBDocumentationRepository
        
        doc_repo = MongoDBDocumentationRepository()
        doc = await doc_repo.get_by_id(request.documentation_id)
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"Documentation {request.documentation_id} not found"
            )
        
        # Verify documentation has API spec
        api_spec = doc.get('api_spec', {})
        if not api_spec or not api_spec.get('endpoints'):
            raise HTTPException(
                status_code=400,
                detail="Documentation does not contain valid API specification"
            )
        
        # Create test execution record first
        from ...infrastructure.database.mongodb.test_execution_repository import MongoDBTestExecutionRepository
        import uuid
        from datetime import datetime
        
        test_exec_repo = MongoDBTestExecutionRepository()
        test_execution_id = str(uuid.uuid4())
        
        # Create initial test execution record
        await test_exec_repo.create({
            'id': test_execution_id,
            'partner_id': request.partner_id,
            'documentation_id': request.documentation_id,
            'status': 'pending',
            'current_phase': 'Initializing',
            'tested_endpoints': 0,
            'total_endpoints': len(api_spec.get('endpoints', [])),
            'passed_tests': 0,
            'failed_tests': 0,
            'started_at': datetime.utcnow(),
            'is_complete': False
        })
        
        logger.info(f"Created test execution: {test_execution_id}")
        
        # Start testing in background
        async def run_testing():
            try:
                logger.info(f"🚀 Background task starting for test execution: {test_execution_id}")
                await test_partner_integration(
                    partner_id=request.partner_id,
                    documentation_id=request.documentation_id,
                    api_spec=api_spec,
                    tenant_id=request.tenant_id,
                    test_execution_id=test_execution_id  # Pass the ID
                )
                logger.info(f"✅ Background task completed for test execution: {test_execution_id}")
            except Exception as e:
                logger.error(f"❌ Background testing failed for {test_execution_id}: {e}", exc_info=True)
                # Update status to failed with detailed error
                try:
                    from datetime import datetime
                    await test_exec_repo.update(test_execution_id, {
                        'status': 'failed',
                        'current_phase': 'Failed',
                        'is_complete': True,
                        'error_message': str(e),
                        'completed_at': datetime.utcnow()
                    })
                    logger.info(f"Updated test execution {test_execution_id} with failure status")
                except Exception as update_error:
                    logger.error(f"Failed to update test execution status: {update_error}")
        
        background_tasks.add_task(run_testing)
        
        # Return immediately with test execution ID
        return StartTestingResponse(
            test_execution_id=test_execution_id,
            status="pending",
            message="API testing started successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start testing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start testing: {str(e)}"
        )


@router.get("/{test_execution_id}/progress", response_model=TestingProgressResponse)
async def get_testing_progress(test_execution_id: str):
    """
    Get real-time progress of API testing
    
    Poll this endpoint to monitor testing progress. Returns current status,
    phase, and metrics.
    """
    try:
        progress = await get_test_execution_progress(test_execution_id)
        
        return TestingProgressResponse(
            test_execution_id=progress['test_execution_id'],
            status=progress['status'],
            current_phase=progress['current_phase'],
            current_endpoint=progress.get('current_endpoint'),
            tested_endpoints=progress['tested_endpoints'],
            total_endpoints=progress['total_endpoints'],
            passed_tests=progress['passed_tests'],
            failed_tests=progress['failed_tests'],
            is_complete=progress['is_complete'],
            error_message=progress.get('error_message')
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get progress: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get progress: {str(e)}"
        )


@router.get("/{test_execution_id}/results")
async def get_testing_results(test_execution_id: str):
    """
    Get complete test results
    
    Returns comprehensive test results including:
    - Overall metrics (pass rate, execution time)
    - Dependency graph
    - Execution order
    - Individual test results per endpoint
    """
    try:
        results = await get_test_execution_results(test_execution_id)
        return results
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get results: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get results: {str(e)}"
        )


@router.post("/partners/{partner_id}/test-integration")
async def start_partner_integration_testing(
    partner_id: str,
    doc_id: str,
    tenant_id: Optional[str] = None
):
    """
    Simplified endpoint to start testing for a partner
    
    This is a convenience endpoint that combines partner ID and doc ID
    """
    request = StartTestingRequest(
        partner_id=partner_id,
        documentation_id=doc_id,
        tenant_id=tenant_id
    )
    
    return await start_api_testing(request, BackgroundTasks())

