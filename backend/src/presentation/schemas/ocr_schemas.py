"""
Pydantic schemas for OCR API endpoints
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class OCRRequest(BaseModel):
    """Single file OCR request"""
    extract_mode: Optional[str] = Field(
        default="full",
        description="Extraction mode: full, structured, or tables"
    )


class OCRResponse(BaseModel):
    """OCR extraction response"""
    success: bool = Field(description="Whether extraction was successful")
    text: str = Field(description="Extracted text content")
    pages: List[str] = Field(description="Text content per page")
    page_count: int = Field(description="Number of pages processed")
    processing_time: float = Field(description="Processing time in seconds")
    file_name: str = Field(description="Original filename")
    metadata: Dict[str, Any] = Field(description="Additional metadata")
    from_cache: Optional[bool] = Field(
        default=False,
        description="Whether result was from cache"
    )


class OCRBatchResponse(BaseModel):
    """Batch OCR response"""
    success: bool = Field(description="Whether batch processing was successful")
    results: List[Dict[str, Any]] = Field(description="Results for each file")
    total_files: int = Field(description="Total number of files processed")
    total_processing_time: float = Field(description="Total processing time in seconds")
    successful_count: int = Field(description="Number of successfully processed files")
    failed_count: int = Field(description="Number of failed files")


class OCRFromURLRequest(BaseModel):
    """Extract OCR from URL request"""
    url: str = Field(description="URL to download file from")
    extract_mode: Optional[str] = Field(
        default="full",
        description="Extraction mode: full, structured, or tables"
    )


class OCRStatsResponse(BaseModel):
    """OCR cache statistics response"""
    cache_hits: int = Field(description="Number of cache hits")
    cache_misses: int = Field(description="Number of cache misses")
    total_requests: int = Field(description="Total cache requests")
    hit_rate: str = Field(description="Cache hit rate percentage")
    cache_enabled: bool = Field(description="Whether caching is enabled")


