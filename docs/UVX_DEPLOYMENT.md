# 🚀 Quick Start with uvx

The simplest way to run MCP Claude Context Server is using `uvx` (no installation required!).

## Prerequisites

- Python 3.11 or higher
- uv installed: `pip install uv` or `brew install uv`

## Quick Start

### 1. Configure Claude Desktop

Add this to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "claude-context": {
      "command": "uvx",
      "args": ["mcp-claude-context"],
      "env": {
        "CLAUDE_SESSION_KEY": "sk-ant-sid01-...",
        "CLAUDE_ORG_ID": "28a16e5b-..."
      }
    }
  }
}
```

### 2. Get Your Credentials

1. Log into [Claude.ai](https://claude.ai)
2. Open Developer Tools (F12)
3. Go to Application → Cookies → claude.ai
4. Copy the `sessionKey` value
5. Find `org_id` in any API request (Network tab)

### 3. Start Using

That's it! The server will start automatically when you open Claude Desktop.

## Alternative Methods

### Run from GitHub (Latest Development)

```json
{
  "mcpServers": {
    "claude-context": {
      "command": "uvx",
      "args": ["git+https://github.com/hamzaamjad/mcp-claude-context"]
    }
  }
}
```

### Run with Custom Database Path

```json
{
  "mcpServers": {
    "claude-context": {
      "command": "uvx",
      "args": ["mcp-claude-context"],
      "env": {
        "CLAUDE_SESSION_KEY": "sk-ant-sid01-...",
        "CLAUDE_ORG_ID": "28a16e5b-...",
        "MCP_DB_PATH": "/path/to/your/conversations.db",
        "MCP_EXPORT_DIR": "/path/to/exports"
      }
    }
  }
}
```

### Run with Debug Logging

```json
{
  "mcpServers": {
    "claude-context": {
      "command": "uvx",
      "args": ["mcp-claude-context"],
      "env": {
        "CLAUDE_SESSION_KEY": "sk-ant-sid01-...",
        "CLAUDE_ORG_ID": "28a16e5b-...",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## Testing the Installation

Once configured, you can test the server in Claude Desktop by typing:

```
Use the list_conversations tool to show my recent Claude conversations.
```

## Chrome Extension Setup

The Chrome extension is needed to extract conversations from Claude.ai:

1. Download the extension from [Releases](https://github.com/hamzaamjad/mcp-claude-context/releases)
2. Open Chrome → Extensions → Enable Developer Mode
3. Click "Load unpacked" and select the extension folder
4. Visit Claude.ai and click the extension icon

## Troubleshooting

### Server not starting
- Check Claude Desktop logs: Help → Show Logs
- Verify Python version: `python --version` (must be 3.11+)
- Try running manually: `uvx mcp-claude-context`

### Authentication errors
- Session keys expire - get fresh credentials
- Ensure no extra spaces in credentials
- Check org_id format (should be UUID-like)

### Can't find conversations
- Install and activate the Chrome extension
- Extract at least one conversation first
- Check database location in logs

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_SESSION_KEY` | Your Claude.ai session key | Required |
| `CLAUDE_ORG_ID` | Your organization ID | Required |
| `MCP_DB_PATH` | Database file location | `~/mcp-claude-context/conversations.db` |
| `MCP_EXPORT_DIR` | Export directory | `~/mcp-claude-context/exports` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Next Steps

- [Full Documentation](./README.md)
- [Chrome Extension Guide](./CHROME_EXTENSION.md)
- [API Reference](./API.md)
- [Rate Limiting Guide](./rate_limiting.md)