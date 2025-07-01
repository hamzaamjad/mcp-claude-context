"""
Example demonstrating rate-limited bulk operations.
This shows how the rate limiting prevents API overload during bulk exports.
"""

import asyncio
import json
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.rate_limiter import RateLimiter, RateLimitConfig, RateLimitedSession
from src.utils.request_queue import RequestQueue, RequestPriority, RequestQueueManager
import requests


async def demonstrate_rate_limiting():
    """Demonstrate rate limiting with mock API calls."""
    print("=== Rate Limiting Demonstration ===\n")
    
    # Configure rate limiting
    config = RateLimitConfig(
        requests_per_second=3.0,  # 3 requests per second
        burst_size=5,             # Allow burst of 5 requests
        max_retries=3
    )
    
    rate_limiter = RateLimiter(config)
    session = requests.Session()
    rate_limited_session = RateLimitedSession(session, rate_limiter)
    
    # Mock API endpoint (httpbin for testing)
    test_url = "https://httpbin.org/delay/0"
    
    print(f"Configuration:")
    print(f"- Rate limit: {config.requests_per_second} requests/second")
    print(f"- Burst size: {config.burst_size} requests")
    print(f"- Making 10 test requests...\n")
    
    # Track timing
    start_time = time.time()
    request_times = []
    
    # Make 10 requests
    for i in range(10):
        request_start = time.time()
        
        try:
            # Make rate-limited request
            response = await rate_limited_session.get(test_url)
            
            request_time = time.time() - request_start
            request_times.append(request_time)
            
            print(f"Request {i+1}: {response.status_code} - Time: {request_time:.2f}s")
            
            # Show metrics every 5 requests
            if (i + 1) % 5 == 0:
                metrics = rate_limiter.get_metrics("default")
                print(f"\nMetrics after {i+1} requests:")
                print(f"- Total requests: {metrics.get('total_requests', 0)}")
                print(f"- Requests/minute: {metrics.get('requests_per_minute', 0)}")
                print()
                
        except Exception as e:
            print(f"Request {i+1} failed: {e}")
    
    total_time = time.time() - start_time
    
    print(f"\n=== Summary ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average time per request: {sum(request_times)/len(request_times):.2f}s")
    print(f"Effective rate: {len(request_times)/total_time:.2f} requests/second")
    
    # Final metrics
    final_metrics = rate_limiter.get_metrics()
    print(f"\nFinal metrics:")
    print(json.dumps(final_metrics, indent=2))


async def demonstrate_priority_queue():
    """Demonstrate priority queue for bulk operations."""
    print("\n\n=== Priority Queue Demonstration ===\n")
    
    queue_manager = RequestQueueManager(default_max_concurrent=2)
    await queue_manager.start()
    
    # Simulate different types of operations
    async def simulate_operation(op_type: str, op_id: int, duration: float):
        print(f"[{time.strftime('%H:%M:%S')}] Starting {op_type} operation {op_id}")
        await asyncio.sleep(duration)
        print(f"[{time.strftime('%H:%M:%S')}] Completed {op_type} operation {op_id}")
        return f"{op_type}-{op_id}"
    
    try:
        print("Queuing operations with different priorities...\n")
        
        # Queue operations with different priorities
        tasks = [
            # Low priority - background sync
            queue_manager.enqueue(
                simulate_operation, "sync", 1, 1.0,
                priority=RequestPriority.LOW
            ),
            queue_manager.enqueue(
                simulate_operation, "sync", 2, 1.0,
                priority=RequestPriority.LOW
            ),
            
            # Normal priority - regular exports
            queue_manager.enqueue(
                simulate_operation, "export", 1, 0.5,
                priority=RequestPriority.NORMAL
            ),
            queue_manager.enqueue(
                simulate_operation, "export", 2, 0.5,
                priority=RequestPriority.NORMAL
            ),
            
            # High priority - user-initiated
            queue_manager.enqueue(
                simulate_operation, "user", 1, 0.3,
                priority=RequestPriority.HIGH
            ),
            
            # Critical - immediate action needed
            queue_manager.enqueue(
                simulate_operation, "critical", 1, 0.2,
                priority=RequestPriority.CRITICAL
            ),
        ]
        
        print(f"Queued {len(tasks)} operations")
        print("Watch the execution order - higher priority tasks execute first\n")
        
        # Wait for all tasks
        results = await asyncio.gather(*tasks)
        
        print(f"\nAll operations completed. Results: {results}")
        
        # Show queue metrics
        metrics = queue_manager.get_all_metrics()
        print("\nQueue metrics:")
        print(json.dumps(metrics, indent=2))
        
    finally:
        await queue_manager.stop()


async def demonstrate_bulk_export_scenario():
    """Demonstrate a realistic bulk export scenario with rate limiting."""
    print("\n\n=== Bulk Export Scenario ===\n")
    
    # Setup
    config = RateLimitConfig(
        requests_per_second=3.0,
        burst_size=5
    )
    rate_limiter = RateLimiter(config)
    queue_manager = RequestQueueManager(default_max_concurrent=3)
    await queue_manager.start()
    
    # Simulate fetching conversation details
    async def fetch_conversation(conv_id: str, priority: RequestPriority):
        # Acquire rate limit
        await rate_limiter.acquire("conversations")
        
        # Simulate API call
        await asyncio.sleep(0.1)
        
        return {
            "id": conv_id,
            "title": f"Conversation {conv_id}",
            "messages": 10,
            "fetched_at": time.time()
        }
    
    try:
        print("Simulating bulk export of 20 conversations...")
        print("- First 5 are high priority (user selected)")
        print("- Next 15 are normal priority (background sync)\n")
        
        # Create tasks
        tasks = []
        
        # High priority conversations (user selected)
        for i in range(1, 6):
            task = queue_manager.enqueue(
                fetch_conversation, f"high-{i}", RequestPriority.HIGH,
                priority=RequestPriority.HIGH
            )
            tasks.append(task)
        
        # Normal priority conversations (background)
        for i in range(1, 16):
            task = queue_manager.enqueue(
                fetch_conversation, f"normal-{i}", RequestPriority.NORMAL,
                priority=RequestPriority.NORMAL
            )
            tasks.append(task)
        
        # Track progress
        start_time = time.time()
        completed = 0
        
        # Wait with progress updates
        for task in asyncio.as_completed(tasks):
            result = await task
            completed += 1
            elapsed = time.time() - start_time
            rate = completed / elapsed if elapsed > 0 else 0
            
            print(f"[{completed}/20] Fetched {result['id']} - Rate: {rate:.2f} conv/s")
        
        total_time = time.time() - start_time
        
        print(f"\n=== Bulk Export Complete ===")
        print(f"Total conversations: 20")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average rate: {20/total_time:.2f} conversations/second")
        
        # Show rate limiter metrics
        metrics = rate_limiter.get_metrics("conversations")
        print(f"\nRate limiter metrics:")
        print(f"- Total requests: {metrics.get('total_requests', 0)}")
        print(f"- Requests/minute: {metrics.get('requests_per_minute', 0)}")
        
    finally:
        await queue_manager.stop()


async def main():
    """Run all demonstrations."""
    await demonstrate_rate_limiting()
    await demonstrate_priority_queue()
    await demonstrate_bulk_export_scenario()


if __name__ == "__main__":
    print("MCP Claude Context - Rate Limiting Examples")
    print("==========================================\n")
    asyncio.run(main())