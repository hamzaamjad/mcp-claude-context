# Changelog

All notable changes to this project will be documented in this file.

## [0.4.0] - 2025-01-01

### Added
- Enhanced Chrome extension with improved message extraction
  - Better title detection using multiple strategies
  - Improved role detection for user/assistant messages
  - Code block preservation with syntax highlighting
  - Real-time monitoring with MutationObserver
- Bulk export feature for extracting all conversations at once
  - Progress tracking and status updates
  - Skip already extracted conversations option
  - Configurable delay between extractions
- Session key management with auto-refresh
  - Verify session validity periodically
  - Save/load session credentials
  - New `update_session` MCP tool
- Analytics dashboard for conversation insights
  - Total conversations, messages, and word count
  - Time-based filtering (day, week, month, all)
  - Interactive charts for conversation trends
  - Topic analysis based on word frequency
  - Recent conversations list

### Changed
- Enhanced popup UI with statistics and bulk operations
- Bridge server now serves analytics dashboard at /dashboard
- Improved error handling and user feedback

## [0.3.0] - 2025-01-01

### Added
- New `get_conversation_messages` tool to read locally extracted conversation data
- New `search_messages` tool to search across all extracted message content
- Message caching system for improved performance
- Integration between MCP server and Chrome extension extracted data
- Comprehensive test suite for new features

### Changed
- Updated MCP server to version 0.3.0
- Reorganized repository structure with dedicated directories for scripts, docs, and config
- Enhanced README with architecture diagram and usage examples
- Improved error handling with helpful hints for users

### Fixed
- Better error messages when extracted data is not found
- Proper merging of API metadata with extracted messages

## [0.2.0] - 2024-12-31

### Added
- Direct API access implementation bypassing Cloudflare
- Chrome extension for message extraction from DOM
- Bridge server for receiving extracted data
- Export functionality for conversations (JSON/CSV)

### Changed
- Switched from Playwright to direct API access for better reliability
- Moved message extraction to Chrome extension due to API limitations

## [0.1.0] - 2024-12-30

### Added
- Initial MCP server implementation
- Basic conversation listing functionality
- Playwright-based web scraping (deprecated)