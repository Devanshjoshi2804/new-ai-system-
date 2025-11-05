"""
Test Executor - Execute API tests with intelligent retry
"""
import asyncio
import json
import re
from typing import Dict, Any, List, Optional

import httpx

from .payload_generator import generate_complete_payload
from .error_fixer import fix_payload_from_error


def retrieve_full_context(chunks: list, endpoint: dict) -> dict:
    """Retrieve ALL relevant information for an endpoint using RAG"""
    endpoint_key = f"{endpoint['method']} {endpoint['path']}"
    
    # Search for endpoint-specific chunks
    search_terms = [
        endpoint['path'].lower(),
        endpoint['method'].lower(),
        endpoint.get('summary', '').lower()
    ]
    
    scored_chunks = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(1 for term in search_terms if term and term in chunk_lower)
        if score > 0:
            scored_chunks.append((score, chunk))
    
    # Sort and get top chunks
    scored_chunks.sort(reverse=True, key=lambda x: x[0])
    relevant_chunks = [chunk for score, chunk in scored_chunks[:5]]  # Get top 5 chunks
    
    combined_context = "\n\n".join(relevant_chunks)
    
    return {
        "context": combined_context,
        "chunks_found": len(relevant_chunks)
    }


async def test_endpoint_with_retry(
    endpoint: dict, 
    chunks: list, 
    base_url: str, 
    client: httpx.AsyncClient, 
    headers: dict, 
    flow_db,
    max_retries: int = 3
) -> Optional[Dict[str, Any]]:
    """Test endpoint with intelligent retry on failures"""
    endpoint_key = f"{endpoint['method']} {endpoint['path']}"
    
    print(f"\n{'=' * 80}")
    print(f"[TEST] TESTING: {endpoint_key}")
    print(f"{'=' * 80}")
    
    # Step A: Retrieve context via RAG
    print(f"[DOC] Step A: Retrieving documentation via RAG...")
    context_data = retrieve_full_context(chunks, endpoint)
    print(f"[OK] Retrieved {context_data['chunks_found']} chunks ({len(context_data['context'])} chars)")
    
    # Step B: Generate initial payload using Flow DB
    print(f"[AI] Step B: Generating complete payload with AI (querying Flow DB)...")
    test_payload = await generate_complete_payload(endpoint, context_data, flow_db)
    print(f"[OK] Generated payload:\n{json.dumps(test_payload, indent=2)}")
    
    # Build URL
    base_api_url = f"{base_url}{endpoint['path']}"
    
    # Try testing with retries
    for attempt in range(1, max_retries + 1):
        # Build URL with query params for GET requests
        if endpoint['method'] == 'GET' and test_payload:
            from urllib.parse import urlencode
            query_string = urlencode(test_payload)
            url = f"{base_api_url}?{query_string}" if query_string else base_api_url
        else:
            url = base_api_url
        
        print(f"\n[START] Attempt {attempt}/{max_retries}: Executing API request...")
        print(f"   URL: {url}")
        print(f"   Method: {endpoint['method']}")
        if endpoint['method'] != 'GET':
            print(f"   Payload: {json.dumps(test_payload)}")
        
        # Query Flow DB for token if needed
        test_headers = headers.copy()
        if endpoint.get('auth_required'):
            token_query = "Find authentication token or bearer token from previous successful login"
            token_data = flow_db.query_for_fields(token_query, k=1)
            # Try to extract token from query result
            token_match = re.search(r'"token":\s*"([^"]+)"', token_data)
            if token_match:
                test_headers['Authorization'] = f"Bearer {token_match.group(1)}"
                print(f"   [INFO] Using token from Flow DB")
        
        try:
            # Execute request
            if endpoint['method'] == 'GET':
                # For GET, params are in URL already
                response = await client.get(url, headers=test_headers)
            elif endpoint['method'] == 'POST':
                response = await client.post(url, headers=test_headers, json=test_payload)
            elif endpoint['method'] == 'PUT':
                response = await client.put(url, headers=test_headers, json=test_payload)
            elif endpoint['method'] == 'DELETE':
                response = await client.delete(url, headers=test_headers)
            else:
                print(f"[WARN] Unsupported method: {endpoint['method']}")
                return None
            
            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {"raw": response.text[:500]}
            
            success = 200 <= response.status_code < 300
            
            if success:
                print(f"\n[OK] SUCCESS - Status: {response.status_code}")
                print(f"[INFO] Response:\n{json.dumps(response_data, indent=2)[:500]}...")
                
                # STORE IN FLOW DB (ChromaDB)
                flow_db.store_request(endpoint_key, test_payload)
                flow_db.store_response(endpoint_key, response_data)
                
                return {
                    'endpoint': endpoint_key,
                    'url': url,
                    'status_code': response.status_code,
                    'success': True,
                    'attempts': attempt,
                    'final_payload': test_payload,
                    'response': response_data
                }
            
            else:
                print(f"\n[ERROR] FAILED - Status: {response.status_code}")
                print(f"[INFO] Response:\n{json.dumps(response_data, indent=2)[:500]}...")
                
                # If not last attempt, try to fix with AI
                if attempt < max_retries:
                    print(f"\n[FIX] Analyzing error and generating fix (Attempt {attempt + 1})...")
                    test_payload = await fix_payload_from_error(
                        endpoint, 
                        test_payload, 
                        response_data, 
                        context_data["context"],
                        flow_db  # Pass Flow DB for querying previous data
                    )
                    print(f"[OK] Fixed payload:\n{json.dumps(test_payload, indent=2)}")
                    await asyncio.sleep(1)  # Small delay before retry
                
                # LAST RESORT: If this is the final attempt and still failing, try documentation examples
                elif attempt == max_retries:
                    print(f"\n[LAST_RESORT] All AI attempts failed. Trying documentation examples...")
                    from .doc_example_extractor import (
                        extract_example_payloads,
                        extract_test_credentials,
                        extract_auth_headers,
                        merge_example_with_ai_payload
                    )
                    
                    # Extract working examples from documentation
                    example_payload = extract_example_payloads(chunks, endpoint)
                    test_credentials = extract_test_credentials(chunks)
                    auth_headers = extract_auth_headers(chunks)
                    
                    if example_payload or test_credentials:
                        # Merge with AI payload
                        if example_payload:
                            test_payload = merge_example_with_ai_payload(test_payload, example_payload, test_credentials)
                        else:
                            # Just inject credentials into AI payload
                            test_payload.update(test_credentials)
                        
                        # Add auth headers if found
                        if auth_headers:
                            test_headers.update(auth_headers)
                            print(f"[OK] Added {len(auth_headers)} authentication headers")
                        
                        print(f"[RETRY] Attempting with documentation example...")
                        print(f"[OK] Final payload:\n{json.dumps(test_payload, indent=2)}")
                        
                        # Try ONE MORE TIME with documentation example
                        try:
                            if endpoint['method'] == 'GET':
                                from urllib.parse import urlencode
                                query_string = urlencode(test_payload)
                                url = f"{base_api_url}?{query_string}" if query_string else base_api_url
                                response = await client.get(url, headers=test_headers)
                            elif endpoint['method'] == 'POST':
                                response = await client.post(base_api_url, headers=test_headers, json=test_payload)
                            elif endpoint['method'] == 'PUT':
                                response = await client.put(base_api_url, headers=test_headers, json=test_payload)
                            elif endpoint['method'] == 'DELETE':
                                response = await client.delete(base_api_url, headers=test_headers)
                            
                            try:
                                response_data = response.json()
                            except:
                                response_data = {"raw": response.text[:500]}
                            
                            success = 200 <= response.status_code < 300
                            
                            if success:
                                print(f"\n[SUCCESS] Documentation example worked! Status: {response.status_code}")
                                flow_db.store_request(endpoint_key, test_payload)
                                flow_db.store_response(endpoint_key, response_data)
                                
                                return {
                                    'endpoint': endpoint_key,
                                    'url': url,
                                    'status_code': response.status_code,
                                    'success': True,
                                    'attempts': attempt + 1,  # Extra attempt with doc example
                                    'final_payload': test_payload,
                                    'response': response_data
                                }
                            else:
                                print(f"\n[FAIL] Even documentation example failed: {response.status_code}")
                        
                        except Exception as e:
                            print(f"[ERROR] Documentation example attempt failed: {e}")
                    else:
                        print(f"[WARN] No documentation examples found")
                    
                    return {
                        'endpoint': endpoint_key,
                        'url': url,
                        'status_code': response.status_code,
                        'success': False,
                        'attempts': attempt,
                        'final_payload': test_payload,
                        'response': response_data,
                        'error': f"Failed after {max_retries} attempts"
                    }
        
        except Exception as e:
            print(f"\n[ERROR] ERROR: {str(e)}")
            if attempt == max_retries:
                return {
                    'endpoint': endpoint_key,
                    'url': url,
                    'status_code': 0,
                    'success': False,
                    'attempts': attempt,
                    'final_payload': test_payload,
                    'error': str(e)
                }


async def test_all_endpoints(base_url: str, endpoints: list, chunks: list) -> List[Dict[str, Any]]:
    """Test all endpoints with smart retry using Flow ChromaDB"""
    from .flow_store_local import FlowDataStore
    
    print("\n" + "=" * 80)
    print("[TEST] TESTING ALL ENDPOINTS WITH FLOW CHROMADB")
    print("=" * 80)
    
    # Initialize Flow DB for this test session
    flow_db = FlowDataStore()
    
    test_results = []
    headers = {"Content-Type": "application/json"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for idx, ep in enumerate(endpoints, 1):
                result = await test_endpoint_with_retry(
                    ep, chunks, base_url, client, headers, flow_db
                )
                
                if result:
                    test_results.append(result)
                
                # Small delay between endpoints
                await asyncio.sleep(0.5)
    finally:
        # Cleanup Flow DB after tests
        flow_db.cleanup()
    
    return test_results


