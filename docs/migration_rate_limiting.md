# Migration Guide: Rate Limiting

## Overview

This guide helps you migrate to the new rate-limited version of MCP Claude Context Server.

## What's Changed

### Before (v0.5.0)
- Direct API calls without rate limiting
- Risk of hitting 429 errors during bulk operations
- No request prioritization
- Manual retry handling needed

### After (v0.5.0+)
- Automatic rate limiting on all API calls
- Smart request queuing with priorities
- Built-in retry with exponential backoff
- Real-time metrics and monitoring

## Migration Steps

### 1. Update Environment Variables

Add these new variables to your `.env` file:

```bash
# Rate limiting (optional - defaults shown)
RATE_LIMIT_PER_SECOND=3.0
RATE_LIMIT_BURST_SIZE=10
RATE_LIMIT_MAX_RETRIES=5

# Request queue (optional - defaults shown)
REQUEST_QUEUE_CONCURRENT=3
```

### 2. Update Docker Deployment

If using Docker, update your `docker-compose.yml`:

```yaml
services:
  mcp-server:
    environment:
      - RATE_LIMIT_PER_SECOND=${RATE_LIMIT_PER_SECOND:-3.0}
      - RATE_LIMIT_BURST_SIZE=${RATE_LIMIT_BURST_SIZE:-10}
```

### 3. Code Changes (if using as library)

If you're importing the server directly:

```python
# Before
server = DirectAPIClaudeContextServer()
await server.run()

# After
server = DirectAPIClaudeContextServer()
await server.start()  # Initialize rate limiter
try:
    await server.run()
finally:
    await server.stop()  # Cleanup
```

### 4. Update Bulk Operations

For bulk operations, consider using priorities:

```python
# Before - all requests equal priority
for conv_id in conversation_ids:
    await get_conversation(conv_id)

# After - use bulk operations with priority
await bulk_operations(
    operation="export",
    conversation_ids=conversation_ids,
    params={"priority": "high"}  # For user-initiated
)
```

## Testing Your Migration

### 1. Check Rate Limiting is Active

```python
# Use the new metrics tool
{
  "tool": "get_rate_limit_metrics"
}
```

Expected response shows configuration and metrics:
```json
{
  "status": "success",
  "rate_limit_config": {
    "requests_per_second": 3.0,
    "burst_size": 10
  }
}
```

### 2. Test Bulk Operation

Try listing many conversations:
```python
{
  "tool": "list_conversations",
  "arguments": {
    "session_key": "your-key",
    "org_id": "your-org",
    "limit": 100
  }
}
```

Monitor that requests are properly rate limited without errors.

### 3. Verify Metrics

After operations, check metrics:
```python
{
  "tool": "get_rate_limit_metrics",
  "arguments": {
    "endpoint": "list_conversations"
  }
}
```

## Common Issues

### Issue: "Module not found: rate_limiter"

**Solution**: Pull latest code and reinstall dependencies:
```bash
git pull
poetry install
```

### Issue: Slower bulk operations

**Expected behavior** - rate limiting prevents API overload. To speed up:
1. Increase `RATE_LIMIT_PER_SECOND` if API allows
2. Use higher priority for urgent tasks
3. Process in parallel where possible

### Issue: Memory usage increased

The queue system uses memory to track pending requests. If concerning:
1. Reduce `REQUEST_QUEUE_CONCURRENT`
2. Process in smaller batches
3. Monitor with `get_rate_limit_metrics`

## Rollback Plan

If you need to rollback:

1. Checkout previous version:
```bash
git checkout v0.5.0
```

2. Remove rate limiting imports from `direct_api_server.py`

3. Replace rate-limited session with regular session

**Note**: We recommend fixing issues rather than rolling back, as rate limiting provides important protection.

## Performance Tuning

### For Interactive Use
Optimize for responsiveness:
```bash
RATE_LIMIT_PER_SECOND=5.0  # If API allows
RATE_LIMIT_BURST_SIZE=20   # Larger burst
```

### For Background Processing
Optimize for stability:
```bash
RATE_LIMIT_PER_SECOND=2.0  # Conservative
RATE_LIMIT_BURST_SIZE=5    # Smaller burst
```

### For Shared Deployments
Balance multiple users:
```bash
RATE_LIMIT_PER_SECOND=3.0
REQUEST_QUEUE_CONCURRENT=2  # Limit concurrent
```

## Monitoring

Set up monitoring for production:

1. **Log Analysis**
   ```bash
   grep "Rate limit" logs/mcp-server.log
   ```

2. **Metrics Export**
   ```python
   # Periodic metrics collection
   metrics = await get_rate_limit_metrics()
   save_to_monitoring_system(metrics)
   ```

3. **Alerts**
   - Queue depth > 100
   - Rate limit errors > 10/minute
   - Request latency > 30s

## Next Steps

After migration:

1. Monitor metrics for a few days
2. Adjust rate limits based on usage
3. Consider implementing bulk export in Chrome extension
4. Plan for Redis-based rate limiting if scaling