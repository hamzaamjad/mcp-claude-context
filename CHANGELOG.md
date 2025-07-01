# CHANGELOG

All notable changes to the claude-context MCP server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-06-30

### Added
- Direct API implementation for Claude.ai conversation access
- New `export_conversations` tool for exporting to JSON/CSV formats
- Comprehensive rate limiting tests
- Session validation and error handling
- Export functionality with timestamps and file size reporting

### Changed
- Switched from Playwright-based browser automation to direct API calls
- Improved authentication handling with session keys and organization IDs
- Enhanced error messages for better debugging

### Fixed
- Cloudflare protection bypass issues from v0.1.0
- Timeout issues when accessing conversations
- Authentication failures with browser automation

### Technical Details
- Uses Claude.ai's `/api/organizations/{org_id}/chat_conversations` endpoint
- Requires both `session_key` and `org_id` for authentication
- Implements conversation caching for improved performance
- No rate limiting detected up to 50 requests/17 seconds (~3 req/sec)

## [0.1.0] - 2025-06-25 (Deprecated)

### Initial Release
- Playwright-based browser automation implementation
- Basic conversation listing functionality
- Message extraction attempts

### Known Issues
- Failed due to Cloudflare protection on Claude.ai
- Browser automation detected and blocked
- Frequent timeout errors
- Unable to retrieve conversation content reliably

### Deprecated
- This version is no longer functional due to anti-automation measures

---

## Migration Guide

### From v0.1.0 to v0.2.0

1. **Update authentication method:**
   - Old: Browser-based login
   - New: Session key + Organization ID

2. **Update tool calls:**
   ```python
   # Old (v0.1.0)
   extract_conversation(url="https://claude.ai/chat/...")
   
   # New (v0.2.0)
   list_conversations(
     session_key="YOUR_SESSION_KEY_HERE",
     org_id="YOUR_ORG_ID_HERE",
     limit=50
   )
   ```

3. **Handle new response format:**
   - Responses now include structured JSON with status indicators
   - Error handling is more granular with specific error codes

## Future Roadmap

### v0.3.0 (Planned)
- Message content retrieval (pending API discovery)
- WebSocket integration for real-time updates
- Pagination support for large conversation lists

### v0.4.0 (Planned)
- Browser extension bridge for complete message access
- Local caching with SQLite
- Incremental sync capabilities

### v1.0.0 (Target)
- Full conversation and message export
- Complete API parity with Claude.ai web interface
- Production-ready stability and performance
