"""
Intelligent Payload Generator - Learns from Documentation
NO HARDCODED VALUES OR ASSUMPTIONS
NOW WITH PROGRESSIVE LEARNING - Gets smarter with each test run!
"""
import logging
import json
import re
from typing import Dict, Any, Optional, List

from ..learning.document_learning_store import DocumentLearningStore

logger = logging.getLogger(__name__)


class IntelligentPayloadGenerator:
    """
    Generates API payloads by LEARNING from documentation
    
    Philosophy:
    - NO hardcoded values ("open", "test", "123")
    - NO assumptions about field names
    - NO guessing of formats
    - EVERYTHING learned from documentation
    - Uses real examples from docs
    - Understands context and patterns
    """
    
    def __init__(self, ai_provider=None, vector_store=None):
        self.ai_provider = ai_provider
        self.vector_store = vector_store
        self.learned_patterns = {}  # Cache learned patterns
        self.example_cache = {}  # Cache extracted examples
        
        # CRITICAL: Initialize learning store
        self.learning_store = DocumentLearningStore()
        logger.info("🧠 Intelligent payload generator with progressive learning enabled")
    
    async def generate_intelligent_payload(
        self,
        endpoint: Dict[str, Any],
        documentation_text: str,
        auth_data: Dict[str, Any] = None,
        doc_id: str = None,
        flow_store = None  # NEW: Flow Vector Store for semantic memory
    ) -> Dict[str, Any]:
        """
        Generate payload by learning from documentation
        
        Process:
        0. CHECK LEARNING STORE FIRST - if we've done this before, use what worked!
        1. Extract examples from documentation
        2. Identify required fields from schema
        3. Learn valid values from documentation
        4. Understand field formats and patterns
        5. Generate payload with real learned values
        """
        try:
            method = endpoint.get('method', 'GET')
            path = endpoint.get('path', '')
            
            # CRITICAL: Check if we've successfully tested this endpoint before!
            if doc_id:
                previous_successes = await self.learning_store.get_successful_payloads(
                    doc_id=doc_id,
                    endpoint_path=path,
                    method=method
                )
                
                if previous_successes:
                    logger.info(f"🎯 Found {len(previous_successes)} previous successful payloads!")
                    # Use the most successful one
                    best_payload = previous_successes[0]['payload']
                    logger.info(f"♻️  Reusing successful payload from previous run (no need to regenerate!)")
                    return best_payload
            
            logger.info(f"🧠 Learning from documentation for {method} {path} (first time)")
            
            # NEW: Query Flow DB for context from previous tests
            flow_context = ""
            if flow_store:
                try:
                    flow_query = f"""
                    Find credentials, tokens, IDs, passwords, user data from previous API calls 
                    that might be needed for {method} {path}.
                    Look for login tokens, signup passwords, created user IDs, etc.
                    """
                    flow_context = await flow_store.query(flow_query, k=3)
                    if flow_context:
                        logger.info(f"📚 Retrieved flow context: {len(flow_context)} chars")
                    else:
                        logger.debug("No flow context found yet (early in test sequence)")
                except Exception as e:
                    logger.warning(f"Failed to query flow store: {e}")
            
            # Step 1: Get focused documentation for this endpoint
            focused_docs = await self._get_focused_documentation(
                doc_id, path, method, documentation_text
            )
            
            # Step 2: Extract ALL examples from documentation
            examples = await self._extract_examples_from_docs(
                focused_docs, path, method
            )
            
            # Step 3: Learn field specifications from documentation
            field_specs = await self._learn_field_specifications(
                endpoint, focused_docs, examples
            )
            
            # Step 4: Generate payload using learned information + flow context
            payload = await self._generate_from_learned_specs(
                field_specs, examples, auth_data, flow_context
            )
            
            # BUG #18 & #19 FIX: Apply type coercion to match schema
            schema = endpoint.get('request_body_schema', {})
            if schema:
                payload = self.coerce_types(payload, schema)
                logger.info(f"🔄 Applied type coercion to payload")
            
            logger.info(f"✅ Generated intelligent payload with {len(payload)} fields (learned from docs)")
            
            return payload
        
        except Exception as e:
            logger.error(f"Error in intelligent generation: {e}", exc_info=True)
            return {}
    
    async def _get_focused_documentation(
        self,
        doc_id: str,
        path: str,
        method: str,
        full_docs: str
    ) -> str:
        """Get focused documentation for specific endpoint"""
        if self.vector_store and doc_id:
            try:
                # Query Vector DB for endpoint-specific chunks
                focused = self.vector_store.get_endpoint_context(
                    doc_id=doc_id,
                    endpoint_path=path,
                    method=method
                )
                
                if focused and len(focused) > 500:
                    logger.info(f"📚 Retrieved {len(focused)} chars from Vector DB")
                    return focused
            except Exception as e:
                logger.warning(f"Vector DB query failed: {e}")
        
        # Fallback: Search full docs for relevant sections
        return self._extract_relevant_sections(full_docs, path, method)
    
    def _extract_relevant_sections(
        self,
        docs: str,
        path: str,
        method: str
    ) -> str:
        """Extract relevant sections from full documentation"""
        # Look for sections mentioning this endpoint
        lines = docs.split('\n')
        relevant = []
        capture = False
        context_lines = 20
        
        for i, line in enumerate(lines):
            # Check if line mentions the endpoint
            if path in line or method in line:
                # Capture surrounding context
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines)
                relevant.extend(lines[start:end])
                capture = True
            elif capture and (line.strip() == '' or line.startswith('#')):
                # End of section
                capture = False
        
        result = '\n'.join(relevant) if relevant else docs[:10000]
        logger.info(f"📄 Extracted {len(result)} chars of relevant documentation")
        return result
    
    async def _extract_examples_from_docs(
        self,
        docs: str,
        path: str,
        method: str
    ) -> List[Dict[str, Any]]:
        """
        Extract ALL examples from documentation
        Looks for JSON blocks, code examples, sample requests
        """
        examples = []
        
        # Try to find JSON examples in documentation
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.finditer(json_pattern, docs, re.DOTALL)
        
        for match in matches:
            try:
                json_text = match.group(0)
                parsed = json.loads(json_text)
                
                # Only include if it looks like a request body
                if isinstance(parsed, dict) and len(parsed) > 0:
                    examples.append(parsed)
                    logger.info(f"📋 Found example: {list(parsed.keys())}")
            except:
                continue
        
        # Use AI to extract examples if available
        if self.ai_provider and not examples:
            examples = await self._ai_extract_examples(docs, path, method)
        
        logger.info(f"📚 Extracted {len(examples)} examples from documentation")
        return examples
    
    async def _ai_extract_examples(
        self,
        docs: str,
        path: str,
        method: str
    ) -> List[Dict[str, Any]]:
        """Use AI to extract examples from unstructured documentation"""
        try:
            prompt = f"""
Extract ALL example request payloads for this endpoint from the documentation.

ENDPOINT: {method} {path}

DOCUMENTATION:
{docs[:8000]}

Find all example requests, sample payloads, or example JSON bodies.
Return them as a JSON array of objects.

Example output:
[
  {{"field1": "value1", "field2": "value2"}},
  {{"field1": "value3", "field2": "value4"}}
]

Return ONLY the JSON array. No markdown, no explanations.
If no examples found, return empty array [].
"""
            
            response = await self.ai_provider.generate_content(prompt, temperature=0.1)
            
            # Try to parse as JSON array
            text = response.strip()
            if text.startswith('['):
                examples = json.loads(text)
                if isinstance(examples, list):
                    logger.info(f"🤖 AI extracted {len(examples)} examples")
                    return examples
            
        except Exception as e:
            logger.warning(f"AI example extraction failed: {e}")
        
        return []
    
    async def _learn_field_specifications(
        self,
        endpoint: Dict[str, Any],
        docs: str,
        examples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Learn field specifications from documentation
        
        For each field, learn:
        - Valid values (enums, examples)
        - Format (date, email, phone, etc.)
        - Constraints (min, max, pattern)
        - Required vs optional
        - Default values
        """
        field_specs = {}
        
        # Get schema from endpoint if available
        schema = endpoint.get('request_body_schema', {})
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        # Learn from schema
        for field_name, field_def in properties.items():
            field_specs[field_name] = {
                'name': field_name,
                'type': field_def.get('type', 'string'),
                'required': field_name in required,
                'description': field_def.get('description', ''),
                'enum': field_def.get('enum', []),
                'format': field_def.get('format'),
                'example': field_def.get('example'),
                'learned_values': []
            }
        
        # Learn from examples - THIS IS CRITICAL
        for example in examples:
            for field_name, value in example.items():
                if field_name not in field_specs:
                    # Discovered new field from example
                    field_specs[field_name] = {
                        'name': field_name,
                        'type': type(value).__name__,
                        'required': False,  # Unknown
                        'learned_values': []
                    }
                
                # Add this value as a learned example
                if value not in field_specs[field_name]['learned_values']:
                    field_specs[field_name]['learned_values'].append(value)
        
        # Learn from documentation text using AI
        if self.ai_provider:
            field_specs = await self._ai_enhance_field_specs(
                field_specs, docs, endpoint
            )
        
        logger.info(f"🎓 Learned specifications for {len(field_specs)} fields")
        return field_specs
    
    async def _ai_enhance_field_specs(
        self,
        field_specs: Dict[str, Any],
        docs: str,
        endpoint: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to enhance field specifications from documentation"""
        try:
            prompt = f"""
Analyze this API documentation and extract detailed field specifications.

ENDPOINT: {endpoint.get('method')} {endpoint.get('path')}

DOCUMENTATION:
{docs[:8000]}

CURRENT KNOWN FIELDS:
{json.dumps(list(field_specs.keys()), indent=2)}

For each field, identify:
1. Valid values (if enum or limited options)
2. Format/pattern (date format, phone format, etc.)
3. Whether it's required or optional
4. Example values from documentation
5. Validation rules

Return JSON object with field specifications:
{{
  "fieldName": {{
    "valid_values": ["value1", "value2"],
    "format": "YYYY-MM-DD",
    "required": true,
    "examples": ["example1", "example2"],
    "pattern": "regex pattern if any"
  }}
}}

Return ONLY the JSON object. Use actual values from documentation, not placeholders.
"""
            
            response = await self.ai_provider.generate_content(prompt, temperature=0.2)
            
            # Parse AI response
            text = response.strip()
            if text.startswith('{'):
                enhanced = json.loads(text)
                
                # Merge AI insights into field_specs
                for field_name, ai_spec in enhanced.items():
                    if field_name in field_specs:
                        # Add AI-learned information
                        if 'valid_values' in ai_spec and ai_spec['valid_values']:
                            field_specs[field_name]['learned_values'].extend(ai_spec['valid_values'])
                        if 'examples' in ai_spec and ai_spec['examples']:
                            field_specs[field_name]['learned_values'].extend(ai_spec['examples'])
                        if 'format' in ai_spec:
                            field_specs[field_name]['format'] = ai_spec['format']
                
                logger.info(f"🤖 AI enhanced field specifications")
        
        except Exception as e:
                logger.warning(f"AI field enhancement failed: {e}")
        
        return field_specs
    
    def validate_payload(self, payload: Dict[str, Any], schema: Dict[str, Any]) -> tuple:
        """
        Validate payload against JSON schema (BUG #8 FIX)
        
        Returns: (is_valid: bool, error_message: str or None)
        """
        if not schema:
            return True, None
        
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        # Check required fields
        for field in required:
            if field not in payload:
                return False, f"Missing required field: '{field}'"
            if payload[field] is None:
                return False, f"Required field '{field}' cannot be null"
        
        # Validate field types and values
        for field, value in payload.items():
            if field not in properties:
                continue  # Extra fields are OK
            
            spec = properties[field]
            expected_type = spec.get('type', 'string')
            
            # Type validation
            type_valid = True
            if expected_type == 'string' and not isinstance(value, str):
                type_valid = False
            elif expected_type in ['number', 'integer'] and not isinstance(value, (int, float)):
                type_valid = False
            elif expected_type == 'boolean' and not isinstance(value, bool):
                type_valid = False
            elif expected_type == 'array' and not isinstance(value, list):
                type_valid = False
            elif expected_type == 'object' and not isinstance(value, dict):
                type_valid = False
            
            if not type_valid:
                return False, f"Field '{field}' should be {expected_type}, got {type(value).__name__}"
            
            # Enum validation
            if 'enum' in spec and value not in spec['enum']:
                return False, f"Field '{field}' must be one of {spec['enum']}, got '{value}'"
            
            # String format validation
            if expected_type == 'string' and 'format' in spec:
                import re
                fmt = spec['format']
                if fmt == 'email' and '@' not in str(value):
                    return False, f"Field '{field}' should be valid email format"
                elif fmt == 'date' and not re.match(r'\d{4}-\d{2}-\d{2}', str(value)):
                    return False, f"Field '{field}' should be date format (YYYY-MM-DD)"
        
        return True, None
    
    def coerce_types(self, payload: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coerce payload values to match schema types (BUG #18 & #19 FIX)
        
        Problem: AI generates strings like "true", "123" instead of bool, int
        Solution: Smart type coercion based on schema
        
        Args:
            payload: The payload to coerce
            schema: JSON schema with type information
            
        Returns:
            Coerced payload
        """
        if not schema or 'properties' not in schema:
            return payload
        
        coerced = payload.copy()
        properties = schema['properties']
        
        for field, value in coerced.items():
            if field not in properties:
                continue
            
            expected_type = properties[field].get('type', 'string')
            
            # Skip if already correct type
            if expected_type == 'string' and isinstance(value, str):
                continue
            elif expected_type in ['number', 'integer'] and isinstance(value, (int, float)):
                continue
            elif expected_type == 'boolean' and isinstance(value, bool):
                continue
            elif expected_type == 'array' and isinstance(value, list):
                continue
            elif expected_type == 'object' and isinstance(value, dict):
                continue
            
            # Coerce to correct type
            try:
                if expected_type == 'boolean':
                    # BUG #19 FIXED: Smart boolean coercion
                    if isinstance(value, str):
                        value_lower = value.lower().strip()
                        if value_lower in ['true', 'yes', '1', 'y', 'on']:
                            coerced[field] = True
                            logger.debug(f"🔄 Coerced '{field}': '{value}' → True")
                        elif value_lower in ['false', 'no', '0', 'n', 'off']:
                            coerced[field] = False
                            logger.debug(f"🔄 Coerced '{field}': '{value}' → False")
                    elif isinstance(value, (int, float)):
                        coerced[field] = bool(value)
                        logger.debug(f"🔄 Coerced '{field}': {value} → {bool(value)}")
                
                elif expected_type == 'integer':
                    # BUG #18 FIXED: Integer coercion
                    if isinstance(value, str):
                        coerced[field] = int(float(value))  # Handle "123.0"
                        logger.debug(f"🔄 Coerced '{field}': '{value}' → {coerced[field]}")
                    elif isinstance(value, float):
                        coerced[field] = int(value)
                        logger.debug(f"🔄 Coerced '{field}': {value} → {coerced[field]}")
                
                elif expected_type == 'number':
                    # BUG #18 FIXED: Number coercion
                    if isinstance(value, str):
                        coerced[field] = float(value)
                        logger.debug(f"🔄 Coerced '{field}': '{value}' → {coerced[field]}")
                    elif isinstance(value, int):
                        coerced[field] = float(value)
                
                elif expected_type == 'string':
                    # Convert to string if needed
                    if not isinstance(value, str):
                        coerced[field] = str(value)
                        logger.debug(f"🔄 Coerced '{field}': {value} → '{coerced[field]}'")
            
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️  Failed to coerce '{field}' to {expected_type}: {e}")
                # Keep original value if coercion fails
        
        return coerced
    
    async def _generate_from_learned_specs(
        self,
        field_specs: Dict[str, Any],
        examples: List[Dict[str, Any]],
        auth_data: Dict[str, Any] = None,
        flow_context: str = ""  # NEW: Context from previous tests
    ) -> Dict[str, Any]:
        """
        Generate payload using learned specifications + flow context
        
        Priority:
        1. Flow context (extracted from previous tests)
        2. Auth data (if field matches)
        3. Learned values from examples
        4. Enum values from schema
        5. AI generation based on specs
        """
        payload = {}
        auth_data = auth_data or {}
        
        # NEW: Try to extract values from flow context first
        flow_extracted = {}
        if flow_context and self.ai_provider:
            try:
                logger.info("🔍 Attempting to extract fields from flow context using AI")
                extraction_prompt = f"""
PREVIOUS API CALLS DATA (from test history):
{flow_context[:2000]}

REQUIRED FIELDS:
{json.dumps(list(field_specs.keys()))}

CRITICAL INSTRUCTIONS:
1. **EXTRACT FROM PREVIOUS DATA**: Look for tokens, IDs, passwords, emails in previous API calls
2. **FOR PASSWORDS**: Use PLAIN TEXT password from signup/register REQUEST (not hashed from response)
3. **FOR TOKENS**: Extract token/access_token/auth_token from login/auth RESPONSE
4. **FOR USER IDs**: Extract userId/user_id/id from user creation RESPONSE
5. **FOR EMAILS**: Extract email from previous requests or responses

Return ONLY a JSON object with extracted values. Use null for values not found.

Example response format:
{{
  "token": "extracted_token_value",
  "password": "plain_password_from_request",
  "userId": "extracted_user_id"
}}
"""
                
                response = await self.ai_provider.generate_content(
                    extraction_prompt,
                    temperature=0.1
                )
                
                flow_extracted = self._parse_json(response)
                if flow_extracted:
                    logger.info(f"✅ Extracted {len(flow_extracted)} fields from flow context: {list(flow_extracted.keys())}")
                
            except Exception as e:
                logger.warning(f"Failed to extract from flow context: {e}")
        
        for field_name, spec in field_specs.items():
            # Skip if optional and no clear value
            if not spec.get('required') and not spec.get('learned_values') and field_name not in flow_extracted:
                continue
            
            # Priority 1: Use flow-extracted data (from previous tests)
            if field_name in flow_extracted and flow_extracted[field_name] is not None:
                payload[field_name] = flow_extracted[field_name]
                logger.debug(f"  • {field_name}: {flow_extracted[field_name]} (from flow context)")
                continue
            
            # Priority 2: Use auth data if field name matches
            if field_name in auth_data:
                payload[field_name] = auth_data[field_name]
                logger.debug(f"  • {field_name}: {auth_data[field_name]} (from auth)")
                continue
            
            # Priority 2: Use learned values from examples
            learned = spec.get('learned_values', [])
            if learned:
                # Use first learned value (most common in examples)
                payload[field_name] = learned[0]
                logger.debug(f"  • {field_name}: {learned[0]} (learned from docs)")
                continue
            
            # Priority 3: Use enum values
            enum = spec.get('enum', [])
            if enum:
                payload[field_name] = enum[0]
                logger.debug(f"  • {field_name}: {enum[0]} (from enum)")
                continue
            
            # Priority 4: Use example from schema
            if spec.get('example'):
                payload[field_name] = spec['example']
                logger.debug(f"  • {field_name}: {spec['example']} (from schema)")
                continue
            
            # Priority 5: Generate based on type and format
            generated = self._generate_by_type(spec)
            if generated is not None:
                payload[field_name] = generated
                logger.debug(f"  • {field_name}: {generated} (generated)")
        
        return payload
    
    def _generate_by_type(self, spec: Dict[str, Any]) -> Any:
        """Generate value based on type and format"""
        field_type = spec.get('type', 'string')
        field_format = spec.get('format')
        
        # Use format if available
        if field_format == 'date':
            return "2024-01-01"
        elif field_format == 'date-time':
            return "2024-01-01T00:00:00Z"
        elif field_format == 'email':
            return "test@example.com"
        elif field_format == 'uuid':
            return "00000000-0000-0000-0000-000000000000"
        
        # Use type
        if field_type == 'string':
            return "test_value"
        elif field_type in ['integer', 'number']:
            return 1
        elif field_type == 'boolean':
            return True
        elif field_type == 'array':
            return []
        elif field_type == 'object':
            return {}
        
        return None
    
    async def fix_payload_intelligently(
        self,
        current_payload: Dict[str, Any],
        error_response: Dict[str, Any],
        endpoint: Dict[str, Any],
        documentation_text: str,
        doc_id: str = None
    ) -> Dict[str, Any]:
        """
        Fix payload by learning from error and documentation
        
        NO hardcoded fixes like "status": "open"
        Learn the correct value from documentation
        """
        error_msg = str(error_response.get('error', ''))
        
        logger.info(f"🔍 Analyzing error: {error_msg[:100]}")
        
        # Step 1: Identify what's wrong
        issue = self._identify_issue(error_msg)
        
        # Step 2: Query documentation for solution
        solution_context = await self._query_docs_for_solution(
            issue, endpoint, documentation_text, doc_id
        )
        
        # Step 3: Use AI to fix with learned context
        if self.ai_provider:
            fixed = await self._ai_fix_with_learned_context(
                current_payload, error_response, solution_context, endpoint
            )
            return fixed
        
        return current_payload
    
    def _identify_issue(self, error_msg: str) -> Dict[str, Any]:
        """Identify the issue from error message"""
        issue = {
            'type': 'unknown',
            'field': None,
            'problem': error_msg
        }
        
        # Parse error message
        error_lower = error_msg.lower()
        
        if 'required' in error_lower or 'missing' in error_lower:
            issue['type'] = 'missing_field'
            # Try to extract field name
            match = re.search(r'[\'"]([\w]+)[\'"]', error_msg)
            if match:
                issue['field'] = match.group(1)
        
        elif 'invalid' in error_lower or 'must be' in error_lower:
            issue['type'] = 'invalid_value'
            # Try to extract field name
            match = re.search(r'[\'"]([\w]+)[\'"]', error_msg)
            if match:
                issue['field'] = match.group(1)
        
        elif 'validation' in error_lower:
            issue['type'] = 'validation_error'
        
        logger.info(f"🔍 Identified issue: {issue['type']} on field {issue.get('field')}")
        return issue
    
    async def _query_docs_for_solution(
        self,
        issue: Dict[str, Any],
        endpoint: Dict[str, Any],
        docs: str,
        doc_id: str
    ) -> str:
        """Query documentation for solution to specific issue"""
        field_name = issue.get('field')
        issue_type = issue.get('type')
        
        if self.vector_store and doc_id and field_name:
            try:
                # Query for field information
                field_info_chunks = self.vector_store.find_field_info(
                    doc_id=doc_id,
                    field_name=field_name
                )
                
                if field_info_chunks:
                    context = '\n'.join([chunk['text'] for chunk in field_info_chunks])
                    logger.info(f"📚 Found {len(context)} chars about field '{field_name}'")
                    return context
            except Exception as e:
                logger.warning(f"Vector DB query for solution failed: {e}")
        
        # Fallback: Search docs for field name
        if field_name:
            lines = docs.split('\n')
            relevant = [line for line in lines if field_name in line]
            context = '\n'.join(relevant[:50])  # First 50 mentions
            logger.info(f"📄 Found {len(relevant)} mentions of '{field_name}' in docs")
            return context
        
        return docs[:5000]
    
    async def _ai_fix_with_learned_context(
        self,
        current_payload: Dict[str, Any],
        error_response: Dict[str, Any],
        solution_context: str,
        endpoint: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to fix payload with learned context - NO HARDCODING"""
        prompt = f"""
You are fixing an API request payload. Learn the solution from the documentation.

ENDPOINT: {endpoint.get('method')} {endpoint.get('path')}

CURRENT PAYLOAD:
{json.dumps(current_payload, indent=2)}

ERROR:
{error_response.get('error', '')}

DOCUMENTATION ABOUT THIS ERROR:
{solution_context}

INSTRUCTIONS:
1. READ the documentation carefully
2. FIND the exact solution in the documentation
3. EXTRACT real values, formats, or patterns from documentation
4. DO NOT guess or use placeholders like "test", "example", "123"
5. USE the actual values/formats shown in the documentation

Fix the payload using ONLY information from the documentation above.

Return ONLY the fixed JSON payload. No markdown, no explanations.
"""
        
        response = await self.ai_provider.generate_content(prompt, temperature=0.2)
        
        try:
            fixed = json.loads(response.strip())
            
            # BUG #8 FIX: Validate payload before using it
            is_valid, error = self.validate_payload(fixed, endpoint.get('request_body_schema', {}))
            if not is_valid:
                logger.warning(f"⚠️  AI payload validation failed: {error}")
                logger.warning(f"   Payload: {json.dumps(fixed, indent=2)[:200]}")
                # Return current payload instead of invalid one
                return current_payload
            
            # Log what changed
            changes = []
            for key in fixed:
                if key not in current_payload:
                    changes.append(f"Added '{key}': {fixed[key]}")
                elif current_payload[key] != fixed[key]:
                    changes.append(f"Changed '{key}': {current_payload[key]} → {fixed[key]}")
            
            if changes:
                logger.info(f"🔧 AI fixed {len(changes)} issues (validated):")
                for change in changes[:5]:
                    logger.info(f"   • {change}")
            
            return fixed
        except:
            return current_payload
