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

__all__ = [
    # Enums
    'OrchestrationPhase',
    'OperationStatus',
    'TestStatus',
    # Data classes
    'OrchestrationResult',
    'PhaseProgress',
    'EndpointInfo',
    'TestResult',
    'AuthConfiguration',
    'DependencyGraph',
    'ExecutionContext',
    # Main components
    'AutonomousOrchestrator',
    'ExecutionEngine',
    'CircuitBreaker',
    'RateLimiter'
]
