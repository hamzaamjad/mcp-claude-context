# README.md
# MCP Claude Context Server

Extract and monitor Claude.ai conversations via Model Context Protocol.

## Objective
Build an MCP server that can:
1. Extract conversations from Claude.ai web interface
2. Monitor Claude Desktop for conversation updates
3. Expose conversations as MCP resources
4. Handle authentication and rate limiting gracefully

## Architecture Requirements
- Python 3.11+ with Poetry
- MCP server implementation
- Playwright for web automation
- Optional: Browser extension for real-time monitoring
- FastAPI endpoint for external integrations

## Implementation Priorities
1. Basic MCP server with conversation extraction tool
2. Web scraping via Playwright
3. Desktop app file monitoring
4. Browser extension (stretch goal)

## Technical Constraints
- Must handle DOM structure changes gracefully
- Respect Anthropic ToS
- Local-first, no cloud dependencies
- Comprehensive error handling and retry logic