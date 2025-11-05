"""
Real-time test execution WebSocket endpoint
Streams test execution events to connected clients
"""
import asyncio
import logging
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import JSONResponse

from src.infrastructure.realtime.test_stream import (
    get_event_stream,
    TestEventStream,
    EventType,
    StreamLogger
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["realtime-testing"])


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        """Initialize connection manager"""
        self.active_connections: Dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, test_id: str):
        """
        Accept and register a WebSocket connection
        
        Args:
            websocket: WebSocket connection
            test_id: Test identifier
        """
        await websocket.accept()
        
        if test_id not in self.active_connections:
            self.active_connections[test_id] = []
        
        self.active_connections[test_id].append(websocket)
        logger.info(f"✅ WebSocket connected for test {test_id} (total: {len(self.active_connections[test_id])})")
    
    def disconnect(self, websocket: WebSocket, test_id: str):
        """
        Remove a WebSocket connection
        
        Args:
            websocket: WebSocket connection
            test_id: Test identifier
        """
        if test_id in self.active_connections:
            if websocket in self.active_connections[test_id]:
                self.active_connections[test_id].remove(websocket)
                logger.info(f"👋 WebSocket disconnected for test {test_id}")
            
            # Cleanup if no more connections
            if not self.active_connections[test_id]:
                del self.active_connections[test_id]
    
    async def broadcast(self, test_id: str, message: str):
        """
        Broadcast message to all connections for a test
        
        Args:
            test_id: Test identifier
            message: Message to broadcast
        """
        if test_id not in self.active_connections:
            return
        
        # Send to all connections
        disconnected = []
        for connection in self.active_connections[test_id]:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"❌ Error sending to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection, test_id)
    
    def get_connection_count(self, test_id: str) -> int:
        """Get number of active connections for a test"""
        return len(self.active_connections.get(test_id, []))


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/test-execution/{test_id}")
async def websocket_test_execution(
    websocket: WebSocket,
    test_id: str
):
    """
    WebSocket endpoint for real-time test execution streaming
    
    Args:
        websocket: WebSocket connection
        test_id: Test execution identifier
    """
    event_stream = get_event_stream()
    subscriber_id = None
    
    try:
        # Accept connection
        await manager.connect(websocket, test_id)
        
        # Create subscriber
        subscriber_id = await event_stream.create_stream(test_id)
        
        # Send connection success message
        await websocket.send_json({
            'type': 'CONNECTION_STATUS',
            'status': 'connected',
            'test_id': test_id,
            'subscriber_id': subscriber_id
        })
        
        # Send buffered events
        buffered_events = await event_stream.get_buffered_events(test_id)
        for event in buffered_events:
            await websocket.send_text(event.to_json())
        
        # Listen for events and send to client
        while True:
            try:
                # Get next event (with timeout to check connection)
                event = await asyncio.wait_for(
                    event_stream.get_events(test_id, subscriber_id),
                    timeout=30.0
                )
                
                if event:
                    await websocket.send_text(event.to_json())
                    
                    # If test is complete, close connection after a delay
                    if event.type == EventType.TEST_COMPLETE:
                        logger.info(f"✅ Test {test_id} completed, closing connection in 5s")
                        await asyncio.sleep(5)
                        break
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({
                        'type': 'PING',
                        'timestamp': event_stream.buffers.get(test_id, [{}])[-1] if test_id in event_stream.buffers else None
                    })
                except:
                    break
            
            except Exception as e:
                logger.error(f"❌ Error in event loop: {e}")
                break
    
    except WebSocketDisconnect:
        logger.info(f"👋 WebSocket disconnected for test {test_id}")
    
    except Exception as e:
        logger.error(f"❌ WebSocket error for test {test_id}: {e}")
        try:
            await websocket.send_json({
                'type': 'ERROR',
                'error': str(e)
            })
        except:
            pass
    
    finally:
        # Cleanup
        manager.disconnect(websocket, test_id)
        if subscriber_id:
            await event_stream.remove_subscriber(test_id, subscriber_id)


@router.get("/test-stream/{test_id}/status")
async def get_test_stream_status(test_id: str) -> Dict[str, Any]:
    """
    Get status of a test stream
    
    Args:
        test_id: Test identifier
        
    Returns:
        Stream status information
    """
    event_stream = get_event_stream()
    
    return {
        'test_id': test_id,
        'active': test_id in event_stream.streams,
        'subscriber_count': event_stream.get_subscriber_count(test_id),
        'connection_count': manager.get_connection_count(test_id),
        'buffered_events': len(event_stream.buffers.get(test_id, []))
    }


@router.get("/test-stream/{test_id}/events")
async def get_test_stream_events(test_id: str) -> Dict[str, Any]:
    """
    Get buffered events for a test (for replay/history)
    
    Args:
        test_id: Test identifier
        
    Returns:
        List of buffered events
    """
    event_stream = get_event_stream()
    
    buffered_events = await event_stream.get_buffered_events(test_id)
    
    return {
        'test_id': test_id,
        'event_count': len(buffered_events),
        'events': [
            {
                'type': event.type.value,
                'timestamp': event.timestamp,
                'data': event.data
            }
            for event in buffered_events
        ]
    }


@router.delete("/test-stream/{test_id}")
async def cleanup_test_stream(test_id: str) -> Dict[str, Any]:
    """
    Manually cleanup a test stream
    
    Args:
        test_id: Test identifier
        
    Returns:
        Cleanup status
    """
    event_stream = get_event_stream()
    
    if test_id not in event_stream.streams:
        raise HTTPException(status_code=404, detail=f"Test stream {test_id} not found")
    
    await event_stream.cleanup_stream(test_id)
    
    return {
        'success': True,
        'message': f'Test stream {test_id} cleaned up successfully'
    }


@router.get("/test-streams/active")
async def get_active_test_streams() -> Dict[str, Any]:
    """
    Get list of active test streams
    
    Returns:
        List of active test IDs with their status
    """
    event_stream = get_event_stream()
    
    active_streams = []
    for test_id in event_stream.get_active_streams():
        active_streams.append({
            'test_id': test_id,
            'subscriber_count': event_stream.get_subscriber_count(test_id),
            'connection_count': manager.get_connection_count(test_id),
            'buffered_events': len(event_stream.buffers.get(test_id, []))
        })
    
    return {
        'active_count': len(active_streams),
        'streams': active_streams
    }


@router.post("/test-stream/{test_id}/emit")
async def emit_test_event(
    test_id: str,
    event_type: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Manually emit an event to a test stream (for testing/debugging)
    
    Args:
        test_id: Test identifier
        event_type: Event type
        data: Event data
        
    Returns:
        Success status
    """
    event_stream = get_event_stream()
    
    try:
        event_type_enum = EventType(event_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
    
    await event_stream.emit_event(test_id, event_type_enum, **data)
    
    return {
        'success': True,
        'message': f'Event {event_type} emitted to test {test_id}'
    }
