"""Test Payload Generator"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.application.ai.ml_models.payload_generator import PayloadGenerator

def test_generator():
    print("\n" + "="*60)
    print("  TESTING PAYLOAD GENERATOR")
    print("="*60 + "\n")

    print("[1/3] Initializing generator...")
    generator = PayloadGenerator()
    print("   [OK] Generator initialized\n")

    print("[2/3] Testing payload generation...")

    test_cases = [
        ("POST", "/api/users", "User creation"),
        ("POST", "/api/products", "Product creation"),
        ("POST", "/api/orders", "Order creation"),
        ("PUT", "/api/users/123", "User update"),
        ("POST", "/api/auth/login", "Authentication"),
    ]

    for method, url, description in test_cases:
        result = generator.generate(url, method)
        payload = result['payload']
        confidence = result['confidence']
        raw = result.get('raw_text', '')

        print(f"   [{method}] {url}")
        print(f"      Description: {description}")
        print(f"      Generated: {payload}")
        print(f"      Confidence: {confidence:.2%}")
        if raw and raw != str(payload):
            print(f"      Raw: {raw[:80]}...")
        print()

    print("[3/3] Model info:")
    print(f"   Device: {generator.model.device}")
    print(f"   Model type: T5ForConditionalGeneration")
    print(f"   Tokenizer: T5Tokenizer")

    print("\n" + "="*60)
    print("  TEST COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_generator()
