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
        self.messages_cache: Dict[str, Any] = {}  # Cache for extracted messages
        self.session = requests.Session()
        self.extracted_messages_dir = Path("/Users/hamzaamjad/mcp-claude-context/extracted_messages")
        self.session_key_file = Path("/Users/hamzaamjad/mcp-claude-context/config/session_key.json")
        self.last_session_check = None
        self.session_check_interval = 300  # Check every 5 minutes
        
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
                ),
                Tool(
                    name="get_conversation_messages",
                    description="Get full conversation messages from locally extracted data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "conversation_id": {
                                "type": "string",
                                "description": "Conversation UUID (required)"
                            }
                        },
                        "required": ["conversation_id"]
                    }
                ),
                Tool(
                    name="search_messages",
                    description="Search through all extracted message content",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query to find in message content"
                            },
                            "case_sensitive": {
                                "type": "boolean",
                                "description": "Whether search should be case sensitive",
                                "default": false
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "minimum": 1,
                                "maximum": 100,
                                "default": 20
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="update_session",
                    description="Update or refresh Claude.ai session credentials",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_key": {
                                "type": "string",
                                "description": "New Claude.ai session key"
                            },
                            "org_id": {
                                "type": "string",
                                "description": "Organization ID"
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
                elif name == "get_conversation_messages":
                    result = await self._get_conversation_messages(
                        arguments.get("conversation_id")
                    )
                elif name == "search_messages":
                    result = await self._search_messages(
                        arguments.get("query"),
                        arguments.get("case_sensitive", False),
                        arguments.get("limit", 20)
                    )
                elif name == "update_session":
                    result = await self._update_session(
                        arguments.get("session_key"),
                        arguments.get("org_id")
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
    
    def _save_session_key(self, session_key: str, org_id: str) -> None:
        """Save session key to file for persistence."""
        try:
            self.session_key_file.parent.mkdir(exist_ok=True)
            data = {
                'session_key': session_key,
                'org_id': org_id,
                'updated_at': datetime.now().isoformat()
            }
            with open(self.session_key_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Session key saved")
        except Exception as e:
            logger.error(f"Failed to save session key: {e}")
    
    def _load_session_key(self) -> Optional[Dict[str, str]]:
        """Load session key from file."""
        try:
            if self.session_key_file.exists():
                with open(self.session_key_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load session key: {e}")
        return None
    
    async def _verify_session(self, session_key: str, org_id: str) -> bool:
        """Verify if session key is still valid."""
        try:
            # Try a simple API call
            url = f'https://claude.ai/api/organizations/{org_id}/chat_conversations?limit=1'
            headers = self._get_headers(session_key)
            
            response = await asyncio.to_thread(
                self.session.get, url, headers=headers, timeout=10
            )
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Session verification failed: {e}")
            return False
    
    async def _check_and_refresh_session(self, session_key: str, org_id: str) -> tuple[str, str]:
        """Check session validity and refresh if needed."""
        current_time = datetime.now()
        
        # Check if we need to verify session
        if self.last_session_check is None or \
           (current_time - self.last_session_check).total_seconds() > self.session_check_interval:
            
            logger.info("Checking session validity...")
            if await self._verify_session(session_key, org_id):
                self.last_session_check = current_time
                self._save_session_key(session_key, org_id)
                return session_key, org_id
            else:
                logger.warning("Session key expired or invalid")
                # In a real implementation, you might prompt for new credentials
                # For now, we'll just return the existing ones
                return session_key, org_id
        
        return session_key, org_id
    
    async def _list_conversations(self, session_key: str, org_id: str, limit: int = 50) -> Dict[str, Any]:
        """List conversations using direct API."""
        logger.info(f"Listing conversations for org {org_id}")
        
        # Check and refresh session if needed
        session_key, org_id = await self._check_and_refresh_session(session_key, org_id)
        
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
    
    async def _get_conversation_messages(self, conversation_id: str) -> Dict[str, Any]:
        """Get full conversation messages from locally extracted data."""
        logger.info(f"Getting messages for conversation {conversation_id}")
        
        # Check cache first
        if conversation_id in self.messages_cache:
            logger.info(f"Returning cached messages for {conversation_id}")
            return {
                "status": "success",
                "source": "cache",
                "conversation": self.messages_cache[conversation_id]
            }
        
        # Check if conversation directory exists
        conv_dir = self.extracted_messages_dir / conversation_id
        
        if not conv_dir.exists():
            logger.warning(f"No extracted data found for conversation {conversation_id}")
            return {
                "status": "error",
                "error": f"No extracted data found for conversation {conversation_id}",
                "hint": "Use the Chrome extension to extract messages from Claude.ai first"
            }
        
        try:
            # Read metadata
            metadata_file = conv_dir / "metadata.json"
            messages_file = conv_dir / "messages.json"
            
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            # Read messages
            messages_data = {}
            if messages_file.exists():
                with open(messages_file, 'r', encoding='utf-8') as f:
                    messages_data = json.load(f)
            else:
                return {
                    "status": "error",
                    "error": f"Messages file not found for conversation {conversation_id}",
                    "hint": "The conversation may have been extracted without messages"
                }
            
            # Combine metadata and messages
            conversation_data = {
                "id": conversation_id,
                "title": metadata.get("title", "Untitled"),
                "created_at": metadata.get("created_at"),
                "updated_at": metadata.get("updated_at"),
                "extracted_at": metadata.get("extracted_at"),
                "message_count": messages_data.get("message_count", 0),
                "messages": messages_data.get("messages", [])
            }
            
            # Cache the result
            self.messages_cache[conversation_id] = conversation_data
            
            # Also check if we have this conversation in our API cache
            if conversation_id in self.conversations_cache:
                # Merge API metadata with extracted messages
                api_data = self.conversations_cache[conversation_id]
                conversation_data.update({
                    "name": api_data.get("name", conversation_data.get("title")),
                    "model": api_data.get("model"),
                    "is_starred": api_data.get("is_starred", False),
                    "settings": api_data.get("settings", {})
                })
            
            return {
                "status": "success",
                "source": "disk",
                "conversation": conversation_data
            }
            
        except Exception as e:
            logger.error(f"Error reading conversation messages: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _search_messages(self, query: str, case_sensitive: bool = False, limit: int = 20) -> Dict[str, Any]:
        """Search through all extracted message content."""
        logger.info(f"Searching for '{query}' in extracted messages")
        
        if not query:
            return {
                "status": "error",
                "error": "Search query cannot be empty"
            }
        
        results = []
        search_query = query if case_sensitive else query.lower()
        
        try:
            # Search through all conversation directories
            if self.extracted_messages_dir.exists():
                for conv_dir in self.extracted_messages_dir.iterdir():
                    if not conv_dir.is_dir():
                        continue
                    
                    conv_id = conv_dir.name
                    messages_file = conv_dir / "messages.json"
                    metadata_file = conv_dir / "metadata.json"
                    
                    if not messages_file.exists():
                        continue
                    
                    # Read conversation data
                    with open(messages_file, 'r', encoding='utf-8') as f:
                        messages_data = json.load(f)
                    
                    metadata = {}
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    
                    # Search through messages
                    for i, message in enumerate(messages_data.get("messages", [])):
                        content = message.get("content", "")
                        search_content = content if case_sensitive else content.lower()
                        
                        if search_query in search_content:
                            # Find the specific lines that match
                            lines = content.split('\n')
                            matching_lines = []
                            
                            for line_num, line in enumerate(lines):
                                search_line = line if case_sensitive else line.lower()
                                if search_query in search_line:
                                    # Add context (previous and next line if available)
                                    context_start = max(0, line_num - 1)
                                    context_end = min(len(lines), line_num + 2)
                                    context = '\n'.join(lines[context_start:context_end])
                                    matching_lines.append({
                                        "line_number": line_num + 1,
                                        "line": line.strip(),
                                        "context": context
                                    })
                            
                            results.append({
                                "conversation_id": conv_id,
                                "conversation_title": metadata.get("title", "Untitled"),
                                "message_index": i,
                                "message_role": message.get("role", "unknown"),
                                "matching_lines": matching_lines[:3],  # Limit context lines per message
                                "content_preview": content[:200] + "..." if len(content) > 200 else content
                            })
                            
                            if len(results) >= limit:
                                break
                    
                    if len(results) >= limit:
                        break
            
            return {
                "status": "success",
                "query": query,
                "case_sensitive": case_sensitive,
                "total_results": len(results),
                "results": results[:limit]
            }
            
        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _update_session(self, session_key: str, org_id: str) -> Dict[str, Any]:
        """Update session credentials."""
        logger.info("Updating session credentials")
        
        try:
            # Verify the new credentials
            if await self._verify_session(session_key, org_id):
                # Save to file
                self._save_session_key(session_key, org_id)
                self.last_session_check = datetime.now()
                
                # Clear caches to force refresh with new credentials
                self.conversations_cache.clear()
                
                return {
                    "status": "success",
                    "message": "Session credentials updated successfully",
                    "valid": True
                }
            else:
                return {
                    "status": "error",
                    "message": "Invalid session credentials",
                    "valid": False
                }
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            initialization_options = InitializationOptions(
                server_name="claude-context-direct",
                server_version="0.4.0",
                capabilities=ServerCapabilities(),
                instructions="Direct API MCP server for Claude.ai conversations. Supports API-based conversation listing and local extracted message reading. API tools require session_key and org_id. Message tools work with locally extracted data."
            )
            await self.server.run(read_stream, write_stream, initialization_options)


async def main():
    """Main entry point."""
    server = DirectAPIClaudeContextServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())