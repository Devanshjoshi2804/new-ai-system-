"""
Adaptive Test Executor - ACTUALLY adapts payloads based on errors!
Replaces the dumb retry logic with intelligent adaptation
Now with Vector DB for focused context retrieval!
LEARNS EVERYTHING FROM DOCUMENTATION - NO HARDCODING!
NOW WITH PROGRESSIVE LEARNING - Gets smarter with each test run!
"""
import logging
import time
import asyncio
import json
from typing import Dict, Any, Optional
import aiohttp
from datetime import datetime

from .intelligent_payload_generator import IntelligentPayloadGenerator
from ..learning.document_learning_store import DocumentLearningStore

logger = logging.getLogger(__name__)


class AdaptiveTestExecutor:
    """
    Executes API tests with INTELLIGENT ADAPTATION
    
    Key difference from TestExecutor:
    - Analyzes error responses
    - Adapts payload based on errors
    - Uses AI to fix issues
    - Learns from each attempt
    """
    
    def __init__(
        self,
        ai_provider=None,
        vector_store=None,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 32.0,
        timeout: int = 30
    ):
        """
        Initialize adaptive test executor
        
        Args:
            ai_provider: AI provider for intelligent adaptation
            vector_store: Vector DB for focused context retrieval
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries
            timeout: Request timeout in seconds
        """
        self.ai_provider = ai_provider
        self.vector_store = vector_store
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.timeout = timeout
        
        # Initialize intelligent payload generator - NO HARDCODING!
        self.payload_generator = IntelligentPayloadGenerator(
            ai_provider=ai_provider,
            vector_store=vector_store
        )
        
        # CRITICAL: Initialize learning store - learns from EVERY failure!
        self.learning_store = DocumentLearningStore()
        
        # Learning memory
        self.failed_attempts = {}  # endpoint -> list of failed attempts
        self.successful_patterns = {}  # endpoint -> successful payload
        
        # Vector DB usage stats
        self.vector_db_queries = 0
        self.context_size_saved = 0
        
        logger.info("✅ Adaptive executor initialized with PROGRESSIVE LEARNING (gets smarter each run)")

    
    async def execute_test(
        self,
        endpoint: Dict[str, Any],
        test_data: Dict[str, Any],
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        attempt: int = 1,
        documentation_text: Optional[str] = None,
        doc_id: Optional[str] = None,
        flow_store = None  # NEW: Flow Vector Store for semantic memory
    ) -> Dict[str, Any]:
        """
        Execute a single test with ADAPTIVE retry logic
        
        Args:
            endpoint: Endpoint specification
            test_data: Test data to send
            base_url: Base URL for the API
            headers: Optional HTTP headers
            attempt: Current attempt number
            documentation_text: Documentation for context
            
        Returns:
            Test result dictionary
        """
        method = endpoint.get('method', 'GET').upper()
        path = endpoint.get('path', '')
        full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        
        # NEW: Store flow_store for use in retry
        self.flow_store = flow_store
        self.doc_id = doc_id
        
        # Replace path parameters and track which ones we used (BUG #4 FIX)
        current_data = test_data.copy()
        path_params_used = set()
        
        for key, value in current_data.items():
            if f"{{{key}}}" in full_url:
                full_url = full_url.replace(f"{{{key}}}", str(value))
                path_params_used.add(key)
                logger.debug(f"🔗 Path param replaced: {key}={value}")
        
        # Remove path params from body data (BUG #4 FIX)
        body_data = {k: v for k, v in current_data.items() if k not in path_params_used}
        if path_params_used:
            logger.debug(f"📤 Removed {len(path_params_used)} path params from body")
        
        # Prepare headers
        request_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if headers:
            request_headers.update(headers)
        
        # Prepare request data (BUG #4 FIX - use body_data not current_data)
        if method in ['GET', 'DELETE']:
            params = body_data
            data = None
        else:
            params = None
            data = body_data if body_data else None
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=full_url,
                    params=params,
                    json=data,
                    headers=request_headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    execution_time = time.time() - start_time
                    
                    # Read response
                    try:
                        response_data = await response.json()
                    except:
                        response_data = {"text": await response.text()}
                    
                    response_headers = dict(response.headers)
                    status_code = response.status
                    is_success = 200 <= status_code < 300
                    
                    result = {
                        "status": "passed" if is_success else "failed",
                        "attempt_number": attempt,
                        "request_data": current_data,
                        "request_headers": request_headers,
                        "response_data": response_data,
                        "response_status": status_code,
                        "response_headers": response_headers,
                        "execution_time": execution_time,
                        "error_message": None if is_success else f"HTTP {status_code}",
                        "error_type": None if is_success else "HTTP_ERROR",
                        "timestamp": datetime.utcnow()
                    }
                    
                    # SUCCESS - Store pattern AND LEARN!
                    if is_success:
                        self.successful_patterns[path] = current_data
                        logger.info(f"✅ Test passed on attempt {attempt}: {method} {path}")
                        
                        # CRITICAL: Learn from successful payload
                        if doc_id:
                            try:
                                await self.learning_store.store_successful_payload(
                                    doc_id=doc_id,
                                    endpoint_path=path,
                                    method=method,
                                    payload=current_data,
                                    response_status=status_code
                                )
                                logger.info(f"🧠 Stored successful payload for future runs")
                            except Exception as e:
                                logger.warning(f"Failed to store successful payload: {e}")
                        
                        return result
                    
                    # FAILED - Try to adapt AND LEARN!
                    if attempt < self.max_retries:
                        # Store failed attempt
                        if path not in self.failed_attempts:
                            self.failed_attempts[path] = []
                        self.failed_attempts[path].append({
                            'attempt': attempt,
                            'payload': current_data,
                            'status_code': status_code,
                            'error': response_data
                        })
                        
                        # CRITICAL: Learn from error (auto-detect missing fields)
                        if doc_id:
                            try:
                                await self.learning_store.learn_from_error(
                                    doc_id=doc_id,
                                    endpoint_path=path,
                                    method=method,
                                    sent_payload=current_data,
                                    error_response=response_data
                                )
                                logger.info(f"🧠 Auto-learned from error response")
                            except Exception as e:
                                logger.warning(f"Failed to learn from error: {e}")
                        
                        logger.warning(f"⚠️  Attempt {attempt} failed: {status_code}")
                        
                        # Check if we should retry
                        if self._should_retry(status_code):
                            # ADAPT THE PAYLOAD!
                            logger.info(f"🧠 Analyzing error and adapting payload...")
                            
                            adapted_data = await self._adapt_payload(
                                endpoint=endpoint,
                                current_payload=current_data,
                                error_response=response_data,
                                status_code=status_code,
                                attempt=attempt,
                                documentation_text=documentation_text
                            )
                            
                            # Check if payload changed
                            if adapted_data != current_data:
                                logger.info(f"🔧 Payload adapted, trying again...")
                                await self._exponential_backoff(attempt)
                                
                                # Retry with ADAPTED payload
                                return await self.execute_test(
                                    endpoint, adapted_data, base_url, headers, 
                                    attempt + 1, documentation_text, doc_id, flow_store
                                )
                            else:
                                # DETECT REPEATING ERRORS
                                is_repeating = self._is_repeating_error(path, str(response_data))
                                if is_repeating:
                                    logger.error(f"🚫 Same error {len(self.failed_attempts.get(path, []))} times! AI is not fixing it. Stopping.")
                                    return result
                                
                                logger.warning(f"⚠️  Payload unchanged, forcing different approach...")
                                # Try a completely different payload generation strategy
                                adapted_data = await self._force_different_payload(
                                    endpoint, current_data, response_data, documentation_text
                                )
                                
                                if adapted_data != current_data:
                                    await self._exponential_backoff(attempt)
                                    return await self.execute_test(
                                        endpoint, adapted_data, base_url, headers,
                                        attempt + 1, documentation_text, doc_id, flow_store
                                    )
                                else:
                                    logger.error(f"❌ Cannot generate different payload. Giving up.")
                                    return result
                    
                    logger.error(f"❌ All {self.max_retries} attempts failed")
                    return result
                    
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.error(f"Request timeout for {method} {path}")
            
            result = {
                "status": "failed",
                "attempt_number": attempt,
                "request_data": current_data,
                "request_headers": request_headers,
                "response_data": None,
                "response_status": None,
                "response_headers": None,
                "execution_time": execution_time,
                "error_message": f"Request timeout after {self.timeout}s",
                "error_type": "TIMEOUT",
                "timestamp": datetime.utcnow()
            }
            
            if attempt < self.max_retries:
                logger.info(f"Timeout, retrying (attempt {attempt + 1}/{self.max_retries})")
                await self._exponential_backoff(attempt)
                return await self.execute_test(
                    endpoint, current_data, base_url, headers, attempt + 1, 
                    documentation_text, doc_id, flow_store
                )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Unexpected error for {method} {path}: {e}")
            
            return {
                "status": "failed",
                "attempt_number": attempt,
                "request_data": current_data,
                "request_headers": request_headers,
                "response_data": None,
                "response_status": None,
                "response_headers": None,
                "execution_time": execution_time,
                "error_message": f"Unexpected error: {str(e)}",
                "error_type": "UNKNOWN_ERROR",
                "timestamp": datetime.utcnow()
            }
    
    async def _adapt_payload(
        self,
        endpoint: Dict[str, Any],
        current_payload: Dict[str, Any],
        error_response: Dict[str, Any],
        status_code: int,
        attempt: int,
        documentation_text: Optional[str]
    ) -> Dict[str, Any]:
        """
        ADAPT payload based on error response using AI
        NOW WITH VECTOR DB + FLOW STORE FOR COMPLETE CONTEXT!
        
        This is the KEY method that makes this adaptive!
        """
        if not self.ai_provider:
            logger.warning("No AI provider, cannot adapt payload")
            return current_payload
        
        try:
            # Extract error message
            error_msg = ""
            if isinstance(error_response, dict):
                error_msg = error_response.get('message', '')
                if not error_msg:
                    error_msg = error_response.get('error', '')
                if not error_msg and 'errors' in error_response:
                    errors = error_response['errors']
                    if isinstance(errors, list):
                        error_msg = ', '.join(str(e) for e in errors)
            
            # CRITICAL FIX: Parse missing fields from error message
            import re
            missing_fields = set()
            if error_msg:
                # Common patterns: "field X is required", "missing required field X", "X should not be empty"
                patterns = [
                    r'[\'"]([\w]+)[\'"]\s+(?:is required|should not be empty|must (?:be a|not be empty))',
                    r'(?:missing|required)\s+field\s+[\'"]([\w]+)[\'"]',
                    r'[\'"]([\w]+)[\'"]\s+should not be empty'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, error_msg, re.IGNORECASE)
                    missing_fields.update(matches)
                
                if missing_fields:
                    logger.info(f"🔍 Detected missing fields from error: {missing_fields}")

            
            # NEW: Query Flow Store for context from previous tests
            flow_context = ""
            if hasattr(self, 'flow_store') and self.flow_store:
                try:
                    fix_query = f"""
                    Find data to fix error for {endpoint.get('method')} {endpoint.get('path')}
                    Error: {error_msg[:200]}
                    Look for tokens, passwords, user IDs, credentials from previous successful API calls
                    """
                    flow_context = await self.flow_store.query(fix_query, k=3)
                    if flow_context:
                        logger.info(f"📚 Retrieved flow context for error fixing: {len(flow_context)} chars")
                except Exception as e:
                    logger.warning(f"Failed to query flow store: {e}")
            
            # Get focused context from Vector DB if available (BUG #6 FIX)
            context_text = documentation_text[:8000] if documentation_text else 'Not available'  # Increased from 2000
            context_source = "Full documentation (first 8000 chars)"
            
            if self.vector_store:
                try:
                    logger.info(f"🧠 Querying Vector DB for {endpoint.get('method')} {endpoint.get('path')}...")
                    
                    # Get doc_id from endpoint or use a default strategy
                    doc_id = endpoint.get('doc_id', 'default')
                    
                    # Use Vector DB's get_endpoint_context method which exists
                    focused_context = self.vector_store.get_endpoint_context(
                        doc_id=doc_id,
                        endpoint_path=endpoint.get('path', ''),
                        method=endpoint.get('method')
                    )
                    
                    if focused_context and len(focused_context) > 100:
                        # Also get error-specific context if we have an error
                        if error_msg:
                            error_context = self.vector_store.get_error_context(
                                doc_id=doc_id,
                                error_message=error_msg,
                                endpoint=endpoint.get('path')
                            )
                            if error_context:
                                focused_context = f"{focused_context}\n\n--- ERROR CONTEXT ---\n{error_context}"
                        
                        context_text = focused_context
                        context_source = "Vector DB (focused)"
                        self.vector_db_queries += 1
                        
                        # Calculate context size savings
                        original_size = len(documentation_text) if documentation_text else 0
                        focused_size = len(focused_context)
                        saved = original_size - focused_size
                        self.context_size_saved += saved
                        
                        logger.info(f"📚 Retrieved focused context: {focused_size} chars (saved {saved} chars, {(original_size / focused_size if focused_size > 0 else 0):.1f}x smaller)")
                    else:
                        logger.warning("⚠️  Vector DB returned empty context, using more documentation")
                        # Instead of just 2000 chars, use 8000 chars
                        context_text = documentation_text[:8000] if documentation_text else 'Not available'
                except Exception as e:
                    logger.warning(f"⚠️  Vector DB query failed: {str(e)}, using more documentation")
                    # Use more context when Vector DB fails
                    context_text = documentation_text[:8000] if documentation_text else 'Not available'
            
            # Build prompt for AI - WITH FLOW CONTEXT + MISSING FIELDS!
            missing_fields_text = ""
            if missing_fields:
                missing_fields_text = f"""
🚨 DETECTED MISSING FIELDS (Add these immediately): {', '.join(missing_fields)}
PRIORITY: Find values for these fields from PREVIOUS API CALLS DATA or documentation examples
"""
            
            prompt = f"""
You are an API testing expert. Fix this API request payload by LEARNING from the documentation AND previous test data.

ENDPOINT: {endpoint.get('method')} {endpoint.get('path')}
ATTEMPT: {attempt}

{missing_fields_text}

CURRENT PAYLOAD (has errors):
{json.dumps(current_payload, indent=2)}

ERROR RESPONSE:
Status Code: {status_code}
Error Message: {error_msg}
Full Response: {json.dumps(error_response, indent=2)[:800]}

PREVIOUS API CALLS DATA (from Flow ChromaDB):
{flow_context[:2000] if flow_context else "No previous test data available yet"}

ENDPOINT SPECIFICATION:
{json.dumps(endpoint, indent=2)[:1000]}

DOCUMENTATION CONTEXT ({context_source}):
{context_text}

CRITICAL INSTRUCTIONS:
1. **ADD MISSING FIELDS FIRST**: {', '.join(missing_fields) if missing_fields else 'Check error message'}
2. **USE PREVIOUS TEST DATA**: Look in "PREVIOUS API CALLS DATA" for needed values
3. **FOR PASSWORDS**: Use PLAIN TEXT password from signup/register REQUEST (not hashed from response)
4. **FOR TOKENS**: Extract token from login/auth RESPONSE
5. **FOR USER IDs**: Extract userId from user creation RESPONSE
6. READ the documentation to understand field requirements
7. FIND examples in documentation - use exact values from examples
8. FIX the payload using PREVIOUS DATA first, then documentation

DO NOT guess or hardcode values like "test", "open", "123".
DO NOT use placeholder values.

PRIORITY ORDER:
1. Add detected missing fields: {', '.join(missing_fields) if missing_fields else 'None'}
2. Extract values from PREVIOUS API CALLS DATA (most reliable)
3. Use values from documentation examples
4. Follow schema requirements

COMMON FIXES:
- If error says "field X is required" → Look in previous data or documentation for field X
- If error says "invalid password" → Find plain text password from signup REQUEST
- If error says "invalid token" → Find token from login RESPONSE
- If error says "user not found" → Find userId from user creation RESPONSE
- If error mentions validation → Check documentation for format/rules

Return ONLY the FIXED JSON payload. No markdown, no explanations.
"""
            
            # Call AI
            response = await self.ai_provider.generate_content(prompt, temperature=0.3)
            
            # Parse JSON from response
            fixed_payload = self._parse_json(response)
            
            if fixed_payload:
                # Log what changed
                changes = self._get_changes(current_payload, fixed_payload)
                if changes:
                    logger.info(f"🔧 AI made {len(changes)} changes:")
                    for change in changes[:5]:
                        logger.info(f"   • {change}")
                
                return fixed_payload
            else:
                logger.warning("AI returned invalid JSON")
                return current_payload
        
        except Exception as e:
            logger.error(f"Error adapting payload: {e}")
            return current_payload
    
    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from AI response"""
        try:
            text = text.strip()
            
            # Remove markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            return json.loads(text)
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            return {}
    
    def _get_changes(self, old: Dict[str, Any], new: Dict[str, Any]) -> list:
        """Get list of changes between two payloads"""
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
    
    def _should_retry(self, status_code: int) -> bool:
        """Determine if should retry (more aggressive than original)"""
        # Retry on 5xx server errors
        if 500 <= status_code < 600:
            return True
        
        # Retry on 429 (rate limiting)
        if status_code == 429:
            return True
        
        # ALSO retry on 400 (we can fix the payload!)
        if status_code == 400:
            return True
        
        # ALSO retry on 404 if it's due to empty path params
        if status_code == 404:
            return True
        
        # Don't retry on 401/403 (auth issues we can't fix)
        if status_code in [401, 403]:
            return False
        
        return False
    
    async def _exponential_backoff(self, attempt: int):
        """Wait with exponential backoff before retry"""
        delay = min(self.initial_delay * (2 ** attempt), self.max_delay)
        logger.debug(f"Waiting {delay}s before retry...")
        await asyncio.sleep(delay)
    
    async def execute_batch(
        self,
        tests: list,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        max_concurrent: int = 5,
        documentation_text: Optional[str] = None
    ) -> list:
        """Execute multiple tests concurrently with rate limiting"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(endpoint, test_data):
            async with semaphore:
                return await self.execute_test(
                    endpoint, test_data, base_url, headers, 1, documentation_text
                )
        
        tasks = [
            execute_with_semaphore(endpoint, test_data)
            for endpoint, test_data in tests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                endpoint, test_data = tests[i]
                processed_results.append({
                    "status": "failed",
                    "attempt_number": 1,
                    "request_data": test_data,
                    "request_headers": headers or {},
                    "response_data": None,
                    "response_status": None,
                    "response_headers": None,
                    "execution_time": 0.0,
                    "error_message": f"Exception during execution: {str(result)}",
                    "error_type": "EXECUTION_ERROR",
                    "timestamp": datetime.utcnow()
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _is_repeating_error(self, path: str, error_response: str) -> bool:
        """
        Detect if the same error is repeating
        This means AI is not actually fixing the issue!
        """
        if path not in self.failed_attempts:
            return False
        
        attempts = self.failed_attempts[path]
        if len(attempts) < 2:
            return False
        
        # Check if last 2 errors are identical
        last_errors = [str(a.get('error', '')) for a in attempts[-2:]]
        
        # Same error message = AI is hallucinating fixes
        if len(set(last_errors)) == 1 and last_errors[0]:
            logger.warning(f"🔴 REPEATING ERROR DETECTED: {last_errors[0][:100]}")
            return True
        
        return False
    
    async def _force_different_payload(
        self,
        endpoint: Dict[str, Any],
        current_payload: Dict[str, Any],
        error_response: Dict[str, Any],
        documentation_text: Optional[str]
    ) -> Dict[str, Any]:
        """
        Force AI to generate a COMPLETELY DIFFERENT payload
        Used when AI keeps returning the same broken payload
        """
        if not self.ai_provider:
            return current_payload
        
        try:
            # Extract all previous failed payloads
            path = endpoint.get('path', '')
            failed_payloads = [a['payload'] for a in self.failed_attempts.get(path, [])]
            
            prompt = f"""
You are an API testing expert. You have failed {len(failed_payloads)} times with similar payloads.

🎯 YOUR MISSION: Generate a COMPLETELY DIFFERENT valid payload that will succeed.

📍 ENDPOINT: {endpoint.get('method')} {endpoint.get('path')}

❌ FAILED PAYLOADS (DO NOT USE THESE):
{json.dumps(failed_payloads, indent=2)}

💥 ERROR RESPONSE:
{json.dumps(error_response, indent=2)[:500]}

📚 DOCUMENTATION (find the CORRECT way):
{documentation_text[:8000] if documentation_text else 'Not available'}

🔥 CRITICAL REQUIREMENTS (Bug #20 FIX):
1. READ THE ERROR MESSAGE - it tells you exactly what's wrong!
2. FIND EXAMPLES in documentation - copy their structure exactly
3. CHECK FIELD TYPES: strings need quotes, numbers don't, booleans are true/false
4. REQUIRED FIELDS: The error message lists missing fields - ADD THEM ALL
5. ENUM VALUES: If error says "must be one of [X, Y, Z]", use EXACTLY one of those values
6. FORMAT VALIDATION: If error mentions "invalid format", find the correct format in docs
7. DO NOT REPEAT FAILED ATTEMPTS - use completely different values
8. MATCH SCHEMA: If docs show field structure, copy it exactly
9. NO EXTRA FIELDS: Only include fields mentioned in documentation
10. USE REALISTIC DATA: Valid emails, proper dates (YYYY-MM-DD), real phone numbers

💡 COMMON MISTAKES TO AVOID:
- Using "string" instead of actual string value
- Missing required fields mentioned in error
- Wrong data types (e.g., string "123" instead of number 123)
- Invalid enum values
- Malformed dates/emails
- Path parameters in request body

✅ SUCCESS PATTERN:
Look for "Example Request" or "Sample Payload" in documentation.
Copy that structure EXACTLY, but with different realistic values.

Return ONLY the JSON payload. No markdown, no code blocks, no explanations.
"""
            
            response = await self.ai_provider.generate_content(prompt, temperature=0.7)  # Higher temp for more variation
            new_payload = self._parse_json(response)
            
            # Verify it's actually different
            if new_payload and new_payload not in failed_payloads:
                changes = self._get_changes(current_payload, new_payload)
                logger.info(f"🔄 Forced {len(changes)} changes to generate different payload")
                return new_payload
            else:
                logger.warning("AI still returned similar payload")
                return current_payload
        
        except Exception as e:
            logger.error(f"Error forcing different payload: {e}")
            return current_payload
    
    def get_vector_db_stats(self) -> Dict[str, Any]:
        """Get Vector DB usage statistics"""
        return {
            "vector_db_enabled": self.vector_store is not None,
            "total_queries": self.vector_db_queries,
            "total_context_saved_chars": self.context_size_saved,
            "avg_context_saved_per_query": self.context_size_saved // self.vector_db_queries if self.vector_db_queries > 0 else 0
        }
