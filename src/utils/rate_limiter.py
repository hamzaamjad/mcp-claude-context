"""
Rate limiting implementation for Claude.ai API requests.
Implements token bucket algorithm with configurable limits.
"""

import asyncio
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 3.0
    burst_size: int = 10
    retry_after_header_respect: bool = True
    backoff_base: float = 2.0
    max_retries: int = 5
    

@dataclass
class TokenBucket:
    """Token bucket implementation for rate limiting."""
    capacity: float
    refill_rate: float
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    
    def __post_init__(self):
        self.tokens = self.capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> tuple[bool, float]:
        """
        Try to consume tokens from the bucket.
        Returns (success, wait_time_if_failed).
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0
        
        # Calculate wait time needed
        tokens_needed = tokens - self.tokens
        wait_time = tokens_needed / self.refill_rate
        return False, wait_time
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on refill rate
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now


class RateLimiter:
    """
    Rate limiter for API requests with per-endpoint limiting.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=self.config.burst_size,
                refill_rate=self.config.requests_per_second
            )
        )
        self._request_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._lock = asyncio.Lock()
    
    async def acquire(self, endpoint: str = "default", tokens: int = 1) -> None:
        """
        Acquire permission to make a request. Blocks if rate limit exceeded.
        
        Args:
            endpoint: The API endpoint or resource identifier
            tokens: Number of tokens to consume (default: 1)
        """
        async with self._lock:
            bucket = self._buckets[endpoint]
            
            while True:
                success, wait_time = bucket.consume(tokens)
                
                if success:
                    # Track metrics
                    self._update_metrics(endpoint, "acquired")
                    logger.debug(f"Rate limit acquired for {endpoint}, tokens remaining: {bucket.tokens:.2f}")
                    return
                
                # Wait before retrying
                logger.info(f"Rate limit exceeded for {endpoint}, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
    
    def _update_metrics(self, endpoint: str, event: str):
        """Update request metrics for monitoring."""
        now = time.time()
        metrics = self._request_metrics[endpoint]
        
        if event == "acquired":
            metrics["last_request"] = now
            metrics["total_requests"] = metrics.get("total_requests", 0) + 1
            
            # Track request rate over last minute
            minute_ago = now - 60
            recent_requests = metrics.get("recent_requests", [])
            recent_requests = [t for t in recent_requests if t > minute_ago]
            recent_requests.append(now)
            metrics["recent_requests"] = recent_requests
            metrics["requests_per_minute"] = len(recent_requests)
    
    def get_metrics(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get rate limiting metrics for monitoring."""
        if endpoint:
            return dict(self._request_metrics.get(endpoint, {}))
        
        # Return all metrics
        return {
            ep: dict(metrics) 
            for ep, metrics in self._request_metrics.items()
        }
    
    def reset(self, endpoint: Optional[str] = None):
        """Reset rate limiter state for endpoint(s)."""
        if endpoint:
            if endpoint in self._buckets:
                del self._buckets[endpoint]
            if endpoint in self._request_metrics:
                del self._request_metrics[endpoint]
        else:
            # Reset all
            self._buckets.clear()
            self._request_metrics.clear()


class RateLimitedSession:
    """
    Wrapper around requests.Session with built-in rate limiting.
    """
    
    def __init__(self, session, rate_limiter: RateLimiter):
        self.session = session
        self.rate_limiter = rate_limiter
        self._retry_count = defaultdict(int)
    
    async def request(self, method: str, url: str, **kwargs) -> Any:
        """
        Make a rate-limited request with automatic retry on 429.
        """
        endpoint = self._extract_endpoint(url)
        retries = 0
        
        while retries <= self.rate_limiter.config.max_retries:
            # Acquire rate limit token
            await self.rate_limiter.acquire(endpoint)
            
            try:
                # Make the actual request
                response = await asyncio.to_thread(
                    self.session.request, method, url, **kwargs
                )
                
                # Check for rate limit response
                if response.status_code == 429:
                    retry_after = self._get_retry_after(response)
                    logger.warning(f"Rate limit hit for {endpoint}, retry after {retry_after}s")
                    
                    if retries < self.rate_limiter.config.max_retries:
                        # Exponential backoff
                        backoff = self.rate_limiter.config.backoff_base ** retries
                        wait_time = max(retry_after, backoff)
                        
                        logger.info(f"Retrying request to {endpoint} after {wait_time}s (attempt {retries + 1})")
                        await asyncio.sleep(wait_time)
                        retries += 1
                        continue
                    else:
                        logger.error(f"Max retries exceeded for {endpoint}")
                        response.raise_for_status()
                
                # Reset retry count on success
                self._retry_count[endpoint] = 0
                return response
                
            except Exception as e:
                logger.error(f"Request failed for {endpoint}: {e}")
                raise
        
        raise Exception(f"Max retries exceeded for {endpoint}")
    
    def _extract_endpoint(self, url: str) -> str:
        """Extract endpoint identifier from URL."""
        # Simple extraction - can be enhanced based on URL patterns
        if "conversations" in url:
            if url.endswith("/conversations"):
                return "list_conversations"
            elif "/conversations/" in url:
                return "get_conversation"
        elif "search" in url:
            return "search"
        
        return "default"
    
    def _get_retry_after(self, response) -> float:
        """Extract retry-after value from response headers."""
        if self.rate_limiter.config.retry_after_header_respect:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    pass
        
        return 1.0  # Default retry after 1 second
    
    # Convenience methods
    async def get(self, url: str, **kwargs):
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs):
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs):
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs):
        return await self.request("DELETE", url, **kwargs)