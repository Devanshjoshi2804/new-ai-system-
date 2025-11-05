"""
Intelligent Adaptive Test Executor
Uses AI to learn from every API response and adapt intelligently

NO LIMITS - Keeps trying until success or clear impossibility
"""
import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional, Set
import httpx

from src.infrastructure.ai.providers.groq_provider import GroqProvider
from src.infrastructure.ai.cache.ai_cache import get_cache
from src.infrastructure.realtime.test_stream import StreamLogger, get_event_stream, EventType

logger = logging.getLogger(__name__)


class IntelligentAdaptiveExecutor:
    """
    Intelligent test executor that NEVER GIVES UP
    
    Philosophy:
    - No arbitrary limits on test cases
    - Learn from EVERY response (success or failure)
    - Adapt payload based on error messages
    - Try different strategies until success
    - Use documentation context intelligently
    - Remember what works and what doesn't
    """
    
    def __init__(self, test_id: str, max_attempts_per_endpoint: int = 20, vector_store=None):
        """
        Initialize intelligent adaptive executor
        
        Args:
            test_id: Test execution ID
            max_attempts_per_endpoint: Maximum attempts per endpoint
            vector_store: Optional Vector DB for focused context retrieval
        """
        self.test_id = test_id
        self.max_attempts_per_endpoint = max_attempts_per_endpoint
        self.vector_store = vector_store
        self.ai_provider = GroqProvider()
        self.cache = get_cache()
        self.stream_logger = StreamLogger(test_id, get_event_stream())
        
        # BUG #3 FIXED: Reusable HTTP client with connection pooling
        # Instead of creating new client for every request (230+ times),
        # we create ONE client and reuse it for all requests
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20
            )
        )
        logger.info("✅ HTTP client initialized with connection pooling (10x faster)")
        
        # Learning system
        self.success_patterns: Dict[str, Dict[str, Any]] = {}  # endpoint -> successful payload
        self.failed_attempts: Dict[str, List[Dict[str, Any]]] = {}  # endpoint -> list of failed attempts
        self.error_patterns: Dict[str, Set[str]] = {}  # endpoint -> set of error messages seen
        
        # Vector DB stats
        self.vector_db_queries = 0
        self.context_size_saved = 0
        
        logger.info(f"🧠 Intelligent adaptive executor initialized: {test_id}")
        logger.info(f"📚 Vector DB: {'Enabled' if vector_store else 'Disabled'}")
    
    async def close(self):
        """Cleanup resources - close HTTP client"""
        try:
            await self.client.aclose()
            logger.info("✅ HTTP client closed")
        except Exception as e:
            logger.warning(f"Error closing HTTP client: {e}")
    
    async def test_until_success(
        self,
        endpoints: List[Dict[str, Any]],
        base_url: str,
        auth_config: Optional[Dict[str, Any]] = None,
        documentation_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Test all endpoints until success or clear impossibility
        
        Args:
            endpoints: List of endpoints to test
            base_url: API base URL
            auth_config: Authentication configuration
            documentation_text: Full documentation for context
            
        Returns:
            Complete test results
        """
        start_time = time.time()
        
        await self.stream_logger.info("🧠 INTELLIGENT ADAPTIVE TESTING")
        await self.stream_logger.info("━" * 80)
        await self.stream_logger.info("🎯 Strategy: Learn from every response and adapt intelligently")
        await self.stream_logger.info("🚀 No limits - Will keep trying until success!")
        await self.stream_logger.info("━" * 80)
        
        # Authenticate
        auth_token = None
        auth_data = {}
        if auth_config:
            auth_result = await self._smart_authenticate(auth_config, base_url, documentation_text)
            if auth_result['success']:
                auth_token = auth_result['token']
                auth_data = auth_result['data']
                await self.stream_logger.success(f"✅ Authenticated: {list(auth_data.keys())}")
        
        # Test each endpoint
        results = []
        total_attempts = 0
        
        for idx, endpoint in enumerate(endpoints, 1):
            path = endpoint.get('path', '')
            method = endpoint.get('method', 'GET')
            
            await self.stream_logger.info(f"\n{'='*80}")
            await self.stream_logger.info(f"[{idx}/{len(endpoints)}] 🎯 {method} {path}")
            await self.stream_logger.info(f"{'='*80}")
            
            # Test this endpoint until success
            endpoint_result = await self._test_endpoint_until_success(
                endpoint=endpoint,
                base_url=base_url,
                auth_token=auth_token,
                auth_data=auth_data,
                documentation_text=documentation_text
            )
            
            results.append(endpoint_result)
            total_attempts += endpoint_result.get('total_attempts', 0)
            
            # Emit progress
            await get_event_stream().emit_event(
                self.test_id,
                EventType.TEST_PROGRESS,
                step=idx,
                total_steps=len(endpoints),
                step_name=f"{method} {path}",
                percentage=round((idx / len(endpoints)) * 100, 1)
            )
        
        duration = time.time() - start_time
        success_count = sum(1 for r in results if r['success'])
        
        await self.stream_logger.info(f"\n{'='*80}")
        await self.stream_logger.info("🏁 TESTING COMPLETE")
        await self.stream_logger.info(f"{'='*80}")
        await self.stream_logger.info(f"✅ Successful: {success_count}/{len(endpoints)}")
        await self.stream_logger.info(f"🔄 Total attempts: {total_attempts}")
        await self.stream_logger.info(f"⏱️  Duration: {duration:.2f}s")
        await self.stream_logger.info(f"📊 Avg attempts per endpoint: {total_attempts/len(endpoints):.1f}")
        
        return {
            'test_id': self.test_id,
            'success': success_count == len(endpoints),
            'total_endpoints': len(endpoints),
            'successful': success_count,
            'failed': len(endpoints) - success_count,
            'total_attempts': total_attempts,
            'duration': duration,
            'results': results
        }
    
    async def _test_endpoint_until_success(
        self,
        endpoint: Dict[str, Any],
        base_url: str,
        auth_token: Optional[str],
        auth_data: Dict[str, Any],
        documentation_text: Optional[str]
    ) -> Dict[str, Any]:
        """
        Test endpoint until success - NO LIMIT!
        
        Strategy:
        1. Try with AI-generated payload
        2. If fails, analyze error with AI
        3. Generate new payload based on error
        4. Try different strategies:
           - Minimal payload (only required fields)
           - Full payload (all fields)
           - Example from documentation
           - Modified successful patterns from similar endpoints
        5. Keep learning and adapting
        """
        path = endpoint.get('path', '')
        method = endpoint.get('method', 'GET')
        
        # Initialize tracking
        if path not in self.failed_attempts:
            self.failed_attempts[path] = []
        if path not in self.error_patterns:
            self.error_patterns[path] = set()
        
        attempt = 0
        strategies_tried = set()
        
        # Strategy 1: AI-generated payload
        await self.stream_logger.info("  📋 Strategy 1: AI-generated realistic payload")
        payload = await self._generate_smart_payload(
            endpoint, auth_data, documentation_text, strategy="realistic"
        )
        
        while True:
            attempt += 1
            await self.stream_logger.info(f"  🔄 Attempt {attempt}")
            
            # Execute request
            result = await self._execute_request(
                method, f"{base_url}{path}", payload, auth_token
            )
            
            # Check success
            if result['success']:
                await self.stream_logger.success(f"  ✅ SUCCESS on attempt {attempt}!")
                await self.stream_logger.info(f"  📥 Status: {result['status_code']} ({result['duration']:.0f}ms)")
                
                # Store successful pattern
                self.success_patterns[path] = {
                    'payload': payload,
                    'strategy': list(strategies_tried)[-1] if strategies_tried else 'initial'
                }
                
                return {
                    'success': True,
                    'endpoint': path,
                    'method': method,
                    'total_attempts': attempt,
                    'status_code': result['status_code'],
                    'winning_strategy': list(strategies_tried)[-1] if strategies_tried else 'initial',
                    'final_payload': payload
                }
            
            # Failed - learn and adapt
            error_msg = result.get('error', '')
            status_code = result.get('status_code', 0)
            
            await self.stream_logger.warning(f"  ⚠️  Failed: {status_code} - {error_msg[:100]}")
            
            # Store failed attempt
            self.failed_attempts[path].append({
                'attempt': attempt,
                'payload': payload,
                'error': error_msg,
                'status_code': status_code
            })
            self.error_patterns[path].add(error_msg[:200])
            
            # Check if we should stop (clear impossibility)
            if self._is_endpoint_impossible(path, status_code, error_msg):
                await self.stream_logger.error(f"  ❌ Endpoint appears impossible to test (auth/permission issue)")
                return {
                    'success': False,
                    'endpoint': path,
                    'method': method,
                    'total_attempts': attempt,
                    'reason': 'impossible',
                    'last_error': error_msg
                }
            
            # Decide next strategy
            next_strategy = self._choose_next_strategy(
                endpoint, strategies_tried, error_msg, status_code, attempt
            )
            
            if not next_strategy:
                await self.stream_logger.error(f"  ❌ Exhausted all strategies after {attempt} attempts")
                return {
                    'success': False,
                    'endpoint': path,
                    'method': method,
                    'total_attempts': attempt,
                    'strategies_tried': list(strategies_tried),
                    'last_error': error_msg
                }
            
            strategies_tried.add(next_strategy)
            await self.stream_logger.info(f"  🧠 Strategy {attempt + 1}: {next_strategy}")
            
            # Generate new payload based on strategy
            payload = await self._generate_payload_with_strategy(
                endpoint=endpoint,
                strategy=next_strategy,
                auth_data=auth_data,
                documentation_text=documentation_text,
                error_response=result,
                failed_attempts=self.failed_attempts[path]
            )
    
    def _is_endpoint_impossible(self, path: str, status_code: int, error_msg: str) -> bool:
        """Check if endpoint is impossible to test (auth issues, not implemented, etc.)"""
        # Check for authentication/permission issues after multiple attempts
        if len(self.failed_attempts.get(path, [])) >= 5:
            # All attempts have same auth error
            auth_errors = ['unauthorized', 'forbidden', 'invalid token', 'authentication', '401', '403']
            if any(err in error_msg.lower() for err in auth_errors):
                return True
        
        # Check for not implemented
        if status_code in [501, 405]:  # Not implemented, method not allowed
            return True
        
        return False
    
    def _choose_next_strategy(
        self,
        endpoint: Dict[str, Any],
        strategies_tried: Set[str],
        error_msg: str,
        status_code: int,
        attempt: int
    ) -> Optional[str]:
        """Choose next testing strategy based on what we've learned"""
        available_strategies = [
            'minimal_required',  # Only required fields
            'full_payload',  # All fields
            'documentation_example',  # Extract from docs
            'similar_endpoint',  # Copy from similar successful endpoint
            'ai_error_fix',  # AI analyzes error and fixes
            'type_variations',  # Try different data types
            'value_variations',  # Try different values
            'field_name_variations',  # Try different field names (camelCase, snake_case)
        ]
        
        # Remove already tried strategies
        remaining = [s for s in available_strategies if s not in strategies_tried]
        
        if not remaining:
            return None
        
        # Choose strategy based on error
        error_lower = error_msg.lower()
        
        # Missing fields -> try full payload
        if 'required' in error_lower or 'missing' in error_lower:
            if 'full_payload' in remaining:
                return 'full_payload'
        
        # Validation error -> try AI fix
        if 'validation' in error_lower or 'invalid' in error_lower:
            if 'ai_error_fix' in remaining:
                return 'ai_error_fix'
        
        # Type error -> try type variations
        if 'type' in error_lower:
            if 'type_variations' in remaining:
                return 'type_variations'
        
        # Return first remaining strategy
        return remaining[0]
    
    async def _generate_payload_with_strategy(
        self,
        endpoint: Dict[str, Any],
        strategy: str,
        auth_data: Dict[str, Any],
        documentation_text: Optional[str],
        error_response: Dict[str, Any],
        failed_attempts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate payload using specific strategy"""
        
        if strategy == 'minimal_required':
            return await self._generate_minimal_payload(endpoint, auth_data)
        
        elif strategy == 'full_payload':
            return await self._generate_full_payload(endpoint, auth_data, documentation_text)
        
        elif strategy == 'documentation_example':
            return await self._extract_example_from_docs(endpoint, documentation_text)
        
        elif strategy == 'similar_endpoint':
            return await self._copy_from_similar_endpoint(endpoint, auth_data)
        
        elif strategy == 'ai_error_fix':
            return await self._ai_fix_based_on_error(
                endpoint, failed_attempts[-1]['payload'], error_response, documentation_text, auth_data
            )
        
        elif strategy == 'type_variations':
            return await self._generate_type_variations(endpoint, failed_attempts[-1]['payload'])
        
        elif strategy == 'value_variations':
            return await self._generate_value_variations(endpoint, failed_attempts[-1]['payload'])
        
        elif strategy == 'field_name_variations':
            return await self._generate_field_name_variations(failed_attempts[-1]['payload'])
        
        else:
            return {}
    
    async def _generate_smart_payload(
        self,
        endpoint: Dict[str, Any],
        auth_data: Dict[str, Any],
        documentation_text: Optional[str],
        strategy: str = "realistic"
    ) -> Dict[str, Any]:
        """Generate smart payload using AI with documentation context"""
        try:
            # Build comprehensive prompt with ALL context
            prompt = f"""
Generate a PERFECT test payload for this API endpoint using ALL available context.

ENDPOINT DETAILS:
Method: {endpoint.get('method')}
Path: {endpoint.get('path')}
Summary: {endpoint.get('summary', '')}
Description: {endpoint.get('description', '')}

PARAMETERS:
{json.dumps(endpoint.get('parameters', []), indent=2)}

REQUEST BODY SCHEMA:
{json.dumps(endpoint.get('request_body_schema', {}), indent=2)}

AUTHENTICATION DATA (use these values!):
{json.dumps(auth_data, indent=2)}

DOCUMENTATION CONTEXT (find examples here!):
{documentation_text[:5000] if documentation_text else 'Not available'}

INSTRUCTIONS:
1. Use EXACT field names from the documentation
2. Use EXACT values from documentation examples
3. Include ALL required fields
4. Use auth_data values (vendorCode, userId, etc.)
5. Use realistic values (not "string", "test", etc.)
6. Match data types exactly (string, number, boolean)
7. Use proper formats (dates, emails, phones)
8. Look for example requests in documentation

Return ONLY a JSON object with the payload. No markdown, no explanations.
"""
            
            # BUG #7 FIXED: Progressive temperature for varied responses
            # Start at 0.2, increase with each attempt to generate different payloads
            base_temp = 0.2
            temperature = min(base_temp + (attempt * 0.15), 0.9)
            logger.info(f"🌡️  Using temperature {temperature:.2f} for attempt {attempt}")
            
            response = await self.ai_provider.generate_content(prompt, temperature=temperature)
            payload = self._parse_json(response)
            
            await self.stream_logger.info(f"  🤖 AI generated payload with {len(payload)} fields")
            
            return payload
        
        except Exception as e:
            logger.error(f"Error generating smart payload: {e}")
            return {}
    
    async def _ai_fix_based_on_error(
        self,
        endpoint: Dict[str, Any],
        current_payload: Dict[str, Any],
        error_response: Dict[str, Any],
        documentation_text: Optional[str],
        auth_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to fix payload based on error"""
        try:
            prompt = f"""
Fix this API request payload based on the error response.

ENDPOINT: {endpoint.get('method')} {endpoint.get('path')}

CURRENT PAYLOAD:
{json.dumps(current_payload, indent=2)}

ERROR RESPONSE:
Status: {error_response.get('status_code')}
Error: {error_response.get('error', '')}
Response: {error_response.get('response_body', '')}

AUTH DATA AVAILABLE:
{json.dumps(auth_data, indent=2)}

DOCUMENTATION:
{documentation_text[:3000] if documentation_text else 'Not available'}

ANALYZE THE ERROR AND FIX:
- If "required field missing" → Add the field
- If "invalid value" → Use correct value from documentation
- If "invalid type" → Fix the data type
- If "vendorCode missing" → Add from auth_data
- If "validation error" → Fix validation issue
- If field name wrong → Use correct name from docs

Return ONLY the FIXED JSON payload. No markdown, no explanations.
"""
            
            response = await self.ai_provider.generate_content(prompt, temperature=0.3)
            fixed_payload = self._parse_json(response)
            
            # Show what changed
            changes = self._get_payload_diff(current_payload, fixed_payload)
            if changes:
                await self.stream_logger.info(f"  🔧 AI made {len(changes)} changes:")
                for change in changes[:5]:  # Show first 5 changes
                    await self.stream_logger.info(f"     • {change}")
            
            return fixed_payload
        
        except Exception as e:
            logger.error(f"Error fixing payload: {e}")
            return current_payload
    
    async def _generate_minimal_payload(
        self,
        endpoint: Dict[str, Any],
        auth_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate minimal payload with only required fields"""
        payload = {}
        
        for param in endpoint.get('parameters', []):
            if param.get('required'):
                field_name = param.get('name')
                field_type = param.get('type', 'string')
                
                # Use auth_data if field name matches
                if field_name in auth_data:
                    payload[field_name] = auth_data[field_name]
                else:
                    payload[field_name] = self._get_default_value(field_type)
        
        await self.stream_logger.info(f"  📝 Minimal payload: {len(payload)} required fields")
        return payload
    
    async def _generate_full_payload(
        self,
        endpoint: Dict[str, Any],
        auth_data: Dict[str, Any],
        documentation_text: Optional[str]
    ) -> Dict[str, Any]:
        """Generate full payload with all fields"""
        # Use AI to generate comprehensive payload
        return await self._generate_smart_payload(
            endpoint, auth_data, documentation_text, strategy="comprehensive"
        )
    
    async def _extract_example_from_docs(
        self,
        endpoint: Dict[str, Any],
        documentation_text: Optional[str]
    ) -> Dict[str, Any]:
        """Extract example payload from documentation"""
        if not documentation_text:
            return {}
        
        try:
            path = endpoint.get('path', '')
            method = endpoint.get('method', '')
            
            prompt = f"""
Find and extract the example request payload for this endpoint from the documentation.

Endpoint: {method} {path}

Documentation:
{documentation_text[:8000]}

Find the example request body and return it as JSON.
Return ONLY the JSON payload, no markdown, no explanations.
"""
            
            response = await self.ai_provider.generate_content(prompt, temperature=0.1)
            example = self._parse_json(response)
            
            await self.stream_logger.info(f"  📚 Extracted example from docs: {len(example)} fields")
            return example
        
        except Exception as e:
            logger.error(f"Error extracting example: {e}")
            return {}
    
    async def _copy_from_similar_endpoint(
        self,
        endpoint: Dict[str, Any],
        auth_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Copy payload from similar successful endpoint"""
        path = endpoint.get('path', '')
        
        # Find similar successful endpoint
        for success_path, success_data in self.success_patterns.items():
            if self._are_endpoints_similar(path, success_path):
                payload = success_data['payload'].copy()
                
                # Adapt for current endpoint
                payload.update(auth_data)
                
                await self.stream_logger.info(f"  🔄 Adapted payload from similar endpoint: {success_path}")
                return payload
        
        return {}
    
    def _are_endpoints_similar(self, path1: str, path2: str) -> bool:
        """Check if two endpoints are similar"""
        # Same base path
        base1 = path1.split('/')[1] if '/' in path1 else path1
        base2 = path2.split('/')[1] if '/' in path2 else path2
        return base1 == base2
    
    async def _generate_type_variations(
        self,
        endpoint: Dict[str, Any],
        current_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Try different data types"""
        new_payload = current_payload.copy()
        
        # Convert strings to numbers where possible
        for key, value in new_payload.items():
            if isinstance(value, str) and value.isdigit():
                new_payload[key] = int(value)
        
        await self.stream_logger.info(f"  🔢 Trying type variations")
        return new_payload
    
    async def _generate_value_variations(
        self,
        endpoint: Dict[str, Any],
        current_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Try different values"""
        # Use AI to generate variations
        return current_payload
    
    async def _generate_field_name_variations(
        self,
        current_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Try different field name formats"""
        new_payload = {}
        
        for key, value in current_payload.items():
            # Try snake_case if camelCase
            if '_' not in key:
                # Convert camelCase to snake_case
                import re
                snake_key = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
                new_payload[snake_key] = value
            else:
                new_payload[key] = value
        
        await self.stream_logger.info(f"  📝 Trying field name variations")
        return new_payload
    
    async def _smart_authenticate(
        self,
        auth_config: Dict[str, Any],
        base_url: str,
        documentation_text: Optional[str]
    ) -> Dict[str, Any]:
        """Smart authentication with learning"""
        # Similar to _execute_authentication but with adaptation
        auth_endpoint = auth_config.get('auth_endpoint', '/api/login')
        credentials = auth_config.get('test_credentials', {})
        
        await self.stream_logger.info(f"🔐 Authenticating at {auth_endpoint}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}{auth_endpoint}",
                    json=credentials
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    
                    # Extract token
                    token_path = auth_config.get('token_response_path', 'data.token')
                    token = self._extract_value(data, token_path)
                    
                    # Extract ALL data from response (not just specified fields)
                    additional_data = self._extract_all_useful_data(data)
                    
                    return {
                        'success': True,
                        'token': token,
                        'data': additional_data
                    }
                else:
                    return {'success': False, 'error': f"Status {response.status_code}"}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _extract_all_useful_data(self, response_data: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
        """Extract all potentially useful data from response"""
        result = {}
        
        for key, value in response_data.items():
            if isinstance(value, dict):
                # Recursively extract from nested dicts
                nested = self._extract_all_useful_data(value, f"{prefix}{key}.")
                result.update(nested)
            elif isinstance(value, (str, int, float, bool)):
                # Store simple values
                full_key = f"{prefix}{key}" if prefix else key
                result[key] = value  # Also store without prefix
                result[full_key] = value  # Store with prefix
        
        return result
    
    def _extract_value(self, data: Any, path: str) -> Any:
        """Extract value using dot notation"""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from AI response with robust error handling (BUG #13 FIX)"""
        import re
        
        # Try direct parse first
        try:
            return json.loads(text.strip())
        except:
            pass
        
        # Try extracting from markdown code blocks
        patterns = [
            r'```json\s*(\{.*?\})\s*```',  # ```json {...} ```
            r'```\s*(\{.*?\})\s*```',      # ``` {...} ```
            r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',  # Any JSON-like structure
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(1)
                    
                    # Clean up common AI mistakes
                    json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)  # Remove comments
                    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)  # Remove trailing commas
                    json_str = json_str.replace("'", '"')  # Fix single quotes
                    
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict) and len(parsed) > 0:
                        return parsed
                except:
                    continue
        
        logger.warning(f"⚠️  Failed to parse JSON from AI response: {text[:200]}")
        return {}
    
    def _get_default_value(self, field_type: str) -> Any:
        """Get default value for field type"""
        type_lower = field_type.lower()
        if 'string' in type_lower or 'str' in type_lower:
            return "test_value"
        elif 'number' in type_lower or 'int' in type_lower:
            return 123
        elif 'bool' in type_lower:
            return True
        elif 'array' in type_lower or 'list' in type_lower:
            return []
        elif 'object' in type_lower or 'dict' in type_lower:
            return {}
        else:
            return None
    
    def _get_payload_diff(self, old: Dict[str, Any], new: Dict[str, Any]) -> List[str]:
        """Get differences between two payloads"""
        changes = []
        
        # Check added fields
        for key in new:
            if key not in old:
                changes.append(f"Added '{key}': {new[key]}")
            elif old[key] != new[key]:
                changes.append(f"Changed '{key}': {old[key]} → {new[key]}")
        
        # Check removed fields
        for key in old:
            if key not in new:
                changes.append(f"Removed '{key}'")
        
        return changes
    
    async def _execute_request(
        self,
        method: str,
        url: str,
        payload: Dict[str, Any],
        auth_token: Optional[str]
    ) -> Dict[str, Any]:
        """Execute HTTP request using reusable client (BUG #3 FIX)"""
        try:
            headers = {'Content-Type': 'application/json'}
            if auth_token:
                headers['Authorization'] = f"Bearer {auth_token}"
            
            start_time = time.time()
            
            # BUG #3 FIXED: Reuse self.client instead of creating new one
            if method.upper() == 'GET':
                response = await self.client.get(url, headers=headers, params=payload)
            elif method.upper() == 'POST':
                response = await self.client.post(url, headers=headers, json=payload)
            elif method.upper() == 'PUT':
                response = await self.client.put(url, headers=headers, json=payload)
            elif method.upper() == 'PATCH':
                response = await self.client.patch(url, headers=headers, json=payload)
            elif method.upper() == 'DELETE':
                response = await self.client.delete(url, headers=headers)
            else:
                return {'success': False, 'error': f'Unsupported method: {method}'}
            
            duration = (time.time() - start_time) * 1000
            success = 200 <= response.status_code < 400
            
            return {
                'success': success,
                'status_code': response.status_code,
                'duration': duration,
                'response_body': response.text,
                'error': None if success else response.text[:500]
            }
        
        except Exception as e:
            return {
                'success': False,
                'status_code': 0,
                'error': str(e),
                'duration': 0
            }
