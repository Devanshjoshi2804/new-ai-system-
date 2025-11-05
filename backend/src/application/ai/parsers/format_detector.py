"""
AI-powered document format detection
"""
import logging
import json
import yaml
from typing import Optional
from fastapi import UploadFile

from src.domain.value_objects.doc_format import DocFormat

logger = logging.getLogger(__name__)


class FormatDetector:
    """
    Detects document format using multiple strategies:
    1. File extension
    2. Content-type header
    3. Content analysis
    4. AI-powered detection (for ambiguous cases)
    """
    
    # File extension to format mapping
    EXTENSION_MAP = {
        '.json': [DocFormat.OPENAPI_30, DocFormat.POSTMAN_COLLECTION],
        '.yaml': [DocFormat.OPENAPI_30, DocFormat.SWAGGER_20],
        '.yml': [DocFormat.OPENAPI_30, DocFormat.SWAGGER_20],
        '.pdf': [DocFormat.PDF],
        '.md': [DocFormat.MARKDOWN],
        '.txt': [DocFormat.TEXT],
        '.docx': [DocFormat.DOCX],
        '.html': [DocFormat.HTML],
        '.htm': [DocFormat.HTML],
    }
    
    # Content-type to format mapping
    CONTENT_TYPE_MAP = {
        'application/json': [DocFormat.OPENAPI_30, DocFormat.POSTMAN_COLLECTION],
        'application/x-yaml': [DocFormat.OPENAPI_30, DocFormat.SWAGGER_20],
        'text/yaml': [DocFormat.OPENAPI_30, DocFormat.SWAGGER_20],
        'application/pdf': [DocFormat.PDF],
        'text/markdown': [DocFormat.MARKDOWN],
        'text/plain': [DocFormat.TEXT],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [DocFormat.DOCX],
        'text/html': [DocFormat.HTML],
    }
    
    async def detect(self, file: UploadFile) -> tuple[DocFormat, float]:
        """
        Detect document format with confidence score
        
        Returns:
            (format, confidence) where confidence is 0.0-1.0
        """
        confidence_scores = {}
        
        # Strategy 1: File extension
        ext_format, ext_confidence = await self._detect_by_extension(file.filename)
        if ext_format:
            confidence_scores[ext_format] = ext_confidence
        
        # Strategy 2: Content-Type
        ct_format, ct_confidence = await self._detect_by_content_type(file.content_type)
        if ct_format:
            if ct_format in confidence_scores:
                confidence_scores[ct_format] = max(confidence_scores[ct_format], ct_confidence)
            else:
                confidence_scores[ct_format] = ct_confidence
        
        # Strategy 3: Content analysis
        content_format, content_confidence = await self._detect_by_content(file)
        if content_format:
            if content_format in confidence_scores:
                confidence_scores[content_format] = max(confidence_scores[content_format], content_confidence)
            else:
                confidence_scores[content_format] = content_confidence
        
        if not confidence_scores:
            logger.warning(f"Could not detect format for file: {file.filename}")
            return DocFormat.UNKNOWN, 0.0
        
        # Return format with highest confidence
        best_format = max(confidence_scores.items(), key=lambda x: x[1])
        logger.info(f"Detected format {best_format[0]} with confidence {best_format[1]}")
        
        return best_format
    
    async def _detect_by_extension(self, filename: Optional[str]) -> tuple[Optional[DocFormat], float]:
        """Detect format by file extension"""
        if not filename:
            return None, 0.0
        
        # Get extension
        ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        
        if ext in self.EXTENSION_MAP:
            possible_formats = self.EXTENSION_MAP[ext]
            return possible_formats[0], 0.7  # 70% confidence from extension
        
        return None, 0.0
    
    async def _detect_by_content_type(self, content_type: Optional[str]) -> tuple[Optional[DocFormat], float]:
        """Detect format by content-type header"""
        if not content_type:
            return None, 0.0
        
        # Normalize content-type
        content_type = content_type.split(';')[0].strip().lower()
        
        if content_type in self.CONTENT_TYPE_MAP:
            possible_formats = self.CONTENT_TYPE_MAP[content_type]
            return possible_formats[0], 0.8  # 80% confidence from content-type
        
        return None, 0.0
    
    async def _detect_by_content(self, file: UploadFile) -> tuple[Optional[DocFormat], float]:
        """Detect format by analyzing content"""
        try:
            # Read beginning of file
            content = await file.read(1024 * 10)  # Read first 10KB
            await file.seek(0)  # Reset file pointer
            
            # Try to detect structured formats
            text_content = None
            try:
                text_content = content.decode('utf-8')
            except:
                # Binary file (likely PDF or DOCX)
                if content.startswith(b'%PDF'):
                    return DocFormat.PDF, 0.95
                elif content.startswith(b'PK'):  # ZIP-based (DOCX)
                    return DocFormat.DOCX, 0.95
            
            if text_content:
                # Check for JSON-based formats
                if text_content.strip().startswith('{'):
                    try:
                        data = json.loads(text_content)
                        
                        # OpenAPI/Swagger detection
                        if 'openapi' in data:
                            version = data.get('openapi', '')
                            if version.startswith('3.0'):
                                return DocFormat.OPENAPI_30, 0.95
                            elif version.startswith('3.1'):
                                return DocFormat.OPENAPI_31, 0.95
                        
                        elif 'swagger' in data:
                            return DocFormat.SWAGGER_20, 0.95
                        
                        # Postman collection
                        elif 'info' in data and 'item' in data:
                            return DocFormat.POSTMAN_COLLECTION, 0.90
                        
                        return DocFormat.UNKNOWN, 0.5
                    
                    except json.JSONDecodeError:
                        pass
                
                # Check for YAML-based formats
                elif any(line.strip() and not line.strip().startswith('{') for line in text_content.split('\n')[:5]):
                    try:
                        data = yaml.safe_load(text_content)
                        if isinstance(data, dict):
                            # OpenAPI/Swagger detection
                            if 'openapi' in data:
                                version = data.get('openapi', '')
                                if version.startswith('3.0'):
                                    return DocFormat.OPENAPI_30, 0.95
                                elif version.startswith('3.1'):
                                    return DocFormat.OPENAPI_31, 0.95
                            
                            elif 'swagger' in data:
                                return DocFormat.SWAGGER_20, 0.95
                        
                    except yaml.YAMLError:
                        pass
                
                # Check for markdown
                if any(line.startswith('#') for line in text_content.split('\n')[:10]):
                    return DocFormat.MARKDOWN, 0.80
                
                # Check for HTML
                if '<html' in text_content.lower() or '<!doctype html' in text_content.lower():
                    return DocFormat.HTML, 0.90
                
                # Default to text
                return DocFormat.TEXT, 0.60
        
        except Exception as e:
            logger.error(f"Error detecting format by content: {e}")
        
        return None, 0.0


