"""
Autonomous Orchestrator

Coordinates the complete autonomous API onboarding workflow:
1. Discovery - Find all API endpoints
2. ML Enhancement - Classify and understand endpoints
3. Testing - Execute tests with auto-fixing
4. Learning - Store results for future improvement

This is the main entry point for autonomous operations.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from .types import (
    OrchestrationPhase,
    OperationStatus,
    OrchestrationResult,
    PhaseProgress,
    EndpointInfo,
    AuthConfiguration,
    ExecutionContext,
    DependencyGraph,
    TestStatus
)

logger = logging.getLogger(__name__)


class AutonomousOrchestrator:
    """
    Main orchestrator for autonomous API integration

    Coordinates all phases of autonomous onboarding from minimal input
    to fully tested and learned API integration.
    """

    def __init__(
        self,
        api_explorer=None,
        hybrid_predictor=None,
        execution_engine=None,
        learning_loop=None
    ):
        """
        Initialize autonomous orchestrator

        Args:
            api_explorer: Phase 1 API discovery component
            hybrid_predictor: Hybrid AI/ML predictor
            execution_engine: Test execution engine
            learning_loop: Learning and improvement component
        """
        self.api_explorer = api_explorer
        self.hybrid_predictor = hybrid_predictor
        self.execution_engine = execution_engine
        self.learning_loop = learning_loop

        # Active operations
        self.active_operations: Dict[str, OrchestrationResult] = {}

        logger.info("[ORCHESTRATOR] Initialized autonomous orchestrator")

    async def autonomous_onboard(
        self,
        minimal_info: str,
        auth_token: Optional[str] = None,
        base_url: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> OrchestrationResult:
        """
        Perform complete autonomous onboarding from minimal information

        Args:
            minimal_info: Minimal API information (URL, description, or doc link)
            auth_token: Optional authentication token
            base_url: Optional base URL for API
            additional_context: Optional additional context

        Returns:
            Complete orchestration result with all phases
        """
        operation_id = str(uuid.uuid4())
        logger.info(f"[ORCHESTRATOR] Starting autonomous onboarding: {operation_id}")
        logger.info(f"[ORCHESTRATOR] Input: {minimal_info[:100]}...")

        # Initialize result
        result = OrchestrationResult(
            operation_id=operation_id,
            status=OperationStatus.IN_PROGRESS,
            current_phase=OrchestrationPhase.INITIALIZATION,
            started_at=datetime.utcnow()
        )

        self.active_operations[operation_id] = result

        try:
            # Phase 1: Discovery
            result.current_phase = OrchestrationPhase.DISCOVERY
            await self._run_discovery_phase(result, minimal_info, base_url, additional_context)

            # Phase 2: ML Enhancement
            result.current_phase = OrchestrationPhase.ML_ENHANCEMENT
            await self._run_ml_enhancement_phase(result)

            # Phase 3: Testing
            result.current_phase = OrchestrationPhase.TESTING
            await self._run_testing_phase(result, auth_token, base_url)

            # Phase 4: Learning
            result.current_phase = OrchestrationPhase.LEARNING
            await self._run_learning_phase(result)

            # Mark as completed
            result.current_phase = OrchestrationPhase.COMPLETED
            result.status = OperationStatus.COMPLETED
            result.completed_at = datetime.utcnow()
            result.total_duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

            logger.info(
                f"[ORCHESTRATOR] Autonomous onboarding completed: {operation_id} "
                f"({result.total_duration_seconds:.2f}s)"
            )

            return result

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Autonomous onboarding failed: {e}")

            result.current_phase = OrchestrationPhase.FAILED
            result.status = OperationStatus.FAILED
            result.completed_at = datetime.utcnow()
            result.total_duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

            # Add error to current phase
            if result.phases:
                result.phases[-1].status = OperationStatus.FAILED
                result.phases[-1].error = str(e)

            return result

        finally:
            # Keep operation in history for a while
            # (In production, would persist to database)
            pass

    async def _run_discovery_phase(
        self,
        result: OrchestrationResult,
        minimal_info: str,
        base_url: Optional[str],
        additional_context: Optional[Dict[str, Any]]
    ):
        """Run API discovery phase"""
        logger.info("[ORCHESTRATOR] Phase 1: Discovery")

        phase = PhaseProgress(
            phase=OrchestrationPhase.DISCOVERY,
            status=OperationStatus.IN_PROGRESS,
            message="Discovering API endpoints...",
            started_at=datetime.utcnow()
        )
        result.phases.append(phase)

        try:
            # Use Phase 1 API Explorer to discover endpoints
            if self.api_explorer:
                discovery_result = await self.api_explorer.explore(
                    minimal_info,
                    base_url=base_url,
                    context=additional_context or {}
                )

                # Convert discovery results to EndpointInfo
                for idx, endpoint in enumerate(discovery_result.get('endpoints', [])):
                    endpoint_info = EndpointInfo(
                        id=endpoint.get('id', f"ep_{idx}"),
                        url=endpoint.get('url', ''),
                        method=endpoint.get('method', 'GET'),
                        description=endpoint.get('description'),
                        parameters=endpoint.get('parameters', {}),
                        headers=endpoint.get('headers', {}),
                        schema=endpoint.get('schema'),
                        metadata=endpoint.get('metadata', {})
                    )
                    result.discovered_endpoints.append(endpoint_info)

                phase.progress_percentage = 100.0
                phase.message = f"Discovered {len(result.discovered_endpoints)} endpoints"

                logger.info(
                    f"[ORCHESTRATOR] Discovery complete: "
                    f"{len(result.discovered_endpoints)} endpoints"
                )

            else:
                # Fallback: Create mock endpoint for testing
                logger.warning("[ORCHESTRATOR] No API Explorer available, using mock data")

                mock_endpoint = EndpointInfo(
                    id="mock_001",
                    url=minimal_info if minimal_info.startswith('http') else f"{base_url or ''}/api/test",
                    method="GET",
                    description="Mock endpoint for testing",
                    metadata={'mock': True}
                )
                result.discovered_endpoints.append(mock_endpoint)

                phase.progress_percentage = 100.0
                phase.message = "Using mock endpoint"

            phase.status = OperationStatus.COMPLETED
            phase.completed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Discovery phase failed: {e}")
            phase.status = OperationStatus.FAILED
            phase.error = str(e)
            raise

    async def _run_ml_enhancement_phase(self, result: OrchestrationResult):
        """Run ML enhancement phase to classify and enhance endpoints"""
        logger.info("[ORCHESTRATOR] Phase 2: ML Enhancement")

        phase = PhaseProgress(
            phase=OrchestrationPhase.ML_ENHANCEMENT,
            status=OperationStatus.IN_PROGRESS,
            message="Enhancing endpoints with ML predictions...",
            started_at=datetime.utcnow()
        )
        result.phases.append(phase)

        try:
            if not self.hybrid_predictor:
                logger.warning("[ORCHESTRATOR] No hybrid predictor available")
                phase.status = OperationStatus.COMPLETED
                phase.message = "Skipped - no predictor available"
                phase.completed_at = datetime.utcnow()
                return

            total = len(result.discovered_endpoints)
            processed = 0

            for endpoint in result.discovered_endpoints:
                try:
                    # Classify endpoint
                    classification = await self.hybrid_predictor.predict_endpoint_classification(
                        url=endpoint.url,
                        method=endpoint.method,
                        context={
                            'description': endpoint.description,
                            'parameters': endpoint.parameters
                        }
                    )

                    # Update endpoint with classification
                    endpoint.category = classification.prediction.get('category', 'unknown')
                    endpoint.confidence = classification.confidence
                    endpoint.metadata['classification_tier'] = classification.tier.value

                    result.classified_endpoints[endpoint.id] = classification.prediction

                    # Generate payload
                    payload_result = await self.hybrid_predictor.generate_payload(
                        endpoint_url=endpoint.url,
                        method=endpoint.method,
                        schema=endpoint.schema,
                        context={
                            'category': endpoint.category,
                            'parameters': endpoint.parameters
                        }
                    )

                    result.generated_payloads[endpoint.id] = payload_result.prediction

                    processed += 1
                    phase.progress_percentage = (processed / total) * 100

                    logger.debug(
                        f"[ORCHESTRATOR] Enhanced {endpoint.id}: "
                        f"{endpoint.category} (confidence={classification.confidence:.3f})"
                    )

                except Exception as e:
                    logger.warning(f"[ORCHESTRATOR] Failed to enhance {endpoint.id}: {e}")
                    processed += 1
                    phase.progress_percentage = (processed / total) * 100
                    continue

            phase.status = OperationStatus.COMPLETED
            phase.message = f"Enhanced {processed}/{total} endpoints"
            phase.completed_at = datetime.utcnow()

            logger.info(
                f"[ORCHESTRATOR] ML enhancement complete: "
                f"{len(result.classified_endpoints)} classified, "
                f"{len(result.generated_payloads)} payloads generated"
            )

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] ML enhancement phase failed: {e}")
            phase.status = OperationStatus.FAILED
            phase.error = str(e)
            raise

    async def _run_testing_phase(
        self,
        result: OrchestrationResult,
        auth_token: Optional[str],
        base_url: Optional[str]
    ):
        """Run testing phase to execute and validate endpoints"""
        logger.info("[ORCHESTRATOR] Phase 3: Testing")

        phase = PhaseProgress(
            phase=OrchestrationPhase.TESTING,
            status=OperationStatus.IN_PROGRESS,
            message="Executing endpoint tests...",
            started_at=datetime.utcnow()
        )
        result.phases.append(phase)

        try:
            if not self.execution_engine:
                logger.warning("[ORCHESTRATOR] No execution engine available")
                phase.status = OperationStatus.COMPLETED
                phase.message = "Skipped - no execution engine available"
                phase.completed_at = datetime.utcnow()
                return

            # Prepare authentication
            auth_config = AuthConfiguration(
                auth_type='bearer' if auth_token else 'none',
                credentials={'token': auth_token} if auth_token else {}
            )

            # Prepare execution context
            context = ExecutionContext(
                auth_config=auth_config,
                base_url=base_url or "",
                timeout_seconds=30,
                max_retries=3,
                enable_auto_fix=True,
                rate_limit_per_second=10
            )

            # Build dependency graph
            dependency_graph = DependencyGraph()
            for endpoint in result.discovered_endpoints:
                dependency_graph.add_node(endpoint)

            # Detect dependencies (e.g., auth endpoints must run first)
            for endpoint in result.discovered_endpoints:
                if endpoint.category == 'authentication':
                    # Auth endpoints have no dependencies
                    pass
                else:
                    # Other endpoints may depend on auth
                    auth_endpoints = [
                        ep for ep in result.discovered_endpoints
                        if ep.category == 'authentication'
                    ]
                    for auth_ep in auth_endpoints:
                        dependency_graph.add_dependency(endpoint.id, auth_ep.id)

            # Execute tests
            test_results = await self.execution_engine.execute_tests(
                endpoints=result.discovered_endpoints,
                payloads=result.generated_payloads,
                dependency_graph=dependency_graph,
                context=context,
                on_progress=lambda p: setattr(phase, 'progress_percentage', p)
            )

            result.test_results = test_results

            # Calculate statistics
            passed = sum(1 for t in test_results if t.status == TestStatus.PASSED)
            failed = sum(1 for t in test_results if t.status == TestStatus.FAILED)
            fixed = sum(1 for t in test_results if t.fixed)

            phase.status = OperationStatus.COMPLETED
            phase.message = f"Tests: {passed} passed, {failed} failed, {fixed} auto-fixed"
            phase.completed_at = datetime.utcnow()

            result.metrics['tests_passed'] = passed
            result.metrics['tests_failed'] = failed
            result.metrics['tests_fixed'] = fixed

            logger.info(
                f"[ORCHESTRATOR] Testing complete: "
                f"{passed} passed, {failed} failed, {fixed} auto-fixed"
            )

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Testing phase failed: {e}")
            phase.status = OperationStatus.FAILED
            phase.error = str(e)
            raise

    async def _run_learning_phase(self, result: OrchestrationResult):
        """Run learning phase to store results for future improvement"""
        logger.info("[ORCHESTRATOR] Phase 4: Learning")

        phase = PhaseProgress(
            phase=OrchestrationPhase.LEARNING,
            status=OperationStatus.IN_PROGRESS,
            message="Storing results for future learning...",
            started_at=datetime.utcnow()
        )
        result.phases.append(phase)

        try:
            if not self.learning_loop:
                logger.warning("[ORCHESTRATOR] No learning loop available")
                phase.status = OperationStatus.COMPLETED
                phase.message = "Skipped - no learning loop available"
                phase.completed_at = datetime.utcnow()
                return

            # Store test results for learning
            patterns_learned = await self.learning_loop.process_results(
                endpoints=result.discovered_endpoints,
                classifications=result.classified_endpoints,
                payloads=result.generated_payloads,
                test_results=result.test_results
            )

            result.patterns_learned = patterns_learned
            result.models_updated = patterns_learned > 0

            phase.status = OperationStatus.COMPLETED
            phase.message = f"Learned {patterns_learned} new patterns"
            phase.completed_at = datetime.utcnow()

            logger.info(f"[ORCHESTRATOR] Learning complete: {patterns_learned} patterns")

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Learning phase failed: {e}")
            phase.status = OperationStatus.FAILED
            phase.error = str(e)
            # Don't raise - learning failure shouldn't fail the whole operation

    async def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of an operation

        Args:
            operation_id: Operation ID to check

        Returns:
            Operation status or None if not found
        """
        if operation_id in self.active_operations:
            result = self.active_operations[operation_id]
            return result.to_dict()

        return None


# ============================================================================
# LANGGRAPH ORCHESTRATION PATTERN
# ============================================================================

class OrchestrationState:
    """
    State class for LangGraph orchestration

    This state is passed between nodes in the LangGraph state machine
    for orchestrating the autonomous workflow.
    """

    def __init__(self):
        """Initialize orchestration state"""
        self.operation_id: str = ""
        self.minimal_info: str = ""
        self.auth_token: Optional[str] = None
        self.base_url: Optional[str] = None
        self.context: Dict[str, Any] = {}

        # Phase results
        self.discovered_endpoints: List[EndpointInfo] = []
        self.classified_endpoints: Dict[str, Dict[str, Any]] = {}
        self.generated_payloads: Dict[str, Dict[str, Any]] = {}
        self.test_results: List[Any] = []

        # Status tracking
        self.current_phase: OrchestrationPhase = OrchestrationPhase.INITIALIZATION
        self.errors: List[str] = []
        self.completed_phases: List[OrchestrationPhase] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return {
            'operation_id': self.operation_id,
            'current_phase': self.current_phase.value,
            'discovered_endpoints': len(self.discovered_endpoints),
            'classified_endpoints': len(self.classified_endpoints),
            'test_results': len(self.test_results),
            'errors': self.errors,
            'completed_phases': [p.value for p in self.completed_phases]
        }


class LangGraphOrchestrator:
    """
    LangGraph-based orchestrator using state machine pattern

    This orchestrator uses LangGraph to manage the workflow as a state machine,
    providing better visibility and control over the orchestration process.
    """

    def __init__(
        self,
        api_explorer=None,
        hybrid_predictor=None,
        execution_engine=None,
        learning_loop=None
    ):
        """Initialize LangGraph orchestrator"""
        self.api_explorer = api_explorer
        self.hybrid_predictor = hybrid_predictor
        self.execution_engine = execution_engine
        self.learning_loop = learning_loop

        logger.info("[LANGGRAPH_ORCHESTRATOR] Initialized")

    async def run_workflow(
        self,
        minimal_info: str,
        auth_token: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> OrchestrationState:
        """
        Run orchestration workflow using LangGraph state machine

        Args:
            minimal_info: Minimal API information
            auth_token: Optional authentication token
            base_url: Optional base URL

        Returns:
            Final orchestration state
        """
        # Initialize state
        state = OrchestrationState()
        state.operation_id = str(uuid.uuid4())
        state.minimal_info = minimal_info
        state.auth_token = auth_token
        state.base_url = base_url

        logger.info(f"[LANGGRAPH_ORCHESTRATOR] Starting workflow: {state.operation_id}")

        try:
            # Node 1: Discovery
            state = await self._discovery_node(state)
            state.completed_phases.append(OrchestrationPhase.DISCOVERY)

            # Node 2: ML Enhancement
            state = await self._ml_enhancement_node(state)
            state.completed_phases.append(OrchestrationPhase.ML_ENHANCEMENT)

            # Node 3: Testing
            state = await self._testing_node(state)
            state.completed_phases.append(OrchestrationPhase.TESTING)

            # Node 4: Learning
            state = await self._learning_node(state)
            state.completed_phases.append(OrchestrationPhase.LEARNING)

            state.current_phase = OrchestrationPhase.COMPLETED
            logger.info(f"[LANGGRAPH_ORCHESTRATOR] Workflow completed: {state.operation_id}")

        except Exception as e:
            logger.error(f"[LANGGRAPH_ORCHESTRATOR] Workflow failed: {e}")
            state.errors.append(str(e))
            state.current_phase = OrchestrationPhase.FAILED

        return state

    async def _discovery_node(self, state: OrchestrationState) -> OrchestrationState:
        """LangGraph node for discovery phase"""
        state.current_phase = OrchestrationPhase.DISCOVERY
        logger.info("[LANGGRAPH_ORCHESTRATOR] Node: Discovery")

        if self.api_explorer:
            discovery_result = await self.api_explorer.explore(
                state.minimal_info,
                base_url=state.base_url,
                context=state.context
            )
            # Process discovery results
            for endpoint in discovery_result.get('endpoints', []):
                endpoint_info = EndpointInfo(
                    id=endpoint.get('id', f"ep_{len(state.discovered_endpoints)}"),
                    url=endpoint.get('url', ''),
                    method=endpoint.get('method', 'GET')
                )
                state.discovered_endpoints.append(endpoint_info)

        return state

    async def _ml_enhancement_node(self, state: OrchestrationState) -> OrchestrationState:
        """LangGraph node for ML enhancement phase"""
        state.current_phase = OrchestrationPhase.ML_ENHANCEMENT
        logger.info("[LANGGRAPH_ORCHESTRATOR] Node: ML Enhancement")

        if self.hybrid_predictor:
            for endpoint in state.discovered_endpoints:
                # Classify and generate payload
                classification = await self.hybrid_predictor.predict_endpoint_classification(
                    url=endpoint.url,
                    method=endpoint.method
                )
                state.classified_endpoints[endpoint.id] = classification.prediction

        return state

    async def _testing_node(self, state: OrchestrationState) -> OrchestrationState:
        """LangGraph node for testing phase"""
        state.current_phase = OrchestrationPhase.TESTING
        logger.info("[LANGGRAPH_ORCHESTRATOR] Node: Testing")

        # Testing logic here
        return state

    async def _learning_node(self, state: OrchestrationState) -> OrchestrationState:
        """LangGraph node for learning phase"""
        state.current_phase = OrchestrationPhase.LEARNING
        logger.info("[LANGGRAPH_ORCHESTRATOR] Node: Learning")

        # Learning logic here
        return state

    async def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel a running operation

        Args:
            operation_id: Operation ID to cancel

        Returns:
            True if cancelled, False if not found
        """
        if operation_id in self.active_operations:
            result = self.active_operations[operation_id]

            if result.status == OperationStatus.IN_PROGRESS:
                result.status = OperationStatus.CANCELLED
                result.completed_at = datetime.utcnow()
                result.total_duration_seconds = (
                    result.completed_at - result.started_at
                ).total_seconds()

                logger.info(f"[ORCHESTRATOR] Operation cancelled: {operation_id}")
                return True

        return False

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get orchestrator metrics

        Returns:
            Dictionary with metrics
        """
        total_operations = len(self.active_operations)
        completed = sum(
            1 for r in self.active_operations.values()
            if r.status == OperationStatus.COMPLETED
        )
        failed = sum(
            1 for r in self.active_operations.values()
            if r.status == OperationStatus.FAILED
        )
        in_progress = sum(
            1 for r in self.active_operations.values()
            if r.status == OperationStatus.IN_PROGRESS
        )

        avg_duration = 0.0
        if completed > 0:
            durations = [
                r.total_duration_seconds
                for r in self.active_operations.values()
                if r.status == OperationStatus.COMPLETED
            ]
            avg_duration = sum(durations) / len(durations)

        return {
            'total_operations': total_operations,
            'completed': completed,
            'failed': failed,
            'in_progress': in_progress,
            'success_rate': completed / total_operations if total_operations > 0 else 0.0,
            'avg_duration_seconds': avg_duration
        }
