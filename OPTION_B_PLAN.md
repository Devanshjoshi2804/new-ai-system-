# 🔄 Option B: Build One Mini-Loop - Step-by-Step Plan

**Goal:** Prove continuous learning works by building ONE complete loop
**Time Estimate:** 2-3 hours
**Risk:** Low (small scope, test everything)

---

## 📋 Current Status

### Discovery
- ✅ Flow DB directory doesn't exist yet (no data collected)
- ✅ Testing infrastructure exists (`simple_testing.py`)
- ✅ Flow DB storage code ready (`flow_store_local.py`)

### Conclusion
**We need to generate data first, then train on it**

---

## 🎯 Step-by-Step Plan

### Phase 1: Generate Training Data (Option A first)
**Goal:** Run tests to populate Flow DB with real data

#### Step 1.1: Check Backend Status
```bash
# Is backend running?
curl http://localhost:8000/health

# If not, start it
cd backend
python -m uvicorn src.main:app --reload --port 8000
```

#### Step 1.2: Run a Simple Test
**Option 1: Use JSONPlaceholder (public API, always works)**
```bash
# Test with public API
curl -X POST http://localhost:8000/api/simple-testing/test \
  -H "Content-Type: application/json" \
  -d '{
    "partner_id": "test-001",
    "documentation_id": "test-doc",
    "base_url": "https://jsonplaceholder.typicode.com"
  }'
```

**Option 2: Use existing documentation in MongoDB**
```python
# If you have API docs uploaded, use those
# Check what docs exist:
from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017")
db = client["cargodham_ai"]
docs = list(db.api_documentation.find())
print(f"Found {len(docs)} documentation files")
```

#### Step 1.3: Verify Flow DB Generated
```bash
# Check if Flow DB was created
ls -la ./data/flow_chroma_db/

# Should see ChromaDB files
```

**Expected:** After running tests, Flow DB should have:
- Request/response pairs stored
- ~10-20 examples from test run

---

### Phase 2: Extract Training Data
**Goal:** Convert Flow DB data to ML training format

#### Step 2.1: Create Flow DB Reader
```python
# File: backend/scripts/extract_flow_db_data.py

import chromadb
import json
from sentence_transformers import SentenceTransformer

def extract_training_data():
    """Extract all data from Flow DB"""
    # Connect to Flow DB
    client = chromadb.PersistentClient(path="./data/flow_chroma_db")

    # Get all collections
    collections = client.list_collections()
    print(f"Found {len(collections)} collections")

    training_examples = []

    for collection in collections:
        # Get all documents
        results = collection.get()

        # Parse into training format
        for i, doc in enumerate(results['documents']):
            metadata = results['metadatas'][i]

            if metadata['type'] == 'request':
                # This is a payload generation example
                example = {
                    'endpoint': metadata['endpoint'],
                    'request_payload': json.loads(metadata['data']),
                    'type': 'request'
                }
                training_examples.append(example)

    return training_examples
```

#### Step 2.2: Convert to Training Format
```python
def convert_to_ml_format(flow_examples):
    """
    Convert Flow DB examples to format for PayloadGenerator training

    Input: Flow DB examples
    Output: Training examples in format:
    {
        'url': '/api/users',
        'method': 'POST',
        'successful_payload': {...},
        'label': 'CREATE'
    }
    """
    training_data = []

    for example in flow_examples:
        if example['type'] == 'request':
            # Parse endpoint
            method, path = example['endpoint'].split(' ', 1)

            training_data.append({
                'url': path,
                'method': method,
                'successful_payload': example['request_payload'],
                'label': infer_label(method, path)
            })

    return training_data

def infer_label(method, path):
    """Infer endpoint type"""
    if 'auth' in path.lower() or 'login' in path.lower():
        return 'AUTH'
    elif method == 'POST':
        return 'CREATE'
    elif method == 'GET':
        return 'READ'
    elif method in ['PUT', 'PATCH']:
        return 'UPDATE'
    elif method == 'DELETE':
        return 'DELETE'
    return 'READ'
```

**Expected Output:**
```json
[
  {
    "url": "/api/users",
    "method": "POST",
    "successful_payload": {"name": "test", "email": "test@example.com"},
    "label": "CREATE"
  },
  ...
]
```

---

### Phase 3: Train Model with Real Data
**Goal:** Train PayloadGenerator on Flow DB data

#### Step 3.1: Simple Training Script
```python
# File: backend/scripts/train_from_flow_db.py

from src.application.ai.ml_models.payload_generator import PayloadGeneratorModel
from extract_flow_db_data import extract_training_data, convert_to_ml_format

async def train_payload_generator():
    """Train PayloadGenerator on real Flow DB data"""

    # Step 1: Extract from Flow DB
    print("[1/4] Extracting data from Flow DB...")
    flow_examples = extract_training_data()
    print(f"Found {len(flow_examples)} examples")

    # Step 2: Convert to training format
    print("[2/4] Converting to ML format...")
    training_data = convert_to_ml_format(flow_examples)
    print(f"Converted {len(training_data)} training examples")

    # Step 3: Train model (simplified)
    print("[3/4] Training PayloadGenerator...")
    # For now, just cache successful payloads (simple approach)
    payload_cache = {}
    for example in training_data:
        key = f"{example['method']} {example['url']}"
        payload_cache[key] = example['successful_payload']

    # Save cache
    with open('./models/payload_cache.json', 'w') as f:
        json.dump(payload_cache, f, indent=2)

    print(f"[4/4] Model trained! Cached {len(payload_cache)} payloads")
    return payload_cache
```

**Note:** For the mini-loop, we'll use a simple caching approach:
- Store successful payloads in a dict
- Look up by endpoint
- This proves the concept without needing full transformer training

---

### Phase 4: Create Hybrid Predictor
**Goal:** Try cached model first, fallback to AI

#### Step 4.1: Hybrid Payload Generator
```python
# File: backend/src/application/ai/simple_testing/payload_generator_hybrid.py

import json
from typing import Dict, Any

# Import original AI-based generator
from .payload_generator import generate_complete_payload as generate_with_ai

class HybridPayloadGenerator:
    """Try model first, fallback to AI"""

    def __init__(self):
        # Load trained cache
        try:
            with open('./models/payload_cache.json', 'r') as f:
                self.payload_cache = json.load(f)
            print(f"[MODEL] Loaded {len(self.payload_cache)} cached payloads")
        except:
            self.payload_cache = {}
            print("[MODEL] No cache found, using AI only")

        self.stats = {
            'model_hits': 0,
            'ai_fallback': 0,
            'total': 0
        }

    async def generate(self, endpoint: dict, context_data: dict, flow_db):
        """Generate payload - try model first"""
        self.stats['total'] += 1
        endpoint_key = f"{endpoint['method']} {endpoint['path']}"

        # Try model cache first
        if endpoint_key in self.payload_cache:
            self.stats['model_hits'] += 1
            print(f"[MODEL] Using cached payload (hit rate: {self.get_hit_rate():.1%})")
            return self.payload_cache[endpoint_key]

        # Fallback to AI
        self.stats['ai_fallback'] += 1
        print(f"[AI] No cached payload, using AI (hit rate: {self.get_hit_rate():.1%})")
        return await generate_with_ai(endpoint, context_data, flow_db)

    def get_hit_rate(self):
        """Calculate model hit rate"""
        if self.stats['total'] == 0:
            return 0.0
        return self.stats['model_hits'] / self.stats['total']

    def get_stats(self):
        """Get performance stats"""
        return {
            'total_predictions': self.stats['total'],
            'model_hits': self.stats['model_hits'],
            'ai_fallback': self.stats['ai_fallback'],
            'hit_rate': self.get_hit_rate(),
            'cost_savings': f"{self.stats['model_hits']} AI calls saved"
        }
```

#### Step 4.2: Update test_executor.py
```python
# In test_executor.py, replace this line:
# test_payload = await generate_complete_payload(endpoint, context_data, flow_db)

# With:
from .payload_generator_hybrid import HybridPayloadGenerator
hybrid_generator = HybridPayloadGenerator()
test_payload = await hybrid_generator.generate(endpoint, context_data, flow_db)
```

---

### Phase 5: Test and Measure
**Goal:** Prove the loop works

#### Step 5.1: Run Test Again
```bash
# Run the same test
curl -X POST http://localhost:8000/api/simple-testing/test \
  -H "Content-Type: application/json" \
  -d '{
    "partner_id": "test-001",
    "documentation_id": "test-doc",
    "base_url": "https://jsonplaceholder.typicode.com"
  }'
```

#### Step 5.2: Check Performance
```python
# Get stats from hybrid generator
stats = hybrid_generator.get_stats()
print(f"""
Hybrid Generator Performance:
- Total predictions: {stats['total_predictions']}
- Model hits: {stats['model_hits']}
- AI fallback: {stats['ai_fallback']}
- Hit rate: {stats['hit_rate']:.1%}
- Cost savings: {stats['cost_savings']}
""")
```

**Expected Results:**
- First run: 0% hit rate (no cache)
- Second run: 50-80% hit rate (using cached payloads)
- Third run: 80-100% hit rate (most cached)

#### Step 5.3: Measure Speed
```python
import time

# Measure AI time
start = time.time()
await generate_with_ai(endpoint, context, flow_db)
ai_time = time.time() - start

# Measure model time
start = time.time()
await hybrid_generator.generate(endpoint, context, flow_db)
model_time = time.time() - start

speedup = ai_time / model_time
print(f"Model is {speedup:.1f}x faster!")
```

**Expected:**
- AI API: 500-2000ms (network + inference)
- Cached model: 1-5ms (instant lookup)
- **Speedup: 100-2000x faster!**

---

## 🎉 Success Criteria

### Proof of Concept Works If:
1. ✅ Flow DB collects data from tests
2. ✅ Can extract and convert data to training format
3. ✅ Hybrid generator uses cached payloads
4. ✅ Hit rate increases with more tests
5. ✅ Model is faster than AI API
6. ✅ Accuracy is same or better

### Measurements to Track:
- **Hit Rate:** % of predictions from model vs AI
- **Speed:** Model time vs AI time
- **Cost:** AI API calls saved
- **Accuracy:** Do cached payloads still work?

---

## 🚧 Potential Issues & Solutions

### Issue 1: No data in Flow DB
**Solution:** Run more tests to generate data

### Issue 2: Data format mismatch
**Solution:** Fix extraction script, document format

### Issue 3: Model worse than AI
**Solution:** That's okay! We learned something. Document why.

### Issue 4: Can't replicate payloads
**Solution:** Some endpoints need dynamic data. That's fine.

---

## 📝 Next Steps After Success

### If Mini-Loop Works:
1. Scale to all 3 models (Endpoint Classifier, Error Fixer)
2. Add confidence scoring (use AI if low confidence)
3. Build auto-retraining (retrain when N new examples)
4. Add performance dashboard

### If Mini-Loop Fails:
1. Document what we learned
2. Identify root cause
3. Decide: Fix approach or change strategy

---

## 🎯 Let's Start!

**Ready to begin?**
1. First, check if backend is running
2. Run a test to generate Flow DB data
3. Extract and convert data
4. Build hybrid generator
5. Test and measure!

**Which step should we start with?**
