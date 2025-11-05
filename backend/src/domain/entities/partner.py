"""
Partner domain entity
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import uuid


class PartnerStatus(str, Enum):
    """Partner onboarding status"""
    PENDING = "pending"
    PARSING = "parsing"
    GENERATING = "generating"
    TESTING = "testing"
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"


class Partner(BaseModel):
    """Partner aggregate root"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str  # Unique tenant identifier
    
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "CargoDham Logistics",
                "company_email": "contact@cargodham.com",
                "company_website": "https://cargodham.com",
                "contact_name": "John Doe",
                "contact_email": "john@cargodham.com",
                "status": "pending"
            }
        }
    
    def activate(self):
        """Activate the partner"""
        self.status = PartnerStatus.ACTIVE
        self.has_active_integration = True
        self.activated_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Deactivate the partner"""
        self.status = PartnerStatus.INACTIVE
        self.has_active_integration = False
        self.updated_at = datetime.utcnow()
    
    def update_status(self, status: PartnerStatus, step: Optional[int] = None):
        """Update onboarding status"""
        self.status = status
        if step is not None:
            self.onboarding_step = step
        self.updated_at = datetime.utcnow()
    
    def is_active(self) -> bool:
        """Check if partner is active"""
        return self.status == PartnerStatus.ACTIVE and self.has_active_integration


