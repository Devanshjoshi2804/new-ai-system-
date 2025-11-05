"""
Relationship Analyzer - Detect dependencies between API endpoints
Builds dependency graphs and determines execution order
"""
import logging
import re
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict
import json

import networkx as nx
import httpx

logger = logging.getLogger(__name__)


class DependencyGraph:
    """Wrapper for NetworkX graph with endpoint dependencies"""

    def __init__(self):
        self.graph = nx.DiGraph()  # Directed graph
        self.execution_order: List[str] = []
        self.data_flows: List[Dict[str, Any]] = []

    def add_dependency(self, from_endpoint: str, to_endpoint: str, reason: str):
        """Add a dependency edge"""
        self.graph.add_edge(from_endpoint, to_endpoint, reason=reason)

    def get_execution_order(self) -> List[str]:
        """Get topologically sorted execution order"""
        try:
            # Topological sort gives us the order to execute
            self.execution_order = list(nx.topological_sort(self.graph))
            return self.execution_order
        except nx.NetworkXError as e:
            logger.error(f"[ERROR] Circular dependency detected: {e}")
            # Return best-effort order
            return list(self.graph.nodes())

    def has_circular_dependencies(self) -> bool:
        """Check for circular dependencies"""
        try:
            list(nx.topological_sort(self.graph))
            return False
        except nx.NetworkXError:
            return True

    def get_dependencies(self, endpoint: str) -> List[str]:
        """Get all dependencies for an endpoint"""
        return list(self.graph.predecessors(endpoint))

    def get_dependents(self, endpoint: str) -> List[str]:
        """Get all endpoints that depend on this one"""
        return list(self.graph.successors(endpoint))

    def to_dict(self) -> Dict[str, Any]:
        """Export graph as dictionary for visualization"""
        return {
            'nodes': [
                {'id': node, 'label': node}
                for node in self.graph.nodes()
            ],
            'edges': [
                {
                    'from': edge[0],
                    'to': edge[1],
                    'reason': self.graph.edges[edge].get('reason', 'unknown')
                }
                for edge in self.graph.edges()
            ],
            'execution_order': self.execution_order
        }


class RelationshipAnalyzer:
    """
    Intelligent relationship analyzer for API endpoints

    Strategies:
    1. Analyze failure patterns (400/422 errors)
    2. Detect data flow (response field → request parameter)
    3. Detect authentication dependencies
    4. Detect resource dependencies (create before read)
    5. Learn from successful execution sequences
    6. Build dependency graph
    7. Generate optimal execution order
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize Relationship Analyzer

        Args:
            timeout: Request timeout
        """
        self.timeout = httpx.Timeout(timeout)
        self._session: Optional[httpx.AsyncClient] = None
        self.dependency_graph = DependencyGraph()

    async def __aenter__(self):
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _get_session(self) -> httpx.AsyncClient:
        if self._session is None or self._session.is_closed:
            self._session = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            )
        return self._session

    async def close(self):
        if self._session and not self._session.is_closed:
            await self._session.aclose()

    async def analyze(
        self,
        base_url: str,
        endpoints: List[Dict[str, Any]],
        auth_token: Optional[str] = None
    ) -> DependencyGraph:
        """
        Analyze relationships between endpoints

        Args:
            base_url: API base URL
            endpoints: List of discovered endpoints
            auth_token: Optional authentication token

        Returns:
            DependencyGraph with all detected dependencies
        """
        try:
            logger.info(f"[START] Relationship analysis for {len(endpoints)} endpoints")

            # Strategy 1: Detect auth dependencies
            await self._detect_auth_dependencies(endpoints, auth_token)

            # Strategy 2: Detect resource hierarchy (REST pattern)
            self._detect_resource_hierarchy(endpoints)

            # Strategy 3: Try executing endpoints to detect failures
            await self._detect_failure_dependencies(base_url, endpoints, auth_token)

            # Strategy 4: Analyze parameter names for data flow
            self._detect_data_flow_dependencies(endpoints)

            # Strategy 5: Get execution order
            execution_order = self.dependency_graph.get_execution_order()

            logger.info(f"[OK] Relationship analysis complete")
            logger.info(f"[INFO] Detected {len(self.dependency_graph.graph.edges())} dependencies")
            logger.info(f"[INFO] Execution order: {len(execution_order)} steps")

            # Check for circular dependencies
            if self.dependency_graph.has_circular_dependencies():
                logger.warning("[WARN] Circular dependencies detected!")

            return self.dependency_graph

        except Exception as e:
            logger.error(f"[ERROR] Relationship analysis failed: {e}", exc_info=True)
            return self.dependency_graph

    async def _detect_auth_dependencies(
        self,
        endpoints: List[Dict[str, Any]],
        auth_token: Optional[str]
    ):
        """Detect endpoints that require authentication"""
        if not auth_token:
            return

        # Find login/auth endpoints
        auth_endpoints = []
        for endpoint in endpoints:
            path = endpoint.get('path', '').lower()
            if any(keyword in path for keyword in ['login', 'auth', 'token', 'signin']):
                auth_endpoints.append(f"{endpoint['method']} {endpoint['path']}")

        # All auth-required endpoints depend on login
        for endpoint in endpoints:
            if endpoint.get('auth_required'):
                endpoint_key = f"{endpoint['method']} {endpoint['path']}"
                for auth_endpoint in auth_endpoints:
                    if auth_endpoint != endpoint_key:
                        self.dependency_graph.add_dependency(
                            auth_endpoint,
                            endpoint_key,
                            "authentication_required"
                        )

    def _detect_resource_hierarchy(self, endpoints: List[Dict[str, Any]]):
        """
        Detect RESTful resource hierarchy

        Pattern:
        POST /resource -> creates resource
        GET /resource/{id} -> needs created resource
        PUT /resource/{id} -> needs existing resource
        DELETE /resource/{id} -> needs existing resource
        """

        # Group endpoints by resource
        resources = defaultdict(list)

        for endpoint in endpoints:
            path = endpoint.get('path', '')
            method = endpoint.get('method', '')

            # Extract resource name (first path segment)
            match = re.match(r'^/?([^/]+)', path)
            if match:
                resource_name = match.group(1)
                resources[resource_name].append({
                    'endpoint': f"{method} {path}",
                    'method': method,
                    'path': path,
                    'has_id': '{id}' in path or '{' in path
                })

        # Analyze each resource group
        for resource_name, resource_endpoints in resources.items():
            # Find POST endpoint (creation)
            create_endpoints = [e for e in resource_endpoints if e['method'] == 'POST' and not e['has_id']]

            # Find endpoints that need existing resource
            need_resource = [e for e in resource_endpoints if e['has_id']]

            # All endpoints that need ID depend on creation
            for create_ep in create_endpoints:
                for need_ep in need_resource:
                    if create_ep['endpoint'] != need_ep['endpoint']:
                        self.dependency_graph.add_dependency(
                            create_ep['endpoint'],
                            need_ep['endpoint'],
                            f"resource_must_exist"
                        )
                        logger.debug(f"[DEPENDENCY] {create_ep['endpoint']} -> {need_ep['endpoint']} (resource)")

    async def _detect_failure_dependencies(
        self,
        base_url: str,
        endpoints: List[Dict[str, Any]],
        auth_token: Optional[str]
    ):
        """
        Try executing endpoints to detect dependencies from failure messages

        Logic:
        - If endpoint fails with "resource not found" or "invalid ID"
        - It likely depends on another endpoint that creates that resource
        """
        session = await self._get_session()
        headers = {}
        if auth_token:
            headers['Authorization'] = f"Bearer {auth_token}"

        for endpoint in endpoints[:10]:  # Limit to first 10 to avoid too many requests
            try:
                method = endpoint['method'].upper()
                path = endpoint['path']
                url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

                # Replace path parameters with test values
                url = re.sub(r'\{[^}]+\}', 'test-id-123', url)

                # Try making request
                if method == 'GET':
                    response = await session.get(url, headers=headers)
                elif method == 'POST':
                    response = await session.post(url, json={}, headers=headers)
                elif method == 'PUT':
                    response = await session.put(url, json={}, headers=headers)
                elif method == 'PATCH':
                    response = await session.patch(url, json={}, headers=headers)
                elif method == 'DELETE':
                    response = await session.delete(url, headers=headers)
                else:
                    continue

                # Analyze error response
                if response.status_code in [404, 400, 422]:
                    try:
                        error_data = response.json()
                        error_message = json.dumps(error_data).lower()

                        # Check for dependency hints
                        if any(hint in error_message for hint in [
                            'not found',
                            'does not exist',
                            'invalid id',
                            'resource not found',
                            'must exist'
                        ]):
                            # This endpoint likely depends on resource creation
                            # Find potential create endpoints
                            resource_from_path = self._extract_resource_name(path)
                            if resource_from_path:
                                create_endpoint = self._find_create_endpoint(endpoints, resource_from_path)
                                if create_endpoint:
                                    endpoint_key = f"{method} {path}"
                                    self.dependency_graph.add_dependency(
                                        create_endpoint,
                                        endpoint_key,
                                        "prerequisite_detected_from_error"
                                    )
                                    logger.debug(f"[DEPENDENCY] {create_endpoint} -> {endpoint_key} (from error)")

                    except:
                        pass

            except Exception as e:
                logger.debug(f"[DEBUG] Error testing endpoint: {e}")
                continue

    def _extract_resource_name(self, path: str) -> Optional[str]:
        """Extract resource name from path"""
        # Remove parameters
        clean_path = re.sub(r'\{[^}]+\}', '', path)
        parts = [p for p in clean_path.split('/') if p]

        if parts:
            return parts[0]

        return None

    def _find_create_endpoint(self, endpoints: List[Dict[str, Any]], resource_name: str) -> Optional[str]:
        """Find POST endpoint for resource creation"""
        for endpoint in endpoints:
            if endpoint['method'].upper() == 'POST':
                path = endpoint.get('path', '')
                if resource_name in path and '{' not in path:
                    return f"POST {path}"

        return None

    def _detect_data_flow_dependencies(self, endpoints: List[Dict[str, Any]]):
        """
        Detect data flow between endpoints by analyzing parameter names

        Example:
        POST /users returns {"userId": "123"}
        POST /orders needs {"userId": ...}
        -> /users must be called before /orders
        """

        # Build map of what each endpoint returns and needs
        endpoint_outputs = {}  # endpoint -> set of field names it returns
        endpoint_inputs = {}   # endpoint -> set of field names it needs

        for endpoint in endpoints:
            endpoint_key = f"{endpoint['method']} {endpoint['path']}"

            # Get parameter names (inputs)
            params = endpoint.get('parameters', [])
            input_fields = set()
            for param in params:
                if isinstance(param, dict):
                    input_fields.add(param.get('name', ''))

            endpoint_inputs[endpoint_key] = input_fields

            # Outputs would need schema inference or actual API calls
            # For now, use common patterns
            path = endpoint.get('path', '')
            if endpoint['method'].upper() == 'POST':
                # POST endpoints likely return IDs
                resource = self._extract_resource_name(path)
                if resource:
                    # Likely returns: {resource}Id, {resource}_id, id
                    endpoint_outputs[endpoint_key] = {
                        f"{resource}Id",
                        f"{resource}_id",
                        "id"
                    }

        # Detect dependencies
        for output_endpoint, output_fields in endpoint_outputs.items():
            for input_endpoint, input_fields in endpoint_inputs.items():
                if output_endpoint == input_endpoint:
                    continue

                # Check if any output field matches any input field
                common_fields = output_fields.intersection(input_fields)
                if common_fields:
                    self.dependency_graph.add_dependency(
                        output_endpoint,
                        input_endpoint,
                        f"data_flow_{list(common_fields)[0]}"
                    )

                    # Store data flow information
                    self.dependency_graph.data_flows.append({
                        'from': output_endpoint,
                        'to': input_endpoint,
                        'field': list(common_fields)[0]
                    })

                    logger.debug(f"[DATA FLOW] {output_endpoint} -> {input_endpoint} ({list(common_fields)[0]})")

    def generate_workflow(self, workflow_type: str = "full") -> Dict[str, Any]:
        """
        Generate workflow definition from dependency graph

        Args:
            workflow_type: Type of workflow (full, create, read, update, delete)

        Returns:
            Workflow definition with steps and data flow
        """
        try:
            execution_order = self.dependency_graph.get_execution_order()

            workflow = {
                'type': workflow_type,
                'steps': [],
                'data_flows': self.dependency_graph.data_flows
            }

            for i, endpoint in enumerate(execution_order):
                # Parse endpoint
                parts = endpoint.split(' ', 1)
                if len(parts) != 2:
                    continue

                method, path = parts

                # Get dependencies
                dependencies = self.dependency_graph.get_dependencies(endpoint)

                workflow['steps'].append({
                    'step': i + 1,
                    'endpoint': path,
                    'method': method,
                    'depends_on': [d.split(' ', 1)[1] if ' ' in d else d for d in dependencies],
                    'description': f"{method} {path}"
                })

            return workflow

        except Exception as e:
            logger.error(f"[ERROR] Failed to generate workflow: {e}")
            return {'type': workflow_type, 'steps': [], 'data_flows': []}
