#!/usr/bin/env python3
"""MCP Claude Context Server v0.5.0 - Enhanced with database, search, and export features."""

import logging
from typing import Any, Dict, List, Optional, Tuple
import asyncio
import json
import requests
from datetime import datetime, timedelta
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

# Database imports
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Import our modules
from src.models.conversation import Base, Conversation, Message, init_database
from src.exporters import ObsidianExporter, PDFExporter, NotionExporter
from src.search import UnifiedSearchEngine
from src.utils.rate_limiter import RateLimiter, RateLimitConfig, RateLimitedSession
from src.utils.request_queue import RequestQueue, RequestPriority, RequestQueueManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DirectAPIClaudeContextServer:
    """MCP server v0.5.0 with enhanced features."""
    
    def __init__(self):
        self.server = Server("claude-context-direct")
        self._setup_handlers()
        self.conversations_cache: Dict[str, Any] = {}
        self.messages_cache: Dict[str, Any] = {}
        
        # Initialize rate limiting
        rate_limit_config = RateLimitConfig(
            requests_per_second=float(os.getenv('RATE_LIMIT_PER_SECOND', '3.0')),
            burst_size=int(os.getenv('RATE_LIMIT_BURST_SIZE', '10')),
            retry_after_header_respect=True,
            backoff_base=2.0,
            max_retries=5
        )
        self.rate_limiter = RateLimiter(rate_limit_config)
        
        # Initialize session with rate limiting
        self.session = requests.Session()
        self.rate_limited_session = RateLimitedSession(self.session, self.rate_limiter)
        
        # Initialize request queue manager
        self.queue_manager = RequestQueueManager(default_max_concurrent=3)
        
        # Paths
        self.extracted_messages_dir = Path("/Users/hamzaamjad/mcp-claude-context/extracted_messages")
        self.session_key_file = Path("/Users/hamzaamjad/mcp-claude-context/config/session_key.json")
        self.db_path = Path("/Users/hamzaamjad/mcp-claude-context/data/db/conversations.db")
        
        # Session management
        self.last_session_check = None
        self.session_check_interval = 300  # Check every 5 minutes
        
        # Initialize database
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = init_database(str(self.db_path))
        self.Session = sessionmaker(bind=self.engine)
        
        # Initialize search engine
        self.search_engine = UnifiedSearchEngine(str(self.db_path))
        
        # Initialize exporters
        self.obsidian_exporter = ObsidianExporter()
        self.pdf_exporter = PDFExporter()
        self.notion_exporter = None  # Will be initialized if API key is provided
        
    async def start(self):
        """Start the server and its components."""
        await self.queue_manager.start()
        logger.info("DirectAPIClaudeContextServer started")
        
    async def stop(self):
        """Stop the server and cleanup."""
        await self.queue_manager.stop()
        logger.info("DirectAPIClaudeContextServer stopped")
        
    def _setup_handlers(self):
        """Set up MCP handlers for tools and resources."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools for conversation extraction."""
            return [
                # Existing tools
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
                            },
                            "sync_to_db": {
                                "type": "boolean",
                                "description": "Sync conversations to database",
                                "default": True
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
                    description="Export conversations to various formats",
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
                                "description": "Export format",
                                "enum": ["json", "csv", "obsidian", "pdf"],
                                "default": "json"
                            },
                            "conversation_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific conversation IDs to export (optional)"
                            },
                            "include_messages": {
                                "type": "boolean",
                                "description": "Include full message content in export",
                                "default": False
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
                                "default": False
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
                ),
                # New v0.5.0 tools
                Tool(
                    name="export_to_obsidian",
                    description="Export conversations to Obsidian vault format",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "conversation_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Conversation IDs to export"
                            },
                            "vault_path": {
                                "type": "string",
                                "description": "Path to Obsidian vault (optional)"
                            }
                        },
                        "required": ["conversation_ids"]
                    }
                ),
                Tool(
                    name="semantic_search",
                    description="Search conversations using semantic similarity",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "search_type": {
                                "type": "string",
                                "enum": ["text", "semantic", "hybrid"],
                                "default": "hybrid",
                                "description": "Type of search to perform"
                            },
                            "top_k": {
                                "type": "integer",
                                "default": 10,
                                "description": "Number of results to return"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="bulk_operations",
                    description="Perform bulk operations on conversations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["tag", "export", "delete", "analyze"],
                                "description": "Operation to perform"
                            },
                            "conversation_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Conversation IDs to operate on"
                            },
                            "params": {
                                "type": "object",
                                "description": "Operation-specific parameters"
                            }
                        },
                        "required": ["operation", "conversation_ids"]
                    }
                ),
                Tool(
                    name="get_analytics",
                    description="Get conversation analytics and statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "time_range": {
                                "type": "string",
                                "enum": ["day", "week", "month", "year", "all"],
                                "default": "all",
                                "description": "Time range for analytics"
                            }
                        }
                    }
                ),
                Tool(
                    name="migrate_to_database",
                    description="Migrate JSON files to SQLite database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "verify": {
                                "type": "boolean",
                                "default": True,
                                "description": "Verify migration after completion"
                            }
                        }
                    }
                ),
                Tool(
                    name="rebuild_search_index",
                    description="Rebuild search indexes for better performance",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "index_type": {
                                "type": "string",
                                "enum": ["text", "semantic", "both"],
                                "default": "both",
                                "description": "Which indexes to rebuild"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_rate_limit_metrics",
                    description="Get rate limiting metrics and API usage statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "endpoint": {
                                "type": "string",
                                "description": "Specific endpoint to get metrics for (optional)"
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool execution."""
            try:
                # Existing tools
                if name == "list_conversations":
                    result = await self._list_conversations(
                        arguments.get("session_key"),
                        arguments.get("org_id"),
                        arguments.get("limit", 50),
                        arguments.get("sync_to_db", True)
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
                        arguments.get("conversation_ids"),
                        arguments.get("include_messages", False)
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
                # New v0.5.0 tools
                elif name == "export_to_obsidian":
                    result = await self._export_to_obsidian(
                        arguments.get("conversation_ids"),
                        arguments.get("vault_path")
                    )
                elif name == "semantic_search":
                    result = await self._semantic_search(
                        arguments.get("query"),
                        arguments.get("search_type", "hybrid"),
                        arguments.get("top_k", 10)
                    )
                elif name == "bulk_operations":
                    result = await self._bulk_operations(
                        arguments.get("operation"),
                        arguments.get("conversation_ids"),
                        arguments.get("params", {})
                    )
                elif name == "get_analytics":
                    result = await self._get_analytics(
                        arguments.get("time_range", "all")
                    )
                elif name == "migrate_to_database":
                    result = await self._migrate_to_database(
                        arguments.get("verify", True)
                    )
                elif name == "rebuild_search_index":
                    result = await self._rebuild_search_index(
                        arguments.get("index_type", "both")
                    )
                elif name == "get_rate_limit_metrics":
                    result = await self._get_rate_limit_metrics(
                        arguments.get("endpoint")
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
            
            # Get conversations from database
            session = self.Session()
            try:
                conversations = session.query(Conversation).limit(100).all()
                for conv in conversations:
                    resources.append(Resource(
                        uri=f"conversation://{conv.id}",
                        name=conv.title,
                        description=f"Created: {conv.created_at}",
                        mimeType="application/json"
                    ))
            finally:
                session.close()
            
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
            
            # Get from database
            session = self.Session()
            try:
                conv = session.query(Conversation).filter_by(id=conv_id).first()
                if not conv:
                    raise ErrorData(
                        code=INVALID_PARAMS,
                        message=f"Conversation {conv_id} not found"
                    )
                
                # Get messages
                messages = session.query(Message).filter_by(
                    conversation_id=conv_id
                ).order_by(Message.index).all()
                
                result = conv.to_dict()
                result['messages'] = [msg.to_dict() for msg in messages]
                
                return json.dumps(result, indent=2)
            finally:
                session.close()
    
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
            
            response = await self.rate_limited_session.get(
                url, headers=headers, timeout=10
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
    
    async def _list_conversations(
        self,
        session_key: str,
        org_id: str,
        limit: int = 50,
        sync_to_db: bool = True
    ) -> Dict[str, Any]:
        """List conversations using direct API."""
        logger.info(f"Listing conversations for org {org_id}")
        
        # Check and refresh session if needed
        session_key, org_id = await self._check_and_refresh_session(session_key, org_id)
        
        url = f'https://claude.ai/api/organizations/{org_id}/chat_conversations'
        headers = self._get_headers(session_key)
        
        try:
            response = await self.rate_limited_session.get(
                url, headers=headers, timeout=30
            )
            
            if response.status_code == 200:
                conversations = response.json()
                
                # Cache conversations
                for conv in conversations[:limit]:
                    self.conversations_cache[conv['uuid']] = conv
                
                # Sync to database if requested
                if sync_to_db:
                    await self._sync_conversations_to_db(conversations[:limit])
                
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
                            "message_count": conv.get('message_count', 0),
                            "model": conv.get('model'),
                            "is_starred": conv.get('is_starred', False)
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
    
    async def _sync_conversations_to_db(self, conversations: List[Dict]) -> None:
        """Sync conversations to database."""
        session = self.Session()
        try:
            for conv_data in conversations:
                # Check if conversation exists
                conv = session.query(Conversation).filter_by(
                    id=conv_data['uuid']
                ).first()
                
                if conv:
                    # Update existing
                    conv.title = conv_data.get('name', 'Untitled')
                    conv.updated_at = datetime.fromisoformat(
                        conv_data['updated_at'].replace('Z', '+00:00')
                    ) if conv_data.get('updated_at') else datetime.now()
                    conv.model = conv_data.get('model', 'unknown')
                    conv.message_count = conv_data.get('message_count', 0)
                else:
                    # Create new
                    conv = Conversation(
                        id=conv_data['uuid'],
                        title=conv_data.get('name', 'Untitled'),
                        created_at=datetime.fromisoformat(
                            conv_data['created_at'].replace('Z', '+00:00')
                        ) if conv_data.get('created_at') else datetime.now(),
                        updated_at=datetime.fromisoformat(
                            conv_data['updated_at'].replace('Z', '+00:00')
                        ) if conv_data.get('updated_at') else datetime.now(),
                        model=conv_data.get('model', 'unknown'),
                        message_count=conv_data.get('message_count', 0),
                        metadata={
                            'is_starred': conv_data.get('is_starred', False),
                            'settings': conv_data.get('settings', {})
                        }
                    )
                    session.add(conv)
            
            session.commit()
            logger.info(f"Synced {len(conversations)} conversations to database")
        except Exception as e:
            logger.error(f"Error syncing to database: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def _get_conversation(self, session_key: str, org_id: str, conversation_id: str) -> Dict[str, Any]:
        """Get a specific conversation."""
        logger.info(f"Getting conversation {conversation_id}")
        
        # First, check database
        session = self.Session()
        try:
            conv = session.query(Conversation).filter_by(id=conversation_id).first()
            if conv:
                messages = session.query(Message).filter_by(
                    conversation_id=conversation_id
                ).order_by(Message.index).all()
                
                result = conv.to_dict()
                result['messages'] = [msg.to_dict() for msg in messages]
                
                return {
                    "status": "success",
                    "source": "database",
                    "conversation": result
                }
        finally:
            session.close()
        
        # If not in database, check cache
        if conversation_id in self.conversations_cache:
            return {
                "status": "success",
                "source": "cache",
                "conversation": self.conversations_cache[conversation_id]
            }
        
        # If not cached, try to fetch conversations first
        await self._list_conversations(session_key, org_id)
        
        if conversation_id in self.conversations_cache:
            return {
                "status": "success",
                "source": "api",
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
        
        # Use database search
        results = self.search_engine.text_search.search_conversations(query, limit=50)
        
        if results:
            return {
                "status": "success",
                "source": "database",
                "query": query,
                "count": len(results),
                "results": results
            }
        
        # Fallback to cache search
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
            "source": "cache",
            "query": query,
            "count": len(results),
            "results": results
        }
    
    async def _export_conversations(
        self,
        session_key: str,
        org_id: str,
        format: str = "json",
        conversation_ids: Optional[List[str]] = None,
        include_messages: bool = False
    ) -> Dict[str, Any]:
        """Export conversations to various formats."""
        logger.info(f"Exporting conversations in {format} format")
        
        # Get conversations to export
        conversations_to_export = []
        
        if conversation_ids:
            # Export specific conversations
            session = self.Session()
            try:
                for conv_id in conversation_ids:
                    conv = session.query(Conversation).filter_by(id=conv_id).first()
                    if conv:
                        conv_data = conv.to_dict()
                        
                        if include_messages:
                            messages = session.query(Message).filter_by(
                                conversation_id=conv_id
                            ).order_by(Message.index).all()
                            conv_data['messages'] = [msg.to_dict() for msg in messages]
                        
                        conversations_to_export.append(conv_data)
            finally:
                session.close()
        else:
            # Export all from cache or database
            if not self.conversations_cache:
                await self._list_conversations(session_key, org_id, limit=100)
            
            for conv_id, conv in self.conversations_cache.items():
                conversations_to_export.append(conv)
        
        if not conversations_to_export:
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
                    "conversation_count": len(conversations_to_export),
                    "conversations": conversations_to_export
                }
                
                # Write JSON file
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            elif format == "csv":
                filename = f"conversations_{timestamp}.csv"
                filepath = exports_dir / filename
                
                # Prepare CSV headers
                headers = ['id', 'name', 'created_at', 'updated_at', 'model', 'message_count']
                
                # Write CSV file
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    
                    for conv in conversations_to_export:
                        row = {
                            'id': conv.get('id', conv.get('uuid')),
                            'name': conv.get('name', conv.get('title', 'Untitled')),
                            'created_at': conv.get('created_at', ''),
                            'updated_at': conv.get('updated_at', ''),
                            'model': conv.get('model', ''),
                            'message_count': conv.get('message_count', 0)
                        }
                        writer.writerow(row)
                        
            elif format == "obsidian":
                # Use Obsidian exporter
                results = []
                for conv in conversations_to_export:
                    if include_messages and 'messages' in conv:
                        filepath = self.obsidian_exporter.export_conversation(
                            conv, conv['messages']
                        )
                        results.append(filepath)
                
                return {
                    "status": "success",
                    "format": "obsidian",
                    "exported_count": len(results),
                    "vault_path": str(self.obsidian_exporter.vault_path),
                    "files": results
                }
                
            elif format == "pdf":
                # Use PDF exporter
                results = []
                for conv in conversations_to_export:
                    if include_messages and 'messages' in conv:
                        filepath = self.pdf_exporter.export_conversation(
                            conv, conv['messages']
                        )
                        results.append(filepath)
                
                return {
                    "status": "success",
                    "format": "pdf",
                    "exported_count": len(results),
                    "output_dir": str(self.pdf_exporter.output_dir),
                    "files": results
                }
            
            else:
                return {
                    "status": "error",
                    "error": f"Unsupported format: {format}"
                }
            
            # Get file size for json/csv
            file_size = os.path.getsize(filepath)
            
            return {
                "status": "success",
                "filename": filename,
                "filepath": str(filepath),
                "format": format,
                "conversation_count": len(conversations_to_export),
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
        
        # Check database first
        session = self.Session()
        try:
            messages = session.query(Message).filter_by(
                conversation_id=conversation_id
            ).order_by(Message.index).all()
            
            if messages:
                conv = session.query(Conversation).filter_by(id=conversation_id).first()
                
                return {
                    "status": "success",
                    "source": "database",
                    "conversation": {
                        "id": conversation_id,
                        "title": conv.title if conv else "Untitled",
                        "created_at": conv.created_at.isoformat() if conv else None,
                        "updated_at": conv.updated_at.isoformat() if conv else None,
                        "message_count": len(messages),
                        "messages": [msg.to_dict() for msg in messages]
                    }
                }
        finally:
            session.close()
        
        # Check cache
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
        """Search through message content using database."""
        logger.info(f"Searching for '{query}' in messages")
        
        if not query:
            return {
                "status": "error",
                "error": "Search query cannot be empty"
            }
        
        # Use database search
        try:
            results = self.search_engine.text_search.search_messages(query, limit=limit)
            
            return {
                "status": "success",
                "source": "database",
                "query": query,
                "case_sensitive": case_sensitive,
                "total_results": len(results),
                "results": results
            }
        except Exception as e:
            logger.error(f"Database search failed: {e}")
        
        # Fallback to file search
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
                "source": "files",
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
    
    # New v0.5.0 methods
    
    async def _export_to_obsidian(
        self,
        conversation_ids: List[str],
        vault_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Export conversations to Obsidian vault format."""
        logger.info(f"Exporting {len(conversation_ids)} conversations to Obsidian")
        
        if vault_path:
            self.obsidian_exporter = ObsidianExporter(vault_path)
        
        results = []
        failed = []
        
        session = self.Session()
        try:
            for conv_id in conversation_ids:
                try:
                    # Get conversation and messages from database
                    conv = session.query(Conversation).filter_by(id=conv_id).first()
                    if not conv:
                        failed.append({
                            'conversation_id': conv_id,
                            'error': 'Conversation not found'
                        })
                        continue
                    
                    messages = session.query(Message).filter_by(
                        conversation_id=conv_id
                    ).order_by(Message.index).all()
                    
                    # Export
                    filepath = self.obsidian_exporter.export_conversation(
                        conv.to_dict(),
                        [msg.to_dict() for msg in messages]
                    )
                    results.append(filepath)
                    
                except Exception as e:
                    failed.append({
                        'conversation_id': conv_id,
                        'error': str(e)
                    })
            
            return {
                "status": "success",
                "exported": len(results),
                "failed": len(failed),
                "vault_path": str(self.obsidian_exporter.vault_path),
                "files": results,
                "errors": failed
            }
            
        finally:
            session.close()
    
    async def _semantic_search(
        self,
        query: str,
        search_type: str = "hybrid",
        top_k: int = 10
    ) -> Dict[str, Any]:
        """Search using semantic similarity."""
        logger.info(f"Performing {search_type} search for: {query}")
        
        results = self.search_engine.search(
            query=query,
            search_type=search_type,
            target='both',
            limit=top_k
        )
        
        return {
            "status": "success",
            "query": query,
            "search_type": search_type,
            "results": results
        }
    
    async def _bulk_operations(
        self,
        operation: str,
        conversation_ids: List[str],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform bulk operations on conversations."""
        logger.info(f"Performing bulk {operation} on {len(conversation_ids)} conversations")
        
        results = {
            "status": "success",
            "operation": operation,
            "processed": 0,
            "failed": 0,
            "details": []
        }
        
        session = self.Session()
        try:
            if operation == "tag":
                tags = params.get("tags", [])
                for conv_id in conversation_ids:
                    try:
                        conv = session.query(Conversation).filter_by(id=conv_id).first()
                        if conv:
                            current_tags = conv.tags or []
                            conv.tags = list(set(current_tags + tags))
                            results["processed"] += 1
                        else:
                            results["failed"] += 1
                    except Exception as e:
                        results["failed"] += 1
                        results["details"].append({
                            "id": conv_id,
                            "error": str(e)
                        })
                
                session.commit()
                
            elif operation == "export":
                format = params.get("format", "json")
                # Delegate to export method
                export_result = await self._export_conversations(
                    "", "", format, conversation_ids, True
                )
                return export_result
                
            elif operation == "delete":
                for conv_id in conversation_ids:
                    try:
                        # Delete messages first
                        session.query(Message).filter_by(
                            conversation_id=conv_id
                        ).delete()
                        
                        # Delete conversation
                        session.query(Conversation).filter_by(
                            id=conv_id
                        ).delete()
                        
                        results["processed"] += 1
                    except Exception as e:
                        results["failed"] += 1
                        results["details"].append({
                            "id": conv_id,
                            "error": str(e)
                        })
                
                session.commit()
                
            elif operation == "analyze":
                # Analyze conversations
                total_messages = 0
                total_chars = 0
                models = {}
                
                for conv_id in conversation_ids:
                    try:
                        messages = session.query(Message).filter_by(
                            conversation_id=conv_id
                        ).all()
                        
                        total_messages += len(messages)
                        total_chars += sum(len(msg.content) for msg in messages)
                        
                        conv = session.query(Conversation).filter_by(id=conv_id).first()
                        if conv:
                            model = conv.model or "unknown"
                            models[model] = models.get(model, 0) + 1
                        
                        results["processed"] += 1
                    except Exception as e:
                        results["failed"] += 1
                
                results["analysis"] = {
                    "total_messages": total_messages,
                    "total_characters": total_chars,
                    "average_messages_per_conversation": total_messages / len(conversation_ids) if conversation_ids else 0,
                    "models_used": models
                }
            
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {operation}"
                }
                
        except Exception as e:
            logger.error(f"Bulk operation failed: {e}")
            results["status"] = "error"
            results["error"] = str(e)
        finally:
            session.close()
        
        return results
    
    async def _get_analytics(self, time_range: str = "all") -> Dict[str, Any]:
        """Get conversation analytics."""
        logger.info(f"Getting analytics for time range: {time_range}")
        
        session = self.Session()
        try:
            # Calculate date filter
            now = datetime.now()
            if time_range == "day":
                start_date = now - timedelta(days=1)
            elif time_range == "week":
                start_date = now - timedelta(weeks=1)
            elif time_range == "month":
                start_date = now - timedelta(days=30)
            elif time_range == "year":
                start_date = now - timedelta(days=365)
            else:
                start_date = None
            
            # Build query
            query = session.query(Conversation)
            if start_date:
                query = query.filter(Conversation.created_at >= start_date)
            
            conversations = query.all()
            
            # Calculate statistics
            total_conversations = len(conversations)
            total_messages = sum(conv.message_count for conv in conversations)
            
            # Model distribution
            model_dist = {}
            for conv in conversations:
                model = conv.model or "unknown"
                model_dist[model] = model_dist.get(model, 0) + 1
            
            # Time distribution
            daily_dist = {}
            for conv in conversations:
                date_key = conv.created_at.strftime("%Y-%m-%d")
                daily_dist[date_key] = daily_dist.get(date_key, 0) + 1
            
            # Message statistics
            message_counts = [conv.message_count for conv in conversations]
            avg_messages = sum(message_counts) / len(message_counts) if message_counts else 0
            max_messages = max(message_counts) if message_counts else 0
            min_messages = min(message_counts) if message_counts else 0
            
            # Search statistics
            search_stats = self.search_engine.get_search_stats()
            
            return {
                "status": "success",
                "time_range": time_range,
                "statistics": {
                    "total_conversations": total_conversations,
                    "total_messages": total_messages,
                    "average_messages_per_conversation": avg_messages,
                    "max_messages_in_conversation": max_messages,
                    "min_messages_in_conversation": min_messages,
                    "model_distribution": model_dist,
                    "daily_distribution": daily_dist,
                    "search_capabilities": search_stats
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            session.close()
    
    async def _migrate_to_database(self, verify: bool = True) -> Dict[str, Any]:
        """Migrate JSON files to database."""
        logger.info("Starting migration to database")
        
        # Import and run migration
        from deployment.scripts.migrate_data import DataMigrator
        
        try:
            migrator = DataMigrator(
                json_dir=str(self.extracted_messages_dir),
                db_path=str(self.db_path)
            )
            
            migrator.migrate()
            
            if verify:
                migrator.verify_migration()
            
            return {
                "status": "success",
                "message": "Migration completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _rebuild_search_index(self, index_type: str = "both") -> Dict[str, Any]:
        """Rebuild search indexes."""
        logger.info(f"Rebuilding {index_type} search index")
        
        try:
            if index_type in ["text", "both"]:
                self.search_engine.text_search.rebuild_search_index()
                
            if index_type in ["semantic", "both"]:
                self.search_engine.semantic_search.build_indexes()
            
            # Optimize after rebuild
            self.search_engine.optimize_indexes()
            
            return {
                "status": "success",
                "message": f"Search index ({index_type}) rebuilt successfully",
                "stats": self.search_engine.get_search_stats()
            }
            
        except Exception as e:
            logger.error(f"Index rebuild failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _get_rate_limit_metrics(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get rate limiting metrics and API usage statistics."""
        logger.info(f"Getting rate limit metrics for endpoint: {endpoint or 'all'}")
        
        try:
            # Get rate limiter metrics
            rate_metrics = self.rate_limiter.get_metrics(endpoint)
            
            # Get queue metrics
            queue_metrics = self.queue_manager.get_all_metrics()
            
            # Build response
            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "rate_limit_config": {
                    "requests_per_second": self.rate_limiter.config.requests_per_second,
                    "burst_size": self.rate_limiter.config.burst_size,
                    "max_retries": self.rate_limiter.config.max_retries
                }
            }
            
            if endpoint:
                # Single endpoint metrics
                result["endpoint"] = endpoint
                result["metrics"] = rate_metrics
                result["queue"] = queue_metrics.get(endpoint, {})
            else:
                # All endpoints metrics
                result["endpoints"] = rate_metrics
                result["queues"] = queue_metrics
                
                # Calculate summary stats
                total_requests = sum(
                    m.get("total_requests", 0) 
                    for m in rate_metrics.values()
                )
                result["summary"] = {
                    "total_requests": total_requests,
                    "active_endpoints": len(rate_metrics),
                    "total_queued": sum(
                        q.get("queue_size", 0) 
                        for q in queue_metrics.values()
                    )
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get rate limit metrics: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            initialization_options = InitializationOptions(
                server_name="claude-context-direct",
                server_version="0.5.0",
                capabilities=ServerCapabilities(),
                instructions="Enhanced MCP server v0.5.0 for Claude.ai conversations. Features include SQLite database storage, semantic search, multiple export formats (Obsidian, PDF), and bulk operations. API tools require session_key and org_id. Message tools work with locally extracted data or database."
            )
            await self.server.run(read_stream, write_stream, initialization_options)


async def main():
    """Main entry point."""
    server = DirectAPIClaudeContextServer()
    try:
        await server.start()
        await server.run()
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
