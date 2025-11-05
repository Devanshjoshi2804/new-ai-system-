"""
Dynamic webhook handler for partner webhooks
Allows partners to send events (shipment updates, tracking updates, etc.)
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Request, Header
from pydantic import BaseModel
import hashlib
import hmac

# Using MongoDB for all data storage
from src.infrastructure.ai.mem0.tenant_mem0_wrapper import get_memory_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class WebhookEvent(BaseModel):
    """Webhook event data"""
    event_type: str
    data: Dict[str, Any]
    timestamp: Optional[str] = None


@router.post("/webhooks/{partner_id}")
async def handle_partner_webhook(
    partner_id: str,
    request: Request,
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature")
):
    """
    Universal webhook handler for all partners
    
    Each partner can configure webhooks to send events to:
    https://platform.example.com/api/webhooks/{partner_id}
    
    Supported events:
    - shipment.created
    - shipment.updated
    - shipment.delivered
    - tracking.updated
    - booking.confirmed
    - booking.cancelled
    
    The webhook signature can be verified using partner's webhook secret
    """
    try:
        logger.info(f"Received webhook for partner: {partner_id}")
        
        # Get partner
        partner = await Partner.find_one(Partner.id == partner_id)
        
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partner not found"
            )
        
        # Get request body
        body = await request.body()
        body_str = body.decode('utf-8')
        
        # Verify signature if partner has webhook secret
        if hasattr(partner, 'webhook_secret') and partner.webhook_secret:
            if not x_webhook_signature:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Webhook signature required"
                )
            
            # Verify signature
            if not verify_webhook_signature(
                body_str,
                x_webhook_signature,
                partner.webhook_secret
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature"
                )
        
        # Parse JSON
        import json
        try:
            payload = json.loads(body_str)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Process webhook event
        result = await process_webhook_event(
            partner_id=partner_id,
            tenant_id=partner.tenant_id,
            payload=payload
        )
        
        logger.info(f"Webhook processed successfully: {result}")
        
        return {
            "success": True,
            "message": "Webhook received and processed",
            "event_id": result.get("event_id")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


async def process_webhook_event(
    partner_id: str,
    tenant_id: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process webhook event
    
    Args:
        partner_id: Partner identifier
        tenant_id: Tenant identifier
        payload: Webhook payload
        
    Returns:
        Processing result
    """
    try:
        # Extract event type
        event_type = payload.get("event", payload.get("event_type", "unknown"))
        
        logger.info(f"Processing webhook event: {event_type}")
        
        # Store event data
        event_id = await store_webhook_event(
            partner_id=partner_id,
            tenant_id=tenant_id,
            event_type=event_type,
            payload=payload
        )
        
        # Route to appropriate handler
        if "shipment" in event_type.lower():
            await handle_shipment_event(partner_id, tenant_id, payload)
        elif "booking" in event_type.lower():
            await handle_booking_event(partner_id, tenant_id, payload)
        elif "tracking" in event_type.lower():
            await handle_tracking_event(partner_id, tenant_id, payload)
        
        # Store in AI memory for learning
        await store_event_in_memory(
            tenant_id=tenant_id,
            event_type=event_type,
            payload=payload
        )
        
        return {
            "event_id": event_id,
            "status": "processed"
        }
    
    except Exception as e:
        logger.error(f"Error processing webhook event: {e}")
        raise


async def store_webhook_event(
    partner_id: str,
    tenant_id: str,
    event_type: str,
    payload: Dict[str, Any]
) -> str:
    """Store webhook event in database"""
    try:
        from infrastructure.database.mongodb.connection import get_database
        from datetime import datetime
        import uuid
        
        db = get_database()
        collection = db[f"tenant_{tenant_id}_webhook_events"]
        
        event_id = str(uuid.uuid4())
        
        await collection.insert_one({
            "event_id": event_id,
            "partner_id": partner_id,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "payload": payload,
            "created_at": datetime.utcnow(),
            "processed": True
        })
        
        logger.info(f"Webhook event stored: {event_id}")
        return event_id
    
    except Exception as e:
        logger.error(f"Error storing webhook event: {e}")
        return ""


async def handle_shipment_event(
    partner_id: str,
    tenant_id: str,
    payload: Dict[str, Any]
):
    """Handle shipment-related webhook events"""
    logger.info(f"Handling shipment event for partner: {partner_id}")
    
    # Extract shipment data
    shipment_data = payload.get("data", payload)
    awb = shipment_data.get("awb", shipment_data.get("tracking_number"))
    status = shipment_data.get("status")
    
    logger.info(f"Shipment {awb} status: {status}")
    
    # TODO: Update shipment in database
    # TODO: Notify relevant users
    # TODO: Trigger any automated workflows


async def handle_booking_event(
    partner_id: str,
    tenant_id: str,
    payload: Dict[str, Any]
):
    """Handle booking-related webhook events"""
    logger.info(f"Handling booking event for partner: {partner_id}")
    
    # Extract booking data
    booking_data = payload.get("data", payload)
    booking_id = booking_data.get("booking_id", booking_data.get("order_id"))
    
    logger.info(f"Booking {booking_id} event received")
    
    # TODO: Update booking in database
    # TODO: Notify relevant users


async def handle_tracking_event(
    partner_id: str,
    tenant_id: str,
    payload: Dict[str, Any]
):
    """Handle tracking update events"""
    logger.info(f"Handling tracking event for partner: {partner_id}")
    
    # Extract tracking data
    tracking_data = payload.get("data", payload)
    
    logger.info("Tracking update processed")
    
    # TODO: Update tracking info in database
    # TODO: Send real-time updates to users


async def store_event_in_memory(
    tenant_id: str,
    event_type: str,
    payload: Dict[str, Any]
):
    """Store webhook event in AI memory for learning"""
    try:
        memory_manager = get_memory_manager()
        
        # Format event as message
        message = f"Webhook event received: {event_type}. Data: {payload}"
        
        # Store in memory
        await memory_manager.add_memory(
            tenant_id=tenant_id,
            messages=[message],
            metadata={
                "type": "webhook_event",
                "event_type": event_type
            }
        )
        
        logger.info("Event stored in AI memory")
    
    except Exception as e:
        logger.error(f"Error storing event in memory: {e}")


def verify_webhook_signature(
    payload: str,
    signature: str,
    secret: str
) -> bool:
    """
    Verify webhook signature using HMAC-SHA256
    
    Args:
        payload: Request body as string
        signature: Signature from header
        secret: Partner's webhook secret
        
    Returns:
        True if signature is valid
    """
    try:
        # Calculate expected signature
        expected_signature = hmac.new(
            key=secret.encode('utf-8'),
            msg=payload.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Compare signatures (constant-time comparison)
        return hmac.compare_digest(expected_signature, signature)
    
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False


@router.get("/webhooks/{partner_id}/test")
async def test_webhook(partner_id: str):
    """
    Test endpoint to verify webhook configuration
    
    Partners can call this to test their webhook setup
    """
    return {
        "webhook_url": f"/api/webhooks/{partner_id}",
        "status": "active",
        "supported_events": [
            "shipment.created",
            "shipment.updated",
            "shipment.delivered",
            "tracking.updated",
            "booking.confirmed",
            "booking.cancelled"
        ],
        "authentication": "X-Webhook-Signature header with HMAC-SHA256",
        "example_payload": {
            "event": "shipment.updated",
            "data": {
                "awb": "AWB123456",
                "status": "in_transit",
                "location": "Mumbai Hub",
                "timestamp": "2024-01-20T10:30:00Z"
            }
        }
    }


