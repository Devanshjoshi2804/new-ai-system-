"""
Base repository interface with tenant awareness
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Any

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Base repository interface"""
    
    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[T]:
        """Find entity by ID"""
        pass
    
    @abstractmethod
    async def find_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Find all entities (with pagination)"""
        pass
    
    @abstractmethod
    async def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """Find entities matching criteria"""
        pass
    
    @abstractmethod
    async def save(self, entity: T) -> T:
        """Save entity (create or update)"""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity by ID"""
        pass
    
    @abstractmethod
    async def count(self, criteria: Optional[Dict[str, Any]] = None) -> int:
        """Count entities"""
        pass


class TenantAwareRepository(BaseRepository[T], ABC):
    """
    Base repository with tenant isolation
    All queries automatically filtered by tenant_id
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def _add_tenant_filter(self, criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add tenant filter to criteria"""
        if criteria is None:
            criteria = {}
        return {**criteria, "tenant_id": self.tenant_id}
    
    @abstractmethod
    async def find_by_tenant(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Find all entities for current tenant"""
        pass


