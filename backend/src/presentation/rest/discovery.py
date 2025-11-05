"""
Discovery REST Endpoints
API endpoints for autonomous API discovery
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime
import asyncio

from src.application.ai.discovery.api_explorer import APIExplorer
from src.application.ai.discovery.auth_detector import AuthDetector
from src.application.ai.discovery.schema_inferencer import SchemaInferencer
from src.application.ai.discovery.relationship_analyzer import RelationshipAnalyzer
from src.domain.entities.discovery_result import (
    DiscoveryResultEntity,
    DiscoveredEndpoint,
    AuthConfiguration
)
from src.infrastructure.database.mongodb.connection import MongoDBConnection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["Discovery"])


# Request/Response Models
class DiscoveryRequest(BaseModel):
    """Request to start API discovery"""
    partner_id: str = Field(..., description="Partner identifier")
    partner_name: str = Field(..., description="Partner name")
    minimal_info: str = Field(..., description="Base URL or API snippet")
    auth_token: Optional[str] = Field(None, description="Optional test auth token")
    sample_endpoint: Optional[str] = Field(None, description="Optional sample endpoint")


class DiscoveryResponse(BaseModel):
    """Response for discovery request"""
    discovery_id: str
    status: str
    message: str


class DiscoveryStatusResponse(BaseModel):
    """Status response"""
    discovery_id: str
    status: str
    progress: float  # 0.0 to 1.0
    current_step: str
    endpoints_found: int
    errors: List[str]
    completed_at: Optional[datetime] = None


class DiscoveryResultResponse(BaseModel):
    """Complete discovery results"""
    discovery_id: str
    partner_id: str
    base_url: str
    status: str

    endpoints: List[Dict[str, Any]]
    auth_config: Optional[Dict[str, Any]]
    documentation_url: Optional[str]
    api_version: Optional[str]
    schemas: Dict[str, Any]
    dependency_graph: Dict[str, Any]
    workflows: List[Dict[str, Any]]

    discovery_time: float
    errors: List[str]
    created_at: datetime


# In-memory storage for progress tracking (in production, use Redis)
_discovery_progress = {}


@router.post("/explore", response_model=DiscoveryResponse)
async def start_discovery(
    request: DiscoveryRequest,
    background_tasks: BackgroundTasks
):
    """
    Start autonomous API discovery

    Process:
    1. Validate base URL
    2. Discover API endpoints
    3. Detect authentication
    4. Infer schemas
    5. Analyze relationships
    6. Store results

    Returns immediately with discovery_id for status tracking
    """
    try:
        logger.info(f"[START] Discovery request for {request.partner_name}: {request.minimal_info}")

        # Create discovery result entity
        discovery_result = DiscoveryResultEntity(
            partner_id=request.partner_id,
            base_url=request.minimal_info,  # Will be validated
            status="in_progress"
        )

        # Initialize progress tracking
        discovery_id = discovery_result.id
        _discovery_progress[discovery_id] = {
            'status': 'in_progress',
            'progress': 0.0,
            'current_step': 'Starting discovery...',
            'endpoints_found': 0,
            'errors': []
        }

        # Start discovery in background
        background_tasks.add_task(
            run_discovery_pipeline,
            discovery_id,
            request
        )

        return DiscoveryResponse(
            discovery_id=discovery_id,
            status="started",
            message=f"Discovery started for {request.partner_name}"
        )

    except Exception as e:
        logger.error(f"[ERROR] Failed to start discovery: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{discovery_id}", response_model=DiscoveryStatusResponse)
async def get_discovery_status(discovery_id: str):
    """Get current status of discovery process"""
    try:
        # Check in-memory progress first
        if discovery_id in _discovery_progress:
            progress = _discovery_progress[discovery_id]
            return DiscoveryStatusResponse(
                discovery_id=discovery_id,
                status=progress['status'],
                progress=progress['progress'],
                current_step=progress['current_step'],
                endpoints_found=progress['endpoints_found'],
                errors=progress['errors']
            )

        # Check database
        db = MongoDBConnection.get_database()
        result = await db.discovery_results.find_one({"id": discovery_id})

        if not result:
            raise HTTPException(status_code=404, detail="Discovery not found")

        return DiscoveryStatusResponse(
            discovery_id=discovery_id,
            status=result.get('status', 'unknown'),
            progress=1.0 if result.get('status') == 'completed' else 0.0,
            current_step='Completed' if result.get('status') == 'completed' else 'Unknown',
            endpoints_found=len(result.get('endpoints', [])),
            errors=result.get('errors', []),
            completed_at=result.get('updated_at')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{discovery_id}", response_model=DiscoveryResultResponse)
async def get_discovery_results(discovery_id: str):
    """Get complete discovery results"""
    try:
        db = MongoDBConnection.get_database()
        result = await db.discovery_results.find_one({"id": discovery_id})

        if not result:
            raise HTTPException(status_code=404, detail="Discovery results not found")

        return DiscoveryResultResponse(
            discovery_id=discovery_id,
            partner_id=result['partner_id'],
            base_url=result['base_url'],
            status=result['status'],
            endpoints=result.get('endpoints', []),
            auth_config=result.get('auth_config'),
            documentation_url=result.get('documentation_url'),
            api_version=result.get('api_version'),
            schemas=result.get('schemas', {}),
            dependency_graph=result.get('dependency_graph', {}),
            workflows=result.get('workflows', []),
            discovery_time=result.get('discovery_time', 0.0),
            errors=result.get('errors', []),
            created_at=result['created_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to get results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_discovery_pipeline(
    discovery_id: str,
    request: DiscoveryRequest
):
    """
    Background task: Run complete discovery pipeline
    """
    try:
        logger.info(f"[PIPELINE] Starting discovery pipeline: {discovery_id}")

        # Update progress
        def update_progress(step: str, progress: float):
            _discovery_progress[discovery_id].update({
                'current_step': step,
                'progress': progress
            })

        # Step 1: API Explorer
        update_progress("Exploring API endpoints...", 0.1)
        async with APIExplorer() as explorer:
            discovery_result = await explorer.explore(
                request.minimal_info,
                request.auth_token
            )

        endpoints_data = [
            {
                'path': ep['path'],
                'method': ep['method'],
                'summary': ep.get('summary', ''),
                'description': ep.get('description', ''),
                'parameters': ep.get('parameters', []),
                'auth_required': ep.get('auth_required', False),
                'source': ep.get('source', 'unknown')
            }
            for ep in discovery_result.endpoints
        ]

        update_progress(f"Found {len(endpoints_data)} endpoints", 0.3)
        _discovery_progress[discovery_id]['endpoints_found'] = len(endpoints_data)

        # Step 2: Auth Detector
        update_progress("Detecting authentication...", 0.4)
        async with AuthDetector() as auth_detector:
            auth_result = await auth_detector.detect(
                discovery_result.base_url,
                sample_endpoint=request.sample_endpoint
            )

        auth_config_data = {
            'auth_type': auth_result.auth_type.value if hasattr(auth_result.auth_type, 'value') else str(auth_result.auth_type),
            'header_name': auth_result.header_name,
            'token_location': auth_result.token_location,
            'scheme': auth_result.scheme,
            'login_endpoint': auth_result.login_endpoint,
            'token_format': auth_result.token_format,
            'confidence': auth_result.confidence,
            'test_passed': auth_result.test_passed
        }

        update_progress("Authentication detected", 0.5)

        # Step 3: Schema Inferencer
        update_progress("Inferring schemas...", 0.6)
        async with SchemaInferencer() as schema_inferencer:
            schemas = await schema_inferencer.infer_schemas(
                discovery_result.base_url,
                discovery_result.endpoints,
                request.auth_token
            )

        update_progress(f"Inferred {len(schemas)} schemas", 0.7)

        # Step 4: Relationship Analyzer
        update_progress("Analyzing endpoint relationships...", 0.8)
        async with RelationshipAnalyzer() as rel_analyzer:
            dependency_graph = await rel_analyzer.analyze(
                discovery_result.base_url,
                discovery_result.endpoints,
                request.auth_token
            )

        # Generate workflows
        workflow = dependency_graph.generate_workflow("full")

        update_progress("Analyzing relationships complete", 0.9)

        # Step 5: Store results
        update_progress("Saving results...", 0.95)

        db = MongoDBConnection.get_database()
        await db.discovery_results.insert_one({
            'id': discovery_id,
            'partner_id': request.partner_id,
            'base_url': discovery_result.base_url,
            'status': 'completed',
            'endpoints': endpoints_data,
            'auth_config': auth_config_data,
            'documentation_url': discovery_result.documentation_url,
            'api_version': discovery_result.api_version,
            'schemas': schemas,
            'dependency_graph': dependency_graph.to_dict(),
            'workflows': [workflow],
            'discovery_time': discovery_result.discovery_time,
            'errors': discovery_result.errors,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })

        # Final update
        _discovery_progress[discovery_id].update({
            'status': 'completed',
            'progress': 1.0,
            'current_step': 'Discovery complete!'
        })

        logger.info(f"[COMPLETE] Discovery pipeline finished: {discovery_id}")

    except Exception as e:
        logger.error(f"[ERROR] Discovery pipeline failed: {e}", exc_info=True)

        _discovery_progress[discovery_id].update({
            'status': 'failed',
            'current_step': f'Error: {str(e)}',
            'errors': [str(e)]
        })

        # Try to save error state
        try:
            db = MongoDBConnection.get_database()
            await db.discovery_results.update_one(
                {'id': discovery_id},
                {'$set': {
                    'status': 'failed',
                    'errors': [str(e)],
                    'updated_at': datetime.utcnow()
                }}
            )
        except:
            pass


@router.get("/health")
async def health_check():
    """Health check for discovery service"""
    return {
        "status": "healthy",
        "service": "discovery",
        "features": [
            "API exploration from minimal info",
            "Multi-strategy endpoint discovery",
            "Automatic authentication detection",
            "Schema inference from responses",
            "Dependency graph analysis",
            "Workflow generation"
        ]
    }
