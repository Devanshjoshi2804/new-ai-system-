"""
Error Fixing - Use Google Gemini (NO RATE LIMITS!)
"""
import os
import json
import random
import string
from typing import Dict, Any


def generate_unique_suffix() -> str:
    """Generate unique suffix for test data"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))


async def fix_payload_from_error(
    endpoint: dict,
    failed_payload: dict,
    error_response: dict,
    doc_context: str,
    flow_db
) -> Dict[str, Any]:
    """Fix payload based on error using Google Gemini"""
    import google.generativeai as genai
    
    gemini_api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    genai.configure(api_key=gemini_api_key)
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Query Flow DB for successful data
    previous_data = flow_db.query_for_fields(
        f"Find successful data for {endpoint['method']} {endpoint['path']}",
        k=3
    )
    
    unique_suffix = generate_unique_suffix()
    
    prompt = f"""Fix this failed API payload based on the error response.

Endpoint: {endpoint['method']} {endpoint['path']}

FAILED PAYLOAD:
{json.dumps(failed_payload, indent=2)}

ERROR RESPONSE:
{json.dumps(error_response, indent=2)}

PREVIOUS SUCCESSFUL DATA:
{previous_data}

DOCUMENTATION CONTEXT:
{doc_context[:2000]}

INSTRUCTIONS:
1. **USE PREVIOUS DATA**: Extract needed fields from previous API calls above
2. **FOR PASSWORD ERRORS**: Use plain text password from signup REQUEST, NOT hashed from response
3. Analyze the error message carefully from documentation context
4. If field is missing: Add it with value from previous data OR documentation
5. If value is invalid: Replace with valid value from documentation examples
6. If user/contact already exists: Generate NEW unique values (email: test_{unique_suffix}@yopmail.com, mobile: 99{random.randint(10000000, 99999999)})
7. If enum/type error: Use correct value from error message or documentation
8. For GET requests: Check if params should be in URL, include ALL required query params
9. Keep all existing correct fields

UNIQUE SUFFIX: {unique_suffix}

Return ONLY the FIXED JSON payload:
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
        fixed_payload = json.loads(result_text)
        return fixed_payload
    except json.JSONDecodeError as e:
        print(f"  [WARN] Failed to parse fixed payload")
        print(f"[OK] Fixed payload:\n{{}}")
        return {}


