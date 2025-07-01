# MCP Claude Context Usage Guide

## Overview

The MCP Claude Context server provides tools to extract and monitor Claude.ai conversations. It exposes three main tools through the MCP protocol:

1. **extract_conversation** - Extract a specific conversation by URL
2. **list_conversations** - List all available conversations 
3. **monitor_conversations** - Monitor for new conversation updates

## Using with Session Key

To use the `list_conversations` tool with your session key ``, you would call it like this:

### Through MCP Protocol

When the MCP server is running, you can call the tool with:

```json
{
  "tool": "list_conversations",
  "arguments": {
    "session_key": "",
    "limit": 20
  }
}
```

### Direct Python Usage

```python
import asyncio
from src.server import MCPClaudeContextServer

async def list_my_conversations():
    server = MCPClaudeContextServer()
    
    result = await server._list_conversations(
        session_key="YOUR_SESSION_KEY_HERE",
        limit=20
    )
    
    print(result)
    await server.cleanup()

asyncio.run(list_my_conversations())
```

## Current Status

During testing, we encountered issues with:

1. **Cookie Authentication**: The session key format suggests it's an Anthropic session ID, but the exact cookie name and format Claude.ai expects is unclear
2. **Network Timeouts**: Playwright had difficulty connecting to Claude.ai, which could be due to:
   - Rate limiting
   - Geographic restrictions  
   - Authentication requirements
   - Changes in Claude.ai's structure

## Recommendations

1. **Verify Session Key**: Ensure the session key is still valid and hasn't expired
2. **Check Cookie Name**: The actual cookie name Claude.ai uses for authentication might be different than what we tried
3. **Browser Context**: You might need to manually authenticate in a browser first and export the full cookie set
4. **API Alternative**: Consider if Claude.ai offers an official API that would be more reliable than web scraping

## Running the MCP Server

To run the server:

```bash
# Install dependencies
poetry install
poetry run playwright install chromium

# Run the server
poetry run mcp-claude-context
```

The server will then be available for MCP clients to connect to and use the exposed tools.