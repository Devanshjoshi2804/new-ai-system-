"""
Partner MongoDB model
"""
from typing import Optional, Dict, Any
from beanie import Document, Indexed
from pydantic import Field, EmailStr
from datetime import datetime

from src.domain.entities.partner import PartnerStatus


class Partner(Document):
    """Partner document model for MongoDB"""
    
    tenant_id: Indexed(str, unique=True)
    
    # Company information
    company_name: str
    company_email: EmailStr
    company_website: Optional[str] = None
    company_logo: Optional[str] = None
    
    # Contact information
    contact_name: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    
    # API information
    api_base_url: Optional[str] = None
    api_documentation_url: Optional[str] = None
    
    # Status
    status: PartnerStatus = PartnerStatus.PENDING
    onboarding_step: int = 0
    
    # Integration details
    integration_config_id: Optional[str] = None
    has_active_integration: bool = False
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    activated_at: Optional[datetime] = None
    
    class Settings:
        name = "partners"
        indexes = [
            "tenant_id",
            "company_email",
            "status",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "CargoDham Logistics",
                "company_email": "contact@cargodham.com",
                "contact_name": "John Doe",
                "contact_email": "john@cargodham.com"
            }
        }


