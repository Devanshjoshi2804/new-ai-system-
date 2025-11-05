"""
ML Models Module

Custom machine learning models for autonomous API discovery and integration.
These models learn from production data to continuously improve accuracy.

Models:
- EndpointClassifier: Classify endpoints into categories (CRUD, auth, etc.)
- PayloadGeneratorModel: Generate valid request payloads
- ErrorFixerModel: Fix requests based on error responses
- WorkflowPredictor: Predict optimal workflow sequences
- ModelServer: Optimized model serving with ONNX
- TrainingPipeline: Automated training and deployment
- DataCollector: Collect and prepare training data
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .data_collector import DataCollector
    from .endpoint_classifier import EndpointClassifier
    from .payload_generator import PayloadGeneratorModel
    from .error_fixer import ErrorFixerModel
    from .workflow_predictor import WorkflowPredictor
    from .model_server import ModelServer
    from .training_pipeline import TrainingPipeline

__all__ = [
    'DataCollector',
    'EndpointClassifier',
    'PayloadGeneratorModel',
    'ErrorFixerModel',
    'WorkflowPredictor',
    'ModelServer',
    'TrainingPipeline',
]
