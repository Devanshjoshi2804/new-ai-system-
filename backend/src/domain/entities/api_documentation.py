"""
API Documentation domain entity
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid

from src.domain.value_objects.doc_format import DocFormat


class ParsingStatus(str, Enum):
    """Documentation parsing status"""
    UPLOADED = "uploaded"
    DETECTING_FORMAT = "detecting_format"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class APIDocumentation(BaseModel):
    """API Documentation entity"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    partner_id: str
    tenant_id: str
    
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
    parsing_progress: int = 0  # 0-100
    parsing_error: Optional[str] = None
    
    # Extracted information
    extracted_spec: Optional[Dict[str, Any]] = None  # APISpecification as dict
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "partner_id": "uuid-here",
                "tenant_id": "tenant-uuid",
                "filename": "api-documentation.pdf",
                "file_path": "/uploads/api-docs/file.pdf",
                "file_size": 1024000,
                "content_type": "application/pdf"
            }
        }
    
    def start_parsing(self):
        """Mark parsing as started"""
        self.parsing_status = ParsingStatus.PARSING
        self.parsing_started_at = datetime.utcnow()
        self.parsing_progress = 10
    
    def update_progress(self, progress: int, status: Optional[ParsingStatus] = None):
        """Update parsing progress"""
        self.parsing_progress = min(100, max(0, progress))
        if status:
            self.parsing_status = status
    
    def complete_parsing(self, extracted_spec: Dict[str, Any], workflows: Optional[Dict[str, Any]] = None):
        """Mark parsing as completed"""
        self.parsing_status = ParsingStatus.COMPLETED
        self.parsing_progress = 100
        self.parsing_completed_at = datetime.utcnow()
        self.extracted_spec = extracted_spec
        self.business_workflows = workflows
    
    def fail_parsing(self, error: str):
        """Mark parsing as failed"""
        self.parsing_status = ParsingStatus.FAILED
        self.parsing_error = error
    
    def is_completed(self) -> bool:
        """Check if parsing is completed"""
        return self.parsing_status == ParsingStatus.COMPLETED
    
    def is_structured_format(self) -> bool:
        """Check if document is in structured format"""
        return DocFormat.is_structured(self.detected_format)


