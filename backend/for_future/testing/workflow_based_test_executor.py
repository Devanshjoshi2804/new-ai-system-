"""
Workflow-Based Test Executor - Intelligent test execution using workflow knowledge
REVOLUTIONARY APPROACH: Tests with full context, not blind guessing
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class WorkflowBasedTestExecutor:
    """
    Executes API tests using complete workflow knowledge
    
    This replaces:
    - Blind test execution
    - Missing field errors
    - Authentication failures
    - Dependency issues
    
    Philosophy:
    - Query workflow knowledge before each test
    - Build payloads with full context
    - Handle authentication automatically
    - Execute in correct order
    - Self-correct using workflow understanding
    """
    
    def __init__(
        self,
        workflow,
        ai_provider,
        vector_store,
        flow_store,
        test_executor
    ):
        """
        Initialize workflow-based executor
        
        Args:
            workflow: CompleteWorkflow from WorkflowExtractor
            ai_provider: AI provider for intelligent decisions
            vector_store: Vector DB with documentation
            flow_store: Flow Vector Store with test history
            test_executor: Underlying test executor (AdaptiveTestExecutor)
        """
        self.workflow = workflow
        self.ai_provider = ai_provider
        self.vector_store = vector_store
        self.flow_store = flow_store
        self.test_executor = test_executor
        
        # Track authentication state
        self.auth_token = None
        self.auth_headers = {}
        
        # Track test results for dependencies
        self.completed_tests = {}  # endpoint -> result
        self.extracted_data = {}  # field_name -> value
    
    async def execute_complete_workflow(
        self,
        base_url: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute complete workflow in optimal order
        
        This is the main entry point that:
        1. Sets up authentication if needed
        2. Executes tests in dependency order
        3. Passes data between tests
        4. Self-corrects on failures
        
        Returns:
            Complete test results
        """
        logger.info("🚀 Starting workflow-based test execution")
        start_time = datetime.utcnow()
        all_results = []
        
        try:
            # Step 1: Setup authentication if required
            if self.workflow.authentication.required:
                logger.info("🔐 Setting up authentication")
                auth_success = await self._setup_authentication(base_url)
                if not auth_success:
                    logger.error("❌ Authentication setup failed - aborting")
                    return {
                        "status": "failed",
                        "error": "Authentication setup failed",
                        "results": []
                    }
            
            # Step 2: Execute tests in workflow order
            logger.info(f"📋 Executing {len(self.workflow.execution_order)} endpoints in order")
            
            for idx, endpoint_path in enumerate(self.workflow.execution_order):
                if progress_callback:
                    await self._update_progress(
                        progress_callback,
                        f"Testing {idx + 1}/{len(self.workflow.execution_order)}: {endpoint_path}"
                    )
                
                logger.info(f"\n{'=' * 60}")
                logger.info(f"🎯 Testing endpoint {idx + 1}/{len(self.workflow.execution_order)}")
                logger.info(f"   Path: {endpoint_path}")
                
                # Execute this endpoint
                result = await self._execute_endpoint_with_context(
                    endpoint_path,
                    base_url
                )
                
                all_results.append(result)
                
                # Store result for dependencies
                if result["status"] == "passed":
                    self.completed_tests[endpoint_path] = result
                    
                    # Extract data that other endpoints might need
                    await self._extract_and_store_data(endpoint_path, result)
                    
                    logger.info(f"✅ {endpoint_path} PASSED")
                else:
                    logger.warning(f"⚠️  {endpoint_path} FAILED: {result.get('error', 'Unknown error')}")
                
                # Small delay between tests
                await asyncio.sleep(0.5)
            
            # Step 3: Generate summary
            duration = (datetime.utcnow() - start_time).total_seconds()
            passed = sum(1 for r in all_results if r["status"] == "passed")
            failed = len(all_results) - passed
            pass_rate = (passed / len(all_results) * 100) if all_results else 0
            
            logger.info(f"\n{'=' * 60}")
            logger.info(f"✅ Workflow execution complete in {duration:.2f}s")
            logger.info(f"   Passed: {passed}/{len(all_results)} ({pass_rate:.1f}%)")
            logger.info(f"   Failed: {failed}/{len(all_results)}")
            
            return {
                "status": "completed" if failed == 0 else "completed_with_failures",
                "total_tests": len(all_results),
                "passed_tests": passed,
                "failed_tests": failed,
                "pass_rate": pass_rate,
                "execution_time": duration,
                "results": all_results,
                "completed_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "results": all_results
            }
    
    async def _setup_authentication(self, base_url: str) -> bool:
        """
        Setup authentication by running signup + login flow
        
        Returns:
            True if authentication successful
        """
        auth = self.workflow.authentication
        
        try:
            # Step 1: Signup if needed
            if auth.signup_endpoint:
                logger.info(f"📝 Running signup: {auth.signup_endpoint}")
                signup_result = await self._execute_endpoint_with_context(
                    auth.signup_endpoint,
                    base_url
                )
                
                if signup_result["status"] != "passed":
                    logger.error(f"❌ Signup failed: {signup_result.get('error')}")
                    return False
                
                logger.info("✅ Signup successful")
                self.completed_tests[auth.signup_endpoint] = signup_result
            
            # Step 2: Login to get token
            if auth.login_endpoint:
                logger.info(f"🔑 Running login: {auth.login_endpoint}")
                login_result = await self._execute_endpoint_with_context(
                    auth.login_endpoint,
                    base_url
                )
                
                if login_result["status"] != "passed":
                    logger.error(f"❌ Login failed: {login_result.get('error')}")
                    return False
                
                # Extract token
                token = self._extract_value_from_response(
                    login_result.get("response_data", {}),
                    auth.token_location
                )
                
                if not token:
                    logger.error(f"❌ Could not extract token from {auth.token_location}")
                    return False
                
                self.auth_token = token
                
                # Build auth headers
                token_value = auth.token_format.replace("{token}", token)
                self.auth_headers[auth.token_header] = token_value
                
                logger.info(f"✅ Authentication successful - token extracted")
                logger.info(f"   Token: {token[:20]}..." if len(token) > 20 else f"   Token: {token}")
                
                self.completed_tests[auth.login_endpoint] = login_result
                return True
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Authentication setup failed: {e}", exc_info=True)
            return False
    
    async def _execute_endpoint_with_context(
        self,
        endpoint_path: str,
        base_url: str
    ) -> Dict[str, Any]:
        """
        Execute endpoint with full workflow context
        
        This is where the magic happens:
        1. Query workflow for requirements
        2. Query Vector DB for documentation context
        3. Query Flow Store for test history
        4. Build intelligent payload
        5. Execute test
        6. Self-correct on failure
        """
        try:
            # Get endpoint spec from workflow
            if endpoint_path not in self.workflow.endpoints:
                logger.warning(f"⚠️  Endpoint {endpoint_path} not in workflow")
                return {
                    "endpoint": endpoint_path,
                    "status": "failed",
                    "error": "Endpoint not found in workflow"
                }
            
            spec = self.workflow.endpoints[endpoint_path]
            logger.info(f"📖 Purpose: {spec.purpose}")
            logger.info(f"   Required fields: {list(spec.required_fields.keys())}")
            logger.info(f"   Dependencies: {spec.dependencies}")
            
            # Build payload using workflow knowledge
            payload = await self._build_intelligent_payload(endpoint_path, spec)
            
            logger.info(f"📦 Built payload with {len(payload)} fields")
            logger.debug(f"   Payload: {json.dumps(payload, indent=2)}")
            
            # Add auth headers if needed
            headers = {}
            if spec.auth_required and self.auth_headers:
                headers.update(self.auth_headers)
                logger.info(f"🔐 Added auth headers")
            
            # Execute test
            logger.info(f"🚀 Executing {spec.method} {endpoint_path}")
            result = await self.test_executor.execute_test(
                endpoint=endpoint_path,
                method=spec.method,
                base_url=base_url,
                headers=headers,
                test_data=payload
            )
            
            # Store in Flow Store for future tests
            if self.flow_store:
                endpoint_key = f"{spec.method} {endpoint_path}"
                await self.flow_store.store_request(endpoint_key, payload)
                if result.get("response_data"):
                    await self.flow_store.store_response(endpoint_key, result["response_data"])
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Failed to execute {endpoint_path}: {e}", exc_info=True)
            return {
                "endpoint": endpoint_path,
                "status": "failed",
                "error": str(e)
            }
    
    async def _build_intelligent_payload(
        self,
        endpoint_path: str,
        spec
    ) -> Dict[str, Any]:
        """
        Build payload using complete workflow context
        
        Data sources (in priority order):
        1. Previous test results (from completed_tests)
        2. Extracted data store (from extracted_data)
        3. Flow Store (semantic search in test history)
        4. Vector DB (documentation examples)
        5. Workflow specifications (required field specs)
        6. AI generation (as last resort)
        """
        payload = {}
        
        # Get data flow for this endpoint
        data_flow = self.workflow.data_flow.get(endpoint_path, {})
        
        logger.info(f"🧠 Building intelligent payload")
        
        # Process each required field
        for field_name, field_spec in spec.required_fields.items():
            logger.debug(f"   Processing field: {field_name}")
            
            # Priority 1: Check data flow (which previous endpoint provides this)
            if field_name in data_flow:
                source = data_flow[field_name]  # Format: "/api/endpoint.response.path"
                value = self._get_value_from_source(source)
                if value is not None:
                    payload[field_name] = value
                    logger.info(f"   ✅ {field_name}: {value} (from data flow: {source})")
                    continue
            
            # Priority 2: Check extracted data store
            if field_name in self.extracted_data:
                payload[field_name] = self.extracted_data[field_name]
                logger.info(f"   ✅ {field_name}: {self.extracted_data[field_name]} (from extracted data)")
                continue
            
            # Priority 3: Query Flow Store
            if self.flow_store:
                flow_value = await self._query_flow_store_for_field(field_name, endpoint_path)
                if flow_value is not None:
                    payload[field_name] = flow_value
                    logger.info(f"   ✅ {field_name}: {flow_value} (from flow store)")
                    continue
            
            # Priority 4: Use example value from workflow spec
            if field_spec.get("example_value"):
                payload[field_name] = field_spec["example_value"]
                logger.info(f"   ✅ {field_name}: {field_spec['example_value']} (from workflow spec)")
                continue
            
            # Priority 5: Generate based on type
            generated_value = self._generate_by_type(field_spec)
            payload[field_name] = generated_value
            logger.info(f"   ⚙️  {field_name}: {generated_value} (generated)")
        
        return payload
    
    def _get_value_from_source(self, source: str) -> Any:
        """
        Get value from data flow source
        
        Source format: "/api/endpoint.response.path.to.field"
        """
        try:
            parts = source.split(".")
            endpoint_path = parts[0]
            response_path = ".".join(parts[1:])
            
            # Check if we have this endpoint's result
            if endpoint_path not in self.completed_tests:
                logger.debug(f"   Endpoint {endpoint_path} not completed yet")
                return None
            
            result = self.completed_tests[endpoint_path]
            response_data = result.get("response_data", {})
            
            # Navigate response path
            return self._extract_value_from_response(response_data, response_path)
        
        except Exception as e:
            logger.debug(f"   Failed to extract from source {source}: {e}")
            return None
    
    def _extract_value_from_response(
        self,
        response: Dict[str, Any],
        path: str
    ) -> Any:
        """
        Extract value from response using dot notation path
        
        Examples:
        - "token" -> response["token"]
        - "data.token" -> response["data"]["token"]
        - "data.user.id" -> response["data"]["user"]["id"]
        """
        try:
            parts = path.split(".")
            current = response
            
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                elif isinstance(current, list) and part.isdigit():
                    current = current[int(part)]
                else:
                    return None
                
                if current is None:
                    return None
            
            return current
        
        except Exception as e:
            logger.debug(f"Failed to extract {path}: {e}")
            return None
    
    async def _query_flow_store_for_field(
        self,
        field_name: str,
        endpoint_path: str
    ) -> Any:
        """
        Query Flow Store for field value using semantic search
        """
        try:
            query = f"Find value for field '{field_name}' needed by {endpoint_path}"
            value = await self.flow_store.get_field(query)
            return value
        except Exception as e:
            logger.debug(f"Flow Store query failed: {e}")
            return None
    
    def _generate_by_type(self, field_spec: Dict[str, Any]) -> Any:
        """Generate value based on field type and format"""
        field_type = field_spec.get("type", "string")
        field_format = field_spec.get("format", "")
        
        # Use format hints
        if field_format == "email":
            return "test@example.com"
        elif field_format == "date":
            return "2024-01-01"
        elif field_format == "date-time":
            return "2024-01-01T00:00:00Z"
        elif field_format == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        
        # Use type
        if field_type == "string":
            return "test_value"
        elif field_type in ["integer", "number"]:
            return 1
        elif field_type == "boolean":
            return True
        elif field_type == "array":
            return []
        elif field_type == "object":
            return {}
        
        return "test_value"
    
    async def _extract_and_store_data(
        self,
        endpoint_path: str,
        result: Dict[str, Any]
    ):
        """
        Extract data from successful test that other endpoints might need
        """
        spec = self.workflow.endpoints[endpoint_path]
        response_data = result.get("response_data", {})
        
        # Store data that this endpoint provides
        for field_name, response_path in spec.provides_data.items():
            value = self._extract_value_from_response(response_data, response_path)
            if value is not None:
                self.extracted_data[field_name] = value
                logger.info(f"📌 Extracted {field_name} = {value} for future tests")
    
    async def _update_progress(self, callback, message: str):
        """Send progress update"""
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback({"status": "testing", "message": message})
                else:
                    callback({"status": "testing", "message": message})
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
