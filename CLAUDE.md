# MCP Claude Context Server - CLAUDE.md

## 🎯 Project Overview
MCP (Model Context Protocol) server for extracting, storing, searching, and analyzing Claude.ai conversations with enhanced database storage, semantic search, and multiple export formats. Version 0.5.0 includes SQLite database, AI-powered search, and Docker deployment.

## 🏗️ Architecture
```
Claude.ai → Chrome Extension → Bridge Server → MCP Server → SQLite DB
                                                     ↓
                                              Search Engine
                                                     ↓
                                            Export Formats
```

## 📁 Repository Structure
```
mcp-claude-context/
├── src/                      # Main MCP server code
│   ├── direct_api_server.py  # Primary server (entry point)
│   ├── models/               # Database models (SQLAlchemy)
│   ├── exporters/            # Export format handlers
│   └── search/               # Search engine components
├── extension/                # Chrome extension for message extraction
│   ├── bridge_server.py      # Local HTTP server (port 9222)
│   └── content.js            # DOM extraction logic
├── deployment/               # Docker & installer scripts
├── extracted_messages/       # Local conversation storage
└── data/db/                  # SQLite database location
```

## 🚀 Quick Commands

### Server Operations
```bash
# Start MCP server (main functionality)
poetry run python -m src.direct_api_server

# Start bridge server (for Chrome extension)
poetry run python extension/bridge_server.py

# Run both with Docker
cd deployment/docker && docker-compose up -d

# One-click install (Mac/Linux)
cd deployment/installer && ./install.sh
```

### Database Operations
```bash
# Initialize database
poetry run python -c "from src.models.conversation import init_database; init_database()"

# Run migration from JSON to SQLite
poetry run python deployment/scripts/migrate_data.py

# Backup database
cp data/db/conversations.db data/db/conversations_backup_$(date +%Y%m%d).db
```

### Testing
```bash
# Run all tests
poetry run pytest

# Test with coverage
poetry run pytest --cov=src --cov-report=html

# Test specific module
poetry run pytest tests/test_direct_api.py -v
```

## 🛠️ MCP Tools Reference

### Core Tools (Require API Keys)
```python
# List conversations from Claude.ai
{
  "tool": "list_conversations",
  "arguments": {
    "session_key": "sk-ant-...",  # Required
    "org_id": "org-...",          # Required
    "limit": 50,
    "sync_to_db": true
  }
}

# Get specific conversation
{
  "tool": "get_conversation",
  "arguments": {
    "session_key": "sk-ant-...",
    "org_id": "org-...",
    "conversation_id": "uuid-here"
  }
}

# Search conversations
{
  "tool": "search_conversations",
  "arguments": {
    "session_key": "sk-ant-...",
    "org_id": "org-...",
    "query": "machine learning"
  }
}
```

### Local Tools (No API Keys)
```python
# Search with AI-powered semantic similarity
{
  "tool": "semantic_search",
  "arguments": {
    "query": "discussions about LLMs",
    "search_type": "hybrid",  # text|semantic|hybrid
    "top_k": 10
  }
}

# Export to Obsidian vault
{
  "tool": "export_to_obsidian",
  "arguments": {
    "conversation_ids": ["id1", "id2"],
    "vault_path": "/path/to/obsidian/vault"
  }
}

# Get analytics
{
  "tool": "get_analytics",
  "arguments": {
    "time_range": "month"  # day|week|month|year|all
  }
}

# Bulk operations
{
  "tool": "bulk_operations",
  "arguments": {
    "operation": "analyze",  # tag|export|delete|analyze
    "conversation_ids": ["id1", "id2"],
    "params": {}
  }
}
```

## 🔐 Authentication Setup

### Getting Session Credentials
1. Log into Claude.ai
2. Open Chrome DevTools (F12)
3. Go to Application → Cookies → claude.ai
4. Copy `sessionKey` value
5. Go to Network tab, find any API request
6. Copy `org_id` from request URL

### Session Management
```python
# Update expired session
{
  "tool": "update_session",
  "arguments": {
    "session_key": "new-session-key",
    "org_id": "org-id"
  }
}
```

## 📊 Database Schema

### Core Tables
- `conversations`: Metadata (id, title, created_at, model)
- `messages`: Content (conversation_id, role, content, index)
- `search_index`: FTS5 virtual table for full-text search
- `embeddings`: Vector embeddings for semantic search

### Key Relationships
```sql
conversations (1) ← → (N) messages
messages (1) → (1) embeddings
```

## 🔍 Search Capabilities

### Search Types
1. **Text Search**: SQLite FTS5 for keyword matching
2. **Semantic Search**: Sentence transformers + FAISS
3. **Hybrid Search**: Combines both approaches

### Search Configuration
```python
# In src/search/unified_search.py
DEFAULT_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
FAISS_INDEX_TYPE = "Flat"  # For <1M vectors
```

## 🐛 Common Issues & Solutions

### Chrome Extension Not Connecting
```bash
# Check bridge server status
curl http://localhost:9222/api/status

# Restart bridge server
pkill -f bridge_server.py
poetry run python extension/bridge_server.py
```

### Database Locked Error
```bash
# Kill existing processes
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Fix permissions
chmod 644 data/db/conversations.db
```

### Session Expired
- Get new credentials from Claude.ai
- Use `update_session` tool
- Session auto-refreshes every 5 minutes

### Search Not Finding Results
```python
# Rebuild search indexes
{
  "tool": "rebuild_search_index",
  "arguments": {
    "index_type": "both"  # text|semantic|both
  }
}
```

## 🎨 Code Style Guidelines

### Python Conventions
- Use type hints for all functions
- Docstrings in Google style
- Max line length: 100 chars
- Use `black` formatter before commits

### Async Patterns
```python
# All tool handlers must be async
async def _tool_name(self, ...):
    # Use asyncio.to_thread for blocking I/O
    result = await asyncio.to_thread(blocking_function)
    return result
```

### Error Handling
```python
# Always wrap tool execution
try:
    result = await self._execute_tool(...)
except Exception as e:
    logger.error(f"Tool failed: {e}")
    raise ErrorData(code=INTERNAL_ERROR, message=str(e))
```

## 🚢 Deployment Checklist

### Pre-deployment
- [ ] Run tests: `poetry run pytest`
- [ ] Check linting: `poetry run ruff check src/`
- [ ] Update version in `pyproject.toml`
- [ ] Update `CHANGELOG.md`

### Docker Deployment
```bash
# Build and test locally
cd deployment/docker
docker-compose build
docker-compose up

# Push to registry
docker tag mcp-claude-context:latest your-registry/mcp-claude-context:v0.5.0
docker push your-registry/mcp-claude-context:v0.5.0
```

### Production Setup
- Use environment variables for sensitive data
- Enable HTTPS with nginx reverse proxy
- Set up automated backups (cron job)
- Monitor with `docker-compose logs -f`

## 🔮 Environment Variables

```bash
# Required
CLAUDE_SESSION_KEY=sk-ant-...
CLAUDE_ORG_ID=org-...

# Optional
MCP_DB_PATH=/custom/path/conversations.db
MCP_EXPORT_DIR=/custom/exports
MCP_PORT=8000
BRIDGE_PORT=9222
LOG_LEVEL=DEBUG  # INFO|DEBUG|WARNING|ERROR

# Integrations
NOTION_API_KEY=secret_...  # For Notion export
```

## 📈 Performance Optimization

### Database
```sql
-- Run periodically
VACUUM;
ANALYZE;
PRAGMA optimize;
```

### Search Performance
- Batch embed messages (100 at a time)
- Use GPU if available: `CUDA_VISIBLE_DEVICES=0`
- Cache frequent queries in Redis (if enabled)

### Memory Management
- Conversation cache limited to 100 items
- Message cache uses LRU eviction
- Streaming exports for large datasets

## 🧪 Testing Patterns

### Unit Tests
```python
# Test async tools
@pytest.mark.asyncio
async def test_semantic_search():
    server = DirectAPIClaudeContextServer()
    result = await server._semantic_search("test query")
    assert result["status"] == "success"
```

### Integration Tests
```bash
# Test full extraction flow
poetry run python scripts/test_extraction_flow.py
```

## 🔄 Migration Notes

### From v0.4.0 → v0.5.0
1. Backup: `cp -r extracted_messages extracted_messages_backup`
2. Run migration: `poetry run python deployment/scripts/migrate_data.py`
3. Verify: Check database has all conversations
4. Update Claude Desktop config to use new server

### Breaking Changes
- JSON file storage deprecated (use SQLite)
- New required parameters for API tools
- Search API completely rewritten

## 📚 Key Dependencies

### Core
- `mcp`: Model Context Protocol SDK
- `sqlalchemy`: Database ORM
- `aiohttp`: Async HTTP client
- `pydantic`: Data validation

### Search
- `sentence-transformers`: Semantic embeddings
- `faiss-cpu`: Vector similarity search

### Export
- `reportlab`: PDF generation
- `openpyxl`: Excel export

## 🎯 Project Goals

1. **Privacy-first**: All data stored locally
2. **Performance**: Handle 100K+ conversations
3. **Extensibility**: Easy to add new export formats
4. **Reliability**: Automatic session refresh, retry logic

## 💡 Development Tips

### Adding New Tools
1. Define in `list_tools()`
2. Implement handler `_tool_name()`
3. Add tests in `tests/`
4. Update this CLAUDE.md

### Debugging
```python
# Enable debug logging
LOG_LEVEL=DEBUG poetry run python -m src.direct_api_server

# Test specific tool
poetry run python -c "
from src.direct_api_server import DirectAPIClaudeContextServer
import asyncio
server = DirectAPIClaudeContextServer()
result = asyncio.run(server._get_analytics('all'))
print(result)
"
```

## 🚨 IMPORTANT Security Notes

- NEVER commit session keys to git
- Use `.env` file for local development
- Rotate API keys regularly
- Database contains sensitive conversations
- Chrome extension requires explicit user action

## 📞 Support & Resources

- GitHub Issues: Report bugs
- `/docs` folder: Detailed guides
- `CHANGELOG.md`: Version history
- `examples/`: Usage examples

---

**Remember**: This MCP server bridges Claude.ai web → local storage → Claude Desktop. Always ensure bridge server is running for Chrome extension to work!