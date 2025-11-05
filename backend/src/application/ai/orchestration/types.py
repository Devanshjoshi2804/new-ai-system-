"""
Orchestration Types and Data Structures

Defines all data types used by the autonomous orchestration system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime


class OrchestrationPhase(str, Enum):
    """Phases of autonomous onboarding workflow"""
    INITIALIZATION = "initialization"
    DISCOVERY = "discovery"
    ML_ENHANCEMENT = "ml_enhancement"
    TESTING = "testing"
    LEARNING = "learning"
    COMPLETED = "completed"
    FAILED = "failed"


class OperationStatus(str, Enum):
    """Status of orchestration operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TestStatus(str, Enum):
    """Status of individual test execution"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    FIXED = "fixed"  # Failed but auto-fixed


@dataclass
class EndpointInfo:
    """Information about a discovered API endpoint"""
    id: str
    url: str
    method: str
    category: Optional[str] = None
    description: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    schema: Optional[Dict[str, Any]] = None
    dependencies: List[str] = field(default_factory=list)  # IDs of endpoints this depends on
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Result of endpoint test execution"""
    endpoint_id: str
    status: TestStatus
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    retry_count: int = 0
    fixed: bool = False  # Whether error was auto-fixed
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhaseProgress:
    """Progress tracking for a workflow phase"""
    phase: OrchestrationPhase
    status: OperationStatus
    progress_percentage: float = 0.0
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationResult:
    """Complete result of autonomous orchestration"""
    operation_id: str
    status: OperationStatus
    current_phase: OrchestrationPhase
    phases: List[PhaseProgress] = field(default_factory=list)

    # Discovery results
    discovered_endpoints: List[EndpointInfo] = field(default_factory=list)

    # ML enhancement results
    classified_endpoints: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    generated_payloads: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Testing results
    test_results: List[TestResult] = field(default_factory=list)

    # Learning results
    patterns_learned: int = 0
    models_updated: bool = False

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_duration_seconds: float = 0.0

    # Metrics
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'operation_id': self.operation_id,
            'status': self.status.value,
            'current_phase': self.current_phase.value,
            'phases': [
                {
                    'phase': p.phase.value,
                    'status': p.status.value,
                    'progress_percentage': p.progress_percentage,
                    'message': p.message,
                    'started_at': p.started_at.isoformat() if p.started_at else None,
                    'completed_at': p.completed_at.isoformat() if p.completed_at else None,
                    'error': p.error
                }
                for p in self.phases
            ],
            'discovered_endpoints': len(self.discovered_endpoints),
            'test_results': len(self.test_results),
            'tests_passed': sum(1 for t in self.test_results if t.status == TestStatus.PASSED),
            'tests_failed': sum(1 for t in self.test_results if t.status == TestStatus.FAILED),
            'tests_fixed': sum(1 for t in self.test_results if t.fixed),
            'patterns_learned': self.patterns_learned,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_duration_seconds': self.total_duration_seconds,
            'metrics': self.metrics
        }


@dataclass
class AuthConfiguration:
    """Authentication configuration for API testing"""
    auth_type: str  # 'none', 'bearer', 'api_key', 'basic', 'oauth2'
    credentials: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = dict(self.headers)

        if self.auth_type == 'bearer':
            token = self.credentials.get('token', '')
            headers['Authorization'] = f"Bearer {token}"

        elif self.auth_type == 'api_key':
            key_name = self.credentials.get('key_name', 'X-API-Key')
            key_value = self.credentials.get('key_value', '')
            headers[key_name] = key_value

        elif self.auth_type == 'basic':
            import base64
            username = self.credentials.get('username', '')
            password = self.credentials.get('password', '')
            credentials = f"{username}:{password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers['Authorization'] = f"Basic {encoded}"

        return headers


@dataclass
class DependencyGraph:
    """Graph of endpoint dependencies for execution ordering"""
    nodes: Dict[str, EndpointInfo] = field(default_factory=dict)
    edges: Dict[str, List[str]] = field(default_factory=dict)  # endpoint_id -> list of dependency ids

    def add_node(self, endpoint: EndpointInfo):
        """Add endpoint to graph"""
        self.nodes[endpoint.id] = endpoint
        if endpoint.id not in self.edges:
            self.edges[endpoint.id] = []

    def add_dependency(self, endpoint_id: str, depends_on: str):
        """Add dependency relationship"""
        if endpoint_id not in self.edges:
            self.edges[endpoint_id] = []
        if depends_on not in self.edges[endpoint_id]:
            self.edges[endpoint_id].append(depends_on)

    def get_execution_order(self) -> List[str]:
        """
        Get topologically sorted execution order

        Returns:
            List of endpoint IDs in execution order

        Raises:
            ValueError: If circular dependency detected
        """
        # Kahn's algorithm for topological sort
        in_degree = {node: 0 for node in self.nodes}

        # Calculate in-degrees
        for node in self.edges:
            for dependency in self.edges[node]:
                if dependency in in_degree:
                    in_degree[node] += 1

        # Queue of nodes with no dependencies
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # Sort by priority (endpoints with auth/setup typically first)
            queue.sort(key=lambda x: (
                0 if self.nodes[x].category == 'authentication' else 1,
                x
            ))

            node = queue.pop(0)
            result.append(node)

            # Reduce in-degree for dependent nodes
            for other_node in self.nodes:
                if node in self.edges.get(other_node, []):
                    in_degree[other_node] -= 1
                    if in_degree[other_node] == 0:
                        queue.append(other_node)

        # Check for cycles
        if len(result) != len(self.nodes):
            raise ValueError("Circular dependency detected in endpoint graph")

        return result

    def get_parallel_batches(self) -> List[List[str]]:
        """
        Get batches of endpoints that can be executed in parallel

        Returns:
            List of batches, where each batch contains endpoint IDs that can run in parallel
        """
        in_degree = {node: 0 for node in self.nodes}

        for node in self.edges:
            for dependency in self.edges[node]:
                if dependency in in_degree:
                    in_degree[node] += 1

        batches = []
        remaining = set(self.nodes.keys())

        while remaining:
            # Get all nodes with no dependencies in remaining set
            batch = [
                node for node in remaining
                if all(dep not in remaining for dep in self.edges.get(node, []))
            ]

            if not batch:
                raise ValueError("Circular dependency detected")

            batches.append(batch)
            remaining -= set(batch)

        return batches


@dataclass
class ExecutionContext:
    """Context for test execution"""
    auth_config: AuthConfiguration
    base_url: str = ""
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    enable_auto_fix: bool = True
    rate_limit_per_second: int = 10
    store_results: bool = True

    # Runtime state
    executed_endpoints: Dict[str, TestResult] = field(default_factory=dict)
    shared_state: Dict[str, Any] = field(default_factory=dict)  # For sharing data between endpoints
