"""
Ultra-Fast OCR Service using Mistral Pixtral-12B
Handles: PDF, DOCX, Images with optimization, caching, and batch processing
"""

import base64
import io
import hashlib
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Callable
from enum import Enum
from PIL import Image

from mistralai import Mistral

from src.infrastructure.config.settings import settings
from src.infrastructure.ai.pdf_converter import get_pdf_converter

logger = logging.getLogger(__name__)


class ExtractionMode(str, Enum):
    """OCR extraction modes"""
    FULL = "full"
    STRUCTURED = "structured"
    TABLES = "tables"


class PixtralOCRService:
    """
    Lightning-fast OCR using Mistral Pixtral-12B-2409
    
    Features:
    - Multiple extraction modes (full, structured, tables)
    - Image optimization for faster processing
    - Batch processing with concurrency
    - Progress tracking for multi-page documents
    - Smart caching integration
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OCR service
        
        Args:
            api_key: Mistral API key (defaults to settings.mistral_api_key)
        """
        self.api_key = api_key or settings.mistral_api_key
        if not self.api_key:
            raise ValueError("Mistral API key is required for OCR service")
        
        self.client = Mistral(api_key=self.api_key)
        self.model = "pixtral-12b-2409"
        self.max_image_size = 2048  # Max dimension for images
        self.default_dpi = getattr(settings, 'ocr_dpi', 200)
        self.concurrent_limit = getattr(settings, 'ocr_concurrent_limit', 5)
        self.max_retries = getattr(settings, 'ocr_max_retries', 3)
        self.retry_delay = getattr(settings, 'ocr_retry_delay', 2.0)
        self.batch_delay = getattr(settings, 'ocr_batch_delay', 1.0)
    
    async def extract_text_from_file(
        self,
        file_path: Optional[Union[str, Path]] = None,
        file_bytes: Optional[bytes] = None,
        file_name: Optional[str] = None,
        extract_mode: ExtractionMode = ExtractionMode.FULL
    ) -> Dict[str, any]:
        """
        Main entry point - automatically detects file type and extracts text
        
        Args:
            file_path: Path to file (PDF, DOCX, or image)
            file_bytes: File content as bytes
            file_name: Original filename (for type detection)
            extract_mode: Extraction mode (full, structured, tables)
        
        Returns:
            {
                "text": str,
                "pages": List[str],
                "page_count": int,
                "metadata": dict,
                "processing_time": float,
                "file_name": str
            }
        """
        import time
        start_time = time.time()
        
        try:
            # Determine file type
            if file_path:
                file_path = Path(file_path)
                extension = file_path.suffix.lower()
                name = file_path.name
            elif file_name:
                extension = Path(file_name).suffix.lower()
                name = file_name
            else:
                # Try to detect from bytes
                if file_bytes and file_bytes.startswith(b'%PDF'):
                    extension = '.pdf'
                    name = 'document.pdf'
                else:
                    extension = '.png'
                    name = 'image.png'
            
            logger.info(f"[FILE] Processing file: {name}, mode: {extract_mode}")
            
            # Route to appropriate handler
            if extension == '.pdf':
                result = await self._process_pdf(file_path, file_bytes, extract_mode)
            elif extension == '.docx':
                result = await self._process_docx(file_path, file_bytes, extract_mode)
            elif extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif']:
                result = await self._process_image(file_path, file_bytes, extract_mode)
            else:
                raise ValueError(f"Unsupported file type: {extension}")
            
            processing_time = time.time() - start_time
            result["processing_time"] = processing_time
            result["file_name"] = name
            
            logger.info(f"[OK] Processing complete in {processing_time:.2f}s")
            
            return result
        
        except Exception as e:
            logger.error(f"[ERROR] OCR error: {e}", exc_info=True)
            raise
    
    async def _process_pdf(
        self,
        pdf_path: Optional[Path],
        pdf_bytes: Optional[bytes],
        extract_mode: ExtractionMode
    ) -> Dict[str, any]:
        """
        Convert PDF to images and process with Pixtral
        """
        try:
            # Read PDF bytes if path provided
            if pdf_path and not pdf_bytes:
                def read_file():
                    with open(pdf_path, 'rb') as f:
                        return f.read()
                pdf_bytes = await asyncio.to_thread(read_file)
            
            if not pdf_bytes:
                raise ValueError("PDF content is required")
            
            # Convert PDF to images
            logger.info("[INFO] Converting PDF to images...")
            pdf_converter = get_pdf_converter(dpi=self.default_dpi)
            images = await pdf_converter.convert_pdf_to_images(pdf_bytes)
            
            logger.info(f"[OK] Converted to {len(images)} page(s)")
            
            # Process all pages concurrently (with limit)
            pages_data = await self._process_images_batch(images, extract_mode)
            
            # Combine results
            full_text = "\n\n--- Page Break ---\n\n".join(
                [p["text"] for p in pages_data]
            )
            
            return {
                "text": full_text,
                "pages": [p["text"] for p in pages_data],
                "page_count": len(images),
                "metadata": {
                    "total_pages": len(images),
                    "extraction_mode": extract_mode,
                    "format": "pdf"
                }
            }
        
        except Exception as e:
            logger.error(f"[ERROR] PDF processing error: {e}")
            raise
    
    async def _process_docx(
        self,
        docx_path: Optional[Path],
        docx_bytes: Optional[bytes],
        extract_mode: ExtractionMode
    ) -> Dict[str, any]:
        """
        Process DOCX file (simplified text extraction for now)
        """
        try:
            from docx import Document
            
            # Read DOCX
            if docx_path:
                doc = Document(docx_path)
            else:
                from io import BytesIO
                doc = Document(BytesIO(docx_bytes))
            
            # Extract text
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            text = "\n\n".join(paragraphs)
            
            # Extract tables if present
            tables_text = []
            if doc.tables and extract_mode == ExtractionMode.TABLES:
                for table in doc.tables:
                    table_text = self._extract_table_from_docx(table)
                    tables_text.append(table_text)
            
            if tables_text:
                text += "\n\n" + "\n\n".join(tables_text)
            
            return {
                "text": text,
                "pages": [text],
                "page_count": 1,
                "metadata": {
                    "extraction_method": "docx_text_extraction",
                    "paragraphs": len(paragraphs),
                    "tables": len(doc.tables),
                    "format": "docx"
                }
            }
        
        except Exception as e:
            logger.error(f"[ERROR] DOCX processing error: {e}")
            raise
    
    async def _process_image(
        self,
        image_path: Optional[Path],
        image_bytes: Optional[bytes],
        extract_mode: ExtractionMode
    ) -> Dict[str, any]:
        """
        Process single image file
        """
        try:
            # Load image
            if image_path:
                image = Image.open(image_path)
            else:
                image = Image.open(io.BytesIO(image_bytes))
            
            # Process with Pixtral
            result = await self._extract_from_image(image, extract_mode)
            
            return {
                "text": result["text"],
                "pages": [result["text"]],
                "page_count": 1,
                "metadata": {
                    "image_size": image.size,
                    "format": image.format or "image",
                    "extraction_mode": extract_mode
                }
            }
        
        except Exception as e:
            logger.error(f"[ERROR] Image processing error: {e}")
            raise
    
    async def _process_images_batch(
        self,
        base64_images: List[str],
        extract_mode: ExtractionMode,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, any]]:
        """
        Process multiple images concurrently with rate limiting and retry logic
        """
        total = len(base64_images)
        results = []
        
        # Process in batches to respect concurrent limit
        for i in range(0, total, self.concurrent_limit):
            batch = base64_images[i:i + self.concurrent_limit]
            batch_num = i // self.concurrent_limit + 1
            total_batches = (total + self.concurrent_limit - 1) // self.concurrent_limit
            
            logger.info(f"[INFO] Processing batch {batch_num}/{total_batches} ({len(batch)} pages)")
            
            # Process batch concurrently
            tasks = [
                self._extract_from_base64_image_with_retry(img, extract_mode, page_num=i+j+1)
                for j, img in enumerate(batch)
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results and errors
            for j, result in enumerate(batch_results):
                page_num = i + j + 1
                if isinstance(result, Exception):
                    logger.error(f"[ERROR] Error on page {page_num} after all retries: {result}")
                    results.append({
                        "text": f"[Error extracting page {page_num}]",
                        "page_num": page_num,
                        "error": str(result)
                    })
                else:
                    results.append(result)
                
                # Progress callback
                if progress_callback:
                    await progress_callback(page_num, total)
            
            # Add delay between batches to avoid rate limiting (except for last batch)
            if i + self.concurrent_limit < total:
                logger.debug(f"⏳ Waiting {self.batch_delay}s before next batch...")
                await asyncio.sleep(self.batch_delay)
        
        return results
    
    async def _extract_from_image(
        self,
        image: Image.Image,
        extract_mode: ExtractionMode,
        page_num: int = 1
    ) -> Dict[str, any]:
        """
        Core OCR function using Pixtral API - from PIL Image
        """
        # Optimize image
        image = self._optimize_image(image)
        
        # Convert to base64
        base64_image = self._image_to_base64(image)
        
        # Extract
        return await self._extract_from_base64_image(base64_image, extract_mode, page_num)
    
    async def _extract_from_base64_image_with_retry(
        self,
        base64_image: str,
        extract_mode: ExtractionMode,
        page_num: int = 1
    ) -> Dict[str, any]:
        """
        Core OCR function with retry logic for handling API failures
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    delay = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"[INFO] Retry {attempt}/{self.max_retries - 1} for page {page_num} after {delay}s...")
                    await asyncio.sleep(delay)
                
                return await self._extract_from_base64_image(base64_image, extract_mode, page_num)
            
            except Exception as e:
                last_error = e
                error_msg = str(e)
                
                # Check if it's a rate limit error
                if "rate" in error_msg.lower() or "429" in error_msg:
                    logger.warning(f"[WARN] Rate limit hit on page {page_num}, attempt {attempt + 1}/{self.max_retries}")
                elif "timeout" in error_msg.lower():
                    logger.warning(f"[WARN] Timeout on page {page_num}, attempt {attempt + 1}/{self.max_retries}")
                else:
                    logger.warning(f"[WARN] Error on page {page_num}, attempt {attempt + 1}/{self.max_retries}: {error_msg}")
                
                # Don't retry on last attempt
                if attempt == self.max_retries - 1:
                    raise last_error
        
        # Should never reach here, but just in case
        raise last_error or Exception(f"Failed to extract page {page_num} after {self.max_retries} attempts")
    
    async def _extract_from_base64_image(
        self,
        base64_image: str,
        extract_mode: ExtractionMode,
        page_num: int = 1
    ) -> Dict[str, any]:
        """
        Core OCR function using Pixtral API - from base64 string
        """
        # Create prompt based on extraction mode
        prompt = self._get_extraction_prompt(extract_mode)
        
        # Call Pixtral API
        response_text = await self._call_pixtral_api(base64_image, prompt)
        
        return {
            "text": response_text,
            "page_num": page_num
        }
    
    def _optimize_image(self, image: Image.Image) -> Image.Image:
        """
        Optimize image size for faster API processing
        """
        # Resize if too large
        if max(image.size) > self.max_image_size:
            ratio = self.max_image_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.debug(f"[INFO] Resized image to {new_size}")
        
        # Convert to RGB if needed (removes alpha channel)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        
        return image
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """
        Convert PIL Image to base64 data URI string
        """
        buffered = io.BytesIO()
        # Use JPEG for better compression, PNG for images with text
        image.save(buffered, format="JPEG", quality=85, optimize=True)
        img_bytes = buffered.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{img_base64}"
    
    def _get_extraction_prompt(self, extract_mode: ExtractionMode) -> str:
        """
        Get appropriate prompt based on extraction mode
        """
        prompts = {
            ExtractionMode.FULL: """
Extract ALL text from this image exactly as it appears.
Maintain the original layout and formatting as much as possible.
Include all text, numbers, labels, and captions.
If there are multiple columns, read left to right, top to bottom.
""",
            ExtractionMode.STRUCTURED: """
Extract text from this image and organize it with clear structure:
- Identify headers and subheaders (mark with # or ##)
- Separate paragraphs clearly
- Identify lists (bullet points or numbered)
- Note any special formatting (bold, italics)
Maintain logical document structure.
""",
            ExtractionMode.TABLES: """
Focus on extracting data from tables in this image:
- Identify all tables
- Extract table data in markdown format
- Preserve column headers and row structure
- If there's text outside tables, include it but prioritize table data
"""
        }
        return prompts.get(extract_mode, prompts[ExtractionMode.FULL])
    
    async def _call_pixtral_api(self, base64_image: str, prompt: str) -> str:
        """
        Call Mistral Pixtral API (async wrapper) with detailed error handling
        """
        try:
            def make_request():
                chat_response = self.client.chat.complete(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": base64_image
                                }
                            ]
                        }
                    ],
                    max_tokens=2000
                )
                return chat_response.choices[0].message.content
            
            # Run in thread to avoid blocking
            return await asyncio.to_thread(make_request)
        
        except Exception as e:
            error_msg = str(e)
            
            # Provide more specific error messages
            if "rate" in error_msg.lower() or "429" in error_msg:
                logger.error(f"[ERROR] Pixtral API rate limit exceeded: {e}")
                raise Exception(f"Rate limit exceeded. Please try again later.")
            elif "timeout" in error_msg.lower():
                logger.error(f"[ERROR] Pixtral API timeout: {e}")
                raise Exception(f"API request timed out. Please try again.")
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                logger.error(f"[ERROR] Pixtral API authentication error: {e}")
                raise Exception(f"API authentication failed. Check your API key.")
            elif "400" in error_msg or "bad request" in error_msg.lower():
                logger.error(f"[ERROR] Pixtral API bad request: {e}")
                raise Exception(f"Invalid request to API. Image may be corrupted.")
            else:
                logger.error(f"[ERROR] Pixtral API error: {e}")
                raise Exception(f"Pixtral API error: {error_msg}")
    
    async def batch_extract(
        self,
        files: List[Dict[str, any]],
        extract_mode: ExtractionMode = ExtractionMode.FULL
    ) -> List[Dict[str, any]]:
        """
        Process multiple files concurrently (SUPER FAST!)
        
        Args:
            files: List of dicts with 'path', 'bytes', or 'name' keys
            extract_mode: Extraction mode to use
        
        Returns:
            List of extraction results
        """
        tasks = [
            self.extract_text_from_file(
                file_path=f.get('path'),
                file_bytes=f.get('bytes'),
                file_name=f.get('name'),
                extract_mode=extract_mode
            )
            for f in files
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error dicts
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "file_name": files[i].get('name', f'file_{i}')
                })
            else:
                result["success"] = True
                processed_results.append(result)
        
        return processed_results
    
    def _extract_table_from_docx(self, table) -> str:
        """
        Extract table from DOCX in markdown format
        """
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append("| " + " | ".join(cells) + " |")
        
        if rows:
            # Add separator after header
            header_sep = "|" + "|".join(["---" for _ in table.rows[0].cells]) + "|"
            return rows[0] + "\n" + header_sep + "\n" + "\n".join(rows[1:])
        
        return ""
    
    @staticmethod
    def calculate_file_hash(content: bytes) -> str:
        """
        Calculate MD5 hash of file content for caching
        
        Args:
            content: File content as bytes
        
        Returns:
            MD5 hash hex string
        """
        return hashlib.md5(content).hexdigest()


# Singleton instance
_ocr_service: Optional[PixtralOCRService] = None


def get_ocr_service() -> PixtralOCRService:
    """
    Get or create singleton OCR service instance
    
    Returns:
        PixtralOCRService instance
    """
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = PixtralOCRService()
    return _ocr_service


