"""
PDF to Image Converter for OCR Processing

Converts PDF pages to high-quality PNG images for better OCR results with Mistral Vision API.
"""
from __future__ import annotations  # Enable postponed annotation evaluation
import base64
import io
import os
import sys
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
import logging

try:
    from pdf2image import convert_from_bytes, pdfinfo_from_bytes
    from PIL import Image
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    Image = None  # Define Image as None when not available
    logging.warning("pdf2image not installed. Install with: pip install pdf2image pillow")

logger = logging.getLogger(__name__)


def get_poppler_path() -> Optional[str]:
    """
    Get poppler path for Windows
    Looks in project directory first, then system PATH
    """
    if sys.platform == 'win32':
        # Check project directory for poppler
        project_root = Path(__file__).parent.parent.parent.parent.parent  # Go up to project root
        
        # Common poppler locations in project
        possible_paths = [
            project_root / "poppler-24.08.0" / "Library" / "bin",
            project_root / "poppler" / "Library" / "bin",
            project_root / "poppler-24.08.0" / "bin",
            project_root / "poppler" / "bin",
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"[OK] Found poppler at: {path}")
                return str(path)
        
        logger.warning("[WARN] Poppler not found in project directory. Assuming it's in system PATH.")
    
    return None


class PDFToImageConverter:
    """Convert PDF pages to images for OCR processing"""
    
    def __init__(self, default_dpi: int = 200):
        """
        Initialize PDF converter
        
        Args:
            default_dpi: Default resolution for conversion (higher = better quality, larger size)
                        200 DPI is good balance between quality and performance
        """
        if not PDF_SUPPORT:
            raise ImportError(
                "pdf2image and Pillow required for PDF conversion. "
                "Install with: pip install pdf2image pillow"
            )
        self.default_dpi = default_dpi
        self.poppler_path = get_poppler_path()
        
        if self.poppler_path:
            logger.info(f"[FIX] Using poppler from: {self.poppler_path}")
        else:
            logger.info("[FIX] Using poppler from system PATH")
    
    async def convert_pdf_to_images(
        self, 
        pdf_bytes: bytes, 
        dpi: int = None,
        first_page: int = None,
        last_page: int = None
    ) -> List[str]:
        """
        Convert PDF to list of base64 PNG images
        
        Args:
            pdf_bytes: PDF file as bytes
            dpi: Resolution for conversion (default: 200)
            first_page: First page to convert (1-indexed)
            last_page: Last page to convert (1-indexed)
            
        Returns:
            List of base64 encoded PNG images (data:image/png;base64,...)
        """
        try:
            dpi = dpi or self.default_dpi
            logger.info(f"[INFO] Converting PDF to images at {dpi} DPI")
            
            # Convert PDF to PIL Images
            kwargs = {"dpi": dpi}
            if first_page:
                kwargs["first_page"] = first_page
            if last_page:
                kwargs["last_page"] = last_page
            
            # Add poppler path for Windows
            if self.poppler_path:
                kwargs["poppler_path"] = self.poppler_path
            
            images = convert_from_bytes(pdf_bytes, **kwargs)
            
            logger.info(f"[OK] Converted PDF to {len(images)} page(s)")
            
            # Convert each image to base64
            base64_images = []
            for i, img in enumerate(images):
                base64_img = await self._image_to_base64(img)
                base64_images.append(base64_img)
                
                # Calculate size for logging
                img_size_kb = len(base64_img.split(',')[1]) * 3 // 4 // 1024
                logger.info(f"[OK] Page {i+1} converted to PNG ({img_size_kb} KB)")
            
            return base64_images
            
        except Exception as e:
            logger.error(f"[ERROR] PDF conversion error: {e}", exc_info=True)
            raise Exception(f"Failed to convert PDF: {str(e)}")
    
    async def convert_single_page(
        self, 
        pdf_bytes: bytes, 
        page_num: int = 1, 
        dpi: int = None
    ) -> str:
        """
        Convert single PDF page to base64 image
        
        Args:
            pdf_bytes: PDF file as bytes
            page_num: Page number (1-indexed)
            dpi: Resolution
            
        Returns:
            Base64 encoded PNG image (data:image/png;base64,...)
        """
        images = await self.convert_pdf_to_images(
            pdf_bytes, 
            dpi=dpi,
            first_page=page_num,
            last_page=page_num
        )
        if not images:
            raise ValueError(f"Failed to convert page {page_num}")
        return images[0]
    
    async def get_page_count(self, pdf_bytes: bytes) -> int:
        """
        Get number of pages in PDF
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            Number of pages
        """
        try:
            # Quick conversion of just first page to get count
            # pdf2image will tell us the total page count
            from pdf2image.pdf2image import pdfinfo_from_bytes
            
            # Pass poppler_path for Windows
            if self.poppler_path:
                info = pdfinfo_from_bytes(pdf_bytes, poppler_path=self.poppler_path)
            else:
                info = pdfinfo_from_bytes(pdf_bytes)
            
            return info.get('Pages', 0)
        except Exception as e:
            logger.warning(f"[WARN] Could not get page count via pdfinfo: {e}")
            # Fallback: convert all pages
            images = await self.convert_pdf_to_images(pdf_bytes, dpi=72)  # Low DPI for speed
            return len(images)
    
    @staticmethod
    async def _image_to_base64(img: Image.Image, format: str = 'PNG') -> str:
        """
        Convert PIL Image to base64 data URI
        
        Args:
            img: PIL Image
            format: Image format (PNG, JPEG, etc.)
            
        Returns:
            Base64 data URI (data:image/png;base64,...)
        """
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        
        # Optimize for file size while maintaining quality
        if format.upper() == 'PNG':
            img.save(img_byte_arr, format='PNG', optimize=True)
            mime_type = 'image/png'
        elif format.upper() in ['JPG', 'JPEG']:
            img.save(img_byte_arr, format='JPEG', quality=90, optimize=True)
            mime_type = 'image/jpeg'
        else:
            img.save(img_byte_arr, format=format)
            mime_type = f'image/{format.lower()}'
        
        img_bytes = img_byte_arr.getvalue()
        
        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        data_uri = f"data:{mime_type};base64,{img_base64}"
        
        return data_uri
    
    async def convert_pdf_to_images_batch(
        self,
        pdf_bytes: bytes,
        batch_size: int = 3,
        max_pages: int = None,
        dpi: int = None
    ) -> List[List[str]]:
        """
        Convert PDF to images in batches (useful for large PDFs)
        
        Args:
            pdf_bytes: PDF file as bytes
            batch_size: Number of pages per batch
            max_pages: Maximum pages to process
            dpi: Resolution
            
        Returns:
            List of batches, each batch is a list of base64 images
        """
        # Get all images
        images = await self.convert_pdf_to_images(pdf_bytes, dpi=dpi)
        
        if max_pages:
            images = images[:max_pages]
        
        # Split into batches
        batches = []
        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]
            batches.append(batch)
        
        logger.info(f"[INFO] Split {len(images)} pages into {len(batches)} batches")
        return batches


def get_pdf_converter(dpi: int = 200) -> PDFToImageConverter:
    """
    Get PDF converter instance
    
    Args:
        dpi: Default DPI for conversions
        
    Returns:
        PDFToImageConverter instance
    """
    return PDFToImageConverter(default_dpi=dpi)


# For backwards compatibility
async def convert_pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> List[str]:
    """
    Utility function to convert PDF to images
    
    Args:
        pdf_bytes: PDF file as bytes
        dpi: Resolution
        
    Returns:
        List of base64 encoded images
    """
    converter = get_pdf_converter(dpi=dpi)
    return await converter.convert_pdf_to_images(pdf_bytes, dpi=dpi)


