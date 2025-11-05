"""
MongoDB implementation of Partner repository
"""
from typing import Optional, List
from beanie import PydanticObjectId

from src.domain.repositories.partner_repository import PartnerRepository
from src.domain.entities.partner import Partner as PartnerEntity, PartnerStatus
from src.infrastructure.database.models.partner_model import Partner as PartnerModel


class MongoPartnerRepository(PartnerRepository):
    """MongoDB implementation of Partner repository"""
    
    async def find_by_id(self, id: str) -> Optional[PartnerEntity]:
        """Find partner by ID"""
        partner_model = await PartnerModel.get(PydanticObjectId(id))
        if partner_model:
            return self._to_entity(partner_model)
        return None
    
    async def find_all(self, skip: int = 0, limit: int = 100) -> List[PartnerEntity]:
        """Find all partners"""
        partners = await PartnerModel.find_all().skip(skip).limit(limit).to_list()
        return [self._to_entity(p) for p in partners]
    
    async def find_by_criteria(self, criteria: dict) -> List[PartnerEntity]:
        """Find partners by criteria"""
        partners = await PartnerModel.find(criteria).to_list()
        return [self._to_entity(p) for p in partners]
    
    async def save(self, entity: PartnerEntity) -> PartnerEntity:
        """Save partner"""
        # Check if exists
        existing = None
        if entity.id:
            try:
                existing = await PartnerModel.get(PydanticObjectId(entity.id))
            except:
                pass
        
        if existing:
            # Update existing
            await existing.set(self._to_model_dict(entity))
            return self._to_entity(existing)
        else:
            # Create new
            partner_model = PartnerModel(**entity.model_dump(exclude={'id'}))
            await partner_model.insert()
            entity.id = str(partner_model.id)
            return entity
    
    async def delete(self, id: str) -> bool:
        """Delete partner"""
        partner = await PartnerModel.get(PydanticObjectId(id))
        if partner:
            await partner.delete()
            return True
        return False
    
    async def count(self, criteria: Optional[dict] = None) -> int:
        """Count partners"""
        if criteria:
            return await PartnerModel.find(criteria).count()
        return await PartnerModel.count()
    
    async def find_by_tenant_id(self, tenant_id: str) -> Optional[PartnerEntity]:
        """Find partner by tenant ID"""
        partner = await PartnerModel.find_one(PartnerModel.tenant_id == tenant_id)
        if partner:
            return self._to_entity(partner)
        return None
    
    async def find_by_email(self, email: str) -> Optional[PartnerEntity]:
        """Find partner by email"""
        partner = await PartnerModel.find_one(PartnerModel.company_email == email)
        if partner:
            return self._to_entity(partner)
        return None
    
    async def find_by_status(self, status: PartnerStatus) -> List[PartnerEntity]:
        """Find partners by status"""
        partners = await PartnerModel.find(PartnerModel.status == status).to_list()
        return [self._to_entity(p) for p in partners]
    
    async def find_active_partners(self) -> List[PartnerEntity]:
        """Find all active partners"""
        partners = await PartnerModel.find(
            PartnerModel.status == PartnerStatus.ACTIVE,
            PartnerModel.has_active_integration == True
        ).to_list()
        return [self._to_entity(p) for p in partners]
    
    async def update_status(self, partner_id: str, status: PartnerStatus) -> bool:
        """Update partner status"""
        partner = await PartnerModel.get(PydanticObjectId(partner_id))
        if partner:
            partner.status = status
            await partner.save()
            return True
        return False
    
    def _to_entity(self, model: PartnerModel) -> PartnerEntity:
        """Convert model to entity"""
        data = model.model_dump(exclude={'id', 'revision_id'})
        data['id'] = str(model.id)
        return PartnerEntity(**data)
    
    def _to_model_dict(self, entity: PartnerEntity) -> dict:
        """Convert entity to model dict"""
        return entity.model_dump(exclude={'id'})


