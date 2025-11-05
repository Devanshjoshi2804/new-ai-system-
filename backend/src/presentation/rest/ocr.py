"""
OCR API endpoints
Lightning-fast document text extraction using Mistral Pixtral
"""

import logging
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
from fastapi.responses import JSONResponse

from src.infrastructure.ai.ocr_service import get_ocr_service, ExtractionMode
from src.infrastructure.ai.ocr_cache import get_ocr_cache, cached_ocr_extract
from src.presentation.schemas.ocr_schemas import (
    OCRResponse,
    OCRBatchResponse,
    OCRFromURLRequest,
    OCRStatsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint for OCR service
    """
    try:
        # Test OCR service initialization
        ocr_service = get_ocr_service()
        
        # Test cache connection (non-blocking)
        cache_status = "unknown"
        try:
            cache = await get_ocr_cache()
            cache_status = "connected" if cache.cache_enabled else "disabled"
        except Exception as e:
            cache_status = f"error: {str(e)}"
        
        return {
            "status": "healthy",
            "ocr_service": "initialized",
            "cache_status": cache_status,
            "model": ocr_service.model,
            "concurrent_limit": ocr_service.concurrent_limit
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.post("/extract", response_model=OCRResponse)
async def extract_text_from_file(
    file: UploadFile = File(..., description="File to extract text from (PDF, DOCX, or image)"),
    extract_mode: str = Query(
        default="full",
        description="Extraction mode: full (all text), structured (with formatting), or tables (focus on tables)"
    )
):
    """
    Extract text from uploaded file using Mistral Pixtral OCR
    
    **Supported file types:**
    - PDF files (.pdf)
    - Word documents (.docx)
    - Images (.jpg, .jpeg, .png, .bmp, .tiff, .webp, .gif)
    
    **Extraction modes:**
    - `full` - Extract all text as-is, maintain layout
    - `structured` - Extract with headers, paragraphs, lists
    - `tables` - Focus on extracting table data in markdown format
    
    **Returns:**
    - Extracted text (full document)
    - Text per page
    - Processing time
    - Metadata (page count, format, etc.)
    """
    temp_path = None
    
    try:
        # Validate extraction mode
        try:
            mode = ExtractionMode(extract_mode.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid extract_mode: {extract_mode}. Must be: full, structured, or tables"
            )
        
        # Validate file type
        allowed_extensions = {'.pdf', '.docx', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif'}
        file_ext = Path(file.filename).suffix.lower() if file.filename else ''
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file_ext}. Allowed: {allowed_extensions}"
            )
        
        # Read file content
        content = await file.read()
        
        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {max_size // 1024 // 1024}MB"
            )
        
        logger.info(f"[FILE] Processing file: {file.filename} ({len(content) // 1024}KB), mode: {extract_mode}")
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(content)
            temp_path = Path(tmp_file.name)
        
        # Extract with caching
        async def extract_fn():
            ocr_service = get_ocr_service()
            return await ocr_service.extract_text_from_file(
                file_path=temp_path,
                file_name=file.filename,
                extract_mode=mode
            )
        
        result = await cached_ocr_extract(
            file_content=content,
            extract_mode=extract_mode,
            ocr_function=extract_fn
        )
        
        logger.info(f"[OK] Extraction complete: {result['page_count']} pages, {result['processing_time']:.2f}s")
        
        return OCRResponse(
            success=True,
            text=result["text"],
            pages=result["pages"],
            page_count=result["page_count"],
            processing_time=result["processing_time"],
            file_name=result["file_name"],
            metadata=result["metadata"],
            from_cache=result.get("from_cache", False)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] OCR extraction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR extraction failed: {str(e)}"
        )
    
    finally:
        # Cleanup temp file
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@router.post("/extract/batch", response_model=OCRBatchResponse)
async def extract_text_from_multiple_files(
    files: List[UploadFile] = File(..., description="Multiple files to extract text from"),
    extract_mode: str = Query(
        default="full",
        description="Extraction mode: full, structured, or tables"
    )
):
    """
    Extract text from multiple files concurrently
    
    **Features:**
    - Process up to 10 files in parallel
    - 5x faster than sequential processing
    - Individual error handling per file
    - Automatic caching for repeated files
    
    **Maximum:** 10 files per batch
    """
    temp_paths = []
    
    try:
        # Validate extraction mode
        try:
            mode = ExtractionMode(extract_mode.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid extract_mode: {extract_mode}"
            )
        
        # Check batch size
        max_batch_size = 10
        if len(files) > max_batch_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {max_batch_size} files allowed per batch. You provided {len(files)}."
            )
        
        if len(files) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )
        
        logger.info(f"[INFO] Batch processing {len(files)} files, mode: {extract_mode}")
        
        # Save all files temporarily
        file_data = []
        for file in files:
            content = await file.read()
            file_ext = Path(file.filename).suffix.lower() if file.filename else '.pdf'
            
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
            tmp_file.write(content)
            tmp_file.close()
            
            temp_path = Path(tmp_file.name)
            temp_paths.append(temp_path)
            
            file_data.append({
                'path': temp_path,
                'name': file.filename,
                'content': content
            })
        
        # Process batch concurrently
        import time
        start_time = time.time()
        
        ocr_service = get_ocr_service()
        results = await ocr_service.batch_extract(
            files=[{'path': fd['path'], 'name': fd['name']} for fd in file_data],
            extract_mode=mode
        )
        
        total_time = time.time() - start_time
        
        # Count successes and failures
        successful = sum(1 for r in results if r.get('success', False))
        failed = len(results) - successful
        
        logger.info(f"[OK] Batch complete: {successful}/{len(files)} successful in {total_time:.2f}s")
        
        return OCRBatchResponse(
            success=True,
            results=results,
            total_files=len(files),
            total_processing_time=total_time,
            successful_count=successful,
            failed_count=failed
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Batch OCR error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch OCR failed: {str(e)}"
        )
    
    finally:
        # Cleanup all temp files
        for path in temp_paths:
            if path.exists():
                path.unlink(missing_ok=True)


@router.post("/extract/url", response_model=OCRResponse)
async def extract_text_from_url(request: OCRFromURLRequest):
    """
    Download file from URL and extract text
    
    **Use cases:**
    - Process files from cloud storage
    - Webhook integrations
    - Remote document processing
    
    **Example:**
    ```json
    {
        "url": "https://example.com/document.pdf",
        "extract_mode": "structured"
    }
    ```
    """
    import aiohttp
    
    temp_path = None
    
    try:
        # Validate extraction mode
        try:
            mode = ExtractionMode(request.extract_mode.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid extract_mode: {request.extract_mode}"
            )
        
        logger.info(f"[INFO] Downloading file from URL: {request.url}")
        
        # Download file
        async with aiohttp.ClientSession() as session:
            async with session.get(request.url) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to download file. HTTP {response.status}"
                    )
                
                content = await response.read()
        
        # Detect file type from URL or content
        file_ext = Path(request.url).suffix.lower() or '.pdf'
        if not file_ext or file_ext == '.':
            # Try to detect from content
            if content.startswith(b'%PDF'):
                file_ext = '.pdf'
            else:
                file_ext = '.png'
        
        logger.info(f"[OK] Downloaded {len(content) // 1024}KB, detected type: {file_ext}")
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(content)
            temp_path = Path(tmp_file.name)
        
        # Extract with caching
        async def extract_fn():
            ocr_service = get_ocr_service()
            return await ocr_service.extract_text_from_file(
                file_path=temp_path,
                file_name=Path(request.url).name,
                extract_mode=mode
            )
        
        result = await cached_ocr_extract(
            file_content=content,
            extract_mode=request.extract_mode,
            ocr_function=extract_fn
        )
        
        logger.info(f"[OK] URL extraction complete: {result['processing_time']:.2f}s")
        
        return OCRResponse(
            success=True,
            text=result["text"],
            pages=result["pages"],
            page_count=result["page_count"],
            processing_time=result["processing_time"],
            file_name=result["file_name"],
            metadata=result["metadata"],
            from_cache=result.get("from_cache", False)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] URL extraction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"URL extraction failed: {str(e)}"
        )
    
    finally:
        # Cleanup temp file
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@router.get("/stats", response_model=OCRStatsResponse)
async def get_cache_stats():
    """
    Get OCR cache statistics
    
    **Metrics:**
    - Cache hits and misses
    - Hit rate percentage
    - Total requests
    - Cache status
    """
    try:
        cache = await get_ocr_cache()
        stats = cache.get_stats()
        
        return OCRStatsResponse(
            cache_hits=stats["hits"],
            cache_misses=stats["misses"],
            total_requests=stats["total_requests"],
            hit_rate=stats["hit_rate"],
            cache_enabled=stats["cache_enabled"]
        )
    
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {str(e)}"
        )


@router.delete("/cache/clear")
async def clear_cache():
    """
    Clear all OCR cache entries
    
    **Use when:**
    - Testing new OCR configurations
    - Freeing up Redis memory
    - Forcing fresh extractions
    """
    try:
        cache = await get_ocr_cache()
        deleted_count = await cache.clear_all()
        
        return {
            "success": True,
            "message": f"Cleared {deleted_count} cache entries",
            "deleted_count": deleted_count
        }
    
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


