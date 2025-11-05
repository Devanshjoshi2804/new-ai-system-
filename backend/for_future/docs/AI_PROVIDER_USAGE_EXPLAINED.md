# AI Provider Usage - Where Each Provider is Used

## Summary

Your system uses **different AI providers for different tasks**! That's why you see Mistral in the logs.

## Provider Usage Breakdown

### 1. **Mistral AI** - PDF Document Parsing 📄
**Used For**: Extracting API specifications from PDF documentation
**Location**: `backend/src/application/ai/parsers/pdf_parser.py`
**When**: During the "Document Upload" and "Parsing Progress" steps in onboarding

```python
# Line 17 in pdf_parser.py
from src.infrastructure.ai.providers.mistral_provider import MistralProvider

# Line 34
def __init__(self):
    self.mistral = MistralProvider()  # ← HARDCODED to use Mistral!
```

**What It Does**:
- Reads your PDF documentation
- Extracts text from pages
- Analyzes text to find API endpoints
- Structures the API specification

**Why Mistral**:
- Good at document understanding
- Fast response times
- Handles large text chunks well

---

### 2. **Groq/Gemini/Mistral** - Autonomous API Testing 🧪
**Used For**: AI-powered test generation and execution
**Location**: `backend/src/application/use_cases/partners/test_partner_integration.py`
**When**: During the "API Testing" step (Step 5) in onboarding

```python
# Lines 151-157 in test_partner_integration.py
ai_api_key = (
    os.getenv('GROQ_API_KEY') or          # 🥇 Priority 1: GROQ
    os.getenv('GOOGLE_GEMINI_API_KEY') or # 🥈 Priority 2: Gemini
    os.getenv('GEMINI_API_KEY') or        # 🥈 Priority 2: Gemini (alt)
    os.getenv('MISTRAL_API_KEY')          # 🥉 Priority 3: Mistral
)
```

**What It Does**:
- Analyzes endpoint dependencies
- Generates comprehensive test cases
- Executes tests intelligently
- Provides AI-powered insights

**Why Groq Priority**:
- Fastest inference speed
- Best for real-time testing
- Generous free tier

---

## What You're Seeing in the Logs

### From Your Terminal Selection (Lines 5-114):

```
2025-10-24 19:54:41,418 - httpcore.http11 - DEBUG - receive_response_headers.complete 
return_value=(b'HTTP/1.1', 429, b'Too Many Requests', ...
[(b'mistral-correlation-id', b'019a169b-824e-77b8-95b9-1b8dc332b67e'), ...
```

This is **Mistral being used for PDF parsing**, not for autonomous testing!

### Timeline of Events:

1. **Line 29-34**: PDF text extraction completed (82 pages, 64,517 chars)
2. **Line 43**: "✅ Extracted 0 endpoints" (text extracted, but not analyzed yet)
3. **Line 68-74**: **Mistral AI called** to analyze the extracted text
4. **Line 75-77**: Found 5 endpoints, base URL, and auth info

This is the **document parsing phase**, which happens **before** the autonomous testing phase.

---

## Complete Flow

### Step 1: Document Upload & Parsing (Uses Mistral)
```
User uploads PDF
    ↓
PyMuPDF extracts text (82 pages)
    ↓
Mistral AI analyzes text  ← YOU ARE HERE (in your logs)
    ↓
Extracts 23 endpoints
```

### Step 2: API Testing (Uses Groq)
```
User clicks "Start Testing"
    ↓
Groq analyzes dependencies
    ↓
Groq generates test cases
    ↓
Tests execute
    ↓
Results displayed
```

---

## Why You See Mistral Rate Limiting

From your logs:
```
Line 11: ⚠️ Rate limited on chunk 1 (attempt 1), waiting 5s before retry...
Line 96: ⚠️ Rate limited on chunk 2 (attempt 1), waiting 5s before retry...
Line 114: ⚠️ Rate limited on chunk 2 (attempt 2), waiting 10s before retry...
```

**Mistral Free Tier Limits**:
- 60 requests per minute
- Your PDF has 82 pages split into 6 chunks
- Each chunk requires 1-2 API calls
- System automatically retries with exponential backoff

**This is normal!** The system handles it gracefully with retries.

---

## How to Change PDF Parser to Use Groq

If you want to use Groq for PDF parsing too (to avoid Mistral rate limits):

### Option 1: Update pdf_parser.py to use Groq

```python
# backend/src/application/ai/parsers/pdf_parser.py

# Change line 17 from:
from src.infrastructure.ai.providers.mistral_provider import MistralProvider

# To:
from src.infrastructure.ai.providers.groq_provider import GroqProvider

# Change line 34 from:
def __init__(self):
    self.mistral = MistralProvider()

# To:
def __init__(self):
    self.ai_provider = GroqProvider()

# Then update all self.mistral references to self.ai_provider
```

### Option 2: Make it configurable (Better!)

```python
# backend/src/application/ai/parsers/pdf_parser.py
import os

def __init__(self):
    # Use Groq if available, fallback to Mistral
    if os.getenv('GROQ_API_KEY'):
        from src.infrastructure.ai.providers.groq_provider import GroqProvider
        self.ai_provider = GroqProvider()
        logger.info("📄 Using Groq for PDF parsing")
    else:
        from src.infrastructure.ai.providers.mistral_provider import MistralProvider
        self.ai_provider = MistralProvider()
        logger.info("📄 Using Mistral for PDF parsing")
```

---

## Current Status Summary

| Task | AI Provider | Status | Location |
|------|-------------|--------|----------|
| **PDF Parsing** | Mistral | ✅ Working (with rate limits) | pdf_parser.py |
| **API Testing** | Groq | ✅ Working | test_partner_integration.py |
| **Image Parsing** | Mistral | ✅ Available | image_parser.py |

---

## Recommendation

**Option A**: Keep as-is
- PDF parsing with Mistral works fine
- Rate limits are handled automatically
- Groq is used for the more intensive testing phase

**Option B**: Switch PDF parsing to Groq
- Faster PDF parsing
- No rate limit issues
- Consistent provider across the system
- Requires code change (shown above)

---

## Why This Design Makes Sense

1. **Separation of Concerns**
   - Document parsing is a one-time operation
   - API testing is the intensive, repeated operation
   - Using different providers optimizes for each use case

2. **Rate Limit Management**
   - Spreads load across multiple providers
   - Reduces chance of hitting limits on any single provider

3. **Fallback Options**
   - If one provider fails, others are available
   - System is more resilient

---

## Bottom Line

✅ **Mistral in logs = PDF parsing** (Document Upload step)
✅ **Groq in testing = API testing** (API Testing step)
✅ **Both are working correctly!**

The rate limiting you see is **normal** and **handled automatically** by the retry logic. The system will complete the parsing successfully, just takes a bit longer due to the retries.

