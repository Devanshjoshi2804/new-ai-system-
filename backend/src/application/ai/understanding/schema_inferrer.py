"""
Schema Inferrer - Infer JSON schemas from examples
"""
import json
import logging
from typing import List, Dict, Any, Optional

from src.infrastructure.ai.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class SchemaInferrer:
    """Infer JSON schemas from example requests/responses"""
    
    def __init__(self):
        self.gemini = GeminiProvider()
    
    async def infer_schema_from_examples(
        self,
        examples: List[Dict[str, Any]],
        schema_type: str = "request"  # "request" or "response"
    ) -> Dict[str, Any]:
        """
        Use AI to infer JSON Schema from examples
        Handles nested objects, arrays, optional fields
        
        Args:
            examples: List of example JSON objects
            schema_type: Type of schema (request or response)
            
        Returns:
            JSON Schema (draft-07 format)
        """
        try:
            logger.info(f"[SEARCH] Inferring {schema_type} schema from {len(examples)} examples...")
            
            prompt = f"""
Infer a JSON Schema from these example {schema_type} objects:

Examples:
{json.dumps(examples, indent=2)}

Provide a JSON Schema (draft-07) that describes these objects:
- Field types (string, number, integer, boolean, object, array, null)
- Required vs optional fields (field is required if present in ALL examples)
- Nested structures (objects within objects)
- Array item types
- Enum values (if a field has same limited values across examples)
- Constraints:
  - minLength, maxLength for strings
  - minimum, maximum for numbers
  - pattern (regex) for formatted strings (emails, phones, dates)
  - format (email, date-time, uri, uuid, etc.)

Consider:
- If a field appears in all examples, it's required
- If a field has same values across examples, consider enum
- If a field looks like email/phone/date, add format/pattern
- Infer realistic constraints from example values

Output ONLY valid JSON Schema (draft-07):
{{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {{
    "field1": {{
      "type": "string",
      "description": "Description of field1",
      "minLength": 1,
      "maxLength": 100
    }},
    "field2": {{
      "type": "number",
      "description": "Description of field2",
      "minimum": 0
    }},
    "nested": {{
      "type": "object",
      "properties": {{
        "subfield": {{"type": "string"}}
      }},
      "required": ["subfield"]
    }},
    "items": {{
      "type": "array",
      "items": {{
        "type": "object",
        "properties": {{
          "id": {{"type": "string"}},
          "name": {{"type": "string"}}
        }}
      }}
    }}
  }},
  "required": ["field1", "field2"],
  "additionalProperties": false
}}

Return ONLY valid JSON Schema, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.1)
            
            # Parse JSON from response
            schema_text = response.strip()
            if "```json" in schema_text:
                schema_text = schema_text.split("```json")[1].split("```")[0].strip()
            elif "```" in schema_text:
                schema_text = schema_text.split("```")[1].split("```")[0].strip()
            
            schema = json.loads(schema_text)
            
            logger.info(f"[OK] Inferred schema with {len(schema.get('properties', {}))} properties")
            
            return schema
        
        except Exception as e:
            logger.error(f"[ERROR] Error inferring schema: {e}")
            # Return basic schema on error
            return {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {},
                "additionalProperties": True
            }
    
    async def infer_field_type(
        self,
        field_name: str,
        example_values: List[Any]
    ) -> Dict[str, Any]:
        """
        Infer field type and constraints from example values
        
        Args:
            field_name: Name of the field
            example_values: List of example values for this field
            
        Returns:
            Field schema
        """
        try:
            logger.info(f"[SEARCH] Inferring type for field '{field_name}'...")
            
            prompt = f"""
Infer the JSON Schema for this field:

Field Name: {field_name}
Example Values: {json.dumps(example_values, indent=2)}

Determine:
- Type (string, number, integer, boolean, array, object, null)
- Format (if applicable: email, date-time, uri, uuid, etc.)
- Pattern (regex for validation)
- Constraints (min, max, minLength, maxLength, enum)
- Description (what this field represents)

Output as JSON Schema property definition:
{{
  "type": "string",
  "description": "User email address",
  "format": "email",
  "minLength": 5,
  "maxLength": 100
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.1)
            
            # Parse JSON from response
            field_schema_text = response.strip()
            if "```json" in field_schema_text:
                field_schema_text = field_schema_text.split("```json")[1].split("```")[0].strip()
            elif "```" in field_schema_text:
                field_schema_text = field_schema_text.split("```")[1].split("```")[0].strip()
            
            field_schema = json.loads(field_schema_text)
            
            logger.info(f"[OK] Inferred type for '{field_name}': {field_schema.get('type')}")
            
            return field_schema
        
        except Exception as e:
            logger.error(f"[ERROR] Error inferring field type: {e}")
            return {"type": "string"}
    
    async def merge_schemas(
        self,
        schemas: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge multiple schemas into one comprehensive schema
        
        Args:
            schemas: List of JSON schemas to merge
            
        Returns:
            Merged JSON schema
        """
        try:
            logger.info(f"[INFO] Merging {len(schemas)} schemas...")
            
            prompt = f"""
Merge these JSON schemas into one comprehensive schema:

Schemas:
{json.dumps(schemas, indent=2)}

Create a merged schema that:
- Includes all properties from all schemas
- Uses most specific type (if conflicts, use union types)
- Field is required only if required in ALL schemas
- Uses most restrictive constraints (smallest max, largest min)
- Combines descriptions

Output as JSON Schema (draft-07):

Return ONLY valid JSON Schema, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.1)
            
            # Parse JSON from response
            merged_text = response.strip()
            if "```json" in merged_text:
                merged_text = merged_text.split("```json")[1].split("```")[0].strip()
            elif "```" in merged_text:
                merged_text = merged_text.split("```")[1].split("```")[0].strip()
            
            merged_schema = json.loads(merged_text)
            
            logger.info(f"[OK] Merged schema with {len(merged_schema.get('properties', {}))} properties")
            
            return merged_schema
        
        except Exception as e:
            logger.error(f"[ERROR] Error merging schemas: {e}")
            return schemas[0] if schemas else {}
    
    async def validate_data_against_schema(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate data against schema and return validation result
        
        Args:
            data: Data to validate
            schema: JSON schema
            
        Returns:
            Validation result with errors
        """
        try:
            from jsonschema import validate, ValidationError
            
            logger.info("[OK] Validating data against schema...")
            
            try:
                validate(instance=data, schema=schema)
                return {
                    'valid': True,
                    'errors': []
                }
            except ValidationError as e:
                return {
                    'valid': False,
                    'errors': [{
                        'message': e.message,
                        'path': list(e.path),
                        'schema_path': list(e.schema_path)
                    }]
                }
        
        except Exception as e:
            logger.error(f"[ERROR] Error validating data: {e}")
            return {
                'valid': False,
                'errors': [{'message': str(e)}]
            }
    
    async def generate_sample_data(
        self,
        schema: Dict[str, Any],
        realistic: bool = True
    ) -> Dict[str, Any]:
        """
        Generate sample data that conforms to schema
        
        Args:
            schema: JSON schema
            realistic: Whether to generate realistic data (vs random)
            
        Returns:
            Sample data object
        """
        try:
            logger.info("[INFO] Generating sample data from schema...")
            
            if realistic:
                prompt = f"""
Generate realistic sample data that conforms to this JSON schema:

Schema:
{json.dumps(schema, indent=2)}

Generate realistic, production-like data:
- Use real-looking names, emails, addresses
- Use realistic numbers and dates
- Follow all constraints (min, max, pattern, format)
- Include all required fields
- Use realistic values for optional fields

Output as JSON:

Return ONLY valid JSON matching the schema, no markdown, no explanations.
"""
            else:
                prompt = f"""
Generate sample data that conforms to this JSON schema:

Schema:
{json.dumps(schema, indent=2)}

Generate valid data:
- Include all required fields
- Follow all constraints
- Use simple test values

Output as JSON:

Return ONLY valid JSON matching the schema, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.7)
            
            # Parse JSON from response
            data_text = response.strip()
            if "```json" in data_text:
                data_text = data_text.split("```json")[1].split("```")[0].strip()
            elif "```" in data_text:
                data_text = data_text.split("```")[1].split("```")[0].strip()
            
            sample_data = json.loads(data_text)
            
            logger.info("[OK] Generated sample data")
            
            return sample_data
        
        except Exception as e:
            logger.error(f"[ERROR] Error generating sample data: {e}")
            return {}

