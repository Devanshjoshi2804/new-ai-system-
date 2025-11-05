"""
Dependency Analyzer - Detects API dependencies and builds execution order
"""
import logging
import re
from typing import List, Dict, Any, Set, Optional
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class DependencyAnalyzer:
    """Analyzes API endpoints to detect dependencies and determine execution order"""
    
    # Common parameter patterns that indicate dependencies
    ID_PATTERNS = [
        r'.*[Ii]d$',  # ends with 'id' or 'Id'
        r'.*[Nn]umber$',  # ends with 'number' or 'Number'
        r'.*[Cc]ode$',  # ends with 'code' or 'Code'
        r'.*[Tt]oken$',  # ends with 'token' or 'Token'
    ]
    
    # Authentication/Login patterns (should come first)
    AUTH_PATTERNS = [
        'login', 'auth', 'signin', 'signup', 'register', 'token'
    ]
    
    # Logistics-specific workflow patterns
    LOGISTICS_WORKFLOW_PATTERNS = {
        # Priority 1: Address validation must come first
        'address_validation': {
            'patterns': ['address/validate', 'validate-address', 'address-check', 'verify-address'],
            'priority': 1,
            'required_before': ['rate', 'booking', 'shipment', 'quote'],
            'returns': ['validated_address', 'address_valid']
        },
        
        # Priority 2: Service availability check
        'service_availability': {
            'patterns': ['service/check', 'serviceability', 'coverage', 'availability'],
            'priority': 2,
            'required_before': ['rate', 'booking'],
            'depends_on': ['address_validation']
        },
        
        # Priority 3: Rate calculation
        'rate_calculation': {
            'patterns': ['rate', 'price', 'quote', 'calculate', 'estimate'],
            'priority': 3,
            'depends_on': ['address_validation', 'service_availability'],
            'required_before': ['booking', 'shipment'],
            'returns': ['rate_id', 'quote_id', 'price']
        },
        
        # Priority 4: Booking/Shipment creation
        'booking': {
            'patterns': ['booking', 'shipment', 'order/create', 'create-shipment'],
            'priority': 4,
            'depends_on': ['rate_calculation', 'address_validation'],
            'returns': ['awb_number', 'tracking_number', 'shipment_id', 'booking_id']
        },
        
        # Priority 5: Label generation
        'label_generation': {
            'patterns': ['label', 'print', 'document', 'shipping-label'],
            'priority': 5,
            'depends_on': ['booking'],
            'requires': ['awb_number', 'shipment_id']
        },
        
        # Priority 6: Pickup scheduling
        'pickup': {
            'patterns': ['pickup', 'schedule', 'collection', 'arrange-pickup'],
            'priority': 6,
            'depends_on': ['booking'],
            'requires': ['shipment_id', 'booking_id']
        },
        
        # Priority 7: Manifest generation (end of day)
        'manifest': {
            'patterns': ['manifest', 'close', 'end-of-day'],
            'priority': 7,
            'depends_on': ['booking', 'pickup']
        },
        
        # Independent: Tracking (can be tested anytime after booking)
        'tracking': {
            'patterns': ['track', 'status', 'trace', 'tracking'],
            'priority': 10,  # Lower priority = can run later
            'depends_on': ['booking'],
            'requires': ['awb_number', 'tracking_number']
        },
        
        # Independent: Cancel (can be tested after booking)
        'cancellation': {
            'patterns': ['cancel', 'void', 'delete-shipment'],
            'priority': 11,
            'depends_on': ['booking'],
            'requires': ['shipment_id', 'booking_id']
        }
    }
    
    def __init__(self, ai_provider=None, gemini_provider=None):
        """
        Initialize dependency analyzer
        
        Args:
            ai_provider: Optional AI provider (Groq/Gemini/Mistral) for AI-enhanced analysis
            gemini_provider: Deprecated, use ai_provider instead
        """
        self.ai_provider = ai_provider or gemini_provider
        # Keep backward compatibility
        self.gemini_provider = self.ai_provider
    
    def analyze(self, endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze endpoints and return dependency information
        
        Args:
            endpoints: List of API endpoint specifications
            
        Returns:
            Dictionary with dependency_graph and execution_order
        """
        logger.info(f"Analyzing dependencies for {len(endpoints)} endpoints")
        
        # Step 1: Detect logistics workflow patterns
        logistics_deps = self._detect_logistics_patterns(endpoints)
        
        # Step 2: Rule-based dependency detection
        rule_based_deps = self._detect_rule_based_dependencies(endpoints)
        
        # Step 3: Merge logistics patterns with rule-based deps
        merged_deps = self._merge_dependencies(logistics_deps, rule_based_deps)
        
        # Step 4: AI-enhanced dependency detection (if available)
        if self.gemini_provider:
            try:
                # BUG #1 FIXED: asyncio.run() in async context causes RuntimeError
                # Temporarily disabled until we refactor this method to be async
                # TODO: Make analyze() async and use await instead of asyncio.run()
                logger.warning("⚠️  AI dependency analysis temporarily disabled (asyncio.run bug - will crash)")
                logger.info("📊 Using logistics + rule-based dependency detection")
                dependency_graph = merged_deps
            except Exception as e:
                logger.warning(f"AI dependency analysis failed, using merged deps: {e}")
                dependency_graph = merged_deps
        else:
            dependency_graph = merged_deps
        
        # Step 5: Topological sort to get execution order
        execution_order = self._topological_sort(dependency_graph, endpoints)
        
        logger.info(f"Dependency analysis complete. Execution order: {len(execution_order)} endpoints")
        
        return {
            "dependency_graph": dependency_graph,
            "execution_order": execution_order
        }
    
    def _detect_rule_based_dependencies(self, endpoints: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Detect dependencies using rule-based analysis
        
        Rules:
        1. Auth/login endpoints come first (no dependencies)
        2. Endpoints with parameters matching ID patterns depend on resource creators
        3. Semantic naming patterns (e.g., 'create' before 'update')
        """
        dependency_graph = {}
        endpoint_map = {ep.get('path', ''): ep for ep in endpoints}
        
        for endpoint in endpoints:
            path = endpoint.get('path', '')
            dependencies = set()
            
            # Skip auth endpoints (they have no dependencies)
            if self._is_auth_endpoint(endpoint):
                dependency_graph[path] = []
                continue
            
            # Check parameters for dependency indicators
            parameters = endpoint.get('parameters', [])
            for param in parameters:
                param_name = param.get('name', '')
                
                # Check if parameter looks like an ID/reference
                if self._is_dependency_parameter(param_name):
                    # Find which endpoint creates this resource
                    creator_endpoint = self._find_creator_endpoint(param_name, endpoints)
                    if creator_endpoint and creator_endpoint != path:
                        dependencies.add(creator_endpoint)
            
            # Check for common patterns in path/summary
            summary = endpoint.get('summary', '').lower()
            method = endpoint.get('method', '').upper()
            
            # Update/Delete operations likely depend on Create operations
            if method in ['PUT', 'PATCH', 'DELETE'] or any(word in summary for word in ['update', 'delete', 'cancel']):
                # Find corresponding create endpoint
                resource_name = self._extract_resource_name(path)
                if resource_name:
                    creator = self._find_create_endpoint(resource_name, endpoints)
                    if creator and creator != path:
                        dependencies.add(creator)
            
            dependency_graph[path] = list(dependencies)
        
        return dependency_graph
    
    def _is_auth_endpoint(self, endpoint: Dict[str, Any]) -> bool:
        """Check if endpoint is an authentication endpoint"""
        path = endpoint.get('path', '').lower()
        summary = endpoint.get('summary', '').lower()
        
        for pattern in self.AUTH_PATTERNS:
            if pattern in path or pattern in summary:
                return True
        return False
    
    def _is_dependency_parameter(self, param_name: str) -> bool:
        """Check if parameter name indicates a dependency"""
        for pattern in self.ID_PATTERNS:
            if re.match(pattern, param_name):
                return True
        return False
    
    def _find_creator_endpoint(self, param_name: str, endpoints: List[Dict[str, Any]]) -> Optional[str]:
        """
        Find the endpoint that creates/returns the resource referenced by param_name
        
        For example, if param_name is 'addressId', find the '/address/create' endpoint
        """
        # Extract resource name from parameter
        # addressId -> address
        # awbNumber -> awb
        # orderId -> order
        resource_name = re.sub(r'(Id|Number|Code|Token)$', '', param_name, flags=re.IGNORECASE).lower()
        
        # Look for endpoints that create this resource
        for endpoint in endpoints:
            path = endpoint.get('path', '').lower()
            method = endpoint.get('method', '').upper()
            summary = endpoint.get('summary', '').lower()
            
            # Check if this endpoint creates the resource
            if method == 'POST' and (resource_name in path or resource_name in summary):
                # Additional checks for 'create' keywords
                if 'create' in summary or 'add' in summary or 'register' in summary:
                    return endpoint.get('path', '')
        
        return None
    
    def _extract_resource_name(self, path: str) -> Optional[str]:
        """Extract resource name from API path"""
        # /api/orders/123 -> orders
        # /cargo-api/address/create -> address
        parts = path.strip('/').split('/')
        for part in parts:
            # Skip common prefixes
            if part in ['api', 'v1', 'v2', 'cargo-api', 'wallet-api']:
                continue
            # Skip path parameters
            if '{' in part or part.isdigit():
                continue
            return part.lower()
        return None
    
    def _find_create_endpoint(self, resource_name: str, endpoints: List[Dict[str, Any]]) -> Optional[str]:
        """Find the CREATE endpoint for a given resource"""
        for endpoint in endpoints:
            path = endpoint.get('path', '').lower()
            method = endpoint.get('method', '').upper()
            summary = endpoint.get('summary', '').lower()
            
            if method == 'POST' and resource_name in path:
                if 'create' in summary or 'add' in summary:
                    return endpoint.get('path', '')
        
        return None
    
    def _merge_dependency_graphs(
        self,
        rule_based: Dict[str, List[str]],
        ai_based: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Merge rule-based and AI-based dependency graphs
        Takes union of dependencies from both sources
        """
        merged = defaultdict(set)
        
        # Add rule-based dependencies
        for endpoint, deps in rule_based.items():
            merged[endpoint].update(deps)
        
        # Add AI-based dependencies
        for endpoint, deps in ai_based.items():
            merged[endpoint].update(deps)
        
        # Convert sets back to lists
        return {endpoint: list(deps) for endpoint, deps in merged.items()}
    
    def _detect_logistics_patterns(self, endpoints: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Detect logistics-specific workflow dependencies
        
        Returns:
            Dictionary mapping endpoint paths to their dependencies
        """
        logger.info("🚚 Detecting logistics workflow patterns...")
        logistics_deps = {}
        endpoint_classifications = {}
        
        # Step 1: Classify each endpoint
        for endpoint in endpoints:
            path = endpoint.get('path', '').lower()
            summary = endpoint.get('summary', '').lower()
            combined = f"{path} {summary}"
            
            # Match against logistics patterns
            for workflow_type, config in self.LOGISTICS_WORKFLOW_PATTERNS.items():
                for pattern in config['patterns']:
                    if pattern in combined:
                        endpoint_classifications[path] = {
                            'type': workflow_type,
                            'priority': config['priority'],
                            'config': config
                        }
                        logger.info(f"  ✅ {path} → {workflow_type} (priority {config['priority']})")
                        break
                if path in endpoint_classifications:
                    break
        
        # Step 2: Build dependencies based on classifications
        for endpoint in endpoints:
            path = endpoint.get('path', '')
            
            if path not in endpoint_classifications:
                # Not a logistics endpoint, no special dependencies
                logistics_deps[path] = []
                continue
            
            classification = endpoint_classifications[path]
            config = classification['config']
            dependencies = set()
            
            # Add explicit dependencies from config
            if 'depends_on' in config:
                for dep_type in config['depends_on']:
                    # Find endpoints of this type
                    for other_path, other_class in endpoint_classifications.items():
                        if other_class['type'] == dep_type and other_path != path:
                            dependencies.add(other_path)
            
            logistics_deps[path] = list(dependencies)
        
        logger.info(f"✅ Detected {len(endpoint_classifications)} logistics endpoints")
        return logistics_deps
    
    def _merge_dependencies(
        self,
        logistics_deps: Dict[str, List[str]],
        rule_based_deps: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Merge logistics patterns with rule-based dependencies
        Logistics patterns take precedence
        """
        merged = {}
        all_paths = set(logistics_deps.keys()) | set(rule_based_deps.keys())
        
        for path in all_paths:
            log_deps = set(logistics_deps.get(path, []))
            rule_deps = set(rule_based_deps.get(path, []))
            
            # Union of both (logistics patterns are already authoritative)
            merged[path] = list(log_deps | rule_deps)
        
        return merged
    
    def _topological_sort(
        self,
        dependency_graph: Dict[str, List[str]],
        endpoints: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Perform topological sort to determine execution order
        
        Uses Kahn's algorithm for topological sorting
        """
        # Build in-degree map
        in_degree = {endpoint: 0 for endpoint in dependency_graph.keys()}
        
        for endpoint, dependencies in dependency_graph.items():
            for dep in dependencies:
                if dep in in_degree:
                    in_degree[endpoint] = in_degree.get(endpoint, 0) + 1
        
        # Find nodes with no dependencies (in-degree = 0)
        queue = deque([endpoint for endpoint, degree in in_degree.items() if degree == 0])
        execution_order = []
        
        # Process queue
        while queue:
            # Sort queue to prioritize auth endpoints
            queue = deque(sorted(queue, key=lambda x: (not self._is_auth_endpoint_path(x, endpoints), x)))
            
            current = queue.popleft()
            execution_order.append(current)
            
            # Reduce in-degree for dependent endpoints
            for endpoint, dependencies in dependency_graph.items():
                if current in dependencies:
                    in_degree[endpoint] -= 1
                    if in_degree[endpoint] == 0:
                        queue.append(endpoint)
        
        # Check for cycles
        if len(execution_order) != len(dependency_graph):
            logger.warning("Circular dependencies detected, some endpoints may not execute in optimal order")
            # Add remaining endpoints to the end
            remaining = set(dependency_graph.keys()) - set(execution_order)
            execution_order.extend(sorted(remaining))
        
        return execution_order
    
    def _is_auth_endpoint_path(self, path: str, endpoints: List[Dict[str, Any]]) -> bool:
        """Check if path is an auth endpoint"""
        for endpoint in endpoints:
            if endpoint.get('path') == path:
                return self._is_auth_endpoint(endpoint)
        return False

