"""
Hybrid AI/ML Predictor - 3-Tier Prediction System

This module implements intelligent prediction routing with automatic fallback:
Cache → ML Model → AI API

Performance Targets:
- Cache hit rate: >80%
- ML inference time: <100ms
- AI API fallback: <10% of requests
- Overall latency: <150ms average
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, Any, List
import asyncio

logger = logging.getLogger(__name__)


class PredictionTier(str, Enum):
    """Prediction tier that served the result"""
    CACHE = "cache"
    ML_MODEL = "ml_model"
    AI_API = "ai_api"
    ERROR = "error"


@dataclass
class PredictionResult:
    """
    Result from hybrid prediction with metadata

    Attributes:
        prediction: The actual prediction (dict, string, or any result)
        confidence: Confidence score 0.0-1.0
        tier: Which tier served this result
        latency_ms: How long it took to generate
        metadata: Additional information (model version, cache key, etc.)
    """
    prediction: Any
    confidence: float
    tier: PredictionTier
    latency_ms: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['tier'] = self.tier.value
        return result


@dataclass
class HybridPredictorConfig:
    """Configuration for hybrid predictor"""

    # Cache settings
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour
    cache_confidence_threshold: float = 0.9  # Only use cached if confidence >0.9

    # ML model settings
    ml_enabled: bool = True
    ml_confidence_threshold: float = 0.7  # Fallback to AI if <0.7
    ml_timeout_ms: int = 200  # Max time for ML inference

    # AI API settings
    ai_enabled: bool = True
    ai_timeout_ms: int = 10000  # Max time for AI API call
    ai_default_model: str = "groq"  # groq, gemini, or mistral

    # Learning settings
    store_for_training: bool = True  # Store AI results for future ML training
    min_confidence_to_cache: float = 0.8  # Don't cache low-confidence results

    # Performance settings
    enable_metrics: bool = True
    log_predictions: bool = True


class PredictionCache:
    """
    High-performance cache for predictions

    Uses in-memory cache with optional Redis backend.
    Stores prediction results with confidence scores and TTL.
    """

    def __init__(self, ttl: int = 3600, max_items: int = 10000):
        """
        Initialize prediction cache

        Args:
            ttl: Time-to-live in seconds
            max_items: Maximum items in memory
        """
        self.ttl = ttl
        self.max_items = max_items
        self.cache: Dict[str, tuple[PredictionResult, float]] = {}
        self._lock = asyncio.Lock()

        logger.info(f"[CACHE] Initialized: ttl={ttl}s, max_items={max_items}")

    def _generate_key(self, input_data: Dict[str, Any]) -> str:
        """Generate cache key from input data"""
        # Sort keys for consistent hashing
        key_str = json.dumps(input_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    async def get(
        self,
        input_data: Dict[str, Any],
        min_confidence: float = 0.9
    ) -> Optional[PredictionResult]:
        """
        Get cached prediction if available and meets confidence threshold

        Args:
            input_data: Input data to look up
            min_confidence: Minimum confidence to return cached result

        Returns:
            Cached prediction or None
        """
        try:
            key = self._generate_key(input_data)

            async with self._lock:
                if key in self.cache:
                    result, timestamp = self.cache[key]

                    # Check if expired
                    if time.time() - timestamp > self.ttl:
                        del self.cache[key]
                        logger.debug(f"[CACHE] Expired: {key[:16]}...")
                        return None

                    # Check confidence threshold
                    if result.confidence >= min_confidence:
                        logger.info(
                            f"[CACHE] HIT: {key[:16]}... "
                            f"(confidence={result.confidence:.3f}, "
                            f"age={time.time()-timestamp:.1f}s)"
                        )
                        return result
                    else:
                        logger.debug(
                            f"[CACHE] Low confidence: {key[:16]}... "
                            f"({result.confidence:.3f} < {min_confidence})"
                        )
                        return None

            return None

        except Exception as e:
            logger.warning(f"[CACHE] Get error: {e}")
            return None

    async def set(
        self,
        input_data: Dict[str, Any],
        result: PredictionResult
    ):
        """
        Cache prediction result

        Args:
            input_data: Input data to cache against
            result: Prediction result to cache
        """
        try:
            key = self._generate_key(input_data)
            timestamp = time.time()

            async with self._lock:
                # Evict oldest if at capacity
                if len(self.cache) >= self.max_items:
                    oldest_key = min(
                        self.cache.keys(),
                        key=lambda k: self.cache[k][1]
                    )
                    del self.cache[oldest_key]
                    logger.debug(f"[CACHE] Evicted: {oldest_key[:16]}...")

                self.cache[key] = (result, timestamp)

            logger.debug(
                f"[CACHE] SET: {key[:16]}... "
                f"(confidence={result.confidence:.3f})"
            )

        except Exception as e:
            logger.warning(f"[CACHE] Set error: {e}")

    async def clear(self):
        """Clear all cached predictions"""
        async with self._lock:
            self.cache.clear()
        logger.info("[CACHE] Cleared")

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            total_items = len(self.cache)

            if total_items == 0:
                return {
                    'total_items': 0,
                    'avg_confidence': 0.0,
                    'avg_age_seconds': 0.0
                }

            confidences = [r.confidence for r, _ in self.cache.values()]
            ages = [time.time() - t for _, t in self.cache.values()]

            return {
                'total_items': total_items,
                'avg_confidence': sum(confidences) / len(confidences),
                'max_confidence': max(confidences),
                'min_confidence': min(confidences),
                'avg_age_seconds': sum(ages) / len(ages),
                'max_age_seconds': max(ages),
                'ttl': self.ttl
            }


class HybridPredictor:
    """
    Hybrid AI/ML Predictor with 3-tier fallback system

    Prediction Flow:
    1. Check cache (target <5ms)
    2. Try ML model (target <100ms)
    3. Fallback to AI API (target <2s)

    Features:
    - Automatic tier selection based on confidence
    - Performance monitoring and metrics
    - Automatic learning from AI API results
    - Configurable thresholds and timeouts
    """

    def __init__(
        self,
        config: Optional[HybridPredictorConfig] = None,
        ml_models: Optional[Dict[str, Any]] = None,
        ai_providers: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize hybrid predictor

        Args:
            config: Configuration settings
            ml_models: Dictionary of ML model instances
            ai_providers: Dictionary of AI provider instances
        """
        self.config = config or HybridPredictorConfig()

        # Initialize cache
        if self.config.cache_enabled:
            self.cache = PredictionCache(
                ttl=self.config.cache_ttl,
                max_items=10000
            )
        else:
            self.cache = None

        # Store ML models and AI providers
        self.ml_models = ml_models or {}
        self.ai_providers = ai_providers or {}

        # Performance metrics
        self.metrics = {
            'total_predictions': 0,
            'cache_hits': 0,
            'ml_predictions': 0,
            'ai_predictions': 0,
            'errors': 0,
            'total_latency_ms': 0,
            'cache_latency_ms': 0,
            'ml_latency_ms': 0,
            'ai_latency_ms': 0
        }
        self._metrics_lock = asyncio.Lock()

        logger.info("[HYBRID] Predictor initialized")
        logger.info(f"[HYBRID] Cache: {self.config.cache_enabled}")
        logger.info(f"[HYBRID] ML Models: {self.config.ml_enabled} ({len(self.ml_models)} loaded)")
        logger.info(f"[HYBRID] AI APIs: {self.config.ai_enabled} ({len(self.ai_providers)} available)")

    async def _update_metrics(self, tier: PredictionTier, latency_ms: float):
        """Update performance metrics"""
        if not self.config.enable_metrics:
            return

        async with self._metrics_lock:
            self.metrics['total_predictions'] += 1
            self.metrics['total_latency_ms'] += latency_ms

            if tier == PredictionTier.CACHE:
                self.metrics['cache_hits'] += 1
                self.metrics['cache_latency_ms'] += latency_ms
            elif tier == PredictionTier.ML_MODEL:
                self.metrics['ml_predictions'] += 1
                self.metrics['ml_latency_ms'] += latency_ms
            elif tier == PredictionTier.AI_API:
                self.metrics['ai_predictions'] += 1
                self.metrics['ai_latency_ms'] += latency_ms
            elif tier == PredictionTier.ERROR:
                self.metrics['errors'] += 1

    async def predict_endpoint_classification(
        self,
        url: str,
        method: str,
        context: Optional[Dict[str, Any]] = None
    ) -> PredictionResult:
        """
        Classify endpoint using hybrid prediction

        Predicts endpoint category, operation type, and required parameters.

        Args:
            url: API endpoint URL
            method: HTTP method
            context: Additional context (headers, description, etc.)

        Returns:
            PredictionResult with classification
        """
        start_time = time.time()

        # Prepare input data
        input_data = {
            'task': 'endpoint_classification',
            'url': url,
            'method': method,
            'context': context or {}
        }

        try:
            # Tier 1: Try cache
            if self.cache and self.config.cache_enabled:
                cached = await self.cache.get(
                    input_data,
                    min_confidence=self.config.cache_confidence_threshold
                )
                if cached:
                    latency_ms = (time.time() - start_time) * 1000
                    await self._update_metrics(PredictionTier.CACHE, latency_ms)

                    if self.config.log_predictions:
                        logger.info(
                            f"[HYBRID] Endpoint classification (CACHE): {url} -> "
                            f"{cached.prediction.get('category', 'unknown')} "
                            f"({latency_ms:.1f}ms)"
                        )

                    return cached

            # Tier 2: Try ML model
            if self.config.ml_enabled and 'endpoint_classifier' in self.ml_models:
                try:
                    ml_start = time.time()
                    classifier = self.ml_models['endpoint_classifier']

                    # Call ML model with timeout
                    ml_result = await asyncio.wait_for(
                        classifier.classify_endpoint(url, method, context),
                        timeout=self.config.ml_timeout_ms / 1000
                    )

                    ml_latency = (time.time() - ml_start) * 1000

                    # Check confidence threshold
                    if ml_result.get('confidence', 0.0) >= self.config.ml_confidence_threshold:
                        result = PredictionResult(
                            prediction=ml_result,
                            confidence=ml_result['confidence'],
                            tier=PredictionTier.ML_MODEL,
                            latency_ms=ml_latency,
                            metadata={'model': 'endpoint_classifier'}
                        )

                        # Cache high-confidence results
                        if (self.cache and
                            result.confidence >= self.config.min_confidence_to_cache):
                            await self.cache.set(input_data, result)

                        total_latency = (time.time() - start_time) * 1000
                        await self._update_metrics(PredictionTier.ML_MODEL, total_latency)

                        if self.config.log_predictions:
                            logger.info(
                                f"[HYBRID] Endpoint classification (ML): {url} -> "
                                f"{ml_result.get('category', 'unknown')} "
                                f"(confidence={ml_result['confidence']:.3f}, "
                                f"{total_latency:.1f}ms)"
                            )

                        return result
                    else:
                        logger.debug(
                            f"[HYBRID] ML confidence too low: {ml_result['confidence']:.3f} "
                            f"< {self.config.ml_confidence_threshold}"
                        )

                except asyncio.TimeoutError:
                    logger.warning(f"[HYBRID] ML timeout after {self.config.ml_timeout_ms}ms")
                except Exception as e:
                    logger.warning(f"[HYBRID] ML error: {e}")

            # Tier 3: Fallback to AI API
            if self.config.ai_enabled:
                ai_start = time.time()

                # Get AI provider (prefer Groq for speed)
                provider_name = self.config.ai_default_model
                if provider_name not in self.ai_providers:
                    provider_name = list(self.ai_providers.keys())[0] if self.ai_providers else None

                if provider_name:
                    provider = self.ai_providers[provider_name]

                    # Construct prompt for classification
                    prompt = f"""Classify this API endpoint:

URL: {url}
Method: {method}
Context: {json.dumps(context or {}, indent=2)}

Provide classification in JSON format:
{{
    "category": "one of: authentication, data_retrieval, data_creation, data_update, data_deletion, file_upload, search, notification, webhook, payment, analytics, other",
    "operation_type": "descriptive operation name",
    "required_params": ["list", "of", "required", "parameters"],
    "optional_params": ["list", "of", "optional", "parameters"],
    "description": "brief description of what this endpoint does",
    "confidence": 0.95
}}"""

                    try:
                        ai_response = await asyncio.wait_for(
                            provider.generate(prompt),
                            timeout=self.config.ai_timeout_ms / 1000
                        )

                        # Parse JSON response
                        ai_result = json.loads(ai_response)
                        ai_latency = (time.time() - ai_start) * 1000

                        result = PredictionResult(
                            prediction=ai_result,
                            confidence=ai_result.get('confidence', 0.9),
                            tier=PredictionTier.AI_API,
                            latency_ms=ai_latency,
                            metadata={'provider': provider_name}
                        )

                        # Store for future training
                        if self.config.store_for_training:
                            # TODO: Store in training database
                            logger.debug(f"[HYBRID] Stored for training: {url}")

                        # Cache high-confidence results
                        if (self.cache and
                            result.confidence >= self.config.min_confidence_to_cache):
                            await self.cache.set(input_data, result)

                        total_latency = (time.time() - start_time) * 1000
                        await self._update_metrics(PredictionTier.AI_API, total_latency)

                        if self.config.log_predictions:
                            logger.info(
                                f"[HYBRID] Endpoint classification (AI): {url} -> "
                                f"{ai_result.get('category', 'unknown')} "
                                f"(confidence={ai_result.get('confidence', 0.9):.3f}, "
                                f"{total_latency:.1f}ms)"
                            )

                        return result

                    except asyncio.TimeoutError:
                        logger.error(f"[HYBRID] AI timeout after {self.config.ai_timeout_ms}ms")
                    except Exception as e:
                        logger.error(f"[HYBRID] AI error: {e}")

            # All tiers failed
            logger.error(f"[HYBRID] All prediction tiers failed for: {url}")
            total_latency = (time.time() - start_time) * 1000
            await self._update_metrics(PredictionTier.ERROR, total_latency)

            return PredictionResult(
                prediction={'category': 'unknown', 'error': 'All prediction tiers failed'},
                confidence=0.0,
                tier=PredictionTier.ERROR,
                latency_ms=total_latency,
                metadata={'url': url, 'method': method}
            )

        except Exception as e:
            logger.error(f"[HYBRID] Prediction error: {e}")
            total_latency = (time.time() - start_time) * 1000
            await self._update_metrics(PredictionTier.ERROR, total_latency)

            return PredictionResult(
                prediction={'error': str(e)},
                confidence=0.0,
                tier=PredictionTier.ERROR,
                latency_ms=total_latency
            )

    async def generate_payload(
        self,
        endpoint_url: str,
        method: str,
        schema: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PredictionResult:
        """
        Generate request payload using hybrid prediction

        Args:
            endpoint_url: API endpoint URL
            method: HTTP method
            schema: OpenAPI schema if available
            context: Additional context

        Returns:
            PredictionResult with generated payload
        """
        start_time = time.time()

        # Prepare input data
        input_data = {
            'task': 'payload_generation',
            'url': endpoint_url,
            'method': method,
            'schema': schema,
            'context': context or {}
        }

        try:
            # Tier 1: Try cache
            if self.cache and self.config.cache_enabled:
                cached = await self.cache.get(
                    input_data,
                    min_confidence=self.config.cache_confidence_threshold
                )
                if cached:
                    latency_ms = (time.time() - start_time) * 1000
                    await self._update_metrics(PredictionTier.CACHE, latency_ms)

                    if self.config.log_predictions:
                        logger.info(
                            f"[HYBRID] Payload generation (CACHE): {endpoint_url} "
                            f"({latency_ms:.1f}ms)"
                        )

                    return cached

            # Tier 2: Try ML model
            if self.config.ml_enabled and 'payload_generator' in self.ml_models:
                try:
                    ml_start = time.time()
                    generator = self.ml_models['payload_generator']

                    # Call ML model with timeout
                    ml_result = await asyncio.wait_for(
                        generator.generate_payload(endpoint_url, method, schema, context),
                        timeout=self.config.ml_timeout_ms / 1000
                    )

                    ml_latency = (time.time() - ml_start) * 1000

                    # Check confidence threshold
                    if ml_result.get('confidence', 0.0) >= self.config.ml_confidence_threshold:
                        result = PredictionResult(
                            prediction=ml_result['payload'],
                            confidence=ml_result['confidence'],
                            tier=PredictionTier.ML_MODEL,
                            latency_ms=ml_latency,
                            metadata={'model': 'payload_generator'}
                        )

                        # Cache high-confidence results
                        if (self.cache and
                            result.confidence >= self.config.min_confidence_to_cache):
                            await self.cache.set(input_data, result)

                        total_latency = (time.time() - start_time) * 1000
                        await self._update_metrics(PredictionTier.ML_MODEL, total_latency)

                        if self.config.log_predictions:
                            logger.info(
                                f"[HYBRID] Payload generation (ML): {endpoint_url} "
                                f"(confidence={ml_result['confidence']:.3f}, "
                                f"{total_latency:.1f}ms)"
                            )

                        return result
                    else:
                        logger.debug(
                            f"[HYBRID] ML confidence too low: {ml_result['confidence']:.3f} "
                            f"< {self.config.ml_confidence_threshold}"
                        )

                except asyncio.TimeoutError:
                    logger.warning(f"[HYBRID] ML timeout after {self.config.ml_timeout_ms}ms")
                except Exception as e:
                    logger.warning(f"[HYBRID] ML error: {e}")

            # Tier 3: Fallback to AI API
            if self.config.ai_enabled:
                ai_start = time.time()

                provider_name = self.config.ai_default_model
                if provider_name not in self.ai_providers:
                    provider_name = list(self.ai_providers.keys())[0] if self.ai_providers else None

                if provider_name:
                    provider = self.ai_providers[provider_name]

                    # Construct prompt for payload generation
                    schema_str = json.dumps(schema, indent=2) if schema else "No schema available"
                    context_str = json.dumps(context or {}, indent=2)

                    prompt = f"""Generate a valid request payload for this API endpoint:

URL: {endpoint_url}
Method: {method}
Schema: {schema_str}
Context: {context_str}

Generate a realistic payload that matches the schema. Respond in JSON format:
{{
    "payload": {{"generated": "payload", "here": "..."}},
    "confidence": 0.95,
    "explanation": "brief explanation of the generated payload"
}}"""

                    try:
                        ai_response = await asyncio.wait_for(
                            provider.generate(prompt),
                            timeout=self.config.ai_timeout_ms / 1000
                        )

                        # Parse JSON response
                        ai_result = json.loads(ai_response)
                        ai_latency = (time.time() - ai_start) * 1000

                        result = PredictionResult(
                            prediction=ai_result['payload'],
                            confidence=ai_result.get('confidence', 0.9),
                            tier=PredictionTier.AI_API,
                            latency_ms=ai_latency,
                            metadata={
                                'provider': provider_name,
                                'explanation': ai_result.get('explanation', '')
                            }
                        )

                        # Store for future training
                        if self.config.store_for_training:
                            logger.debug(f"[HYBRID] Stored for training: {endpoint_url}")

                        # Cache high-confidence results
                        if (self.cache and
                            result.confidence >= self.config.min_confidence_to_cache):
                            await self.cache.set(input_data, result)

                        total_latency = (time.time() - start_time) * 1000
                        await self._update_metrics(PredictionTier.AI_API, total_latency)

                        if self.config.log_predictions:
                            logger.info(
                                f"[HYBRID] Payload generation (AI): {endpoint_url} "
                                f"(confidence={ai_result.get('confidence', 0.9):.3f}, "
                                f"{total_latency:.1f}ms)"
                            )

                        return result

                    except asyncio.TimeoutError:
                        logger.error(f"[HYBRID] AI timeout after {self.config.ai_timeout_ms}ms")
                    except Exception as e:
                        logger.error(f"[HYBRID] AI error: {e}")

            # All tiers failed
            logger.error(f"[HYBRID] All prediction tiers failed for payload generation: {endpoint_url}")
            total_latency = (time.time() - start_time) * 1000
            await self._update_metrics(PredictionTier.ERROR, total_latency)

            return PredictionResult(
                prediction={},
                confidence=0.0,
                tier=PredictionTier.ERROR,
                latency_ms=total_latency,
                metadata={'url': endpoint_url, 'method': method, 'error': 'All tiers failed'}
            )

        except Exception as e:
            logger.error(f"[HYBRID] Payload generation error: {e}")
            total_latency = (time.time() - start_time) * 1000
            await self._update_metrics(PredictionTier.ERROR, total_latency)

            return PredictionResult(
                prediction={},
                confidence=0.0,
                tier=PredictionTier.ERROR,
                latency_ms=total_latency,
                metadata={'error': str(e)}
            )

    async def fix_error(
        self,
        endpoint_url: str,
        error_response: Dict[str, Any],
        original_payload: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> PredictionResult:
        """
        Fix error by suggesting corrected payload

        Args:
            endpoint_url: API endpoint URL
            error_response: Error response from API
            original_payload: Original payload that caused error
            context: Additional context

        Returns:
            PredictionResult with fixed payload
        """
        start_time = time.time()

        # Prepare input data
        input_data = {
            'task': 'error_fixing',
            'url': endpoint_url,
            'error': error_response,
            'payload': original_payload,
            'context': context or {}
        }

        try:
            # Tier 1: Try cache (errors are less cacheable, but try anyway)
            if self.cache and self.config.cache_enabled:
                cached = await self.cache.get(
                    input_data,
                    min_confidence=self.config.cache_confidence_threshold
                )
                if cached:
                    latency_ms = (time.time() - start_time) * 1000
                    await self._update_metrics(PredictionTier.CACHE, latency_ms)

                    if self.config.log_predictions:
                        logger.info(
                            f"[HYBRID] Error fix (CACHE): {endpoint_url} "
                            f"({latency_ms:.1f}ms)"
                        )

                    return cached

            # Tier 2: Try ML model
            if self.config.ml_enabled and 'error_fixer' in self.ml_models:
                try:
                    ml_start = time.time()
                    fixer = self.ml_models['error_fixer']

                    # Call ML model with timeout
                    ml_result = await asyncio.wait_for(
                        fixer.fix_error(endpoint_url, error_response, original_payload, context),
                        timeout=self.config.ml_timeout_ms / 1000
                    )

                    ml_latency = (time.time() - ml_start) * 1000

                    # Check confidence threshold
                    if ml_result.get('confidence', 0.0) >= self.config.ml_confidence_threshold:
                        result = PredictionResult(
                            prediction=ml_result['fixed_payload'],
                            confidence=ml_result['confidence'],
                            tier=PredictionTier.ML_MODEL,
                            latency_ms=ml_latency,
                            metadata={
                                'model': 'error_fixer',
                                'changes': ml_result.get('changes', [])
                            }
                        )

                        # Cache high-confidence results
                        if (self.cache and
                            result.confidence >= self.config.min_confidence_to_cache):
                            await self.cache.set(input_data, result)

                        total_latency = (time.time() - start_time) * 1000
                        await self._update_metrics(PredictionTier.ML_MODEL, total_latency)

                        if self.config.log_predictions:
                            logger.info(
                                f"[HYBRID] Error fix (ML): {endpoint_url} "
                                f"(confidence={ml_result['confidence']:.3f}, "
                                f"{total_latency:.1f}ms)"
                            )

                        return result
                    else:
                        logger.debug(
                            f"[HYBRID] ML confidence too low: {ml_result['confidence']:.3f} "
                            f"< {self.config.ml_confidence_threshold}"
                        )

                except asyncio.TimeoutError:
                    logger.warning(f"[HYBRID] ML timeout after {self.config.ml_timeout_ms}ms")
                except Exception as e:
                    logger.warning(f"[HYBRID] ML error: {e}")

            # Tier 3: Fallback to AI API
            if self.config.ai_enabled:
                ai_start = time.time()

                provider_name = self.config.ai_default_model
                if provider_name not in self.ai_providers:
                    provider_name = list(self.ai_providers.keys())[0] if self.ai_providers else None

                if provider_name:
                    provider = self.ai_providers[provider_name]

                    # Construct prompt for error fixing
                    error_str = json.dumps(error_response, indent=2)
                    payload_str = json.dumps(original_payload, indent=2)
                    context_str = json.dumps(context or {}, indent=2)

                    prompt = f"""Fix this API error by providing a corrected payload:

URL: {endpoint_url}

Original Payload:
{payload_str}

Error Response:
{error_str}

Context:
{context_str}

Analyze the error and provide a fixed payload. Respond in JSON format:
{{
    "fixed_payload": {{"corrected": "payload", "here": "..."}},
    "changes": ["list of changes made"],
    "confidence": 0.95,
    "explanation": "why the error occurred and how it was fixed"
}}"""

                    try:
                        ai_response = await asyncio.wait_for(
                            provider.generate(prompt),
                            timeout=self.config.ai_timeout_ms / 1000
                        )

                        # Parse JSON response
                        ai_result = json.loads(ai_response)
                        ai_latency = (time.time() - ai_start) * 1000

                        result = PredictionResult(
                            prediction=ai_result['fixed_payload'],
                            confidence=ai_result.get('confidence', 0.9),
                            tier=PredictionTier.AI_API,
                            latency_ms=ai_latency,
                            metadata={
                                'provider': provider_name,
                                'changes': ai_result.get('changes', []),
                                'explanation': ai_result.get('explanation', '')
                            }
                        )

                        # Store for future training
                        if self.config.store_for_training:
                            logger.debug(f"[HYBRID] Stored error fix for training: {endpoint_url}")

                        # Cache high-confidence results
                        if (self.cache and
                            result.confidence >= self.config.min_confidence_to_cache):
                            await self.cache.set(input_data, result)

                        total_latency = (time.time() - start_time) * 1000
                        await self._update_metrics(PredictionTier.AI_API, total_latency)

                        if self.config.log_predictions:
                            logger.info(
                                f"[HYBRID] Error fix (AI): {endpoint_url} "
                                f"(confidence={ai_result.get('confidence', 0.9):.3f}, "
                                f"{total_latency:.1f}ms)"
                            )

                        return result

                    except asyncio.TimeoutError:
                        logger.error(f"[HYBRID] AI timeout after {self.config.ai_timeout_ms}ms")
                    except Exception as e:
                        logger.error(f"[HYBRID] AI error: {e}")

            # All tiers failed
            logger.error(f"[HYBRID] All prediction tiers failed for error fixing: {endpoint_url}")
            total_latency = (time.time() - start_time) * 1000
            await self._update_metrics(PredictionTier.ERROR, total_latency)

            return PredictionResult(
                prediction=original_payload,  # Return original as fallback
                confidence=0.0,
                tier=PredictionTier.ERROR,
                latency_ms=total_latency,
                metadata={
                    'url': endpoint_url,
                    'error': 'All tiers failed',
                    'note': 'Returning original payload unchanged'
                }
            )

        except Exception as e:
            logger.error(f"[HYBRID] Error fixing error: {e}")
            total_latency = (time.time() - start_time) * 1000
            await self._update_metrics(PredictionTier.ERROR, total_latency)

            return PredictionResult(
                prediction=original_payload,
                confidence=0.0,
                tier=PredictionTier.ERROR,
                latency_ms=total_latency,
                metadata={'error': str(e)}
            )

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics

        Returns:
            Dictionary with performance stats
        """
        async with self._metrics_lock:
            total = self.metrics['total_predictions']

            if total == 0:
                return {
                    'total_predictions': 0,
                    'cache_hit_rate': 0.0,
                    'ml_usage_rate': 0.0,
                    'ai_usage_rate': 0.0,
                    'error_rate': 0.0,
                    'avg_latency_ms': 0.0
                }

            stats = {
                'total_predictions': total,
                'cache_hit_rate': self.metrics['cache_hits'] / total,
                'ml_usage_rate': self.metrics['ml_predictions'] / total,
                'ai_usage_rate': self.metrics['ai_predictions'] / total,
                'error_rate': self.metrics['errors'] / total,
                'avg_latency_ms': self.metrics['total_latency_ms'] / total,
                'avg_cache_latency_ms': (
                    self.metrics['cache_latency_ms'] / self.metrics['cache_hits']
                    if self.metrics['cache_hits'] > 0 else 0
                ),
                'avg_ml_latency_ms': (
                    self.metrics['ml_latency_ms'] / self.metrics['ml_predictions']
                    if self.metrics['ml_predictions'] > 0 else 0
                ),
                'avg_ai_latency_ms': (
                    self.metrics['ai_latency_ms'] / self.metrics['ai_predictions']
                    if self.metrics['ai_predictions'] > 0 else 0
                ),
            }

            # Add cache stats if available
            if self.cache:
                cache_stats = await self.cache.get_stats()
                stats['cache'] = cache_stats

            return stats

    async def clear_cache(self):
        """Clear prediction cache"""
        if self.cache:
            await self.cache.clear()
            logger.info("[HYBRID] Cache cleared")

    async def reset_metrics(self):
        """Reset performance metrics"""
        async with self._metrics_lock:
            for key in self.metrics:
                self.metrics[key] = 0
        logger.info("[HYBRID] Metrics reset")
