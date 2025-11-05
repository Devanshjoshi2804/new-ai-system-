# 🔍 OCR Viewer - User Guide

## Overview

The OCR Viewer is a new frontend feature that allows you to test and visualize the Ultra-Fast OCR extraction capabilities. You can upload documents and see the extracted text in real-time.

## Access

Navigate to: **http://localhost:3000/ocr**

Or click the "Test OCR Viewer ✨" button from:
- Activation step after onboarding
- Dashboard header ("OCR Viewer" button)

## Features

### 📤 File Upload
- **Supported Formats**: PDF, PNG, JPG, JPEG, WEBP, GIF, DOCX
- **Drag & Drop**: Simply click the upload area to select a file
- **File Info**: See file name and size after selection

### ⚙️ Extraction Modes

1. **Full Text** - Extract all text as-is, maintaining layout
2. **Structured** - Extract with headers, paragraphs, and lists organized
3. **Tables** - Focus on extracting table data in markdown format

### 📊 Results Display

#### Metadata Panel (Left Side)
- **File Name**: Original uploaded file name
- **Pages**: Total number of pages extracted
- **Processing Time**: How long the OCR took (in seconds)
- **Characters**: Total character count extracted
- **Cache Status**: Shows if result was served from cache (faster!)
- **Format**: Detected document format

#### Text Viewer (Right Side)
- **Page Navigation**: For multi-page documents, switch between individual pages
- **All Pages View**: See the complete extracted text from all pages
- **Copy Button**: One-click copy to clipboard
- **Formatted Display**: Monospace font with preserved formatting

## How to Use

1. **Upload a Document**
   ```
   Click the upload area → Select a file (PDF, image, etc.)
   ```

2. **Choose Extraction Mode**
   ```
   Select: Full Text | Structured | Tables
   ```

3. **Extract Text**
   ```
   Click the "Extract Text" button
   Wait for processing (usually < 2 seconds per page)
   ```

4. **View Results**
   ```
   Browse pages using the page selector
   Copy text using the "Copy" button
   Check metadata for processing info
   ```

## Performance Benefits

### ⚡ Ultra-Fast Processing
- Average: **< 1 second per page**
- Multi-page PDFs processed concurrently
- Up to 5 pages processed simultaneously

### 💾 Smart Caching
- Identical files cached for 1 hour
- Cache hits return instantly
- Hash-based cache keys (MD5)

### 📈 Real-time Stats
- See processing time for each extraction
- Track cache effectiveness
- Monitor character counts

## Use Cases

### 1. **Test Document Extraction**
Upload sample documents to test OCR accuracy and speed

### 2. **Debug API Documentation**
Extract text from PDF API docs to verify parsing quality

### 3. **Batch Processing**
Upload multiple pages and see concurrent processing in action

### 4. **Quality Assurance**
Compare different extraction modes to find the best fit

## Backend Integration

The OCR Viewer uses the following backend endpoints:

- `POST /api/ocr/extract` - Single file extraction
- `POST /api/ocr/extract/batch` - Batch file processing
- `POST /api/ocr/extract/url` - Extract from URL
- `GET /api/ocr/stats` - Cache statistics
- `DELETE /api/ocr/cache/clear` - Clear cache

## Tips & Tricks

### 🎯 Best Results
- Use high-resolution images (200 DPI or higher)
- Ensure text is clear and readable
- For tables, use "Tables" extraction mode

### 🚀 Performance
- Files are cached automatically
- Re-uploading the same file is instant
- Processing is done concurrently for PDFs

### 🛠️ Troubleshooting

**Problem**: "Rate limit exceeded"
- **Solution**: Wait 60 seconds (Mistral API rate limit)

**Problem**: Poppler error on Windows
- **Solution**: Ensure `poppler-24.08.0/` is in project root

**Problem**: Low accuracy
- **Solution**: Try different extraction modes or increase image quality

## Example Workflow

```bash
# 1. Start the frontend
cd frontend
npm run dev

# 2. Navigate to OCR Viewer
http://localhost:3000/ocr

# 3. Upload a PDF document
# 4. Select "Structured" mode
# 5. Click "Extract Text"
# 6. Browse pages and copy text
```

## Frontend Code

The OCR Viewer is located at:
```
frontend/src/features/ocr/components/OCRViewer.tsx
```

It uses the vision API client:
```
frontend/src/lib/api/vision.ts
```

## What's Next?

Future enhancements:
- [ ] Side-by-side view (original PDF + extracted text)
- [ ] Highlight extraction regions
- [ ] Download extracted text as file
- [ ] Batch upload with queue
- [ ] Real-time preview while typing
- [ ] Comparison between extraction modes
- [ ] Export to various formats (TXT, MD, JSON)

## Related Documentation

- [Ultra-Fast OCR Implementation Plan](../ultra-fast-ocr-implementation.plan.md)
- [OCR Service Documentation](../backend/docs/OCR_IMPLEMENTATION_SUMMARY.md)
- [Mistral OCR Fix](../backend/docs/MISTRAL_OCR_FIX.md)

---

**Note**: The OCR Viewer is a development/testing tool. For production use, the OCR service is automatically used during the onboarding flow when parsing API documentation.

