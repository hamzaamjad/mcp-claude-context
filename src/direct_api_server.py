#!/usr/bin/env python3
"""MCP Claude Context Server using direct API access."""

import logging
from typing import Any, Dict, List, Optional
import asyncio
import json
import requests
from datetime import datetime
import csv
import os
from pathlib import Path

from mcp.server import Server, InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    Resource,
    TextContent,
    ErrorData,
    INVALID_PARAMS,
    INTERNAL_ERROR,
    ServerCapabilities,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DirectAPIClaudeContextServer:
    """MCP server using direct Claude.ai API access."""
    
    def __init__(self):
        self.server = Server("claude-context-direct")
        self._setup_handlers()
        self.conversations_cache: Dict[str, Any] = {}
        self.session = requests.Session()
        
    def _setup_handlers(self):
        """Set up MCP handlers for tools and resources."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools for conversation extraction."""
            return [
                Tool(
                    name="list_conversations",
                    description="List all conversations from Claude.ai",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_key": {
                                "type": "string",
                                "description": "Claude.ai session key (required)"
                            },
                            "org_id": {
                                "type": "string",
                                "description": "Organization ID (required)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of conversations to return",
                                "minimum": 1,
                                "maximum": 100,
                                "default": 50
                            }
                        },
                        "required": ["session_key", "org_id"]
                    }
                ),
                Tool(
                    name="get_conversation",
                    description="Get a specific conversation with all messages",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_key": {
                                "type": "string",
                                "description": "Claude.ai session key (required)"
                            },
                            "org_id": {
                                "type": "string",
                                "description": "Organization ID (required)"
                            },
                            "conversation_id": {
                                "type": "string",
                                "description": "Conversation UUID (required)"
                            }
                        },
                        "required": ["session_key", "org_id", "conversation_id"]
                    }
                ),
                Tool(
                    name="search_conversations",
                    description="Search conversations by keyword",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_key": {
                                "type": "string",
                                "description": "Claude.ai session key (required)"
                            },
                            "org_id": {
                                "type": "string",
                                "description": "Organization ID (required)"
                            },
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            }
                        },
                        "required": ["session_key", "org_id", "query"]
                    }
                ),
                Tool(
                    name="export_conversations",
                    description="Export conversations to JSON or CSV format",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_key": {
                                "type": "string",
                                "description": "Claude.ai session key (required)"
                            },
                            "org_id": {
                                "type": "string",
                                "description": "Organization ID (required)"
                            },
                            "format": {
                                "type": "string",
                                "description": "Export format (json or csv)",
                                "enum": ["json", "csv"],
                                "default": "json"
                            },
                            "include_settings": {
                                "type": "boolean",
                                "description": "Include conversation settings in export",
                                "default": false
                            }
                        },
                        "required": ["session_key", "org_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool execution."""
            try:
                if name == "list_conversations":
                    result = await self._list_conversations(
                        arguments.get("session_key"),
                        arguments.get("org_id"),
                        arguments.get("limit", 50)
                    )
                elif name == "get_conversation":
                    result = await self._get_conversation(
                        arguments.get("session_key"),
                        arguments.get("org_id"),
                        arguments.get("conversation_id")
                    )
                elif name == "search_conversations":
                    result = await self._search_conversations(
                        arguments.get("session_key"),
                        arguments.get("org_id"),
                        arguments.get("query")
                    )
                elif name == "export_conversations":
                    result = await self._export_conversations(
                        arguments.get("session_key"),
                        arguments.get("org_id"),
                        arguments.get("format", "json"),
                        arguments.get("include_settings", False)
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
                    name=conv_data.get("name", f"Conversation {conv_id}"),
                    description=f"Created: {conv_data.get('created_at', 'unknown')}",
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
    
    def _get_headers(self, session_key: str) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            'Cookie': f'sessionKey={session_key}',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://claude.ai/',
            'Origin': 'https://claude.ai'
        }
    
    async def _list_conversations(self, session_key: str, org_id: str, limit: int = 50) -> Dict[str, Any]:
        """List conversations using direct API."""
        logger.info(f"Listing conversations for org {org_id}")
        
        url = f'https://claude.ai/api/organizations/{org_id}/chat_conversations'
        headers = self._get_headers(session_key)
        
        try:
            response = await asyncio.to_thread(
                self.session.get, url, headers=headers, timeout=30
            )
            
            if response.status_code == 200:
                conversations = response.json()
                
                # Cache conversations
                for conv in conversations[:limit]:
                    self.conversations_cache[conv['uuid']] = conv
                
                # Format response
                return {
                    "status": "success",
                    "count": len(conversations),
                    "conversations": [
                        {
                            "id": conv['uuid'],
                            "name": conv.get('name', 'Untitled'),
                            "created_at": conv.get('created_at'),
                            "updated_at": conv.get('updated_at'),
                            "message_count": conv.get('message_count', 0)
                        }
                        for conv in conversations[:limit]
                    ]
                }
            else:
                return {
                    "status": "error",
                    "error": f"API returned status {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _get_conversation(self, session_key: str, org_id: str, conversation_id: str) -> Dict[str, Any]:
        """Get a specific conversation."""
        logger.info(f"Getting conversation {conversation_id}")
        
        # First, check if we have it cached
        if conversation_id in self.conversations_cache:
            return {
                "status": "success",
                "conversation": self.conversations_cache[conversation_id]
            }
        
        # If not cached, try to fetch conversations first
        await self._list_conversations(session_key, org_id)
        
        if conversation_id in self.conversations_cache:
            return {
                "status": "success",
                "conversation": self.conversations_cache[conversation_id]
            }
        else:
            return {
                "status": "error",
                "error": f"Conversation {conversation_id} not found"
            }
    
    async def _search_conversations(self, session_key: str, org_id: str, query: str) -> Dict[str, Any]:
        """Search conversations by keyword."""
        logger.info(f"Searching conversations for: {query}")
        
        # First, ensure we have conversations cached
        if not self.conversations_cache:
            await self._list_conversations(session_key, org_id, limit=100)
        
        # Search in cached conversations
        query_lower = query.lower()
        results = []
        
        for conv_id, conv in self.conversations_cache.items():
            name = conv.get('name', '').lower()
            if query_lower in name:
                results.append({
                    "id": conv['uuid'],
                    "name": conv.get('name', 'Untitled'),
                    "created_at": conv.get('created_at'),
                    "updated_at": conv.get('updated_at')
                })
        
        return {
            "status": "success",
            "query": query,
            "count": len(results),
            "results": results
        }
    
    async def _export_conversations(self, session_key: str, org_id: str, format: str = "json", include_settings: bool = False) -> Dict[str, Any]:
        """Export conversations to JSON or CSV format."""
        logger.info(f"Exporting conversations in {format} format")
        
        # Ensure we have conversations
        if not self.conversations_cache:
            await self._list_conversations(session_key, org_id, limit=100)
        
        if not self.conversations_cache:
            return {
                "status": "error",
                "error": "No conversations found to export"
            }
        
        # Create exports directory
        exports_dir = Path("/Users/hamzaamjad/mcp-claude-context/exports")
        exports_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        
        try:
            if format == "json":
                filename = f"conversations_{timestamp}.json"
                filepath = exports_dir / filename
                
                # Prepare data for export
                export_data = {
                    "export_timestamp": datetime.now().isoformat(),
                    "org_id": org_id,
                    "conversation_count": len(self.conversations_cache),
                    "conversations": []
                }
                
                for conv_id, conv in self.conversations_cache.items():
                    conv_data = {
                        "id": conv['uuid'],
                        "name": conv.get('name', 'Untitled'),
                        "created_at": conv.get('created_at'),
                        "updated_at": conv.get('updated_at'),
                        "model": conv.get('model'),
                        "is_starred": conv.get('is_starred', False)
                    }
                    
                    if include_settings:
                        conv_data['settings'] = conv.get('settings', {})
                    
                    export_data['conversations'].append(conv_data)
                
                # Write JSON file
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            elif format == "csv":
                filename = f"conversations_{timestamp}.csv"
                filepath = exports_dir / filename
                
                # Prepare CSV headers
                headers = ['id', 'name', 'created_at', 'updated_at', 'model', 'is_starred']
                
                # Write CSV file
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    
                    for conv_id, conv in self.conversations_cache.items():
                        row = {
                            'id': conv['uuid'],
                            'name': conv.get('name', 'Untitled'),
                            'created_at': conv.get('created_at', ''),
                            'updated_at': conv.get('updated_at', ''),
                            'model': conv.get('model', ''),
                            'is_starred': conv.get('is_starred', False)
                        }
                        writer.writerow(row)
            
            else:
                return {
                    "status": "error",
                    "error": f"Unsupported format: {format}"
                }
            
            # Get file size
            file_size = os.path.getsize(filepath)
            
            return {
                "status": "success",
                "filename": filename,
                "filepath": str(filepath),
                "format": format,
                "conversation_count": len(self.conversations_cache),
                "file_size_bytes": file_size,
                "file_size_human": self._format_file_size(file_size),
                "export_timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            initialization_options = InitializationOptions(
                server_name="claude-context-direct",
                server_version="0.2.0",
                capabilities=ServerCapabilities(),
                instructions="Direct API MCP server for Claude.ai conversations. Requires session_key and org_id."
            )
            await self.server.run(read_stream, write_stream, initialization_options)


async def main():
    """Main entry point."""
    server = DirectAPIClaudeContextServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())