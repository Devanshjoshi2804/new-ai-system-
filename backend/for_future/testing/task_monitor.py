"""
Background Task Monitor (BUG #14 FIX)
Monitors long-running test executions and provides real-time status
"""
import asyncio
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class BackgroundTaskMonitor:
    """
    Monitors background test execution tasks
    BUG #14 FIX: Prevents silent failures and provides visibility
    """
    
    def __init__(self):
        """Initialize task monitor"""
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.completed_tasks: Dict[str, Dict[str, Any]] = {}
        self.failed_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_handles: Dict[str, asyncio.Task] = {}
        
        logger.info("BackgroundTaskMonitor initialized")
    
    def register_task(
        self,
        task_id: str,
        task_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Register a new background task
        
        Args:
            task_id: Unique task identifier
            task_type: Type of task (e.g., 'test_execution', 'api_test')
            metadata: Optional metadata
        """
        self.active_tasks[task_id] = {
            "task_id": task_id,
            "task_type": task_type,
            "status": "running",
            "started_at": datetime.utcnow(),
            "last_update": datetime.utcnow(),
            "metadata": metadata or {},
            "progress": 0,
            "errors": []
        }
        
        logger.info(f"📋 Registered task: {task_id} ({task_type})")
    
    def update_task_progress(
        self,
        task_id: str,
        progress: int,
        message: Optional[str] = None
    ):
        """
        Update task progress
        
        Args:
            task_id: Task identifier
            progress: Progress percentage (0-100)
            message: Optional status message
        """
        if task_id not in self.active_tasks:
            logger.warning(f"⚠️  Task {task_id} not found")
            return
        
        self.active_tasks[task_id]["progress"] = progress
        self.active_tasks[task_id]["last_update"] = datetime.utcnow()
        
        if message:
            self.active_tasks[task_id]["last_message"] = message
        
        logger.debug(f"📊 Task {task_id}: {progress}% - {message}")
    
    def report_task_error(self, task_id: str, error: str):
        """
        Report an error for a task
        
        Args:
            task_id: Task identifier
            error: Error message
        """
        if task_id not in self.active_tasks:
            logger.warning(f"⚠️  Task {task_id} not found")
            return
        
        self.active_tasks[task_id]["errors"].append({
            "error": error,
            "timestamp": datetime.utcnow()
        })
        
        logger.error(f"❌ Task {task_id} error: {error}")
    
    def complete_task(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None
    ):
        """
        Mark task as completed
        
        Args:
            task_id: Task identifier
            result: Optional result data
        """
        if task_id not in self.active_tasks:
            logger.warning(f"⚠️  Task {task_id} not found")
            return
        
        task = self.active_tasks.pop(task_id)
        task["status"] = "completed"
        task["completed_at"] = datetime.utcnow()
        task["duration"] = (task["completed_at"] - task["started_at"]).total_seconds()
        
        if result:
            task["result"] = result
        
        self.completed_tasks[task_id] = task
        
        # Clean up task handle
        if task_id in self.task_handles:
            del self.task_handles[task_id]
        
        logger.info(f"✅ Task {task_id} completed in {task['duration']:.1f}s")
    
    def fail_task(self, task_id: str, reason: str):
        """
        Mark task as failed
        
        Args:
            task_id: Task identifier
            reason: Failure reason
        """
        if task_id not in self.active_tasks:
            logger.warning(f"⚠️  Task {task_id} not found")
            return
        
        task = self.active_tasks.pop(task_id)
        task["status"] = "failed"
        task["completed_at"] = datetime.utcnow()
        task["duration"] = (task["completed_at"] - task["started_at"]).total_seconds()
        task["failure_reason"] = reason
        
        self.failed_tasks[task_id] = task
        
        # Clean up task handle
        if task_id in self.task_handles:
            del self.task_handles[task_id]
        
        logger.error(f"❌ Task {task_id} failed: {reason}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status dictionary or None
        """
        # Check active tasks
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        
        # Check completed tasks
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        
        # Check failed tasks
        if task_id in self.failed_tasks:
            return self.failed_tasks[task_id]
        
        return None
    
    def get_all_tasks(self) -> Dict[str, Any]:
        """
        Get all tasks grouped by status
        
        Returns:
            Dictionary with active, completed, and failed tasks
        """
        return {
            "active": list(self.active_tasks.values()),
            "completed": list(self.completed_tasks.values()),
            "failed": list(self.failed_tasks.values()),
            "summary": {
                "active_count": len(self.active_tasks),
                "completed_count": len(self.completed_tasks),
                "failed_count": len(self.failed_tasks),
                "total_count": len(self.active_tasks) + len(self.completed_tasks) + len(self.failed_tasks)
            }
        }
    
    async def monitor_task(
        self,
        task_id: str,
        coro,
        task_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Monitor an async task and track its lifecycle
        
        Args:
            task_id: Unique task identifier
            coro: Coroutine to execute
            task_type: Type of task
            metadata: Optional metadata
            
        Returns:
            Task result
        """
        # Register task
        self.register_task(task_id, task_type, metadata)
        
        try:
            # Create task
            task = asyncio.create_task(coro)
            self.task_handles[task_id] = task
            
            # Execute and monitor
            result = await task
            
            # Mark as completed
            self.complete_task(task_id, result)
            
            return result
        
        except asyncio.CancelledError:
            logger.warning(f"⚠️  Task {task_id} was cancelled")
            self.fail_task(task_id, "Task cancelled")
            raise
        
        except Exception as e:
            logger.error(f"❌ Task {task_id} failed with exception: {e}", exc_info=True)
            self.fail_task(task_id, str(e))
            raise
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if cancelled successfully
        """
        if task_id not in self.task_handles:
            logger.warning(f"⚠️  Task {task_id} not found or already completed")
            return False
        
        task = self.task_handles[task_id]
        task.cancel()
        
        logger.info(f"🛑 Cancelled task: {task_id}")
        return True
    
    def cleanup_old_tasks(self, hours_old: int = 24):
        """
        Clean up old completed/failed tasks
        
        Args:
            hours_old: Remove tasks older than this many hours
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours_old)
        
        # Clean completed tasks
        old_completed = [
            task_id for task_id, task in self.completed_tasks.items()
            if task.get('completed_at', datetime.utcnow()) < cutoff
        ]
        
        for task_id in old_completed:
            del self.completed_tasks[task_id]
        
        # Clean failed tasks
        old_failed = [
            task_id for task_id, task in self.failed_tasks.items()
            if task.get('completed_at', datetime.utcnow()) < cutoff
        ]
        
        for task_id in old_failed:
            del self.failed_tasks[task_id]
        
        total_cleaned = len(old_completed) + len(old_failed)
        if total_cleaned > 0:
            logger.info(f"🧹 Cleaned up {total_cleaned} old tasks")
    
    async def auto_cleanup_loop(self, cleanup_interval_hours: int = 6):
        """
        Run automatic cleanup loop
        
        Args:
            cleanup_interval_hours: Hours between cleanup runs
        """
        logger.info(f"🔄 Starting auto-cleanup loop (every {cleanup_interval_hours}h)")
        
        while True:
            try:
                await asyncio.sleep(cleanup_interval_hours * 3600)
                self.cleanup_old_tasks(hours_old=24)
            
            except Exception as e:
                logger.error(f"❌ Auto-cleanup error: {e}")
                await asyncio.sleep(60)


# Global monitor instance
_monitor_instance: Optional[BackgroundTaskMonitor] = None


def get_monitor() -> BackgroundTaskMonitor:
    """Get global monitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = BackgroundTaskMonitor()
    return _monitor_instance
