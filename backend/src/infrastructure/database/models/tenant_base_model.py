"""
Base model for tenant-aware documents
"""
from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import Field


class TenantBaseDocument(Document):
    """Base document model with tenant isolation"""
    
    tenant_id: str = Field(..., index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        use_state_management = True
        validate_on_save = True
    
    async def save(self, *args, **kwargs):
        """Override save to update timestamp"""
        self.updated_at = datetime.utcnow()
        return await super().save(*args, **kwargs)
    
    @classmethod
    async def find_by_tenant(cls, tenant_id: str, **kwargs):
        """Find documents by tenant ID"""
        return await cls.find(cls.tenant_id == tenant_id, **kwargs).to_list()
    
    @classmethod
    async def find_one_by_tenant(cls, tenant_id: str, **kwargs):
        """Find single document by tenant ID"""
        return await cls.find_one(cls.tenant_id == tenant_id, **kwargs)


