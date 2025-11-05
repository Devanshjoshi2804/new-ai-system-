"""
Generate Flow DB Data - Standalone Test Script

This script tests a public API and stores results in Flow DB
to generate training data for our ML models.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import httpx
import json
from datetime import datetime

# Import our Flow DB storage
from src.application.ai.simple_testing.flow_store_local import FlowDataStore


async def test_jsonplaceholder_api():
    """
    Test JSONPlaceholder API (public, free, always available)
    This will generate Flow DB data we can train on
    """
    print("\n" + "="*80)
    print("   FLOW DB DATA GENERATION - Testing JSONPlaceholder API")
    print("="*80 + "\n")

    # Initialize Flow DB
    print("[1/5] Initializing Flow DB...")
    flow_db = FlowDataStore()
    print(f"   ✅ Flow DB initialized: {flow_db.collection_name}\n")

    # Base URL
    base_url = "https://jsonplaceholder.typicode.com"

    # Create HTTP client
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("[2/5] Running test suite...\n")

        test_count = 0
        success_count = 0

        # Test 1: GET /posts - List posts
        print(f"[TEST {test_count+1}] GET /posts (List all posts)")
        try:
            response = await client.get(f"{base_url}/posts")
            if response.status_code == 200:
                data = response.json()
                # Store in Flow DB
                flow_db.store_request("GET /posts", {})
                flow_db.store_response("GET /posts", data[:2])  # Store first 2 posts
                print(f"   ✅ Success: {response.status_code} - Found {len(data)} posts")
                success_count += 1
            else:
                print(f"   ❌ Failed: {response.status_code}")
            test_count += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            test_count += 1

        # Test 2: GET /posts/1 - Get specific post
        print(f"\n[TEST {test_count+1}] GET /posts/1 (Get specific post)")
        try:
            response = await client.get(f"{base_url}/posts/1")
            if response.status_code == 200:
                data = response.json()
                flow_db.store_request("GET /posts/{id}", {"id": 1})
                flow_db.store_response("GET /posts/{id}", data)
                print(f"   ✅ Success: {response.status_code}")
                print(f"   Post: {data.get('title', 'N/A')[:50]}...")
                success_count += 1
            else:
                print(f"   ❌ Failed: {response.status_code}")
            test_count += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            test_count += 1

        # Test 3: POST /posts - Create post
        print(f"\n[TEST {test_count+1}] POST /posts (Create new post)")
        try:
            payload = {
                "title": "Test Post from Flow DB Generator",
                "body": "This is a test post to generate training data",
                "userId": 1
            }
            response = await client.post(f"{base_url}/posts", json=payload)
            if response.status_code == 201:
                data = response.json()
                flow_db.store_request("POST /posts", payload)
                flow_db.store_response("POST /posts", data)
                print(f"   ✅ Success: {response.status_code} - Created post ID: {data.get('id')}")
                success_count += 1
            else:
                print(f"   ❌ Failed: {response.status_code}")
            test_count += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            test_count += 1

        # Test 4: GET /users - List users
        print(f"\n[TEST {test_count+1}] GET /users (List all users)")
        try:
            response = await client.get(f"{base_url}/users")
            if response.status_code == 200:
                data = response.json()
                flow_db.store_request("GET /users", {})
                flow_db.store_response("GET /users", data[:2])  # Store first 2 users
                print(f"   ✅ Success: {response.status_code} - Found {len(data)} users")
                success_count += 1
            else:
                print(f"   ❌ Failed: {response.status_code}")
            test_count += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            test_count += 1

        # Test 5: GET /comments - List comments
        print(f"\n[TEST {test_count+1}] GET /comments (List all comments)")
        try:
            response = await client.get(f"{base_url}/comments?postId=1")
            if response.status_code == 200:
                data = response.json()
                flow_db.store_request("GET /comments", {"postId": 1})
                flow_db.store_response("GET /comments", data[:2])  # Store first 2 comments
                print(f"   ✅ Success: {response.status_code} - Found {len(data)} comments")
                success_count += 1
            else:
                print(f"   ❌ Failed: {response.status_code}")
            test_count += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            test_count += 1

        # Test 6: PUT /posts/1 - Update post
        print(f"\n[TEST {test_count+1}] PUT /posts/1 (Update existing post)")
        try:
            payload = {
                "id": 1,
                "title": "Updated Post Title",
                "body": "Updated post body for training data",
                "userId": 1
            }
            response = await client.put(f"{base_url}/posts/1", json=payload)
            if response.status_code == 200:
                data = response.json()
                flow_db.store_request("PUT /posts/{id}", payload)
                flow_db.store_response("PUT /posts/{id}", data)
                print(f"   ✅ Success: {response.status_code} - Updated post")
                success_count += 1
            else:
                print(f"   ❌ Failed: {response.status_code}")
            test_count += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            test_count += 1

        # Test 7: DELETE /posts/1 - Delete post
        print(f"\n[TEST {test_count+1}] DELETE /posts/1 (Delete post)")
        try:
            response = await client.delete(f"{base_url}/posts/1")
            if response.status_code == 200:
                flow_db.store_request("DELETE /posts/{id}", {"id": 1})
                flow_db.store_response("DELETE /posts/{id}", {})
                print(f"   ✅ Success: {response.status_code} - Deleted post")
                success_count += 1
            else:
                print(f"   ❌ Failed: {response.status_code}")
            test_count += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            test_count += 1

        # Test 8: GET /albums - List albums
        print(f"\n[TEST {test_count+1}] GET /albums (List all albums)")
        try:
            response = await client.get(f"{base_url}/albums")
            if response.status_code == 200:
                data = response.json()
                flow_db.store_request("GET /albums", {})
                flow_db.store_response("GET /albums", data[:2])
                print(f"   ✅ Success: {response.status_code} - Found {len(data)} albums")
                success_count += 1
            else:
                print(f"   ❌ Failed: {response.status_code}")
            test_count += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            test_count += 1

    # Summary
    print(f"\n[3/5] Test Summary")
    print(f"   Total tests: {test_count}")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {test_count - success_count}")
    print(f"   Success rate: {success_count/test_count*100:.1f}%\n")

    # Query Flow DB to verify data
    print("[4/5] Verifying Flow DB data...")
    query_result = flow_db.query_for_fields("Find POST requests", k=3)
    print(f"   Sample query result (first 200 chars):")
    print(f"   {query_result[:200]}...\n")

    # Show Flow DB location
    print("[5/5] Flow DB Summary")
    print(f"   📁 Location: {flow_db.persist_directory}")
    print(f"   📊 Collection: {flow_db.collection_name}")
    print(f"   ✅ Stored {success_count * 2} documents (requests + responses)")

    print("\n" + "="*80)
    print("   ✅ FLOW DB DATA GENERATION COMPLETE!")
    print("="*80 + "\n")

    print("📊 Next Steps:")
    print("   1. Inspect Flow DB: ls -la ./data/flow_chroma_db/")
    print("   2. Extract training data: python scripts/extract_flow_db_data.py")
    print("   3. Build cache-based model: python scripts/build_payload_cache.py")
    print("   4. Test hybrid system: python scripts/test_hybrid_generator.py")

    return {
        'total_tests': test_count,
        'successful': success_count,
        'flow_db_location': flow_db.persist_directory,
        'collection_name': flow_db.collection_name
    }


if __name__ == "__main__":
    result = asyncio.run(test_jsonplaceholder_api())
    print(f"\n✅ Generated training data from {result['successful']} successful API calls")
