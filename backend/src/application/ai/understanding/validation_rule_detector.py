"""
Validation Rule Detector - Learn validation rules from examples and errors
Part of Universal Autonomous API Testing System
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from src.infrastructure.ai.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class ValidationRule(BaseModel):
    """Represents a validation rule for a field"""
    field_name: str
    rule_type: str  # "format", "length", "range", "pattern", "enum", "custom"
    rule_description: str
    validation_logic: str  # Executable validation logic
    error_message: str
    examples_valid: List[Any]
    examples_invalid: List[Any]
    confidence: float  # 0.0 to 1.0
    learned_from: str  # "documentation", "examples", "error_messages"


class ValidationRuleDetector:
    """
    Detect and learn validation rules from documentation, examples, and error messages
    
    Learns rules like:
    - Phone must be 10 digits (from examples: "9876543210")
    - Email must be valid format (from examples: "user@example.com")
    - Weight must be > 0 (from error: "Weight must be greater than 0")
    - Pincode must be 6 digits (from examples: "411014")
    - GST format: 22AAAAA0000A1Z5 (from examples)
    """
    
    def __init__(self):
        self.gemini = GeminiProvider()
        self.common_patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone_india': r'^\+?91[-\s]?[6-9]\d{9}$',
            'phone_10digit': r'^\d{10}$',
            'pincode_india': r'^\d{6}$',
            'gst_india': r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$',
            'url': r'^https?://[^\s]+$',
            'date_iso': r'^\d{4}-\d{2}-\d{2}$',
            'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        }
    
    async def detect_rules(
        self,
        raw_text: str,
        schemas: Dict[str, Any],
        examples: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect all validation rules from documentation and examples
        
        Args:
            raw_text: Raw documentation text
            schemas: Endpoint schemas with field definitions
            examples: Example requests/responses
            
        Returns:
            Dictionary with validation rules
        """
        try:
            logger.info("[SEARCH] Detecting validation rules from documentation...")
            
            # Extract rules from documentation text
            doc_rules = await self._extract_rules_from_documentation(raw_text)
            
            # Extract rules from examples
            example_rules = await self._extract_rules_from_examples(
                schemas, examples
            )
            
            # Extract rules from schema constraints
            schema_rules = self._extract_rules_from_schemas(schemas)
            
            # Merge and deduplicate rules
            all_rules = self._merge_rules(doc_rules, example_rules, schema_rules)
            
            logger.info(f"[OK] Detected {len(all_rules)} validation rules")
            
            return {
                'validation_rules': all_rules,
                'rules_by_field': self._group_rules_by_field(all_rules),
                'rules_by_type': self._group_rules_by_type(all_rules),
                'rule_summary': {
                    'total_rules': len(all_rules),
                    'high_confidence': len([r for r in all_rules if r.get('confidence', 0) >= 0.8]),
                    'learned_from_docs': len([r for r in all_rules if r.get('learned_from') == 'documentation']),
                    'learned_from_examples': len([r for r in all_rules if r.get('learned_from') == 'examples']),
                    'learned_from_schema': len([r for r in all_rules if r.get('learned_from') == 'schema'])
                }
            }
        
        except Exception as e:
            logger.error(f"[ERROR] Error detecting validation rules: {e}")
            return {
                'validation_rules': [],
                'rules_by_field': {},
                'rules_by_type': {},
                'rule_summary': {}
            }
    
    async def _extract_rules_from_documentation(
        self,
        raw_text: str
    ) -> List[Dict[str, Any]]:
        """Extract validation rules from documentation text using AI"""
        try:
            prompt = f"""
Analyze this API documentation and extract ALL validation rules.

Documentation:
{raw_text[:15000]}

Look for validation rules in:
1. Field descriptions (e.g., "phone must be 10 digits")
2. Constraints (e.g., "weight must be greater than 0")
3. Format requirements (e.g., "email must be valid format")
4. Business rules (e.g., "cannot cancel after pickup")
5. Examples that show valid formats

For EACH validation rule, extract:
- Field name
- Rule type (format, length, range, pattern, enum, custom)
- Description of the rule
- Validation logic (how to check)
- Error message (if mentioned)
- Valid examples
- Invalid examples

Common patterns to look for:
- Phone: "10 digits", "starts with 6-9", "+91-XXXXXXXXXX"
- Email: "valid email format"
- Pincode: "6 digits"
- GST: "15 characters", "format: 22AAAAA0000A1Z5"
- Weight: "must be > 0", "in kg"
- Dimensions: "in cm", "length x width x height"
- Dates: "ISO format", "YYYY-MM-DD"

Output as JSON:
{{
  "rules": [
    {{
      "field_name": "phone",
      "rule_type": "format",
      "rule_description": "Phone number must be 10 digits",
      "validation_logic": "len(phone) == 10 and phone.isdigit()",
      "error_message": "Phone must be exactly 10 digits",
      "examples_valid": ["9876543210", "8765432109"],
      "examples_invalid": ["123", "abcd123456", "+91-9876543210"],
      "confidence": 0.95,
      "learned_from": "documentation"
    }},
    {{
      "field_name": "email",
      "rule_type": "format",
      "rule_description": "Email must be valid format",
      "validation_logic": "regex: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$",
      "error_message": "Invalid email format",
      "examples_valid": ["user@example.com", "test.user@domain.co.in"],
      "examples_invalid": ["notanemail", "user@", "@domain.com"],
      "confidence": 0.9,
      "learned_from": "documentation"
    }},
    {{
      "field_name": "weight",
      "rule_type": "range",
      "rule_description": "Weight must be greater than 0",
      "validation_logic": "weight > 0",
      "error_message": "Weight must be positive",
      "examples_valid": [0.5, 10, 100.5],
      "examples_invalid": [0, -5, -10.5],
      "confidence": 1.0,
      "learned_from": "documentation"
    }}
  ]
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.2)
            result = self._parse_json_response(response)
            
            return result.get('rules', [])
        
        except Exception as e:
            logger.error(f"Error extracting rules from documentation: {e}")
            return []
    
    async def _extract_rules_from_examples(
        self,
        schemas: Dict[str, Any],
        examples: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Learn validation rules from example data"""
        try:
            if not examples:
                return []
            
            prompt = f"""
Analyze these API examples and infer validation rules.

Schemas:
{json.dumps(schemas, indent=2)[:10000]}

Examples:
{json.dumps(examples, indent=2)[:10000]}

From the examples, infer validation rules:

1. **Format Rules**: Look at example values to infer formats
   - If phone is "9876543210" → 10 digits
   - If email is "user@example.com" → email format
   - If pincode is "411014" → 6 digits

2. **Range Rules**: Look at numeric values
   - If weight is always > 0 → must be positive
   - If quantity is 1-100 → range constraint

3. **Length Rules**: Look at string lengths
   - If name is 3-50 chars → length constraint

4. **Pattern Rules**: Look for consistent patterns
   - If GST is "22AAAAA0000A1Z5" → specific format
   - If order IDs are "ORD-12345" → prefix + number

5. **Enum Rules**: Look for repeated values
   - If status is always "pending", "confirmed", "cancelled" → enum

Output as JSON:
{{
  "rules": [
    {{
      "field_name": "phone",
      "rule_type": "format",
      "rule_description": "Phone is always 10 digits (inferred from examples)",
      "validation_logic": "len(phone) == 10 and phone.isdigit()",
      "error_message": "Phone must be 10 digits",
      "examples_valid": ["9876543210"],
      "examples_invalid": ["123", "98765"],
      "confidence": 0.85,
      "learned_from": "examples"
    }}
  ]
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.2)
            result = self._parse_json_response(response)
            
            return result.get('rules', [])
        
        except Exception as e:
            logger.error(f"Error extracting rules from examples: {e}")
            return []
    
    def _extract_rules_from_schemas(
        self,
        schemas: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract validation rules from JSON schemas"""
        rules = []
        
        try:
            for endpoint, schema_data in schemas.items():
                request_schema = schema_data.get('request_schema', {})
                properties = request_schema.get('properties', {})
                required = request_schema.get('required', [])
                
                for field_name, field_schema in properties.items():
                    field_type = field_schema.get('type', 'string')
                    
                    # Required field rule
                    if field_name in required:
                        rules.append({
                            'field_name': field_name,
                            'rule_type': 'required',
                            'rule_description': f'{field_name} is required',
                            'validation_logic': f'{field_name} is not None and {field_name} != ""',
                            'error_message': f'{field_name} is required',
                            'examples_valid': ['any value'],
                            'examples_invalid': [None, ''],
                            'confidence': 1.0,
                            'learned_from': 'schema'
                        })
                    
                    # Type rule
                    rules.append({
                        'field_name': field_name,
                        'rule_type': 'type',
                        'rule_description': f'{field_name} must be {field_type}',
                        'validation_logic': f'isinstance({field_name}, {field_type})',
                        'error_message': f'{field_name} must be of type {field_type}',
                        'examples_valid': [self._get_example_for_type(field_type)],
                        'examples_invalid': ['wrong_type'],
                        'confidence': 1.0,
                        'learned_from': 'schema'
                    })
                    
                    # Length constraints
                    if 'minLength' in field_schema or 'maxLength' in field_schema:
                        min_len = field_schema.get('minLength', 0)
                        max_len = field_schema.get('maxLength', float('inf'))
                        rules.append({
                            'field_name': field_name,
                            'rule_type': 'length',
                            'rule_description': f'{field_name} length must be between {min_len} and {max_len}',
                            'validation_logic': f'{min_len} <= len({field_name}) <= {max_len}',
                            'error_message': f'{field_name} length must be between {min_len} and {max_len}',
                            'examples_valid': ['a' * (min_len + 1)],
                            'examples_invalid': ['a' * (max_len + 1)],
                            'confidence': 1.0,
                            'learned_from': 'schema'
                        })
                    
                    # Numeric range constraints
                    if field_type in ['number', 'integer']:
                        if 'minimum' in field_schema or 'maximum' in field_schema:
                            min_val = field_schema.get('minimum', float('-inf'))
                            max_val = field_schema.get('maximum', float('inf'))
                            rules.append({
                                'field_name': field_name,
                                'rule_type': 'range',
                                'rule_description': f'{field_name} must be between {min_val} and {max_val}',
                                'validation_logic': f'{min_val} <= {field_name} <= {max_val}',
                                'error_message': f'{field_name} must be between {min_val} and {max_val}',
                                'examples_valid': [min_val + 1],
                                'examples_invalid': [min_val - 1],
                                'confidence': 1.0,
                                'learned_from': 'schema'
                            })
                    
                    # Pattern constraints
                    if 'pattern' in field_schema:
                        pattern = field_schema['pattern']
                        rules.append({
                            'field_name': field_name,
                            'rule_type': 'pattern',
                            'rule_description': f'{field_name} must match pattern: {pattern}',
                            'validation_logic': f'regex: {pattern}',
                            'error_message': f'{field_name} format is invalid',
                            'examples_valid': [],
                            'examples_invalid': [],
                            'confidence': 1.0,
                            'learned_from': 'schema'
                        })
                    
                    # Enum constraints
                    if 'enum' in field_schema:
                        enum_values = field_schema['enum']
                        rules.append({
                            'field_name': field_name,
                            'rule_type': 'enum',
                            'rule_description': f'{field_name} must be one of: {", ".join(map(str, enum_values))}',
                            'validation_logic': f'{field_name} in {enum_values}',
                            'error_message': f'{field_name} must be one of: {", ".join(map(str, enum_values))}',
                            'examples_valid': enum_values,
                            'examples_invalid': ['invalid_value'],
                            'confidence': 1.0,
                            'learned_from': 'schema'
                        })
        
        except Exception as e:
            logger.error(f"Error extracting rules from schemas: {e}")
        
        return rules
    
    def _merge_rules(
        self,
        *rule_lists: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge rules from different sources, removing duplicates"""
        merged = {}
        
        for rules in rule_lists:
            for rule in rules:
                field_name = rule.get('field_name')
                rule_type = rule.get('rule_type')
                key = f"{field_name}_{rule_type}"
                
                # Keep rule with higher confidence
                if key not in merged or rule.get('confidence', 0) > merged[key].get('confidence', 0):
                    merged[key] = rule
        
        return list(merged.values())
    
    def _group_rules_by_field(
        self,
        rules: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group rules by field name"""
        grouped = {}
        for rule in rules:
            field = rule.get('field_name', 'unknown')
            if field not in grouped:
                grouped[field] = []
            grouped[field].append(rule)
        return grouped
    
    def _group_rules_by_type(
        self,
        rules: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group rules by rule type"""
        grouped = {}
        for rule in rules:
            rtype = rule.get('rule_type', 'unknown')
            if rtype not in grouped:
                grouped[rtype] = []
            grouped[rtype].append(rule)
        return grouped
    
    def _get_example_for_type(self, field_type: str) -> Any:
        """Get example value for a field type"""
        examples = {
            'string': 'example_string',
            'number': 123.45,
            'integer': 123,
            'boolean': True,
            'array': [],
            'object': {}
        }
        return examples.get(field_type, 'example')
    
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
    
    async def learn_from_error(
        self,
        error_message: str,
        field_name: str,
        attempted_value: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Learn validation rule from error message
        
        Args:
            error_message: Error message from API
            field_name: Field that caused the error
            attempted_value: Value that was rejected
            
        Returns:
            Learned validation rule
        """
        try:
            logger.info(f"[DOC] Learning from error: {error_message}")
            
            prompt = f"""
Analyze this API error and extract the validation rule.

Error Message: {error_message}
Field Name: {field_name}
Attempted Value: {attempted_value}

Extract the validation rule that was violated:
- What is the rule?
- How should the field be validated?
- What are valid examples?
- What are invalid examples?

Output as JSON:
{{
  "field_name": "{field_name}",
  "rule_type": "format|length|range|pattern|enum|custom",
  "rule_description": "Description of the rule",
  "validation_logic": "How to validate",
  "error_message": "{error_message}",
  "examples_valid": ["valid1", "valid2"],
  "examples_invalid": ["{attempted_value}"],
  "confidence": 0.9,
  "learned_from": "error_messages"
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.2)
            result = self._parse_json_response(response)
            
            logger.info(f"[OK] Learned validation rule from error")
            
            return result
        
        except Exception as e:
            logger.error(f"Error learning from error: {e}")
            return None

