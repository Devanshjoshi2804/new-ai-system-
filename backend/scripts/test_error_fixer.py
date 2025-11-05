"""Test Error Fixer Model"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.application.ai.ml_models.error_fixer import ErrorFixer

def test_fixer():
    print("\n" + "="*60)
    print("  TESTING ERROR FIXER MODEL")
    print("="*60 + "\n")

    print("[1/4] Initializing error fixer...")
    fixer = ErrorFixer()
    print("   [OK] Fixer initialized\n")

    print("[2/4] Testing error analysis...")

    test_errors = [
        "Invalid JSON format in request body",
        "Required field 'email' is missing",
        "Authentication failed: Invalid token",
        "Resource not found: User with ID 123",
        "Rate limit exceeded: Too many requests",
    ]

    for error_msg in test_errors:
        analysis = fixer.model.analyze_error_pattern(error_msg)
        error_types = ', '.join(analysis['error_types'])
        fixable = "Yes" if analysis['fixable'] else "No"
        print(f"   Error: {error_msg[:50]}...")
        print(f"      Types: {error_types}")
        print(f"      Fixable: {fixable}")
        print()

    print("[3/4] Testing error correction...")

    test_cases = [
        {
            'error_request': 'POST /api/users {"name": "John", "age": 30}',
            'error_message': 'Required field email is missing',
            'description': 'Missing required field'
        },
        {
            'error_request': 'POST /api/products {"title": "Widget", "price": "invalid"}',
            'error_message': 'Invalid type for field price: expected number',
            'description': 'Invalid field type'
        },
        {
            'error_request': 'GET /api/users/abc',
            'error_message': 'Invalid ID format: expected integer',
            'description': 'Invalid ID format'
        },
        {
            'error_request': 'POST /api/auth/login {"username": "admin"}',
            'error_message': 'Missing required field: password',
            'description': 'Authentication error'
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"   Test {i}: {test_case['description']}")
        print(f"      Original: {test_case['error_request']}")
        print(f"      Error: {test_case['error_message']}")

        result = fixer.fix(test_case['error_request'], test_case['error_message'])

        print(f"      Fixed: {result['fixed_request']}")
        print(f"      Confidence: {result['confidence']:.2%}")
        print(f"      Error Types: {', '.join(result['error_analysis']['error_types'])}")
        print()

    print("[4/4] Model info:")
    print(f"   Device: {fixer.model.device}")
    print(f"   Model type: BartForConditionalGeneration")
    print(f"   Tokenizer: BartTokenizer")
    print(f"   Error patterns: 7 types detected")

    print("\n" + "="*60)
    print("  TEST COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_fixer()
