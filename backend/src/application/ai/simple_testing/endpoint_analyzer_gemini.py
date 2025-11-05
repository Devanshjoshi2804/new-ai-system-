"""
Endpoint Analysis - Use Google Gemini (NO RATE LIMITS!)
"""
import os
import json
from typing import Tuple, List, Dict, Any


async def analyze_endpoints(full_text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Use Google Gemini to extract API endpoints - FREE TIER: 15 req/min, 1M tokens/min"""
    print("\n" + "=" * 80)
    print("[INFO] STEP 3: AI ENDPOINT ANALYSIS (Using Google Gemini)")
    print("=" * 80)
    
    import google.generativeai as genai
    
    gemini_api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    genai.configure(api_key=gemini_api_key)
    
    # Use Gemini 1.5 Flash (fast and free)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Split into chunks
    max_chars = 30000  # Gemini can handle larger chunks
    text_chunks = [full_text[i:i + max_chars] for i in range(0, len(full_text), max_chars)]
    
    print(f"[INFO] Analyzing {len(text_chunks)} text chunks...")
    
    all_endpoints = []
    base_url = None
    
    for idx, chunk in enumerate(text_chunks):
        print(f"\n[SEARCH] Analyzing chunk {idx + 1}/{len(text_chunks)}...")
        
        prompt = f"""Analyze this API documentation and extract:
1. Base URL
2. All API endpoints with complete details

Documentation:
{chunk}

Return ONLY valid JSON:
{{
    "base_url": "https://api.example.com",
    "endpoints": [
        {{
            "path": "/api/endpoint",
            "method": "POST",
            "summary": "Brief description",
            "parameters": [
                {{
                    "name": "param_name",
                    "type": "string",
                    "required": true,
                    "location": "body"
                }}
            ],
            "auth_required": true
        }}
    ]
}}

Return ONLY JSON, no markdown."""

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
            data = json.loads(result_text)
            
            if not base_url and data.get('base_url'):
                base_url = data['base_url']
                print(f"[OK] Found base URL: {base_url}")
            
            if data.get('endpoints'):
                all_endpoints.extend(data['endpoints'])
                print(f"[OK] Found {len(data['endpoints'])} endpoints")
        
        except json.JSONDecodeError as e:
            print(f"[WARN] Failed to parse JSON: {e}")
    
    print(f"\n[OK] Total endpoints: {len(all_endpoints)}")
    return base_url, all_endpoints


