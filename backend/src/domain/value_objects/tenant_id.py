"""
Tenant ID value object
"""
from typing import Optional
from pydantic import BaseModel, Field, validator
import uuid


class TenantId(BaseModel):
    """Tenant identifier value object"""
    
    value: str = Field(..., description="Unique tenant identifier")
    
    @validator('value')
    def validate_tenant_id(cls, v):
        """Validate tenant ID format"""
        if not v or not v.strip():
            raise ValueError("Tenant ID cannot be empty")
        
        # Ensure it's a valid format (UUID or alphanumeric)
        if len(v) < 3:
            raise ValueError("Tenant ID must be at least 3 characters")
        
        return v.strip()
    
    @classmethod
    def generate(cls) -> 'TenantId':
        """Generate a new tenant ID"""
        return cls(value=str(uuid.uuid4()))
    
    def __str__(self) -> str:
        return self.value
    
    def __hash__(self) -> int:
        return hash(self.value)
    
    def __eq__(self, other) -> bool:
        if isinstance(other, TenantId):
            return self.value == other.value
        return False


class TenantContext(BaseModel):
    """Tenant context for request scoping"""
    
    tenant_id: str
    partner_id: Optional[str] = None
    user_id: Optional[str] = None
    
    class Config:
        frozen = True  # Immutable


