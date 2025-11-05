# OCR API Quick Start Guide

## Endpoints Overview

### 1. Extract Text from File
**Endpoint:** `POST /api/ocr/extract`

Extract text from uploaded document (PDF, DOCX, images).

```bash
curl -X POST "http://localhost:8000/api/ocr/extract?extract_mode=structured" \
  -F "file=@document.pdf"
```

**Query Parameters:**
- `extract_mode` (optional): `full`, `structured`, or `tables`
  - `full` - Extract all text as-is (default)
  - `structured` - Extract with formatting (headers, lists)
  - `tables` - Focus on extracting tables

**Response:**
```json
{
  "success": true,
  "text": "Full document text...",
  "pages": ["Page 1 text...", "Page 2 text..."],
  "page_count": 2,
  "processing_time": 1.23,
  "file_name": "document.pdf",
  "metadata": {
    "total_pages": 2,
    "extraction_mode": "structured",
    "format": "pdf"
  },
  "from_cache": false
}
```

### 2. Batch Extract (Multiple Files)
**Endpoint:** `POST /api/ocr/extract/batch`

Process multiple files concurrently (up to 10 files).

```bash
curl -X POST "http://localhost:8000/api/ocr/extract/batch?extract_mode=full" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@invoice.jpg"
```

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "success": true,
      "text": "Doc 1 text...",
      "file_name": "doc1.pdf",
      "processing_time": 0.8
    },
    {
      "success": true,
      "text": "Doc 2 text...",
      "file_name": "doc2.pdf",
      "processing_time": 0.9
    }
  ],
  "total_files": 2,
  "total_processing_time": 1.7,
  "successful_count": 2,
  "failed_count": 0
}
```

### 3. Extract from URL
**Endpoint:** `POST /api/ocr/extract/url`

Download file from URL and extract text.

```bash
curl -X POST "http://localhost:8000/api/ocr/extract/url" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/document.pdf",
    "extract_mode": "structured"
  }'
```

### 4. Get Cache Statistics
**Endpoint:** `GET /api/ocr/stats`

Get OCR cache performance metrics.

```bash
curl "http://localhost:8000/api/ocr/stats"
```

**Response:**
```json
{
  "cache_hits": 45,
  "cache_misses": 15,
  "total_requests": 60,
  "hit_rate": "75.00%",
  "cache_enabled": true
}
```

### 5. Clear Cache
**Endpoint:** `DELETE /api/ocr/cache/clear`

Clear all cached OCR results.

```bash
curl -X DELETE "http://localhost:8000/api/ocr/cache/clear"
```

**Response:**
```json
{
  "success": true,
  "message": "Cleared 23 cache entries",
  "deleted_count": 23
}
```

## Frontend Usage (TypeScript)

### Single File Extraction

```typescript
import { extractTextFromFile } from '@/lib/api/vision';

async function handleFileUpload(file: File) {
  try {
    const result = await extractTextFromFile(file, 'structured');
    
    console.log(`Extracted ${result.page_count} pages`);
    console.log(`Processing time: ${result.processing_time}s`);
    console.log(`From cache: ${result.from_cache}`);
    console.log('Text:', result.text);
    
    // Access per-page text
    result.pages.forEach((pageText, i) => {
      console.log(`Page ${i + 1}:`, pageText);
    });
  } catch (error) {
    console.error('Extraction failed:', error);
  }
}
```

### Batch Processing

```typescript
import { extractTextFromBatch } from '@/lib/api/vision';

async function handleMultipleFiles(files: File[]) {
  try {
    const result = await extractTextFromBatch(files, 'full');
    
    console.log(`Processed ${result.successful_count}/${result.total_files} files`);
    console.log(`Total time: ${result.total_processing_time}s`);
    
    result.results.forEach((fileResult, i) => {
      if (fileResult.success) {
        console.log(`File ${i + 1}: ${fileResult.file_name}`);
        console.log('Text:', fileResult.text);
      } else {
        console.error(`File ${i + 1} failed:`, fileResult.error);
      }
    });
  } catch (error) {
    console.error('Batch processing failed:', error);
  }
}
```

### Extract from URL

```typescript
import { extractTextFromURL } from '@/lib/api/vision';

async function extractFromRemote(url: string) {
  try {
    const result = await extractTextFromURL(url, 'tables');
    console.log('Extracted text:', result.text);
  } catch (error) {
    console.error('URL extraction failed:', error);
  }
}
```

### Get Statistics

```typescript
import { getOCRStats, clearOCRCache } from '@/lib/api/vision';

async function showCacheStats() {
  const stats = await getOCRStats();
  console.log(`Cache hit rate: ${stats.hit_rate}`);
  console.log(`Total requests: ${stats.total_requests}`);
}

async function resetCache() {
  const result = await clearOCRCache();
  console.log(`Cleared ${result.deleted_count} entries`);
}
```

## Backend Usage (Python)

### Direct Service Usage

```python
from src.infrastructure.ai.ocr_service import get_ocr_service, ExtractionMode

async def extract_text():
    ocr = get_ocr_service()
    
    # Single file
    result = await ocr.extract_text_from_file(
        file_path="document.pdf",
        extract_mode=ExtractionMode.STRUCTURED
    )
    
    print(f"Pages: {result['page_count']}")
    print(f"Time: {result['processing_time']:.2f}s")
    print(f"Text: {result['text']}")
    
    # Batch processing
    files = [
        {'path': 'doc1.pdf', 'name': 'doc1.pdf'},
        {'path': 'doc2.pdf', 'name': 'doc2.pdf'},
    ]
    results = await ocr.batch_extract(files, ExtractionMode.FULL)
    
    for r in results:
        print(f"{r['file_name']}: {r['page_count']} pages")
```

### With Caching

```python
from src.infrastructure.ai.ocr_cache import cached_ocr_extract, get_ocr_cache
from src.infrastructure.ai.ocr_service import get_ocr_service, ExtractionMode

async def extract_with_cache():
    # Read file
    with open('document.pdf', 'rb') as f:
        content = f.read()
    
    # Extract with automatic caching
    async def extract_fn():
        ocr = get_ocr_service()
        return await ocr.extract_text_from_file(
            file_bytes=content,
            file_name='document.pdf',
            extract_mode=ExtractionMode.FULL
        )
    
    result = await cached_ocr_extract(
        file_content=content,
        extract_mode='full',
        ocr_function=extract_fn
    )
    
    print(f"From cache: {result.get('from_cache', False)}")
    print(f"Text: {result['text']}")
```

### Cache Management

```python
from src.infrastructure.ai.ocr_cache import get_ocr_cache

async def manage_cache():
    cache = await get_ocr_cache()
    
    # Get statistics
    stats = cache.get_stats()
    print(f"Hit rate: {stats['hit_rate']}")
    print(f"Hits: {stats['hits']}, Misses: {stats['misses']}")
    
    # Clear cache
    deleted = await cache.clear_all()
    print(f"Cleared {deleted} entries")
    
    # Reset stats
    cache.reset_stats()
```

## Extraction Modes Explained

### 1. Full Mode (`full`)
- Extracts all text exactly as it appears
- Maintains original layout and formatting
- Best for: General purpose extraction, archival

**Example output:**
```
INVOICE #12345
Date: 2024-01-20
Amount: $1,250.00
```

### 2. Structured Mode (`structured`)
- Identifies headers, paragraphs, lists
- Adds markdown formatting
- Organizes content logically
- Best for: API documentation, reports

**Example output:**
```
# INVOICE #12345

- **Date**: 2024-01-20
- **Amount**: $1,250.00

## Items
1. Product A - $500
2. Product B - $750
```

### 3. Tables Mode (`tables`)
- Focuses on extracting tables
- Outputs in markdown table format
- Preserves column structure
- Best for: Invoices, data sheets, financial documents

**Example output:**
```
| Item | Quantity | Price |
|------|----------|-------|
| Product A | 2 | $500 |
| Product B | 3 | $750 |
```

## Supported File Types

- **PDF** (.pdf) - Multi-page support
- **Word Documents** (.docx) - Text and tables
- **Images** (.jpg, .jpeg, .png, .bmp, .tiff, .webp, .gif)

**Max file size:** 50MB per file

## Performance Tips

1. **Use Batch Processing**: Process multiple files together for 5x speed improvement
2. **Enable Caching**: Repeated documents will be instant (cache hit)
3. **Choose Right Mode**: Use `full` for speed, `structured` for better organization
4. **Optimize Images**: System auto-optimizes, but pre-compressing helps
5. **Monitor Cache**: Check stats regularly and clear if needed

## Error Handling

### Common Errors

**413 Request Entity Too Large**
```json
{
  "detail": "File too large. Maximum size: 50MB"
}
```
Solution: Split large files or increase `OCR_MAX_FILE_SIZE` setting

**400 Bad Request - Invalid Mode**
```json
{
  "detail": "Invalid extract_mode: fast. Must be: full, structured, or tables"
}
```
Solution: Use one of the three valid modes

**500 Internal Server Error - OCR Failed**
```json
{
  "detail": "OCR extraction failed: Mistral API error: ..."
}
```
Solution: Check Mistral API key, network, and API status

## Configuration

Environment variables (`.env`):
```env
# Mistral API
MISTRAL_API_KEY=your_key_here

# Redis (for caching)
REDIS_URL=redis://localhost:6379

# OCR Settings (optional, defaults shown)
OCR_MAX_FILE_SIZE=52428800  # 50MB
OCR_DPI=200
OCR_CONCURRENT_LIMIT=5
OCR_CACHE_TTL=3600  # 1 hour
OCR_MAX_BATCH_SIZE=10
```

## Testing

### Test with cURL

```bash
# Quick test
curl -X POST "http://localhost:8000/api/ocr/extract" \
  -F "file=@test.pdf" \
  | jq '.processing_time'

# Test cache (run twice)
curl -X POST "http://localhost:8000/api/ocr/extract" \
  -F "file=@test.pdf" \
  | jq '.from_cache'
# First call: false
# Second call: true (instant!)
```

### Test in Browser (Swagger)

1. Visit: http://localhost:8000/docs
2. Find "OCR" section
3. Try `/api/ocr/extract` endpoint
4. Upload a file and click "Execute"
5. See results instantly

## Support

For issues or questions:
1. Check logs: `tail -f backend/logs/app.log`
2. Verify environment variables are set
3. Test with sample files first
4. Check Redis connection if caching issues

---

**🚀 Ready to extract text at lightning speed!**

