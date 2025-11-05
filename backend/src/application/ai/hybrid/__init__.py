"""
Hybrid AI/ML Prediction System

This module implements a 3-tier prediction system:
1. Cache Layer (Redis) - <5ms response time
2. ML Model Layer (PyTorch) - <100ms response time
3. AI API Layer (Groq/Gemini/Mistral) - >1s response time

The system automatically falls back to the next tier if:
- Cache miss
- ML confidence too low (<0.7)
- Any errors occur

All successful AI API calls are stored for future ML training.
"""

from .hybrid_predictor import (
    HybridPredictor,
    PredictionResult,
    PredictionTier,
    HybridPredictorConfig,
    PredictionCache
)
from .ml_adapters import (
    EndpointClassifierAdapter,
    PayloadGeneratorAdapter,
    ErrorFixerAdapter,
    WorkflowPredictorAdapter,
    create_ml_adapters
)
from .ai_adapters import (
    GroqProvider,
    GeminiProvider,
    MistralProvider,
    FallbackProvider,
    create_ai_providers
)

__all__ = [
    # Core predictor
    'HybridPredictor',
    'PredictionResult',
    'PredictionTier',
    'HybridPredictorConfig',
    'PredictionCache',
    # ML adapters
    'EndpointClassifierAdapter',
    'PayloadGeneratorAdapter',
    'ErrorFixerAdapter',
    'WorkflowPredictorAdapter',
    'create_ml_adapters',
    # AI providers
    'GroqProvider',
    'GeminiProvider',
    'MistralProvider',
    'FallbackProvider',
    'create_ai_providers'
]
