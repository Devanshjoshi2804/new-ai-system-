"""
AI-powered workflow analyzer to understand business logic from API documentation
"""
import logging
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from src.domain.value_objects.api_schema import APISpecification
from src.infrastructure.ai.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class BusinessWorkflow(BaseModel):
    """Represents a business workflow"""
    name: str
    description: str
    endpoint_sequence: List[str]  # List of endpoint paths in order
    required_fields: Dict[str, List[str]]  # endpoint_path -> [field_names]
    optional_fields: Dict[str, List[str]]
    business_rules: List[str]
    error_handling: Dict[str, str]  # error_type -> handling_strategy
    prerequisites: List[str]  # What must be done before this workflow


class WorkflowAnalyzer:
    """
    Understands business workflows from API documentation
    
    Uses Google Gemini to analyze:
    - Booking flow (which endpoints in what order)
    - Tracking flow
    - Cancellation/modification flows
    - Required vs optional fields
    - Business rules and constraints
    """
    
    def __init__(self):
        self.gemini = GeminiProvider()
    
    async def analyze_workflows(
        self,
        api_spec: APISpecification,
        documentation_text: Optional[str] = None
    ) -> List[BusinessWorkflow]:
        """
        Analyze API specification and extract business workflows
        
        Args:
            api_spec: Parsed API specification
            documentation_text: Optional additional documentation text
            
        Returns:
            List of identified business workflows
        """
        try:
            logger.info(f"Analyzing workflows for API: {api_spec.title}")
            
            # Build analysis prompt
            prompt = self._build_analysis_prompt(api_spec, documentation_text)
            
            # Use Gemini for analysis
            response = await self.gemini.generate_content(
                prompt=prompt,
                temperature=0.3,  # Lower temperature for structured analysis
                system_instruction="""You are an expert API analyst specialized in understanding 
                logistics and shipping workflows. Analyze the provided API and identify all business 
                workflows, their sequences, and rules."""
            )
            
            # Parse response
            workflows = self._parse_workflows_response(response)
            
            logger.info(f"Identified {len(workflows)} workflows")
            
            return workflows
        
        except Exception as e:
            logger.error(f"Error analyzing workflows: {e}")
            # Return basic workflows as fallback
            return self._generate_basic_workflows(api_spec)
    
    def _build_analysis_prompt(
        self,
        api_spec: APISpecification,
        documentation_text: Optional[str]
    ) -> str:
        """Build comprehensive analysis prompt"""
        
        # Convert endpoints to readable format
        endpoints_info = []
        for endpoint in api_spec.endpoints:
            endpoint_info = {
                "method": endpoint.method.value,
                "path": endpoint.path,
                "summary": endpoint.summary,
                "description": endpoint.description,
                "parameters": [
                    {
                        "name": p.name,
                        "location": p.location.value,
                        "required": p.required,
                        "type": p.type
                    }
                    for p in endpoint.parameters
                ],
                "auth_required": endpoint.auth_required
            }
            endpoints_info.append(endpoint_info)
        
        prompt = f"""
Analyze this logistics/shipping API and identify all business workflows.

API Information:
- Title: {api_spec.title}
- Version: {api_spec.version}
- Base URL: {api_spec.base_url}
- Description: {api_spec.description}

Available Endpoints:
{json.dumps(endpoints_info, indent=2)}

Authentication:
{json.dumps(api_spec.auth.model_dump() if api_spec.auth else None, indent=2)}

"""
        
        if documentation_text:
            prompt += f"\nAdditional Documentation:\n{documentation_text}\n"
        
        prompt += """
Identify and describe ALL business workflows for this API. Common logistics workflows include:
1. Booking/Order Creation Flow
2. Shipment Tracking Flow
3. Rate Calculation Flow
4. Address Validation Flow
5. Order Cancellation/Modification Flow
6. Pickup Scheduling Flow
7. Label Generation Flow
8. Webhook Setup Flow

For EACH workflow, provide in JSON format:
{
  "workflows": [
    {
      "name": "Workflow name",
      "description": "What this workflow does",
      "endpoint_sequence": ["POST /endpoint1", "GET /endpoint2", ...],
      "required_fields": {
        "POST /endpoint1": ["field1", "field2"],
        "GET /endpoint2": ["field3"]
      },
      "optional_fields": {
        "POST /endpoint1": ["optional1"]
      },
      "business_rules": [
        "Rule 1: Description",
        "Rule 2: Description"
      ],
      "error_handling": {
        "invalid_address": "Validate address first using /validate endpoint",
        "insufficient_funds": "Check rate before booking"
      },
      "prerequisites": [
        "Must authenticate first",
        "Must validate pincode"
      ]
    }
  ]
}

Output ONLY valid JSON, no markdown formatting.
"""
        
        return prompt
    
    def _parse_workflows_response(self, response: str) -> List[BusinessWorkflow]:
        """Parse Gemini response into BusinessWorkflow objects"""
        try:
            # Clean response (remove markdown if present)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # Parse JSON
            data = json.loads(response)
            
            workflows = []
            for workflow_data in data.get("workflows", []):
                workflow = BusinessWorkflow(
                    name=workflow_data.get("name", "Unknown Workflow"),
                    description=workflow_data.get("description", ""),
                    endpoint_sequence=workflow_data.get("endpoint_sequence", []),
                    required_fields=workflow_data.get("required_fields", {}),
                    optional_fields=workflow_data.get("optional_fields", {}),
                    business_rules=workflow_data.get("business_rules", []),
                    error_handling=workflow_data.get("error_handling", {}),
                    prerequisites=workflow_data.get("prerequisites", [])
                )
                workflows.append(workflow)
            
            return workflows
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse workflow JSON: {e}")
            logger.debug(f"Response was: {response}")
            return []
        except Exception as e:
            logger.error(f"Error parsing workflows: {e}")
            return []
    
    def _generate_basic_workflows(self, api_spec: APISpecification) -> List[BusinessWorkflow]:
        """
        Generate basic workflows based on common patterns
        (fallback when AI analysis fails)
        """
        workflows = []
        
        # Look for common patterns in endpoints
        booking_endpoints = [e for e in api_spec.endpoints if any(
            word in e.path.lower() or (e.summary and word in e.summary.lower())
            for word in ["order", "booking", "shipment", "create"]
        )]
        
        if booking_endpoints:
            workflows.append(BusinessWorkflow(
                name="Booking Creation",
                description="Create a new shipment booking",
                endpoint_sequence=[f"{e.method.value} {e.path}" for e in booking_endpoints],
                required_fields={},
                optional_fields={},
                business_rules=["Validate addresses before booking"],
                error_handling={},
                prerequisites=["Authentication required"]
            ))
        
        # Tracking workflow
        tracking_endpoints = [e for e in api_spec.endpoints if any(
            word in e.path.lower() or (e.summary and word in e.summary.lower())
            for word in ["track", "status", "shipment"]
        ) and e.method.value == "GET"]
        
        if tracking_endpoints:
            workflows.append(BusinessWorkflow(
                name="Shipment Tracking",
                description="Track shipment status",
                endpoint_sequence=[f"{e.method.value} {e.path}" for e in tracking_endpoints],
                required_fields={},
                optional_fields={},
                business_rules=[],
                error_handling={},
                prerequisites=["Valid tracking/AWB number"]
            ))
        
        return workflows
    
    async def analyze_single_workflow(
        self,
        workflow_name: str,
        api_spec: APISpecification
    ) -> Optional[BusinessWorkflow]:
        """
        Analyze a specific workflow in detail
        """
        prompt = f"""
Analyze the "{workflow_name}" workflow for this API.

API Endpoints:
{json.dumps([{
    "method": e.method.value,
    "path": e.path,
    "summary": e.summary
} for e in api_spec.endpoints], indent=2)}

Provide detailed analysis of the {workflow_name} workflow including:
- Exact sequence of API calls
- All required and optional fields
- Business rules and validation
- Error handling strategies
- Prerequisites

Output as JSON matching the BusinessWorkflow schema.
"""
        
        try:
            response = await self.gemini.generate_content(prompt, temperature=0.2)
            workflows = self._parse_workflows_response(f'{{"workflows": [{response}]}}')
            return workflows[0] if workflows else None
        except Exception as e:
            logger.error(f"Error analyzing single workflow: {e}")
            return None


