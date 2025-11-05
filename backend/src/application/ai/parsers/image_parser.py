"""
Image parser using Ultra-Fast OCR Service for screenshots and diagrams
"""
import logging
from typing import Optional
from fastapi import UploadFile
import tempfile
import os

from src.application.ai.parsers.base_parser import BaseParser
from src.domain.value_objects.doc_format import DocFormat
from src.domain.value_objects.api_schema import APISpecification
from src.infrastructure.ai.ocr_service import get_ocr_service, ExtractionMode
from src.infrastructure.ai.providers.mistral_provider import MistralProvider

logger = logging.getLogger(__name__)


class ImageParser(BaseParser):
    """
    Parse API documentation from images (screenshots, diagrams)
    using Ultra-Fast OCR Service
    """
    
    def __init__(self):
        self.ocr_service = get_ocr_service()
        self.mistral = MistralProvider()  # Keep for structured extraction
    
    @property
    def supported_formats(self) -> list[DocFormat]:
        return [DocFormat.PDF]  # Mistral OCR handles images via PDF format
    
    async def can_parse(self, file: UploadFile) -> bool:
        """Check if file is an image"""
        image_types = [
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/webp",
            "image/gif"
        ]
        
        if file.content_type in image_types:
            return True
        
        if file.filename:
            ext = file.filename.lower().split('.')[-1]
            return ext in ['png', 'jpg', 'jpeg', 'webp', 'gif']
        
        return False
    
    async def detect_format(self, file: UploadFile) -> tuple[DocFormat, float]:
        """Detect image format"""
        if await self.can_parse(file):
            return DocFormat.PDF, 0.85  # Using PDF parser for images
        return DocFormat.UNKNOWN, 0.0
    
    async def parse(self, file: UploadFile) -> APISpecification:
        """
        Parse API documentation from image using Ultra-Fast OCR Service
        """
        try:
            logger.info(f"[INFO] Parsing image: {file.filename}")
            
            # Read file content
            content = await file.read()
            await file.seek(0)
            
            # Determine file extension
            ext = '.png'
            if file.filename:
                ext = '.' + file.filename.split('.')[-1].lower()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            try:
                # Step 1: Extract text from image using OCR service
                logger.info("[INFO] Extracting text from image with OCR service...")
                
                ocr_result = await self.ocr_service.extract_text_from_file(
                    file_path=tmp_path,
                    file_name=file.filename,
                    extract_mode=ExtractionMode.STRUCTURED
                )
                
                document_text = ocr_result["text"]
                logger.info(f"[OK] Extracted {len(document_text)} characters in {ocr_result['processing_time']:.2f}s")
                
                # Step 2: Extract structured API data using AI
                logger.info("[AI] Extracting API specification with AI...")
                
                extraction_prompt = f"""
                This text was extracted from an API documentation image. Please extract the following and provide as JSON:
                1. API endpoints (methods and paths)
                2. Parameters and their types
                3. Response formats
                4. Authentication details
                5. Any URLs or base paths
                
                Output format:
                {{
                  "title": "API Name",
                  "version": "1.0.0",
                  "description": "Description",
                  "base_url": "https://api.example.com",
                  "endpoints": [...],
                  "schemas": {{...}}
                }}
                
                Text content:
                {document_text}
                """
                
                # Use text generation with the extracted text instead of processing image again
                import json
                response_text = await self.mistral.generate_content(
                    prompt=extraction_prompt,
                    model="mistral-large-latest",
                    temperature=0.1
                )
                
                # Parse JSON from response
                text = response_text.strip()
                if "```json" in text:
                    json_start = text.find("```json") + 7
                    json_end = text.find("```", json_start)
                    text = text[json_start:json_end].strip()
                elif "```" in text:
                    json_start = text.find("```") + 3
                    json_end = text.find("```", json_start)
                    text = text[json_start:json_end].strip()
                
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON, using defaults")
                    data = {}
                
                # Convert to APISpecification (simplified)
                return APISpecification(
                    title=data.get("title", "API from Image"),
                    version=data.get("version", "1.0.0"),
                    description=data.get("description", "Extracted from image documentation"),
                    base_url=data.get("base_url", "https://api.example.com"),
                    endpoints=[],
                    schemas=data.get("schemas", {})
                )
            
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        except Exception as e:
            logger.error(f"[ERROR] Error parsing image: {e}")
            raise ValueError(f"Failed to parse image: {str(e)}")


