"""
ML Model Integration Adapters

Provides consistent interface for HybridPredictor to call Phase 2 ML models.
Handles model loading, inference, and result formatting.
"""

import logging
from typing import Dict, Any, Optional, List
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


class EndpointClassifierAdapter:
    """
    Adapter for EndpointClassifier ML model

    Provides async interface for endpoint classification predictions.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize classifier adapter

        Args:
            model_path: Path to saved model (optional)
        """
        self.model_path = model_path
        self.model = None
        self.loaded = False

        logger.info("[ML_ADAPTER] EndpointClassifier adapter initialized")

    async def load_model(self):
        """Load the ML model asynchronously"""
        if self.loaded:
            return

        try:
            # Import the Phase 2 model
            from backend.src.application.ai.ml_models.endpoint_classifier import (
                EndpointClassifierModel
            )

            # Load model in thread pool to avoid blocking
            def _load():
                model = EndpointClassifierModel()
                if self.model_path and Path(self.model_path).exists():
                    model.load(self.model_path)
                return model

            self.model = await asyncio.to_thread(_load)
            self.loaded = True

            logger.info("[ML_ADAPTER] EndpointClassifier model loaded successfully")

        except Exception as e:
            logger.error(f"[ML_ADAPTER] Failed to load EndpointClassifier: {e}")
            raise

    async def classify_endpoint(
        self,
        url: str,
        method: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify API endpoint

        Args:
            url: Endpoint URL
            method: HTTP method
            context: Additional context (headers, description, etc.)

        Returns:
            Dictionary with classification result and confidence
        """
        # Ensure model is loaded
        if not self.loaded:
            await self.load_model()

        try:
            # Call model prediction in thread pool
            def _predict():
                # Prepare input text
                context_str = ""
                if context:
                    if 'description' in context:
                        context_str = f" {context['description']}"
                    elif 'headers' in context:
                        context_str = f" Headers: {context['headers']}"

                input_text = f"{method} {url}{context_str}"

                # Get prediction
                result = self.model.predict([input_text])

                if not result or len(result) == 0:
                    return {
                        'category': 'unknown',
                        'confidence': 0.0,
                        'error': 'No prediction returned'
                    }

                prediction = result[0]

                # Map category to standard categories
                category_map = {
                    'auth': 'authentication',
                    'authentication': 'authentication',
                    'get': 'data_retrieval',
                    'retrieve': 'data_retrieval',
                    'post': 'data_creation',
                    'create': 'data_creation',
                    'put': 'data_update',
                    'update': 'data_update',
                    'patch': 'data_update',
                    'delete': 'data_deletion',
                    'upload': 'file_upload',
                    'search': 'search',
                    'webhook': 'webhook',
                    'payment': 'payment',
                    'analytics': 'analytics'
                }

                category = prediction.get('category', 'unknown').lower()
                mapped_category = category_map.get(category, 'other')

                # Extract operation type from URL
                path_parts = url.split('/')
                operation_type = path_parts[-1] if path_parts else 'unknown'

                return {
                    'category': mapped_category,
                    'operation_type': operation_type,
                    'required_params': prediction.get('required_params', []),
                    'optional_params': prediction.get('optional_params', []),
                    'description': f"{method} request to {url}",
                    'confidence': prediction.get('confidence', 0.75)
                }

            result = await asyncio.to_thread(_predict)
            return result

        except Exception as e:
            logger.error(f"[ML_ADAPTER] Classification error: {e}")
            return {
                'category': 'unknown',
                'confidence': 0.0,
                'error': str(e)
            }


class PayloadGeneratorAdapter:
    """
    Adapter for PayloadGenerator ML model

    Provides async interface for payload generation.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize payload generator adapter

        Args:
            model_path: Path to saved model (optional)
        """
        self.model_path = model_path
        self.model = None
        self.loaded = False

        logger.info("[ML_ADAPTER] PayloadGenerator adapter initialized")

    async def load_model(self):
        """Load the ML model asynchronously"""
        if self.loaded:
            return

        try:
            from backend.src.application.ai.ml_models.payload_generator import (
                PayloadGeneratorModel
            )

            def _load():
                model = PayloadGeneratorModel()
                if self.model_path and Path(self.model_path).exists():
                    model.load(self.model_path)
                return model

            self.model = await asyncio.to_thread(_load)
            self.loaded = True

            logger.info("[ML_ADAPTER] PayloadGenerator model loaded successfully")

        except Exception as e:
            logger.error(f"[ML_ADAPTER] Failed to load PayloadGenerator: {e}")
            raise

    async def generate_payload(
        self,
        endpoint_url: str,
        method: str,
        schema: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate request payload

        Args:
            endpoint_url: API endpoint URL
            method: HTTP method
            schema: OpenAPI schema if available
            context: Additional context

        Returns:
            Dictionary with generated payload and confidence
        """
        if not self.loaded:
            await self.load_model()

        try:
            def _generate():
                # Prepare input for model
                schema_str = str(schema) if schema else ""
                context_str = str(context) if context else ""

                input_text = f"""Generate payload for:
URL: {endpoint_url}
Method: {method}
Schema: {schema_str}
Context: {context_str}"""

                # Get prediction
                result = self.model.generate([input_text])

                if not result or len(result) == 0:
                    return {
                        'payload': {},
                        'confidence': 0.0,
                        'error': 'No payload generated'
                    }

                generated = result[0]

                return {
                    'payload': generated.get('payload', {}),
                    'confidence': generated.get('confidence', 0.75)
                }

            result = await asyncio.to_thread(_generate)
            return result

        except Exception as e:
            logger.error(f"[ML_ADAPTER] Payload generation error: {e}")
            return {
                'payload': {},
                'confidence': 0.0,
                'error': str(e)
            }


class ErrorFixerAdapter:
    """
    Adapter for ErrorFixer ML model

    Provides async interface for error fixing.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize error fixer adapter

        Args:
            model_path: Path to saved model (optional)
        """
        self.model_path = model_path
        self.model = None
        self.loaded = False

        logger.info("[ML_ADAPTER] ErrorFixer adapter initialized")

    async def load_model(self):
        """Load the ML model asynchronously"""
        if self.loaded:
            return

        try:
            from backend.src.application.ai.ml_models.error_fixer import (
                ErrorFixerModel
            )

            def _load():
                model = ErrorFixerModel()
                if self.model_path and Path(self.model_path).exists():
                    model.load(self.model_path)
                return model

            self.model = await asyncio.to_thread(_load)
            self.loaded = True

            logger.info("[ML_ADAPTER] ErrorFixer model loaded successfully")

        except Exception as e:
            logger.error(f"[ML_ADAPTER] Failed to load ErrorFixer: {e}")
            raise

    async def fix_error(
        self,
        endpoint_url: str,
        error_response: Dict[str, Any],
        original_payload: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fix error by suggesting corrected payload

        Args:
            endpoint_url: API endpoint URL
            error_response: Error response from API
            original_payload: Original payload that caused error
            context: Additional context

        Returns:
            Dictionary with fixed payload and confidence
        """
        if not self.loaded:
            await self.load_model()

        try:
            def _fix():
                # Prepare input for model
                error_str = str(error_response)
                payload_str = str(original_payload)
                context_str = str(context) if context else ""

                input_text = f"""Fix error for:
URL: {endpoint_url}
Original Payload: {payload_str}
Error: {error_str}
Context: {context_str}"""

                # Get prediction
                result = self.model.fix([input_text])

                if not result or len(result) == 0:
                    return {
                        'fixed_payload': original_payload,
                        'changes': [],
                        'confidence': 0.0,
                        'error': 'No fix generated'
                    }

                fixed = result[0]

                return {
                    'fixed_payload': fixed.get('fixed_payload', original_payload),
                    'changes': fixed.get('changes', []),
                    'confidence': fixed.get('confidence', 0.75)
                }

            result = await asyncio.to_thread(_fix)
            return result

        except Exception as e:
            logger.error(f"[ML_ADAPTER] Error fixing error: {e}")
            return {
                'fixed_payload': original_payload,
                'changes': [],
                'confidence': 0.0,
                'error': str(e)
            }


class WorkflowPredictorAdapter:
    """
    Adapter for WorkflowPredictor ML model (GNN-based)

    Provides async interface for workflow and dependency prediction.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize workflow predictor adapter

        Args:
            model_path: Path to saved model (optional)
        """
        self.model_path = model_path
        self.model = None
        self.loaded = False

        logger.info("[ML_ADAPTER] WorkflowPredictor adapter initialized")

    async def load_model(self):
        """Load the ML model asynchronously"""
        if self.loaded:
            return

        try:
            from backend.src.application.ai.ml_models.workflow_predictor import (
                WorkflowPredictorModel
            )

            def _load():
                model = WorkflowPredictorModel()
                if self.model_path and Path(self.model_path).exists():
                    model.load(self.model_path)
                return model

            self.model = await asyncio.to_thread(_load)
            self.loaded = True

            logger.info("[ML_ADAPTER] WorkflowPredictor model loaded successfully")

        except Exception as e:
            logger.error(f"[ML_ADAPTER] Failed to load WorkflowPredictor: {e}")
            raise

    async def predict_workflow(
        self,
        endpoints: List[Dict[str, Any]],
        api_graph: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Predict workflow and dependencies between endpoints

        Args:
            endpoints: List of API endpoints
            api_graph: Optional API graph structure

        Returns:
            Dictionary with workflow prediction and confidence
        """
        if not self.loaded:
            await self.load_model()

        try:
            def _predict():
                # Prepare graph data
                if not api_graph:
                    # Build simple graph from endpoints
                    api_graph = {
                        'nodes': [
                            {
                                'id': i,
                                'url': ep.get('url', ''),
                                'method': ep.get('method', 'GET')
                            }
                            for i, ep in enumerate(endpoints)
                        ],
                        'edges': []  # No edges if not provided
                    }

                # Get prediction
                result = self.model.predict(api_graph)

                if not result:
                    return {
                        'workflow': [],
                        'dependencies': {},
                        'confidence': 0.0,
                        'error': 'No workflow predicted'
                    }

                return {
                    'workflow': result.get('workflow', []),
                    'dependencies': result.get('dependencies', {}),
                    'confidence': result.get('confidence', 0.75)
                }

            result = await asyncio.to_thread(_predict)
            return result

        except Exception as e:
            logger.error(f"[ML_ADAPTER] Workflow prediction error: {e}")
            return {
                'workflow': [],
                'dependencies': {},
                'confidence': 0.0,
                'error': str(e)
            }


def create_ml_adapters(model_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Factory function to create all ML model adapters

    Args:
        model_dir: Directory containing saved models

    Returns:
        Dictionary mapping model names to adapter instances
    """
    model_dir = Path(model_dir) if model_dir else Path("./models")

    adapters = {
        'endpoint_classifier': EndpointClassifierAdapter(
            model_path=str(model_dir / "endpoint_classifier.pt")
            if (model_dir / "endpoint_classifier.pt").exists() else None
        ),
        'payload_generator': PayloadGeneratorAdapter(
            model_path=str(model_dir / "payload_generator.pt")
            if (model_dir / "payload_generator.pt").exists() else None
        ),
        'error_fixer': ErrorFixerAdapter(
            model_path=str(model_dir / "error_fixer.pt")
            if (model_dir / "error_fixer.pt").exists() else None
        ),
        'workflow_predictor': WorkflowPredictorAdapter(
            model_path=str(model_dir / "workflow_predictor.pt")
            if (model_dir / "workflow_predictor.pt").exists() else None
        )
    }

    logger.info(f"[ML_ADAPTER] Created {len(adapters)} ML adapters")

    return adapters
