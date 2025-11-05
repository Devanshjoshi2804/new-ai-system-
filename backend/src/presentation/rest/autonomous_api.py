"""
Autonomous Orchestration REST API

Provides HTTP endpoints for autonomous API integration operations.

Endpoints:
- POST /api/autonomous/onboard - Trigger autonomous onboarding
- POST /api/autonomous/test - Test specific endpoint
- POST /api/autonomous/fix - Fix failing endpoint
- GET /api/autonomous/status/{operation_id} - Get operation status
- POST /api/autonomous/cancel/{operation_id} - Cancel operation
- GET /api/autonomous/metrics - Get performance metrics
- GET /api/autonomous/models - Get model registry info
- POST /api/autonomous/models/promote - Promote model
- POST /api/autonomous/retrain - Trigger model retraining
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/autonomous", tags=["autonomous"])


# Request/Response Models

class OnboardRequest(BaseModel):
    """Request to trigger autonomous onboarding"""
    minimal_info: str = Field(..., description="Minimal API information (URL, docs link, etc.)")
    auth_token: Optional[str] = Field(None, description="Optional authentication token")
    base_url: Optional[str] = Field(None, description="Optional base URL for API")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class TestEndpointRequest(BaseModel):
    """Request to test a specific endpoint"""
    endpoint_url: str
    method: str = "GET"
    payload: Optional[Dict[str, Any]] = None
    auth_token: Optional[str] = None
    base_url: Optional[str] = None


class FixEndpointRequest(BaseModel):
    """Request to fix a failing endpoint"""
    endpoint_url: str
    method: str
    error_response: Dict[str, Any]
    original_payload: Dict[str, Any]
    auth_token: Optional[str] = None


class PromoteModelRequest(BaseModel):
    """Request to promote a model"""
    model_id: str
    target_status: str  # 'testing', 'staging', 'production', 'retired'


class RetrainRequest(BaseModel):
    """Request to trigger model retraining"""
    model_type: str  # 'endpoint_classifier', 'payload_generator', etc.
    force: bool = False


# Global instances (initialized by main app)
_orchestrator = None
_hybrid_predictor = None
_learning_loop = None
_performance_monitor = None
_model_registry = None


def init_orchestration_api(
    orchestrator=None,
    hybrid_predictor=None,
    learning_loop=None,
    performance_monitor=None,
    model_registry=None
):
    """
    Initialize API with component instances

    This should be called from main.py on startup
    """
    global _orchestrator, _hybrid_predictor, _learning_loop, _performance_monitor, _model_registry

    _orchestrator = orchestrator
    _hybrid_predictor = hybrid_predictor
    _learning_loop = learning_loop
    _performance_monitor = performance_monitor
    _model_registry = model_registry

    logger.info("[AUTONOMOUS_API] Initialized with components")


# Endpoints

@router.post("/onboard")
async def autonomous_onboard(
    request: OnboardRequest,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Trigger autonomous API onboarding

    Performs complete end-to-end onboarding from minimal information:
    1. Discovery - Find all API endpoints
    2. ML Enhancement - Classify and understand endpoints
    3. Testing - Execute tests with auto-fixing
    4. Learning - Store results for improvement

    Returns operation ID for status tracking.
    """
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")

    try:
        logger.info(f"[AUTONOMOUS_API] Starting onboarding: {request.minimal_info[:100]}...")

        # Start autonomous onboarding (async)
        result = await _orchestrator.autonomous_onboard(
            minimal_info=request.minimal_info,
            auth_token=request.auth_token,
            base_url=request.base_url,
            additional_context=request.additional_context
        )

        return JSONResponse(
            status_code=202,  # Accepted
            content={
                'operation_id': result.operation_id,
                'status': result.status.value,
                'message': 'Autonomous onboarding started',
                'result': result.to_dict()
            }
        )

    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Onboarding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_endpoint(request: TestEndpointRequest) -> JSONResponse:
    """
    Test a specific API endpoint

    Uses the execution engine to test a single endpoint with
    retry logic and auto-fixing.
    """
    if not _hybrid_predictor:
        raise HTTPException(status_code=503, detail="Hybrid predictor not available")

    try:
        # Import here to avoid circular dependency
        from backend.src.application.ai.orchestration import (
            ExecutionEngine,
            EndpointInfo,
            ExecutionContext,
            AuthConfiguration,
            DependencyGraph
        )

        logger.info(f"[AUTONOMOUS_API] Testing endpoint: {request.method} {request.endpoint_url}")

        # Create endpoint info
        endpoint = EndpointInfo(
            id="test_endpoint",
            url=request.endpoint_url,
            method=request.method
        )

        # Create execution context
        auth_config = AuthConfiguration(
            auth_type='bearer' if request.auth_token else 'none',
            credentials={'token': request.auth_token} if request.auth_token else {}
        )

        context = ExecutionContext(
            auth_config=auth_config,
            base_url=request.base_url or "",
            max_retries=3,
            enable_auto_fix=True
        )

        # Create execution engine
        engine = ExecutionEngine(hybrid_predictor=_hybrid_predictor)

        # Execute test
        result = await engine._execute_single_test(
            endpoint=endpoint,
            payload=request.payload or {},
            context=context
        )

        return JSONResponse(content={
            'endpoint': request.endpoint_url,
            'method': request.method,
            'status': result.status.value,
            'response': result.response,
            'error': result.error,
            'latency_ms': result.latency_ms,
            'retry_count': result.retry_count,
            'fixed': result.fixed
        })

    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix")
async def fix_endpoint(request: FixEndpointRequest) -> JSONResponse:
    """
    Fix a failing endpoint

    Uses the hybrid predictor to suggest fixes for a failing endpoint.
    """
    if not _hybrid_predictor:
        raise HTTPException(status_code=503, detail="Hybrid predictor not available")

    try:
        logger.info(f"[AUTONOMOUS_API] Fixing endpoint: {request.method} {request.endpoint_url}")

        # Call hybrid predictor to fix error
        fix_result = await _hybrid_predictor.fix_error(
            endpoint_url=request.endpoint_url,
            error_response=request.error_response,
            original_payload=request.original_payload
        )

        return JSONResponse(content={
            'endpoint': request.endpoint_url,
            'method': request.method,
            'fixed_payload': fix_result.prediction,
            'confidence': fix_result.confidence,
            'tier': fix_result.tier.value,
            'latency_ms': fix_result.latency_ms,
            'metadata': fix_result.metadata
        })

    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Fix error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{operation_id}")
async def get_operation_status(
    operation_id: str = Path(..., description="Operation ID to check")
) -> JSONResponse:
    """
    Get status of an operation

    Returns current status and progress for an operation.
    """
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")

    try:
        status = await _orchestrator.get_operation_status(operation_id)

        if not status:
            raise HTTPException(status_code=404, detail="Operation not found")

        return JSONResponse(content=status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel/{operation_id}")
async def cancel_operation(
    operation_id: str = Path(..., description="Operation ID to cancel")
) -> JSONResponse:
    """Cancel a running operation"""
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")

    try:
        success = await _orchestrator.cancel_operation(operation_id)

        if not success:
            raise HTTPException(status_code=404, detail="Operation not found or already completed")

        return JSONResponse(content={
            'operation_id': operation_id,
            'cancelled': True
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Cancel error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_metrics(
    time_range_minutes: int = Query(60, description="Time range for metrics in minutes")
) -> JSONResponse:
    """
    Get performance metrics

    Returns current and historical performance metrics including:
    - Cache/ML/AI hit rates
    - Latency statistics
    - Cost calculations
    - Error rates
    """
    try:
        metrics = {}

        # Get orchestrator metrics
        if _orchestrator:
            metrics['orchestrator'] = await _orchestrator.get_metrics()

        # Get hybrid predictor metrics
        if _hybrid_predictor:
            metrics['hybrid_predictor'] = await _hybrid_predictor.get_metrics()

        # Get performance monitor metrics
        if _performance_monitor:
            metrics['performance'] = {
                'current': await _performance_monitor.get_current_metrics(),
                'historical': await _performance_monitor.get_historical_metrics(time_range_minutes),
                'alerts': await _performance_monitor.get_alerts(limit=10)
            }

        # Get learning loop metrics
        if _learning_loop:
            metrics['learning'] = await _learning_loop.get_metrics()

        return JSONResponse(content=metrics)

    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/report")
async def get_performance_report(
    time_range_minutes: int = Query(60, description="Time range for report")
) -> JSONResponse:
    """
    Get detailed performance report

    Generates a comprehensive report with trends and analysis.
    """
    if not _performance_monitor:
        raise HTTPException(status_code=503, detail="Performance monitor not available")

    try:
        report = await _performance_monitor.generate_report(time_range_minutes)
        return JSONResponse(content=report)

    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_models(
    model_type: Optional[str] = Query(None, description="Filter by model type"),
    status: Optional[str] = Query(None, description="Filter by status")
) -> JSONResponse:
    """
    Get registered models

    Returns information about registered ML models.
    """
    if not _model_registry:
        raise HTTPException(status_code=503, detail="Model registry not available")

    try:
        from backend.src.application.ai.orchestration.model_registry import ModelStatus

        # Get models
        if model_type:
            status_enum = ModelStatus(status) if status else None
            models = _model_registry.get_models_by_type(model_type, status=status_enum)
        else:
            models = list(_model_registry.models.values())

        return JSONResponse(content={
            'models': [model.to_dict() for model in models],
            'total': len(models)
        })

    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}")
async def get_model(model_id: str) -> JSONResponse:
    """Get specific model information"""
    if not _model_registry:
        raise HTTPException(status_code=503, detail="Model registry not available")

    try:
        model = _model_registry.get_model(model_id)

        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        return JSONResponse(content=model.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Model error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/promote")
async def promote_model(request: PromoteModelRequest) -> JSONResponse:
    """
    Promote model to new status

    Moves a model through the deployment pipeline:
    training -> testing -> staging -> production
    """
    if not _model_registry:
        raise HTTPException(status_code=503, detail="Model registry not available")

    try:
        from backend.src.application.ai.orchestration.model_registry import ModelStatus

        target_status = ModelStatus(request.target_status)

        success = _model_registry.promote_model(request.model_id, target_status)

        if not success:
            raise HTTPException(status_code=400, detail="Invalid promotion")

        return JSONResponse(content={
            'model_id': request.model_id,
            'new_status': target_status.value,
            'promoted': True
        })

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Promote error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/rollback")
async def rollback_model(
    model_type: str = Query(..., description="Type of model to rollback")
) -> JSONResponse:
    """
    Rollback to previous production model

    Reverts to the previously deployed production model.
    """
    if not _model_registry:
        raise HTTPException(status_code=503, detail="Model registry not available")

    try:
        success = _model_registry.rollback_model(model_type)

        if not success:
            raise HTTPException(status_code=400, detail="Rollback failed")

        return JSONResponse(content={
            'model_type': model_type,
            'rolled_back': True
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Rollback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrain")
async def trigger_retrain(request: RetrainRequest) -> JSONResponse:
    """
    Trigger model retraining

    Initiates retraining for a specific model type using
    accumulated learning data.
    """
    if not _learning_loop:
        raise HTTPException(status_code=503, detail="Learning loop not available")

    try:
        logger.info(f"[AUTONOMOUS_API] Triggering retrain: {request.model_type}")

        # Get training data
        training_data = await _learning_loop.get_training_data()

        if not training_data and not request.force:
            raise HTTPException(
                status_code=400,
                detail="No training data available. Use force=true to retrain anyway."
            )

        # TODO: Implement actual retraining logic
        # For now, just log and return success

        return JSONResponse(content={
            'model_type': request.model_type,
            'training_data_size': len(training_data),
            'retraining_triggered': True,
            'message': 'Retraining started (placeholder)'
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Retrain error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/patterns")
async def get_learning_patterns(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, description="Maximum number of patterns")
) -> JSONResponse:
    """
    Get learned API patterns

    Returns patterns learned from successful test executions.
    """
    if not _learning_loop:
        raise HTTPException(status_code=503, detail="Learning loop not available")

    try:
        patterns = await _learning_loop.get_training_data(category=category, limit=limit)

        return JSONResponse(content={
            'patterns': patterns,
            'total': len(patterns)
        })

    except Exception as e:
        logger.error(f"[AUTONOMOUS_API] Patterns error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint

    Returns status of all orchestration components.
    """
    health = {
        'status': 'healthy',
        'components': {
            'orchestrator': _orchestrator is not None,
            'hybrid_predictor': _hybrid_predictor is not None,
            'learning_loop': _learning_loop is not None,
            'performance_monitor': _performance_monitor is not None,
            'model_registry': _model_registry is not None
        },
        'timestamp': datetime.utcnow().isoformat()
    }

    # Set status to degraded if any component is missing
    if not all(health['components'].values()):
        health['status'] = 'degraded'

    return JSONResponse(content=health)
