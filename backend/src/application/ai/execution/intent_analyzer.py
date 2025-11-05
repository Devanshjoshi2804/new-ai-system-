"""
Intent Analyzer - Understand user intent from natural language
"""
import json
import logging
from typing import Dict, Any, List, Optional

from src.infrastructure.ai.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """Understand user intent and map to API operations"""
    
    def __init__(self):
        self.gemini = GeminiProvider()
    
    async def analyze_intent(
        self,
        user_message: str,
        api_spec: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze user intent and create execution plan
        
        Args:
            user_message: User's natural language command
            api_spec: Complete API specification
            context: Optional context (previous interactions, user data)
            
        Returns:
            Intent analysis with execution plan
        """
        try:
            logger.info(f"[INFO] Analyzing intent: '{user_message}'")
            
            # Prepare context
            context_str = json.dumps(context, indent=2) if context else "No previous context"
            
            # Prepare API spec summary (limit size)
            endpoints_summary = [
                {
                    "method": ep.get("method"),
                    "path": ep.get("path"),
                    "summary": ep.get("summary", "")
                }
                for ep in api_spec.get("endpoints", [])[:30]  # Limit to 30 endpoints
            ]
            
            prompt = f"""
Analyze this user command and determine what API operations to perform:

**User Command:** "{user_message}"

**Available API Endpoints:**
{json.dumps(endpoints_summary, indent=2)}

**API Workflows:**
{json.dumps(api_spec.get('workflow_analysis', {}), indent=2)[:3000]}

**Context from Previous Interactions:**
{context_str}

**Your Task:**
Determine:
1. **Intent**: What does the user want to do?
   - create_resource (create booking, order, shipment, etc.)
   - read_resource (get, fetch, retrieve, check, view)
   - update_resource (update, modify, change, edit)
   - delete_resource (delete, cancel, remove)
   - search_resource (search, find, list, query)
   - complex_workflow (multi-step operation)

2. **Confidence**: How confident are you? (0.0 to 1.0)

3. **Endpoints to Call**: Which endpoints should be called and in what order?

4. **Extracted Data**: What data can you extract from the user message?
   - Locations (Mumbai, Delhi, etc.)
   - Quantities (10kg, 5 items, etc.)
   - IDs (booking #12345, order ID 789, etc.)
   - Dates (tomorrow, next week, 2025-10-25, etc.)
   - Names, emails, phone numbers, etc.

5. **Missing Data**: What data is needed but not provided?

6. **Execution Plan**: Step-by-step plan with:
   - Which endpoint to call
   - What data to send
   - What to extract from response
   - How to use extracted data in next step

Output as JSON:
{{
  "intent": "create_resource",
  "intent_description": "User wants to create a booking from Mumbai to Delhi",
  "confidence": 0.95,
  "resource_type": "booking",
  "action": "create",
  "endpoints_to_call": [
    "/api/login",
    "/api/validate-address", 
    "/api/bookings"
  ],
  "extracted_data": {{
    "origin": "Mumbai",
    "destination": "Delhi",
    "weight": 10,
    "weight_unit": "kg"
  }},
  "missing_data": [
    {{
      "field": "pickup_date",
      "type": "date",
      "required": true,
      "question": "When would you like the pickup?"
    }},
    {{
      "field": "contact_phone",
      "type": "phone",
      "required": true,
      "question": "What's your contact phone number?"
    }}
  ],
  "execution_plan": [
    {{
      "step": 1,
      "action": "authenticate",
      "endpoint": "/api/login",
      "method": "POST",
      "description": "Login to get authentication token",
      "data_source": "credentials",
      "extracts": {{
        "token": "data.token",
        "vendorCode": "data.vendorCode"
      }}
    }},
    {{
      "step": 2,
      "action": "validate_origin",
      "endpoint": "/api/validate-address",
      "method": "POST",
      "description": "Validate origin address",
      "data": {{
        "address": "{{{{origin}}}}"
      }},
      "requires": ["token", "vendorCode"],
      "extracts": {{
        "origin_address_id": "data.addressId"
      }}
    }},
    {{
      "step": 3,
      "action": "validate_destination",
      "endpoint": "/api/validate-address",
      "method": "POST",
      "description": "Validate destination address",
      "data": {{
        "address": "{{{{destination}}}}"
      }},
      "requires": ["token", "vendorCode"],
      "extracts": {{
        "destination_address_id": "data.addressId"
      }}
    }},
    {{
      "step": 4,
      "action": "create_booking",
      "endpoint": "/api/bookings",
      "method": "POST",
      "description": "Create the booking",
      "data": {{
        "origin_address_id": "{{{{origin_address_id}}}}",
        "destination_address_id": "{{{{destination_address_id}}}}",
        "weight": "{{{{weight}}}}",
        "vendorCode": "{{{{vendorCode}}}}"
      }},
      "requires": ["token", "origin_address_id", "destination_address_id"],
      "extracts": {{
        "booking_id": "data.bookingId",
        "awb_number": "data.awbNumber"
      }}
    }}
  ],
  "expected_outcome": "Booking created successfully with AWB number",
  "clarification_needed": false
}}

**Important:**
- If user command is ambiguous or missing critical info, set clarification_needed=true
- Use workflow_analysis to understand correct endpoint sequences
- Extract as much data as possible from the user message
- Be smart about inferring data (e.g., "tomorrow" → date, "10kg" → weight)

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.3)
            
            # Parse JSON from response
            intent_text = response.strip()
            if "```json" in intent_text:
                intent_text = intent_text.split("```json")[1].split("```")[0].strip()
            elif "```" in intent_text:
                intent_text = intent_text.split("```")[1].split("```")[0].strip()
            
            intent = json.loads(intent_text)
            
            logger.info(f"[OK] Intent: {intent.get('intent')} (confidence: {intent.get('confidence', 0)})")
            logger.info(f"[INFO] Execution plan: {len(intent.get('execution_plan', []))} steps")
            
            return intent
        
        except Exception as e:
            logger.error(f"[ERROR] Error analyzing intent: {e}", exc_info=True)
            return {
                'intent': 'unknown',
                'intent_description': 'Could not understand the command',
                'confidence': 0.0,
                'endpoints_to_call': [],
                'extracted_data': {},
                'missing_data': [],
                'execution_plan': [],
                'expected_outcome': '',
                'clarification_needed': True,
                'error': str(e)
            }
    
    async def clarify_intent(
        self,
        user_message: str,
        previous_intent: Dict[str, Any],
        user_response: str
    ) -> Dict[str, Any]:
        """
        Clarify intent based on user's response to questions
        
        Args:
            user_message: Original user command
            previous_intent: Previous intent analysis
            user_response: User's response to clarification questions
            
        Returns:
            Updated intent analysis
        """
        try:
            logger.info("[SEARCH] Clarifying intent with user response...")
            
            prompt = f"""
Update the intent analysis with user's response:

**Original Command:** "{user_message}"

**Previous Analysis:**
{json.dumps(previous_intent, indent=2)}

**User's Response:** "{user_response}"

**Your Task:**
1. Extract additional data from user's response
2. Update missing_data list (remove provided data)
3. Update execution_plan with new data
4. Set clarification_needed=false if all data is now available

Output updated intent analysis as JSON.

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.3)
            
            # Parse JSON from response
            intent_text = response.strip()
            if "```json" in intent_text:
                intent_text = intent_text.split("```json")[1].split("```")[0].strip()
            elif "```" in intent_text:
                intent_text = intent_text.split("```")[1].split("```")[0].strip()
            
            updated_intent = json.loads(intent_text)
            
            logger.info(f"[OK] Intent clarified, missing data: {len(updated_intent.get('missing_data', []))}")
            
            return updated_intent
        
        except Exception as e:
            logger.error(f"[ERROR] Error clarifying intent: {e}")
            return previous_intent
    
    async def suggest_commands(
        self,
        api_spec: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Suggest natural language commands based on API capabilities
        
        Args:
            api_spec: API specification
            context: Optional context
            
        Returns:
            List of suggested commands
        """
        try:
            logger.info("[IDEA] Generating command suggestions...")
            
            prompt = f"""
Based on this API specification, suggest natural language commands users can say:

**API Endpoints:**
{json.dumps([ep.get('summary', '') for ep in api_spec.get('endpoints', [])[:20]], indent=2)}

**Workflows:**
{json.dumps(api_spec.get('workflow_analysis', {}).get('workflows', []), indent=2)[:2000]}

Generate 10-15 example commands users might say, such as:
- "Create a booking from Mumbai to Delhi"
- "Check status of order #12345"
- "Cancel my booking"
- "Get all my shipments"
- "Update delivery address to Bangalore"

Output as JSON array:
[
  "Create a booking from Mumbai to Delhi",
  "Track shipment AWB123456",
  ...
]

Return ONLY valid JSON array, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.7)
            
            # Parse JSON from response
            suggestions_text = response.strip()
            if "```json" in suggestions_text:
                suggestions_text = suggestions_text.split("```json")[1].split("```")[0].strip()
            elif "```" in suggestions_text:
                suggestions_text = suggestions_text.split("```")[1].split("```")[0].strip()
            
            suggestions = json.loads(suggestions_text)
            
            logger.info(f"[OK] Generated {len(suggestions)} command suggestions")
            
            return suggestions
        
        except Exception as e:
            logger.error(f"[ERROR] Error generating suggestions: {e}")
            return [
                "Create a booking",
                "Check order status",
                "Cancel booking",
                "Get shipment details"
            ]
    
    async def extract_entities(
        self,
        text: str
    ) -> Dict[str, Any]:
        """
        Extract entities from text (locations, dates, quantities, IDs, etc.)
        
        Args:
            text: Text to extract entities from
            
        Returns:
            Extracted entities
        """
        try:
            logger.info(f"[SEARCH] Extracting entities from: '{text}'")
            
            prompt = f"""
Extract entities from this text:

**Text:** "{text}"

Extract:
- **Locations**: Cities, addresses, states, countries
- **Dates**: Dates, times, relative dates (tomorrow, next week)
- **Quantities**: Weights, dimensions, counts
- **IDs**: Order IDs, booking IDs, AWB numbers, tracking numbers
- **Contact**: Names, emails, phone numbers
- **Money**: Prices, costs, amounts
- **Other**: Any other relevant entities

Output as JSON:
{{
  "locations": [
    {{"type": "city", "value": "Mumbai", "role": "origin"}},
    {{"type": "city", "value": "Delhi", "role": "destination"}}
  ],
  "dates": [
    {{"type": "relative", "value": "tomorrow", "normalized": "2025-10-25"}}
  ],
  "quantities": [
    {{"type": "weight", "value": 10, "unit": "kg"}}
  ],
  "ids": [
    {{"type": "booking_id", "value": "12345"}}
  ],
  "contact": [
    {{"type": "phone", "value": "+91-9876543210"}}
  ],
  "money": [
    {{"type": "amount", "value": 500, "currency": "INR"}}
  ],
  "other": []
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.2)
            
            # Parse JSON from response
            entities_text = response.strip()
            if "```json" in entities_text:
                entities_text = entities_text.split("```json")[1].split("```")[0].strip()
            elif "```" in entities_text:
                entities_text = entities_text.split("```")[1].split("```")[0].strip()
            
            entities = json.loads(entities_text)
            
            logger.info(f"[OK] Extracted entities: {sum(len(v) for v in entities.values())} total")
            
            return entities
        
        except Exception as e:
            logger.error(f"[ERROR] Error extracting entities: {e}")
            return {
                'locations': [],
                'dates': [],
                'quantities': [],
                'ids': [],
                'contact': [],
                'money': [],
                'other': []
            }

