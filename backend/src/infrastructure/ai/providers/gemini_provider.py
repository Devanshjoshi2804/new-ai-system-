"""
Google Gemini AI Provider for advanced API testing and reasoning
Enhanced with caching and resilience patterns
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from src.infrastructure.ai.cache.ai_cache import get_cache
from src.infrastructure.ai.resilience.retry_handler import resilient_call
from src.infrastructure.ai.resilience.circuit_breaker import with_circuit_breaker

logger = logging.getLogger(__name__)


class GeminiProvider:
    """
    Google Gemini API integration for advanced reasoning in API testing
    Enhanced with caching, retry logic, and circuit breaker
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, use_cache: bool = True):
        """
        Initialize Gemini provider
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model_name: Model to use (defaults to GEMINI_MODEL env var or gemini-2.0-flash-exp)
            use_cache: Whether to use response caching
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.use_cache = use_cache
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=GenerationConfig(
                temperature=0.2,  # Lower temperature for more deterministic outputs
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
            )
        )
        
        # Get cache instance
        self.cache = get_cache() if use_cache else None
        
        logger.info(f"[OK] Gemini provider initialized: model={self.model_name}, cache={'enabled' if use_cache else 'disabled'}")
    
    @resilient_call(max_retries=3, timeout=60.0, initial_delay=2.0)
    @with_circuit_breaker("gemini_api", failure_threshold=5, timeout=120.0)
    async def _generate_content_with_resilience(self, prompt: str) -> str:
        """Internal method for resilient content generation"""
        import asyncio
        
        # Run in thread to avoid blocking
        def generate():
            response = self.model.generate_content(prompt)
            return response.text.strip()
        
        return await asyncio.to_thread(generate)
    
    async def generate_content(self, prompt: str, temperature: float = 0.2, use_cache: bool = True) -> str:
        """
        Generate content with caching and resilience
        
        Args:
            prompt: The prompt text
            temperature: Sampling temperature
            use_cache: Whether to use cache for this call
            
        Returns:
            Generated text
        """
        # Check cache first
        if use_cache and self.cache:
            cached = await self.cache.get(prompt, self.model_name, temperature=temperature)
            if cached:
                return cached
        
        # Generate content with resilience
        result = await self._generate_content_with_resilience(prompt)
        
        # Cache the result
        if use_cache and self.cache:
            await self.cache.set(prompt, self.model_name, result, temperature=temperature)
        
        return result
    
    async def analyze_api_dependencies(self, endpoints: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Use Gemini to understand API relationships and dependencies
        
        Args:
            endpoints: List of API endpoint specifications
            
        Returns:
            Dictionary mapping endpoint paths to list of dependency paths
        """
        try:
            prompt = f"""
Analyze these API endpoints and identify dependencies between them.

API Endpoints:
{json.dumps(endpoints, indent=2)}

For each endpoint, determine which other endpoints it depends on. Consider:
1. Authentication endpoints must be called first
2. Endpoints that create resources (return IDs) should come before endpoints that use those IDs
3. Parameter names like "addressId", "awbNumber", "orderId" indicate dependencies
4. Sequential workflows (login → address → wallet → booking)

Return ONLY a JSON object mapping endpoint paths to arrays of dependency paths:
{{
  "/endpoint1": [],
  "/endpoint2": ["/endpoint1"],
  "/endpoint3": ["/endpoint1", "/endpoint2"]
}}
"""
            
            result_text = await self.generate_content(prompt, temperature=0.1)
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            dependencies = json.loads(result_text)
            logger.info(f"[OK] Gemini analyzed {len(endpoints)} endpoints and found dependencies")
            
            return dependencies
        
        except Exception as e:
            logger.error(f"[ERROR] Error analyzing API dependencies with Gemini: {e}")
            # Return empty dependencies on error
            return {endpoint.get("path", ""): [] for endpoint in endpoints}
    
    async def generate_test_scenarios(self, endpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate comprehensive test cases for an API endpoint
        
        Args:
            endpoint: API endpoint specification with path, method, parameters
            
        Returns:
            List of test scenarios with test data
        """
        try:
            prompt = f"""
Generate comprehensive test cases for this API endpoint:

Endpoint: {endpoint.get('method', 'GET')} {endpoint.get('path', '')}
Description: {endpoint.get('summary', '')}
Parameters: {json.dumps(endpoint.get('parameters', []), indent=2)}

Generate 5-8 test scenarios covering:
1. Happy path with all required fields
2. Missing required fields (one at a time)
3. Invalid data types
4. Boundary values (empty strings, very long strings, negative numbers)
5. Optional field combinations
6. Edge cases specific to this API

Return ONLY a JSON array of test scenarios:
[
  {{
    "name": "Test scenario name",
    "description": "What this tests",
    "test_data": {{"field1": "value1", "field2": "value2"}},
    "expected_status": 200,
    "should_fail": false
  }}
]
"""
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            test_scenarios = json.loads(result_text)
            logger.info(f"Generated {len(test_scenarios)} test scenarios for {endpoint.get('path', '')}")
            
            return test_scenarios
            
        except Exception as e:
            logger.error(f"Error generating test scenarios with Gemini: {e}")
            # Return basic test case on error
            return [{
                "name": "Basic happy path test",
                "description": "Test with all required fields",
                "test_data": {},
                "expected_status": 200,
                "should_fail": False
            }]
    
    async def analyze_workflow_and_data_flow(
        self,
        endpoints: List[Dict[str, Any]],
        documentation_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze complete workflow including login flow, data dependencies, and execution order
        
        Args:
            endpoints: List of API endpoint specifications
            documentation_text: Optional full documentation text for context
            
        Returns:
            Complete workflow analysis with login flow, data mappings, and workflows
        """
        try:
            # Prepare documentation context (limit to 8000 chars for token limits)
            doc_context = ""
            if documentation_text:
                doc_context = f"\n\nDocumentation Context:\n{documentation_text[:8000]}"
            
            prompt = f"""
Analyze this API documentation and understand the complete workflow, authentication, and data dependencies.

API Endpoints:
{json.dumps(endpoints, indent=2)[:10000]}
{doc_context}

Analyze and return a JSON with:

1. **Login Flow**: Does the API require login/authentication?
   - Which endpoint is the login/auth endpoint?
   - What credentials are needed? (look for test credentials in documentation)
   - Where is the token in the response? (JSON path like "data.token" or "data._id")
   - How should the token be used? (header name and format)
   - What other data should be extracted from login? (vendorCode, userId, etc.)

2. **Workflows**: Identify logical workflows (e.g., "Create Shipment", "Track Order")
   - For each workflow, list the sequence of endpoints
   - For each step, identify what data it extracts and what data it needs

3. **Data Mappings**: For each piece of data (IDs, codes, tokens):
   - Which endpoint creates/returns it?
   - What's the JSON path in the response?
   - Which endpoints need this data?
   - What parameter name do they use?

Return ONLY valid JSON (no markdown, no explanations) in this EXACT format:
{{
  "login_flow": {{
    "required": true,
    "endpoint": "/api/login",
    "method": "POST",
    "credentials": {{"email": "test@example.com", "password": "password"}},
    "token_extraction": "data.token",
    "token_header": "Authorization",
    "token_format": "Bearer {{token}}",
    "additional_extractions": {{
      "vendorCode": "data.vendorCode",
      "userId": "data._id"
    }}
  }},
  "workflows": [
    {{
      "name": "Main Workflow",
      "description": "Primary workflow description",
      "steps": [
        {{
          "endpoint": "/endpoint1",
          "order": 1,
          "extracts": {{"field_name": "response.path.to.value"}},
          "requires": {{}}
        }}
      ]
    }}
  ],
  "data_mappings": {{
    "token": {{
      "source_endpoint": "/api/login",
      "source_path": "data.token",
      "used_in_header": "Authorization",
      "used_in_endpoints": ["all"]
    }},
    "vendorCode": {{
      "source_endpoint": "/api/login",
      "source_path": "data.vendorCode",
      "used_in_parameter": "vendorCode",
      "used_in_endpoints": ["/api/address", "/api/orders"]
    }}
  }}
}}
"""
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            workflow_analysis = json.loads(result_text)
            logger.info(f"[OK] Gemini analyzed workflow: {len(workflow_analysis.get('workflows', []))} workflows, {len(workflow_analysis.get('data_mappings', {}))} data mappings")
            
            return workflow_analysis
        
        except Exception as e:
            logger.error(f"Error analyzing workflow with Gemini: {e}")
            # Return minimal structure on error
            return {
                "login_flow": {"required": False},
                "workflows": [],
                "data_mappings": {}
            }
    
    async def infer_test_data(self, field_schema: Dict[str, Any], context: Optional[Dict] = None) -> Any:
        """
        Generate realistic test data for a specific field
        
        Args:
            field_schema: Schema for the field (name, type, description, required, etc.)
            context: Additional context (endpoint purpose, other fields, etc.)
            
        Returns:
            Generated test data value
        """
        try:
            prompt = f"""
Generate realistic test data for this API field:

Field: {json.dumps(field_schema, indent=2)}
Context: {json.dumps(context or {}, indent=2)}

Consider:
- Field name and type
- Whether it's required or optional
- Description/purpose
- Common patterns (emails, phone numbers, addresses, IDs)

Return ONLY the generated value (as JSON if complex, or just the value):
"""
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Try to parse as JSON, otherwise return as string
            try:
                if result_text.startswith('{') or result_text.startswith('['):
                    return json.loads(result_text)
                elif result_text.startswith('"') and result_text.endswith('"'):
                    return result_text[1:-1]
                else:
                    return result_text
            except:
                return result_text
        
        except Exception as e:
            logger.error(f"Error inferring test data with Gemini: {e}")
            # Return default values based on type
            field_type = field_schema.get("type", "string").lower()
            if field_type in ["string", "str"]:
                return "test_value"
            elif field_type in ["number", "integer", "int"]:
                return 123
            elif field_type == "boolean":
                return True
            else:
                return None
    
    async def analyze_test_failure(
        self,
        endpoint: Dict[str, Any],
        test_data: Dict[str, Any],
        error_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze why a test failed and suggest fixes
        
        Args:
            endpoint: API endpoint specification
            test_data: Data used in the failed test
            error_response: Error response from API
            
        Returns:
            Analysis with suggested fixes
        """
        try:
            prompt = f"""
Analyze this API test failure:

Endpoint: {endpoint.get('method', 'GET')} {endpoint.get('path', '')}
Test Data: {json.dumps(test_data, indent=2)}
Error Response: {json.dumps(error_response, indent=2)}

Determine:
1. Root cause of failure
2. Which fields are problematic
3. Suggested fixes for test data
4. Whether this is a data issue or API issue

Return JSON:
{{
  "root_cause": "explanation",
  "problematic_fields": ["field1", "field2"],
  "suggested_fixes": {{"field1": "new_value"}},
  "is_api_issue": false,
  "retry_recommended": true
}}
"""
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(result_text)
            return analysis
        
        except Exception as e:
            logger.error(f"Error analyzing test failure with Gemini: {e}")
            return {
                "root_cause": "Unknown error",
                "problematic_fields": [],
                "suggested_fixes": {},
                "is_api_issue": False,
                "retry_recommended": False
            }

