"""
Real-time test event streaming system
Manages event streams for test execution with WebSocket support
"""
import asyncio
import logging
import json
from typing import Dict, Any, Optional, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Test event types"""
    TEST_START = "TEST_START"
    TEST_PROGRESS = "TEST_PROGRESS"
    TEST_LOG = "TEST_LOG"
    TEST_SUCCESS = "TEST_SUCCESS"
    TEST_ERROR = "TEST_ERROR"
    TEST_WARNING = "TEST_WARNING"
    TEST_COMPLETE = "TEST_COMPLETE"
    CONNECTION_STATUS = "CONNECTION_STATUS"


@dataclass
class TestEvent:
    """Test event data structure"""
    type: EventType
    test_id: str
    timestamp: str
    data: Dict[str, Any]
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps({
            'type': self.type.value,
            'test_id': self.test_id,
            'timestamp': self.timestamp,
            'data': self.data
        })
    
    @classmethod
    def create(
        cls,
        event_type: EventType,
        test_id: str,
        **data
    ) -> 'TestEvent':
        """Create a new test event"""
        return cls(
            type=event_type,
            test_id=test_id,
            timestamp=datetime.utcnow().isoformat(),
            data=data
        )


class TestEventStream:
    """
    Manages real-time event streaming for test execution
    
    Features:
    - Multiple subscribers per test
    - Event buffering
    - Automatic cleanup
    - Thread-safe operations
    """
    
    def __init__(self, buffer_size: int = 1000):
        """
        Initialize event stream
        
        Args:
            buffer_size: Maximum events to buffer per test
        """
        self.buffer_size = buffer_size
        
        # Active streams: test_id -> queue
        self.streams: Dict[str, asyncio.Queue] = {}
        
        # Subscribers: test_id -> set of subscriber_ids
        self.subscribers: Dict[str, Set[str]] = {}
        
        # Event buffers: test_id -> list of events
        self.buffers: Dict[str, list] = {}
        
        # Locks for thread safety
        self._locks: Dict[str, asyncio.Lock] = {}
        
        logger.info("[OK] Test event stream initialized")
    
    async def create_stream(self, test_id: str) -> str:
        """
        Create a new event stream for a test
        
        Args:
            test_id: Test identifier
            
        Returns:
            Subscriber ID
        """
        subscriber_id = str(uuid.uuid4())
        
        # Initialize stream if not exists
        if test_id not in self.streams:
            self.streams[test_id] = asyncio.Queue()
            self.subscribers[test_id] = set()
            self.buffers[test_id] = []
            self._locks[test_id] = asyncio.Lock()
            logger.info(f"[INFO] Created new stream for test: {test_id}")
        
        # Add subscriber
        self.subscribers[test_id].add(subscriber_id)
        logger.info(f"[INFO] Subscriber {subscriber_id[:8]} joined test {test_id}")
        
        # Send buffered events to new subscriber
        if self.buffers[test_id]:
            logger.info(f"[INFO] Sending {len(self.buffers[test_id])} buffered events to subscriber")
        
        return subscriber_id
    
    async def emit_event(
        self,
        test_id: str,
        event_type: EventType,
        **data
    ):
        """
        Emit an event to all subscribers
        
        Args:
            test_id: Test identifier
            event_type: Type of event
            **data: Event data
        """
        if test_id not in self.streams:
            logger.warning(f"[WARN] No stream found for test {test_id}")
            return
        
        # Create event
        event = TestEvent.create(event_type, test_id, **data)
        
        # Add to buffer
        async with self._locks[test_id]:
            self.buffers[test_id].append(event)
            
            # Trim buffer if too large
            if len(self.buffers[test_id]) > self.buffer_size:
                self.buffers[test_id] = self.buffers[test_id][-self.buffer_size:]
        
        # Put event in queue
        await self.streams[test_id].put(event)
        
        logger.debug(f"[INFO] Emitted {event_type.value} event for test {test_id}")
    
    async def get_events(
        self,
        test_id: str,
        subscriber_id: str
    ) -> Optional[TestEvent]:
        """
        Get next event for subscriber
        
        Args:
            test_id: Test identifier
            subscriber_id: Subscriber identifier
            
        Returns:
            Next event or None
        """
        if test_id not in self.streams:
            return None
        
        if subscriber_id not in self.subscribers.get(test_id, set()):
            logger.warning(f"[WARN] Unknown subscriber {subscriber_id[:8]} for test {test_id}")
            return None
        
        try:
            # Get event from queue
            event = await self.streams[test_id].get()
            return event
        except Exception as e:
            logger.error(f"[ERROR] Error getting event: {e}")
            return None
    
    async def get_buffered_events(self, test_id: str) -> list[TestEvent]:
        """
        Get all buffered events for a test
        
        Args:
            test_id: Test identifier
            
        Returns:
            List of buffered events
        """
        if test_id not in self.buffers:
            return []
        
        async with self._locks[test_id]:
            return self.buffers[test_id].copy()
    
    async def remove_subscriber(self, test_id: str, subscriber_id: str):
        """
        Remove a subscriber from a test stream
        
        Args:
            test_id: Test identifier
            subscriber_id: Subscriber identifier
        """
        if test_id in self.subscribers:
            self.subscribers[test_id].discard(subscriber_id)
            logger.info(f"[INFO] Subscriber {subscriber_id[:8]} left test {test_id}")
            
            # Cleanup if no more subscribers
            if not self.subscribers[test_id]:
                await self.cleanup_stream(test_id)
    
    async def cleanup_stream(self, test_id: str):
        """
        Clean up a test stream
        
        Args:
            test_id: Test identifier
        """
        if test_id in self.streams:
            # Remove from all dictionaries
            del self.streams[test_id]
            del self.subscribers[test_id]
            del self.buffers[test_id]
            del self._locks[test_id]
            
            logger.info(f"[DEL] Cleaned up stream for test {test_id}")
    
    def get_active_streams(self) -> list[str]:
        """Get list of active test IDs"""
        return list(self.streams.keys())
    
    def get_subscriber_count(self, test_id: str) -> int:
        """Get number of subscribers for a test"""
        return len(self.subscribers.get(test_id, set()))


# Global event stream instance
_global_stream: Optional[TestEventStream] = None


def get_event_stream() -> TestEventStream:
    """Get or create global event stream instance"""
    global _global_stream
    if _global_stream is None:
        _global_stream = TestEventStream()
    return _global_stream


class StreamLogger:
    """
    Logger that streams to event system
    
    Usage:
        logger = StreamLogger(test_id, event_stream)
        logger.info("Test started")
        logger.success("Test passed")
        logger.error("Test failed")
    """
    
    def __init__(self, test_id: str, event_stream: Optional[TestEventStream] = None):
        """
        Initialize stream logger
        
        Args:
            test_id: Test identifier
            event_stream: Event stream instance (uses global if None)
        """
        self.test_id = test_id
        self.event_stream = event_stream or get_event_stream()
    
    async def log(self, level: str, message: str, **extra):
        """
        Log a message
        
        Args:
            level: Log level (info, success, warning, error)
            message: Log message
            **extra: Additional data
        """
        await self.event_stream.emit_event(
            self.test_id,
            EventType.TEST_LOG,
            level=level,
            message=message,
            **extra
        )
    
    async def info(self, message: str, **extra):
        """Log info message"""
        await self.log('info', message, **extra)
    
    async def success(self, message: str, **extra):
        """Log success message"""
        await self.log('success', message, **extra)
    
    async def warning(self, message: str, **extra):
        """Log warning message"""
        await self.log('warning', message, **extra)
    
    async def error(self, message: str, **extra):
        """Log error message"""
        await self.log('error', message, **extra)
    
    async def progress(self, step: int, total_steps: int, step_name: str, **extra):
        """
        Log progress update
        
        Args:
            step: Current step number
            total_steps: Total number of steps
            step_name: Name of current step
            **extra: Additional data
        """
        await self.event_stream.emit_event(
            self.test_id,
            EventType.TEST_PROGRESS,
            step=step,
            total_steps=total_steps,
            step_name=step_name,
            percentage=round((step / total_steps) * 100, 1),
            **extra
        )

