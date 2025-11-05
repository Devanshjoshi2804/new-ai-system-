"""
REST API endpoints for Autonomous Testing System
"""
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.application.ai.understanding.comprehensive_api_analyzer import ComprehensiveAPIAnalyzer
from src.application.ai.testing.autonomous_test_generator import AutonomousTestGenerator
from src.application.ai.testing.intelligent_test_executor import IntelligentTestExecutor
from src.application.ai.testing.error_analyzer import ErrorAnalyzer
from src.application.ai.understanding.schema_inferrer import SchemaInferrer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/autonomous-testing", tags=["Autonomous Testing"])


# Request/Response Models
class AnalyzeDocumentationRequest(BaseModel):
    """Request model for documentation analysis"""
    partner_id: str
    file_url: Optional[str] = None


class AnalyzeDocumentationResponse(BaseModel):
    """Response model for documentation analysis"""
    success: bool
    endpoints_found: int
    test_scenarios_generated: int
    analysis: Dict[str, Any]
    error: Optional[str] = None


class GenerateTestsRequest(BaseModel):
    """Request model for test generation"""
    partner_id: str


class GenerateTestsResponse(BaseModel):
    """Response model for test generation"""
    success: bool
    tests_generated: int
    tests: List[Dict[str, Any]]
    test_data: Dict[str, Any]
    coverage: Dict[str, Any]
    error: Optional[str] = None


class RunTestsRequest(BaseModel):
    """Request model for running tests"""
    partner_id: str
    base_url: str
    max_retries: int = 3


class RunTestsResponse(BaseModel):
    """Response model for test execution"""
    success: bool
    total_tests: int
    passed: int
    failed: int
    errors: int
    pass_rate: float
    results: List[Dict[str, Any]]
    improvements: Dict[str, Any]
    error: Optional[str] = None


class ExecuteCommandRequest(BaseModel):
    """Request model for natural language command execution"""
    partner_id: str
    command: str
    base_url: str


class ExecuteCommandResponse(BaseModel):
    """Response model for command execution"""
    success: bool
    response: str
    api_calls_made: int
    details: List[Dict[str, Any]]
    error: Optional[str] = None


# In-memory storage (replace with database in production)
api_specifications = {}
generated_tests = {}


@router.post("/analyze-documentation", response_model=AnalyzeDocumentationResponse)
async def analyze_documentation(
    file: UploadFile = File(...),
    partner_id: str = "default"
):
    """
    Analyze API documentation and extract everything
    Returns comprehensive API specification
    
    This endpoint:
    1. Extracts text from PDF/document using OCR
    2. Analyzes with LangGraph to extract endpoints, auth, schemas, etc.
    3. Generates test scenarios automatically
    4. Stores results for later use
    """
    try:
        logger.info(f"📄 Analyzing documentation for partner: {partner_id}")
        
        # Read file
        file_bytes = await file.read()
        
        # Analyze using comprehensive analyzer
        analyzer = ComprehensiveAPIAnalyzer()
        result = await analyzer.analyze_from_file(file_bytes=file_bytes)
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Analysis failed'))
        
        # Store API specification
        api_specifications[partner_id] = result
        
        logger.info(f"✅ Analysis complete for {partner_id}")
        logger.info(f"📊 Found {result['statistics']['endpoints_found']} endpoints")
        
        return AnalyzeDocumentationResponse(
            success=True,
            endpoints_found=result['statistics']['endpoints_found'],
            test_scenarios_generated=result['statistics']['test_scenarios'],
            analysis=result
        )
    
    except Exception as e:
        logger.error(f"❌ Error analyzing documentation: {e}", exc_info=True)
        return AnalyzeDocumentationResponse(
            success=False,
            endpoints_found=0,
            test_scenarios_generated=0,
            analysis={},
            error=str(e)
        )


@router.post("/generate-tests", response_model=GenerateTestsResponse)
async def generate_tests(request: GenerateTestsRequest):
    """
    Generate comprehensive tests for partner API
    Uses CrewAI multi-agent system
    
    This endpoint:
    1. Retrieves API specification
    2. Uses CrewAI agents to generate comprehensive tests
    3. Generates test data for all scenarios
    4. Validates test coverage
    5. Stores tests for execution
    """
    try:
        partner_id = request.partner_id
        logger.info(f"🤖 Generating tests for partner: {partner_id}")
        
        # Get API specification
        api_spec = api_specifications.get(partner_id)
        if not api_spec:
            raise HTTPException(status_code=404, detail=f"No API specification found for partner {partner_id}")
        
        # Generate tests using CrewAI
        test_generator = AutonomousTestGenerator()
        test_results = await test_generator.generate_tests(
            api_spec=api_spec,
            test_scenarios=api_spec.get('test_scenarios', [])
        )
        
        if test_results.get('error'):
            raise HTTPException(status_code=500, detail=test_results['error'])
        
        # Store generated tests
        generated_tests[partner_id] = test_results
        
        test_cases = test_results.get('test_cases', [])
        logger.info(f"✅ Generated {len(test_cases)} tests for {partner_id}")
        
        return GenerateTestsResponse(
            success=True,
            tests_generated=len(test_cases),
            tests=test_cases,
            test_data=test_results.get('test_data', {}),
            coverage=test_results.get('coverage', {}),
            error=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating tests: {e}", exc_info=True)
        return GenerateTestsResponse(
            success=False,
            tests_generated=0,
            tests=[],
            test_data={},
            coverage={},
            error=str(e)
        )


@router.post("/run-tests", response_model=RunTestsResponse)
async def run_tests(request: RunTestsRequest):
    """
    Run all tests with self-healing
    Returns results with AI analysis
    
    This endpoint:
    1. Retrieves generated tests
    2. Executes tests using LangGraph with self-healing
    3. Analyzes failures with AI
    4. Suggests improvements
    5. Returns comprehensive results
    """
    try:
        partner_id = request.partner_id
        logger.info(f"🚀 Running tests for partner: {partner_id}")
        
        # Get tests
        test_data = generated_tests.get(partner_id)
        if not test_data:
            raise HTTPException(status_code=404, detail=f"No tests found for partner {partner_id}")
        
        test_cases = test_data.get('test_cases', [])
        if not test_cases:
            raise HTTPException(status_code=400, detail="No test cases to execute")
        
        # Get API specification for auth config
        api_spec = api_specifications.get(partner_id)
        if not api_spec:
            raise HTTPException(status_code=404, detail=f"No API specification found for partner {partner_id}")
        
        auth_config = api_spec.get('auth_config', {})
        
        # Execute tests with self-healing
        executor = IntelligentTestExecutor()
        execution_result = await executor.execute_tests(
            test_cases=test_cases,
            auth_config=auth_config,
            base_url=request.base_url,
            max_retries=request.max_retries
        )
        
        if execution_result.get('error'):
            raise HTTPException(status_code=500, detail=execution_result['error'])
        
        # Analyze results and suggest improvements
        error_analyzer = ErrorAnalyzer()
        improvements = await error_analyzer.suggest_test_improvements(
            test_results=execution_result.get('test_results', [])
        )
        
        logger.info(f"✅ Test execution complete for {partner_id}")
        logger.info(f"📊 Results: {execution_result['passed']}/{execution_result['total_tests']} passed")
        
        return RunTestsResponse(
            success=execution_result.get('success', False),
            total_tests=execution_result.get('total_tests', 0),
            passed=execution_result.get('passed', 0),
            failed=execution_result.get('failed', 0),
            errors=execution_result.get('errors', 0),
            pass_rate=execution_result.get('pass_rate', 0),
            results=execution_result.get('test_results', []),
            improvements=improvements,
            error=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error running tests: {e}", exc_info=True)
        return RunTestsResponse(
            success=False,
            total_tests=0,
            passed=0,
            failed=0,
            errors=0,
            pass_rate=0,
            results=[],
            improvements={},
            error=str(e)
        )


@router.post("/execute-command", response_model=ExecuteCommandResponse)
async def execute_command(request: ExecuteCommandRequest):
    """
    Execute natural language command
    AI figures out what to do and does it
    
    This endpoint:
    1. Understands user intent from natural language
    2. Plans execution steps
    3. Executes API calls autonomously
    4. Handles errors and retries
    5. Returns natural language response
    
    Example commands:
    - "Create a booking from Mumbai to Delhi"
    - "Get all my orders"
    - "Cancel booking #12345"
    - "Check shipment status"
    """
    try:
        partner_id = request.partner_id
        command = request.command
        
        logger.info(f"💬 Executing command for {partner_id}: {command}")
        
        # Get API specification
        api_spec = api_specifications.get(partner_id)
        if not api_spec:
            raise HTTPException(status_code=404, detail=f"No API specification found for partner {partner_id}")
        
        # Execute autonomously
        from src.application.ai.execution.autonomous_executor import AutonomousExecutor
        
        executor = AutonomousExecutor()
        result = await executor.execute_command(
            user_message=command,
            api_spec=api_spec,
            base_url=request.base_url,
            context={}
        )
        
        # Learn from success (Phase 5 - will be implemented)
        if result.get('success'):
            logger.info("✅ Command executed successfully")
            # TODO: Store successful pattern in Mem0
        
        return ExecuteCommandResponse(
            success=result.get('success', False),
            response=result.get('response', ''),
            api_calls_made=result.get('api_calls_made', 0),
            details=result.get('details', []),
            error=result.get('error')
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error executing command: {e}", exc_info=True)
        return ExecuteCommandResponse(
            success=False,
            response="I encountered an error while processing your command.",
            api_calls_made=0,
            details=[],
            error=str(e)
        )


@router.get("/api-spec/{partner_id}")
async def get_api_specification(partner_id: str):
    """
    Get stored API specification for partner
    """
    try:
        api_spec = api_specifications.get(partner_id)
        if not api_spec:
            raise HTTPException(status_code=404, detail=f"No API specification found for partner {partner_id}")
        
        return {
            'success': True,
            'partner_id': partner_id,
            'api_spec': api_spec
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving API spec: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests/{partner_id}")
async def get_generated_tests(partner_id: str):
    """
    Get generated tests for partner
    """
    try:
        tests = generated_tests.get(partner_id)
        if not tests:
            raise HTTPException(status_code=404, detail=f"No tests found for partner {partner_id}")
        
        return {
            'success': True,
            'partner_id': partner_id,
            'tests': tests
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-error")
async def analyze_error(
    request: Dict[str, Any],
    response: Dict[str, Any],
    partner_id: Optional[str] = None
):
    """
    Analyze a specific API error
    Returns detailed analysis and suggested fixes
    """
    try:
        logger.info("🔍 Analyzing specific error...")
        
        # Get API spec if partner_id provided
        api_spec = None
        if partner_id:
            api_spec = api_specifications.get(partner_id)
        
        # Analyze error
        error_analyzer = ErrorAnalyzer()
        analysis = await error_analyzer.analyze_error(
            request=request,
            response=response,
            api_spec=api_spec
        )
        
        # Generate user-friendly explanation
        explanation = await error_analyzer.explain_error_to_user(
            error=analysis,
            user_friendly=True
        )
        
        return {
            'success': True,
            'analysis': analysis,
            'explanation': explanation
        }
    
    except Exception as e:
        logger.error(f"❌ Error analyzing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/partner/{partner_id}")
async def delete_partner_data(partner_id: str):
    """
    Delete all data for a partner
    """
    try:
        logger.info(f"🗑️ Deleting data for partner: {partner_id}")
        
        # Remove from storage
        if partner_id in api_specifications:
            del api_specifications[partner_id]
        if partner_id in generated_tests:
            del generated_tests[partner_id]
        
        return {
            'success': True,
            'message': f'All data deleted for partner {partner_id}'
        }
    
    except Exception as e:
        logger.error(f"❌ Error deleting partner data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
