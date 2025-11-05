"""
Endpoint Analysis - Use AI with automatic fallback (Groq → Gemini → Mistral)
"""
import json
from typing import Tuple, List, Dict, Any
from .ai_provider_fallback import get_ai_provider


async def analyze_endpoints(full_text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Use AI with automatic fallback to extract API endpoints"""
    print("\n" + "=" * 80)
    print("[INFO] STEP 3: AI ENDPOINT ANALYSIS (with automatic fallback)")
    print("=" * 80)
    
    ai = get_ai_provider()
    
    # Split into chunks
    max_chars = 20000
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

        result_text, provider = ai.generate(
            prompt=prompt,
            system_prompt="Extract API endpoints and return ONLY valid JSON."
        )
        
        if not result_text:
            print(f"[WARN] All AI providers failed for chunk {idx + 1}")
            continue
        
        print(f"[OK] Used {provider.value.upper()}")
        
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

