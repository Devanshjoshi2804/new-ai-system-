"""
Autonomous API Executor
Executes API operations based on natural language commands
"""
import json
import logging
import httpx
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END

from src.application.ai.execution.intent_analyzer import IntentAnalyzer
from src.infrastructure.ai.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class ExecutionState(TypedDict):
    """State for autonomous execution"""
    user_message: str
    api_spec: Dict[str, Any]
    base_url: str
    intent: Dict[str, Any]
    execution_plan: List[Dict[str, Any]]
    current_step: int
    collected_data: Dict[str, Any]
    api_responses: List[Dict[str, Any]]
    auth_token: Optional[str]
    final_response: str
    execution_complete: bool
    error: Optional[str]
    context: Dict[str, Any]


async def understand_intent_node(state: ExecutionState) -> ExecutionState:
    """Understand what user wants to do"""
    try:
        logger.info("[INFO] Understanding user intent...")
        
        analyzer = IntentAnalyzer()
        intent = await analyzer.analyze_intent(
            user_message=state['user_message'],
            api_spec=state['api_spec'],
            context=state.get('context', {})
        )
        
        # Check if clarification needed
        if intent.get('clarification_needed'):
            logger.info("[INFO] Clarification needed from user")
            return {
                **state,
                "intent": intent,
                "execution_complete": True,
                "final_response": f"I need more information: {', '.join([q['question'] for q in intent.get('missing_data', [])])}"
            }
        
        execution_plan = intent.get('execution_plan', [])
        
        logger.info(f"[OK] Intent understood: {intent.get('intent')}")
        logger.info(f"[INFO] Execution plan: {len(execution_plan)} steps")
        
        return {
            **state,
            "intent": intent,
            "execution_plan": execution_plan,
            "collected_data": intent.get('extracted_data', {})
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Error understanding intent: {e}")
        return {
            **state,
            "error": str(e),
            "execution_complete": True,
            "final_response": "I couldn't understand your request. Please try rephrasing."
        }


async def collect_missing_data_node(state: ExecutionState) -> ExecutionState:
    """Try to infer or collect missing data"""
    try:
        missing = state['intent'].get('missing_data', [])
        
        if not missing:
            logger.info("[OK] All required data available")
            return state
        
        logger.info(f"[SEARCH] Attempting to infer {len(missing)} missing fields...")
        
        # Try to infer from context or use defaults
        gemini = GeminiProvider()
        
        prompt = f"""
Try to infer or provide reasonable defaults for missing data:

**User Command:** "{state['user_message']}"

**Already Collected Data:**
{json.dumps(state['collected_data'], indent=2)}

**Missing Data:**
{json.dumps(missing, indent=2)}

**Context:**
{json.dumps(state.get('context', {}), indent=2)}

**Your Task:**
For each missing field:
1. Try to infer from context or command
2. If can't infer and field is optional, provide reasonable default
3. If can't infer and field is required, mark as "needs_user_input"

Output as JSON:
{{
  "inferred_data": {{
    "field1": "inferred_value",
    "field2": "default_value"
  }},
  "still_missing": [
    {{
      "field": "field3",
      "question": "What is field3?"
    }}
  ]
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
        
        response = await gemini.generate_content(prompt, temperature=0.5)
        
        # Parse JSON from response
        inference_text = response.strip()
        if "```json" in inference_text:
            inference_text = inference_text.split("```json")[1].split("```")[0].strip()
        elif "```" in inference_text:
            inference_text = inference_text.split("```")[1].split("```")[0].strip()
        
        inference = json.loads(inference_text)
        
        # Update collected data
        collected = {**state['collected_data'], **inference.get('inferred_data', {})}
        
        still_missing = inference.get('still_missing', [])
        
        if still_missing:
            logger.info(f"[INFO] Still missing {len(still_missing)} required fields")
            questions = [m['question'] for m in still_missing]
            return {
                **state,
                "collected_data": collected,
                "execution_complete": True,
                "final_response": f"I need more information: {', '.join(questions)}"
            }
        
        logger.info(f"[OK] All data collected/inferred")
        
        return {**state, "collected_data": collected}
    
    except Exception as e:
        logger.error(f"[ERROR] Error collecting data: {e}")
        return state


async def authenticate_node(state: ExecutionState) -> ExecutionState:
    """Authenticate if needed"""
    try:
        # Check if authentication is in execution plan
        auth_step = None
        for step in state['execution_plan']:
            if step.get('action') in ['authenticate', 'login']:
                auth_step = step
                break
        
        if not auth_step:
            logger.info("ℹ[INFO] No authentication required")
            return state
        
        logger.info("[INFO] Authenticating...")
        
        # Get auth config
        auth_config = state['api_spec'].get('auth_config', {})
        credentials = auth_config.get('test_credentials', {})
        
        if not credentials:
            logger.warning("[WARN] No test credentials available")
            return state
        
        # Call auth endpoint
        endpoint = auth_step.get('endpoint', '/api/login')
        method = auth_step.get('method', 'POST')
        url = f"{state['base_url']}{endpoint}"
        
        logger.info(f"[INFO] Calling auth endpoint: {method} {url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == 'POST':
                response = await client.post(url, json=credentials)
            else:
                response = await client.get(url, params=credentials)
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                
                # Extract token and other data
                extracts = auth_step.get('extracts', {})
                collected = state['collected_data'].copy()
                
                for key, path in extracts.items():
                    value = extract_value_from_path(response_data, path)
                    collected[key] = value
                    logger.info(f"[INFO] Extracted {key} = {value}")
                
                # Get token
                token = collected.get('token')
                
                logger.info("[OK] Authentication successful")
                
                return {
                    **state,
                    "auth_token": token,
                    "collected_data": collected,
                    "api_responses": [{
                        'step': 'authenticate',
                        'endpoint': endpoint,
                        'success': True,
                        'response': response_data
                    }]
                }
            else:
                logger.error(f"[ERROR] Authentication failed: {response.status_code}")
                return {
                    **state,
                    "error": f"Authentication failed: {response.status_code}",
                    "execution_complete": True,
                    "final_response": "Authentication failed. Please check your credentials."
                }
    
    except Exception as e:
        logger.error(f"[ERROR] Error in authentication: {e}")
        return {
            **state,
            "error": str(e),
            "execution_complete": True,
            "final_response": f"Authentication error: {str(e)}"
        }


async def execute_api_call_node(state: ExecutionState) -> ExecutionState:
    """Execute current step in execution plan"""
    try:
        current_idx = state['current_step']
        
        # Skip authentication step if already done
        step = state['execution_plan'][current_idx]
        if step.get('action') in ['authenticate', 'login'] and state.get('auth_token'):
            logger.info("⏭[INFO] Skipping authentication (already done)")
            return state
        
        logger.info(f"[INFO] Executing step {current_idx + 1}/{len(state['execution_plan'])}: {step.get('description', 'Unknown')}")
        
        # Prepare request
        endpoint = step.get('endpoint', '')
        method = step.get('method', 'GET').upper()
        
        # Substitute variables in endpoint
        endpoint = substitute_variables(endpoint, state['collected_data'])
        
        # Prepare data
        data = step.get('data', {})
        if isinstance(data, dict):
            data = substitute_variables(data, state['collected_data'])
        
        # Prepare headers
        headers = {}
        if state.get('auth_token'):
            auth_config = state['api_spec'].get('auth_config', {})
            header_name = auth_config.get('header_name', 'Authorization')
            token_format = auth_config.get('token_format', 'Bearer {token}')
            headers[header_name] = token_format.replace('{token}', state['auth_token']).replace('{{token}}', state['auth_token'])
        
        url = f"{state['base_url']}{endpoint}"
        
        logger.info(f"[INFO] {method} {url}")
        logger.debug(f"[INFO] Data: {json.dumps(data, indent=2)}")
        
        # Execute request
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == 'GET':
                response = await client.get(url, params=data, headers=headers)
            elif method == 'POST':
                response = await client.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = await client.put(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = await client.patch(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {'text': response.text}
            
            logger.info(f"[INFO] Response: {response.status_code}")
            logger.debug(f"[INFO] Data: {json.dumps(response_data, indent=2)[:500]}")
            
            # Check if successful
            success = response.status_code in [200, 201, 202, 204]
            
            # Extract data from response
            if success and step.get('extracts'):
                collected = state['collected_data'].copy()
                for key, path in step['extracts'].items():
                    value = extract_value_from_path(response_data, path)
                    collected[key] = value
                    logger.info(f"[INFO] Extracted {key} = {value}")
                state = {**state, "collected_data": collected}
            
            # Record response
            api_responses = state['api_responses'] + [{
                'step': current_idx + 1,
                'action': step.get('action', 'unknown'),
                'endpoint': endpoint,
                'method': method,
                'success': success,
                'status_code': response.status_code,
                'response': response_data,
                'timestamp': datetime.utcnow().isoformat()
            }]
            
            if not success:
                logger.error(f"[ERROR] API call failed: {response.status_code}")
                return {
                    **state,
                    "api_responses": api_responses,
                    "error": f"API call failed: {response.status_code}",
                    "execution_complete": True,
                    "final_response": f"Operation failed: {response_data.get('error', 'Unknown error')}"
                }
            
            return {**state, "api_responses": api_responses}
    
    except Exception as e:
        logger.error(f"[ERROR] Error executing API call: {e}")
        return {
            **state,
            "error": str(e),
            "execution_complete": True,
            "final_response": f"Error executing operation: {str(e)}"
        }


async def generate_response_node(state: ExecutionState) -> ExecutionState:
    """Generate natural language response for user"""
    try:
        logger.info("[INFO] Generating user response...")
        
        gemini = GeminiProvider()
        
        prompt = f"""
Generate a natural, friendly response for the user:

**User Asked:** "{state['user_message']}"

**What We Did:**
{json.dumps([{
    'step': r.get('step'),
    'action': r.get('action'),
    'success': r.get('success'),
    'response': str(r.get('response', {}))[:200]
} for r in state['api_responses']], indent=2)}

**Final Data:**
{json.dumps(state['collected_data'], indent=2)}

**Expected Outcome:** {state['intent'].get('expected_outcome', 'Operation completed')}

**Your Task:**
Generate a natural, conversational response that:
1. Confirms what was done
2. Includes relevant details (IDs, numbers, confirmation codes)
3. Is concise but informative
4. Is friendly and helpful

Examples:
- "[OK] Your booking has been created! Booking ID: BK12345, AWB Number: AWB789. Pickup is scheduled for tomorrow."
- "[OK] I found 3 active shipments: AWB123 (In Transit), AWB456 (Delivered), AWB789 (Pending Pickup)."
- "[OK] Booking #12345 has been cancelled successfully. Refund will be processed in 3-5 business days."

Output as plain text (not JSON), 2-3 sentences max.
"""
        
        response = await gemini.generate_content(prompt, temperature=0.7)
        final_response = response.strip()
        
        # Remove any markdown formatting
        final_response = final_response.replace('```', '').replace('**', '')
        
        logger.info(f"[OK] Response generated: {final_response[:100]}...")
        
        return {
            **state,
            "final_response": final_response,
            "execution_complete": True
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Error generating response: {e}")
        return {
            **state,
            "final_response": "Operation completed successfully.",
            "execution_complete": True
        }


def has_more_steps(state: ExecutionState) -> str:
    """Check if there are more steps to execute"""
    if state.get('error') or state.get('execution_complete'):
        return "generate_response"
    
    if state['current_step'] + 1 < len(state['execution_plan']):
        return "execute_api_call"
    
    return "generate_response"


async def next_step_node(state: ExecutionState) -> ExecutionState:
    """Move to next step"""
    return {**state, "current_step": state['current_step'] + 1}


def build_autonomous_execution_graph() -> StateGraph:
    """Build autonomous API execution graph"""
    logger.info("[INFO] Building autonomous execution graph...")
    
    workflow = StateGraph(ExecutionState)
    
    # Add nodes
    workflow.add_node("understand_intent", understand_intent_node)
    workflow.add_node("collect_data", collect_missing_data_node)
    workflow.add_node("authenticate", authenticate_node)
    workflow.add_node("execute_api_call", execute_api_call_node)
    workflow.add_node("next_step", next_step_node)
    workflow.add_node("generate_response", generate_response_node)
    
    # Define flow
    workflow.set_entry_point("understand_intent")
    workflow.add_edge("understand_intent", "collect_data")
    workflow.add_edge("collect_data", "authenticate")
    workflow.add_edge("authenticate", "execute_api_call")
    
    workflow.add_conditional_edges(
        "execute_api_call",
        has_more_steps,
        {
            "execute_api_call": "next_step",
            "generate_response": "generate_response"
        }
    )
    
    workflow.add_edge("next_step", "execute_api_call")
    workflow.add_edge("generate_response", END)
    
    logger.info("[OK] Autonomous execution graph built")
    
    return workflow.compile()


# Helper functions

def extract_value_from_path(data: Dict[str, Any], path: str) -> Any:
    """Extract value from nested dict using dot notation path"""
    try:
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    except:
        return None


def substitute_variables(obj: Any, variables: Dict[str, Any]) -> Any:
    """Substitute variables in strings, recursively"""
    if isinstance(obj, str):
        # Replace {{variable}} with value
        for key, value in variables.items():
            obj = obj.replace(f"{{{{{key}}}}}", str(value))
            obj = obj.replace(f"{{{key}}}", str(value))
        return obj
    elif isinstance(obj, dict):
        return {k: substitute_variables(v, variables) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [substitute_variables(item, variables) for item in obj]
    else:
        return obj


class AutonomousExecutor:
    """Main class for autonomous API execution"""
    
    def __init__(self):
        self.graph = build_autonomous_execution_graph()
    
    async def execute_command(
        self,
        user_message: str,
        api_spec: Dict[str, Any],
        base_url: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute natural language command
        
        Args:
            user_message: User's natural language command
            api_spec: Complete API specification
            base_url: Base URL for API
            context: Optional context from previous interactions
            
        Returns:
            Execution result with response
        """
        try:
            logger.info(f"[START] Executing command: '{user_message}'")
            
            initial_state: ExecutionState = {
                'user_message': user_message,
                'api_spec': api_spec,
                'base_url': base_url,
                'intent': {},
                'execution_plan': [],
                'current_step': 0,
                'collected_data': {},
                'api_responses': [],
                'auth_token': None,
                'final_response': '',
                'execution_complete': False,
                'error': None,
                'context': context or {}
            }
            
            result = await self.graph.ainvoke(initial_state)
            
            return {
                'success': result.get('execution_complete', False) and not result.get('error'),
                'response': result.get('final_response', ''),
                'intent': result.get('intent', {}),
                'api_calls_made': len(result.get('api_responses', [])),
                'details': result.get('api_responses', []),
                'collected_data': result.get('collected_data', {}),
                'error': result.get('error')
            }
        
        except Exception as e:
            logger.error(f"[ERROR] Error in autonomous execution: {e}", exc_info=True)
            return {
                'success': False,
                'response': f"I encountered an error: {str(e)}",
                'intent': {},
                'api_calls_made': 0,
                'details': [],
                'collected_data': {},
                'error': str(e)
            }

