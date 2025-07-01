# Rate Limiting & Request Management

## Overview

MCP Claude Context Server v0.5.0+ includes sophisticated rate limiting and request queue management to prevent API throttling and ensure reliable operation during bulk operations.

## Features

### 1. Token Bucket Rate Limiting
- **Algorithm**: Token bucket with configurable refill rate
- **Default**: 3 requests/second with burst capacity of 10
- **Automatic retry**: Exponential backoff on 429 errors
- **Per-endpoint limiting**: Different limits for different API endpoints

### 2. Priority Queue System
- **Priority levels**: CRITICAL, HIGH, NORMAL, LOW
- **Concurrent processing**: Configurable max concurrent requests
- **Fair scheduling**: Higher priority requests processed first
- **Queue metrics**: Real-time monitoring of queue status

### 3. Request Metrics & Monitoring
- **Live metrics**: Track requests per minute, total requests
- **Endpoint-specific stats**: Monitor usage by API endpoint
- **Queue depth**: Monitor pending requests
- **Error tracking**: Track rate limit hits and retries

## Configuration

### Environment Variables

```bash
# Rate limiting configuration
RATE_LIMIT_PER_SECOND=3.0      # Requests per second (default: 3.0)
RATE_LIMIT_BURST_SIZE=10       # Burst capacity (default: 10)
RATE_LIMIT_MAX_RETRIES=5       # Max retry attempts (default: 5)

# Queue configuration
REQUEST_QUEUE_CONCURRENT=3      # Max concurrent requests (default: 3)
```

### Programmatic Configuration

```python
from src.utils.rate_limiter import RateLimitConfig

config = RateLimitConfig(
    requests_per_second=3.0,
    burst_size=10,
    retry_after_header_respect=True,
    backoff_base=2.0,
    max_retries=5
)
```

## Usage Examples

### Basic Rate Limiting

All API calls to Claude.ai are automatically rate limited:

```python
# Using MCP tools - rate limiting is automatic
{
  "tool": "list_conversations",
  "arguments": {
    "session_key": "sk-ant-...",
    "org_id": "org-...",
    "limit": 50
  }
}
```

### Bulk Operations with Priority

When performing bulk operations, requests are automatically queued:

```python
# High priority - user-initiated action
{
  "tool": "bulk_operations",
  "arguments": {
    "operation": "export",
    "conversation_ids": ["id1", "id2", "id3"],
    "params": {"priority": "high"}
  }
}
```

### Monitoring Rate Limits

Use the new tool to check rate limiting status:

```python
# Get overall metrics
{
  "tool": "get_rate_limit_metrics"
}

# Get metrics for specific endpoint
{
  "tool": "get_rate_limit_metrics",
  "arguments": {
    "endpoint": "list_conversations"
  }
}
```

## Rate Limit Strategies

### 1. Burst Strategy
Best for interactive operations where users expect quick responses:
- Use full burst capacity for initial requests
- Smooth out to sustained rate afterwards
- Good for: Listing conversations, single exports

### 2. Steady Strategy
Best for background operations:
- Maintain consistent request rate
- Avoid bursts to preserve capacity
- Good for: Bulk sync, large exports

### 3. Priority Strategy
Best for mixed workloads:
- Critical requests bypass queue
- Background tasks use remaining capacity
- Good for: Multi-user environments

## Handling Rate Limits

### Automatic Handling
The rate limiter automatically:
1. Delays requests to stay within limits
2. Retries on 429 errors with exponential backoff
3. Respects Retry-After headers from API
4. Tracks metrics for monitoring

### Manual Handling
For custom rate limit handling:

```python
from src.utils.rate_limiter import RateLimiter

# Check current capacity
metrics = rate_limiter.get_metrics("endpoint")
if metrics["requests_per_minute"] > 150:
    # Slow down or pause operations
    await asyncio.sleep(60)
```

## Best Practices

### 1. Use Priority Appropriately
- **CRITICAL**: User waiting for immediate response
- **HIGH**: User-initiated batch operations
- **NORMAL**: Standard automated tasks
- **LOW**: Background sync, cleanup tasks

### 2. Monitor Queue Depth
```python
metrics = await get_rate_limit_metrics()
if metrics["summary"]["total_queued"] > 100:
    # Consider pausing non-critical operations
    pass
```

### 3. Batch Operations
Instead of many small requests, batch when possible:
```python
# Good - single bulk operation
await bulk_operations("export", conversation_ids[:50])

# Less optimal - individual requests
for conv_id in conversation_ids[:50]:
    await get_conversation(conv_id)
```

### 4. Set Reasonable Timeouts
For bulk operations, increase timeouts:
```python
# For bulk export of 100+ conversations
response = await rate_limited_session.get(url, timeout=300)  # 5 minutes
```

## Troubleshooting

### Common Issues

1. **"Rate limit exceeded" errors**
   - Check `RATE_LIMIT_PER_SECOND` setting
   - Monitor with `get_rate_limit_metrics` tool
   - Reduce concurrent operations

2. **Slow bulk operations**
   - Increase `RATE_LIMIT_PER_SECOND` if API allows
   - Use higher priority for urgent tasks
   - Check queue depth isn't too high

3. **Memory usage during bulk ops**
   - Queue has built-in limits
   - Consider processing in smaller batches
   - Monitor system resources

### Debug Mode

Enable debug logging for detailed rate limit info:

```bash
LOG_LEVEL=DEBUG poetry run python -m src.direct_api_server
```

This will show:
- Token bucket state changes
- Queue operations
- Retry attempts
- Metric updates

## API Endpoint Limits

Based on testing, Claude.ai endpoints have different characteristics:

| Endpoint | Observed Limit | Burst Tolerance | Notes |
|----------|---------------|-----------------|-------|
| `/conversations` | ~3-5 req/s | High | List operations |
| `/conversations/{id}` | ~2-3 req/s | Medium | Individual fetches |
| `/search` | ~1-2 req/s | Low | Resource intensive |

**Note**: These are observed limits and may change. The rate limiter adapts automatically to 429 responses.

## Integration with Chrome Extension

The rate limiting system integrates with the planned bulk export feature:

1. Extension initiates bulk export
2. Server queues all conversations with HIGH priority
3. Rate limiter ensures API compliance
4. Progress updates sent back to extension
5. Extension shows progress bar to user

## Future Enhancements

Planned improvements for rate limiting:

1. **Adaptive Rate Limiting**: Automatically adjust limits based on API responses
2. **Cost Tracking**: Monitor API usage costs
3. **User Quotas**: Per-user rate limits for shared deployments
4. **Circuit Breaker**: Temporary disable on repeated failures
5. **Redis Backend**: Distributed rate limiting for multi-instance deployments