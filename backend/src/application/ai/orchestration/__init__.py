"""
Orchestration Module

Complete autonomous API integration orchestration system.

This module coordinates all phases of autonomous API onboarding:
1. Discovery - Find API endpoints
2. ML Enhancement - Classify and understand endpoints
3. Testing - Execute tests with auto-fixing
4. Learning - Store results for improvement

Main Components:
- AutonomousOrchestrator: Coordinates full workflow
- ExecutionEngine: Intelligent test execution
- LearningLoop: Continuous improvement and pattern storage
- PerformanceMonitor: Real-time metrics and alerting
- ModelRegistry: ML model version management
- Types: Data structures and enums
"""

from .types import (
    OrchestrationPhase,
    OperationStatus,
    TestStatus,
    OrchestrationResult,
    PhaseProgress,
    EndpointInfo,
    TestResult,
    AuthConfiguration,
    DependencyGraph,
    ExecutionContext
)

from .autonomous_orchestrator import AutonomousOrchestrator

from .execution_engine import (
    ExecutionEngine,
    CircuitBreaker,
    RateLimiter
)

from .learning_loop import LearningLoop

from .performance_monitor import (
    PerformanceMonitor,
    PerformanceSnapshot,
    Alert
)

from .model_registry import (
    ModelRegistry,
    ModelVersion,
    ModelStatus
)

__all__ = [
    # Enums
    'OrchestrationPhase',
    'OperationStatus',
    'TestStatus',
    'ModelStatus',
    # Data classes
    'OrchestrationResult',
    'PhaseProgress',
    'EndpointInfo',
    'TestResult',
    'AuthConfiguration',
    'DependencyGraph',
    'ExecutionContext',
    'PerformanceSnapshot',
    'Alert',
    'ModelVersion',
    # Main components
    'AutonomousOrchestrator',
    'ExecutionEngine',
    'CircuitBreaker',
    'RateLimiter',
    'LearningLoop',
    'PerformanceMonitor',
    'ModelRegistry'
]
