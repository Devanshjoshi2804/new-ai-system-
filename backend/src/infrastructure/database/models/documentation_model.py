"""
API Documentation MongoDB model
"""
from typing import Optional, Dict, Any
from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime

from src.domain.value_objects.doc_format import DocFormat
from src.domain.entities.api_documentation import ParsingStatus


class APIDocumentation(Document):
    """API Documentation document model for MongoDB"""
    
    partner_id: Indexed(str)
    tenant_id: Indexed(str)
    
    # File information
    filename: str
    file_path: str
    file_size: int
    content_type: str
    
    # Format detection
    detected_format: DocFormat = DocFormat.UNKNOWN
    format_confidence: float = 0.0
    
    # Parsing status
    parsing_status: ParsingStatus = ParsingStatus.UPLOADED
    parsing_progress: int = 0
    parsing_error: Optional[str] = None
    
    # Extracted information
    extracted_spec: Optional[Dict[str, Any]] = None
    business_workflows: Optional[Dict[str, Any]] = None
    
    # AI analysis
    ai_insights: Optional[Dict[str, Any]] = None
    complexity_score: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    parsing_started_at: Optional[datetime] = None
    parsing_completed_at: Optional[datetime] = None
    
    class Settings:
        name = "api_documentation"
        indexes = [
            "partner_id",
            "tenant_id",
            "parsing_status",
        ]


