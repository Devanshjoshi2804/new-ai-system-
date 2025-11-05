"""Test Endpoint Classifier"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.application.ai.ml_models.endpoint_classifier import EndpointClassifier

def test_classifier():
    print("\n" + "="*60)
    print("  TESTING ENDPOINT CLASSIFIER")
    print("="*60 + "\n")
    
    print("[1/3] Initializing classifier...")
    classifier = EndpointClassifier()
    print("   [OK] Classifier initialized\n")
    
    print("[2/3] Testing predictions...")
    
    test_cases = [
        ("POST", "/api/users", "CREATE"),
        ("GET", "/api/users/123", "READ"),
        ("PUT", "/api/users/123", "UPDATE"),
        ("DELETE", "/api/users/123", "DELETE"),
        ("POST", "/api/auth/login", "AUTH"),
        ("GET", "/api/health", "HEALTH"),
        ("GET", "/api/search", "SEARCH"),
    ]
    
    correct = 0
    for method, url, expected in test_cases:
        result = classifier.predict(url, method)
        predicted = result['label']
        confidence = result['confidence']
        
        status = "[OK]" if predicted == expected else "[DIFF]"
        print(f"   {status} {method:6} {url:30} -> {predicted:8} ({confidence:.2%})")
        if predicted == expected:
            correct += 1
    
    accuracy = correct / len(test_cases)
    print(f"\n   Accuracy: {accuracy:.1%} ({correct}/{len(test_cases)})")
    
    print("\n[3/3] Model info:")
    print(f"   Device: {classifier.device}")
    print(f"   Labels: {len(classifier.LABELS)}")
    print(f"   Available: {', '.join(classifier.LABELS)}")
    
    print("\n" + "="*60)
    print("  TEST COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_classifier()
