"""
Integration Tests for Phase 3 - Autonomous Orchestration System

Tests the complete end-to-end workflow including:
- Autonomous onboarding
- Hybrid prediction (Cache → ML → AI)
- Execution engine with retry and auto-fix
- Learning loop
- Performance monitoring
- Model registry
- REST APIs
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch


class TestHybridPredictorIntegration:
    """Integration tests for hybrid prediction system"""

    @pytest.mark.asyncio
    async def test_hybrid_predictor_tier_fallback(self):
        """Test that hybrid predictor falls back through tiers correctly"""
        from backend.src.application.ai.hybrid import (
            HybridPredictor,
            HybridPredictorConfig,
            PredictionTier
        )

        # Create predictor with cache only (ML/AI disabled)
        config = HybridPredictorConfig(
            cache_enabled=True,
            ml_enabled=False,
            ai_enabled=False
        )

        predictor = HybridPredictor(
            config=config,
            ml_models={},
            ai_providers={}
        )

        # First call - should be cache miss
        result1 = await predictor.predict_endpoint_classification(
            url="/api/test",
            method="GET"
        )

        # With ML/AI disabled and cache miss, should fail gracefully
        assert result1.tier == PredictionTier.ERROR

    @pytest.mark.asyncio
    async def test_hybrid_predictor_cache_hit(self):
        """Test cache hit scenario"""
        from backend.src.application.ai.hybrid import (
            HybridPredictor,
            HybridPredictorConfig,
            PredictionResult,
            PredictionTier
        )

        config = HybridPredictorConfig(cache_enabled=True)
        predictor = HybridPredictor(config=config)

        # Manually add to cache
        input_data = {
            'task': 'endpoint_classification',
            'url': '/api/test',
            'method': 'GET',
            'context': {}
        }

        cached_result = PredictionResult(
            prediction={'category': 'data_retrieval'},
            confidence=0.95,
            tier=PredictionTier.CACHE,
            latency_ms=2.0
        )

        await predictor.cache.set(input_data, cached_result)

        # Call again - should hit cache
        result = await predictor.predict_endpoint_classification(
            url="/api/test",
            method="GET"
        )

        assert result.tier == PredictionTier.CACHE
        assert result.confidence == 0.95


class TestAutonomousOrchestratorIntegration:
    """Integration tests for autonomous orchestrator"""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Test orchestrator can be initialized"""
        from backend.src.application.ai.orchestration import AutonomousOrchestrator

        orchestrator = AutonomousOrchestrator(
            api_explorer=None,
            hybrid_predictor=None,
            execution_engine=None,
            learning_loop=None
        )

        assert orchestrator is not None
        assert len(orchestrator.active_operations) == 0

    @pytest.mark.asyncio
    async def test_orchestrator_metrics(self):
        """Test orchestrator metrics collection"""
        from backend.src.application.ai.orchestration import AutonomousOrchestrator

        orchestrator = AutonomousOrchestrator()
        metrics = await orchestrator.get_metrics()

        assert metrics is not None
        assert 'total_operations' in metrics
        assert metrics['total_operations'] == 0


class TestExecutionEngineIntegration:
    """Integration tests for execution engine"""

    @pytest.mark.asyncio
    async def test_execution_engine_initialization(self):
        """Test execution engine initialization"""
        from backend.src.application.ai.orchestration import ExecutionEngine

        engine = ExecutionEngine(hybrid_predictor=None)

        assert engine is not None
        assert engine.circuit_breaker is not None

    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker pattern"""
        from backend.src.application.ai.orchestration import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3)

        # Simulate failures
        for i in range(3):
            try:
                async def failing_function():
                    raise Exception("Test failure")

                await breaker.call(failing_function)
            except:
                pass

        # Circuit should be open now
        assert breaker.state == 'open'

    @pytest.mark.asyncio
    async def test_rate_limiter_functionality(self):
        """Test rate limiter"""
        from backend.src.application.ai.orchestration import RateLimiter
        import time

        limiter = RateLimiter(rate_per_second=10)

        # Acquire multiple tokens
        start = time.time()
        for i in range(5):
            await limiter.acquire()
        elapsed = time.time() - start

        # Should take minimal time for first few
        assert elapsed < 1.0


class TestLearningLoopIntegration:
    """Integration tests for learning loop"""

    @pytest.mark.asyncio
    async def test_learning_loop_initialization(self):
        """Test learning loop can be initialized"""
        from backend.src.application.ai.orchestration import LearningLoop

        learning_loop = LearningLoop(
            flow_db_path="./test_flow_db",
            enable_learning=False  # Disable for test
        )

        assert learning_loop is not None
        assert learning_loop.enable_learning is False

    @pytest.mark.asyncio
    async def test_learning_loop_metrics(self):
        """Test learning loop metrics"""
        from backend.src.application.ai.orchestration import LearningLoop

        learning_loop = LearningLoop(enable_learning=False)
        metrics = await learning_loop.get_metrics()

        assert metrics is not None
        assert 'total_patterns_stored' in metrics


class TestPerformanceMonitorIntegration:
    """Integration tests for performance monitor"""

    @pytest.mark.asyncio
    async def test_performance_monitor_initialization(self):
        """Test performance monitor initialization"""
        from backend.src.application.ai.orchestration import PerformanceMonitor

        monitor = PerformanceMonitor(
            history_size=100,
            snapshot_interval_seconds=60
        )

        assert monitor is not None
        assert len(monitor.history) == 0

    @pytest.mark.asyncio
    async def test_performance_monitor_record_prediction(self):
        """Test recording predictions"""
        from backend.src.application.ai.orchestration import PerformanceMonitor

        monitor = PerformanceMonitor()

        # Record some predictions
        await monitor.record_prediction('cache', latency_ms=5.0, success=True)
        await monitor.record_prediction('ml', latency_ms=95.0, success=True)
        await monitor.record_prediction('ai', latency_ms=1500.0, success=True)

        # Get metrics
        metrics = await monitor.get_current_metrics()

        assert metrics['total_requests'] == 3
        assert metrics['cache_hits'] == 1
        assert metrics['ml_predictions'] == 1
        assert metrics['ai_predictions'] == 1

    @pytest.mark.asyncio
    async def test_performance_monitor_cost_calculation(self):
        """Test cost calculation"""
        from backend.src.application.ai.orchestration import PerformanceMonitor

        monitor = PerformanceMonitor()

        # Record predictions
        await monitor.record_prediction('cache', 5.0, True)  # $0.000001
        await monitor.record_prediction('ml', 95.0, True)    # $0.0001
        await monitor.record_prediction('ai', 1500.0, True)  # $0.002

        metrics = await monitor.get_current_metrics()

        # Should have some cost
        assert metrics['estimated_cost'] > 0
        # AI should be most expensive
        assert metrics['estimated_cost'] > 0.002

    @pytest.mark.asyncio
    async def test_performance_monitor_snapshot(self):
        """Test snapshot creation"""
        from backend.src.application.ai.orchestration import PerformanceMonitor

        monitor = PerformanceMonitor()

        # Record some data
        await monitor.record_prediction('cache', 5.0, True)

        # Create snapshot
        snapshot = await monitor.create_snapshot()

        assert snapshot is not None
        assert snapshot.total_requests == 1
        assert snapshot.cache_hits == 1


class TestModelRegistryIntegration:
    """Integration tests for model registry"""

    @pytest.mark.asyncio
    async def test_model_registry_initialization(self):
        """Test model registry initialization"""
        from backend.src.application.ai.orchestration import (
            ModelRegistry,
            ModelStatus
        )

        registry = ModelRegistry(
            registry_path="./test_registry.json",
            models_dir="./test_models"
        )

        assert registry is not None
        assert len(registry.models) == 0

    @pytest.mark.asyncio
    async def test_model_registry_register_model(self):
        """Test model registration"""
        from backend.src.application.ai.orchestration import (
            ModelRegistry,
            ModelStatus
        )

        registry = ModelRegistry(
            registry_path="./test_registry.json"
        )

        # Register a model
        model = registry.register_model(
            model_type="endpoint_classifier",
            version="v1.0.0",
            model_path="./test_model.pt",
            description="Test model",
            status=ModelStatus.TESTING
        )

        assert model is not None
        assert model.model_type == "endpoint_classifier"
        assert model.version == "v1.0.0"
        assert model.status == ModelStatus.TESTING

    @pytest.mark.asyncio
    async def test_model_registry_promotion(self):
        """Test model promotion"""
        from backend.src.application.ai.orchestration import (
            ModelRegistry,
            ModelStatus
        )

        registry = ModelRegistry(registry_path="./test_registry.json")

        # Register and promote
        model = registry.register_model(
            model_type="test_model",
            version="v1",
            model_path="./test.pt",
            status=ModelStatus.TESTING
        )

        # Promote to staging
        success = registry.promote_model(model.model_id, ModelStatus.STAGING)

        assert success is True
        assert model.status == ModelStatus.STAGING


class TestDependencyGraphIntegration:
    """Integration tests for dependency graph"""

    @pytest.mark.asyncio
    async def test_dependency_graph_topological_sort(self):
        """Test topological sorting"""
        from backend.src.application.ai.orchestration import (
            DependencyGraph,
            EndpointInfo
        )

        graph = DependencyGraph()

        # Create endpoints with dependencies
        ep_a = EndpointInfo(id="A", url="/auth", method="POST", category="authentication")
        ep_b = EndpointInfo(id="B", url="/users", method="GET")
        ep_c = EndpointInfo(id="C", url="/posts", method="GET")
        ep_d = EndpointInfo(id="D", url="/comments", method="POST")

        # Add to graph
        graph.add_node(ep_a)
        graph.add_node(ep_b)
        graph.add_node(ep_c)
        graph.add_node(ep_d)

        # Add dependencies: B and C depend on A, D depends on C
        graph.add_dependency("B", "A")
        graph.add_dependency("C", "A")
        graph.add_dependency("D", "C")

        # Get execution order
        order = graph.get_execution_order()

        # A should be first (auth)
        assert order[0] == "A"
        # D should be last (depends on C which depends on A)
        assert order[-1] == "D"
        # B and C should be after A but before D
        assert order.index("B") > order.index("A")
        assert order.index("C") > order.index("A")

    @pytest.mark.asyncio
    async def test_dependency_graph_parallel_batches(self):
        """Test parallel batch detection"""
        from backend.src.application.ai.orchestration import (
            DependencyGraph,
            EndpointInfo
        )

        graph = DependencyGraph()

        ep_a = EndpointInfo(id="A", url="/auth", method="POST")
        ep_b = EndpointInfo(id="B", url="/users", method="GET")
        ep_c = EndpointInfo(id="C", url="/posts", method="GET")

        graph.add_node(ep_a)
        graph.add_node(ep_b)
        graph.add_node(ep_c)

        # B and C depend on A
        graph.add_dependency("B", "A")
        graph.add_dependency("C", "A")

        # Get parallel batches
        batches = graph.get_parallel_batches()

        # Should have 2 batches
        assert len(batches) == 2
        # First batch: A
        assert batches[0] == ["A"]
        # Second batch: B and C (can run in parallel)
        assert set(batches[1]) == {"B", "C"}


class TestEndToEndWorkflow:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_complete_workflow_structure(self):
        """Test that all components can be initialized together"""
        from backend.src.application.ai.orchestration import (
            AutonomousOrchestrator,
            ExecutionEngine,
            LearningLoop,
            PerformanceMonitor,
            ModelRegistry
        )
        from backend.src.application.ai.hybrid import HybridPredictor

        # Initialize all components
        hybrid_predictor = HybridPredictor()
        execution_engine = ExecutionEngine(hybrid_predictor=hybrid_predictor)
        learning_loop = LearningLoop(enable_learning=False)
        performance_monitor = PerformanceMonitor()
        model_registry = ModelRegistry(registry_path="./test_registry.json")

        orchestrator = AutonomousOrchestrator(
            api_explorer=None,
            hybrid_predictor=hybrid_predictor,
            execution_engine=execution_engine,
            learning_loop=learning_loop
        )

        # Verify all initialized
        assert hybrid_predictor is not None
        assert execution_engine is not None
        assert learning_loop is not None
        assert performance_monitor is not None
        assert model_registry is not None
        assert orchestrator is not None


class TestRESTAPIIntegration:
    """Integration tests for REST API endpoints"""

    def test_api_router_creation(self):
        """Test that API router can be imported"""
        from backend.src.presentation.rest.autonomous_api import router

        assert router is not None
        assert router.prefix == "/api/autonomous"

    def test_api_health_check_structure(self):
        """Test health check endpoint structure"""
        from backend.src.presentation.rest.autonomous_api import health_check

        assert health_check is not None

    def test_api_initialization_function(self):
        """Test API initialization function"""
        from backend.src.presentation.rest.autonomous_api import init_orchestration_api

        # Should not raise error
        init_orchestration_api(
            orchestrator=None,
            hybrid_predictor=None,
            learning_loop=None,
            performance_monitor=None,
            model_registry=None
        )


class TestPerformanceOptimization:
    """Performance tests"""

    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """Test cache is fast"""
        from backend.src.application.ai.hybrid import PredictionCache
        import time

        cache = PredictionCache()

        # Add item
        from backend.src.application.ai.hybrid import PredictionResult, PredictionTier

        result = PredictionResult(
            prediction={'test': 'data'},
            confidence=0.95,
            tier=PredictionTier.CACHE,
            latency_ms=5.0
        )

        input_data = {'test': 'key'}

        await cache.set(input_data, result)

        # Retrieve - should be very fast
        start = time.time()
        cached = await cache.get(input_data)
        elapsed = (time.time() - start) * 1000  # ms

        assert cached is not None
        assert elapsed < 10  # Should be < 10ms

    @pytest.mark.asyncio
    async def test_rate_limiter_performance(self):
        """Test rate limiter doesn't add too much overhead"""
        from backend.src.application.ai.orchestration import RateLimiter
        import time

        limiter = RateLimiter(rate_per_second=100)  # High rate

        start = time.time()
        for i in range(10):
            await limiter.acquire()
        elapsed = time.time() - start

        # Should be fast with high rate
        assert elapsed < 0.5  # < 500ms for 10 tokens


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
