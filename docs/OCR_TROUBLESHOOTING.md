# 🔧 OCR Troubleshooting Guide

## Quick Diagnostics

### 1. Check if Backend is Running

Open a terminal and run:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok"
}
```

If you get an error, the backend server is not running. Start it with:
```bash
cd backend
python run_server.py
```

### 2. Check OCR Service Health

```bash
curl http://localhost:8000/api/ocr/health
```

Expected response:
```json
{
  "status": "healthy",
  "ocr_service": "initialized",
  "cache_status": "connected" or "disabled",
  "model": "pixtral-12b-2409",
  "concurrent_limit": 5
}
```

### 3. Check Frontend is Running

Open: http://localhost:3000/ocr

If you see a blank page or error, start the frontend:
```bash
cd frontend
npm run dev
```

## Common Errors and Solutions

### Error: "OCR extraction failed"

**Check the browser console** (F12 → Console tab) for detailed error messages.

**Possible causes:**

#### 1. Backend not running
**Solution**: Start the backend server
```bash
cd backend
python run_server.py
```

#### 2. Mistral API key missing
**Error**: "Mistral API key is required for OCR service"

**Solution**: Add API key to `.env` file:
```bash
# backend/.env
MISTRAL_API_KEY=your_key_here
```

#### 3. Poppler not found (Windows)
**Error**: "Is poppler installed and in PATH?"

**Solution**: 
- Ensure `poppler-24.08.0/` folder is in the project root
- Or install Poppler system-wide

#### 4. Rate limit exceeded
**Error**: "Rate limit exceeded"

**Solution**: Wait 60 seconds (Mistral API limit: 60 requests/minute)

#### 5. File too large
**Error**: "File too large. Maximum size: 50MB"

**Solution**: Compress the PDF or use a smaller file

#### 6. Redis connection failed
**Warning in logs**: "Failed to connect to Redis. Caching disabled."

**Solution**: This is OK! Caching will be disabled but OCR will still work.

To enable caching:
```bash
# Install Redis (Windows)
# Download from: https://github.com/microsoftarchive/redis/releases
# Or use Docker:
docker run -d -p 6379:6379 redis
```

### Error: "Failed to parse PDF"

**Possible causes:**

#### 1. PDF is actually sent as PDF (not images)
**Check backend logs** for: "Image content must be a URL or base64 encoded image"

**Solution**: This should be fixed! But if you see this:
- Restart the backend server
- Clear browser cache
- Try again

#### 2. Corrupted PDF
**Solution**: Try a different PDF file

#### 3. Password-protected PDF
**Solution**: Remove password protection first

## Testing Steps

### Step 1: Test with Small Image

1. Create a simple text image:
   - Open Paint
   - Type "Hello World"
   - Save as `test.png`

2. Upload to OCR Viewer
3. Click "Extract Text"
4. Should work in < 1 second

### Step 2: Test with Small PDF (1 page)

1. Find a 1-page PDF (< 1 MB)
2. Upload to OCR Viewer
3. Click "Extract Text"
4. Should work in < 2 seconds

### Step 3: Test with Multi-page PDF

1. Upload a 5-10 page PDF
2. Watch the processing time
3. Navigate between pages

## Debug Mode

### Enable Verbose Logging

**Backend** (`backend/src/main.py`):
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Frontend**: Check browser console (F12)

### Test OCR API Directly

**Using curl:**

```bash
# Upload and extract
curl -X POST "http://localhost:8000/api/ocr/extract?extract_mode=full" \
  -F "file=@test.pdf" \
  -H "accept: application/json"
```

**Using Python:**

```python
import requests

url = "http://localhost:8000/api/ocr/extract"
files = {"file": open("test.pdf", "rb")}
params = {"extract_mode": "full"}

response = requests.post(url, files=files, params=params)
print(response.json())
```

## Check Backend Logs

**Look for these messages:**

✅ **Success:**
```
📄 Processing file: test.pdf (1010KB), mode: full
🔄 Converting PDF to images...
✅ Converted to 50 page(s)
📦 Processing batch 1 (5 pages)
✅ Extraction complete: 50 pages, 25.43s
```

❌ **Errors:**
```
❌ Poppler not found in project directory
❌ Pixtral API error: Rate limit exceeded
❌ PDF processing error: [error details]
```

## Performance Issues

### Slow extraction (> 5s per page)

**Possible causes:**
1. Large images (> 2048px)
2. High DPI (> 300)
3. Network latency to Mistral API
4. Rate limiting

**Solutions:**
1. Reduce image size
2. Lower DPI in settings
3. Use caching (Redis)
4. Process in batches

### Memory issues

**Symptoms:**
- Backend crashes during processing
- "Out of memory" errors

**Solutions:**
1. Reduce concurrent limit (default: 5)
2. Process smaller batches
3. Increase system RAM
4. Use server with more resources

## Getting Help

### Collect Debug Information

When asking for help, provide:

1. **Backend logs** (last 50 lines)
2. **Frontend console errors** (F12 → Console)
3. **Network tab details** (F12 → Network → select failed request → Headers & Response)
4. **File details** (type, size, page count)
5. **System info** (OS, Python version, Node version)

### Example Debug Report

```
Environment:
- OS: Windows 10
- Python: 3.11.0
- Node: 18.x
- Backend: Running on http://localhost:8000
- Frontend: Running on http://localhost:3000

Error:
- Message: "OCR extraction failed"
- File: test.pdf (1.5 MB, 10 pages)
- Extract Mode: full

Backend Log:
❌ PDF processing error: Is poppler installed and in PATH?

Network Response:
Status: 500 Internal Server Error
Detail: "OCR extraction failed: ..."
```

## Quick Fixes Summary

| Issue | Quick Fix |
|-------|-----------|
| Backend not running | `cd backend && python run_server.py` |
| Frontend not running | `cd frontend && npm run dev` |
| Mistral API key missing | Add `MISTRAL_API_KEY=xxx` to `.env` |
| Poppler not found | Ensure `poppler-24.08.0/` is in project root |
| Rate limit hit | Wait 60 seconds |
| File too large | Use smaller file (< 50 MB) |
| Redis not available | OK! Caching will be disabled |

## Still Not Working?

1. ✅ Restart backend server
2. ✅ Clear browser cache (Ctrl+Shift+Delete)
3. ✅ Try incognito mode
4. ✅ Check firewall/antivirus
5. ✅ Try a different file
6. ✅ Check backend logs for detailed errors
7. ✅ Test health endpoints
8. ✅ Verify Mistral API key is valid

---

**Remember**: The improved error messages in the frontend will now show the actual backend error! Check the red error box in the OCR Viewer.

