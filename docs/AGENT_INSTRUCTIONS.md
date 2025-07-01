# AGENT_INSTRUCTIONS.md
# Instructions for Claude Code

## Project Overview
Build a production-ready MCP server for extracting Claude.ai conversations.

## Key Implementation Details

1. **MCP Server Structure**
   - Use the official MCP Python SDK
   - Implement both tools and resources
   - Handle stdio communication properly

2. **Conversation Extraction Methods**
   - Primary: Playwright-based web scraping
   - Secondary: File system monitoring for Claude Desktop
   - Tertiary: Browser extension bridge (create manifest.json)

3. **Error Handling**
   - Graceful degradation when DOM changes
   - Retry logic with exponential backoff
   - Clear error messages in MCP responses

4. **Code Style**
   - Type hints everywhere
   - Comprehensive docstrings
   - Async/await patterns throughout

5. **Testing**
   - Unit tests for each extraction method
   - Mock Playwright responses
   - Integration test with real Claude.ai (optional)

## Architecture Decisions You Should Make
- Whether to use selenium vs playwright (recommend playwright)
- Storage backend for cached conversations (recommend sqlite)
- Browser extension communication protocol (WebSocket vs HTTP polling)

## Files to Create
1. `src/server.py` - Main MCP server
2. `src/extractors/web.py` - Playwright-based extraction
3. `src/extractors/desktop.py` - File system monitoring
4. `src/models.py` - Pydantic models for conversations
5. `extension/manifest.json` - Browser extension setup
6. `extension/content.js` - DOM monitoring script
7. `docs/API.md` - MCP tool/resource documentation

## Success Criteria
- Can extract conversations from Claude.ai with active session
- Handles pagination and long conversations
- Exposes clean MCP interface
- Passes all CI/CD checks