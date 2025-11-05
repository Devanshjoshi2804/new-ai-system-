"""
Partner repository interface
"""
from abc import abstractmethod
from typing import Optional, List
from src.domain.repositories.base_repository import BaseRepository
from src.domain.entities.partner import Partner, PartnerStatus


class PartnerRepository(BaseRepository[Partner]):
    """Partner repository interface"""
    
    @abstractmethod
    async def find_by_tenant_id(self, tenant_id: str) -> Optional[Partner]:
        """Find partner by tenant ID"""
        pass
    
    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[Partner]:
        """Find partner by email"""
        pass
    
    @abstractmethod
    async def find_by_status(self, status: PartnerStatus) -> List[Partner]:
        """Find partners by status"""
        pass
    
    @abstractmethod
    async def find_active_partners(self) -> List[Partner]:
        """Find all active partners"""
        pass
    
    @abstractmethod
    async def update_status(self, partner_id: str, status: PartnerStatus) -> bool:
        """Update partner status"""
        pass


