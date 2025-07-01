"""Utility functions for MCP Claude Context server."""

import asyncio
import logging
from typing import TypeVar, Callable, Optional, Any
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0
) -> T:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        max_delay: Maximum delay between retries
        
    Returns:
        Result of the function call
        
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    f"Attempt {attempt + 1} failed: {str(e)}. "
                    f"Retrying in {delay:.1f} seconds..."
                )
                await asyncio.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed. Last error: {str(e)}")
    
    raise last_exception


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0
):
    """
    Decorator to add retry logic to async functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        max_delay: Maximum delay between retries
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                initial_delay=initial_delay,
                backoff_factor=backoff_factor,
                max_delay=max_delay
            )
        return wrapper
    return decorator


class MCPError(Exception):
    """Base exception for MCP Claude Context errors."""
    pass


class ExtractionError(MCPError):
    """Error during conversation extraction."""
    pass


class AuthenticationError(MCPError):
    """Authentication error with Claude.ai."""
    pass


class RateLimitError(MCPError):
    """Rate limit exceeded error."""
    pass


def sanitize_url(url: str) -> str:
    """
    Sanitize and validate Claude.ai conversation URL.
    
    Args:
        url: URL to sanitize
        
    Returns:
        Sanitized URL
        
    Raises:
        ValueError: If URL is invalid
    """
    if not url:
        raise ValueError("URL cannot be empty")
    
    # Ensure it's a Claude.ai URL
    if not (url.startswith("https://claude.ai/") or url.startswith("http://claude.ai/")):
        raise ValueError("URL must be a claude.ai conversation URL")
    
    # Ensure HTTPS
    if url.startswith("http://"):
        url = url.replace("http://", "https://", 1)
    
    return url.strip()