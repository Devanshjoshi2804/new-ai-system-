"""
Test Partner Integration Use Case - Main entry point for API testing
"""
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from ...ai.graphs.testing_graph import run_testing_workflow
from ....infrastructure.database.models.test_execution_model import TestExecution, APITestResult
from ....infrastructure.database.mongodb.connection import MongoDBConnection

logger = logging.getLogger(__name__)


async def test_partner_integration(
    partner_id: str,
    documentation_id: str,
    api_spec: Dict[str, Any],
    tenant_id: Optional[str] = None,
    test_execution_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Test partner API integration comprehensively
    
    This is the main entry point for the API testing workflow. It:
    1. Gets parsed API spec from documentation
    2. Initializes Gemini-powered coordinator
    3. Runs LangGraph testing workflow
    4. Saves results to database
    5. Returns comprehensive results
    
    Args:
        partner_id: Partner ID
        documentation_id: Documentation ID
        api_spec: Parsed API specification
        tenant_id: Optional tenant ID
        test_execution_id: Optional pre-created test execution ID
        
    Returns:
        Dictionary with test execution ID and summary
    """
    logger.info(f"Starting API testing for partner {partner_id}")
    
    db = MongoDBConnection.get_database()
    test_executions = db['test_executions']
    test_results_collection = db['api_test_results']
    
    try:
        # Use existing test execution ID or create new one
        if test_execution_id:
            logger.info(f"Using existing test execution: {test_execution_id}")
            # Update status to running
            await test_executions.update_one(
                {"id": test_execution_id},
                {"$set": {
                    "status": "running",
                    "current_phase": "Initializing",
                    "started_at": datetime.utcnow()
                }}
            )
        else:
            # Create test execution record
            test_execution_data = {
                "partner_id": partner_id,
                "documentation_id": documentation_id,
                "tenant_id": tenant_id,
                "status": "pending",
                "total_endpoints": len(api_spec.get('endpoints', [])),
                "tested_endpoints": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "skipped_tests": 0,
                "dependency_graph": {},
                "execution_order": [],
                "test_results": [],
                "test_data_store": {},
                "current_endpoint": None,
                "current_phase": "initializing",
                "global_errors": [],
                "total_execution_time": 0.0,
                "average_response_time": 0.0,
                "pass_rate": 0.0,
                "started_at": datetime.utcnow(),
                "completed_at": None,
                "max_retries": 5,
                "retry_delay": 1.0
            }
            
            result = await test_executions.insert_one(test_execution_data)
            test_execution_id = str(result.inserted_id)
            
            logger.info(f"Created test execution: {test_execution_id}")
        
        # Extract base URL from API spec
        base_url = api_spec.get('baseUrl', '') or api_spec.get('base_url', '')
        
        if not base_url:
            raise ValueError("Base URL not found in API specification")
        
        # Build authentication headers from API spec
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Extract auth configuration from API spec
        auth_config = api_spec.get('auth', {})
        if auth_config:
            auth_type = auth_config.get('type', '')
            logger.info(f"Found authentication config: {auth_type}")
            
            # Handle different auth types
            if auth_type == 'api_key':
                # API Key authentication
                header_name = auth_config.get('header_name', 'X-API-Key')
                api_key = auth_config.get('api_key') or auth_config.get('value')
                if api_key:
                    headers[header_name] = api_key
                    logger.info(f"Added API key header: {header_name}")
                else:
                    logger.warning(f"API key authentication required but no key found in config")
                    
            elif auth_type == 'bearer' or auth_type == 'bearer_token':
                # Bearer token authentication
                token = auth_config.get('token') or auth_config.get('value')
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                    logger.info("Added Bearer token authentication")
                else:
                    logger.warning("Bearer token authentication required but no token found in config")
                    
            elif auth_type == 'basic' or auth_type == 'basic_auth':
                # Basic authentication
                username = auth_config.get('username')
                password = auth_config.get('password')
                if username and password:
                    import base64
                    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                    headers['Authorization'] = f'Basic {credentials}'
                    logger.info("Added Basic authentication")
                else:
                    logger.warning("Basic auth required but credentials not found in config")
                    
            else:
                logger.warning(f"Unknown authentication type: {auth_type}")
        else:
            logger.info("No authentication configuration found in API spec")
        
        # Get AI provider API key from environment (priority: Groq > Gemini > Mistral)
        ai_api_key = (
            os.getenv('GROQ_API_KEY') or 
            os.getenv('GOOGLE_GEMINI_API_KEY') or 
            os.getenv('GEMINI_API_KEY') or
            os.getenv('MISTRAL_API_KEY')
        )
        
        # Determine which provider will be used
        provider_name = "None"
        if os.getenv('GROQ_API_KEY'):
            provider_name = "Groq"
        elif os.getenv('GOOGLE_GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY'):
            provider_name = "Gemini"
        elif os.getenv('MISTRAL_API_KEY'):
            provider_name = "Mistral"
        
        # Run testing workflow
        logger.info("Running testing workflow...")
        logger.info(f"Using headers: {[k for k in headers.keys()]}")  # Log header keys only (not values for security)
        logger.info(f"Base URL: {base_url}")
        logger.info(f"Total endpoints: {len(api_spec.get('endpoints', []))}")
        logger.info(f"AI Provider: {provider_name} (API key available: {bool(ai_api_key)})")
        
        await test_executions.update_one(
            {"id": test_execution_id},
            {"$set": {"status": "running", "current_phase": "Starting workflow"}}
        )
        
        try:
            logger.info("[START] Calling run_testing_workflow...")
            final_state = await run_testing_workflow(
                partner_id=partner_id,
                documentation_id=documentation_id,
                api_spec=api_spec,
                base_url=base_url,
                headers=headers,
                ai_api_key=ai_api_key
            )
            logger.info(f"[OK] Workflow completed with status: {final_state.get('status')}")
        except Exception as workflow_error:
            logger.error(f"[ERROR] Workflow execution failed: {workflow_error}", exc_info=True)
            raise
        
        # Save individual test results
        logger.info("Saving test results...")
        test_result_ids = []
        
        for result in final_state.get('test_results', []):
            test_result_data = {
                "test_execution_id": test_execution_id,
                "endpoint": result.get('endpoint', ''),
                "method": result.get('method', ''),
                "test_case_id": result.get('test_case_id', ''),
                "test_case_name": result.get('test_case_name', ''),
                "status": result.get('status', 'unknown'),
                "attempt_number": result.get('attempt_number', 1),
                "request_data": result.get('request_data', {}),
                "request_headers": result.get('request_headers', {}),
                "response_data": result.get('response_data'),
                "response_status": result.get('response_status'),
                "response_headers": result.get('response_headers'),
                "execution_time": result.get('execution_time', 0.0),
                "error_message": result.get('error_message'),
                "error_type": result.get('error_type'),
                "ai_analysis": result.get('ai_analysis'),
                "timestamp": result.get('timestamp', datetime.utcnow())
            }
            
            test_result = await test_results_collection.insert_one(test_result_data)
            test_result_ids.append(str(test_result.inserted_id))
        
        # Calculate metrics
        passed_tests = final_state.get('passed_tests', 0)
        failed_tests = final_state.get('failed_tests', 0)
        total_tests = passed_tests + failed_tests
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0
        
        # Calculate average response time
        execution_times = [r.get('execution_time', 0) for r in final_state.get('test_results', []) if r.get('execution_time')]
        average_response_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        # Calculate total execution time
        # Fetch the test execution to get started_at
        test_execution_record = await test_executions.find_one({"id": test_execution_id})
        started_at = test_execution_record.get('started_at', datetime.utcnow()) if test_execution_record else datetime.utcnow()
        completed_at = datetime.utcnow()
        total_execution_time = (completed_at - started_at).total_seconds()
        
        # Update test execution with final results
        update_data = {
            "status": final_state.get('status', 'completed'),
            "tested_endpoints": final_state.get('tested_endpoints', 0),
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": final_state.get('skipped_tests', 0),
            "dependency_graph": final_state.get('dependency_graph', {}),
            "execution_order": final_state.get('execution_order', []),
            "test_results": test_result_ids,
            "test_data_store": final_state.get('test_data_store', {}),
            "current_phase": "completed",
            "completed_at": completed_at,
            "total_execution_time": total_execution_time,
            "average_response_time": average_response_time,
            "pass_rate": pass_rate
        }
        
        await test_executions.update_one(
            {"id": test_execution_id},
            {"$set": update_data}
        )
        
        logger.info(f"Testing complete: {passed_tests}/{total_tests} passed")
        
        # Return summary
        return {
            "test_execution_id": test_execution_id,
            "status": update_data['status'],
            "total_endpoints": len(api_spec.get('endpoints', [])),
            "tested_endpoints": update_data['tested_endpoints'],
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": pass_rate,
            "average_response_time": average_response_time,
            "total_execution_time": total_execution_time,
            "dependency_graph": update_data['dependency_graph'],
            "execution_order": update_data['execution_order'],
            "is_successful": failed_tests == 0
        }
        
    except Exception as e:
        logger.error(f"Testing failed with error: {e}", exc_info=True)
        
        # Update execution record with error
        if 'test_execution_id' in locals():
            await test_executions.update_one(
                {"id": test_execution_id},
                {"$set": {
                    "status": "failed",
                    "global_errors": [{
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }],
                    "completed_at": datetime.utcnow()
                }}
            )
        
        raise


async def get_test_execution_progress(test_execution_id: str) -> Dict[str, Any]:
    """
    Get current progress of a test execution
    
    Args:
        test_execution_id: Test execution ID
        
    Returns:
        Progress information
    """
    db = MongoDBConnection.get_database()
    test_executions = db['test_executions']
    
    # Try to find by id field first (UUID string), then by _id (ObjectId)
    test_execution = await test_executions.find_one({"id": test_execution_id})
    if not test_execution:
        try:
            test_execution = await test_executions.find_one({"_id": ObjectId(test_execution_id)})
        except:
            pass
    
    if not test_execution:
        raise ValueError(f"Test execution {test_execution_id} not found")
    
    # Check if complete
    status = test_execution.get('status', 'pending')
    is_complete = status in ["completed", "completed_with_failures", "failed"]
    
    return {
        "test_execution_id": test_execution_id,
        "status": status,
        "current_phase": test_execution.get('current_phase', 'Initializing'),
        "current_endpoint": test_execution.get('current_endpoint'),
        "tested_endpoints": test_execution.get('tested_endpoints', 0),
        "total_endpoints": test_execution.get('total_endpoints', 0),
        "passed_tests": test_execution.get('passed_tests', 0),
        "failed_tests": test_execution.get('failed_tests', 0),
        "dependency_graph": test_execution.get('dependency_graph', {}),
        "execution_order": test_execution.get('execution_order', []),
        "is_complete": is_complete,
        "error_message": test_execution.get('error_message')
    }


async def get_test_execution_results(test_execution_id: str) -> Dict[str, Any]:
    """
    Get complete results of a test execution
    
    Args:
        test_execution_id: Test execution ID
        
    Returns:
        Complete test results
    """
    db = MongoDBConnection.get_database()
    test_executions = db['test_executions']
    test_results_collection = db['api_test_results']
    
    # Try to find by id field first (UUID string), then by _id (ObjectId)
    test_execution = await test_executions.find_one({"id": test_execution_id})
    if not test_execution:
        try:
            test_execution = await test_executions.find_one({"_id": ObjectId(test_execution_id)})
        except:
            pass
    
    if not test_execution:
        raise ValueError(f"Test execution {test_execution_id} not found")
    
    # Get all test results
    cursor = test_results_collection.find({"test_execution_id": test_execution_id})
    test_results = await cursor.to_list(length=None)
    
    # Convert to dict
    results_data = [
        {
            "id": str(result['_id']),
            "endpoint": result.get('endpoint'),
            "method": result.get('method'),
            "test_case_name": result.get('test_case_name'),
            "status": result.get('status'),
            "attempt_number": result.get('attempt_number'),
            "response_status": result.get('response_status'),
            "execution_time": result.get('execution_time'),
            "error_message": result.get('error_message'),
            "timestamp": result.get('timestamp').isoformat() if result.get('timestamp') else None
        }
        for result in test_results
    ]
    
    return {
        "test_execution_id": test_execution_id,
        "partner_id": test_execution.get('partner_id'),
        "status": test_execution.get('status'),
        "total_endpoints": test_execution.get('total_endpoints', 0),
        "tested_endpoints": test_execution.get('tested_endpoints', 0),
        "total_tests": len(test_results),
        "passed_tests": test_execution.get('passed_tests', 0),
        "failed_tests": test_execution.get('failed_tests', 0),
        "pass_rate": test_execution.get('pass_rate', 0.0),
        "average_response_time": test_execution.get('average_response_time', 0.0),
        "total_execution_time": test_execution.get('total_execution_time', 0.0),
        "dependency_graph": test_execution.get('dependency_graph', {}),
        "execution_order": test_execution.get('execution_order', []),
        "test_results": results_data,
        "started_at": test_execution.get('started_at').isoformat() if test_execution.get('started_at') else None,
        "completed_at": test_execution.get('completed_at').isoformat() if test_execution.get('completed_at') else None
    }


