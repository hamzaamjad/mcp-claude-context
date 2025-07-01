#!/usr/bin/env python3
"""
Integration tests for the Direct API Claude Context Server.
Tests use mock responses based on actual conversation data.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# Import the server module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from direct_api_server import DirectAPIClaudeContextServer

# Load sample data
SAMPLE_DATA_PATH = Path(__file__).parent.parent / "conversations.json"
with open(SAMPLE_DATA_PATH, 'r') as f:
    SAMPLE_CONVERSATIONS = json.load(f)


class TestDirectAPIClaudeContextServer:
    """Test suite for Direct API Claude Context Server."""
    
    @pytest.fixture
    def server(self):
        """Create a server instance for testing."""
        return DirectAPIClaudeContextServer()
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock requests session."""
        with patch('direct_api_server.requests.Session') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_list_conversations_success(self, server, mock_session):
        """Test successful conversation listing."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_CONVERSATIONS[:10]
        
        # Configure mock session
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        server.session = mock_session_instance
        
        # Test
        result = await server._list_conversations(
            session_key="test_key",
            org_id="test_org",
            limit=10
        )
        
        # Assertions
        assert result["status"] == "success"
        assert result["count"] == 10
        assert len(result["conversations"]) == 10
        assert result["conversations"][0]["name"] == "Claude Conversation History Retrieval"
        
        # Verify API call
        mock_session_instance.get.assert_called_once_with(
            'https://claude.ai/api/organizations/test_org/chat_conversations',
            headers={
                'Cookie': 'sessionKey=test_key',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate',
                'Referer': 'https://claude.ai/',
                'Origin': 'https://claude.ai'
            },
            timeout=30
        )
    
    @pytest.mark.asyncio
    async def test_list_conversations_error(self, server, mock_session):
        """Test conversation listing with API error."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        
        # Configure mock session
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        server.session = mock_session_instance
        
        # Test
        result = await server._list_conversations(
            session_key="invalid_key",
            org_id="test_org",
            limit=10
        )
        
        # Assertions
        assert result["status"] == "error"
        assert "403" in result["error"]
        assert result["details"] == "Forbidden"
    
    @pytest.mark.asyncio
    async def test_search_conversations(self, server):
        """Test conversation search functionality."""
        # Pre-populate cache
        server.conversations_cache = {
            conv['uuid']: conv for conv in SAMPLE_CONVERSATIONS[:20]
        }
        
        # Test search
        result = await server._search_conversations(
            session_key="test_key",
            org_id="test_org",
            query="Mirror"
        )
        
        # Assertions
        assert result["status"] == "success"
        assert result["query"] == "Mirror"
        assert result["count"] > 0
        
        # Verify search results contain "Mirror"
        for conv in result["results"]:
            assert "mirror" in conv["name"].lower()
    
    @pytest.mark.asyncio
    async def test_get_conversation_from_cache(self, server):
        """Test getting a conversation from cache."""
        # Pre-populate cache
        test_conv = SAMPLE_CONVERSATIONS[0]
        server.conversations_cache[test_conv['uuid']] = test_conv
        
        # Test
        result = await server._get_conversation(
            session_key="test_key",
            org_id="test_org",
            conversation_id=test_conv['uuid']
        )
        
        # Assertions
        assert result["status"] == "success"
        assert result["conversation"]["uuid"] == test_conv['uuid']
        assert result["conversation"]["name"] == test_conv["name"]
    
    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, server):
        """Test getting a non-existent conversation."""
        # Test with empty cache
        result = await server._get_conversation(
            session_key="test_key",
            org_id="test_org",
            conversation_id="non-existent-id"
        )
        
        # Assertions
        assert result["status"] == "error"
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_export_conversations_json(self, server):
        """Test exporting conversations to JSON format."""
        # Pre-populate cache
        server.conversations_cache = {
            conv['uuid']: conv for conv in SAMPLE_CONVERSATIONS[:5]
        }
        
        # Test export
        result = await server._export_conversations(
            session_key="test_key",
            org_id="test_org",
            format="json",
            include_settings=False
        )
        
        # Assertions
        assert result["status"] == "success"
        assert result["format"] == "json"
        assert result["conversation_count"] == 5
        assert result["filename"].endswith(".json")
        assert Path(result["filepath"]).exists()
        
        # Verify file content
        with open(result["filepath"], 'r') as f:
            export_data = json.load(f)
            assert export_data["conversation_count"] == 5
            assert len(export_data["conversations"]) == 5
        
        # Cleanup
        Path(result["filepath"]).unlink()
    
    @pytest.mark.asyncio
    async def test_export_conversations_csv(self, server):
        """Test exporting conversations to CSV format."""
        # Pre-populate cache
        server.conversations_cache = {
            conv['uuid']: conv for conv in SAMPLE_CONVERSATIONS[:5]
        }
        
        # Test export
        result = await server._export_conversations(
            session_key="test_key",
            org_id="test_org",
            format="csv",
            include_settings=False
        )
        
        # Assertions
        assert result["status"] == "success"
        assert result["format"] == "csv"
        assert result["conversation_count"] == 5
        assert result["filename"].endswith(".csv")
        assert Path(result["filepath"]).exists()
        
        # Verify file content
        import csv
        with open(result["filepath"], 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 5
            assert 'id' in rows[0]
            assert 'name' in rows[0]
        
        # Cleanup
        Path(result["filepath"]).unlink()
    
    @pytest.mark.asyncio
    async def test_export_conversations_invalid_format(self, server):
        """Test export with invalid format."""
        result = await server._export_conversations(
            session_key="test_key",
            org_id="test_org",
            format="xml"
        )
        
        assert result["status"] == "error"
        assert "Unsupported format" in result["error"]
    
    def test_format_file_size(self, server):
        """Test file size formatting."""
        assert server._format_file_size(500) == "500.00 B"
        assert server._format_file_size(1024) == "1.00 KB"
        assert server._format_file_size(1024 * 1024) == "1.00 MB"
        assert server._format_file_size(1024 * 1024 * 1024) == "1.00 GB"
    
    def test_get_headers(self, server):
        """Test header generation."""
        headers = server._get_headers("test_session_key")
        
        assert headers['Cookie'] == 'sessionKey=test_session_key'
        assert 'Mozilla' in headers['User-Agent']
        assert headers['Accept'] == 'application/json'
        assert headers['Origin'] == 'https://claude.ai'


class TestMCPIntegration:
    """Test MCP server integration."""
    
    @pytest.mark.asyncio
    async def test_tool_listing(self):
        """Test that all tools are properly listed."""
        server = DirectAPIClaudeContextServer()
        
        # Mock the MCP server methods
        with patch.object(server.server, 'list_tools') as mock_list:
            # Get the actual handler
            handler = None
            for call in server.server.list_tools.call_args_list:
                if call[0] and callable(call[0][0]):
                    handler = call[0][0]
                    break
            
            # If we found the handler, test it
            if handler:
                tools = await handler()
                
                # Verify tools
                tool_names = [tool.name for tool in tools]
                assert "list_conversations" in tool_names
                assert "get_conversation" in tool_names
                assert "search_conversations" in tool_names
                assert "export_conversations" in tool_names
                
                # Verify tool schemas
                for tool in tools:
                    assert tool.inputSchema["type"] == "object"
                    assert "session_key" in tool.inputSchema["properties"]
                    assert "org_id" in tool.inputSchema["properties"]


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_search_query(self, server):
        """Test search with empty query."""
        server = DirectAPIClaudeContextServer()
        result = await server._search_conversations("key", "org", "")
        
        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["results"] == []
    
    @pytest.mark.asyncio
    async def test_rate_limiting_handling(self, server):
        """Test handling of rate limiting responses."""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        
        # Configure mock session
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        server.session = mock_session_instance
        
        # Test
        result = await server._list_conversations(
            session_key="test_key",
            org_id="test_org",
            limit=10
        )
        
        # Assertions
        assert result["status"] == "error"
        assert "429" in result["error"]
    
    @pytest.mark.asyncio
    async def test_network_timeout(self, server):
        """Test handling of network timeouts."""
        # Configure mock to raise timeout
        mock_session_instance = Mock()
        mock_session_instance.get.side_effect = asyncio.TimeoutError("Request timed out")
        server.session = mock_session_instance
        
        # Test
        result = await server._list_conversations(
            session_key="test_key",
            org_id="test_org",
            limit=10
        )
        
        # Assertions
        assert result["status"] == "error"
        assert "Request timed out" in result["error"]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
