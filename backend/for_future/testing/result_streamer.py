"""
Result Streamer - Stream test results to database in real-time (BUG #16 FIX)
Prevents memory buildup by writing results immediately
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from queue import Queue
from threading import Thread

logger = logging.getLogger(__name__)


class ResultStreamer:
    """
    Streams test results to database in real-time
    BUG #16 FIX: Prevents holding all results in memory
    """
    
    def __init__(self, test_execution_repo, batch_size: int = 10):
        """
        Initialize result streamer
        
        Args:
            test_execution_repo: Test execution repository
            batch_size: Number of results to batch before writing
        """
        self.repo = test_execution_repo
        self.batch_size = batch_size
        self.result_queue = asyncio.Queue()
        self.is_streaming = False
        self.total_streamed = 0
        
        logger.info(f"ResultStreamer initialized (batch_size={batch_size})")
    
    async def start_streaming(self, test_execution_id: str):
        """
        Start streaming results to database
        
        Args:
            test_execution_id: ID of test execution
        """
        self.is_streaming = True
        self.test_execution_id = test_execution_id
        self.total_streamed = 0
        
        logger.info(f"📊 Started streaming results for {test_execution_id}")
        
        # Start background task to process queue
        asyncio.create_task(self._process_queue())
    
    async def stream_result(self, result: Dict[str, Any]):
        """
        Stream a single result to database
        
        Args:
            result: Test result to stream
        """
        if not self.is_streaming:
            logger.warning("⚠️  Streamer not started, result will be queued")
        
        await self.result_queue.put(result)
        logger.debug(f"📤 Queued result (queue size: {self.result_queue.qsize()})")
    
    async def _process_queue(self):
        """
        Process queued results in batches
        BUG #16 FIX: Write to DB immediately instead of holding in memory
        """
        batch = []
        
        while self.is_streaming or not self.result_queue.empty():
            try:
                # Get result with timeout
                result = await asyncio.wait_for(
                    self.result_queue.get(),
                    timeout=0.5
                )
                
                batch.append(result)
                
                # Write batch when full
                if len(batch) >= self.batch_size:
                    await self._write_batch(batch)
                    batch = []
            
            except asyncio.TimeoutError:
                # Timeout - write partial batch if any
                if batch:
                    await self._write_batch(batch)
                    batch = []
            
            except Exception as e:
                logger.error(f"❌ Error processing result queue: {e}")
        
        # Write remaining results
        if batch:
            await self._write_batch(batch)
        
        logger.info(f"✅ Finished streaming {self.total_streamed} results")
    
    async def _write_batch(self, batch: List[Dict[str, Any]]):
        """
        Write batch of results to database
        
        Args:
            batch: Batch of results to write
        """
        try:
            # Add results to test execution
            update_data = {
                f"results_{self.total_streamed}": batch,
                "result_count": self.total_streamed + len(batch),
                "updated_at": datetime.utcnow()
            }
            
            success = await self.repo.update(self.test_execution_id, update_data)
            
            if success:
                self.total_streamed += len(batch)
                logger.info(f"💾 Streamed batch of {len(batch)} results (total: {self.total_streamed})")
            else:
                logger.error(f"❌ Failed to stream batch of {len(batch)} results")
        
        except Exception as e:
            logger.error(f"❌ Error writing batch: {e}")
    
    async def stop_streaming(self) -> int:
        """
        Stop streaming and return total count
        
        Returns:
            Total number of results streamed
        """
        self.is_streaming = False
        
        # Wait for queue to be empty
        while not self.result_queue.empty():
            await asyncio.sleep(0.1)
        
        logger.info(f"🛑 Stopped streaming (total: {self.total_streamed})")
        return self.total_streamed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics"""
        return {
            "is_streaming": self.is_streaming,
            "total_streamed": self.total_streamed,
            "queue_size": self.result_queue.qsize(),
            "test_execution_id": getattr(self, 'test_execution_id', None)
        }


class ResultBatcher:
    """
    Alternative implementation using batching
    Simpler than streaming, still prevents memory buildup
    """
    
    def __init__(self, test_execution_repo, batch_size: int = 50):
        self.repo = test_execution_repo
        self.batch_size = batch_size
        self.current_batch = []
        self.total_written = 0
        self.test_execution_id = None
    
    async def add_result(self, result: Dict[str, Any]):
        """Add result to batch and write if full"""
        self.current_batch.append(result)
        
        if len(self.current_batch) >= self.batch_size:
            await self.flush()
    
    async def flush(self):
        """Write current batch to database"""
        if not self.current_batch:
            return
        
        if not self.test_execution_id:
            logger.warning("⚠️  No test_execution_id set, cannot flush")
            return
        
        try:
            # Write batch
            update_data = {
                "results": self.current_batch,
                "result_count": len(self.current_batch),
                "updated_at": datetime.utcnow()
            }
            
            await self.repo.update(self.test_execution_id, update_data)
            
            self.total_written += len(self.current_batch)
            logger.info(f"💾 Flushed {len(self.current_batch)} results (total: {self.total_written})")
            
            # Clear batch
            self.current_batch = []
        
        except Exception as e:
            logger.error(f"❌ Error flushing batch: {e}")
