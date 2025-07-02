# MCP Claude Context Server v0.5.0

[![PyPI version](https://badge.fury.io/py/mcp-claude-context.svg)](https://badge.fury.io/py/mcp-claude-context)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Model Context Protocol (MCP) server for extracting, storing, searching, and analyzing Claude.ai conversations with enhanced database storage, semantic search, and multiple export formats.

## 🚀 What's New in v0.5.0

- **SQLite Database Storage** - Migrate from JSON files to efficient database
- **Semantic Search** - AI-powered search using sentence transformers
- **Multiple Export Formats** - Obsidian, PDF, JSON, CSV
- **Easy Deployment** - Docker support and one-click installers
- **Performance Improvements** - 10x faster search, 35% faster operations

## Features

### Core Functionality
- ✅ Direct API access for Claude.ai conversations
- ✅ Chrome extension for full message extraction
- ✅ SQLite database with full-text search
- ✅ Semantic search capabilities
- ✅ Multiple export formats (Obsidian, PDF, JSON, CSV)
- ✅ Bulk operations and analytics
- ✅ Session management with auto-refresh
- ✅ Real-time analytics dashboard

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude.ai Web  │────▶│ Chrome Extension │────▶│  Bridge Server  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   MCP Client    │◀────│    MCP Server    │◀────│    Database     │
│  (Claude App)   │     │   (Enhanced)     │     │  (SQLite+FTS)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                        ┌───────┴───────┐
                        ▼               ▼
                  ┌──────────┐    ┌──────────┐
                  │ Exporters│    │  Search  │
                  │ (PDF/MD) │    │ (AI/FTS) │
                  └──────────┘    └──────────┘
```

## 🛠️ Installation

### Quick Start with uvx (Recommended - No Installation!)

Add to your Claude Desktop config:

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

That's it! No installation needed. [See full uvx guide →](docs/UVX_DEPLOYMENT.md)

### Quick Start with Docker

```bash
# Using pre-built image
docker run -d \
  --name mcp-claude-context \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  hamzaamjad/mcp-claude-context:latest

# Or with docker-compose
curl -O https://raw.githubusercontent.com/hamzaamjad/mcp-claude-context/main/docker-compose.simple.yml
docker-compose -f docker-compose.simple.yml up -d
```

### One-Click Installer

```bash
# Mac/Linux
curl -sSL https://raw.githubusercontent.com/hamzaamjad/mcp-claude-context/main/deployment/one-click-install.sh | bash

# Windows (PowerShell)
iwr -useb https://raw.githubusercontent.com/hamzaamjad/mcp-claude-context/main/deployment/install.ps1 | iex
```

### Manual Installation

1. **Prerequisites:**
   - Python 3.11+
   - Chrome browser
   - Poetry (Python package manager)

2. **Install dependencies:**
   ```bash
   poetry install
   ```

3. **Initialize database:**
   ```bash
   poetry run python -c "from src.models.conversation import init_database; init_database()"
   ```

4. **Install Chrome extension:**
   - Open Chrome → `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" → Select `extension/` directory

5. **Start the server:**
   ```bash
   poetry run python -m src.direct_api_server
   ```

## 📚 Available MCP Tools

### Conversation Management
| Tool | Description | Requires API Keys |
|------|-------------|-------------------|
| `list_conversations` | List all conversations from Claude.ai | ✅ |
| `get_conversation` | Get specific conversation details | ✅ |
| `search_conversations` | Search conversations by keyword | ✅ |
| `get_conversation_messages` | Get full messages from local data | ❌ |

### Search & Analytics
| Tool | Description |
|------|-------------|
| `search_messages` | Full-text search across all messages |
| `semantic_search` | AI-powered similarity search |
| `get_analytics` | Get conversation statistics and insights |

### Export & Operations
| Tool | Description |
|------|-------------|
| `export_conversations` | Export to JSON/CSV formats |
| `export_to_obsidian` | Export to Obsidian vault with backlinks |
| `bulk_operations` | Tag, export, delete, or analyze in bulk |

### System Management
| Tool | Description |
|------|-------------|
| `update_session` | Update Claude.ai session credentials |
| `migrate_to_database` | Migrate JSON files to SQLite |
| `rebuild_search_index` | Optimize search performance |

## 💡 Usage Examples

### Basic Operations

```python
# List conversations
{
  "tool": "list_conversations",
  "arguments": {
    "session_key": "YOUR_SESSION_KEY",
    "org_id": "YOUR_ORG_ID",
    "limit": 50,
    "sync_to_db": true
  }
}

# Search with AI
{
  "tool": "semantic_search",
  "arguments": {
    "query": "discussions about machine learning",
    "search_type": "hybrid",
    "top_k": 10
  }
}

# Export to Obsidian
{
  "tool": "export_to_obsidian",
  "arguments": {
    "conversation_ids": ["conv-id-1", "conv-id-2"],
    "vault_path": "/path/to/obsidian/vault"
  }
}
```

### Chrome Extension Usage

1. **Extract single conversation:**
   - Navigate to conversation on Claude.ai
   - Click extension icon
   - Click "Extract Current Conversation"

2. **Bulk extract all conversations:**
   - Click extension icon
   - Click "Extract All Conversations"
   - Monitor progress in popup

3. **View analytics:**
   - Visit http://localhost:8765/dashboard
   - See statistics, trends, and insights

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_DB_PATH` | Database location | `data/db/conversations.db` |
| `MCP_EXPORT_DIR` | Export directory | `exports/` |
| `NOTION_API_KEY` | Notion integration | Optional |

### Getting Session Credentials

1. Log into Claude.ai
2. Open Chrome DevTools (F12)
3. Go to Application → Cookies
4. Find `sessionKey` value
5. Find `org_id` in Network tab API calls

## 📊 Performance

### v0.5.0 Improvements
- **Search Speed**: 10x faster with SQLite FTS5
- **Storage**: 20% less space with database compression
- **Operations**: 35% faster read/write performance
- **Scalability**: Handles 100K+ conversations efficiently

### Benchmark Results
| Operation | JSON Files | SQLite Database |
|-----------|------------|-----------------|
| Search 1K convos | 2.3s | 0.23s |
| Load conversation | 150ms | 45ms |
| Export 100 convos | 5.2s | 1.8s |

## 🚀 Advanced Features

### Semantic Search
The server uses sentence transformers for AI-powered search:
- Find similar conversations
- Search by meaning, not just keywords
- Discover related topics automatically

### Obsidian Integration
Export conversations with:
- Proper frontmatter metadata
- Automatic backlinks
- Daily notes integration
- Tag organization
- Dataview queries

### Bulk Operations
Process multiple conversations:
```python
{
  "tool": "bulk_operations",
  "arguments": {
    "operation": "analyze",
    "conversation_ids": ["id1", "id2", "id3"],
    "params": {}
  }
}
```

## 🐛 Troubleshooting

### Common Issues

1. **"Session expired" error**
   - Get fresh session key from Claude.ai
   - Use `update_session` tool

2. **Chrome extension not connecting**
   - Ensure bridge server is running (port 9222)
   - Check extension permissions

3. **Database locked error**
   - Ensure only one server instance running
   - Check file permissions

4. **Search not finding results**
   - Run `rebuild_search_index` tool
   - Verify conversations are in database

### Debug Mode

Enable detailed logging:
```bash
LOG_LEVEL=DEBUG poetry run python -m src.direct_api_server
```

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

### Development Setup

```bash
# Install dev dependencies
poetry install --with dev

# Run tests
poetry run pytest

# Format code
poetry run black src/
poetry run ruff src/
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- Built on [Model Context Protocol](https://github.com/anthropics/mcp)
- Uses [Sentence Transformers](https://www.sbert.net/) for semantic search
- PDF generation with [ReportLab](https://www.reportlab.com/)

## 📞 Support

- [GitHub Issues](https://github.com/yourusername/mcp-claude-context/issues)
- [Documentation](docs/)
- [Changelog](CHANGELOG.md)

---

**Note**: This tool is not affiliated with Anthropic. Use responsibly and respect rate limits.
