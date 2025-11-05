"""
Workflow Extractor - AI-Powered Complete Workflow Understanding
REVOLUTIONARY APPROACH: One AI call to understand everything
"""
import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EndpointSpec:
    """Complete specification for an endpoint"""
    path: str
    method: str
    purpose: str
    required_fields: Dict[str, Any]  # field_name -> {type, format, example}
    optional_fields: Dict[str, Any]
    dependencies: List[str]  # Endpoints this depends on
    provides_data: Dict[str, str]  # What data this endpoint provides (field -> path_in_response)
    auth_required: bool
    execution_order: int


@dataclass
class AuthenticationFlow:
    """Complete authentication workflow"""
    required: bool
    signup_endpoint: Optional[str]
    login_endpoint: Optional[str]
    token_location: str  # Path in response (e.g., "data.token")
    token_header: str  # Header name (e.g., "Authorization")
    token_format: str  # Format (e.g., "Bearer {token}")
    dependencies: List[str]  # What endpoints must run first


@dataclass
class CompleteWorkflow:
    """Complete API workflow understanding"""
    authentication: AuthenticationFlow
    endpoints: Dict[str, EndpointSpec]  # path -> spec
    execution_order: List[str]  # Optimal test order
    data_flow: Dict[str, Dict[str, str]]  # endpoint -> {field -> source_endpoint.response_path}
    common_fields: Dict[str, Any]  # Fields used across multiple endpoints


class WorkflowExtractor:
    """
    Extracts complete workflow understanding using ONE AI call
    
    This replaces:
    - dependency_analyzer.py (regex-based, brittle)
    - Multiple AI calls for different aspects
    - Guessing and assumptions
    
    Philosophy:
    - ONE comprehensive analysis
    - Extract EVERYTHING in one shot
    - Store in Vector DB
    - Use for all subsequent test generation
    """
    
    def __init__(self, ai_provider, vector_store=None):
        """
        Initialize workflow extractor
        
        Args:
            ai_provider: AI provider (Groq/Gemini/Mistral)
            vector_store: Optional Vector DB for storing workflow knowledge
        """
        self.ai_provider = ai_provider
        self.vector_store = vector_store
        self.cached_workflows = {}  # Cache by doc_id
    
    async def extract_complete_workflow(
        self,
        endpoints: List[Dict[str, Any]],
        documentation_text: str,
        doc_id: Optional[str] = None
    ) -> CompleteWorkflow:
        """
        Extract complete workflow in ONE AI call
        
        This is the magic - instead of complex regex and multiple AI calls,
        we ask the AI to understand EVERYTHING at once.
        
        Args:
            endpoints: List of endpoint specifications
            documentation_text: Full API documentation
            doc_id: Optional doc ID for caching
            
        Returns:
            Complete workflow understanding
        """
        # Check cache first
        if doc_id and doc_id in self.cached_workflows:
            logger.info(f"[OK] Using cached workflow for doc {doc_id}")
            return self.cached_workflows[doc_id]
        
        logger.info(f"[INFO] Extracting complete workflow from {len(endpoints)} endpoints")
        start_time = datetime.utcnow()
        
        # Build the ONE comprehensive prompt
        prompt = self._build_comprehensive_prompt(endpoints, documentation_text)
        
        # ONE AI call to understand everything
        try:
            response = await self.ai_provider.generate_content(
                prompt=prompt,
                temperature=0.1,  # Low temp for accuracy
                system_prompt="""You are an expert API analyst. Analyze the ENTIRE workflow and return comprehensive, accurate information.
                
CRITICAL RULES:
1. Extract REAL values from documentation, not placeholders
2. Identify ALL required fields for each endpoint
3. Map complete authentication flow (signup -> login -> use token)
4. Identify data dependencies (which endpoint needs output from which)
5. Return valid JSON only, no markdown
6. If unsure, mark with "UNKNOWN" not fake values"""
            )
            
            # Parse the comprehensive response
            workflow = self._parse_workflow_response(response, endpoints)
            
            # Store in Vector DB
            if self.vector_store and doc_id:
                await self._store_workflow_in_vector_db(workflow, doc_id)
            
            # Cache it
            if doc_id:
                self.cached_workflows[doc_id] = workflow
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"[OK] Workflow extracted in {duration:.2f}s")
            logger.info(f"   • Authentication: {workflow.authentication.required}")
            logger.info(f"   • Endpoints: {len(workflow.endpoints)}")
            logger.info(f"   • Execution order: {len(workflow.execution_order)} steps")
            logger.info(f"   • Data flows: {len(workflow.data_flow)} mappings")
            
            return workflow
        
        except Exception as e:
            logger.error(f"[ERROR] Workflow extraction failed: {e}", exc_info=True)
            # Return fallback workflow
            return self._create_fallback_workflow(endpoints)
    
    def _build_comprehensive_prompt(
        self,
        endpoints: List[Dict[str, Any]],
        documentation: str
    ) -> str:
        """
        Build ONE comprehensive prompt that extracts everything
        """
        # Summarize endpoints
        endpoint_summary = []
        for ep in endpoints:
            ep_info = {
                "path": ep.get("path", ""),
                "method": ep.get("method", ""),
                "summary": ep.get("summary", ""),
                "parameters": [p.get("name") for p in ep.get("parameters", [])],
                "request_body": ep.get("request_body_schema", {}).get("properties", {}).keys() if ep.get("request_body_schema") else []
            }
            endpoint_summary.append(ep_info)
        
        prompt = f"""Analyze this complete API workflow and extract ALL information in ONE comprehensive analysis.

# ENDPOINTS
{json.dumps(endpoint_summary, indent=2)}

# DOCUMENTATION
{documentation[:15000]}

# TASK
Extract and return a COMPLETE JSON object with:

1. **Authentication Flow**: Does the API require authentication? If yes:
   - signup_endpoint: Which endpoint to create user (or null)
   - login_endpoint: Which endpoint to get auth token (or null)
   - token_location: JSON path in login response (e.g., "data.token")
   - token_header: Header name for auth (e.g., "Authorization")
   - token_format: Token format (e.g., "Bearer {{token}}")

2. **Endpoint Specifications**: For EACH endpoint, provide:
   - purpose: What it does in 1 sentence
   - required_fields: ALL required fields with {{name, type, format, example_value}}
   - optional_fields: Optional fields with same structure
   - dependencies: List of endpoint paths that must execute first
   - provides_data: What data this endpoint returns that others need {{"field_name": "path.in.response"}}
   - auth_required: true/false

3. **Data Flow**: Map how data flows between endpoints
   - For each endpoint, which fields come from which previous endpoint's response

4. **Execution Order**: Optimal order to test endpoints (as array of paths)

5. **Common Fields**: Fields that appear in multiple endpoints

# OUTPUT FORMAT
Return ONLY valid JSON in this exact structure:
{{
  "authentication": {{
    "required": true/false,
    "signup_endpoint": "/path/to/signup" or null,
    "login_endpoint": "/path/to/login" or null,
    "token_location": "data.token",
    "token_header": "Authorization",
    "token_format": "Bearer {{token}}"
  }},
  "endpoints": {{
    "/api/endpoint": {{
      "method": "POST",
      "purpose": "Clear purpose",
      "required_fields": {{
        "fieldName": {{
          "type": "string",
          "format": "email",
          "example_value": "actual@example.com"
        }}
      }},
      "optional_fields": {{}},
      "dependencies": ["/api/other"],
      "provides_data": {{
        "userId": "data.userId",
        "token": "data.token"
      }},
      "auth_required": false,
      "execution_order": 0
    }}
  }},
  "data_flow": {{
    "/api/dependent": {{
      "token": "/api/login.data.token",
      "userId": "/api/signup.data.userId"
    }}
  }},
  "execution_order": ["/api/signup", "/api/login", "/api/use"],
  "common_fields": {{
    "token": {{"type": "string", "source": "login_response"}}
  }}
}}

CRITICAL RULES:
- Extract REAL values from documentation
- ALL required fields must be identified
- Dependencies must be accurate
- Execution order must respect dependencies
- NO placeholders or fake values
- Return ONLY the JSON object, no markdown formatting
"""
        return prompt
    
    def _parse_workflow_response(
        self,
        response: str,
        endpoints: List[Dict[str, Any]]
    ) -> CompleteWorkflow:
        """
        Parse AI response into CompleteWorkflow
        """
        try:
            # Clean response (remove markdown if present)
            response_clean = response.strip()
            if response_clean.startswith("```"):
                # Remove markdown code blocks
                lines = response_clean.split("\n")
                response_clean = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                if response_clean.startswith("json"):
                    response_clean = response_clean[4:].strip()
            
            # Parse JSON
            data = json.loads(response_clean)
            
            # Build AuthenticationFlow
            auth_data = data.get("authentication", {})
            authentication = AuthenticationFlow(
                required=auth_data.get("required", False),
                signup_endpoint=auth_data.get("signup_endpoint"),
                login_endpoint=auth_data.get("login_endpoint"),
                token_location=auth_data.get("token_location", "token"),
                token_header=auth_data.get("token_header", "Authorization"),
                token_format=auth_data.get("token_format", "Bearer {token}"),
                dependencies=[]
            )
            
            # Build EndpointSpec for each endpoint
            endpoint_specs = {}
            endpoints_data = data.get("endpoints", {})
            
            for path, spec_data in endpoints_data.items():
                endpoint_specs[path] = EndpointSpec(
                    path=path,
                    method=spec_data.get("method", "GET"),
                    purpose=spec_data.get("purpose", ""),
                    required_fields=spec_data.get("required_fields", {}),
                    optional_fields=spec_data.get("optional_fields", {}),
                    dependencies=spec_data.get("dependencies", []),
                    provides_data=spec_data.get("provides_data", {}),
                    auth_required=spec_data.get("auth_required", False),
                    execution_order=spec_data.get("execution_order", 999)
                )
            
            # Build workflow
            workflow = CompleteWorkflow(
                authentication=authentication,
                endpoints=endpoint_specs,
                execution_order=data.get("execution_order", []),
                data_flow=data.get("data_flow", {}),
                common_fields=data.get("common_fields", {})
            )
            
            logger.info(f"[OK] Successfully parsed workflow response")
            return workflow
        
        except json.JSONDecodeError as e:
            logger.error(f"[ERROR] Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return self._create_fallback_workflow(endpoints)
        except Exception as e:
            logger.error(f"[ERROR] Failed to parse workflow response: {e}", exc_info=True)
            return self._create_fallback_workflow(endpoints)
    
    def _create_fallback_workflow(
        self,
        endpoints: List[Dict[str, Any]]
    ) -> CompleteWorkflow:
        """
        Create a basic fallback workflow when AI extraction fails
        """
        logger.warning("[WARN]  Using fallback workflow (AI extraction failed)")
        
        # Simple fallback: no auth, all endpoints independent
        endpoint_specs = {}
        execution_order = []
        
        for idx, ep in enumerate(endpoints):
            path = ep.get("path", f"/endpoint_{idx}")
            method = ep.get("method", "GET")
            
            # Extract required fields from schema
            required_fields = {}
            schema = ep.get("request_body_schema", {})
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            for field in required:
                if field in properties:
                    required_fields[field] = {
                        "type": properties[field].get("type", "string"),
                        "format": properties[field].get("format", ""),
                        "example_value": properties[field].get("example", "")
                    }
            
            endpoint_specs[path] = EndpointSpec(
                path=path,
                method=method,
                purpose=ep.get("summary", "No description"),
                required_fields=required_fields,
                optional_fields={},
                dependencies=[],
                provides_data={},
                auth_required=False,
                execution_order=idx
            )
            execution_order.append(path)
        
        return CompleteWorkflow(
            authentication=AuthenticationFlow(
                required=False,
                signup_endpoint=None,
                login_endpoint=None,
                token_location="token",
                token_header="Authorization",
                token_format="Bearer {token}",
                dependencies=[]
            ),
            endpoints=endpoint_specs,
            execution_order=execution_order,
            data_flow={},
            common_fields={}
        )
    
    async def _store_workflow_in_vector_db(
        self,
        workflow: CompleteWorkflow,
        doc_id: str
    ):
        """
        Store workflow in Vector DB for fast retrieval
        """
        if not self.vector_store:
            return
        
        try:
            # Store complete workflow as JSON
            workflow_json = {
                "authentication": {
                    "required": workflow.authentication.required,
                    "signup_endpoint": workflow.authentication.signup_endpoint,
                    "login_endpoint": workflow.authentication.login_endpoint,
                    "token_location": workflow.authentication.token_location,
                    "token_header": workflow.authentication.token_header,
                    "token_format": workflow.authentication.token_format
                },
                "endpoints": {
                    path: {
                        "method": spec.method,
                        "purpose": spec.purpose,
                        "required_fields": spec.required_fields,
                        "optional_fields": spec.optional_fields,
                        "dependencies": spec.dependencies,
                        "provides_data": spec.provides_data,
                        "auth_required": spec.auth_required,
                        "execution_order": spec.execution_order
                    }
                    for path, spec in workflow.endpoints.items()
                },
                "execution_order": workflow.execution_order,
                "data_flow": workflow.data_flow,
                "common_fields": workflow.common_fields
            }
            
            # Store in vector DB (implementation depends on your vector store)
            # This would be stored with embeddings for semantic search
            await self.vector_store.store_workflow(doc_id, workflow_json)
            
            logger.info(f"[OK] Workflow stored in Vector DB for doc {doc_id}")
        
        except Exception as e:
            logger.warning(f"[WARN]  Failed to store workflow in Vector DB: {e}")
    
    def get_endpoint_requirements(
        self,
        workflow: CompleteWorkflow,
        endpoint_path: str
    ) -> Dict[str, Any]:
        """
        Get complete requirements for testing an endpoint
        
        Returns everything needed:
        - Required fields
        - Where to get dependency data
        - Auth requirements
        - Execution prerequisites
        """
        if endpoint_path not in workflow.endpoints:
            logger.warning(f"[WARN]  Endpoint {endpoint_path} not found in workflow")
            return {}
        
        spec = workflow.endpoints[endpoint_path]
        data_flow = workflow.data_flow.get(endpoint_path, {})
        
        return {
            "required_fields": spec.required_fields,
            "optional_fields": spec.optional_fields,
            "data_sources": data_flow,  # Where each field comes from
            "dependencies": spec.dependencies,  # Must run these first
            "auth_required": spec.auth_required,
            "auth_setup": workflow.authentication if spec.auth_required else None,
            "execution_order": spec.execution_order,
            "purpose": spec.purpose
        }

