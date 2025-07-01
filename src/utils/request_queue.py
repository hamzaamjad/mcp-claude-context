"""
Priority queue system for managing API requests with different priority levels.
"""

import asyncio
import time
from typing import Optional, Any, Callable, Dict
from dataclasses import dataclass, field
from enum import Enum
import heapq
import uuid
import logging

logger = logging.getLogger(__name__)


class RequestPriority(Enum):
    """Priority levels for requests."""
    CRITICAL = 1  # Highest priority - user-initiated actions
    HIGH = 2      # Important background tasks
    NORMAL = 3    # Standard requests
    LOW = 4       # Background sync, non-urgent tasks
    

@dataclass
class QueuedRequest:
    """Represents a queued request with priority."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: RequestPriority = RequestPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    callback: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    result_future: asyncio.Future = field(default_factory=asyncio.Future)
    
    def __lt__(self, other):
        """Compare by priority, then by creation time."""
        if self.priority.value == other.priority.value:
            return self.created_at < other.created_at
        return self.priority.value < other.priority.value


class RequestQueue:
    """
    Priority queue for managing API requests.
    Ensures high-priority requests are processed first.
    """
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._queue: list[QueuedRequest] = []
        self._active_requests: Dict[str, QueuedRequest] = {}
        self._lock = asyncio.Lock()
        self._worker_task: Optional[asyncio.Task] = None
        self._shutdown = False
        self._metrics = {
            "queued": 0,
            "processed": 0,
            "failed": 0,
            "active": 0,
            "by_priority": {p.name: 0 for p in RequestPriority}
        }
    
    async def start(self):
        """Start the queue worker."""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("Request queue worker started")
    
    async def stop(self):
        """Stop the queue worker gracefully."""
        self._shutdown = True
        if self._worker_task:
            await self._worker_task
        logger.info("Request queue worker stopped")
    
    async def enqueue(
        self, 
        callback: Callable,
        *args,
        priority: RequestPriority = RequestPriority.NORMAL,
        **kwargs
    ) -> Any:
        """
        Add a request to the queue and wait for result.
        
        Args:
            callback: The async function to call
            priority: Request priority level
            *args, **kwargs: Arguments for the callback
            
        Returns:
            The result of the callback execution
        """
        request = QueuedRequest(
            priority=priority,
            callback=callback,
            args=args,
            kwargs=kwargs
        )
        
        async with self._lock:
            heapq.heappush(self._queue, request)
            self._metrics["queued"] += 1
            self._metrics["by_priority"][priority.name] += 1
            
        logger.debug(f"Request {request.id} queued with priority {priority.name}")
        
        # Wait for the result
        try:
            return await request.result_future
        except Exception as e:
            logger.error(f"Request {request.id} failed: {e}")
            raise
    
    async def _worker(self):
        """Worker coroutine that processes requests from the queue."""
        logger.info("Request queue worker starting")
        
        while not self._shutdown:
            try:
                # Check if we can process more requests
                if len(self._active_requests) >= self.max_concurrent:
                    await asyncio.sleep(0.1)
                    continue
                
                # Get next request from queue
                request = await self._get_next_request()
                if request is None:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process the request
                asyncio.create_task(self._process_request(request))
                
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)
        
        # Wait for active requests to complete
        while self._active_requests:
            logger.info(f"Waiting for {len(self._active_requests)} active requests to complete")
            await asyncio.sleep(1)
        
        logger.info("Request queue worker stopped")
    
    async def _get_next_request(self) -> Optional[QueuedRequest]:
        """Get the next request from the priority queue."""
        async with self._lock:
            if not self._queue:
                return None
            
            request = heapq.heappop(self._queue)
            self._active_requests[request.id] = request
            self._metrics["active"] = len(self._active_requests)
            
            # Log queue status
            wait_time = time.time() - request.created_at
            logger.info(
                f"Processing request {request.id} "
                f"(priority: {request.priority.name}, "
                f"waited: {wait_time:.2f}s, "
                f"queue size: {len(self._queue)})"
            )
            
            return request
    
    async def _process_request(self, request: QueuedRequest):
        """Process a single request."""
        try:
            # Execute the callback
            result = await request.callback(*request.args, **request.kwargs)
            
            # Set the result
            request.result_future.set_result(result)
            
            # Update metrics
            async with self._lock:
                self._metrics["processed"] += 1
                
            logger.debug(f"Request {request.id} completed successfully")
            
        except Exception as e:
            # Set the exception
            request.result_future.set_exception(e)
            
            # Update metrics
            async with self._lock:
                self._metrics["failed"] += 1
                
            logger.error(f"Request {request.id} failed: {e}")
            
        finally:
            # Remove from active requests
            async with self._lock:
                self._active_requests.pop(request.id, None)
                self._metrics["active"] = len(self._active_requests)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get queue metrics for monitoring."""
        return {
            **self._metrics,
            "queue_size": len(self._queue),
            "active_count": len(self._active_requests),
            "oldest_waiting": self._get_oldest_waiting_time()
        }
    
    def _get_oldest_waiting_time(self) -> Optional[float]:
        """Get the wait time of the oldest request in queue."""
        if not self._queue:
            return None
        
        oldest = min(self._queue, key=lambda r: r.created_at)
        return time.time() - oldest.created_at
    
    async def clear(self, priority: Optional[RequestPriority] = None):
        """
        Clear requests from the queue.
        
        Args:
            priority: If specified, only clear requests with this priority
        """
        async with self._lock:
            if priority is None:
                # Clear all
                for request in self._queue:
                    request.result_future.cancel()
                self._queue.clear()
                logger.info("Cleared all requests from queue")
            else:
                # Clear specific priority
                remaining = []
                cleared = 0
                
                for request in self._queue:
                    if request.priority == priority:
                        request.result_future.cancel()
                        cleared += 1
                    else:
                        remaining.append(request)
                
                self._queue = remaining
                heapq.heapify(self._queue)
                logger.info(f"Cleared {cleared} {priority.name} priority requests from queue")


class RequestQueueManager:
    """
    Manager for multiple request queues (e.g., per endpoint).
    """
    
    def __init__(self, default_max_concurrent: int = 3):
        self.default_max_concurrent = default_max_concurrent
        self._queues: Dict[str, RequestQueue] = {}
        self._started = False
    
    async def start(self):
        """Start all queues."""
        for queue in self._queues.values():
            await queue.start()
        self._started = True
        logger.info("Request queue manager started")
    
    async def stop(self):
        """Stop all queues."""
        for queue in self._queues.values():
            await queue.stop()
        self._started = False
        logger.info("Request queue manager stopped")
    
    def get_queue(self, name: str = "default") -> RequestQueue:
        """Get or create a queue by name."""
        if name not in self._queues:
            queue = RequestQueue(self.default_max_concurrent)
            self._queues[name] = queue
            
            if self._started:
                # Start the queue if manager is already running
                asyncio.create_task(queue.start())
        
        return self._queues[name]
    
    async def enqueue(
        self,
        callback: Callable,
        *args,
        queue_name: str = "default",
        priority: RequestPriority = RequestPriority.NORMAL,
        **kwargs
    ) -> Any:
        """Enqueue a request to a specific queue."""
        queue = self.get_queue(queue_name)
        return await queue.enqueue(callback, *args, priority=priority, **kwargs)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all queues."""
        return {
            name: queue.get_metrics()
            for name, queue in self._queues.items()
        }