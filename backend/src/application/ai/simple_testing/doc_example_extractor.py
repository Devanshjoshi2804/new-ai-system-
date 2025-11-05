"""
Documentation Example Extractor
Extract working payloads, credentials, and auth headers from documentation
ONLY USED AS LAST RESORT when AI generation fails!
"""
import json
import re
from typing import Dict, Any, Optional, List


def extract_example_payloads(chunks: list, endpoint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract example request payloads from documentation chunks
    
    This is the LAST RESORT - only called when AI generation fails 3 times!
    
    Looks for:
    - JSON examples in code blocks
    - Request body examples
    - Sample payloads
    - Test data
    """
    print(f"[LAST_RESORT] Searching documentation for working example payload...")
    
    endpoint_path = endpoint.get('path', '')
    endpoint_method = endpoint.get('method', 'GET')
    
    # Search all chunks for examples related to this endpoint
    relevant_examples = []
    
    for chunk in chunks:
        chunk_lower = chunk.lower()
        
        # Check if chunk is relevant to this endpoint
        if endpoint_path.lower() in chunk_lower or endpoint.get('summary', '').lower() in chunk_lower:
            # Look for JSON code blocks
            json_blocks = re.findall(r'```(?:json)?\s*\n(.*?)\n```', chunk, re.DOTALL)
            for json_block in json_blocks:
                try:
                    example = json.loads(json_block.strip())
                    if isinstance(example, dict):
                        relevant_examples.append(example)
                        print(f"   [FOUND] JSON example in documentation")
                except:
                    pass
            
            # Look for inline JSON objects
            json_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', chunk)
            for json_str in json_objects:
                try:
                    example = json.loads(json_str)
                    if isinstance(example, dict) and len(example) > 1:  # Must have multiple fields
                        relevant_examples.append(example)
                        print(f"   [FOUND] Inline JSON example")
                except:
                    pass
    
    if relevant_examples:
        # Return the most complete example (one with most fields)
        best_example = max(relevant_examples, key=lambda x: len(x))
        print(f"[OK] Found working example with {len(best_example)} fields")
        return best_example
    
    print(f"[WARN] No example payload found in documentation")
    return None


def extract_auth_headers(chunks: list) -> Dict[str, str]:
    """
    Extract authentication headers from documentation
    
    Looks for:
    - API keys
    - Authorization tokens
    - Custom headers
    - Bearer tokens
    """
    print(f"[SEARCH] Looking for authentication headers in documentation...")
    
    auth_headers = {}
    
    for chunk in chunks:
        chunk_lower = chunk.lower()
        
        # Look for API key patterns
        api_key_patterns = [
            r'api[_-]?key[:\s]+([a-zA-Z0-9_-]+)',
            r'x-api-key[:\s]+([a-zA-Z0-9_-]+)',
            r'apikey[:\s]+([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in api_key_patterns:
            matches = re.findall(pattern, chunk_lower)
            if matches:
                auth_headers['X-API-Key'] = matches[0]
                print(f"   [FOUND] API Key header")
        
        # Look for Authorization header
        auth_patterns = [
            r'authorization[:\s]+bearer\s+([a-zA-Z0-9_.-]+)',
            r'authorization[:\s]+([a-zA-Z0-9_.-]+)',
        ]
        
        for pattern in auth_patterns:
            matches = re.findall(pattern, chunk_lower)
            if matches:
                auth_headers['Authorization'] = f"Bearer {matches[0]}"
                print(f"   [FOUND] Authorization header")
        
        # Look for custom headers in code examples
        header_pattern = r'"([Xx]-[A-Za-z-]+)":\s*"([^"]+)"'
        matches = re.findall(header_pattern, chunk)
        for header_name, header_value in matches:
            auth_headers[header_name] = header_value
            print(f"   [FOUND] Custom header: {header_name}")
    
    if auth_headers:
        print(f"[OK] Found {len(auth_headers)} authentication headers")
    else:
        print(f"[INFO] No authentication headers found")
    
    return auth_headers


def extract_test_credentials(chunks: list) -> Dict[str, Any]:
    """
    Extract test credentials and data from documentation
    
    Looks for:
    - Test user IDs
    - Test vendor codes
    - Test partner codes
    - Sample data values
    """
    print(f"[SEARCH] Looking for test credentials in documentation...")
    
    credentials = {}
    
    for chunk in chunks:
        # Look for vendor codes
        vendor_matches = re.findall(r'vendorCode["\']?\s*:\s*["\']([^"\']+)["\']', chunk, re.IGNORECASE)
        if vendor_matches:
            credentials['vendorCode'] = vendor_matches[0]
            print(f"   [FOUND] Vendor code: {vendor_matches[0]}")
        
        # Look for partner codes
        partner_matches = re.findall(r'partnerCode["\']?\s*:\s*["\']([^"\']+)["\']', chunk, re.IGNORECASE)
        if partner_matches:
            credentials['partnerCode'] = partner_matches[0]
            print(f"   [FOUND] Partner code: {partner_matches[0]}")
        
        # Look for user IDs
        user_matches = re.findall(r'userId["\']?\s*:\s*["\']([^"\']+)["\']', chunk, re.IGNORECASE)
        if user_matches:
            credentials['userId'] = user_matches[0]
            print(f"   [FOUND] User ID: {user_matches[0]}")
        
        # Look for test/demo indicators
        if 'test' in chunk.lower() or 'demo' in chunk.lower() or 'example' in chunk.lower():
            # Extract email addresses
            email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', chunk)
            if email_matches:
                credentials['email'] = email_matches[0]
                print(f"   [FOUND] Test email: {email_matches[0]}")
            
            # Extract phone numbers
            phone_matches = re.findall(r'\+?\d{10,15}', chunk)
            if phone_matches:
                credentials['phone'] = phone_matches[0]
                print(f"   [FOUND] Test phone: {phone_matches[0]}")
    
    if credentials:
        print(f"[OK] Found {len(credentials)} test credentials")
    else:
        print(f"[INFO] No test credentials found")
    
    return credentials


def merge_example_with_ai_payload(ai_payload: Dict[str, Any], example_payload: Dict[str, Any], credentials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge documentation example with AI-generated payload
    
    Strategy:
    1. Start with AI payload structure
    2. Replace values with example values where available
    3. Add any missing fields from example
    4. Inject test credentials
    """
    print(f"[MERGE] Combining AI payload with documentation example...")
    
    # Start with AI payload
    merged = ai_payload.copy()
    
    # Replace values from example (keeping AI structure)
    for key, value in example_payload.items():
        if key in merged:
            # Replace AI value with example value
            merged[key] = value
            print(f"   [REPLACE] {key}: {value}")
        else:
            # Add missing field from example
            merged[key] = value
            print(f"   [ADD] {key}: {value}")
    
    # Inject credentials
    for key, value in credentials.items():
        if key not in merged or not merged[key]:
            merged[key] = value
            print(f"   [INJECT] {key}: {value}")
    
    print(f"[OK] Merged payload has {len(merged)} fields")
    return merged

