"""
Pattern Extractor - Extract workflow patterns and data dependencies from documentation
Part of Universal Autonomous API Testing System
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from src.infrastructure.ai.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class WorkflowPattern(BaseModel):
    """Represents a discovered workflow pattern"""
    pattern_id: str
    pattern_type: str  # "sequential", "conditional", "parallel", "loop"
    description: str
    steps: List[str]  # List of endpoint paths in order
    data_dependencies: Dict[str, str]  # {"target_field": "source_endpoint.field"}
    conditions: List[str]  # Business conditions for this pattern
    confidence: float  # 0.0 to 1.0
    examples: List[Dict[str, Any]]  # Example data flows


class DataDependency(BaseModel):
    """Represents a data dependency between endpoints"""
    source_endpoint: str
    source_field: str
    target_endpoint: str
    target_field: str
    dependency_type: str  # "required", "optional", "conditional"
    extraction_path: str  # JSONPath to extract from response
    transformation: Optional[str] = None  # Optional transformation rule


class PatternExtractor:
    """
    Extract workflow patterns and data dependencies from API documentation
    
    Uses AI to identify:
    - Common workflow sequences (login → create → use)
    - Data flow patterns (extract ID → use in next call)
    - Conditional patterns (check balance → create order)
    - Business logic patterns
    """
    
    def __init__(self):
        self.gemini = GeminiProvider()
    
    async def extract_patterns(
        self,
        raw_text: str,
        endpoints: List[Dict[str, Any]],
        schemas: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract all patterns from documentation
        
        Args:
            raw_text: Raw documentation text
            endpoints: Parsed endpoints
            schemas: Endpoint schemas
            
        Returns:
            Dictionary with patterns and dependencies
        """
        try:
            logger.info("[SEARCH] Extracting workflow patterns from documentation...")
            
            # Extract workflow patterns
            workflow_patterns = await self._extract_workflow_patterns(
                raw_text, endpoints
            )
            
            # Extract data dependencies
            data_dependencies = await self._extract_data_dependencies(
                raw_text, endpoints, schemas
            )
            
            # Extract sequential patterns
            sequential_patterns = await self._extract_sequential_patterns(
                endpoints, workflow_patterns
            )
            
            # Extract conditional patterns
            conditional_patterns = await self._extract_conditional_patterns(
                raw_text, endpoints
            )
            
            logger.info(f"[OK] Extracted {len(workflow_patterns)} workflow patterns")
            logger.info(f"[OK] Extracted {len(data_dependencies)} data dependencies")
            
            return {
                'workflow_patterns': workflow_patterns,
                'data_dependencies': data_dependencies,
                'sequential_patterns': sequential_patterns,
                'conditional_patterns': conditional_patterns,
                'pattern_summary': self._create_pattern_summary(
                    workflow_patterns,
                    data_dependencies
                )
            }
        
        except Exception as e:
            logger.error(f"[ERROR] Error extracting patterns: {e}")
            return {
                'workflow_patterns': [],
                'data_dependencies': [],
                'sequential_patterns': [],
                'conditional_patterns': [],
                'pattern_summary': {}
            }
    
    async def _extract_workflow_patterns(
        self,
        raw_text: str,
        endpoints: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract workflow patterns using AI"""
        try:
            prompt = f"""
Analyze this API documentation and identify ALL workflow patterns.

Documentation:
{raw_text[:15000]}

Available Endpoints:
{json.dumps([{{'method': e.get('method'), 'path': e.get('path'), 'summary': e.get('summary')}} for e in endpoints], indent=2)}

Identify workflow patterns such as:

1. **Authentication Patterns**:
   - Login → Get Token → Use Token in subsequent calls
   - Refresh Token → Get New Token
   
2. **CRUD Patterns**:
   - Create Resource → Get ID → Use ID in other calls
   - Create → Read → Update → Delete sequences
   
3. **Business Workflow Patterns**:
   - Check Balance → Create Order
   - Validate Address → Create Shipment
   - Upload File → Get URL → Reference URL
   - Create Parent → Create Children (e.g., Order → Items)
   
4. **Data Flow Patterns**:
   - Extract data from response → Use in next request
   - Accumulate data across multiple calls
   - Transform data between calls

For EACH pattern, provide:
- Pattern type (sequential, conditional, parallel, loop)
- Description of what the pattern does
- Exact sequence of endpoints
- Data dependencies (what data flows between steps)
- Conditions or business rules
- Confidence level (0.0 to 1.0)

Output as JSON:
{{
  "patterns": [
    {{
      "pattern_id": "auth_flow",
      "pattern_type": "sequential",
      "description": "Authentication flow - login and use token",
      "steps": ["/api/login", "/api/other-endpoints"],
      "data_dependencies": {{
        "token": "login.response.data.token",
        "vendorCode": "login.response.data.vendorCode"
      }},
      "conditions": ["Must login before any other API call"],
      "confidence": 0.95,
      "examples": [
        {{
          "step_1": {{"endpoint": "/api/login", "extracts": {{"token": "data.token"}}}},
          "step_2": {{"endpoint": "/api/orders", "uses": {{"token": "Authorization header"}}}}
        }}
      ]
    }}
  ]
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.2)
            result = self._parse_json_response(response)
            
            return result.get('patterns', [])
        
        except Exception as e:
            logger.error(f"Error extracting workflow patterns: {e}")
            return []
    
    async def _extract_data_dependencies(
        self,
        raw_text: str,
        endpoints: List[Dict[str, Any]],
        schemas: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract data dependencies between endpoints"""
        try:
            prompt = f"""
Analyze data dependencies between API endpoints.

Endpoints:
{json.dumps(endpoints[:20], indent=2)}

Schemas:
{json.dumps(schemas, indent=2)[:10000]}

Documentation:
{raw_text[:10000]}

Identify data dependencies where:
1. One endpoint returns data that another endpoint needs
2. IDs, tokens, codes, or references flow between endpoints
3. Response fields map to request parameters

For EACH dependency, identify:
- Source endpoint (where data comes from)
- Source field (field name in response)
- Target endpoint (where data is used)
- Target field (parameter name in request)
- Dependency type (required, optional, conditional)
- Extraction path (JSONPath to extract from response)
- Any transformation needed

Look for patterns like:
- "addressId" in request → comes from "id" in /create-address response
- "token" in header → comes from "token" in /login response
- "orderId" parameter → comes from "orderId" in /create-order response

Output as JSON:
{{
  "dependencies": [
    {{
      "source_endpoint": "/api/login",
      "source_field": "token",
      "target_endpoint": "*",
      "target_field": "Authorization",
      "dependency_type": "required",
      "extraction_path": "data.token",
      "transformation": "Bearer {{token}}"
    }},
    {{
      "source_endpoint": "/api/address/create",
      "source_field": "id",
      "target_endpoint": "/api/order/create",
      "target_field": "addressId",
      "dependency_type": "required",
      "extraction_path": "data.address.id",
      "transformation": null
    }}
  ]
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.2)
            result = self._parse_json_response(response)
            
            return result.get('dependencies', [])
        
        except Exception as e:
            logger.error(f"Error extracting data dependencies: {e}")
            return []
    
    async def _extract_sequential_patterns(
        self,
        endpoints: List[Dict[str, Any]],
        workflow_patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract sequential execution patterns"""
        try:
            # Analyze endpoint methods and paths to find sequential patterns
            sequential = []
            
            # Pattern: POST (create) → GET (read) → PUT/PATCH (update) → DELETE
            resource_groups = {}
            for endpoint in endpoints:
                path = endpoint.get('path', '')
                method = endpoint.get('method', '')
                
                # Extract resource name
                resource = self._extract_resource_name(path)
                if resource:
                    if resource not in resource_groups:
                        resource_groups[resource] = []
                    resource_groups[resource].append({
                        'method': method,
                        'path': path,
                        'endpoint': endpoint
                    })
            
            # Build CRUD sequences
            for resource, group in resource_groups.items():
                methods = {ep['method']: ep['path'] for ep in group}
                
                if 'POST' in methods:
                    sequence = [methods['POST']]
                    
                    if 'GET' in methods:
                        sequence.append(methods['GET'])
                    
                    if 'PUT' in methods or 'PATCH' in methods:
                        sequence.append(methods.get('PUT', methods.get('PATCH')))
                    
                    if 'DELETE' in methods:
                        sequence.append(methods['DELETE'])
                    
                    if len(sequence) > 1:
                        sequential.append({
                            'pattern_id': f'crud_{resource}',
                            'pattern_type': 'sequential',
                            'description': f'CRUD sequence for {resource}',
                            'steps': sequence,
                            'resource': resource,
                            'confidence': 0.9
                        })
            
            return sequential
        
        except Exception as e:
            logger.error(f"Error extracting sequential patterns: {e}")
            return []
    
    async def _extract_conditional_patterns(
        self,
        raw_text: str,
        endpoints: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract conditional workflow patterns"""
        try:
            prompt = f"""
Identify CONDITIONAL workflow patterns from this API documentation.

Documentation:
{raw_text[:15000]}

Endpoints:
{json.dumps([{{'method': e.get('method'), 'path': e.get('path'), 'summary': e.get('summary')}} for e in endpoints[:20]], indent=2)}

Look for patterns like:
- "If balance sufficient → create order, else → top up balance first"
- "If address valid → proceed, else → validate address"
- "If item in stock → create order, else → return error"
- "Check status → if pending → cancel, if shipped → cannot cancel"

For EACH conditional pattern:
- Condition to check
- Endpoint to call if true
- Endpoint to call if false (or error handling)
- How to evaluate the condition

Output as JSON:
{{
  "conditional_patterns": [
    {{
      "pattern_id": "check_balance_before_order",
      "description": "Check balance before creating order",
      "condition": "balance >= order_amount",
      "check_endpoint": "/api/wallet/balance",
      "check_field": "data.balance",
      "true_path": ["/api/order/create"],
      "false_path": ["/api/wallet/topup", "/api/order/create"],
      "confidence": 0.85
    }}
  ]
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.3)
            result = self._parse_json_response(response)
            
            return result.get('conditional_patterns', [])
        
        except Exception as e:
            logger.error(f"Error extracting conditional patterns: {e}")
            return []
    
    def _extract_resource_name(self, path: str) -> Optional[str]:
        """Extract resource name from API path"""
        # /api/orders/123 -> orders
        # /cargo-api/address/create -> address
        parts = path.strip('/').split('/')
        for part in parts:
            # Skip common prefixes and parameters
            if part in ['api', 'v1', 'v2', 'v3', 'cargo-api', 'wallet-api']:
                continue
            if '{' in part or part.isdigit() or part in ['create', 'update', 'delete', 'get']:
                continue
            return part.lower()
        return None
    
    def _create_pattern_summary(
        self,
        workflow_patterns: List[Dict[str, Any]],
        data_dependencies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create summary of extracted patterns"""
        return {
            'total_patterns': len(workflow_patterns),
            'total_dependencies': len(data_dependencies),
            'pattern_types': self._count_pattern_types(workflow_patterns),
            'dependency_types': self._count_dependency_types(data_dependencies),
            'high_confidence_patterns': len([
                p for p in workflow_patterns 
                if p.get('confidence', 0) >= 0.8
            ])
        }
    
    def _count_pattern_types(self, patterns: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count patterns by type"""
        counts = {}
        for pattern in patterns:
            ptype = pattern.get('pattern_type', 'unknown')
            counts[ptype] = counts.get(ptype, 0) + 1
        return counts
    
    def _count_dependency_types(self, dependencies: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count dependencies by type"""
        counts = {}
        for dep in dependencies:
            dtype = dep.get('dependency_type', 'unknown')
            counts[dtype] = counts.get(dtype, 0) + 1
        return counts
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from AI response"""
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
            return {}

