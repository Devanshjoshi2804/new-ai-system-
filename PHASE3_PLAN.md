# Phase 3: Integration & Orchestration Layer

**Status**: Starting Now
**Estimated Duration**: 3-4 days
**Priority**: HIGH
**Dependencies**: Phase 1 ✅ Complete, Phase 2 ✅ Complete

---

## Overview

Phase 3 builds the **Integration Layer** that connects:
- Discovery System (Phase 1)
- ML Models (Phase 2)
- AI APIs (Groq/Gemini/Mistral)
- Continuous Learning Loop

Creating a **Hybrid AI/ML System** with intelligent fallback:
```
User Request → Cache Check → ML Model → AI API (fallback) → Learn & Store
```

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   REST API LAYER                            │
│  POST /api/autonomous/onboard  POST /api/autonomous/test   │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│              AUTONOMOUS ORCHESTRATOR                        │
│   Coordinates: Discovery → ML Enhancement → Testing        │
└────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────┬──────────────────┬──────────────────────┐
│  HYBRID         │   EXECUTION      │   LEARNING           │
│  PREDICTOR      │   ENGINE         │   LOOP               │
│                 │                  │                      │
│  1. Cache       │  - Retry logic   │  - Store patterns    │
│  2. ML Models   │  - Parallel exec │  - Update models     │
│  3. AI APIs     │  - Dependencies  │  - Feedback loop     │
│  (fallback)     │  - Rate limit    │  - Metrics           │
└─────────────────┴──────────────────┴──────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│                    DATA LAYER                               │
│  Flow DB (ChromaDB) | Model Cache | MongoDB | Redis        │
└────────────────────────────────────────────────────────────┘
```

---

## Components to Build

### 1. Hybrid Prediction System
**File**: `backend/src/application/ai/hybrid/hybrid_predictor.py`
**Lines**: 500-600
**Priority**: HIGHEST

**Purpose**: Intelligent multi-tier prediction system with fallback

**Key Features**:
```python
class HybridPredictor:
    """
    Multi-tier prediction system:
    1. Cache Check (Redis) - Instant (<5ms)
    2. ML Model Inference - Fast (<100ms)
    3. AI API Call - Fallback (>1s)
    """

    async def predict_endpoint_classification(
        url: str,
        method: str,
        context: Dict
    ) -> PredictionResult:
        # Try cache first
        cached = await self.cache_store.get(cache_key)
        if cached and cached.confidence > 0.9:
            return cached

        # Try ML model
        ml_result = await self.ml_predictor.classify(url, method)
        if ml_result.confidence > 0.7:
            await self.cache_store.set(cache_key, ml_result)
            return ml_result

        # Fallback to AI API
        ai_result = await self.ai_predictor.classify(url, method, context)
        await self.learning_loop.store_for_training(ai_result)
        return ai_result

    async def generate_payload(
        endpoint: Dict,
        schema: Dict,
        flow_db_context: str
    ) -> PayloadResult:
        """Generate payload with hybrid approach"""
        pass

    async def fix_error(
        request: Dict,
        error_response: Dict,
        attempt: int
    ) -> FixResult:
        """Fix errors with hybrid approach"""
        pass
```

**Performance Metrics Tracked**:
- Hit rate per tier (cache/ML/AI)
- Latency per tier
- Confidence scores
- Cost per prediction (AI API calls)
- Accuracy over time

---

### 2. Autonomous Orchestrator
**File**: `backend/src/application/ai/orchestration/autonomous_orchestrator.py`
**Lines**: 600-700
**Priority**: HIGH

**Purpose**: Main coordinator for end-to-end autonomous workflow

**Workflow Steps**:
```python
class AutonomousOrchestrator:
    """
    Complete autonomous onboarding workflow:
    1. Discovery Phase
    2. ML Enhancement Phase
    3. Testing Phase
    4. Learning Phase
    """

    async def autonomous_onboard(
        minimal_info: str,
        auth_token: Optional[str] = None
    ) -> OnboardingResult:
        """
        Full autonomous onboarding from URL to working integration
        """
        # Phase 1: Discovery
        discovery_result = await self.api_explorer.explore(minimal_info)
        auth_config = await self.auth_detector.detect(discovery_result.base_url)
        schemas = await self.schema_inferencer.infer_schemas(discovery_result.endpoints)
        dependency_graph = await self.relationship_analyzer.analyze(
            discovery_result.endpoints
        )

        # Phase 2: ML Enhancement
        # Use Hybrid Predictor for intelligent classification
        classified_endpoints = await self.hybrid_predictor.classify_batch(
            discovery_result.endpoints
        )

        # Generate test payloads using hybrid approach
        test_payloads = await self.hybrid_predictor.generate_payloads_batch(
            classified_endpoints,
            schemas
        )

        # Phase 3: Testing
        test_results = await self.execution_engine.execute_tests(
            classified_endpoints,
            test_payloads,
            auth_config,
            dependency_graph
        )

        # Phase 4: Learning
        await self.learning_loop.process_results(test_results)

        return OnboardingResult(
            discovery=discovery_result,
            ml_enhancements=classified_endpoints,
            test_results=test_results,
            success_rate=self._calculate_success_rate(test_results)
        )

    async def test_integration(
        partner_id: str,
        endpoint: str
    ) -> TestResult:
        """Test a single endpoint with hybrid prediction"""
        pass

    async def fix_failing_endpoint(
        partner_id: str,
        endpoint: str,
        error_details: Dict
    ) -> FixResult:
        """Use hybrid error fixer to fix failing endpoint"""
        pass
```

---

### 3. Enhanced Execution Engine
**File**: `backend/src/application/ai/orchestration/execution_engine.py`
**Lines**: 400-500
**Priority**: HIGH

**Purpose**: Execute API tests with retries, dependencies, and error handling

**Key Features**:
```python
class ExecutionEngine:
    """
    Intelligent test execution engine
    """

    async def execute_tests(
        endpoints: List[Dict],
        payloads: Dict[str, Dict],
        auth_config: AuthConfiguration,
        dependency_graph: DependencyGraph
    ) -> List[TestResult]:
        """
        Execute tests in correct order respecting dependencies
        """
        # Topological sort for execution order
        execution_order = dependency_graph.get_execution_order()

        results = []
        for endpoint_id in execution_order:
            endpoint = self._get_endpoint(endpoint_id, endpoints)
            payload = payloads.get(endpoint_id)

            # Execute with retry and error fixing
            result = await self._execute_with_retry(
                endpoint,
                payload,
                auth_config,
                max_retries=3
            )

            results.append(result)

            # Store results in Flow DB for learning
            if result.success:
                await self.flow_db.store_success(endpoint, payload, result)
            else:
                await self.flow_db.store_failure(endpoint, payload, result)

        return results

    async def _execute_with_retry(
        self,
        endpoint: Dict,
        payload: Dict,
        auth_config: AuthConfiguration,
        max_retries: int = 3
    ) -> TestResult:
        """
        Execute with intelligent retry and error fixing
        """
        for attempt in range(max_retries):
            try:
                result = await self._execute_single(endpoint, payload, auth_config)

                if result.success:
                    return result

                # Use hybrid error fixer
                fixed_payload = await self.hybrid_predictor.fix_error(
                    payload,
                    result.error_response,
                    attempt
                )

                payload = fixed_payload

            except Exception as e:
                if attempt == max_retries - 1:
                    return TestResult(
                        success=False,
                        error=str(e),
                        attempts=attempt + 1
                    )

        return TestResult(success=False, attempts=max_retries)

    async def _execute_single(
        self,
        endpoint: Dict,
        payload: Dict,
        auth_config: AuthConfiguration
    ) -> TestResult:
        """Execute single API call"""
        pass
```

---

### 4. Continuous Learning Loop
**File**: `backend/src/application/ai/orchestration/learning_loop.py`
**Lines**: 300-400
**Priority**: MEDIUM

**Purpose**: Continuous learning from production data

**Key Features**:
```python
class LearningLoop:
    """
    Continuous learning system that improves over time
    """

    async def process_results(self, test_results: List[TestResult]):
        """
        Process test results and trigger learning
        """
        # Extract training examples
        training_examples = self._extract_training_data(test_results)

        # Store in Flow DB
        await self.flow_db.store_batch(training_examples)

        # Check if retraining threshold reached
        if await self._should_retrain():
            await self.trigger_retraining()

    async def trigger_retraining(self):
        """
        Trigger model retraining when enough new data collected
        """
        # Get training data from Flow DB
        training_data = await self.flow_db.get_training_data()

        # Trigger async training job
        await self.training_pipeline.train_models(training_data)

    async def _should_retrain(self) -> bool:
        """
        Determine if we have enough new data to retrain

        Criteria:
        - N new successful examples (e.g., 1000)
        - M days since last training (e.g., 7)
        - Accuracy drop detected
        """
        pass

    def _extract_training_data(
        self,
        test_results: List[TestResult]
    ) -> List[TrainingExample]:
        """Extract labeled training examples from test results"""
        pass
```

---

### 5. Performance Monitor
**File**: `backend/src/application/ai/orchestration/performance_monitor.py`
**Lines**: 300-400
**Priority**: MEDIUM

**Purpose**: Track system performance and model metrics

**Key Metrics**:
```python
class PerformanceMonitor:
    """
    Monitor system performance and model accuracy
    """

    async def track_prediction(
        self,
        prediction_type: str,  # "classification", "payload", "error_fix"
        tier_used: str,  # "cache", "ml", "ai_api"
        latency_ms: float,
        confidence: float,
        success: bool
    ):
        """Track individual prediction performance"""
        await self.metrics_store.increment(
            f"{prediction_type}.{tier_used}.count"
        )
        await self.metrics_store.record(
            f"{prediction_type}.{tier_used}.latency",
            latency_ms
        )
        await self.metrics_store.record(
            f"{prediction_type}.{tier_used}.confidence",
            confidence
        )
        if success:
            await self.metrics_store.increment(
                f"{prediction_type}.{tier_used}.success"
            )

    async def get_metrics_summary(
        self,
        time_range: str = "24h"
    ) -> MetricsSummary:
        """
        Get performance summary:
        - Hit rate by tier
        - Average latency by tier
        - Success rate by tier
        - Cost savings (AI API calls avoided)
        - Model accuracy trends
        """
        pass

    async def detect_accuracy_degradation(self) -> bool:
        """Detect if model accuracy is dropping"""
        pass
```

---

### 6. Model Registry & Versioning
**File**: `backend/src/application/ai/orchestration/model_registry.py`
**Lines**: 300-400
**Priority**: MEDIUM

**Purpose**: Manage model versions and A/B testing

**Key Features**:
```python
class ModelRegistry:
    """
    Manage ML model versions and deployments
    """

    async def register_model(
        self,
        model_name: str,
        version: str,
        model_path: str,
        metrics: Dict[str, float]
    ):
        """Register new model version"""
        pass

    async def get_active_model(
        self,
        model_name: str
    ) -> ModelVersion:
        """Get currently active model version"""
        pass

    async def promote_model(
        self,
        model_name: str,
        version: str
    ):
        """
        Promote model version to production
        - Run A/B test
        - Compare metrics
        - Auto-promote if better
        """
        pass

    async def rollback_model(
        self,
        model_name: str,
        to_version: str
    ):
        """Rollback to previous model version"""
        pass
```

---

### 7. REST API Endpoints
**File**: `backend/src/presentation/rest/orchestration.py`
**Lines**: 400-500
**Priority**: HIGH

**New Endpoints**:
```python
# Autonomous Onboarding
POST   /api/autonomous/onboard
{
  "url_or_snippet": "https://api.example.com",
  "auth_token": "optional-token"
}

# Test Integration
POST   /api/autonomous/test
{
  "partner_id": "partner_123",
  "endpoint": "/api/users"
}

# Fix Failing Endpoint
POST   /api/autonomous/fix
{
  "partner_id": "partner_123",
  "endpoint": "/api/users",
  "error_details": {...}
}

# Get Operation Status
GET    /api/autonomous/status/{operation_id}

# Get Performance Metrics
GET    /api/autonomous/metrics?range=24h

# Trigger Model Retraining
POST   /api/autonomous/retrain
{
  "model_name": "endpoint_classifier"
}

# Get Model Registry
GET    /api/autonomous/models
```

---

## Implementation Plan

### Day 1: Core Hybrid System
**Focus**: Build the hybrid prediction system
- ✅ Create `hybrid_predictor.py` (500-600 lines)
- ✅ Implement cache layer (Redis)
- ✅ Implement ML model tier
- ✅ Implement AI API fallback tier
- ✅ Add performance tracking
- ✅ Write unit tests

**Deliverables**:
- Hybrid prediction system working
- 3-tier fallback (cache → ML → AI)
- Metrics collection in place

---

### Day 2: Orchestrator & Execution
**Focus**: Build autonomous orchestrator and execution engine
- ✅ Create `autonomous_orchestrator.py` (600-700 lines)
- ✅ Create `execution_engine.py` (400-500 lines)
- ✅ Integrate with Phase 1 (Discovery)
- ✅ Integrate with Phase 2 (ML Models)
- ✅ Add retry logic and error handling
- ✅ Dependency resolution
- ✅ Write integration tests

**Deliverables**:
- End-to-end autonomous onboarding working
- Tests executing in correct order
- Error fixing with retries

---

### Day 3: Learning Loop & APIs
**Focus**: Continuous learning and REST APIs
- ✅ Create `learning_loop.py` (300-400 lines)
- ✅ Create `performance_monitor.py` (300-400 lines)
- ✅ Create `model_registry.py` (300-400 lines)
- ✅ Create `orchestration.py` REST APIs (400-500 lines)
- ✅ Integrate with training pipeline
- ✅ Add monitoring and alerts
- ✅ Write API tests

**Deliverables**:
- Continuous learning loop active
- REST APIs available
- Performance monitoring dashboard
- Model versioning system

---

### Day 4: Integration Testing & Optimization
**Focus**: End-to-end testing and performance optimization
- ✅ End-to-end integration tests
- ✅ Load testing (1000+ req/sec)
- ✅ Cache optimization
- ✅ Model inference optimization
- ✅ Error scenarios testing
- ✅ Documentation
- ✅ Demo preparation

**Deliverables**:
- All tests passing
- Performance benchmarks met
- Documentation complete
- Ready for Phase 4

---

## Success Metrics

### Performance Targets
- ✅ **Cache Hit Rate**: >80% after warmup
- ✅ **ML Model Inference**: <100ms p99
- ✅ **Total Prediction Time**: <200ms p99
- ✅ **AI API Fallback**: <10% of predictions
- ✅ **Success Rate**: >90% on first test attempt
- ✅ **Error Fix Rate**: >70% after 3 retries

### Cost Savings
- ✅ **AI API Calls Avoided**: >80% (via cache + ML)
- ✅ **Cost per Prediction**: <$0.001 average
- ✅ **Cost Reduction**: >90% vs AI-only approach

### Accuracy
- ✅ **Endpoint Classification**: >95% accuracy
- ✅ **Payload Generation**: >85% valid payloads
- ✅ **Error Fixing**: >70% successful fixes
- ✅ **Workflow Prediction**: >80% optimal paths

---

## Dependencies Required

```txt
# Redis for caching
redis==5.0.0
aioredis==2.0.1

# Model serving
onnxruntime==1.16.0

# Monitoring
prometheus-client==0.19.0
```

---

## Testing Strategy

### Unit Tests
- Each component tested independently
- Mock external dependencies
- 90%+ code coverage

### Integration Tests
- End-to-end workflow testing
- Real API calls (JSONPlaceholder)
- Database integration
- Model inference

### Performance Tests
- Load test with 1000+ concurrent requests
- Cache hit rate measurement
- Latency profiling
- Memory usage profiling

---

## Documentation

### Technical Docs
- Architecture diagrams
- API specifications (OpenAPI)
- Component interaction diagrams
- Deployment guide

### User Docs
- API usage examples
- Integration guide
- Troubleshooting guide
- Performance tuning guide

---

## Phase 3 Deliverables

**Code Files** (7 new):
1. `backend/src/application/ai/hybrid/hybrid_predictor.py` (500-600 lines)
2. `backend/src/application/ai/orchestration/autonomous_orchestrator.py` (600-700 lines)
3. `backend/src/application/ai/orchestration/execution_engine.py` (400-500 lines)
4. `backend/src/application/ai/orchestration/learning_loop.py` (300-400 lines)
5. `backend/src/application/ai/orchestration/performance_monitor.py` (300-400 lines)
6. `backend/src/application/ai/orchestration/model_registry.py` (300-400 lines)
7. `backend/src/presentation/rest/orchestration.py` (400-500 lines)

**Test Files** (4 new):
1. `backend/tests/test_hybrid_predictor.py`
2. `backend/tests/test_autonomous_orchestrator.py`
3. `backend/tests/test_execution_engine.py`
4. `backend/tests/test_orchestration_apis.py`

**Documentation** (3 new):
1. `PHASE3_COMPLETE.md`
2. `INTEGRATION_GUIDE.md`
3. `API_REFERENCE.md`

**Total Lines**: ~3,400-4,000 lines of production code

---

## Next Steps After Phase 3

Once Phase 3 is complete, we'll have:
- ✅ Complete autonomous onboarding pipeline
- ✅ Hybrid AI/ML system with intelligent fallback
- ✅ Continuous learning from production data
- ✅ REST APIs for all orchestration operations
- ✅ Performance monitoring and metrics
- ✅ Model versioning and registry

**Ready for Phase 4**: Frontend & User Experience

---

**Document Version**: 1.0
**Created**: November 5, 2025
**Status**: Implementation Ready
**Estimated Completion**: November 8-9, 2025
