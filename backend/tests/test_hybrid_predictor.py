"""
Integration tests for Hybrid Predictor system

Tests the 3-tier prediction system (Cache → ML → AI API)
"""

import pytest
import asyncio
from backend.src.application.ai.hybrid import (
    HybridPredictor,
    HybridPredictorConfig,
    PredictionTier,
    create_ml_adapters,
    create_ai_providers
)


class TestHybridPredictor:
    """Test hybrid prediction system"""

    @pytest.fixture
    async def hybrid_predictor(self):
        """Create hybrid predictor with mocked providers"""

        # Create configuration
        config = HybridPredictorConfig(
            cache_enabled=True,
            ml_enabled=False,  # Disable ML for basic test
            ai_enabled=False,  # Disable AI for basic test
            cache_confidence_threshold=0.9,
            ml_confidence_threshold=0.7
        )

        # Create predictor
        predictor = HybridPredictor(
            config=config,
            ml_models={},
            ai_providers={}
        )

        return predictor

    @pytest.mark.asyncio
    async def test_predictor_initialization(self, hybrid_predictor):
        """Test that predictor initializes correctly"""
        assert hybrid_predictor is not None
        assert hybrid_predictor.config is not None
        assert hybrid_predictor.cache is not None
        assert hybrid_predictor.metrics is not None

    @pytest.mark.asyncio
    async def test_cache_functionality(self, hybrid_predictor):
        """Test cache stores and retrieves predictions"""

        # Test cache set/get
        from backend.src.application.ai.hybrid import PredictionResult

        input_data = {
            'task': 'test',
            'url': '/api/test',
            'method': 'GET'
        }

        result = PredictionResult(
            prediction={'test': 'data'},
            confidence=0.95,
            tier=PredictionTier.CACHE,
            latency_ms=5.0
        )

        # Store in cache
        await hybrid_predictor.cache.set(input_data, result)

        # Retrieve from cache
        cached = await hybrid_predictor.cache.get(input_data, min_confidence=0.9)

        assert cached is not None
        assert cached.confidence == 0.95
        assert cached.prediction == {'test': 'data'}

    @pytest.mark.asyncio
    async def test_get_metrics(self, hybrid_predictor):
        """Test metrics collection"""

        metrics = await hybrid_predictor.get_metrics()

        assert metrics is not None
        assert 'total_predictions' in metrics
        assert 'cache_hit_rate' in metrics
        assert 'avg_latency_ms' in metrics

    @pytest.mark.asyncio
    async def test_cache_stats(self, hybrid_predictor):
        """Test cache statistics"""

        stats = await hybrid_predictor.cache.get_stats()

        assert stats is not None
        assert 'total_items' in stats

    @pytest.mark.asyncio
    async def test_clear_cache(self, hybrid_predictor):
        """Test cache clearing"""

        # Add item to cache
        input_data = {'test': 'data'}
        result = PredictionResult(
            prediction={'result': 'test'},
            confidence=0.95,
            tier=PredictionTier.CACHE,
            latency_ms=5.0
        )

        await hybrid_predictor.cache.set(input_data, result)

        # Clear cache
        await hybrid_predictor.clear_cache()

        # Verify cache is empty
        stats = await hybrid_predictor.cache.get_stats()
        assert stats['total_items'] == 0


@pytest.mark.asyncio
async def test_ml_adapters_creation():
    """Test ML adapter factory"""

    try:
        from backend.src.application.ai.hybrid import create_ml_adapters

        adapters = create_ml_adapters(model_dir="./models")

        assert adapters is not None
        assert 'endpoint_classifier' in adapters
        assert 'payload_generator' in adapters
        assert 'error_fixer' in adapters
        assert 'workflow_predictor' in adapters

    except ImportError as e:
        # ML models might not be available in test environment
        pytest.skip(f"ML models not available: {e}")


@pytest.mark.asyncio
async def test_ai_providers_creation():
    """Test AI provider factory"""

    from backend.src.application.ai.hybrid import create_ai_providers

    # This should work even without API keys (providers will just fail on generate)
    providers = create_ai_providers(default_provider='fallback')

    assert providers is not None
    assert 'fallback' in providers


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
