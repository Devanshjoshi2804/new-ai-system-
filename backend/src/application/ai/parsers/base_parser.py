"""
Base parser interface for documentation parsing
"""
from abc import ABC, abstractmethod
from typing import Optional
from fastapi import UploadFile

from src.domain.value_objects.api_schema import APISpecification
from src.domain.value_objects.doc_format import DocFormat


class BaseParser(ABC):
    """Base interface for documentation parsers"""
    
    @property
    @abstractmethod
    def supported_formats(self) -> list[DocFormat]:
        """List of supported document formats"""
        pass
    
    @abstractmethod
    async def can_parse(self, file: UploadFile) -> bool:
        """Check if this parser can handle the given file"""
        pass
    
    @abstractmethod
    async def parse(self, file: UploadFile) -> APISpecification:
        """
        Parse documentation and extract API specification
        
        Args:
            file: Uploaded documentation file
            
        Returns:
            APISpecification object with extracted information
            
        Raises:
            ValueError: If file cannot be parsed
        """
        pass
    
    @abstractmethod
    async def detect_format(self, file: UploadFile) -> tuple[DocFormat, float]:
        """
        Detect document format and return confidence score
        
        Returns:
            (DocFormat, confidence) where confidence is 0.0-1.0
        """
        pass
    
    async def extract_text(self, file: UploadFile) -> str:
        """
        Extract raw text from document
        Default implementation reads file content as text
        """
        content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            # Try with different encoding
            return content.decode('latin-1', errors='ignore')


