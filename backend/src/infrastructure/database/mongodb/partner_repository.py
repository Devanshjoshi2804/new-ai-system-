"""
Simple MongoDB Partner Repository
Uses Motor directly without Beanie
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from src.infrastructure.database.mongodb.simple_repository import SimpleMongoRepository

logger = logging.getLogger(__name__)


class MongoDBPartnerRepository:
    """MongoDB Partner Repository using Motor directly"""
    
    def __init__(self):
        self.repo = SimpleMongoRepository('partners')
    
    async def create(self, partner_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new partner"""
        # Generate IDs if not provided
        if 'id' not in partner_data:
            partner_data['id'] = str(uuid.uuid4())
        if 'tenant_id' not in partner_data:
            partner_data['tenant_id'] = f"tenant_{uuid.uuid4().hex[:12]}"
        
        # Set defaults
        partner_data.setdefault('status', 'pending')
        partner_data.setdefault('onboarding_step', 0)
        partner_data.setdefault('has_active_integration', False)
        partner_data.setdefault('metadata', {})
        
        # Insert into MongoDB
        doc_id = await self.repo.insert_one(partner_data)
        
        # Return the created partner
        return await self.get_by_id(partner_data['id'])
    
    async def get_by_id(self, partner_id: str) -> Optional[Dict[str, Any]]:
        """Get partner by ID"""
        return await self.repo.find_one({'id': partner_id})
    
    async def get_by_tenant_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get partner by tenant ID"""
        return await self.repo.find_one({'tenant_id': tenant_id})
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get partner by company email"""
        return await self.repo.find_one({'company_email': email})
    
    async def find_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all partners"""
        return await self.repo.find_many({}, limit=limit)
    
    async def find_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Find partners by status"""
        return await self.repo.find_many({'status': status})
    
    async def update(self, partner_id: str, update_data: Dict[str, Any]) -> bool:
        """Update partner"""
        return await self.repo.update_one({'id': partner_id}, update_data)
    
    async def update_status(self, partner_id: str, status: str) -> bool:
        """Update partner status"""
        return await self.repo.update_one({'id': partner_id}, {'status': status})
    
    async def update_onboarding_step(self, partner_id: str, step: int) -> bool:
        """Update onboarding step"""
        return await self.repo.update_one({'id': partner_id}, {'onboarding_step': step})
    
    async def activate_integration(self, partner_id: str, integration_config_id: str) -> bool:
        """Activate integration for partner"""
        return await self.repo.update_one(
            {'id': partner_id},
            {
                'has_active_integration': True,
                'integration_config_id': integration_config_id,
                'status': 'active',
                'activated_at': datetime.utcnow()
            }
        )
    
    async def delete(self, partner_id: str) -> bool:
        """Delete partner"""
        return await self.repo.delete_one({'id': partner_id})
    
    async def count(self) -> int:
        """Count all partners"""
        return await self.repo.count({})


