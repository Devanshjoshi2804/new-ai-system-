"""
Discovery System Verification Script
Tests the complete AI discovery pipeline end-to-end
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import httpx
import json
from datetime import datetime

# Test configuration
API_BASE = "http://localhost:8000"
TEST_API_URL = "https://jsonplaceholder.typicode.com"  # Public test API


async def test_discovery_system():
    """
    Complete end-to-end test of discovery system
    """
    print("=" * 80)
    print(" AI DISCOVERY SYSTEM - VERIFICATION TEST")
    print("=" * 80)
    print()

    async with httpx.AsyncClient(timeout=60.0) as client:

        # Step 1: Check if server is running
        print("[1/6] Checking if server is running...")
        try:
            response = await client.get(f"{API_BASE}/")
            assert response.status_code == 200, "Server not responding"
            print(f"   [OK] Server is running: {response.json()}")
        except Exception as e:
            print(f"   [FAIL] Server check failed: {e}")
            print(f"   [TIP] Make sure to start the server: python -m uvicorn src.main:app --reload")
            return False

        # Step 2: Test discovery health endpoint
        print("\n[2/6] Testing discovery health endpoint...")
        try:
            response = await client.get(f"{API_BASE}/api/discovery/health")
            assert response.status_code == 200
            health_data = response.json()
            print(f"   [OK] Discovery service is healthy")
            print(f"   Features: {', '.join(health_data.get('features', []))}")
        except Exception as e:
            print(f"   [FAIL] Health check failed: {e}")
            return False

        # Step 3: Start discovery
        print("\n[3/6] Starting API discovery...")
        try:
            discovery_request = {
                "partner_id": "test_partner_001",
                "partner_name": "JSONPlaceholder Test",
                "minimal_info": TEST_API_URL,
                "auth_token": None,
                "sample_endpoint": "/posts"
            }

            response = await client.post(
                f"{API_BASE}/api/discovery/explore",
                json=discovery_request
            )

            assert response.status_code == 200, f"Discovery failed: {response.text}"
            discovery_data = response.json()
            discovery_id = discovery_data['discovery_id']

            print(f"   [OK] Discovery started")
            print(f"   Discovery ID: {discovery_id}")
            print(f"   Status: {discovery_data['status']}")

        except Exception as e:
            print(f"   [FAIL] Discovery start failed: {e}")
            return False

        # Step 4: Poll for status
        print("\n[4/6] Monitoring discovery progress...")
        max_polls = 30  # 30 seconds timeout
        poll_count = 0

        while poll_count < max_polls:
            try:
                response = await client.get(
                    f"{API_BASE}/api/discovery/status/{discovery_id}"
                )

                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data['status']
                    progress = status_data['progress']
                    current_step = status_data['current_step']
                    endpoints_found = status_data['endpoints_found']

                    print(f"   Progress: {progress*100:.0f}% | {current_step} | Endpoints: {endpoints_found}")

                    if status == 'completed':
                        print(f"   [OK] Discovery completed!")
                        break
                    elif status == 'failed':
                        print(f"   [FAIL] Discovery failed: {status_data.get('errors')}")
                        return False

                await asyncio.sleep(1)
                poll_count += 1

            except Exception as e:
                print(f"   [WARN]  Status check error: {e}")
                await asyncio.sleep(1)
                poll_count += 1

        if poll_count >= max_polls:
            print(f"   [WARN]  Discovery timeout (still in progress)")

        # Step 5: Get results
        print("\n[5/6] Retrieving discovery results...")
        try:
            response = await client.get(
                f"{API_BASE}/api/discovery/results/{discovery_id}"
            )

            assert response.status_code == 200, "Failed to get results"
            results = response.json()

            print(f"   [OK] Results retrieved successfully")
            print(f"\n   📊 DISCOVERY RESULTS:")
            print(f"   Base URL: {results['base_url']}")
            print(f"   Endpoints found: {len(results['endpoints'])}")
            print(f"   API Version: {results.get('api_version', 'Not detected')}")
            print(f"   Discovery time: {results['discovery_time']:.2f}s")

            # Show auth config
            if results.get('auth_config'):
                auth = results['auth_config']
                print(f"\n   🔐 AUTHENTICATION:")
                print(f"   Type: {auth['auth_type']}")
                print(f"   Confidence: {auth['confidence']*100:.0f}%")
                if auth.get('header_name'):
                    print(f"   Header: {auth['header_name']}")

            # Show sample endpoints
            if results['endpoints']:
                print(f"\n   🔗 SAMPLE ENDPOINTS:")
                for i, endpoint in enumerate(results['endpoints'][:5]):
                    print(f"   {i+1}. {endpoint['method']} {endpoint['path']}")
                    if endpoint.get('summary'):
                        print(f"      {endpoint['summary']}")

            # Show schemas
            if results.get('schemas'):
                print(f"\n   📋 SCHEMAS INFERRED: {len(results['schemas'])}")

            # Show dependency graph
            if results.get('dependency_graph'):
                graph = results['dependency_graph']
                print(f"\n   🔗 DEPENDENCY GRAPH:")
                print(f"   Nodes: {len(graph.get('nodes', []))}")
                print(f"   Dependencies: {len(graph.get('edges', []))}")
                if graph.get('execution_order'):
                    print(f"   Execution order: {len(graph['execution_order'])} steps")

            # Show workflows
            if results.get('workflows'):
                print(f"\n   [WORKFLOW]  WORKFLOWS GENERATED: {len(results['workflows'])}")
                for workflow in results['workflows']:
                    print(f"   Type: {workflow.get('type')}, Steps: {len(workflow.get('steps', []))}")

        except Exception as e:
            print(f"   [FAIL] Failed to get results: {e}")
            return False

        # Step 6: Verify data integrity
        print("\n[6/6] Verifying data integrity...")
        try:
            assert len(results['endpoints']) > 0, "No endpoints discovered"
            assert results['base_url'] == TEST_API_URL, "Base URL mismatch"
            assert results['status'] == 'completed', "Status not completed"
            assert results['discovery_time'] > 0, "Invalid discovery time"

            print(f"   [OK] All data integrity checks passed")

        except AssertionError as e:
            print(f"   [FAIL] Data integrity check failed: {e}")
            return False

    # Final summary
    print("\n" + "=" * 80)
    print(" TEST SUMMARY")
    print("=" * 80)
    print(f" [OK] All tests passed!")
    print(f" Discovery system is fully operational!")
    print("=" * 80)

    return True


async def test_individual_components():
    """
    Test individual discovery components
    """
    print("\n" + "=" * 80)
    print(" COMPONENT-LEVEL TESTS")
    print("=" * 80)

    from src.application.ai.discovery.api_explorer import APIExplorer
    from src.application.ai.discovery.auth_detector import AuthDetector
    from src.application.ai.discovery.schema_inferencer import SchemaInferencer
    from src.application.ai.discovery.relationship_analyzer import RelationshipAnalyzer

    # Test APIExplorer
    print("\n[TEST] API Explorer...")
    try:
        async with APIExplorer() as explorer:
            result = await explorer.explore(TEST_API_URL)
            assert len(result.endpoints) > 0
            print(f"   [OK] Found {len(result.endpoints)} endpoints")
    except Exception as e:
        print(f"   [FAIL] Failed: {e}")

    # Test AuthDetector
    print("\n[TEST] Auth Detector...")
    try:
        async with AuthDetector() as detector:
            result = await detector.detect(TEST_API_URL)
            print(f"   [OK] Detected: {result.auth_type} (confidence: {result.confidence*100:.0f}%)")
    except Exception as e:
        print(f"   [FAIL] Failed: {e}")

    # Test SchemaInferencer
    print("\n[TEST] Schema Inferencer...")
    try:
        async with SchemaInferencer() as inferencer:
            schemas = await inferencer.infer_schemas(
                TEST_API_URL,
                [{"method": "GET", "path": "/posts", "auth_required": False}]
            )
            print(f"   [OK] Inferred {len(schemas)} schemas")
    except Exception as e:
        print(f"   [FAIL] Failed: {e}")

    # Test RelationshipAnalyzer
    print("\n[TEST] Relationship Analyzer...")
    try:
        async with RelationshipAnalyzer() as analyzer:
            graph = await analyzer.analyze(
                TEST_API_URL,
                [
                    {"method": "POST", "path": "/posts", "auth_required": False},
                    {"method": "GET", "path": "/posts/{id}", "auth_required": False}
                ]
            )
            print(f"   [OK] Built graph with {len(graph.graph.nodes())} nodes")
    except Exception as e:
        print(f"   [FAIL] Failed: {e}")


async def main():
    """Run all tests"""
    print("""
    ==================================================================

              AI DISCOVERY SYSTEM VERIFICATION
              Production-Ready Testing Suite

    ==================================================================
    """)

    # Run component tests first
    await test_individual_components()

    # Run end-to-end test
    success = await test_discovery_system()

    if success:
        print("\n🎉 ALL SYSTEMS OPERATIONAL! 🎉")
        print("\nNext steps:")
        print("1. Access API docs: http://localhost:8000/docs")
        print("2. Try discovery endpoint: POST /api/discovery/explore")
        print("3. View results: GET /api/discovery/results/{discovery_id}")
        return 0
    else:
        print("\n[FAIL] TESTS FAILED")
        print("\nTroubleshooting:")
        print("1. Make sure MongoDB is running")
        print("2. Make sure server is started")
        print("3. Check logs for errors")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
