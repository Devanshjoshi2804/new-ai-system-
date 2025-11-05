"""Test Data Collector for ML Training"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.application.ai.ml_models.data_collector import DataCollector


async def test_data_collector():
    """Test the data collector"""
    print("\n" + "="*60)
    print("  TESTING DATA COLLECTOR FOR ML TRAINING")
    print("="*60 + "\n")
    
    collector = DataCollector()
    
    print("[1/3] Connecting to MongoDB...")
    await collector.connect()
    print("   [OK] Connected\n")
    
    print("[2/3] Collecting endpoint examples...")
    examples = await collector.collect_endpoint_examples(limit=100)
    print(f"   [OK] Collected {len(examples)} examples\n")
    
    if examples:
        print("[3/3] Sample data:")
        for i, example in enumerate(examples[:5]):
            print(f"   Example {i+1}: {example['method']} {example['url'][:50]} -> {example['label']}")
        
        print(f"\n[STATS] Label distribution:")
        from collections import Counter
        labels = Counter(ex['label'] for ex in examples)
        for label, count in labels.most_common():
            print(f"   {label}: {count}")
    else:
        print("   [INFO] No examples found in database")
        print("   [TIP] Run some API tests first to generate training data")
    
    print("\n" + "="*60)
    print("  DATA COLLECTOR TEST COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_data_collector())
