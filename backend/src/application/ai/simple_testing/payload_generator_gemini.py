"""
Payload Generation - Use Google Gemini (NO RATE LIMITS!)
"""
import os
import json
import random
import string
from typing import Dict, Any


def generate_unique_suffix() -> str:
    """Generate unique suffix for test data"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))


async def generate_complete_payload(endpoint: dict, context_data: dict, flow_db) -> Dict[str, Any]:
    """Generate complete test payload using Google Gemini + Flow DB"""
    import google.generativeai as genai
    
    gemini_api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    genai.configure(api_key=gemini_api_key)
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Query Flow DB for previous successful data
    endpoint_key = f"{endpoint['method']} {endpoint['path']}"
    previous_data = flow_db.query_for_fields(
        f"Find all data from previous successful API calls for {endpoint_key}",
        k=5
    )
    
    unique_suffix = generate_unique_suffix()
    
    prompt = f"""Generate a complete test payload for this API endpoint.

Endpoint: {endpoint['method']} {endpoint['path']}
Summary: {endpoint.get('summary', 'No summary')}

Parameters from API spec:
{json.dumps(endpoint.get('parameters', []), indent=2)}

PREVIOUS API CALLS DATA (from Flow ChromaDB):
{previous_data}

Documentation Context:
{context_data['context'][:3000]}

CRITICAL INSTRUCTIONS:
1. **USE PREVIOUS DATA**: Extract credentials, tokens, IDs, codes from previous API responses above
2. **FOR LOGIN**: Use the ORIGINAL plain text password from signup REQUEST, NOT hashed password from response
3. Extract ALL required fields from documentation
4. For signup/registration: Generate UNIQUE values (email: test_{unique_suffix}@yopmail.com, mobile: 99{random.randint(10000000, 99999999)})
5. Look for example payloads in documentation and use similar structure
6. For GET requests: Include ALL query parameters mentioned in documentation
7. Match exact field names and types from documentation

UNIQUE SUFFIX: {unique_suffix}

Return ONLY valid JSON payload (for GET requests, these will be query params):
{{"field": "value"}}
"""
    
    response = model.generate_content(prompt)
    result_text = response.text.strip()
    
    # Clean markdown
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    if result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
    result_text = result_text.strip()
    
    try:
        payload = json.loads(result_text)
        return payload
    except json.JSONDecodeError as e:
        print(f"[WARN] Failed to parse payload JSON: {e}")
        return {}


