"""Tests for MCP Claude Context server."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from src.server import MCPClaudeContextServer
from src.models import Conversation, ConversationMessage, MessageContent, MessageRole


@pytest.mark.asyncio
async def test_server_initialization():
    """Test server initializes correctly."""
    server = MCPClaudeContextServer()
    assert server.server.name == "claude-context"
    assert server.conversations_cache == {}
    assert server.extractor is None


@pytest.mark.asyncio
async def test_extract_conversation_invalid_url():
    """Test extraction with invalid URL."""
    server = MCPClaudeContextServer()
    
    result = await server._extract_conversation("https://example.com/not-claude")
    
    assert result["status"] == "error"
    assert "claude.ai" in result["error"].lower()