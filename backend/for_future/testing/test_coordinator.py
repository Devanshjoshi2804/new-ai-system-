"""
Test Coordinator - Master agent that orchestrates the entire testing workflow
"""
import logging
import asyncio
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from .dependency_analyzer import DependencyAnalyzer
from .test_data_generator import TestDataGenerator
from .test_executor import TestExecutor
from .adaptive_test_executor import AdaptiveTestExecutor
from .api_test_agent import APITestAgent
from ....infrastructure.ai.vector_store import FlowVectorStore

logger = logging.getLogger(__name__)


class TestCoordinator:
    """Master coordinator that orchestrates multi-agent API testing"""
    
    def __init__(
        self,
        ai_provider=None,
        vector_store=None,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        sequential_learning: bool = True,
        enable_flow_store: bool = True
    ):
        """
        Initialize test coordinator
        
        Args:
            ai_provider: Optional AI provider (Groq/Gemini/Mistral) for AI features
            vector_store: Optional Vector DB for focused context retrieval
            max_retries: Maximum retry attempts per test
            initial_delay: Initial retry delay in seconds
            sequential_learning: Enable sequential test execution with progressive learning
            enable_flow_store: Enable Flow Vector Store for semantic memory
        """
        self.ai_provider = ai_provider
        self.vector_store = vector_store
        # Keep backward compatibility
        self.gemini_provider = ai_provider
        
        # NEW: Flow Vector Store for semantic memory
        self.sequential_learning = sequential_learning
        self.enable_flow_store = enable_flow_store
        self.flow_store = None
        
        if enable_flow_store:
            try:
                self.flow_store = FlowVectorStore()
                logger.info("✅ Flow Vector Store enabled - semantic memory active")
                
                # Verify it's working (Fix #6)
                stats = self.flow_store.get_stats()
                if not stats:
                    raise RuntimeError("Flow Store initialized but not responding")
                logger.info(f"📊 Flow Store stats: {stats}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to initialize Flow Store: {e}")
                
                # Check if Flow Store is required (Fix #6)
                require_flow = os.getenv("REQUIRE_FLOW_STORE", "false").lower() == "true"
                
                if require_flow:
                    # Fail fast in production
                    raise RuntimeError(f"Flow Store required but failed to initialize: {e}")
                else:
                    # Graceful degradation in development
                    logger.warning("⚠️  Continuing without Flow Store (sequential learning disabled)")
                    self.flow_store = None
                    self.sequential_learning = False  # Disable if Flow Store fails
        
        # Initialize components
        self.dependency_analyzer = DependencyAnalyzer(ai_provider=ai_provider)
        self.test_data_generator = TestDataGenerator(
            ai_provider=ai_provider,
            flow_store=self.flow_store  # Pass Flow Store to data generator
        )
        
        # Use ADAPTIVE executor if AI provider available, otherwise fallback to regular
        if ai_provider:
            if vector_store:
                logger.info("🧠 Using ADAPTIVE test executor with Vector DB (AI-powered + focused context)")
            else:
                logger.info("🧠 Using ADAPTIVE test executor (AI-powered)")
            
            self.test_executor = AdaptiveTestExecutor(
                ai_provider=ai_provider,
                vector_store=vector_store,
                max_retries=max_retries,
                initial_delay=initial_delay
            )
        else:
            logger.warning("⚠️  Using regular test executor (no AI adaptation)")
            self.test_executor = TestExecutor(
                max_retries=max_retries,
                initial_delay=initial_delay
            )
        
        # State
        self.sub_agents: Dict[str, APITestAgent] = {}
        self.test_data_store = {}  # Shared data between agents
        self.all_results = []
        self.documentation_text = ""  # Store documentation for adaptive testing
        self.documentation_id = None  # BUG #17 FIX: Store doc_id to avoid passing full text
        
        mode = "SEQUENTIAL LEARNING" if sequential_learning else "PARALLEL"
        flow_status = "ENABLED" if self.flow_store else "DISABLED"
        logger.info(f"Test coordinator initialized - Mode: {mode}, Flow Store: {flow_status}")
    
    async def coordinate_testing(
        self,
        api_spec: Dict[str, Any],
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Coordinate the entire testing workflow
        
        Args:
            api_spec: API specification with endpoints
            base_url: Base URL for the API
            headers: Optional HTTP headers
            progress_callback: Optional callback for progress updates
            
        Returns:
            Complete test results
        """
        logger.info("Starting coordinated API testing")
        start_time = datetime.utcnow()
        
        # CRITICAL FIX: Extract documentation text from api_spec
        self.documentation_text = api_spec.get('documentation_text', '')
        if self.documentation_text:
            logger.info(f"📄 Loaded documentation text: {len(self.documentation_text)} chars")
        else:
            logger.warning("⚠️  No documentation text provided in api_spec")
        
        # BUG #2 FIX: Create isolated test data store per execution
        isolated_test_data_store = {}  # Fresh store for this test run
        isolated_results = []  # Fresh results list
        
        # NEW: Clear Flow Store for fresh session
        if self.flow_store:
            self.flow_store.clear_session()
            logger.info("🧹 Flow Store session cleared - starting fresh")
        
        try:
            # Phase 1: Analyze dependencies
            await self._update_progress(progress_callback, "analyzing", "Analyzing API dependencies...")
            logger.info("Phase 1: Analyzing dependencies")
            
            endpoints = api_spec.get('endpoints', [])
            if not endpoints:
                raise ValueError("No endpoints found in API specification")
            
            dependency_analysis = self.dependency_analyzer.analyze(endpoints)
            dependency_graph = dependency_analysis['dependency_graph']
            execution_order = dependency_analysis['execution_order']
            
            logger.info(f"Dependency analysis complete. Execution order: {len(execution_order)} endpoints")
            
            # Phase 1.5: Analyze workflow and data flow with AI
            workflow_analysis = {}
            data_mappings = {}
            login_flow = {}
            
            # Store documentation text for adaptive testing
            self.documentation_text = api_spec.get('documentation_text', '')
            
            if self.gemini_provider:
                try:
                    await self._update_progress(progress_callback, "analyzing_workflow", "Analyzing workflows and data dependencies...")
                    logger.info("Phase 1.5: Analyzing workflow with Gemini")
                    
                    # Get documentation text if available
                    doc_text = self.documentation_text
                    
                    workflow_analysis = await self.gemini_provider.analyze_workflow_and_data_flow(
                        endpoints=endpoints,
                        documentation_text=doc_text
                    )
                    
                    login_flow = workflow_analysis.get('login_flow', {})
                    data_mappings = workflow_analysis.get('data_mappings', {})
                    workflows = workflow_analysis.get('workflows', [])
                    
                    logger.info(f"✅ Workflow analysis complete: {len(workflows)} workflows, {len(data_mappings)} data mappings")
                    
                    # Handle login flow if required
                    if login_flow.get('required'):
                        login_endpoint = login_flow.get('endpoint')
                        logger.info(f"🔐 Login required: {login_endpoint}")
                        
                        # Execute login first
                        login_result = await self._execute_login_flow(
                            login_flow=login_flow,
                            base_url=base_url,
                            headers=headers
                        )
                        
                        if login_result.get('success'):
                            logger.info("✅ Login successful, token stored")
                            # Update headers with auth token
                            if headers is None:
                                headers = {}
                            token_header = login_flow.get('token_header', 'Authorization')
                            token_format = login_flow.get('token_format', 'Bearer {token}')
                            token = login_result.get('token')
                            if token:
                                headers[token_header] = token_format.replace('{token}', token)
                                logger.info(f"Added auth header: {token_header}")
                        else:
                            logger.warning("⚠️ Login failed, continuing without authentication")
                    
                except Exception as e:
                    logger.warning(f"Workflow analysis failed, continuing with basic analysis: {e}")
            
            # Phase 2: Create sub-agents
            await self._update_progress(progress_callback, "creating_agents", "Creating specialized test agents...")
            logger.info("Phase 2: Creating sub-agents")
            
            for endpoint in endpoints:
                path = endpoint.get('path', '')
                agent = APITestAgent(
                    endpoint=endpoint,
                    test_executor=self.test_executor,
                    test_data_generator=self.test_data_generator,
                    gemini_provider=self.gemini_provider
                )
                self.sub_agents[path] = agent
            
            logger.info(f"Created {len(self.sub_agents)} sub-agents")
            
            # Phase 3: Execute tests with intelligent execution (sequential or parallel)
            await self._update_progress(progress_callback, "testing", "Executing API tests...")
            execution_mode = "SEQUENTIAL with learning" if self.sequential_learning else "PARALLEL"
            logger.info(f"Phase 3: Executing tests with {execution_mode}")
            
            total_endpoints = len(execution_order)
            tested_endpoints = 0
            
            # Group endpoints by dependency level
            dependency_levels = self._group_by_dependency_level(execution_order, dependency_graph)
            logger.info(f"Grouped endpoints into {len(dependency_levels)} dependency levels")
            
            for level_idx, level_endpoints in enumerate(dependency_levels):
                exec_mode_desc = "sequentially" if self.sequential_learning else "in parallel"
                logger.info(f"Level {level_idx + 1}/{len(dependency_levels)}: Testing {len(level_endpoints)} endpoints {exec_mode_desc}")
                
                # Update progress
                await self._update_progress(
                    progress_callback,
                    "testing",
                    f"Testing level {level_idx + 1}/{len(dependency_levels)} ({len(level_endpoints)} endpoints)...",
                    {
                        "current_level": level_idx + 1,
                        "total_levels": len(dependency_levels),
                        "tested_endpoints": tested_endpoints,
                        "total_endpoints": total_endpoints
                    }
                )
                
                # NEW: Sequential learning mode
                if self.sequential_learning and self.flow_store:
                    # Execute endpoints one by one, storing in Flow DB after each
                    for endpoint_path in level_endpoints:
                        agent = self.sub_agents.get(endpoint_path)
                        if agent:
                            try:
                                results = await agent.run_tests(
                                    base_url=base_url,
                                    headers=headers,
                                    test_data_store=isolated_test_data_store,
                                    documentation_text=self.documentation_text,
                                    doc_id=self.documentation_id,
                                    flow_store=self.flow_store  # NEW: Pass Flow Store
                                )
                                
                                self.all_results.extend(results)
                                isolated_results.extend(results)
                                
                                # Store in Flow DB immediately after each test
                                for result in results:
                                    endpoint_key = f"{result.get('method', 'GET')} {result.get('endpoint', endpoint_path)}"
                                    
                                    # Store request
                                    if result.get('request_data'):
                                        await self.flow_store.store_request(
                                            endpoint_key,
                                            result['request_data']
                                        )
                                    
                                    # Store response
                                    if result.get('response_data'):
                                        await self.flow_store.store_response(
                                            endpoint_key,
                                            result['response_data']
                                        )
                                
                                # Small delay for embedding generation
                                await asyncio.sleep(0.3)
                                
                                # Also store in test data generator for backward compatibility
                                for result in results:
                                    if result['status'] == 'passed' and result.get('response_data'):
                                        self.test_data_generator.store_response_data(
                                            response=result['response_data'],
                                            endpoint=result.get('endpoint', '')
                                        )
                                
                                tested_endpoints += 1
                                logger.info(f"✅ Tested {tested_endpoints}/{total_endpoints} endpoints")
                                
                            except Exception as e:
                                logger.error(f"Error testing {endpoint_path}: {e}", exc_info=True)
                                tested_endpoints += 1
                
                # Parallel execution for independent endpoints
                elif len(level_endpoints) > 1:
                    # Parallel execution for independent endpoints
                    level_results = await self._execute_endpoints_in_parallel(
                        endpoint_paths=level_endpoints,
                        base_url=base_url,
                        headers=headers,
                        progress_callback=progress_callback
                    )
                    self.all_results.extend(level_results)
                    isolated_results.extend(level_results)  # BUG #2 FIX
                    
                    # BUG #23 FIX: Check if any endpoints in this level failed
                    level_failed = sum(1 for r in level_results if r['status'] == 'failed')
                    if level_failed > 0:
                        logger.warning(f"⚠️  Level {level_idx + 1}: {level_failed}/{len(level_endpoints)} endpoints failed")
                        logger.warning(f"⚠️  Dependent endpoints in next levels may also fail!")
                    
                    # Store successful results for dependencies
                    for result in level_results:
                        if result['status'] == 'passed' and result.get('response_data'):
                            self.test_data_generator.store_response_data(
                                response=result['response_data'],
                                endpoint=result.get('endpoint', '')
                            )
                
                else:
                    # Single endpoint, execute normally
                    endpoint_path = level_endpoints[0]
                    agent = self.sub_agents.get(endpoint_path)
                    if agent:
                        try:
                            results = await agent.run_tests(
                                base_url=base_url,
                                headers=headers,
                                test_data_store=isolated_test_data_store,  # BUG #2 FIX: Use isolated store
                                documentation_text=self.documentation_text,
                                doc_id=self.documentation_id,  # BUG #17 FIX: Pass doc_id
                                flow_store=self.flow_store  # CRITICAL FIX: Pass Flow Store
                            )
                            self.all_results.extend(results)
                            isolated_results.extend(results)  # BUG #2 FIX: Also store in isolated results
                            
                            # BUG #23 FIX: Check if this endpoint failed
                            endpoint_failed = any(r['status'] == 'failed' for r in results)
                            if endpoint_failed:
                                logger.warning(f"⚠️  Endpoint {endpoint_path} failed!")
                                logger.warning(f"⚠️  Dependent endpoints may not have required data!")
                            
                            # Store successful results for dependencies
                            for result in results:
                                if result['status'] == 'passed' and result.get('response_data'):
                                    self.test_data_generator.store_response_data(
                                        response=result['response_data'],
                                        endpoint=endpoint_path
                                    )
                        except Exception as e:
                            logger.error(f"Error testing {endpoint_path}: {e}")
                
                tested_endpoints += len(level_endpoints)
                logger.info(f"✅ Level {level_idx + 1} complete: {tested_endpoints}/{total_endpoints} endpoints tested")
            
            # Phase 4: Aggregate and analyze results
            await self._update_progress(progress_callback, "analyzing_results", "Analyzing test results...")
            logger.info("Phase 4: Aggregating results")
            
            # BUG #2 FIX: Use isolated_results for this execution instead of self.all_results
            summary = self._generate_summary_from_results(
                isolated_results,  # Use isolated results
                endpoints=endpoints,
                execution_order=execution_order,
                dependency_graph=dependency_graph
            )
            
            end_time = datetime.utcnow()
            summary['started_at'] = start_time
            summary['completed_at'] = end_time
            summary['total_execution_time'] = (end_time - start_time).total_seconds()
            
            # Determine overall status
            if summary['failed_tests'] == 0:
                summary['status'] = 'completed'
            elif summary['passed_tests'] > 0:
                summary['status'] = 'completed_with_failures'
            else:
                summary['status'] = 'failed'
            
            await self._update_progress(progress_callback, summary['status'], "Testing complete")
            
            logger.info(f"Testing complete: {summary['passed_tests']}/{summary['total_tests']} passed")
            
            return summary
            
        except Exception as e:
            logger.error(f"Fatal error during testing: {e}")
            await self._update_progress(progress_callback, "failed", f"Testing failed: {str(e)}")
            raise
    
    def _generate_summary(
        self,
        endpoints: List[Dict[str, Any]],
        execution_order: List[str],
        dependency_graph: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Generate comprehensive testing summary (DEPRECATED - use _generate_summary_from_results)"""
        return self._generate_summary_from_results(
            self.all_results, endpoints, execution_order, dependency_graph
        )
    
    def _generate_summary_from_results(
        self,
        results: List[Dict[str, Any]],
        endpoints: List[Dict[str, Any]],
        execution_order: List[str],
        dependency_graph: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Generate comprehensive testing summary from specific result set (BUG #2 FIX)"""
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['status'] == 'passed')
        failed_tests = sum(1 for r in results if r['status'] == 'failed')
        
        # Calculate average response time
        execution_times = [r.get('execution_time', 0) for r in results if r.get('execution_time')]
        avg_response_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Group results by endpoint
        results_by_endpoint = {}
        for result in results:
            endpoint = result.get('endpoint', 'unknown')
            if endpoint not in results_by_endpoint:
                results_by_endpoint[endpoint] = []
            results_by_endpoint[endpoint].append(result)
        
        # Generate per-endpoint summaries
        endpoint_summaries = []
        for endpoint_path in execution_order:
            endpoint_results = results_by_endpoint.get(endpoint_path, [])
            if endpoint_results:
                ep_passed = sum(1 for r in endpoint_results if r['status'] == 'passed')
                ep_total = len(endpoint_results)
                endpoint_summaries.append({
                    "endpoint": endpoint_path,
                    "total_tests": ep_total,
                    "passed": ep_passed,
                    "failed": ep_total - ep_passed,
                    "success_rate": (ep_passed / ep_total * 100) if ep_total > 0 else 0
                })
        
        return {
            "total_endpoints": len(endpoints),
            "tested_endpoints": len([ep for ep in execution_order if ep in results_by_endpoint]),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": 0,
            "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "average_response_time": avg_response_time,
            "dependency_graph": dependency_graph,
            "execution_order": execution_order,
            "endpoint_summaries": endpoint_summaries,
            "test_results": self.all_results,
            "test_data_store": self.test_data_store
        }
    
    async def _update_progress(
        self,
        callback: Optional[callable],
        status: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """Send progress update via callback"""
        if callback:
            try:
                update = {
                    "status": status,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
                if data:
                    update.update(data)
                
                if asyncio.iscoroutinefunction(callback):
                    await callback(update)
                else:
                    callback(update)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    async def _execute_login_flow(
        self,
        login_flow: Dict[str, Any],
        base_url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute login flow and extract authentication data
        
        Args:
            login_flow: Login flow configuration from workflow analysis
            base_url: Base URL for the API
            headers: Optional HTTP headers
            
        Returns:
            Login result with token and extracted data
        """
        try:
            endpoint = login_flow.get('endpoint')
            method = login_flow.get('method', 'POST')
            credentials = login_flow.get('credentials', {})
            token_extraction = login_flow.get('token_extraction', 'token')
            additional_extractions = login_flow.get('additional_extractions', {})
            
            logger.info(f"🔐 Executing login flow: {method} {endpoint}")
            logger.info(f"Credentials: {list(credentials.keys())}")
            
            # Execute login request
            result = await self.test_executor.execute_test(
                endpoint=endpoint,
                method=method,
                base_url=base_url,
                headers=headers or {},
                test_data=credentials
            )
            
            if result.get('status') != 'passed':
                logger.error(f"❌ Login failed: {result.get('error')}")
                return {"success": False, "error": result.get('error')}
            
            response_data = result.get('response_data', {})
            
            # Extract token
            token = self.test_data_generator.extract_value_by_path(response_data, token_extraction)
            if not token:
                logger.warning(f"⚠️ Could not extract token from path: {token_extraction}")
                return {"success": False, "error": "Token not found in response"}
            
            logger.info(f"✅ Token extracted: {token[:20]}..." if len(str(token)) > 20 else f"✅ Token extracted: {token}")
            
            # Store login response for data extraction
            self.test_data_store[endpoint] = response_data
            
            # Extract additional data
            extracted_data = {"token": token}
            for key, path in additional_extractions.items():
                value = self.test_data_generator.extract_value_by_path(response_data, path)
                if value:
                    extracted_data[key] = value
                    self.test_data_store[key] = value
                    logger.info(f"✅ Extracted {key}: {value}")
            
            return {
                "success": True,
                "token": token,
                "extracted_data": extracted_data,
                "response": response_data
            }
            
        except Exception as e:
            logger.error(f"❌ Login flow execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_endpoints_in_parallel(
        self,
        endpoint_paths: List[str],
        base_url: str,
        headers: Optional[Dict[str, str]],
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple independent endpoints in parallel for faster testing
        
        Args:
            endpoint_paths: List of endpoint paths to test
            base_url: Base URL for the API
            headers: Optional HTTP headers
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of test results
        """
        logger.info(f"🚀 Executing {len(endpoint_paths)} endpoints in parallel")
        
        async def test_endpoint(endpoint_path: str):
            agent = self.sub_agents.get(endpoint_path)
            if not agent:
                logger.warning(f"No agent found for {endpoint_path}")
                return []
            
            try:
                results = await agent.run_tests(
                    base_url=base_url,
                    headers=headers,
                    test_data_store=self.test_data_store,
                    documentation_text=self.documentation_text,
                    doc_id=self.documentation_id,  # Pass doc_id
                    flow_store=self.flow_store  # CRITICAL FIX: Pass Flow Store
                )
                
                # Store successful results
                for result in results:
                    if result['status'] == 'passed' and result.get('response_data'):
                        self.test_data_generator.store_response_data(
                            response=result['response_data'],
                            endpoint=endpoint_path
                        )
                
                return results
            except Exception as e:
                logger.error(f"Error testing {endpoint_path}: {e}")
                return []
        
        # Execute all endpoints in parallel
        results_lists = await asyncio.gather(*[test_endpoint(ep) for ep in endpoint_paths])
        
        # Flatten results
        all_results = []
        for results in results_lists:
            all_results.extend(results)
        
        logger.info(f"✅ Parallel execution complete: {len(all_results)} tests executed")
        return all_results
    
    def _group_by_dependency_level(
        self,
        execution_order: List[str],
        dependency_graph: Dict[str, List[str]]
    ) -> List[List[str]]:
        """
        Group endpoints by dependency level for parallel execution
        
        Endpoints at the same level have no dependencies on each other
        and can be executed in parallel.
        
        Args:
            execution_order: Ordered list of endpoints
            dependency_graph: Dependency relationships
            
        Returns:
            List of levels, where each level is a list of endpoints that can run in parallel
        """
        levels = []
        processed = set()
        remaining = set(execution_order)
        
        while remaining:
            # Find all endpoints that have no unprocessed dependencies
            current_level = []
            for endpoint in execution_order:
                if endpoint in processed:
                    continue
                
                # Check if all dependencies are processed
                dependencies = dependency_graph.get(endpoint, [])
                if all(dep in processed or dep not in execution_order for dep in dependencies):
                    current_level.append(endpoint)
            
            if not current_level:
                # No progress made, add remaining endpoints to avoid infinite loop
                logger.warning("Circular dependency detected, adding remaining endpoints")
                current_level = list(remaining)
            
            levels.append(current_level)
            processed.update(current_level)
            remaining -= set(current_level)
        
        return levels

