"""
Workflow Orchestrator - Dynamically build and execute API workflows
Part of Universal Autonomous API Testing System

NO HARDCODED WORKFLOWS - Everything learned from patterns!
"""
import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime

from src.application.ai.learning.knowledge_graph import KnowledgeGraph
from src.application.ai.testing.smart_data_generator import SmartDataGenerator
from src.infrastructure.ai.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Orchestrate API workflows dynamically based on learned patterns
    
    Key Features:
    - NO hardcoded workflows
    - Queries knowledge graph for execution order
    - Extracts and passes data between steps
    - Adapts based on learned patterns
    - Handles errors intelligently
    """
    
    def __init__(self):
        self.knowledge_graph = KnowledgeGraph()
        self.data_generator = SmartDataGenerator()
        self.gemini = GeminiProvider()
    
    async def execute_workflow(
        self,
        partner_id: str,
        api_spec: Dict[str, Any],
        user_intent: str,
        base_url: str
    ) -> Dict[str, Any]:
        """
        Execute a workflow dynamically based on learned patterns
        
        Args:
            partner_id: Partner identifier
            api_spec: API specification with patterns and dependencies
            user_intent: What the user wants to do (e.g., "create a booking")
            base_url: API base URL
            
        Returns:
            Execution results
        """
        try:
            logger.info(f"[START] Executing workflow for: '{user_intent}'")
            
            # Step 1: Query knowledge graph for similar workflows
            similar_workflows = await self.knowledge_graph.query_similar_patterns(
                query=user_intent,
                partner_id=partner_id,
                pattern_type='workflow',
                limit=5
            )
            
            # Step 2: Build execution plan
            if similar_workflows:
                logger.info(f"[OK] Found {len(similar_workflows)} similar workflows")
                execution_plan = await self._build_plan_from_patterns(
                    similar_workflows,
                    api_spec,
                    user_intent
                )
            else:
                logger.info("[WARN] No similar workflows found, building from dependencies")
                execution_plan = await self._build_plan_from_dependencies(
                    api_spec,
                    user_intent
                )
            
            logger.info(f"[INFO] Execution plan: {len(execution_plan)} steps")
            
            # Step 3: Execute plan with adaptive data generation
            results = await self._execute_plan(
                execution_plan=execution_plan,
                api_spec=api_spec,
                base_url=base_url,
                partner_id=partner_id
            )
            
            # Step 4: Store successful pattern for future use
            if all(r.get('success', False) for r in results):
                await self._store_successful_workflow(
                    partner_id=partner_id,
                    user_intent=user_intent,
                    execution_plan=execution_plan,
                    results=results
                )
            
            return {
                'success': all(r.get('success', False) for r in results),
                'execution_plan': execution_plan,
                'results': results,
                'total_steps': len(execution_plan),
                'successful_steps': sum(1 for r in results if r.get('success', False)),
                'failed_steps': sum(1 for r in results if not r.get('success', True))
            }
        
        except Exception as e:
            logger.error(f"[ERROR] Error executing workflow: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_plan': [],
                'results': []
            }
    
    async def _build_plan_from_patterns(
        self,
        similar_workflows: List[Dict[str, Any]],
        api_spec: Dict[str, Any],
        user_intent: str
    ) -> List[Dict[str, Any]]:
        """Build execution plan from learned patterns"""
        try:
            # Use the most successful pattern as base
            best_pattern = max(
                similar_workflows,
                key=lambda x: x.get('success_rate', 0)
            )
            
            logger.info(f"[INFO] Using pattern: {best_pattern.get('description', 'Unknown')}")
            
            # Extract steps from pattern
            steps = best_pattern.get('steps', [])
            data_dependencies = best_pattern.get('data_dependencies', {})
            
            # Build execution plan
            execution_plan = []
            for i, endpoint_path in enumerate(steps):
                # Find endpoint details from API spec
                endpoint = self._find_endpoint(endpoint_path, api_spec)
                
                if endpoint:
                    execution_plan.append({
                        'step_number': i + 1,
                        'endpoint': endpoint_path,
                        'method': endpoint.get('method', 'GET'),
                        'summary': endpoint.get('summary', ''),
                        'data_dependencies': self._get_dependencies_for_step(
                            endpoint_path,
                            data_dependencies
                        ),
                        'schema': api_spec.get('schemas', {}).get(endpoint_path, {}),
                        'validation_rules': self._get_validation_rules_for_endpoint(
                            endpoint_path,
                            api_spec
                        )
                    })
            
            return execution_plan
        
        except Exception as e:
            logger.error(f"Error building plan from patterns: {e}")
            return []
    
    async def _build_plan_from_dependencies(
        self,
        api_spec: Dict[str, Any],
        user_intent: str
    ) -> List[Dict[str, Any]]:
        """Build execution plan from dependency graph"""
        try:
            # Use AI to build plan from dependencies
            prompt = f"""
Build an execution plan for this user intent: "{user_intent}"

API Specification:
Endpoints: {json.dumps(api_spec.get('endpoints', [])[:20], indent=2)}
Dependencies: {json.dumps(api_spec.get('dependency_graph', {}), indent=2)}
Patterns: {json.dumps(api_spec.get('workflow_patterns', [])[:5], indent=2)}

Build a step-by-step execution plan:
1. Determine which endpoints to call
2. Determine the order (respecting dependencies)
3. Identify data to extract and pass between steps

Output as JSON:
{{
  "plan": [
    {{
      "step_number": 1,
      "endpoint": "/api/login",
      "method": "POST",
      "summary": "Authenticate to get token",
      "extract": ["token", "vendorCode"],
      "pass_to_next": true
    }},
    {{
      "step_number": 2,
      "endpoint": "/api/orders",
      "method": "POST",
      "summary": "Create order",
      "uses_data_from": [1],
      "extract": ["orderId"]
    }}
  ]
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.3)
            result = self._parse_json_response(response)
            
            return result.get('plan', [])
        
        except Exception as e:
            logger.error(f"Error building plan from dependencies: {e}")
            return []
    
    async def _execute_plan(
        self,
        execution_plan: List[Dict[str, Any]],
        api_spec: Dict[str, Any],
        base_url: str,
        partner_id: str
    ) -> List[Dict[str, Any]]:
        """Execute the plan step by step"""
        results = []
        context = {}  # Store extracted data
        
        for step in execution_plan:
            try:
                logger.info(f"[INFO] Executing step {step.get('step_number')}: {step.get('endpoint')}")
                
                # Generate data for this step
                data = await self._generate_step_data(
                    step=step,
                    api_spec=api_spec,
                    context=context
                )
                
                # Execute the API call
                result = await self._execute_api_call(
                    endpoint=step.get('endpoint'),
                    method=step.get('method', 'GET'),
                    data=data,
                    base_url=base_url,
                    context=context
                )
                
                # Handle errors
                if not result.get('success', False):
                    # Query knowledge graph for error fix
                    error_fix = await self.knowledge_graph.query_error_fix(
                        error=result.get('error', ''),
                        partner_id=partner_id
                    )
                    
                    if error_fix:
                        logger.info("[FIX] Applying learned error fix")
                        result = await self._retry_with_fix(
                            step=step,
                            data=data,
                            fix=error_fix,
                            base_url=base_url,
                            context=context
                        )
                
                # Extract data for next steps
                if result.get('success', False):
                    extracted = self._extract_data(
                        response=result.get('response', {}),
                        extract_rules=step.get('data_dependencies', {})
                    )
                    context.update(extracted)
                    logger.info(f"[OK] Step {step.get('step_number')} completed")
                else:
                    logger.error(f"[ERROR] Step {step.get('step_number')} failed")
                
                results.append({
                    'step': step.get('step_number'),
                    'endpoint': step.get('endpoint'),
                    'success': result.get('success', False),
                    'response': result.get('response', {}),
                    'error': result.get('error'),
                    'extracted_data': extracted if result.get('success') else {}
                })
                
                # Stop if step failed and is critical
                if not result.get('success', False) and step.get('critical', True):
                    logger.error("[ERROR] Critical step failed, stopping execution")
                    break
            
            except Exception as e:
                logger.error(f"[ERROR] Error in step {step.get('step_number')}: {e}")
                results.append({
                    'step': step.get('step_number'),
                    'endpoint': step.get('endpoint'),
                    'success': False,
                    'error': str(e)
                })
                break
        
        return results
    
    async def _generate_step_data(
        self,
        step: Dict[str, Any],
        api_spec: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate data for a step using smart data generator"""
        try:
            schema = step.get('schema', {})
            validation_rules = step.get('validation_rules', [])
            
            # Generate base data
            data = await self.data_generator.generate_test_data(
                schema=schema,
                scenario_type='valid',
                context={
                    'endpoint': step.get('endpoint'),
                    'validation_rules': validation_rules
                }
            )
            
            # Apply data from context (from previous steps)
            data_dependencies = step.get('data_dependencies', {})
            for target_field, source_path in data_dependencies.items():
                if source_path in context:
                    data[target_field] = context[source_path]
            
            return data
        
        except Exception as e:
            logger.error(f"Error generating step data: {e}")
            return {}
    
    async def _execute_api_call(
        self,
        endpoint: str,
        method: str,
        data: Dict[str, Any],
        base_url: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an API call"""
        try:
            url = f"{base_url.rstrip('/')}{endpoint}"
            
            # Build headers
            headers = {'Content-Type': 'application/json'}
            
            # Add auth token if available
            if 'token' in context:
                headers['Authorization'] = f"Bearer {context['token']}"
            
            # Make request
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == 'GET':
                    response = await client.get(url, headers=headers, params=data)
                elif method.upper() == 'POST':
                    response = await client.post(url, headers=headers, json=data)
                elif method.upper() == 'PUT':
                    response = await client.put(url, headers=headers, json=data)
                elif method.upper() == 'PATCH':
                    response = await client.patch(url, headers=headers, json=data)
                elif method.upper() == 'DELETE':
                    response = await client.delete(url, headers=headers)
                else:
                    return {'success': False, 'error': f'Unsupported method: {method}'}
                
                # Parse response
                try:
                    response_data = response.json()
                except:
                    response_data = {'text': response.text}
                
                return {
                    'success': response.status_code < 400,
                    'status_code': response.status_code,
                    'response': response_data,
                    'error': None if response.status_code < 400 else response_data.get('message', 'Request failed')
                }
        
        except Exception as e:
            logger.error(f"Error executing API call: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _retry_with_fix(
        self,
        step: Dict[str, Any],
        data: Dict[str, Any],
        fix: Dict[str, Any],
        base_url: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Retry API call with learned fix"""
        try:
            # Apply fix to data
            fixed_data = self._apply_fix(data, fix.get('fix', {}))
            
            # Retry
            return await self._execute_api_call(
                endpoint=step.get('endpoint'),
                method=step.get('method', 'GET'),
                data=fixed_data,
                base_url=base_url,
                context=context
            )
        
        except Exception as e:
            logger.error(f"Error retrying with fix: {e}")
            return {'success': False, 'error': str(e)}
    
    def _apply_fix(
        self,
        data: Dict[str, Any],
        fix: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply a fix to data"""
        fixed_data = data.copy()
        
        for field, value in fix.items():
            fixed_data[field] = value
        
        return fixed_data
    
    def _extract_data(
        self,
        response: Dict[str, Any],
        extract_rules: Dict[str, str]
    ) -> Dict[str, Any]:
        """Extract data from response using JSONPath-like rules"""
        extracted = {}
        
        for key, path in extract_rules.items():
            try:
                # Simple JSONPath extraction
                value = response
                for part in path.split('.'):
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        break
                
                if value is not None:
                    extracted[key] = value
            except Exception as e:
                logger.error(f"Error extracting {key} from {path}: {e}")
        
        return extracted
    
    def _find_endpoint(
        self,
        endpoint_path: str,
        api_spec: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find endpoint details from API spec"""
        for endpoint in api_spec.get('endpoints', []):
            if endpoint.get('path') == endpoint_path:
                return endpoint
        return None
    
    def _get_dependencies_for_step(
        self,
        endpoint_path: str,
        data_dependencies: Dict[str, str]
    ) -> Dict[str, str]:
        """Get data dependencies for a specific step"""
        # Filter dependencies relevant to this endpoint
        return {
            k: v for k, v in data_dependencies.items()
            if endpoint_path in k or v.startswith(endpoint_path)
        }
    
    def _get_validation_rules_for_endpoint(
        self,
        endpoint_path: str,
        api_spec: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get validation rules for an endpoint"""
        all_rules = api_spec.get('validation_rules', [])
        
        # Filter rules relevant to this endpoint
        return [
            rule for rule in all_rules
            if endpoint_path in rule.get('applies_to', [])
        ]
    
    async def _store_successful_workflow(
        self,
        partner_id: str,
        user_intent: str,
        execution_plan: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ):
        """Store successful workflow in knowledge graph"""
        try:
            pattern = {
                'description': user_intent,
                'pattern_type': 'sequential',
                'steps': [step.get('endpoint') for step in execution_plan],
                'data_dependencies': {},
                'success': True,
                'execution_time': datetime.utcnow().isoformat()
            }
            
            await self.knowledge_graph.store_workflow_pattern(
                partner_id=partner_id,
                pattern=pattern,
                success_rate=1.0
            )
        
        except Exception as e:
            logger.error(f"Error storing successful workflow: {e}")
    
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

