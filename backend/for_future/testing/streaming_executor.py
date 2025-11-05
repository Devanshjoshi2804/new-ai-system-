"""
Streaming Test Executor
Executes tests with real-time event streaming
"""
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
import uuid

from src.infrastructure.realtime.test_stream import (
    get_event_stream,
    EventType,
    StreamLogger
)
from src.infrastructure.monitoring.performance_monitor import PerformanceTracker

logger = logging.getLogger(__name__)


class StreamingTestExecutor:
    """
    Execute API tests with real-time streaming
    
    Features:
    - Real-time progress updates
    - Live log streaming
    - Step-by-step execution tracking
    - Error reporting
    - Performance metrics
    """
    
    def __init__(self, test_id: Optional[str] = None):
        """
        Initialize streaming test executor
        
        Args:
            test_id: Test identifier (generates UUID if not provided)
        """
        self.test_id = test_id or str(uuid.uuid4())
        self.event_stream = get_event_stream()
        self.stream_logger = StreamLogger(self.test_id, self.event_stream)
        
        logger.info(f"✅ Streaming test executor initialized: {self.test_id}")
    
    async def execute_test_suite(
        self,
        test_scenarios: List[Dict[str, Any]],
        base_url: str,
        auth_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a complete test suite with streaming
        
        Args:
            test_scenarios: List of test scenarios
            base_url: API base URL
            auth_config: Authentication configuration
            
        Returns:
            Test execution results
        """
        start_time = time.time()
        
        try:
            # Emit test start event
            await self.event_stream.emit_event(
                self.test_id,
                EventType.TEST_START,
                total_steps=len(test_scenarios),
                base_url=base_url,
                scenario_count=len(test_scenarios)
            )
            
            await self.stream_logger.info(f"🧪 Starting test execution with {len(test_scenarios)} scenarios")
            await self.stream_logger.info(f"🌐 Base URL: {base_url}")
            
            # Execute authentication if needed
            auth_token = None
            auth_data = {}
            if auth_config:
                await self.stream_logger.info("🔐 Authenticating...")
                auth_result = await self._execute_authentication(auth_config, base_url)
                
                if auth_result['success']:
                    auth_token = auth_result.get('token')
                    auth_data = auth_result.get('data', {})
                    await self.stream_logger.success(f"✅ Authentication successful")
                else:
                    await self.stream_logger.error(f"❌ Authentication failed: {auth_result.get('error')}")
                    raise Exception(f"Authentication failed: {auth_result.get('error')}")
            
            # Execute test scenarios
            results = []
            success_count = 0
            failure_count = 0
            
            for idx, scenario in enumerate(test_scenarios, 1):
                scenario_name = scenario.get('name', f'Test {idx}')
                
                # Emit progress event
                await self.stream_logger.progress(
                    step=idx,
                    total_steps=len(test_scenarios),
                    step_name=scenario_name
                )
                
                await self.stream_logger.info(f"\n{'='*60}")
                await self.stream_logger.info(f"[{idx}/{len(test_scenarios)}] 🧪 {scenario_name}")
                await self.stream_logger.info(f"{'='*60}")
                
                # Execute scenario
                scenario_result = await self._execute_scenario(
                    scenario,
                    base_url,
                    auth_token,
                    auth_data,
                    idx
                )
                
                results.append(scenario_result)
                
                if scenario_result['success']:
                    success_count += 1
                    await self.stream_logger.success(f"✅ Test passed: {scenario_name}")
                else:
                    failure_count += 1
                    await self.stream_logger.error(f"❌ Test failed: {scenario_name}")
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Emit completion event
            await self.event_stream.emit_event(
                self.test_id,
                EventType.TEST_COMPLETE,
                total_steps=len(test_scenarios),
                success_count=success_count,
                failure_count=failure_count,
                duration=duration,
                results=results
            )
            
            await self.stream_logger.info(f"\n{'='*60}")
            await self.stream_logger.info(f"🏁 Test Execution Complete")
            await self.stream_logger.info(f"{'='*60}")
            await self.stream_logger.info(f"✅ Passed: {success_count}/{len(test_scenarios)}")
            await self.stream_logger.info(f"❌ Failed: {failure_count}/{len(test_scenarios)}")
            await self.stream_logger.info(f"⏱️  Duration: {duration:.2f}s")
            await self.stream_logger.info(f"{'='*60}\n")
            
            return {
                'test_id': self.test_id,
                'success': failure_count == 0,
                'total_tests': len(test_scenarios),
                'passed': success_count,
                'failed': failure_count,
                'duration': duration,
                'results': results
            }
        
        except Exception as e:
            logger.error(f"❌ Test execution error: {e}", exc_info=True)
            
            # Emit error event
            await self.event_stream.emit_event(
                self.test_id,
                EventType.TEST_ERROR,
                error=str(e),
                step=0,
                fatal=True
            )
            
            await self.stream_logger.error(f"❌ Fatal error: {str(e)}")
            
            return {
                'test_id': self.test_id,
                'success': False,
                'error': str(e),
                'duration': time.time() - start_time
            }
    
    async def _execute_authentication(
        self,
        auth_config: Dict[str, Any],
        base_url: str
    ) -> Dict[str, Any]:
        """Execute authentication step"""
        try:
            import httpx
            
            auth_endpoint = auth_config.get('auth_endpoint', '/api/login')
            auth_method = auth_config.get('auth_method', 'POST')
            credentials = auth_config.get('test_credentials', {})
            
            await self.stream_logger.info(f"📡 {auth_method} {auth_endpoint}")
            await self.stream_logger.info(f"📦 Credentials: {list(credentials.keys())}")
            
            # Make auth request
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{base_url}{auth_endpoint}"
                
                if auth_method.upper() == 'POST':
                    response = await client.post(url, json=credentials)
                else:
                    response = await client.get(url, params=credentials)
                
                await self.stream_logger.info(f"📥 Status: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    
                    # Extract token
                    token_path = auth_config.get('token_response_path', 'data.token')
                    token = self._extract_value(data, token_path)
                    
                    # Extract additional data
                    additional_data = {}
                    for key, path in auth_config.get('additional_data', {}).items():
                        additional_data[key] = self._extract_value(data, path)
                    
                    await self.stream_logger.info(f"🔑 Token extracted: {token[:20]}..." if token else "⚠️ No token found")
                    
                    return {
                        'success': True,
                        'token': token,
                        'data': additional_data,
                        'response': data
                    }
                else:
                    return {
                        'success': False,
                        'error': f"Status {response.status_code}: {response.text}"
                    }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _execute_scenario(
        self,
        scenario: Dict[str, Any],
        base_url: str,
        auth_token: Optional[str],
        auth_data: Dict[str, Any],
        step_number: int
    ) -> Dict[str, Any]:
        """Execute a single test scenario"""
        try:
            import httpx
            
            steps = scenario.get('steps', [])
            scenario_data = {}  # Store extracted data
            
            for step_idx, step in enumerate(steps, 1):
                endpoint = step.get('endpoint', '')
                method = step.get('method', 'GET')
                test_data = step.get('data', {})
                expected_status = step.get('expected_status', 200)
                extract = step.get('extract', {})
                
                await self.stream_logger.info(f"  [{step_idx}/{len(steps)}] 📡 {method} {endpoint}")
                
                # Replace variables in test data
                test_data = self._replace_variables(test_data, {**auth_data, **scenario_data})
                
                # Make request
                async with httpx.AsyncClient(timeout=30.0) as client:
                    url = f"{base_url}{endpoint}"
                    headers = {}
                    
                    # Add auth token if available
                    if auth_token:
                        headers['Authorization'] = f"Bearer {auth_token}"
                    
                    start_time = time.time()
                    
                    try:
                        if method.upper() == 'GET':
                            response = await client.get(url, headers=headers, params=test_data)
                        elif method.upper() == 'POST':
                            response = await client.post(url, headers=headers, json=test_data)
                        elif method.upper() == 'PUT':
                            response = await client.put(url, headers=headers, json=test_data)
                        elif method.upper() == 'DELETE':
                            response = await client.delete(url, headers=headers)
                        else:
                            raise ValueError(f"Unsupported method: {method}")
                        
                        duration = (time.time() - start_time) * 1000  # ms
                        
                        await self.stream_logger.info(f"  📥 Status: {response.status_code} ({duration:.0f}ms)")
                        
                        # Check status code
                        if response.status_code != expected_status:
                            await self.stream_logger.warning(
                                f"  ⚠️ Expected {expected_status}, got {response.status_code}"
                            )
                        
                        # Extract data
                        if extract and response.status_code in [200, 201]:
                            response_data = response.json()
                            
                            for key, path in extract.items():
                                value = self._extract_value(response_data, path)
                                scenario_data[key] = value
                                await self.stream_logger.info(f"  📌 Extracted {key}: {value}")
                        
                        # Check if step passed
                        step_passed = response.status_code == expected_status
                        
                        if step_passed:
                            await self.stream_logger.success(f"  ✅ Step {step_idx} passed")
                        else:
                            await self.stream_logger.error(f"  ❌ Step {step_idx} failed")
                            
                            return {
                                'success': False,
                                'scenario': scenario.get('name'),
                                'failed_step': step_idx,
                                'error': f"Status code mismatch: expected {expected_status}, got {response.status_code}"
                            }
                    
                    except httpx.TimeoutException:
                        await self.stream_logger.error(f"  ❌ Request timeout")
                        return {
                            'success': False,
                            'scenario': scenario.get('name'),
                            'failed_step': step_idx,
                            'error': 'Request timeout'
                        }
                    
                    except Exception as e:
                        await self.stream_logger.error(f"  ❌ Request error: {str(e)}")
                        return {
                            'success': False,
                            'scenario': scenario.get('name'),
                            'failed_step': step_idx,
                            'error': str(e)
                        }
            
            # All steps passed
            return {
                'success': True,
                'scenario': scenario.get('name'),
                'steps_executed': len(steps),
                'extracted_data': scenario_data
            }
        
        except Exception as e:
            await self.stream_logger.error(f"  ❌ Scenario error: {str(e)}")
            return {
                'success': False,
                'scenario': scenario.get('name'),
                'error': str(e)
            }
    
    def _extract_value(self, data: Dict[str, Any], path: str) -> Any:
        """Extract value from nested dict using dot notation"""
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        
        return value
    
    def _replace_variables(self, data: Any, variables: Dict[str, Any]) -> Any:
        """Replace variables in data (recursive)"""
        if isinstance(data, dict):
            return {
                key: self._replace_variables(value, variables)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._replace_variables(item, variables) for item in data]
        elif isinstance(data, str) and data.startswith('{{') and data.endswith('}}'):
            # Variable placeholder
            var_name = data[2:-2].strip()
            return variables.get(var_name, data)
        else:
            return data
