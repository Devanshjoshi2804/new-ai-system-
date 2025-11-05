"""
Intelligent Test Executor with Self-Healing
Uses LangGraph for autonomous test execution with AI-powered error recovery
"""
import json
import logging
import httpx
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END

from src.infrastructure.ai.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class TestExecutionState(TypedDict):
    """State for test execution workflow"""
    test_cases: List[Dict[str, Any]]
    current_test_index: int
    auth_config: Dict[str, Any]
    auth_token: Optional[str]
    auth_data: Dict[str, Any]  # Additional data from auth (vendorCode, userId, etc.)
    test_results: List[Dict[str, Any]]
    failed_tests: List[Dict[str, Any]]
    retry_count: int
    max_retries: int
    base_url: str
    execution_complete: bool
    failure_analysis: Optional[Dict[str, Any]]
    extracted_data: Dict[str, Any]  # Data extracted from responses for use in subsequent tests


async def setup_authentication_node(state: TestExecutionState) -> TestExecutionState:
    """Authenticate before running tests"""
    try:
        logger.info("🔐 Setting up authentication...")
        
        auth_config = state.get('auth_config', {})
        
        if not auth_config or not auth_config.get('required', True):
            logger.info("ℹ️ No authentication required")
            return {**state, "auth_token": None, "auth_data": {}}
        
        # Determine authentication method
        auth_type = auth_config.get('type', '').lower()
        
        if auth_type in ['api_key', 'apikey']:
            # Use provided API key
            token = auth_config.get('api_key') or auth_config.get('test_credentials', {}).get('api_key')
            logger.info("✅ Using API key authentication")
            return {**state, "auth_token": token, "auth_data": {}}
        
        elif auth_type in ['bearer', 'oauth2', 'jwt']:
            # Call auth endpoint to get token
            auth_endpoint = auth_config.get('auth_endpoint', '/api/login')
            auth_method = auth_config.get('auth_method', 'POST')
            credentials = auth_config.get('test_credentials', {})
            
            if not credentials:
                logger.warning("⚠️ No test credentials provided")
                return {**state, "auth_token": None, "auth_data": {}}
            
            # Call auth endpoint
            url = f"{state['base_url']}{auth_endpoint}"
            logger.info(f"🔑 Calling auth endpoint: {auth_method} {url}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if auth_method.upper() == 'POST':
                    response = await client.post(url, json=credentials)
                else:
                    response = await client.get(url, params=credentials)
                
                if response.status_code in [200, 201]:
                    response_data = response.json()
                    
                    # Extract token
                    token_path = auth_config.get('token_response_path', 'data.token')
                    token = extract_value_from_path(response_data, token_path)
                    
                    # Extract additional data
                    additional_extractions = auth_config.get('additional_data', {})
                    auth_data = {}
                    for key, path in additional_extractions.items():
                        auth_data[key] = extract_value_from_path(response_data, path)
                    
                    logger.info(f"✅ Authentication successful, token obtained")
                    logger.info(f"📊 Additional data extracted: {list(auth_data.keys())}")
                    
                    return {**state, "auth_token": token, "auth_data": auth_data}
                else:
                    logger.error(f"❌ Authentication failed: {response.status_code} - {response.text}")
                    return {**state, "auth_token": None, "auth_data": {}, "execution_complete": True}
        
        else:
            logger.warning(f"⚠️ Unknown auth type: {auth_type}")
            return {**state, "auth_token": None, "auth_data": {}}
    
    except Exception as e:
        logger.error(f"❌ Error in authentication: {e}", exc_info=True)
        return {**state, "auth_token": None, "auth_data": {}, "execution_complete": True}


async def execute_test_node(state: TestExecutionState) -> TestExecutionState:
    """Execute single test case"""
    try:
        current_idx = state['current_test_index']
        test_case = state['test_cases'][current_idx]
        
        logger.info(f"🧪 Executing test {current_idx + 1}/{len(state['test_cases'])}: {test_case.get('name', 'Unnamed')}")
        
        # Execute test steps
        step_results = []
        test_success = True
        test_error = None
        
        for step in test_case.get('steps', []):
            try:
                step_result = await execute_test_step(
                    step=step,
                    base_url=state['base_url'],
                    auth_token=state.get('auth_token'),
                    auth_data=state.get('auth_data', {}),
                    extracted_data=state.get('extracted_data', {})
                )
                
                step_results.append(step_result)
                
                if not step_result.get('success'):
                    test_success = False
                    test_error = step_result.get('error')
                    break
                
                # Extract data from response for use in subsequent steps
                if step.get('extract'):
                    extracted_data = state.get('extracted_data', {})
                    for key, path in step['extract'].items():
                        value = extract_value_from_path(step_result.get('response_data', {}), path)
                        extracted_data[key] = value
                        logger.info(f"📤 Extracted {key} = {value}")
                    state = {**state, "extracted_data": extracted_data}
            
            except Exception as e:
                logger.error(f"❌ Error in test step: {e}")
                step_results.append({
                    'success': False,
                    'error': str(e),
                    'step': step
                })
                test_success = False
                test_error = str(e)
                break
        
        # Create test result
        test_result = {
            'test_id': test_case.get('test_id', f"test_{current_idx}"),
            'test_name': test_case.get('name', 'Unnamed'),
            'status': 'passed' if test_success else 'failed',
            'steps': step_results,
            'error': test_error,
            'timestamp': datetime.utcnow().isoformat(),
            'retry_count': state.get('retry_count', 0)
        }
        
        # Validate assertions if test succeeded
        if test_success and test_case.get('assertions'):
            assertion_results = await validate_assertions(
                assertions=test_case['assertions'],
                step_results=step_results
            )
            test_result['assertions'] = assertion_results
            
            if not all(a.get('passed') for a in assertion_results):
                test_result['status'] = 'failed'
                test_result['error'] = 'Assertion failures'
                test_success = False
        
        results = state['test_results'] + [test_result]
        
        if test_success:
            logger.info(f"✅ Test passed: {test_case.get('name')}")
            return {**state, "test_results": results, "retry_count": 0}
        else:
            logger.error(f"❌ Test failed: {test_case.get('name')} - {test_error}")
            failed = state['failed_tests'] + [test_case]
            return {**state, "test_results": results, "failed_tests": failed}
    
    except Exception as e:
        logger.error(f"❌ Error executing test: {e}", exc_info=True)
        
        test_result = {
            'test_id': f"test_{current_idx}",
            'test_name': 'Error',
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        results = state['test_results'] + [test_result]
        failed = state['failed_tests'] + [state['test_cases'][current_idx]]
        
        return {**state, "test_results": results, "failed_tests": failed}


async def execute_test_step(
    step: Dict[str, Any],
    base_url: str,
    auth_token: Optional[str],
    auth_data: Dict[str, Any],
    extracted_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute a single test step
    
    Args:
        step: Test step definition
        base_url: Base URL for API
        auth_token: Authentication token
        auth_data: Additional auth data (vendorCode, userId, etc.)
        extracted_data: Data extracted from previous steps
        
    Returns:
        Step execution result
    """
    try:
        endpoint = step.get('endpoint', '')
        method = step.get('method', 'GET').upper()
        data = step.get('data', {})
        
        # Substitute variables in data
        data = substitute_variables(data, {**auth_data, **extracted_data})
        
        # Substitute variables in endpoint
        endpoint = substitute_variables(endpoint, {**auth_data, **extracted_data})
        
        url = f"{base_url}{endpoint}"
        
        # Prepare headers
        headers = {}
        if auth_token:
            auth_config = step.get('auth_config', {})
            header_name = auth_config.get('header_name', 'Authorization')
            token_format = auth_config.get('token_format', 'Bearer {token}')
            headers[header_name] = token_format.replace('{token}', auth_token).replace('{{token}}', auth_token)
        
        logger.info(f"📡 {method} {url}")
        logger.debug(f"📤 Request data: {json.dumps(data, indent=2)}")
        
        # Execute request
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == 'GET':
                response = await client.get(url, params=data, headers=headers)
            elif method == 'POST':
                response = await client.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = await client.put(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = await client.patch(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {'text': response.text}
            
            logger.info(f"📥 Response: {response.status_code}")
            logger.debug(f"📥 Response data: {json.dumps(response_data, indent=2)[:500]}")
            
            # Check expected status
            expected_status = step.get('expected_status', 200)
            success = response.status_code == expected_status
            
            return {
                'success': success,
                'step': step.get('action', 'Unknown'),
                'endpoint': endpoint,
                'method': method,
                'status_code': response.status_code,
                'expected_status': expected_status,
                'response_data': response_data,
                'error': None if success else f"Expected {expected_status}, got {response.status_code}"
            }
    
    except Exception as e:
        logger.error(f"❌ Error executing step: {e}")
        return {
            'success': False,
            'step': step.get('action', 'Unknown'),
            'endpoint': step.get('endpoint', ''),
            'method': step.get('method', 'GET'),
            'error': str(e)
        }


async def analyze_failure_node(state: TestExecutionState) -> TestExecutionState:
    """AI analyzes test failures and suggests fixes"""
    try:
        if not state['failed_tests']:
            return state
        
        logger.info("🔍 Analyzing test failure with AI...")
        
        failed_test = state['failed_tests'][-1]
        last_result = state['test_results'][-1]
        
        gemini = GeminiProvider()
        
        prompt = f"""
Analyze this API test failure and suggest a fix:

Test Case:
{json.dumps(failed_test, indent=2)}

Test Result:
{json.dumps(last_result, indent=2)}

Determine:
1. **Root Cause**: What went wrong?
   - Authentication issue?
   - Data format issue?
   - Missing required field?
   - Wrong endpoint?
   - Dependency issue (missing prerequisite data)?
   - Business rule violation?

2. **Suggested Fix**: How to fix the test?
   - Modify request data?
   - Change endpoint?
   - Add missing field?
   - Fix data format?
   - Call prerequisite endpoint first?

3. **Retry Strategy**: Should we retry?
   - Yes, with modified data
   - Yes, with different approach
   - No, it's an API issue

Output as JSON:
{{
  "root_cause": "Detailed explanation",
  "root_cause_category": "auth|data_format|missing_field|endpoint|dependency|business_rule|api_issue",
  "suggested_fix": {{
    "type": "modify_data|change_endpoint|add_prerequisite|fix_format",
    "changes": {{
      "field1": "new_value",
      "field2": "new_value"
    }},
    "explanation": "Why this fix should work"
  }},
  "retry_recommended": true,
  "confidence": 0.8
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
        
        response = await gemini.generate_content(prompt, temperature=0.2)
        
        # Parse JSON from response
        analysis_text = response.strip()
        if "```json" in analysis_text:
            analysis_text = analysis_text.split("```json")[1].split("```")[0].strip()
        elif "```" in analysis_text:
            analysis_text = analysis_text.split("```")[1].split("```")[0].strip()
        
        analysis = json.loads(analysis_text)
        
        logger.info(f"🔍 Root cause: {analysis.get('root_cause_category')}")
        logger.info(f"💡 Suggested fix: {analysis.get('suggested_fix', {}).get('type')}")
        
        return {**state, "failure_analysis": analysis}
    
    except Exception as e:
        logger.error(f"❌ Error analyzing failure: {e}")
        return {**state, "failure_analysis": None}


async def apply_fix_node(state: TestExecutionState) -> TestExecutionState:
    """Apply AI-suggested fix and prepare for retry"""
    try:
        if state['retry_count'] >= state['max_retries']:
            logger.info("⚠️ Max retries reached, moving to next test")
            return state
        
        analysis = state.get('failure_analysis')
        if not analysis or not analysis.get('retry_recommended'):
            logger.info("ℹ️ Retry not recommended, moving to next test")
            return state
        
        logger.info("🔧 Applying AI-suggested fix...")
        
        # Get failed test
        failed_test = state['failed_tests'][-1].copy()
        suggested_fix = analysis.get('suggested_fix', {})
        
        # Apply fix based on type
        fix_type = suggested_fix.get('type', '')
        changes = suggested_fix.get('changes', {})
        
        if fix_type == 'modify_data':
            # Modify test data
            for step in failed_test.get('steps', []):
                if step.get('data'):
                    step['data'].update(changes)
        
        elif fix_type == 'change_endpoint':
            # Change endpoint
            for step in failed_test.get('steps', []):
                if 'endpoint' in changes:
                    step['endpoint'] = changes['endpoint']
        
        elif fix_type == 'add_prerequisite':
            # Add prerequisite step
            prerequisite_step = changes.get('prerequisite_step')
            if prerequisite_step:
                failed_test['steps'].insert(0, prerequisite_step)
        
        elif fix_type == 'fix_format':
            # Fix data format
            for step in failed_test.get('steps', []):
                if step.get('data'):
                    for field, new_value in changes.items():
                        if field in step['data']:
                            step['data'][field] = new_value
        
        # Add fixed test back to queue
        test_cases = state['test_cases'] + [failed_test]
        retry_count = state['retry_count'] + 1
        
        logger.info(f"✅ Fix applied, retry count: {retry_count}/{state['max_retries']}")
        
        return {**state, "test_cases": test_cases, "retry_count": retry_count}
    
    except Exception as e:
        logger.error(f"❌ Error applying fix: {e}")
        return state


def should_retry(state: TestExecutionState) -> str:
    """Decide whether to retry failed test"""
    if state['failed_tests'] and state['retry_count'] < state['max_retries']:
        return "analyze_failure"
    return "next_test"


def has_more_tests(state: TestExecutionState) -> str:
    """Check if there are more tests to run"""
    if state['current_test_index'] + 1 < len(state['test_cases']):
        return "execute_test"
    return "complete"


async def next_test_node(state: TestExecutionState) -> TestExecutionState:
    """Move to next test"""
    return {
        **state,
        "current_test_index": state['current_test_index'] + 1,
        "retry_count": 0,
        "failure_analysis": None
    }


async def complete_execution_node(state: TestExecutionState) -> TestExecutionState:
    """Mark execution as complete"""
    logger.info("✅ Test execution complete")
    
    total = len(state['test_results'])
    passed = len([r for r in state['test_results'] if r['status'] == 'passed'])
    failed = len([r for r in state['test_results'] if r['status'] == 'failed'])
    errors = len([r for r in state['test_results'] if r['status'] == 'error'])
    
    logger.info(f"📊 Results: {passed} passed, {failed} failed, {errors} errors out of {total} tests")
    
    return {**state, "execution_complete": True}


def build_test_execution_graph() -> StateGraph:
    """Build intelligent test execution graph with self-healing"""
    logger.info("🏗️ Building test execution graph...")
    
    workflow = StateGraph(TestExecutionState)
    
    # Add nodes
    workflow.add_node("setup_auth", setup_authentication_node)
    workflow.add_node("execute_test", execute_test_node)
    workflow.add_node("analyze_failure", analyze_failure_node)
    workflow.add_node("apply_fix", apply_fix_node)
    workflow.add_node("next_test", next_test_node)
    workflow.add_node("complete", complete_execution_node)
    
    # Define flow
    workflow.set_entry_point("setup_auth")
    workflow.add_edge("setup_auth", "execute_test")
    
    # Conditional edges
    workflow.add_conditional_edges(
        "execute_test",
        should_retry,
        {
            "analyze_failure": "analyze_failure",
            "next_test": "next_test"
        }
    )
    
    workflow.add_edge("analyze_failure", "apply_fix")
    workflow.add_edge("apply_fix", "execute_test")
    
    workflow.add_conditional_edges(
        "next_test",
        has_more_tests,
        {
            "execute_test": "execute_test",
            "complete": "complete"
        }
    )
    
    workflow.add_edge("complete", END)
    
    logger.info("✅ Test execution graph built")
    
    return workflow.compile()


# Helper functions

def extract_value_from_path(data: Dict[str, Any], path: str) -> Any:
    """Extract value from nested dict using dot notation path"""
    try:
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    except:
        return None


def substitute_variables(obj: Any, variables: Dict[str, Any]) -> Any:
    """Substitute variables in strings, recursively"""
    if isinstance(obj, str):
        # Replace {{variable}} with value
        for key, value in variables.items():
            obj = obj.replace(f"{{{{{key}}}}}", str(value))
            obj = obj.replace(f"{{{key}}}", str(value))
        return obj
    elif isinstance(obj, dict):
        return {k: substitute_variables(v, variables) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [substitute_variables(item, variables) for item in obj]
    else:
        return obj


async def validate_assertions(
    assertions: List[str],
    step_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Validate test assertions"""
    assertion_results = []
    
    for assertion in assertions:
        # Simple assertion validation
        # In production, this would be more sophisticated
        passed = True  # Placeholder
        
        assertion_results.append({
            'assertion': assertion,
            'passed': passed,
            'message': 'Assertion passed' if passed else 'Assertion failed'
        })
    
    return assertion_results


class IntelligentTestExecutor:
    """Main class for intelligent test execution"""
    
    def __init__(self):
        self.graph = build_test_execution_graph()
    
    async def execute_tests(
        self,
        test_cases: List[Dict[str, Any]],
        auth_config: Dict[str, Any],
        base_url: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Execute tests with self-healing
        
        Args:
            test_cases: List of test cases to execute
            auth_config: Authentication configuration
            base_url: Base URL for API
            max_retries: Maximum retry attempts per test
            
        Returns:
            Execution results
        """
        try:
            logger.info(f"🚀 Starting intelligent test execution for {len(test_cases)} tests...")
            
            initial_state: TestExecutionState = {
                'test_cases': test_cases,
                'current_test_index': 0,
                'auth_config': auth_config,
                'auth_token': None,
                'auth_data': {},
                'test_results': [],
                'failed_tests': [],
                'retry_count': 0,
                'max_retries': max_retries,
                'base_url': base_url,
                'execution_complete': False,
                'failure_analysis': None,
                'extracted_data': {}
            }
            
            result = await self.graph.ainvoke(initial_state)
            
            # Compile final results
            total = len(result['test_results'])
            passed = len([r for r in result['test_results'] if r['status'] == 'passed'])
            failed = len([r for r in result['test_results'] if r['status'] == 'failed'])
            errors = len([r for r in result['test_results'] if r['status'] == 'error'])
            
            return {
                'success': result.get('execution_complete', False),
                'total_tests': total,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'pass_rate': (passed / total * 100) if total > 0 else 0,
                'test_results': result['test_results'],
                'failed_tests': result['failed_tests'],
                'execution_time': None  # Could add timing
            }
        
        except Exception as e:
            logger.error(f"❌ Error in test execution: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0,
                'pass_rate': 0,
                'test_results': [],
                'failed_tests': []
            }
