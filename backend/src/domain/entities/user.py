"""
User domain entity
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import uuid


class UserRole(str, Enum):
    """User roles"""
    ADMIN = "admin"  # Platform admin
    PARTNER_ADMIN = "partner_admin"  # Partner administrator
    PARTNER_USER = "partner_user"  # Partner user
    USER = "user"  # End user


class User(BaseModel):
    """User entity"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    hashed_password: str
    
    # Profile
    full_name: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Role and permissions
    role: UserRole = UserRole.USER
    tenant_ids: List[str] = Field(default_factory=list)  # Tenants user has access to
    
    # Status
    is_active: bool = True
    is_verified: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "role": "user"
            }
        }
    
    def has_access_to_tenant(self, tenant_id: str) -> bool:
        """Check if user has access to tenant"""
        return tenant_id in self.tenant_ids or self.role == UserRole.ADMIN
    
    def add_tenant_access(self, tenant_id: str):
        """Grant access to tenant"""
        if tenant_id not in self.tenant_ids:
            self.tenant_ids.append(tenant_id)
            self.updated_at = datetime.utcnow()
    
    def remove_tenant_access(self, tenant_id: str):
        """Revoke access to tenant"""
        if tenant_id in self.tenant_ids:
            self.tenant_ids.remove(tenant_id)
            self.updated_at = datetime.utcnow()
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login_at = datetime.utcnow()


