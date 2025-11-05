"""
Document format enumeration
"""
from enum import Enum


class DocFormat(str, Enum):
    """Supported documentation formats"""
    
    # Structured formats
    OPENAPI_30 = "openapi_3.0"
    OPENAPI_31 = "openapi_3.1"
    SWAGGER_20 = "swagger_2.0"
    POSTMAN_COLLECTION = "postman_collection"
    
    # Unstructured formats
    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"
    DOCX = "docx"
    HTML = "html"
    
    # Unknown/Auto-detect
    UNKNOWN = "unknown"
    
    @classmethod
    def is_structured(cls, format_type: 'DocFormat') -> bool:
        """Check if format is structured"""
        return format_type in [
            cls.OPENAPI_30,
            cls.OPENAPI_31,
            cls.SWAGGER_20,
            cls.POSTMAN_COLLECTION
        ]
    
    @classmethod
    def is_unstructured(cls, format_type: 'DocFormat') -> bool:
        """Check if format is unstructured"""
        return format_type in [
            cls.PDF,
            cls.MARKDOWN,
            cls.TEXT,
            cls.DOCX,
            cls.HTML
        ]


