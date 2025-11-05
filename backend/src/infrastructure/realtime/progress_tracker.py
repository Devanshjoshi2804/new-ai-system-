"""
Real-time Progress Tracker
Tracks and broadcasts progress updates for long-running operations
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ProgressStatus(str, Enum):
    """Progress status enum"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProgressTracker:
    """Track progress of long-running operations"""
    
    def __init__(self):
        """Initialize progress tracker"""
        self.operations: Dict[str, Dict[str, Any]] = {}
        self.subscribers: Dict[str, List[callable]] = {}
    
    def start_operation(
        self,
        operation_id: str,
        operation_type: str,
        total_steps: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Start tracking an operation
        
        Args:
            operation_id: Unique operation identifier
            operation_type: Type of operation (e.g., "analyze_documentation")
            total_steps: Total number of steps
            metadata: Optional metadata
        """
        self.operations[operation_id] = {
            'operation_id': operation_id,
            'operation_type': operation_type,
            'status': ProgressStatus.IN_PROGRESS,
            'current_step': 0,
            'total_steps': total_steps,
            'progress_percentage': 0,
            'steps': [],
            'started_at': datetime.utcnow().isoformat(),
            'completed_at': None,
            'error': None,
            'metadata': metadata or {}
        }
        
        logger.info(f"[INFO] Started tracking operation: {operation_id} ({operation_type})")
        self._broadcast_update(operation_id)
    
    def update_step(
        self,
        operation_id: str,
        step_name: str,
        step_status: ProgressStatus,
        step_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update current step
        
        Args:
            operation_id: Operation identifier
            step_name: Name of the step
            step_status: Status of the step
            step_data: Optional step data
        """
        if operation_id not in self.operations:
            logger.warning(f"[WARN] Operation {operation_id} not found")
            return
        
        operation = self.operations[operation_id]
        
        # Add step
        step = {
            'step_number': operation['current_step'] + 1,
            'step_name': step_name,
            'status': step_status,
            'data': step_data or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        operation['steps'].append(step)
        
        # Update current step if completed
        if step_status == ProgressStatus.COMPLETED:
            operation['current_step'] += 1
            operation['progress_percentage'] = int(
                (operation['current_step'] / operation['total_steps']) * 100
            )
        
        logger.info(f"[INFO] Step update: {operation_id} - {step_name} ({step_status})")
        self._broadcast_update(operation_id)
    
    def complete_operation(
        self,
        operation_id: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark operation as completed
        
        Args:
            operation_id: Operation identifier
            result: Optional result data
        """
        if operation_id not in self.operations:
            return
        
        operation = self.operations[operation_id]
        operation['status'] = ProgressStatus.COMPLETED
        operation['progress_percentage'] = 100
        operation['completed_at'] = datetime.utcnow().isoformat()
        operation['result'] = result
        
        logger.info(f"[OK] Operation completed: {operation_id}")
        self._broadcast_update(operation_id)
    
    def fail_operation(
        self,
        operation_id: str,
        error: str
    ) -> None:
        """
        Mark operation as failed
        
        Args:
            operation_id: Operation identifier
            error: Error message
        """
        if operation_id not in self.operations:
            return
        
        operation = self.operations[operation_id]
        operation['status'] = ProgressStatus.FAILED
        operation['completed_at'] = datetime.utcnow().isoformat()
        operation['error'] = error
        
        logger.error(f"[ERROR] Operation failed: {operation_id} - {error}")
        self._broadcast_update(operation_id)
    
    def get_progress(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current progress
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            Progress data or None
        """
        return self.operations.get(operation_id)
    
    def subscribe(self, operation_id: str, callback: callable) -> None:
        """
        Subscribe to progress updates
        
        Args:
            operation_id: Operation identifier
            callback: Callback function to call on updates
        """
        if operation_id not in self.subscribers:
            self.subscribers[operation_id] = []
        
        self.subscribers[operation_id].append(callback)
        logger.info(f"[INFO] Subscribed to operation: {operation_id}")
    
    def unsubscribe(self, operation_id: str, callback: callable) -> None:
        """
        Unsubscribe from progress updates
        
        Args:
            operation_id: Operation identifier
            callback: Callback function to remove
        """
        if operation_id in self.subscribers:
            self.subscribers[operation_id].remove(callback)
    
    def _broadcast_update(self, operation_id: str) -> None:
        """
        Broadcast update to all subscribers
        
        Args:
            operation_id: Operation identifier
        """
        if operation_id not in self.subscribers:
            return
        
        progress = self.get_progress(operation_id)
        if not progress:
            return
        
        # Call all subscribers
        for callback in self.subscribers[operation_id]:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"[ERROR] Error in subscriber callback: {e}")
    
    def cleanup_old_operations(self, max_age_hours: int = 24) -> None:
        """
        Cleanup old operations
        
        Args:
            max_age_hours: Maximum age in hours
        """
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for op_id, operation in self.operations.items():
            started_at = datetime.fromisoformat(operation['started_at'])
            if started_at < cutoff:
                to_remove.append(op_id)
        
        for op_id in to_remove:
            del self.operations[op_id]
            if op_id in self.subscribers:
                del self.subscribers[op_id]
        
        if to_remove:
            logger.info(f"[INFO] Cleaned up {len(to_remove)} old operations")


# Global progress tracker instance
_progress_tracker = None


def get_progress_tracker() -> ProgressTracker:
    """Get global progress tracker instance"""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker

