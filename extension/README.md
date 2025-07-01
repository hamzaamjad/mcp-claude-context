# Claude Context Bridge - Browser Extension

A Chrome extension that bridges Claude.ai web interface with the local MCP server to enable complete message extraction.

## Overview

Since Claude.ai's API doesn't provide direct access to conversation messages, this browser extension extracts data directly from the web interface DOM and sends it to a local bridge server, which then feeds it into the MCP ecosystem.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Claude.ai     │────▶│ Content Script   │────▶│ Local Bridge    │
│  Web Interface  │     │ (Extension)      │     │ Server (8765)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │   MCP Server    │
                                                  │ (Claude Context)│
                                                  └─────────────────┘
```

## Features

1. **Conversation List Extraction**
   - Extracts all conversations from the sidebar
   - Captures conversation IDs, names, and URLs

2. **Message Extraction**
   - Extracts all messages from the current conversation
   - Preserves message roles (user/assistant)
   - Captures code blocks and formatting

3. **Real-time Monitoring**
   - Monitors DOM changes for new messages
   - Optional auto-sync to local server

4. **Local Bridge Server**
   - Receives data from extension
   - Stores in local database
   - Provides MCP-compatible interface

## Installation

### 1. Install the Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `/Users/hamzaamjad/mcp-claude-context/extension` directory

### 2. Set Up Local Bridge Server

```bash
cd /Users/hamzaamjad/mcp-claude-context
python bridge_server.py
```

### 3. Configure MCP Server

The MCP server can now access complete conversation data through the local bridge.

## Usage

### Manual Extraction

1. Navigate to Claude.ai
2. Click the extension icon
3. Choose extraction options:
   - "Extract Current Conversation"
   - "Extract All Conversations"
   - "Sync to Local Server"

### Automatic Sync

1. Enable auto-sync in extension settings
2. Messages will be automatically sent to local server as they appear

### API Endpoints (Local Bridge Server)

```
POST http://localhost:8765/sync
- Full sync of all data

POST http://localhost:8765/update
- Incremental update with new messages

GET http://localhost:8765/conversations
- List all synced conversations

GET http://localhost:8765/conversations/{id}/messages
- Get messages for a specific conversation
```

## Development

### Extension Structure

```
extension/
├── manifest.json         # Extension configuration
├── content.js           # DOM extraction logic
├── background.js        # Service worker
├── inject.js           # Injected script for deeper access
├── popup.html          # Extension popup UI
├── popup.js            # Popup logic
└── icons/              # Extension icons
```

### Key Components

1. **Content Script (`content.js`)**
   - Runs in Claude.ai page context
   - Extracts data from DOM
   - Monitors for changes

2. **Background Script (`background.js`)**
   - Manages extension lifecycle
   - Coordinates between components
   - Handles cross-origin requests

3. **Injected Script (`inject.js`)**
   - Runs in page's JavaScript context
   - Can access React props and internal state
   - Provides deeper integration if needed

4. **Bridge Server (`bridge_server.py`)**
   - HTTP server on port 8765
   - Receives data from extension
   - Stores in SQLite database
   - Provides MCP-compatible API

## Security Considerations

1. **Local Only**
   - Bridge server only accepts connections from localhost
   - No external network access required

2. **Data Privacy**
   - All data stays on your machine
   - No cloud services involved
   - You control what gets extracted

3. **Permissions**
   - Extension only has access to claude.ai domain
   - Minimal permissions requested

## Limitations

1. **DOM Dependence**
   - Relies on Claude.ai's DOM structure
   - May break if Claude updates their UI

2. **Performance**
   - Large conversations may be slow to extract
   - Consider pagination for better performance

3. **Rate Limiting**
   - Extension doesn't bypass Claude's rate limits
   - Still subject to normal usage restrictions

## Future Enhancements

1. **WebSocket Support**
   - Real-time message streaming
   - Lower latency updates

2. **Compression**
   - Compress large conversations before storage
   - Reduce memory footprint

3. **Selective Sync**
   - Choose which conversations to sync
   - Filter by date, project, or tags

4. **Firefox Support**
   - Port extension to Firefox
   - Cross-browser compatibility

## Troubleshooting

### Extension Not Working

1. Check if extension is enabled in `chrome://extensions/`
2. Reload the Claude.ai page
3. Check browser console for errors

### Bridge Server Issues

1. Ensure server is running: `python bridge_server.py`
2. Check port 8765 is not in use
3. Verify firewall allows local connections

### Data Not Syncing

1. Check extension popup for error messages
2. Verify bridge server is receiving requests
3. Check browser developer tools Network tab

## Contributing

1. Test DOM selectors with Claude.ai updates
2. Add error handling for edge cases
3. Improve message extraction accuracy
4. Add support for more data types (artifacts, images)

## License

Same as parent project (mcp-claude-context)
