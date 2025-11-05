"""
Comprehensive API Analyzer using LangGraph
Extracts ALL information from API documentation autonomously
"""
import json
import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from src.infrastructure.ai.providers.gemini_provider import GeminiProvider
from src.infrastructure.ai.providers.mistral_provider import MistralProvider
from src.application.ai.understanding.pattern_extractor import PatternExtractor
from src.application.ai.understanding.validation_rule_detector import ValidationRuleDetector

logger = logging.getLogger(__name__)


class APIAnalysisState(TypedDict):
    """State for API analysis workflow"""
    raw_text: str
    endpoints: List[Dict[str, Any]]
    auth_config: Dict[str, Any]
    schemas: Dict[str, Any]
    dependencies: Dict[str, List[str]]
    business_rules: List[str]
    test_scenarios: List[Dict[str, Any]]
    workflow_analysis: Dict[str, Any]
    # NEW: Universal pattern extraction
    workflow_patterns: List[Dict[str, Any]]
    data_dependencies: List[Dict[str, Any]]
    validation_rules: List[Dict[str, Any]]
    dependency_graph: Dict[str, Any]
    analysis_complete: bool
    error: Optional[str]


def parse_json_response(response: str) -> Any:
    """Parse JSON from AI response, handling markdown code blocks"""
    try:
        text = response.strip()
        
        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        return json.loads(text)
    except Exception as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.debug(f"Response text: {response[:500]}")
        raise


async def extract_endpoints_node(state: APIAnalysisState) -> APIAnalysisState:
    """Extract all API endpoints using Gemini"""
    try:
        logger.info("[SEARCH] Extracting API endpoints...")
        
        prompt = f"""
Analyze this API documentation and extract ALL endpoints.

Documentation:
{state['raw_text'][:15000]}  # Limit for token constraints

For EACH endpoint, provide:
- HTTP method (GET/POST/PUT/PATCH/DELETE)
- Path (with path parameters in {{braces}})
- Summary/description
- Request body schema (if any)
- Response schema
- Query parameters
- Headers required
- Authentication required (yes/no)
- Rate limits (if mentioned)

Output as JSON array:
[
  {{
    "method": "POST",
    "path": "/api/bookings",
    "summary": "Create a new booking",
    "request_body": {{"type": "object", "properties": {{}}}},
    "response_schema": {{"type": "object", "properties": {{}}}},
    "query_params": [],
    "headers": ["Authorization"],
    "auth_required": true,
    "rate_limit": "100 requests per minute"
  }}
]

Return ONLY valid JSON array, no markdown, no explanations.
"""
        
        gemini = GeminiProvider()
        response = await gemini.generate_content(prompt, temperature=0.1)
        endpoints = parse_json_response(response)
        
        logger.info(f"[OK] Extracted {len(endpoints)} endpoints")
        
        return {**state, "endpoints": endpoints}
    
    except Exception as e:
        logger.error(f"[ERROR] Error extracting endpoints: {e}")
        return {**state, "endpoints": [], "error": str(e)}


async def extract_auth_config_node(state: APIAnalysisState) -> APIAnalysisState:
    """Extract authentication configuration"""
    try:
        logger.info("[INFO] Extracting authentication configuration...")
        
        prompt = f"""
Analyze authentication requirements from this documentation:

Documentation:
{state['raw_text'][:15000]}

Identify:
- Auth type (API Key, Bearer Token, OAuth2, Basic Auth, Custom)
- Where to provide credentials (header, query parameter, body)
- Header/parameter names
- Token format (e.g., "Bearer {{token}}", "{{token}}", "API-Key {{token}}")
- How to obtain credentials (which endpoint to call)
- Test credentials (if mentioned in documentation)
- Token expiration (if mentioned)

Output as JSON:
{{
  "type": "bearer",
  "location": "header",
  "header_name": "Authorization",
  "token_format": "Bearer {{token}}",
  "auth_endpoint": "/api/login",
  "auth_method": "POST",
  "credentials_required": ["email", "password"],
  "test_credentials": {{"email": "test@example.com", "password": "test123"}},
  "token_response_path": "data.token",
  "token_expiration": "24 hours",
  "additional_data": {{
    "vendorCode": "data.vendorCode",
    "userId": "data._id"
  }}
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
        
        gemini = GeminiProvider()
        response = await gemini.generate_content(prompt, temperature=0.1)
        auth_config = parse_json_response(response)
        
        logger.info(f"[OK] Extracted auth config: {auth_config.get('type', 'unknown')}")
        
        return {**state, "auth_config": auth_config}
    
    except Exception as e:
        logger.error(f"[ERROR] Error extracting auth config: {e}")
        return {**state, "auth_config": {}, "error": str(e)}


async def extract_schemas_node(state: APIAnalysisState) -> APIAnalysisState:
    """Extract request/response schemas from examples"""
    try:
        logger.info("[INFO] Extracting data schemas...")
        
        prompt = f"""
Extract data schemas from examples in this documentation:

Documentation:
{state['raw_text'][:15000]}

Endpoints:
{json.dumps(state['endpoints'], indent=2)[:5000]}

For each endpoint, provide:
- Request body schema (JSON Schema format)
- Response schema (JSON Schema format)
- Required vs optional fields
- Field types and constraints (min, max, pattern, enum)
- Example values
- Field descriptions

Output as JSON:
{{
  "/api/endpoint1": {{
    "request_schema": {{
      "type": "object",
      "properties": {{
        "field1": {{"type": "string", "description": "...", "required": true}},
        "field2": {{"type": "number", "minimum": 0}}
      }},
      "required": ["field1"]
    }},
    "response_schema": {{
      "type": "object",
      "properties": {{
        "status": {{"type": "string"}},
        "data": {{"type": "object"}}
      }}
    }},
    "example_request": {{"field1": "value1"}},
    "example_response": {{"status": "success", "data": {{}}}}
  }}
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
        
        gemini = GeminiProvider()
        response = await gemini.generate_content(prompt, temperature=0.1)
        schemas = parse_json_response(response)
        
        logger.info(f"[OK] Extracted schemas for {len(schemas)} endpoints")
        
        return {**state, "schemas": schemas}
    
    except Exception as e:
        logger.error(f"[ERROR] Error extracting schemas: {e}")
        return {**state, "schemas": {}, "error": str(e)}


async def map_dependencies_node(state: APIAnalysisState) -> APIAnalysisState:
    """Map dependencies between endpoints"""
    try:
        logger.info("[INFO] Mapping endpoint dependencies...")
        
        prompt = f"""
Analyze endpoint dependencies:

Endpoints: {json.dumps(state['endpoints'], indent=2)}

Identify:
- Which endpoints must be called before others
- Which endpoints provide data needed by others (IDs, tokens, codes)
- Authentication flow dependencies
- Data flow between endpoints (e.g., create address → use addressId)

Consider parameter names like:
- addressId, orderId, bookingId → need create endpoints first
- token, authToken → need auth endpoint first
- vendorCode, userId → may come from login

Output as JSON:
{{
  "/api/endpoint1": [],
  "/api/endpoint2": ["/api/endpoint1"],
  "/api/endpoint3": ["/api/endpoint1", "/api/endpoint2"]
}}

Return ONLY valid JSON mapping endpoint paths to dependency arrays.
"""
        
        gemini = GeminiProvider()
        response = await gemini.generate_content(prompt, temperature=0.2)
        dependencies = parse_json_response(response)
        
        logger.info(f"[OK] Mapped dependencies for {len(dependencies)} endpoints")
        
        return {**state, "dependencies": dependencies}
    
    except Exception as e:
        logger.error(f"[ERROR] Error mapping dependencies: {e}")
        return {**state, "dependencies": {}, "error": str(e)}


async def extract_business_rules_node(state: APIAnalysisState) -> APIAnalysisState:
    """Extract business rules and constraints"""
    try:
        logger.info("[INFO] Extracting business rules...")
        
        prompt = f"""
Extract business rules and constraints from this documentation:

Documentation:
{state['raw_text'][:15000]}

Identify:
- Validation rules (e.g., "weight must be > 0", "email must be valid")
- Business constraints (e.g., "cannot cancel after pickup", "max 50kg per shipment")
- Required sequences (e.g., "must validate address before booking")
- Error conditions and handling
- Rate limits and quotas
- Data format requirements (date formats, phone formats, etc.)

Output as JSON array of rules:
[
  {{
    "rule": "Weight must be greater than 0",
    "type": "validation",
    "applies_to": ["/api/bookings"],
    "severity": "error"
  }},
  {{
    "rule": "Cannot cancel booking after pickup",
    "type": "business_constraint",
    "applies_to": ["/api/cancel"],
    "severity": "error"
  }}
]

Return ONLY valid JSON array, no markdown, no explanations.
"""
        
        gemini = GeminiProvider()
        response = await gemini.generate_content(prompt, temperature=0.2)
        rules = parse_json_response(response)
        
        logger.info(f"[OK] Extracted {len(rules)} business rules")
        
        return {**state, "business_rules": rules}
    
    except Exception as e:
        logger.error(f"[ERROR] Error extracting business rules: {e}")
        return {**state, "business_rules": [], "error": str(e)}


async def analyze_workflow_node(state: APIAnalysisState) -> APIAnalysisState:
    """Analyze complete workflow and data flow"""
    try:
        logger.info("[INFO] Analyzing workflow and data flow...")
        
        gemini = GeminiProvider()
        workflow_analysis = await gemini.analyze_workflow_and_data_flow(
            endpoints=state['endpoints'],
            documentation_text=state['raw_text'][:10000]
        )
        
        logger.info(f"[OK] Analyzed {len(workflow_analysis.get('workflows', []))} workflows")
        
        return {**state, "workflow_analysis": workflow_analysis}
    
    except Exception as e:
        logger.error(f"[ERROR] Error analyzing workflow: {e}")
        return {
            **state,
            "workflow_analysis": {
                "login_flow": {"required": False},
                "workflows": [],
                "data_mappings": {}
            },
            "error": str(e)
        }


async def extract_patterns_node(state: APIAnalysisState) -> APIAnalysisState:
    """Extract workflow patterns and data dependencies (NEW)"""
    try:
        logger.info("[SEARCH] Extracting workflow patterns and data dependencies...")
        
        pattern_extractor = PatternExtractor()
        patterns_result = await pattern_extractor.extract_patterns(
            raw_text=state['raw_text'],
            endpoints=state['endpoints'],
            schemas=state['schemas']
        )
        
        logger.info(f"[OK] Extracted {len(patterns_result.get('workflow_patterns', []))} workflow patterns")
        logger.info(f"[OK] Extracted {len(patterns_result.get('data_dependencies', []))} data dependencies")
        
        return {
            **state,
            'workflow_patterns': patterns_result.get('workflow_patterns', []),
            'data_dependencies': patterns_result.get('data_dependencies', [])
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Error extracting patterns: {e}")
        return {
            **state,
            'workflow_patterns': [],
            'data_dependencies': [],
            'error': str(e)
        }


async def detect_validation_rules_node(state: APIAnalysisState) -> APIAnalysisState:
    """Detect validation rules from documentation and examples (NEW)"""
    try:
        logger.info("[SEARCH] Detecting validation rules...")
        
        rule_detector = ValidationRuleDetector()
        rules_result = await rule_detector.detect_rules(
            raw_text=state['raw_text'],
            schemas=state['schemas'],
            examples=None  # Could extract from test scenarios
        )
        
        logger.info(f"[OK] Detected {len(rules_result.get('validation_rules', []))} validation rules")
        
        return {
            **state,
            'validation_rules': rules_result.get('validation_rules', [])
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Error detecting validation rules: {e}")
        return {
            **state,
            'validation_rules': [],
            'error': str(e)
        }


async def build_dependency_graph_node(state: APIAnalysisState) -> APIAnalysisState:
    """Build comprehensive dependency graph (NEW)"""
    try:
        logger.info("[INFO] Building comprehensive dependency graph...")
        
        # Build graph from data dependencies and workflow patterns
        graph = {
            'nodes': [],
            'edges': [],
            'execution_order': []
        }
        
        # Add endpoints as nodes
        for endpoint in state['endpoints']:
            graph['nodes'].append({
                'id': endpoint.get('path'),
                'method': endpoint.get('method'),
                'summary': endpoint.get('summary'),
                'type': 'endpoint'
            })
        
        # Add edges from data dependencies
        for dep in state.get('data_dependencies', []):
            graph['edges'].append({
                'from': dep.get('source_endpoint'),
                'to': dep.get('target_endpoint'),
                'type': 'data_dependency',
                'field': dep.get('target_field'),
                'extraction': dep.get('extraction_path')
            })
        
        # Build execution order using topological sort
        execution_order = _topological_sort(graph['edges'], graph['nodes'])
        graph['execution_order'] = execution_order
        
        logger.info(f"[OK] Built dependency graph with {len(graph['nodes'])} nodes and {len(graph['edges'])} edges")
        
        return {
            **state,
            'dependency_graph': graph
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Error building dependency graph: {e}")
        return {
            **state,
            'dependency_graph': {'nodes': [], 'edges': [], 'execution_order': []},
            'error': str(e)
        }


def _topological_sort(edges: List[Dict[str, Any]], nodes: List[Dict[str, Any]]) -> List[str]:
    """Simple topological sort for execution order"""
    from collections import defaultdict, deque
    
    # Build adjacency list and in-degree
    adj = defaultdict(list)
    in_degree = defaultdict(int)
    
    # Initialize all nodes
    for node in nodes:
        node_id = node['id']
        in_degree[node_id] = 0
    
    # Build graph
    for edge in edges:
        from_node = edge.get('from')
        to_node = edge.get('to')
        if from_node and to_node and to_node != '*':  # Skip wildcard targets
            adj[from_node].append(to_node)
            in_degree[to_node] += 1
    
    # Find nodes with no dependencies
    queue = deque([node for node, degree in in_degree.items() if degree == 0])
    result = []
    
    while queue:
        current = queue.popleft()
        result.append(current)
        
        for neighbor in adj[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # Add any remaining nodes (in case of cycles)
    for node in nodes:
        if node['id'] not in result:
            result.append(node['id'])
    
    return result


async def generate_test_scenarios_node(state: APIAnalysisState) -> APIAnalysisState:
    """Generate comprehensive test scenarios"""
    try:
        logger.info("[TEST] Generating test scenarios...")
        
        prompt = f"""
Generate comprehensive test scenarios for this API:

Endpoints: {json.dumps(state['endpoints'], indent=2)[:8000]}
Dependencies: {json.dumps(state['dependencies'], indent=2)}
Business Rules: {json.dumps(state['business_rules'], indent=2)[:3000]}
Workflow: {json.dumps(state.get('workflow_analysis', {}), indent=2)[:3000]}

Create test scenarios covering:
1. **Happy Path**: Success cases with valid data
2. **Authentication**: Login flow, token usage, auth failures
3. **Edge Cases**: Boundary values, empty strings, max lengths
4. **Error Cases**: Invalid data, missing required fields, constraint violations
5. **Dependency Violations**: Calling endpoints without prerequisites
6. **Business Rule Violations**: Breaking business constraints
7. **Complete Workflows**: End-to-end user journeys

For each scenario:
- Name and description
- Endpoint sequence to call (in order)
- Test data for each step
- Expected result (success/failure)
- Expected status codes
- What to extract from responses

Output as JSON array:
[
  {{
    "name": "Happy Path - Create Booking",
    "description": "Complete booking flow with valid data",
    "type": "happy_path",
    "steps": [
      {{
        "order": 1,
        "endpoint": "/api/login",
        "method": "POST",
        "data": {{"email": "test@example.com", "password": "test123"}},
        "expected_status": 200,
        "extract": {{"token": "data.token", "vendorCode": "data.vendorCode"}}
      }},
      {{
        "order": 2,
        "endpoint": "/api/bookings",
        "method": "POST",
        "data": {{"origin": "Mumbai", "destination": "Delhi"}},
        "expected_status": 201,
        "extract": {{"bookingId": "data.id"}}
      }}
    ]
  }}
]

Return ONLY valid JSON array, no markdown, no explanations.
"""
        
        gemini = GeminiProvider()
        response = await gemini.generate_content(prompt, temperature=0.3)
        scenarios = parse_json_response(response)
        
        logger.info(f"[OK] Generated {len(scenarios)} test scenarios")
        
        return {**state, "test_scenarios": scenarios, "analysis_complete": True}
    
    except Exception as e:
        logger.error(f"[ERROR] Error generating test scenarios: {e}")
        return {**state, "test_scenarios": [], "analysis_complete": True, "error": str(e)}


def build_api_analysis_graph() -> StateGraph:
    """Build comprehensive API analysis graph"""
    logger.info("[INFO] Building API analysis graph...")
    
    workflow = StateGraph(APIAnalysisState)
    
    # Add nodes
    workflow.add_node("extract_endpoints", extract_endpoints_node)
    workflow.add_node("extract_auth", extract_auth_config_node)
    workflow.add_node("extract_schemas", extract_schemas_node)
    workflow.add_node("map_dependencies", map_dependencies_node)
    workflow.add_node("extract_rules", extract_business_rules_node)
    workflow.add_node("analyze_workflow", analyze_workflow_node)
    # NEW: Pattern extraction and validation rules
    workflow.add_node("extract_patterns", extract_patterns_node)
    workflow.add_node("detect_validation_rules", detect_validation_rules_node)
    workflow.add_node("build_dependency_graph", build_dependency_graph_node)
    workflow.add_node("generate_scenarios", generate_test_scenarios_node)
    
    # Define flow
    workflow.set_entry_point("extract_endpoints")
    workflow.add_edge("extract_endpoints", "extract_auth")
    workflow.add_edge("extract_auth", "extract_schemas")
    workflow.add_edge("extract_schemas", "map_dependencies")
    workflow.add_edge("map_dependencies", "extract_rules")
    workflow.add_edge("extract_rules", "analyze_workflow")
    # NEW: Enhanced analysis flow
    workflow.add_edge("analyze_workflow", "extract_patterns")
    workflow.add_edge("extract_patterns", "detect_validation_rules")
    workflow.add_edge("detect_validation_rules", "build_dependency_graph")
    workflow.add_edge("build_dependency_graph", "generate_scenarios")
    workflow.add_edge("generate_scenarios", END)
    
    logger.info("[OK] API analysis graph built successfully")
    
    return workflow.compile()


class ComprehensiveAPIAnalyzer:
    """Main class for comprehensive API analysis"""
    
    def __init__(self):
        self.graph = build_api_analysis_graph()
        self.mistral = MistralProvider()
    
    async def analyze_from_file(
        self,
        file_path: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        file_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze API documentation from file
        
        Args:
            file_path: Path to documentation file
            file_bytes: File content as bytes
            file_url: URL to documentation file
            
        Returns:
            Complete API analysis
        """
        try:
            logger.info("[FILE] Starting comprehensive API analysis...")
            
            # Step 1: Extract text using Mistral OCR
            logger.info("[SEARCH] Extracting text from document...")
            ocr_result = await self.mistral.process_document(
                document_path=file_path,
                document_bytes=file_bytes,
                document_url=file_url,
                include_images=False
            )
            
            raw_text = ocr_result.get('text', '')
            logger.info(f"[OK] Extracted {len(raw_text)} characters of text")
            
            # Step 2: Run comprehensive analysis
            logger.info("[AI] Running AI analysis pipeline...")
            initial_state: APIAnalysisState = {
                'raw_text': raw_text,
                'endpoints': [],
                'auth_config': {},
                'schemas': {},
                'dependencies': {},
                'business_rules': [],
                'test_scenarios': [],
                'workflow_analysis': {},
                # NEW: Universal pattern extraction
                'workflow_patterns': [],
                'data_dependencies': [],
                'validation_rules': [],
                'dependency_graph': {},
                'analysis_complete': False,
                'error': None
            }
            
            result = await self.graph.ainvoke(initial_state)
            
            # Step 3: Compile final result
            analysis = {
                'success': result.get('analysis_complete', False),
                'endpoints': result.get('endpoints', []),
                'auth_config': result.get('auth_config', {}),
                'schemas': result.get('schemas', {}),
                'dependencies': result.get('dependencies', {}),
                'business_rules': result.get('business_rules', []),
                'workflow_analysis': result.get('workflow_analysis', {}),
                'test_scenarios': result.get('test_scenarios', []),
                # NEW: Universal pattern extraction results
                'workflow_patterns': result.get('workflow_patterns', []),
                'data_dependencies': result.get('data_dependencies', []),
                'validation_rules': result.get('validation_rules', []),
                'dependency_graph': result.get('dependency_graph', {}),
                'raw_text': raw_text,
                'error': result.get('error'),
                'statistics': {
                    'endpoints_found': len(result.get('endpoints', [])),
                    'schemas_extracted': len(result.get('schemas', {})),
                    'dependencies_mapped': len(result.get('dependencies', {})),
                    'business_rules': len(result.get('business_rules', [])),
                    'test_scenarios': len(result.get('test_scenarios', [])),
                    'workflows': len(result.get('workflow_analysis', {}).get('workflows', [])),
                    # NEW statistics
                    'workflow_patterns': len(result.get('workflow_patterns', [])),
                    'data_dependencies': len(result.get('data_dependencies', [])),
                    'validation_rules': len(result.get('validation_rules', [])),
                    'dependency_graph_nodes': len(result.get('dependency_graph', {}).get('nodes', [])),
                    'dependency_graph_edges': len(result.get('dependency_graph', {}).get('edges', []))
                }
            }
            
            logger.info("[OK] Comprehensive API analysis complete!")
            logger.info(f"[INFO] Statistics: {json.dumps(analysis['statistics'], indent=2)}")
            
            return analysis
        
        except Exception as e:
            logger.error(f"[ERROR] Error in comprehensive API analysis: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'endpoints': [],
                'auth_config': {},
                'schemas': {},
                'dependencies': {},
                'business_rules': [],
                'workflow_analysis': {},
                'test_scenarios': [],
                'statistics': {}
            }
    
    async def analyze_from_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze API documentation from raw text
        
        Args:
            text: Documentation text
            
        Returns:
            Complete API analysis
        """
        try:
            logger.info("[NOTE] Starting analysis from text...")
            
            initial_state: APIAnalysisState = {
                'raw_text': text,
                'endpoints': [],
                'auth_config': {},
                'schemas': {},
                'dependencies': {},
                'business_rules': [],
                'test_scenarios': [],
                'workflow_analysis': {},
                'analysis_complete': False,
                'error': None
            }
            
            result = await self.graph.ainvoke(initial_state)
            
            analysis = {
                'success': result.get('analysis_complete', False),
                'endpoints': result.get('endpoints', []),
                'auth_config': result.get('auth_config', {}),
                'schemas': result.get('schemas', {}),
                'dependencies': result.get('dependencies', {}),
                'business_rules': result.get('business_rules', []),
                'workflow_analysis': result.get('workflow_analysis', {}),
                'test_scenarios': result.get('test_scenarios', []),
                'raw_text': text,
                'error': result.get('error'),
                'statistics': {
                    'endpoints_found': len(result.get('endpoints', [])),
                    'schemas_extracted': len(result.get('schemas', {})),
                    'dependencies_mapped': len(result.get('dependencies', {})),
                    'business_rules': len(result.get('business_rules', [])),
                    'test_scenarios': len(result.get('test_scenarios', [])),
                    'workflows': len(result.get('workflow_analysis', {}).get('workflows', []))
                }
            }
            
            logger.info("[OK] Analysis complete!")
            
            return analysis
        
        except Exception as e:
            logger.error(f"[ERROR] Error analyzing text: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'endpoints': [],
                'auth_config': {},
                'schemas': {},
                'dependencies': {},
                'business_rules': [],
                'workflow_analysis': {},
                'test_scenarios': [],
                'statistics': {}
            }

