"""
Test AI parsers
"""
import pytest
from src.application.ai.parsers.pdf_parser import PDFParser
from src.application.ai.parsers.format_detector import FormatDetector
from src.application.ai.parsers.multi_parser import MultiParser


class TestPDFParser:
    """Test PDF parser"""
    
    @pytest.mark.asyncio
    async def test_pdf_parser_exists(self):
        """Test that PDF parser can be instantiated"""
        parser = PDFParser()
        assert parser is not None
        assert hasattr(parser, 'supported_formats')


class TestMultiParser:
    """Test Multi parser"""
    
    @pytest.mark.asyncio
    async def test_multi_parser_exists(self):
        """Test that multi parser can be instantiated"""
        parser = MultiParser()
        assert parser is not None
        assert hasattr(parser, 'supported_formats')


class TestFormatDetector:
    """Test format detection"""
    
    @pytest.mark.asyncio
    async def test_detect_pdf_format(self):
        """Test detecting PDF format"""
        detector = FormatDetector()
        
        class MockFile:
            filename = "api.pdf"
            content_type = "application/pdf"
            
            async def read(self, size=None):
                return b'%PDF-1.4'
            
            async def seek(self, pos):
                pass
        
        file = MockFile()
        format_result, confidence = await detector.detect(file)
        
        assert format_result is not None
        assert confidence > 0

