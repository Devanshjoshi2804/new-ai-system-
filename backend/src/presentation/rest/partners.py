"""
Partner REST API endpoints
"""
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Depends
from pydantic import BaseModel, EmailStr

from src.domain.entities.partner import Partner, PartnerStatus
# Use MongoDB
from src.infrastructure.database.mongodb.partner_repository import MongoDBPartnerRepository

logger = logging.getLogger(__name__)

router = APIRouter()


class PartnerRegistrationRequest(BaseModel):
    """Partner registration request"""
    company_name: str
    company_email: EmailStr
    company_website: Optional[str] = None
    contact_name: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    api_base_url: Optional[str] = None


class PartnerResponse(BaseModel):
    """Partner response"""
    id: str
    tenant_id: str
    company_name: str
    company_email: str
    status: str
    onboarding_step: int
    has_active_integration: bool
    created_at: str


@router.post("/partners/register", response_model=PartnerResponse, status_code=status.HTTP_201_CREATED)
async def register_partner(request: PartnerRegistrationRequest):
    """
    Register a new partner
    
    This creates:
    1. Partner account
    2. Tenant ID
    """
    try:
        # Generate tenant ID
        import uuid
        tenant_id = str(uuid.uuid4())
        
        # Create partner entity
        partner = Partner(
            tenant_id=tenant_id,
            company_name=request.company_name,
            company_email=request.company_email,
            company_website=request.company_website,
            contact_name=request.contact_name,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone,
            api_base_url=request.api_base_url,
            status=PartnerStatus.PENDING,
            onboarding_step=0,
            integration_config_id=None,
            has_active_integration=False,
            metadata={}
        )
        
        # Save to MongoDB
        repo = MongoDBPartnerRepository()
        partner_data = {
            'tenant_id': tenant_id,
            'company_name': request.company_name,
            'company_email': request.company_email,
            'company_website': request.company_website,
            'contact_name': request.contact_name,
            'contact_email': request.contact_email,
            'contact_phone': request.contact_phone,
            'api_base_url': request.api_base_url,
            'status': 'pending',
            'onboarding_step': 0,
            'has_active_integration': False,
            'metadata': {}
        }
        saved_partner = await repo.create(partner_data)
        
        logger.info(f"Partner registered: {saved_partner['company_name']} (tenant_id: {tenant_id})")
        
        return PartnerResponse(
            id=saved_partner['id'],
            tenant_id=saved_partner['tenant_id'],
            company_name=saved_partner['company_name'],
            company_email=saved_partner['company_email'],
            status=saved_partner['status'],
            onboarding_step=saved_partner['onboarding_step'],
            has_active_integration=saved_partner['has_active_integration'],
            created_at=saved_partner.get('createdAt', datetime.utcnow()).isoformat() if isinstance(saved_partner.get('createdAt'), datetime) else str(saved_partner.get('createdAt', ''))
        )
    
    except Exception as e:
        logger.error(f"Error registering partner: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register partner: {str(e)}"
        )


@router.get("/partners/{partner_id}", response_model=PartnerResponse)
async def get_partner(partner_id: str):
    """Get partner by ID"""
    try:
        repo = MongoDBPartnerRepository()
        partner = await repo.get_by_id(partner_id)
        
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partner not found"
            )
        
        return PartnerResponse(
            id=partner['id'],
            tenant_id=partner['tenant_id'],
            company_name=partner['company_name'],
            company_email=partner['company_email'],
            status=partner['status'],
            onboarding_step=partner['onboarding_step'],
            has_active_integration=partner['has_active_integration'],
            created_at=partner.get('createdAt', datetime.utcnow()).isoformat() if isinstance(partner.get('createdAt'), datetime) else str(partner.get('createdAt', ''))
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting partner: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/partners/tenant/{tenant_id}", response_model=PartnerResponse)
async def get_partner_by_tenant(tenant_id: str):
    """Get partner by tenant ID"""
    try:
        repo = SQLitePartnerRepository()
        partner = await repo.get_by_tenant_id(tenant_id)
        
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partner not found"
            )
        
        return PartnerResponse(
            id=partner.id,
            tenant_id=partner.tenant_id,
            company_name=partner.company_name,
            company_email=partner.company_email,
            status=partner.status.value,
            onboarding_step=partner.onboarding_step,
            has_active_integration=partner.has_active_integration,
            created_at=partner.created_at.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting partner by tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


