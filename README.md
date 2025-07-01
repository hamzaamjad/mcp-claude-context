# MCP Claude Context Server

Extract and access Claude.ai conversations via Model Context Protocol.

## Features

### Version 0.3.0
- ✅ Direct API access for listing conversations (bypassed Cloudflare)
- ✅ Chrome extension for extracting full message content
- ✅ Bridge server for saving conversations locally
- ✅ MCP tools for accessing extracted messages
- ✅ Search functionality across all message content
- ✅ Export conversations to JSON/CSV formats

## Architecture

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

## Available MCP Tools

### API-based Tools (require session_key and org_id)
- `list_conversations` - List all conversations from Claude.ai
- `get_conversation` - Get conversation metadata (no messages)
- `search_conversations` - Search conversations by title
- `export_conversations` - Export conversation list to JSON/CSV

### Local Data Tools (work with extracted messages)
- `get_conversation_messages` - Get full conversation with messages
- `search_messages` - Search through all extracted message content

## Quick Start

1. Install dependencies:
```bash
poetry install
```

2. Run the MCP server:
```bash
poetry run python -m src.direct_api_server
```

3. Run the bridge server (in another terminal):
```bash
poetry run python extension/bridge_server.py
```

4. Install the Chrome extension:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" and select the `extension/` directory

5. Extract conversations:
   - Go to Claude.ai and log in
   - Click the extension icon
   - Navigate to a conversation
   - Click "Extract Current Conversation"

## Usage Examples

### List conversations (API):
```json
{
  "tool": "list_conversations",
  "arguments": {
    "session_key": "YOUR_SESSION_KEY",
    "org_id": "YOUR_ORG_ID",
    "limit": 50
  }
}
```

### Get conversation with messages (local):
```json
{
  "tool": "get_conversation_messages",
  "arguments": {
    "conversation_id": "5b585cbe-7982-425a-97c5-d828f39dc37a"
  }
}
```

### Search messages:
```json
{
  "tool": "search_messages",
  "arguments": {
    "query": "Python",
    "case_sensitive": false,
    "limit": 20
  }
}
```

## Technical Details

- **Session Key**: Found in browser cookies after logging into Claude.ai
- **Organization ID**: Found in API responses or URL parameters
- **Extracted Data**: Stored in `/extracted_messages/` directory
- **Rate Limiting**: ~3 requests/second is sustainable for API calls