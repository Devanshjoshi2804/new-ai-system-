"""
Smart Test Data Generator
Generates realistic test data using AI + learned validation rules
Enhanced with Knowledge Graph integration
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random

from src.infrastructure.ai.providers.gemini_provider import GeminiProvider
from src.application.ai.learning.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class SmartDataGenerator:
    """Generate realistic test data using AI + learned validation rules"""
    
    def __init__(self):
        self.gemini = GeminiProvider()
        self.knowledge_graph = KnowledgeGraph()
    
    async def generate_test_data(
        self,
        schema: Dict[str, Any],
        scenario_type: str = "valid",  # "valid", "invalid", "edge"
        context: Optional[Dict[str, Any]] = None,
        partner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate test data based on schema and scenario type
        Uses Gemini + learned validation rules
        
        Args:
            schema: JSON schema for the data
            scenario_type: Type of scenario (valid, invalid, edge)
            context: Additional context (endpoint purpose, business rules, etc.)
            partner_id: Optional partner ID for querying learned validation rules
            
        Returns:
            Generated test data
        """
        try:
            logger.info(f"🎲 Generating {scenario_type} test data...")
            
            # Step 1: Query knowledge graph for validation rules
            learned_rules = []
            if partner_id and self.knowledge_graph:
                # Get validation rules for fields in schema
                properties = schema.get('properties', {})
                for field_name in properties.keys():
                    rules = await self.knowledge_graph.query_validation_rules(
                        field_name=field_name,
                        partner_id=partner_id
                    )
                    learned_rules.extend(rules)
                
                if learned_rules:
                    logger.info(f"✅ Found {len(learned_rules)} learned validation rules")
            
            context_str = json.dumps(context, indent=2) if context else "No additional context"
            learned_rules_str = json.dumps(learned_rules, indent=2) if learned_rules else "No learned rules"
            
            if scenario_type == "valid":
                prompt = f"""
Generate VALID test data for this schema:

Schema:
{json.dumps(schema, indent=2)}

Context:
{context_str}

Learned Validation Rules (MUST follow these):
{learned_rules_str}

Requirements:
- Include ALL required fields
- Use correct data types
- Respect all constraints (min, max, pattern, format)
- **CRITICAL: Follow ALL learned validation rules above**
- Use realistic values (real addresses, names, emails, phone numbers)
- Follow business rules from context
- Make data production-like

Examples of realistic data:
- Addresses: "123 Main Street, Mumbai, Maharashtra 400001, India"
- Names: "Rajesh Kumar", "Priya Sharma"
- Emails: "rajesh.kumar@example.com"
- Phones: "+91-9876543210"
- Weights: 15.5 (kg)
- Dimensions: {{"length": 30, "width": 20, "height": 10}} (cm)

Output as JSON matching the schema:

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            elif scenario_type == "invalid":
                prompt = f"""
Generate INVALID test data for this schema:

Schema:
{json.dumps(schema, indent=2)}

Context:
{context_str}

Requirements:
- Violate ONE constraint intelligently (missing required field, wrong type, invalid format, etc.)
- Keep other fields valid
- Make violation realistic (common user mistakes)
- Include a comment explaining what's invalid

Common violations:
- Missing required fields
- Wrong data types (string instead of number)
- Invalid formats (bad email, phone, date)
- Violating constraints (negative weight, too long string)
- Violating business rules

Output as JSON:
{{
  "data": {{...invalid data...}},
  "violation": "Description of what's invalid",
  "expected_error": "Expected error message"
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            elif scenario_type == "edge":
                prompt = f"""
Generate EDGE CASE test data for this schema:

Schema:
{json.dumps(schema, indent=2)}

Context:
{context_str}

Requirements:
- Use boundary values (min, max, zero, empty, null)
- Test limits (max length, max value, min value)
- Use special characters where applicable
- Test unusual but valid combinations

Edge cases to consider:
- Empty strings: ""
- Very long strings: (max length)
- Zero values: 0
- Negative values: -1 (if allowed)
- Maximum values: 999999
- Special characters: "Test & Co.", "O'Brien"
- Unicode: "测试", "परीक्षण"
- Dates: today, past, future, edge dates

Output as JSON:
{{
  "data": {{...edge case data...}},
  "edge_case": "Description of edge case being tested"
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            else:
                raise ValueError(f"Unknown scenario type: {scenario_type}")
            
            response = await self.gemini.generate_content(prompt, temperature=0.7)
            
            # Parse JSON from response
            data_text = response.strip()
            if "```json" in data_text:
                data_text = data_text.split("```json")[1].split("```")[0].strip()
            elif "```" in data_text:
                data_text = data_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(data_text)
            
            logger.info(f"✅ Generated {scenario_type} test data")
            
            return data
        
        except Exception as e:
            logger.error(f"❌ Error generating test data: {e}")
            return self._generate_fallback_data(schema, scenario_type)
    
    def _generate_fallback_data(
        self,
        schema: Dict[str, Any],
        scenario_type: str
    ) -> Dict[str, Any]:
        """
        Generate basic fallback data when AI generation fails
        
        Args:
            schema: JSON schema
            scenario_type: Type of scenario
            
        Returns:
            Basic test data
        """
        try:
            data = {}
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            for field_name, field_schema in properties.items():
                field_type = field_schema.get('type', 'string')
                
                if scenario_type == "invalid" and field_name in required:
                    # Skip one required field to make it invalid
                    continue
                
                if field_type == 'string':
                    if scenario_type == "edge":
                        data[field_name] = ""  # Empty string edge case
                    else:
                        data[field_name] = f"test_{field_name}"
                
                elif field_type in ['number', 'integer']:
                    if scenario_type == "edge":
                        data[field_name] = 0  # Zero edge case
                    elif scenario_type == "invalid":
                        data[field_name] = -1  # Negative (often invalid)
                    else:
                        data[field_name] = 100
                
                elif field_type == 'boolean':
                    data[field_name] = True
                
                elif field_type == 'array':
                    data[field_name] = []
                
                elif field_type == 'object':
                    data[field_name] = {}
            
            return data
        
        except Exception as e:
            logger.error(f"Error generating fallback data: {e}")
            return {}
    
    async def generate_bulk_test_data(
        self,
        schema: Dict[str, Any],
        count: int = 10,
        scenario_type: str = "valid"
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple test data sets
        
        Args:
            schema: JSON schema
            count: Number of data sets to generate
            scenario_type: Type of scenario
            
        Returns:
            List of test data sets
        """
        try:
            logger.info(f"🎲 Generating {count} {scenario_type} test data sets...")
            
            prompt = f"""
Generate {count} different {scenario_type} test data sets for this schema:

Schema:
{json.dumps(schema, indent=2)}

Requirements:
- Generate {count} DIFFERENT data sets
- Each should be unique and realistic
- Vary the values across data sets
- Follow schema constraints

Output as JSON array:
[
  {{...data set 1...}},
  {{...data set 2...}},
  ...
]

Return ONLY valid JSON array, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.8)
            
            # Parse JSON from response
            data_text = response.strip()
            if "```json" in data_text:
                data_text = data_text.split("```json")[1].split("```")[0].strip()
            elif "```" in data_text:
                data_text = data_text.split("```")[1].split("```")[0].strip()
            
            data_sets = json.loads(data_text)
            
            logger.info(f"✅ Generated {len(data_sets)} test data sets")
            
            return data_sets
        
        except Exception as e:
            logger.error(f"❌ Error generating bulk test data: {e}")
            # Generate fallback data
            return [self._generate_fallback_data(schema, scenario_type) for _ in range(count)]
    
    async def generate_data_for_workflow(
        self,
        workflow: Dict[str, Any],
        schemas: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate test data for complete workflow
        Handles data dependencies between steps
        
        Args:
            workflow: Workflow definition with steps
            schemas: Schemas for each endpoint
            
        Returns:
            Test data for each step with dependencies resolved
        """
        try:
            logger.info("🔄 Generating test data for workflow...")
            
            prompt = f"""
Generate test data for this complete workflow:

Workflow:
{json.dumps(workflow, indent=2)}

Schemas:
{json.dumps(schemas, indent=2)[:5000]}

Requirements:
- Generate data for each step in the workflow
- Handle data dependencies (e.g., use ID from step 1 in step 2)
- Use realistic, consistent data across steps
- Ensure data flows correctly between steps

Output as JSON:
{{
  "step_1": {{
    "endpoint": "/api/login",
    "data": {{"email": "test@example.com", "password": "test123"}},
    "extracts": {{"token": "{{response.data.token}}"}}
  }},
  "step_2": {{
    "endpoint": "/api/bookings",
    "data": {{"origin": "Mumbai", "destination": "Delhi"}},
    "uses": {{"token": "{{step_1.token}}"}},
    "extracts": {{"bookingId": "{{response.data.id}}"}}
  }}
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.5)
            
            # Parse JSON from response
            data_text = response.strip()
            if "```json" in data_text:
                data_text = data_text.split("```json")[1].split("```")[0].strip()
            elif "```" in data_text:
                data_text = data_text.split("```")[1].split("```")[0].strip()
            
            workflow_data = json.loads(data_text)
            
            logger.info(f"✅ Generated workflow test data for {len(workflow_data)} steps")
            
            return workflow_data
        
        except Exception as e:
            logger.error(f"❌ Error generating workflow test data: {e}")
            return {}
    
    async def mutate_data(
        self,
        original_data: Dict[str, Any],
        mutation_type: str = "random"  # "random", "boundary", "invalid"
    ) -> Dict[str, Any]:
        """
        Mutate existing data to create variations
        
        Args:
            original_data: Original test data
            mutation_type: Type of mutation
            
        Returns:
            Mutated test data
        """
        try:
            logger.info(f"🧬 Mutating test data ({mutation_type})...")
            
            prompt = f"""
Mutate this test data:

Original Data:
{json.dumps(original_data, indent=2)}

Mutation Type: {mutation_type}

Requirements:
- For "random": Change some values randomly but keep valid
- For "boundary": Change values to boundary cases (min, max, zero, empty)
- For "invalid": Make one field invalid

Output as JSON:
{{
  "mutated_data": {{...mutated data...}},
  "changes": ["Changed field1 from X to Y", "Changed field2 from A to B"]
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.7)
            
            # Parse JSON from response
            data_text = response.strip()
            if "```json" in data_text:
                data_text = data_text.split("```json")[1].split("```")[0].strip()
            elif "```" in data_text:
                data_text = data_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(data_text)
            
            logger.info(f"✅ Mutated test data")
            
            return result.get('mutated_data', original_data)
        
        except Exception as e:
            logger.error(f"❌ Error mutating test data: {e}")
            return original_data
