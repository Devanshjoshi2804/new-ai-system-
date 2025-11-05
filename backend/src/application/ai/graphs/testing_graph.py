"""
LangGraph Testing Workflow - State machine for API testing orchestration
"""
import logging
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END

from ..testing.test_coordinator import TestCoordinator
from ....infrastructure.ai.providers import get_ai_provider, AIProviderType

logger = logging.getLogger(__name__)


class TestingState(TypedDict):
    """State for testing workflow"""
    # Input
    partner_id: str
    documentation_id: str
    api_spec: Dict[str, Any]
    base_url: str
    headers: Optional[Dict[str, str]]
    
    # Analysis results
    dependency_graph: Dict[str, List[str]]
    execution_order: List[str]
    
    # Execution state
    current_phase: str
    current_endpoint: Optional[str]
    tested_endpoints: int
    total_endpoints: int
    
    # Test results
    test_results: List[Dict[str, Any]]
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    
    # Shared data
    test_data_store: Dict[str, Any]
    
    # Status
    status: str
    error_message: Optional[str]
    
    # Metrics
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_execution_time: float


def create_testing_workflow(ai_api_key: Optional[str] = None, provider_type: str = "auto", doc_id: Optional[str] = None) -> StateGraph:
    """
    Create the LangGraph testing workflow
    
    Args:
        ai_api_key: Optional AI API key (for any provider)
        provider_type: Provider type ("auto", "groq", "gemini", "mistral")
        doc_id: Optional documentation ID for Vector DB
        
    Returns:
        Compiled StateGraph workflow
    """
    # Initialize AI provider (auto-selects Groq > Gemini > Mistral)
    ai_provider = None
    try:
        if provider_type == "auto":
            ai_provider = get_ai_provider(api_key=ai_api_key)
        else:
            ai_provider = get_ai_provider(
                provider_type=AIProviderType(provider_type),
                api_key=ai_api_key
            )
        logger.info(f"[OK] Testing workflow using: {type(ai_provider).__name__}")
    except Exception as e:
        logger.warning(f"[WARN] Failed to initialize AI provider: {e}")
        logger.warning("Testing will continue without AI-powered features")
    
    # Initialize Vector DB if doc_id provided
    vector_store = None
    if doc_id:
        try:
            from ....infrastructure.ai.vector_store.document_vector_store import DocumentVectorStore
            from ....infrastructure.config.settings import get_settings
            settings = get_settings()
            
            vector_store = DocumentVectorStore(
                collection_name=settings.vector_db_collection_prefix,
                persist_directory=settings.vector_db_persist_dir,
                embedding_model=settings.embedding_model
            )
            logger.info(f"[OK] Vector DB initialized for doc_id: {doc_id}")
        except Exception as e:
            logger.warning(f"[WARN] Failed to initialize Vector DB: {e}")
            logger.warning("Testing will continue without Vector DB")
    
    # Initialize coordinator with Vector DB
    coordinator = TestCoordinator(
        ai_provider=ai_provider,
        vector_store=vector_store,
        max_retries=5,
        initial_delay=1.0
    )
    
    # Define workflow nodes
    def initialize_node(state: TestingState) -> TestingState:
        """Initialize testing workflow"""
        logger.info("Initializing testing workflow")
        
        state['current_phase'] = 'initializing'
        state['status'] = 'initializing'
        state['started_at'] = datetime.utcnow()
        state['tested_endpoints'] = 0
        state['passed_tests'] = 0
        state['failed_tests'] = 0
        state['skipped_tests'] = 0
        state['test_results'] = []
        state['test_data_store'] = {}
        state['error_message'] = None
        
        # Validate inputs
        if not state.get('api_spec') or not state['api_spec'].get('endpoints'):
            state['status'] = 'failed'
            state['error_message'] = 'No API endpoints found in specification'
            return state
        
        endpoints = state['api_spec'].get('endpoints', [])
        state['total_endpoints'] = len(endpoints)
        
        logger.info(f"Initialized testing for {state['total_endpoints']} endpoints")
        return state
    
    def analyze_dependencies_node(state: TestingState) -> TestingState:
        """Analyze API dependencies"""
        logger.info("Analyzing API dependencies")
        
        state['current_phase'] = 'analyzing'
        state['status'] = 'analyzing'
        
        try:
            endpoints = state['api_spec'].get('endpoints', [])
            
            # Analyze dependencies
            analysis = coordinator.dependency_analyzer.analyze(endpoints)
            
            state['dependency_graph'] = analysis['dependency_graph']
            state['execution_order'] = analysis['execution_order']
            
            logger.info(f"Dependency analysis complete. Execution order: {len(state['execution_order'])} endpoints")
            
        except Exception as e:
            logger.error(f"Dependency analysis failed: {e}")
            state['status'] = 'failed'
            state['error_message'] = f"Dependency analysis failed: {str(e)}"
        
        return state
    
    def create_sub_agents_node(state: TestingState) -> TestingState:
        """Create specialized sub-agents for each endpoint"""
        logger.info("Creating sub-agents")
        
        state['current_phase'] = 'creating_agents'
        
        try:
            endpoints = state['api_spec'].get('endpoints', [])
            
            # Agents are created by coordinator when needed
            logger.info(f"Sub-agent creation configured for {len(endpoints)} endpoints")
            
        except Exception as e:
            logger.error(f"Sub-agent creation failed: {e}")
            state['status'] = 'failed'
            state['error_message'] = f"Sub-agent creation failed: {str(e)}"
        
        return state
    
    async def execute_tests_node(state: TestingState) -> TestingState:
        """Execute all tests"""
        logger.info("Executing tests")
        
        state['current_phase'] = 'testing'
        state['status'] = 'testing'
        
        try:
            # Progress callback to update state
            async def progress_callback(update: Dict[str, Any]):
                state['current_endpoint'] = update.get('current_endpoint')
                state['tested_endpoints'] = update.get('tested_endpoints', state['tested_endpoints'])
                logger.info(f"Progress: {update.get('message', 'Testing...')}")
            
            # Run coordinated testing
            results = await coordinator.coordinate_testing(
                api_spec=state['api_spec'],
                base_url=state['base_url'],
                headers=state.get('headers'),
                progress_callback=progress_callback
            )
            
            # Update state with results
            state['test_results'] = results.get('test_results', [])
            state['passed_tests'] = results.get('passed_tests', 0)
            state['failed_tests'] = results.get('failed_tests', 0)
            state['tested_endpoints'] = results.get('tested_endpoints', 0)
            state['test_data_store'] = results.get('test_data_store', {})
            
            logger.info(f"Testing complete: {state['passed_tests']}/{state['passed_tests'] + state['failed_tests']} passed")
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            state['status'] = 'failed'
            state['error_message'] = f"Test execution failed: {str(e)}"
        
        return state
    
    def validate_results_node(state: TestingState) -> TestingState:
        """Validate and analyze test results"""
        logger.info("Validating results")
        
        state['current_phase'] = 'validating'
        
        try:
            total_tests = state['passed_tests'] + state['failed_tests']
            
            # Determine overall status
            if state['failed_tests'] == 0 and total_tests > 0:
                state['status'] = 'completed'
                logger.info("All tests passed!")
            elif state['passed_tests'] > 0:
                state['status'] = 'completed_with_failures'
                logger.warning(f"{state['failed_tests']} tests failed")
            else:
                state['status'] = 'failed'
                logger.error("All tests failed")
            
            state['completed_at'] = datetime.utcnow()
            if state['started_at']:
                state['total_execution_time'] = (
                    state['completed_at'] - state['started_at']
                ).total_seconds()
            
        except Exception as e:
            logger.error(f"Result validation failed: {e}")
            state['status'] = 'failed'
            state['error_message'] = f"Result validation failed: {str(e)}"
        
        return state
    
    def retry_failed_node(state: TestingState) -> TestingState:
        """Handle failed tests and retry logic"""
        logger.info("Handling failed tests")
        
        # This node can implement additional retry logic if needed
        # For now, retries are handled by TestExecutor
        
        return state
    
    # Build workflow graph
    workflow = StateGraph(TestingState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_node)
    workflow.add_node("analyze_dependencies", analyze_dependencies_node)
    workflow.add_node("create_sub_agents", create_sub_agents_node)
    workflow.add_node("execute_tests", execute_tests_node)
    workflow.add_node("validate_results", validate_results_node)
    workflow.add_node("retry_failed", retry_failed_node)
    
    # Define edges
    workflow.set_entry_point("initialize")
    
    workflow.add_edge("initialize", "analyze_dependencies")
    workflow.add_edge("analyze_dependencies", "create_sub_agents")
    workflow.add_edge("create_sub_agents", "execute_tests")
    workflow.add_edge("execute_tests", "validate_results")
    
    # Conditional edge from validate_results
    def should_retry(state: TestingState) -> str:
        """Determine if we should retry failed tests"""
        # For now, skip retry logic and go directly to END
        # Can implement smart retry logic here
        return "end"
    
    workflow.add_conditional_edges(
        "validate_results",
        should_retry,
        {
            "retry": "retry_failed",
            "end": END
        }
    )
    
    workflow.add_edge("retry_failed", "validate_results")
    
    return workflow.compile()


# Helper function to run testing workflow
async def run_testing_workflow(
    partner_id: str,
    documentation_id: str,
    api_spec: Dict[str, Any],
    base_url: str,
    headers: Optional[Dict[str, str]] = None,
    ai_api_key: Optional[str] = None
) -> TestingState:
    """
    Run the complete testing workflow
    
    Args:
        partner_id: Partner ID
        documentation_id: Documentation ID
        api_spec: API specification with endpoints
        base_url: Base URL for API
        headers: Optional HTTP headers
        ai_api_key: Optional AI provider API key (Groq/Gemini/Mistral)
        
    Returns:
        Final testing state
    """
    # Create workflow with AI provider and Vector DB
    workflow = create_testing_workflow(ai_api_key=ai_api_key, doc_id=documentation_id)
    
    # Initialize state
    initial_state = TestingState(
        partner_id=partner_id,
        documentation_id=documentation_id,
        api_spec=api_spec,
        base_url=base_url,
        headers=headers,
        dependency_graph={},
        execution_order=[],
        current_phase='pending',
        current_endpoint=None,
        tested_endpoints=0,
        total_endpoints=0,
        test_results=[],
        passed_tests=0,
        failed_tests=0,
        skipped_tests=0,
        test_data_store={},
        status='pending',
        error_message=None,
        started_at=None,
        completed_at=None,
        total_execution_time=0.0
    )
    
    # Run workflow
    final_state = await workflow.ainvoke(initial_state)
    
    return final_state


