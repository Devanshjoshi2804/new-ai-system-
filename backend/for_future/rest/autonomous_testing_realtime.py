"""
REST API endpoints for Autonomous Testing with Real-time Progress
"""
import logging
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import asyncio

from src.application.ai.understanding.comprehensive_api_analyzer import ComprehensiveAPIAnalyzer
from src.application.ai.testing.autonomous_test_generator import AutonomousTestGenerator
from src.application.ai.testing.intelligent_test_executor import IntelligentTestExecutor
from src.infrastructure.realtime.progress_tracker import get_progress_tracker, ProgressStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/autonomous-testing-realtime", tags=["Autonomous Testing Real-time"])

# In-memory storage
api_specifications = {}
generated_tests = {}


class StartAutonomousTestingRequest(BaseModel):
    """Request to start autonomous testing"""
    partner_id: str
    base_url: str
    auto_execute: bool = True  # Auto-execute tests after generation


class ProgressResponse(BaseModel):
    """Progress response"""
    operation_id: str
    status: str
    progress_percentage: int
    current_step: int
    total_steps: int
    steps: List[Dict[str, Any]]
    error: Optional[str] = None


@router.post("/start-full-pipeline")
async def start_full_autonomous_pipeline(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    partner_id: str = "default",
    base_url: str = "https://api.example.com",
    auto_execute: bool = True
):
    """
    Start full autonomous testing pipeline with real-time progress
    
    This endpoint:
    1. Analyzes documentation (with progress)
    2. Generates tests (with progress)
    3. Executes tests (with progress) - if auto_execute=True
    4. Returns operation_id for tracking progress
    
    The entire process runs in background with real-time progress updates
    """
    try:
        # Generate operation ID
        operation_id = f"auto_test_{partner_id}_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🚀 Starting full autonomous pipeline: {operation_id}")
        
        # Read file
        file_bytes = await file.read()
        
        # Start background task
        background_tasks.add_task(
            run_full_pipeline,
            operation_id=operation_id,
            partner_id=partner_id,
            file_bytes=file_bytes,
            base_url=base_url,
            auto_execute=auto_execute
        )
        
        return {
            'success': True,
            'operation_id': operation_id,
            'message': 'Autonomous testing pipeline started',
            'progress_endpoint': f'/api/autonomous-testing-realtime/progress/{operation_id}',
            'stream_endpoint': f'/api/autonomous-testing-realtime/progress-stream/{operation_id}'
        }
    
    except Exception as e:
        logger.error(f"❌ Error starting pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def run_full_pipeline(
    operation_id: str,
    partner_id: str,
    file_bytes: bytes,
    base_url: str,
    auto_execute: bool
):
    """
    Run full autonomous testing pipeline with progress tracking
    
    Args:
        operation_id: Operation identifier
        partner_id: Partner identifier
        file_bytes: Documentation file bytes
        base_url: API base URL
        auto_execute: Whether to auto-execute tests
    """
    tracker = get_progress_tracker()
    
    try:
        # Calculate total steps
        total_steps = 3 if auto_execute else 2  # analyze, generate, [execute]
        
        # Start tracking
        tracker.start_operation(
            operation_id=operation_id,
            operation_type="full_autonomous_pipeline",
            total_steps=total_steps,
            metadata={
                'partner_id': partner_id,
                'base_url': base_url,
                'auto_execute': auto_execute
            }
        )
        
        # Step 1: Analyze documentation
        tracker.update_step(
            operation_id=operation_id,
            step_name="Analyzing API Documentation",
            step_status=ProgressStatus.IN_PROGRESS,
            step_data={'message': 'Extracting text and analyzing endpoints...'}
        )
        
        analyzer = ComprehensiveAPIAnalyzer()
        api_spec = await analyzer.analyze_from_file(file_bytes=file_bytes)
        
        if not api_spec.get('success'):
            raise Exception(api_spec.get('error', 'Analysis failed'))
        
        # Store API spec
        api_specifications[partner_id] = api_spec
        
        tracker.update_step(
            operation_id=operation_id,
            step_name="Analyzing API Documentation",
            step_status=ProgressStatus.COMPLETED,
            step_data={
                'endpoints_found': api_spec['statistics']['endpoints_found'],
                'test_scenarios': api_spec['statistics']['test_scenarios']
            }
        )
        
        # Step 2: Generate tests
        tracker.update_step(
            operation_id=operation_id,
            step_name="Generating Comprehensive Tests",
            step_status=ProgressStatus.IN_PROGRESS,
            step_data={'message': 'AI agents are collaborating to create tests...'}
        )
        
        test_generator = AutonomousTestGenerator()
        test_results = await test_generator.generate_tests(
            api_spec=api_spec,
            test_scenarios=api_spec.get('test_scenarios', [])
        )
        
        # Store tests
        generated_tests[partner_id] = test_results
        
        test_cases = test_results.get('test_cases', [])
        
        tracker.update_step(
            operation_id=operation_id,
            step_name="Generating Comprehensive Tests",
            step_status=ProgressStatus.COMPLETED,
            step_data={
                'tests_generated': len(test_cases),
                'test_data_sets': len(test_results.get('test_data', {}))
            }
        )
        
        # Step 3: Execute tests (if auto_execute)
        execution_results = None
        if auto_execute and test_cases:
            tracker.update_step(
                operation_id=operation_id,
                step_name="Executing Tests with Self-Healing",
                step_status=ProgressStatus.IN_PROGRESS,
                step_data={'message': f'Running {len(test_cases)} tests...'}
            )
            
            executor = IntelligentTestExecutor()
            execution_results = await executor.execute_tests(
                test_cases=test_cases,
                auth_config=api_spec.get('auth_config', {}),
                base_url=base_url,
                max_retries=3
            )
            
            tracker.update_step(
                operation_id=operation_id,
                step_name="Executing Tests with Self-Healing",
                step_status=ProgressStatus.COMPLETED,
                step_data={
                    'total_tests': execution_results.get('total_tests', 0),
                    'passed': execution_results.get('passed', 0),
                    'failed': execution_results.get('failed', 0),
                    'pass_rate': execution_results.get('pass_rate', 0)
                }
            )
        
        # Complete operation
        tracker.complete_operation(
            operation_id=operation_id,
            result={
                'api_spec': {
                    'endpoints_found': api_spec['statistics']['endpoints_found'],
                    'test_scenarios': api_spec['statistics']['test_scenarios']
                },
                'tests': {
                    'generated': len(test_cases)
                },
                'execution': execution_results if execution_results else None
            }
        )
        
        logger.info(f"✅ Full pipeline completed: {operation_id}")
    
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {operation_id} - {e}", exc_info=True)
        tracker.fail_operation(operation_id=operation_id, error=str(e))


@router.get("/progress/{operation_id}", response_model=ProgressResponse)
async def get_progress(operation_id: str):
    """
    Get current progress of an operation
    
    Args:
        operation_id: Operation identifier
        
    Returns:
        Current progress
    """
    try:
        tracker = get_progress_tracker()
        progress = tracker.get_progress(operation_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail=f"Operation {operation_id} not found")
        
        return ProgressResponse(
            operation_id=progress['operation_id'],
            status=progress['status'],
            progress_percentage=progress['progress_percentage'],
            current_step=progress['current_step'],
            total_steps=progress['total_steps'],
            steps=progress['steps'],
            error=progress.get('error')
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress-stream/{operation_id}")
async def stream_progress(operation_id: str):
    """
    Stream progress updates using Server-Sent Events (SSE)
    
    Args:
        operation_id: Operation identifier
        
    Returns:
        SSE stream of progress updates
    """
    async def event_generator():
        """Generate SSE events"""
        tracker = get_progress_tracker()
        
        # Check if operation exists
        progress = tracker.get_progress(operation_id)
        if not progress:
            yield f"data: {json.dumps({'error': 'Operation not found'})}\n\n"
            return
        
        # Send initial state
        yield f"data: {json.dumps(progress)}\n\n"
        
        # Subscribe to updates
        update_queue = asyncio.Queue()
        
        def callback(updated_progress):
            """Callback for progress updates"""
            try:
                asyncio.create_task(update_queue.put(updated_progress))
            except:
                pass
        
        tracker.subscribe(operation_id, callback)
        
        try:
            # Stream updates until operation completes
            while True:
                try:
                    # Wait for update with timeout
                    updated_progress = await asyncio.wait_for(
                        update_queue.get(),
                        timeout=30.0
                    )
                    
                    yield f"data: {json.dumps(updated_progress)}\n\n"
                    
                    # Stop if operation completed or failed
                    if updated_progress['status'] in [ProgressStatus.COMPLETED, ProgressStatus.FAILED]:
                        break
                
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
        
        finally:
            tracker.unsubscribe(operation_id, callback)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/operations")
async def list_operations():
    """
    List all tracked operations
    
    Returns:
        List of operations with their status
    """
    try:
        tracker = get_progress_tracker()
        
        operations = []
        for op_id, operation in tracker.operations.items():
            operations.append({
                'operation_id': op_id,
                'operation_type': operation['operation_type'],
                'status': operation['status'],
                'progress_percentage': operation['progress_percentage'],
                'started_at': operation['started_at'],
                'completed_at': operation.get('completed_at')
            })
        
        return {
            'success': True,
            'operations': operations,
            'total': len(operations)
        }
    
    except Exception as e:
        logger.error(f"❌ Error listing operations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/operation/{operation_id}")
async def cancel_operation(operation_id: str):
    """
    Cancel an operation
    
    Args:
        operation_id: Operation identifier
    """
    try:
        tracker = get_progress_tracker()
        progress = tracker.get_progress(operation_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail=f"Operation {operation_id} not found")
        
        # Mark as cancelled
        progress['status'] = ProgressStatus.CANCELLED
        progress['completed_at'] = datetime.utcnow().isoformat()
        
        return {
            'success': True,
            'message': f'Operation {operation_id} cancelled'
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error cancelling operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
