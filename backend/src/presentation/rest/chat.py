"""
Chat API for autonomous operations
Users send natural language commands, AI executes them
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel

from src.application.ai.graphs.execution_graph import get_execution_graph
# Using MongoDB for all data storage

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessageRequest(BaseModel):
    """Chat message request"""
    message: str
    session_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """Chat message response"""
    response: str
    intent: Optional[str] = None
    entities: Optional[dict] = None
    api_calls: list = []
    success: bool = True
    session_id: Optional[str] = None


@router.post("/chat/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
):
    """
    Send a chat message for autonomous execution
    
    Examples:
    - "Book a shipment from Mumbai to Delhi for 5kg"
    - "Track shipment AWB123456"
    - "Calculate rate from Pune to Bangalore for 10kg"
    - "Cancel booking ORDER789"
    
    The AI will:
    1. Understand your intent
    2. Extract necessary information
    3. Call the partner's APIs automatically
    4. Return the result
    """
    try:
        if not x_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Tenant-ID header is required"
            )
        
        # Get partner from tenant ID
        partner = await Partner.find_one(Partner.tenant_id == x_tenant_id)
        
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partner not found for this tenant"
            )
        
        # Check if partner is active
        if not partner.has_active_integration:
            return ChatMessageResponse(
                response="Integration is still being set up. Please complete the onboarding process first.",
                success=False
            )
        
        logger.info(f"Processing chat message: {request.message}")
        
        # Execute autonomous operation
        execution_graph = get_execution_graph()
        
        result = await execution_graph.execute(
            user_message=request.message,
            partner_id=str(partner.id),
            tenant_id=x_tenant_id
        )
        
        return ChatMessageResponse(
            response=result.get("response", "Operation completed"),
            intent=result.get("intent"),
            entities=result.get("entities"),
            api_calls=result.get("api_calls", []),
            success=result.get("success", True),
            session_id=request.session_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/chat/capabilities")
async def get_chat_capabilities(x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """
    Get available capabilities for this tenant's chat
    
    Shows what operations the AI can perform
    """
    try:
        if not x_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Tenant-ID header is required"
            )
        
        # Get partner
        partner = await Partner.find_one(Partner.tenant_id == x_tenant_id)
        
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partner not found"
            )
        
        # Get integration config to see available operations
        from infrastructure.database.models.integration_model import IntegrationConfig
        
        integration = await IntegrationConfig.find_one(
            IntegrationConfig.partner_id == str(partner.id),
            IntegrationConfig.is_deployed == True
        )
        
        capabilities = {
            "partner_name": partner.company_name,
            "integration_active": partner.has_active_integration,
            "available_operations": [],
            "example_commands": [
                "Book a shipment from [origin] to [destination]",
                "Track shipment [AWB number]",
                "Calculate rate from [origin] to [destination] for [weight]",
                "Get status of order [order ID]"
            ]
        }
        
        if integration:
            # Extract operations from endpoints
            endpoints = integration.api_spec.get("endpoints", [])
            operations = set()
            
            for endpoint in endpoints:
                path = endpoint.get("path", "").lower()
                if "book" in path or "order" in path:
                    operations.add("CREATE_BOOKING")
                if "track" in path or "status" in path:
                    operations.add("TRACK_SHIPMENT")
                if "rate" in path or "price" in path:
                    operations.add("CALCULATE_RATE")
            
            capabilities["available_operations"] = list(operations)
        
        return capabilities
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


