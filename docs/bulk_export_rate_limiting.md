# Chrome Extension Bulk Export with Rate Limiting

## Overview

The Chrome extension now includes integrated rate limiting to prevent overwhelming the bridge server and Claude.ai when performing bulk exports. This ensures stable operation even when exporting hundreds of conversations.

## Rate Limiting Architecture

### Server-Side Rate Limiting (Bridge Server)
- **Location**: `extension/bridge_server.py`
- **Algorithm**: Token bucket with configurable limits
- **Default Limits**: 
  - 3 requests per second
  - Burst capacity of 10 requests
- **Implementation**: Middleware that intercepts all API requests

### Client-Side Rate Limiting (Chrome Extension)
- **Location**: `extension/content.js`
- **Purpose**: Prevents overwhelming the bridge server
- **Coordination**: Works in tandem with server-side limits

## Key Features

### 1. Rate Limited Endpoints
All bridge server API endpoints are rate limited:
- `POST /api/conversation` - Save conversation metadata
- `POST /api/messages` - Save conversation messages
- `GET /api/conversations` - List conversations
- `GET /api/conversations/{id}` - Check if conversation exists

### 2. Rate Limit Headers
The server returns standard rate limit headers:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1704067200
```

### 3. Automatic Retry Logic
When rate limits are hit (429 response):
- Client waits for the `Retry-After` duration
- Automatically retries the request
- Exponential backoff for repeated failures

### 4. Rate Limit Monitoring
Check current rate limit status:
- Click "Check Rate Limits" in the extension popup
- View real-time token availability per endpoint
- Visual indicators show capacity usage

## Usage

### Starting Bulk Export
1. Navigate to Claude.ai
2. Click the extension icon
3. Click "Extract All Conversations"
4. The export will automatically respect rate limits

### Configuration Options
In `extension/popup.html`:
- **Skip existing**: Avoid re-extracting conversations
- **Auto-scroll**: Navigate through conversation list
- **Delay between**: Additional delay between extractions (1-10 seconds)

### Monitoring Progress
The extension shows:
- Progress bar with percentage complete
- Current conversation being extracted
- Count of completed/skipped/failed extractions
- Rate limit status when checked

## Performance Considerations

### Optimal Settings
- **Small exports (<50 conversations)**: Use default 2-second delay
- **Large exports (>100 conversations)**: Increase delay to 3-5 seconds
- **Very large exports (>500)**: Consider running in batches

### Expected Throughput
With default rate limits:
- Maximum: 3 conversations per second
- Typical: 1-2 conversations per second (with navigation time)
- Large export (1000 conversations): ~15-20 minutes

## Error Handling

### Rate Limit Errors
- Automatically handled with retry logic
- Maximum 5 retries per request
- Exponential backoff prevents thundering herd

### Network Failures
- Graceful degradation on connection loss
- Progress saved, can resume from last position
- Failed extractions tracked separately

## API Reference

### Bridge Server Rate Limit Status
```
GET http://localhost:8765/api/rate-limit-status

Response:
{
  "status": "success",
  "rate_limits": {
    "requests_per_second": 3,
    "burst_size": 10
  },
  "endpoints": {
    "POST:messages": {
      "tokens_available": 7.5,
      "capacity": 10,
      "refill_rate": 3,
      "metrics": {
        "last_request": 1704067123,
        "total_requests": 42,
        "requests_per_minute": 12
      }
    }
  }
}
```

### Client-Side Rate Limiter
```javascript
// Create rate limiter instance
const rateLimiter = new ContentScriptRateLimiter(3, 10);

// Acquire token before making request
await rateLimiter.acquire();

// Make rate-limited request
const response = await fetch(url, options);
```

## Troubleshooting

### "Rate limit exceeded" errors
- Check rate limit status in popup
- Increase delay between extractions
- Ensure bridge server is not overloaded

### Slow extraction speed
- Normal for large exports
- Check network connection
- Verify bridge server is running locally

### Extraction stops unexpectedly
- Check browser console for errors
- Verify Claude.ai session is active
- Restart bridge server if needed

## Best Practices

1. **Start small**: Test with a few conversations first
2. **Monitor progress**: Keep popup open to track status
3. **Run during off-hours**: For very large exports
4. **Backup regularly**: Extracted data is stored locally
5. **Check rate limits**: Before starting large exports

## Technical Details

### Token Bucket Algorithm
- Tokens refill at configured rate (3/second)
- Burst capacity allows temporary spikes
- Empty bucket = request must wait
- Fair queuing ensures order preservation

### Integration Points
1. **Bridge Server**: Rate limiting middleware
2. **Content Script**: Client-side rate limiter
3. **Background Script**: Coordination and retry logic
4. **Popup UI**: Status display and controls

### Future Enhancements
- Adaptive rate limiting based on server load
- Priority queues for critical requests
- WebSocket support for real-time updates
- Distributed rate limiting for multiple clients