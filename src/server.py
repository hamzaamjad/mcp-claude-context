#!/usr/bin/env python3
"""MCP Claude Context Server - Extract and monitor Claude.ai conversations."""

import logging
from typing import Any, Dict, List, Optional
import asyncio
import json

from mcp.server import Server, InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    Resource,
    TextContent,
    ImageContent,
    ErrorData,
    INVALID_PARAMS,
    INTERNAL_ERROR,
    ServerCapabilities,
)

from pydantic import BaseModel, Field

from .extractors.web import ClaudeWebExtractor
from .models import ExtractionConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPClaudeContextServer:
    """MCP server for extracting and monitoring Claude.ai conversations."""
    
    def __init__(self):
        self.server = Server("claude-context")
        self._setup_handlers()
        self.conversations_cache: Dict[str, Any] = {}
        self.extractor: Optional[ClaudeWebExtractor] = None
        
    def _setup_handlers(self):
        """Set up MCP handlers for tools and resources."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools for conversation extraction."""
            return [
                Tool(
                    name="extract_conversation",
                    description="Extract a specific conversation from Claude.ai by URL or ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "conversation_url": {
                                "type": "string",
                                "description": "The Claude.ai conversation URL (e.g., https://claude.ai/chat/xxx)"
                            },
                            "session_key": {
                                "type": "string",
                                "description": "Optional session key for authentication"
                            }
                        },
                        "required": ["conversation_url"]
                    }
                ),
                Tool(
                    name="list_conversations",
                    description="List all available conversations from Claude.ai",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_key": {
                                "type": "string", 
                                "description": "Optional session key for authentication"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of conversations to return",
                                "minimum": 1,
                                "maximum": 100,
                                "default": 20
                            }
                        }
                    }
                ),
                Tool(
                    name="monitor_conversations",
                    description="Start monitoring Claude.ai for new conversation updates",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_key": {
                                "type": "string",
                                "description": "Optional session key for authentication"
                            },
                            "poll_interval": {
                                "type": "integer",
                                "description": "Polling interval in seconds",
                                "minimum": 5,
                                "maximum": 300,
                                "default": 30
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool execution."""
            try:
                if name == "extract_conversation":
                    result = await self._extract_conversation(
                        arguments.get("conversation_url"),
                        arguments.get("session_key")
                    )
                elif name == "list_conversations":
                    result = await self._list_conversations(
                        arguments.get("session_key"),
                        arguments.get("limit", 20)
                    )
                elif name == "monitor_conversations":
                    result = await self._monitor_conversations(
                        arguments.get("session_key"),
                        arguments.get("poll_interval", 30)
                    )
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                raise ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Tool execution failed: {str(e)}"
                )
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available conversation resources."""
            resources = []
            for conv_id, conv_data in self.conversations_cache.items():
                resources.append(Resource(
                    uri=f"conversation://{conv_id}",
                    name=conv_data.get("title", f"Conversation {conv_id}"),
                    description=f"Claude conversation from {conv_data.get('created_at', 'unknown')}",
                    mimeType="application/json"
                ))
            return resources
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a specific conversation resource."""
            if not uri.startswith("conversation://"):
                raise ErrorData(
                    code=INVALID_PARAMS,
                    message="Invalid resource URI format"
                )
                
            conv_id = uri.replace("conversation://", "")
            if conv_id not in self.conversations_cache:
                raise ErrorData(
                    code=INVALID_PARAMS,
                    message=f"Conversation {conv_id} not found"
                )
                
            return json.dumps(self.conversations_cache[conv_id], indent=2)
    
    async def _extract_conversation(self, conversation_url: str, session_key: Optional[str] = None) -> Dict[str, Any]:
        """Extract a specific conversation from Claude.ai."""
        logger.info(f"Extracting conversation from: {conversation_url}")
        
        # Initialize extractor if needed
        if not self.extractor:
            config = ExtractionConfig(session_key=session_key)
            self.extractor = ClaudeWebExtractor(config)
            await self.extractor.initialize()
        
        # Extract conversation
        result = await self.extractor.extract_conversation(conversation_url)
        
        if result.success and result.conversation:
            # Cache the conversation
            self.conversations_cache[result.conversation.id] = result.conversation.dict()
            
            return {
                "status": "success",
                "conversation": result.conversation.dict()
            }
        else:
            return {
                "status": "error",
                "error": result.error or "Unknown error occurred"
            }
    
    async def _list_conversations(self, session_key: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """List available conversations from Claude.ai."""
        logger.info(f"Listing conversations (limit: {limit})")
        
        # Initialize extractor if needed
        if not self.extractor:
            config = ExtractionConfig(session_key=session_key)
            self.extractor = ClaudeWebExtractor(config)
            await self.extractor.initialize()
        
        # List conversations
        conversations = await self.extractor.list_conversations(limit)
        
        # Cache conversations
        for conv in conversations:
            self.conversations_cache[conv.id] = {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "url": str(conv.url) if conv.url else None
            }
        
        return {
            "status": "success",
            "conversations": [conv.dict() for conv in conversations],
            "count": len(conversations)
        }
    
    async def _monitor_conversations(self, session_key: Optional[str] = None, poll_interval: int = 30) -> Dict[str, Any]:
        """Start monitoring conversations for updates."""
        logger.info(f"Starting conversation monitoring (interval: {poll_interval}s)")
        
        # Initialize extractor if needed
        if not self.extractor:
            config = ExtractionConfig(session_key=session_key)
            self.extractor = ClaudeWebExtractor(config)
            await self.extractor.initialize()
        
        # Define callback for new conversations
        async def on_new_conversation(conv_summary):
            logger.info(f"New conversation detected: {conv_summary.id}")
            # Extract full conversation
            result = await self.extractor.extract_conversation(str(conv_summary.url))
            if result.success and result.conversation:
                self.conversations_cache[result.conversation.id] = result.conversation.dict()
        
        # Start monitoring in background
        asyncio.create_task(
            self.extractor.monitor_conversations(on_new_conversation, poll_interval)
        )
        
        return {
            "status": "monitoring_started",
            "poll_interval": poll_interval,
            "message": f"Monitoring conversations every {poll_interval} seconds"
        }
    
    async def cleanup(self):
        """Clean up resources."""
        if self.extractor:
            await self.extractor.cleanup()
            self.extractor = None
    
    async def run(self):
        """Run the MCP server."""
        try:
            async with stdio_server() as (read_stream, write_stream):
                initialization_options = InitializationOptions(
                    server_name="claude-context",
                    server_version="0.1.0",
                    capabilities=ServerCapabilities(),
                    instructions="MCP server for extracting and monitoring Claude.ai conversations"
                )
                await self.server.run(read_stream, write_stream, initialization_options)
        finally:
            await self.cleanup()


async def main():
    """Main entry point."""
    server = MCPClaudeContextServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())