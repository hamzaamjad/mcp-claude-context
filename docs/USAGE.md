# MCP Claude Context Server Usage Guide

## Quick Start

1. **Install dependencies**:
   ```bash
   ./bootstrap.sh
   ```

2. **Run the server**:
   ```bash
   poetry run python -m src.server
   ```

3. **Configure Claude Desktop**:
   Add to your Claude Desktop config:
   ```json
   {
     "mcpServers": {
       "claude-context": {
         "command": "python",
         "args": ["-m", "src.server"],
         "cwd": "/path/to/mcp-claude-context",
         "env": {
           "PYTHONPATH": "."
         }
       }
     }
   }
   ```

## Available Tools

### extract_conversation
Extract a specific conversation from Claude.ai.

**Parameters:**
- `conversation_url` (required): The Claude.ai conversation URL
- `session_key` (optional): Authentication session key

**Example:**
```json
{
  "tool": "extract_conversation",
  "arguments": {
    "conversation_url": "https://claude.ai/chat/abc123"
  }
}
```

### list_conversations
List available conversations from Claude.ai.

**Parameters:**
- `session_key` (optional): Authentication session key
- `limit` (optional): Maximum conversations to return (default: 20)

**Example:**
```json
{
  "tool": "list_conversations",
  "arguments": {
    "limit": 10
  }
}
```

### monitor_conversations
Monitor Claude.ai for new conversations.

**Parameters:**
- `session_key` (optional): Authentication session key
- `poll_interval` (optional): Check interval in seconds (default: 30)

**Example:**
```json
{
  "tool": "monitor_conversations",
  "arguments": {
    "poll_interval": 60
  }
}
```

## Resources

Extracted conversations are exposed as MCP resources with URIs like:
```
conversation://conversation-id
```

## Authentication

If you encounter authentication errors, you'll need to provide a session key. This can be obtained from your browser's cookies when logged into Claude.ai.

## Troubleshooting

1. **Playwright not installed**: Run `poetry run playwright install chromium`
2. **Import errors**: Ensure `PYTHONPATH=.` is set
3. **Authentication required**: Provide a valid session_key parameter

## Development

Run tests:
```bash
poetry run pytest
```

Format code:
```bash
poetry run black src tests
poetry run ruff check src tests
```