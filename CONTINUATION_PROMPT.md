# MCP Claude Context - Continuation Prompt

## Project Status Summary

I've built an MCP Claude Context server that extracts conversations from Claude.ai. The project has two main components working together:

1. **MCP Server (v0.2.0)** - Uses direct API access to list conversations
2. **Chrome Extension + Bridge Server** - Extracts full message content from the DOM

### What's Working:
- ✅ Direct API access to list conversations (bypassed Cloudflare blocking)
- ✅ Chrome extension successfully extracts messages from Claude.ai
- ✅ Bridge server saves conversations locally with metadata and full content
- ✅ Export functionality (JSON/CSV) for conversation lists
- ✅ No rate limiting detected (~3 req/sec sustainable)

### Key Files:
- `src/direct_api_server.py` - Main MCP server using direct API
- `extension/` - Chrome extension for message extraction
- `extension/bridge_server.py` - Local server receiving extracted data
- `/extracted_messages/` - Where conversations are stored

### Current Limitations:
- Claude.ai API doesn't expose message content (only metadata)
- Chrome extension required for full message extraction
- Title extraction needs improvement (often shows "Untitled")

## Continuation Tasks

### 1. **Improve Message Extraction**
```
The Chrome extension currently extracts messages but has issues with:
- Title detection (shows "Untitled Conversation" often)
- Role detection (some messages marked as "UNKNOWN")
- Code block formatting preservation

Please improve the content.js selectors to better extract:
1. Conversation titles from the current Claude UI
2. User vs Assistant role detection
3. Code blocks with proper formatting
4. Timestamps if available in the DOM
```

### 2. **Add Bulk Export Feature**
```
Currently users must extract one conversation at a time. Add:
1. "Extract All Conversations" button to extension
2. Iterate through conversation list in sidebar
3. Navigate to each and extract messages
4. Progress indicator in popup.html
5. Batch sending to bridge server
```

### 3. **Integrate Extracted Messages with MCP Server**
```
The MCP server and Chrome extension work separately. Integrate them:
1. Add new MCP tool: get_conversation_messages
2. Read from /extracted_messages/ directory
3. Return full conversation with messages
4. Cache in memory for performance
5. Add search across message content
```

### 4. **Add Real-time Monitoring**
```
Implement auto-sync for new messages:
1. Use MutationObserver in content.js (already started)
2. Detect new messages added to conversation
3. Auto-append to existing extracted data
4. Optional: WebSocket connection for real-time updates
```

### 5. **Improve Authentication**
```
Current session key expires. Implement:
1. Session key refresh mechanism
2. Detection of expired sessions
3. Prompt user to re-authenticate
4. Store encrypted credentials safely
```

### 6. **Analytics Dashboard**
```
Create insights from extracted conversations:
1. Conversation frequency over time
2. Average message length
3. Topic clustering
4. Token usage estimates
5. Export as HTML report
```

## Technical Context

### API Endpoints Found:
- `/api/organizations/{org_id}/chat_conversations` - Lists conversations (working)
- `/api/account` - User account info
- `/api/bootstrap` - Initial app data
- No message content endpoints found (need DOM extraction)

### Architecture:
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude.ai Web  │────▶│ Chrome Extension │────▶│  Bridge Server  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                            │
                                                            ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   MCP Client    │◀────│    MCP Server    │◀────│ Extracted Data  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Session Info for Testing:
- session_key: YOUR_SESSION_KEY_HERE
- org_id: YOUR_ORG_ID_HERE
- Test conversation: YOUR_CONVERSATION_ID_HERE

## Development Commands

```bash
# Install dependencies
poetry install

# Run MCP server
poetry run python -m src.direct_api_server

# Run bridge server
poetry run python extension/bridge_server.py

# Run tests
poetry run pytest tests/

# Check API endpoints
poetry run python discover_api.py SESSION_KEY ORG_ID
```

## Priority Recommendation

Start with **Task 3** (Integrate Extracted Messages with MCP Server) as it provides the most immediate value - allowing MCP tools to access full conversation content that's already been extracted.

Then move to **Task 2** (Bulk Export) to make it easier for users to backup all their conversations at once.

Good luck with the continuation! The foundation is solid and working well.