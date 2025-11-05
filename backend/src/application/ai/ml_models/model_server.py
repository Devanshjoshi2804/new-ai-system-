"""
Model Server - Fast ML inference with ONNX optimization

This server provides:
- Fast inference using ONNX Runtime (8-10x faster than PyTorch)
- Model versioning and A/B testing
- Batch processing for efficiency
- Fallback mechanisms for reliability
- Caching for repeated queries
"""
import logging
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class ModelCache:
    """
    Multi-layer caching for model predictions
    L1: In-memory dict (fastest)
    L2: Could be Redis (future)
    """

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0

    def _make_key(self, model_name: str, input_data: Any) -> str:
        """Generate cache key from model name and input"""
        input_str = json.dumps(input_data, sort_keys=True)
        return f"{model_name}:{hashlib.md5(input_str.encode()).hexdigest()}"

    def get(self, model_name: str, input_data: Any) -> Optional[Dict]:
        """Get cached prediction"""
        key = self._make_key(model_name, input_data)

        if key in self.cache:
            entry = self.cache[key]
            # Check if expired
            if datetime.now() < entry['expires_at']:
                self.hits += 1
                logger.debug(f"Cache HIT for {model_name}")
                return entry['result']
            else:
                # Expired, remove it
                del self.cache[key]

        self.misses += 1
        logger.debug(f"Cache MISS for {model_name}")
        return None

    def set(self, model_name: str, input_data: Any, result: Dict):
        """Store prediction in cache"""
        key = self._make_key(model_name, input_data)

        # Evict oldest if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['created_at'])
            del self.cache[oldest_key]

        self.cache[key] = {
            'result': result,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(seconds=self.ttl_seconds)
        }

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate
        }


class ModelVersion:
    """Represents a specific version of a model"""

    def __init__(
        self,
        name: str,
        version: str,
        model_path: str,
        is_onnx: bool = False,
        accuracy: Optional[float] = None
    ):
        self.name = name
        self.version = version
        self.model_path = model_path
        self.is_onnx = is_onnx
        self.accuracy = accuracy
        self.loaded_at = datetime.now()
        self.inference_count = 0
        self.total_inference_time = 0.0
        self.model = None  # Will be loaded lazily

    def load(self):
        """Load model into memory"""
        if self.model is not None:
            return  # Already loaded

        try:
            if self.is_onnx:
                # Load ONNX model
                try:
                    import onnxruntime as ort
                    self.model = ort.InferenceSession(self.model_path)
                    logger.info(f"Loaded ONNX model: {self.name} v{self.version}")
                except ImportError:
                    logger.warning("onnxruntime not installed, falling back to PyTorch")
                    self.is_onnx = False
                    self._load_pytorch_model()
            else:
                self._load_pytorch_model()

        except Exception as e:
            logger.error(f"Failed to load model {self.name}: {e}")
            raise

    def _load_pytorch_model(self):
        """Load PyTorch model"""
        try:
            import torch
            self.model = torch.load(self.model_path)
            self.model.eval()
            logger.info(f"Loaded PyTorch model: {self.name} v{self.version}")
        except ImportError:
            logger.error("torch not installed")
            raise

    def predict(self, input_data: Any) -> Any:
        """Run inference"""
        if self.model is None:
            self.load()

        start_time = time.time()

        try:
            if self.is_onnx:
                result = self._predict_onnx(input_data)
            else:
                result = self._predict_pytorch(input_data)

            inference_time = time.time() - start_time
            self.inference_count += 1
            self.total_inference_time += inference_time

            return result

        except Exception as e:
            logger.error(f"Prediction failed for {self.name}: {e}")
            raise

    def _predict_onnx(self, input_data: Any) -> Any:
        """ONNX inference"""
        # ONNX inference is ~10x faster
        outputs = self.model.run(None, input_data)
        return outputs

    def _predict_pytorch(self, input_data: Any) -> Any:
        """PyTorch inference"""
        import torch
        with torch.no_grad():
            outputs = self.model(input_data)
        return outputs

    def get_stats(self) -> Dict:
        """Get model statistics"""
        avg_time = self.total_inference_time / self.inference_count if self.inference_count > 0 else 0.0

        return {
            'name': self.name,
            'version': self.version,
            'is_onnx': self.is_onnx,
            'accuracy': self.accuracy,
            'inference_count': self.inference_count,
            'avg_inference_time_ms': avg_time * 1000,
            'loaded_at': self.loaded_at.isoformat()
        }


class ModelServer:
    """
    Central model serving infrastructure

    Features:
    - Multiple model versions with A/B testing
    - ONNX optimization for 8-10x speedup
    - Automatic fallback on errors
    - Request caching
    - Performance monitoring
    """

    def __init__(self):
        self.models = {}  # model_name -> list of ModelVersion
        self.active_versions = {}  # model_name -> active version
        self.cache = ModelCache(max_size=10000, ttl_seconds=3600)
        logger.info("Model Server initialized")

    def register_model(
        self,
        name: str,
        version: str,
        model_path: str,
        is_onnx: bool = False,
        accuracy: Optional[float] = None,
        set_active: bool = True
    ):
        """
        Register a new model version

        Args:
            name: Model name (e.g., 'endpoint_classifier')
            version: Version string (e.g., 'v1.0')
            model_path: Path to model file
            is_onnx: Whether this is an ONNX model
            accuracy: Model accuracy on validation set
            set_active: Set this as the active version
        """
        model_version = ModelVersion(
            name=name,
            version=version,
            model_path=model_path,
            is_onnx=is_onnx,
            accuracy=accuracy
        )

        if name not in self.models:
            self.models[name] = []

        self.models[name].append(model_version)

        if set_active:
            self.active_versions[name] = version

        logger.info(f"Registered model: {name} v{version} (ONNX={is_onnx}, Active={set_active})")

    def get_model(self, name: str, version: Optional[str] = None) -> Optional[ModelVersion]:
        """
        Get a specific model version

        Args:
            name: Model name
            version: Specific version (if None, returns active version)
        """
        if name not in self.models:
            logger.warning(f"Model not found: {name}")
            return None

        if version is None:
            # Get active version
            version = self.active_versions.get(name)
            if version is None:
                logger.warning(f"No active version set for {name}")
                return None

        # Find version
        for model in self.models[name]:
            if model.version == version:
                return model

        logger.warning(f"Version not found: {name} v{version}")
        return None

    async def predict(
        self,
        model_name: str,
        input_data: Dict,
        use_cache: bool = True,
        fallback: bool = True
    ) -> Dict:
        """
        Run inference with a model

        Args:
            model_name: Name of model to use
            input_data: Input data for prediction
            use_cache: Whether to use cache
            fallback: Whether to fallback to previous version on error

        Returns:
            Dict with prediction results
        """
        # Check cache first
        if use_cache:
            cached = self.cache.get(model_name, input_data)
            if cached is not None:
                cached['from_cache'] = True
                return cached

        # Get active model
        model = self.get_model(model_name)
        if model is None:
            return {
                'error': f'Model not found: {model_name}',
                'success': False
            }

        try:
            # Run prediction
            start_time = time.time()
            result = model.predict(input_data)
            inference_time = time.time() - start_time

            prediction = {
                'result': result,
                'model_name': model_name,
                'version': model.version,
                'is_onnx': model.is_onnx,
                'inference_time_ms': inference_time * 1000,
                'from_cache': False,
                'success': True
            }

            # Cache result
            if use_cache:
                self.cache.set(model_name, input_data, prediction)

            return prediction

        except Exception as e:
            logger.error(f"Prediction error for {model_name}: {e}")

            # Try fallback to previous version
            if fallback and len(self.models.get(model_name, [])) > 1:
                logger.info(f"Attempting fallback for {model_name}")
                # Get second-most-recent version
                versions = sorted(self.models[model_name], key=lambda m: m.loaded_at, reverse=True)
                if len(versions) > 1:
                    fallback_model = versions[1]
                    try:
                        result = fallback_model.predict(input_data)
                        return {
                            'result': result,
                            'model_name': model_name,
                            'version': fallback_model.version,
                            'is_onnx': fallback_model.is_onnx,
                            'fallback': True,
                            'success': True
                        }
                    except Exception as fallback_error:
                        logger.error(f"Fallback also failed: {fallback_error}")

            return {
                'error': str(e),
                'model_name': model_name,
                'success': False
            }

    async def batch_predict(
        self,
        model_name: str,
        batch_inputs: List[Dict],
        use_cache: bool = True
    ) -> List[Dict]:
        """
        Batch prediction for efficiency

        Args:
            model_name: Model to use
            batch_inputs: List of inputs
            use_cache: Whether to use cache

        Returns:
            List of predictions
        """
        results = []

        # TODO: Implement true batch inference for ONNX models
        # For now, process one by one
        for input_data in batch_inputs:
            result = await self.predict(model_name, input_data, use_cache=use_cache)
            results.append(result)

        return results

    def set_active_version(self, model_name: str, version: str):
        """
        Change the active version of a model (for A/B testing)

        Args:
            model_name: Model name
            version: Version to activate
        """
        model = self.get_model(model_name, version=version)
        if model is None:
            raise ValueError(f"Model not found: {model_name} v{version}")

        self.active_versions[model_name] = version
        logger.info(f"Activated {model_name} v{version}")

    def get_stats(self) -> Dict:
        """Get server statistics"""
        model_stats = {}

        for name, versions in self.models.items():
            model_stats[name] = {
                'active_version': self.active_versions.get(name),
                'total_versions': len(versions),
                'versions': [v.get_stats() for v in versions]
            }

        return {
            'models': model_stats,
            'cache': self.cache.get_stats(),
            'server_uptime': 'unknown'  # TODO: Track uptime
        }

    def health_check(self) -> Dict:
        """Health check for monitoring"""
        try:
            # Check if models are loaded
            models_ok = len(self.models) > 0

            # Check if active versions are set
            active_ok = len(self.active_versions) > 0

            return {
                'status': 'healthy' if (models_ok and active_ok) else 'degraded',
                'models_registered': len(self.models),
                'active_models': len(self.active_versions),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Global model server instance
_model_server: Optional[ModelServer] = None


def get_model_server() -> ModelServer:
    """Get or create global model server instance"""
    global _model_server
    if _model_server is None:
        _model_server = ModelServer()
    return _model_server


# Convenience functions for common operations
async def classify_endpoint(url: str, method: str) -> Dict:
    """Classify an endpoint using the endpoint classifier model"""
    server = get_model_server()
    return await server.predict(
        model_name='endpoint_classifier',
        input_data={'url': url, 'method': method}
    )


async def generate_payload(url: str, method: str, schema: Optional[Dict] = None) -> Dict:
    """Generate a payload using the payload generator model"""
    server = get_model_server()
    return await server.predict(
        model_name='payload_generator',
        input_data={'url': url, 'method': method, 'schema': schema}
    )


async def fix_error(error_request: str, error_message: str) -> Dict:
    """Fix an error using the error fixer model"""
    server = get_model_server()
    return await server.predict(
        model_name='error_fixer',
        input_data={'error_request': error_request, 'error_message': error_message}
    )


async def predict_workflow(endpoints: List[Dict], goal: str) -> Dict:
    """Predict workflow using the workflow predictor model"""
    server = get_model_server()
    return await server.predict(
        model_name='workflow_predictor',
        input_data={'endpoints': endpoints, 'goal': goal}
    )
