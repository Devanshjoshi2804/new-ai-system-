"""
API Test Agent - Specialized agent for testing individual API endpoints
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class APITestAgent:
    """Agent responsible for testing a single API endpoint comprehensively"""
    
    def __init__(
        self,
        endpoint: Dict[str, Any],
        test_executor,
        test_data_generator,
        gemini_provider=None
    ):
        """
        Initialize API test agent
        
        Args:
            endpoint: API endpoint specification
            test_executor: TestExecutor instance
            test_data_generator: TestDataGenerator instance
            gemini_provider: Optional Gemini provider for AI analysis
        """
        self.endpoint = endpoint
        self.test_executor = test_executor
        self.test_data_generator = test_data_generator
        self.gemini_provider = gemini_provider
        
        self.path = endpoint.get('path', '')
        self.method = endpoint.get('method', 'GET')
        self.parameters = endpoint.get('parameters', [])
        self.summary = endpoint.get('summary', '')
        
        logger.info(f"Initialized agent for {self.method} {self.path}")
    
    async def run_tests(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        test_data_store: Optional[Dict[str, Any]] = None,
        documentation_text: Optional[str] = None,
        doc_id: Optional[str] = None,  # BUG #17 FIX: Accept doc_id
        flow_store = None  # NEW: Flow Vector Store for semantic memory
    ) -> List[Dict[str, Any]]:
        """
        Run comprehensive tests for this endpoint
        
        Args:
            base_url: Base URL for API
            headers: Optional HTTP headers
            test_data_store: Shared data from previous tests
            documentation_text: Full documentation text (legacy)
            doc_id: Documentation ID for Vector DB (BUG #17 FIX)
            
        Returns:
            List of test results
        """
        logger.info(f"Running tests for {self.method} {self.path}")
        
        results = []
        
        # Step 1: Generate test scenarios
        test_scenarios = await self._generate_test_scenarios()
        logger.info(f"Generated {len(test_scenarios)} test scenarios")
        
        # Step 2: Execute each test scenario
        for i, scenario in enumerate(test_scenarios):
            logger.info(f"Executing scenario {i+1}/{len(test_scenarios)}: {scenario.get('name', 'Unnamed')}")
            
            # Generate test data for this scenario
            test_data = await self._prepare_test_data(scenario, test_data_store, documentation_text)
            
            # Execute test (pass documentation_text and flow_store if executor supports it)
            try:
                result = await self.test_executor.execute_test(
                    endpoint=self.endpoint,
                    test_data=test_data,
                    base_url=base_url,
                    headers=headers,
                    documentation_text=documentation_text,
                    doc_id=doc_id,  # BUG #17 FIX: Pass doc_id to executor
                    flow_store=flow_store  # NEW: Pass flow store
                )
            except TypeError:
                # Fallback for old executor that doesn't support all parameters
                try:
                    result = await self.test_executor.execute_test(
                        endpoint=self.endpoint,
                        test_data=test_data,
                        base_url=base_url,
                        headers=headers,
                        documentation_text=documentation_text,
                        doc_id=doc_id
                    )
                except TypeError:
                    # Ultimate fallback
                    result = await self.test_executor.execute_test(
                        endpoint=self.endpoint,
                        test_data=test_data,
                        base_url=base_url,
                        headers=headers
                    )
            
            # Add scenario metadata
            result['test_case_id'] = f"{self.path}_{i}"
            result['test_case_name'] = scenario.get('name', '')
            result['endpoint'] = self.path
            result['method'] = self.method
            
            # Analyze failures with AI
            if result['status'] == 'failed' and self.gemini_provider:
                try:
                    analysis = await self.gemini_provider.analyze_test_failure(
                        endpoint=self.endpoint,
                        test_data=test_data,
                        error_response=result.get('response_data', {})
                    )
                    result['ai_analysis'] = analysis
                    
                    # If AI suggests fixes and retry is recommended
                    if analysis.get('retry_recommended') and analysis.get('suggested_fixes'):
                        logger.info("AI suggested fixes, retrying with corrected data...")
                        corrected_data = test_data.copy()
                        corrected_data.update(analysis['suggested_fixes'])
                        
                        retry_result = await self.test_executor.execute_test(
                            endpoint=self.endpoint,
                            test_data=corrected_data,
                            base_url=base_url,
                            headers=headers
                        )
                        
                        if retry_result['status'] == 'passed':
                            logger.info("Retry with AI-corrected data succeeded!")
                            result = retry_result
                            result['ai_corrected'] = True
                        
                except Exception as e:
                    logger.warning(f"AI analysis failed: {e}")
            
            results.append(result)
            
            # If this test passed, store useful response data
            if result['status'] == 'passed' and result.get('response_data'):
                self.test_data_generator.store_response_data(
                    response=result['response_data'],
                    endpoint=self.path
                )
        
        # Calculate success rate
        passed = sum(1 for r in results if r['status'] == 'passed')
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        logger.info(f"Completed tests for {self.path}: {passed}/{total} passed ({success_rate:.1f}%)")
        
        return results
    
    async def _generate_test_scenarios(self) -> List[Dict[str, Any]]:
        """Generate test scenarios for this endpoint"""
        
        # Use AI to generate scenarios if available
        if self.gemini_provider:
            try:
                scenarios = await self.gemini_provider.generate_test_scenarios(self.endpoint)
                if scenarios and len(scenarios) > 0:
                    return scenarios
            except Exception as e:
                logger.warning(f"AI scenario generation failed, using rule-based: {e}")
        
        # Fallback to rule-based scenario generation
        scenarios = []
        
        # Scenario 1: Happy path with all required fields
        scenarios.append({
            "name": "Happy path - all required fields",
            "description": "Test with all required fields populated",
            "test_data": {},  # Will be populated later
            "expected_status": 200,
            "should_fail": False
        })
        
        # Scenario 2-N: Missing required fields (one at a time)
        required_params = [p for p in self.parameters if p.get('required', False)]
        for param in required_params:
            scenarios.append({
                "name": f"Missing required field: {param.get('name')}",
                "description": f"Test with {param.get('name')} missing",
                "test_data": {"_exclude": [param.get('name')]},
                "expected_status": 400,
                "should_fail": True
            })
        
        # Scenario N+1: Empty strings for string fields (CRITICAL FIX: Exclude path params)
        string_params = [p for p in self.parameters if p.get('type', '').lower() in ['string', 'str']]
        if string_params:
            # Extract path parameters to exclude them from empty string tests
            import re
            path_params_names = set(re.findall(r'\{(\w+)\}', self.path))
            
            # Only test empty strings on non-path parameters
            testable_params = [p for p in string_params if p.get('name') not in path_params_names]
            
            if testable_params:  # Only add scenario if there are testable params
                scenarios.append({
                    "name": "Empty strings for text fields",
                    "description": "Test with empty strings (excludes path parameters)",
                    "test_data": {"_empty_strings": [p.get('name') for p in testable_params[:3]]},
                    "expected_status": 400,
                    "should_fail": True
                })
        
        return scenarios
    
    async def _prepare_test_data(
        self,
        scenario: Dict[str, Any],
        test_data_store: Optional[Dict[str, Any]] = None,
        documentation_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare test data for a scenario
        
        Args:
            scenario: Test scenario specification
            test_data_store: Shared data from previous tests
            documentation_text: Full documentation text for context
            
        Returns:
            Generated test data
        """
        # Extract path parameters from endpoint path
        import re
        path_params = re.findall(r'\{(\w+)\}', self.path)
        
        # Add path parameters to the parameters list if not already there
        param_names = {p.get('name') for p in self.parameters}
        for path_param in path_params:
            if path_param not in param_names:
                self.parameters.append({
                    'name': path_param,
                    'type': 'string',
                    'required': True,
                    'in': 'path',
                    'description': f'Path parameter {path_param}'
                })
        
        # Generate base test data WITH CONTEXT (BUG FIX: Use context-aware method)
        base_data = await self.test_data_generator.generate_test_data_with_context(
            endpoint_key=f"{self.method} {self.path}",
            parameters=self.parameters,
            test_data_store=test_data_store,
            documentation_text=documentation_text  # Pass documentation!
        )
        
        # Try to get path parameter values from test_data_store
        if test_data_store:
            for path_param in path_params:
                if path_param not in base_data or not base_data[path_param]:
                    # Try to find it in the store
                    if path_param in test_data_store:
                        base_data[path_param] = test_data_store[path_param]
                        logger.info(f"✅ Using stored value for path param {path_param}: {base_data[path_param]}")
                    else:
                        # Generate a reasonable default
                        base_data[path_param] = self._generate_path_param_value(path_param)
                        logger.warning(f"⚠️ Generated fallback value for path param {path_param}: {base_data[path_param]}")
        
        # Apply scenario-specific modifications
        test_data = base_data.copy()
        scenario_data = scenario.get('test_data', {})
        
        # Handle exclusions (for missing field tests)
        if '_exclude' in scenario_data:
            for field in scenario_data['_exclude']:
                test_data.pop(field, None)
        
        # Handle empty strings
        if '_empty_strings' in scenario_data:
            for field in scenario_data['_empty_strings']:
                if field in test_data:
                    test_data[field] = ""
        
        # Apply direct overrides
        for key, value in scenario_data.items():
            if not key.startswith('_'):
                test_data[key] = value
        
        return test_data
    
    def _generate_path_param_value(self, param_name: str) -> str:
        """Generate a reasonable value for a path parameter"""
        param_lower = param_name.lower()
        
        # Common ID patterns
        if 'id' in param_lower:
            return "123456789"
        elif 'code' in param_lower:
            return "TEST123"
        elif 'number' in param_lower or 'awb' in param_lower:
            return "1234567890"
        elif 'ticket' in param_lower:
            return "TICKET123"
        elif 'order' in param_lower:
            return "ORDER123"
        else:
            return "test-value"
    
    def get_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary of test results
        
        Args:
            results: List of test results
            
        Returns:
            Summary dictionary
        """
        total = len(results)
        passed = sum(1 for r in results if r['status'] == 'passed')
        failed = sum(1 for r in results if r['status'] == 'failed')
        
        avg_time = sum(r.get('execution_time', 0) for r in results) / total if total > 0 else 0
        
        return {
            "endpoint": self.path,
            "method": self.method,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "average_execution_time": avg_time,
            "results": results
        }

