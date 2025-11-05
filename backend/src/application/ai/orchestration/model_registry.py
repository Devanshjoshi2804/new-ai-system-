"""
Model Registry

ML model version management system with A/B testing support.

Features:
- Model versioning and metadata
- Performance tracking per version
- A/B testing support
- Model promotion and rollback
- Model comparison
- Deployment management
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class ModelStatus(str, Enum):
    """Model deployment status"""
    TRAINING = "training"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    RETIRED = "retired"


@dataclass
class ModelVersion:
    """Model version with metadata"""
    model_id: str
    version: str
    model_type: str  # 'endpoint_classifier', 'payload_generator', etc.
    status: ModelStatus

    # Files
    model_path: Optional[str] = None
    config_path: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    description: str = ""
    tags: List[str] = field(default_factory=list)

    # Training info
    training_data_size: int = 0
    training_duration_seconds: float = 0.0
    training_metrics: Dict[str, Any] = field(default_factory=dict)

    # Performance metrics
    inference_count: int = 0
    avg_latency_ms: float = 0.0
    avg_confidence: float = 0.0
    accuracy: float = 0.0

    # A/B testing
    ab_test_group: Optional[str] = None  # 'A', 'B', None
    ab_test_traffic_percent: float = 0.0

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'model_id': self.model_id,
            'version': self.version,
            'model_type': self.model_type,
            'status': self.status.value,
            'model_path': self.model_path,
            'config_path': self.config_path,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'description': self.description,
            'tags': self.tags,
            'training_data_size': self.training_data_size,
            'training_duration_seconds': self.training_duration_seconds,
            'training_metrics': self.training_metrics,
            'inference_count': self.inference_count,
            'avg_latency_ms': self.avg_latency_ms,
            'avg_confidence': self.avg_confidence,
            'accuracy': self.accuracy,
            'ab_test_group': self.ab_test_group,
            'ab_test_traffic_percent': self.ab_test_traffic_percent,
            'metadata': self.metadata
        }


class ModelRegistry:
    """
    Central registry for ML model versions

    Manages model lifecycle, versioning, and deployment strategies
    including A/B testing and gradual rollouts.
    """

    def __init__(
        self,
        registry_path: str = "./data/model_registry.json",
        models_dir: str = "./models"
    ):
        """
        Initialize model registry

        Args:
            registry_path: Path to registry metadata file
            models_dir: Directory containing model files
        """
        self.registry_path = Path(registry_path)
        self.models_dir = Path(models_dir)

        # Ensure directories exist
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Model versions
        self.models: Dict[str, ModelVersion] = {}

        # Load existing registry
        self._load_registry()

        logger.info(f"[MODEL_REGISTRY] Initialized: {len(self.models)} models registered")

    def _load_registry(self):
        """Load registry from disk"""
        if not self.registry_path.exists():
            logger.info("[MODEL_REGISTRY] No existing registry found")
            return

        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)

            for model_data in data.get('models', []):
                # Reconstruct ModelVersion from dict
                model = ModelVersion(
                    model_id=model_data['model_id'],
                    version=model_data['version'],
                    model_type=model_data['model_type'],
                    status=ModelStatus(model_data['status']),
                    model_path=model_data.get('model_path'),
                    config_path=model_data.get('config_path'),
                    created_at=datetime.fromisoformat(model_data['created_at']),
                    created_by=model_data.get('created_by', 'system'),
                    description=model_data.get('description', ''),
                    tags=model_data.get('tags', []),
                    training_data_size=model_data.get('training_data_size', 0),
                    training_duration_seconds=model_data.get('training_duration_seconds', 0.0),
                    training_metrics=model_data.get('training_metrics', {}),
                    inference_count=model_data.get('inference_count', 0),
                    avg_latency_ms=model_data.get('avg_latency_ms', 0.0),
                    avg_confidence=model_data.get('avg_confidence', 0.0),
                    accuracy=model_data.get('accuracy', 0.0),
                    ab_test_group=model_data.get('ab_test_group'),
                    ab_test_traffic_percent=model_data.get('ab_test_traffic_percent', 0.0),
                    metadata=model_data.get('metadata', {})
                )

                self.models[model.model_id] = model

            logger.info(f"[MODEL_REGISTRY] Loaded {len(self.models)} models")

        except Exception as e:
            logger.error(f"[MODEL_REGISTRY] Failed to load registry: {e}")

    def _save_registry(self):
        """Save registry to disk"""
        try:
            data = {
                'models': [model.to_dict() for model in self.models.values()],
                'last_updated': datetime.utcnow().isoformat()
            }

            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug("[MODEL_REGISTRY] Registry saved")

        except Exception as e:
            logger.error(f"[MODEL_REGISTRY] Failed to save registry: {e}")

    def register_model(
        self,
        model_type: str,
        version: str,
        model_path: str,
        config_path: Optional[str] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
        training_metrics: Optional[Dict[str, Any]] = None,
        status: ModelStatus = ModelStatus.TESTING
    ) -> ModelVersion:
        """
        Register a new model version

        Args:
            model_type: Type of model
            version: Version string
            model_path: Path to model file
            config_path: Path to config file
            description: Model description
            tags: Optional tags
            training_metrics: Training metrics
            status: Initial status

        Returns:
            Registered model version
        """
        model_id = f"{model_type}_{version}"

        if model_id in self.models:
            logger.warning(f"[MODEL_REGISTRY] Model already registered: {model_id}")
            return self.models[model_id]

        model = ModelVersion(
            model_id=model_id,
            version=version,
            model_type=model_type,
            status=status,
            model_path=model_path,
            config_path=config_path,
            description=description,
            tags=tags or [],
            training_metrics=training_metrics or {}
        )

        self.models[model_id] = model
        self._save_registry()

        logger.info(f"[MODEL_REGISTRY] Registered model: {model_id}")

        return model

    def get_model(self, model_id: str) -> Optional[ModelVersion]:
        """Get model version by ID"""
        return self.models.get(model_id)

    def get_models_by_type(
        self,
        model_type: str,
        status: Optional[ModelStatus] = None
    ) -> List[ModelVersion]:
        """
        Get all models of a specific type

        Args:
            model_type: Type of model
            status: Optional status filter

        Returns:
            List of matching models
        """
        models = [
            m for m in self.models.values()
            if m.model_type == model_type
        ]

        if status:
            models = [m for m in models if m.status == status]

        # Sort by created_at descending
        models.sort(key=lambda m: m.created_at, reverse=True)

        return models

    def get_production_model(self, model_type: str) -> Optional[ModelVersion]:
        """Get current production model for a type"""
        models = self.get_models_by_type(model_type, status=ModelStatus.PRODUCTION)

        if not models:
            return None

        # Return most recent production model
        return models[0]

    def promote_model(
        self,
        model_id: str,
        target_status: ModelStatus
    ) -> bool:
        """
        Promote model to new status

        Args:
            model_id: Model to promote
            target_status: Target status

        Returns:
            True if successful
        """
        model = self.get_model(model_id)

        if not model:
            logger.error(f"[MODEL_REGISTRY] Model not found: {model_id}")
            return False

        # Validate promotion path
        valid_promotions = {
            ModelStatus.TRAINING: [ModelStatus.TESTING, ModelStatus.RETIRED],
            ModelStatus.TESTING: [ModelStatus.STAGING, ModelStatus.RETIRED],
            ModelStatus.STAGING: [ModelStatus.PRODUCTION, ModelStatus.TESTING, ModelStatus.RETIRED],
            ModelStatus.PRODUCTION: [ModelStatus.RETIRED]
        }

        if target_status not in valid_promotions.get(model.status, []):
            logger.error(
                f"[MODEL_REGISTRY] Invalid promotion: "
                f"{model.status} -> {target_status}"
            )
            return False

        # If promoting to production, retire current production model
        if target_status == ModelStatus.PRODUCTION:
            current_prod = self.get_production_model(model.model_type)
            if current_prod and current_prod.model_id != model_id:
                logger.info(
                    f"[MODEL_REGISTRY] Retiring current production model: "
                    f"{current_prod.model_id}"
                )
                current_prod.status = ModelStatus.RETIRED

        model.status = target_status
        self._save_registry()

        logger.info(f"[MODEL_REGISTRY] Promoted {model_id} to {target_status.value}")

        return True

    def rollback_model(self, model_type: str) -> bool:
        """
        Rollback to previous production model

        Args:
            model_type: Type of model to rollback

        Returns:
            True if successful
        """
        # Get current production model
        current = self.get_production_model(model_type)

        if not current:
            logger.error(f"[MODEL_REGISTRY] No production model to rollback: {model_type}")
            return False

        # Find previous production model (now retired)
        retired_models = self.get_models_by_type(model_type, status=ModelStatus.RETIRED)

        if not retired_models:
            logger.error(f"[MODEL_REGISTRY] No retired model to rollback to: {model_type}")
            return False

        previous = retired_models[0]  # Most recently retired

        # Swap statuses
        current.status = ModelStatus.RETIRED
        previous.status = ModelStatus.PRODUCTION

        self._save_registry()

        logger.info(
            f"[MODEL_REGISTRY] Rolled back {model_type}: "
            f"{current.model_id} -> {previous.model_id}"
        )

        return True

    def update_performance(
        self,
        model_id: str,
        inference_count: int = 1,
        latency_ms: float = 0.0,
        confidence: float = 0.0,
        accuracy: Optional[float] = None
    ):
        """
        Update model performance metrics

        Args:
            model_id: Model ID
            inference_count: Number of inferences (increment)
            latency_ms: Latency to add
            confidence: Confidence to add
            accuracy: Optional accuracy update
        """
        model = self.get_model(model_id)

        if not model:
            return

        # Update running averages
        total = model.inference_count + inference_count

        model.avg_latency_ms = (
            (model.avg_latency_ms * model.inference_count + latency_ms * inference_count) / total
        )

        model.avg_confidence = (
            (model.avg_confidence * model.inference_count + confidence * inference_count) / total
        )

        model.inference_count = total

        if accuracy is not None:
            model.accuracy = accuracy

        self._save_registry()

    def setup_ab_test(
        self,
        model_a_id: str,
        model_b_id: str,
        traffic_split: float = 0.5
    ) -> bool:
        """
        Setup A/B test between two models

        Args:
            model_a_id: Model A ID
            model_b_id: Model B ID
            traffic_split: Percentage for model B (0.0-1.0)

        Returns:
            True if successful
        """
        model_a = self.get_model(model_a_id)
        model_b = self.get_model(model_b_id)

        if not model_a or not model_b:
            logger.error("[MODEL_REGISTRY] One or both models not found for A/B test")
            return False

        if model_a.model_type != model_b.model_type:
            logger.error("[MODEL_REGISTRY] Models must be same type for A/B test")
            return False

        # Setup A/B test
        model_a.ab_test_group = 'A'
        model_a.ab_test_traffic_percent = (1.0 - traffic_split) * 100

        model_b.ab_test_group = 'B'
        model_b.ab_test_traffic_percent = traffic_split * 100

        self._save_registry()

        logger.info(
            f"[MODEL_REGISTRY] A/B test setup: "
            f"{model_a_id} ({model_a.ab_test_traffic_percent:.1f}%) vs "
            f"{model_b_id} ({model_b.ab_test_traffic_percent:.1f}%)"
        )

        return True

    def get_ab_test_models(self, model_type: str) -> Dict[str, ModelVersion]:
        """
        Get models in A/B test for a type

        Args:
            model_type: Type of model

        Returns:
            Dictionary with 'A' and 'B' models
        """
        models = self.get_models_by_type(model_type)

        ab_models = {
            'A': None,
            'B': None
        }

        for model in models:
            if model.ab_test_group in ['A', 'B']:
                ab_models[model.ab_test_group] = model

        return ab_models

    def compare_models(
        self,
        model_id_a: str,
        model_id_b: str
    ) -> Dict[str, Any]:
        """
        Compare two model versions

        Args:
            model_id_a: First model ID
            model_id_b: Second model ID

        Returns:
            Comparison results
        """
        model_a = self.get_model(model_id_a)
        model_b = self.get_model(model_id_b)

        if not model_a or not model_b:
            return {'error': 'One or both models not found'}

        comparison = {
            'model_a': {
                'model_id': model_a.model_id,
                'version': model_a.version,
                'status': model_a.status.value,
                'inference_count': model_a.inference_count,
                'avg_latency_ms': model_a.avg_latency_ms,
                'avg_confidence': model_a.avg_confidence,
                'accuracy': model_a.accuracy
            },
            'model_b': {
                'model_id': model_b.model_id,
                'version': model_b.version,
                'status': model_b.status.value,
                'inference_count': model_b.inference_count,
                'avg_latency_ms': model_b.avg_latency_ms,
                'avg_confidence': model_b.avg_confidence,
                'accuracy': model_b.accuracy
            },
            'comparison': {
                'latency_diff_ms': model_b.avg_latency_ms - model_a.avg_latency_ms,
                'confidence_diff': model_b.avg_confidence - model_a.avg_confidence,
                'accuracy_diff': model_b.accuracy - model_a.accuracy,
                'faster_model': model_a.model_id if model_a.avg_latency_ms < model_b.avg_latency_ms else model_b.model_id,
                'more_confident_model': model_a.model_id if model_a.avg_confidence > model_b.avg_confidence else model_b.model_id,
                'more_accurate_model': model_a.model_id if model_a.accuracy > model_b.accuracy else model_b.model_id
            }
        }

        return comparison

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        models_by_type = {}
        models_by_status = {}

        for model in self.models.values():
            # By type
            if model.model_type not in models_by_type:
                models_by_type[model.model_type] = 0
            models_by_type[model.model_type] += 1

            # By status
            status_key = model.status.value
            if status_key not in models_by_status:
                models_by_status[status_key] = 0
            models_by_status[status_key] += 1

        return {
            'total_models': len(self.models),
            'models_by_type': models_by_type,
            'models_by_status': models_by_status,
            'registry_path': str(self.registry_path),
            'models_dir': str(self.models_dir)
        }
