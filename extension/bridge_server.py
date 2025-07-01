#!/usr/bin/env python3
"""Bridge server for Claude Context browser extension."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from aiohttp import web
from aiohttp.web import Request, Response, json_response
import aiohttp_cors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Storage directory for extracted conversations
STORAGE_DIR = Path("/Users/hamzaamjad/mcp-claude-context/extracted_messages")
STORAGE_DIR.mkdir(exist_ok=True)


class BridgeServer:
    """HTTP server that receives messages from the browser extension."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.conversations: Dict[str, Any] = {}
        self._setup_routes()
        self._setup_cors()
        
    def _setup_routes(self):
        """Set up HTTP routes."""
        self.app.router.add_post('/api/conversation', self.handle_conversation)
        self.app.router.add_post('/api/messages', self.handle_messages)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/api/conversations', self.list_conversations)
        self.app.router.add_get('/api/conversations/{conv_id}', self.check_conversation)
        self.app.router.add_get('/api/analytics', self.get_analytics)
        self.app.router.add_get('/dashboard', self.serve_dashboard)
        self.app.router.add_get('/', self.serve_dashboard)
        
    def _setup_cors(self):
        """Set up CORS for browser extension access."""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Configure CORS on all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def handle_conversation(self, request: Request) -> Response:
        """Handle conversation metadata from extension."""
        try:
            data = await request.json()
            conv_id = data.get('id')
            
            if not conv_id:
                return json_response({'error': 'Missing conversation ID'}, status=400)
            
            # Store conversation metadata
            self.conversations[conv_id] = {
                'id': conv_id,
                'title': data.get('title', 'Untitled'),
                'created_at': data.get('created_at'),
                'updated_at': datetime.now().isoformat(),
                'message_count': data.get('message_count', 0),
                'url': data.get('url'),
                'extracted_at': datetime.now().isoformat()
            }
            
            # Save to file
            await self._save_conversation(conv_id, self.conversations[conv_id])
            
            logger.info(f"Received conversation: {conv_id} - {data.get('title')}")
            
            return json_response({
                'status': 'success',
                'conversation_id': conv_id,
                'message': 'Conversation metadata saved'
            })
            
        except Exception as e:
            logger.error(f"Error handling conversation: {e}")
            return json_response({'error': str(e)}, status=500)
    
    async def handle_messages(self, request: Request) -> Response:
        """Handle messages from extension."""
        try:
            data = await request.json()
            conv_id = data.get('conversation_id')
            messages = data.get('messages', [])
            
            if not conv_id:
                return json_response({'error': 'Missing conversation ID'}, status=400)
            
            # Update conversation with messages
            if conv_id in self.conversations:
                self.conversations[conv_id]['messages'] = messages
                self.conversations[conv_id]['message_count'] = len(messages)
                self.conversations[conv_id]['updated_at'] = datetime.now().isoformat()
            else:
                # Create new conversation entry
                self.conversations[conv_id] = {
                    'id': conv_id,
                    'title': data.get('title', 'Untitled'),
                    'messages': messages,
                    'message_count': len(messages),
                    'extracted_at': datetime.now().isoformat()
                }
            
            # Save complete conversation with messages
            await self._save_conversation(conv_id, self.conversations[conv_id], include_messages=True)
            
            logger.info(f"Received {len(messages)} messages for conversation: {conv_id}")
            
            return json_response({
                'status': 'success',
                'conversation_id': conv_id,
                'message_count': len(messages),
                'message': 'Messages saved successfully'
            })
            
        except Exception as e:
            logger.error(f"Error handling messages: {e}")
            return json_response({'error': str(e)}, status=500)
    
    async def handle_status(self, request: Request) -> Response:
        """Handle status check."""
        return json_response({
            'status': 'running',
            'conversations_cached': len(self.conversations),
            'server_time': datetime.now().isoformat(),
            'storage_path': str(STORAGE_DIR)
        })
    
    async def list_conversations(self, request: Request) -> Response:
        """List all extracted conversations."""
        conversations_list = []
        
        for conv_id, conv_data in self.conversations.items():
            conversations_list.append({
                'id': conv_id,
                'title': conv_data.get('title'),
                'message_count': conv_data.get('message_count', 0),
                'extracted_at': conv_data.get('extracted_at'),
                'has_messages': 'messages' in conv_data
            })
        
        return json_response({
            'status': 'success',
            'count': len(conversations_list),
            'conversations': conversations_list
        })
    
    async def check_conversation(self, request: Request) -> Response:
        """Check if a specific conversation has been extracted."""
        conv_id = request.match_info.get('conv_id')
        
        # Check in memory
        if conv_id in self.conversations:
            return json_response({
                'status': 'success',
                'exists': True,
                'data': self.conversations[conv_id]
            })
        
        # Check on disk
        conv_dir = STORAGE_DIR / conv_id
        if conv_dir.exists() and (conv_dir / "messages.json").exists():
            # Load it into memory
            try:
                metadata_file = conv_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        self.conversations[conv_id] = metadata
                        return json_response({
                            'status': 'success',
                            'exists': True,
                            'data': metadata
                        })
            except Exception as e:
                logger.error(f"Error loading conversation {conv_id}: {e}")
        
        return json_response({
            'status': 'success',
            'exists': False
        }, status=404)
    
    async def _save_conversation(self, conv_id: str, data: Dict[str, Any], include_messages: bool = False):
        """Save conversation to disk."""
        try:
            # Create conversation directory
            conv_dir = STORAGE_DIR / conv_id
            conv_dir.mkdir(exist_ok=True)
            
            # Save metadata
            metadata_file = conv_dir / "metadata.json"
            metadata = {k: v for k, v in data.items() if k != 'messages'}
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Save messages if included
            if include_messages and 'messages' in data:
                messages_file = conv_dir / "messages.json"
                with open(messages_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'conversation_id': conv_id,
                        'message_count': len(data['messages']),
                        'messages': data['messages']
                    }, f, indent=2, ensure_ascii=False)
                
                # Also save as readable text
                text_file = conv_dir / "conversation.txt"
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(f"Conversation: {data.get('title', 'Untitled')}\n")
                    f.write(f"ID: {conv_id}\n")
                    f.write(f"Extracted: {data.get('extracted_at', 'Unknown')}\n")
                    f.write("=" * 80 + "\n\n")
                    
                    for msg in data['messages']:
                        f.write(f"[{msg.get('role', 'unknown').upper()}]\n")
                        f.write(f"{msg.get('content', '')}\n")
                        f.write("-" * 40 + "\n\n")
            
        except Exception as e:
            logger.error(f"Error saving conversation {conv_id}: {e}")
    
    async def get_analytics(self, request: Request) -> Response:
        """Get analytics data for all conversations."""
        analytics_data = []
        
        # Load all conversations from disk
        if STORAGE_DIR.exists():
            for conv_dir in STORAGE_DIR.iterdir():
                if not conv_dir.is_dir():
                    continue
                
                try:
                    # Load metadata
                    metadata_file = conv_dir / "metadata.json"
                    messages_file = conv_dir / "messages.json"
                    
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        # Add message data if available
                        if messages_file.exists():
                            with open(messages_file, 'r', encoding='utf-8') as f:
                                messages_data = json.load(f)
                                metadata['messages'] = messages_data.get('messages', [])
                                metadata['message_count'] = len(metadata['messages'])
                        
                        analytics_data.append(metadata)
                except Exception as e:
                    logger.error(f"Error loading conversation {conv_dir.name}: {e}")
        
        return json_response({
            'status': 'success',
            'conversations': analytics_data,
            'total': len(analytics_data)
        })
    
    async def serve_dashboard(self, request: Request) -> Response:
        """Serve the analytics dashboard."""
        dashboard_path = Path(__file__).parent / "dashboard.html"
        
        if dashboard_path.exists():
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return web.Response(text=content, content_type='text/html')
        else:
            return web.Response(text="Dashboard not found", status=404)
    
    def run(self):
        """Run the bridge server."""
        logger.info(f"Starting bridge server on http://{self.host}:{self.port}")
        logger.info(f"Storage directory: {STORAGE_DIR}")
        logger.info(f"Analytics dashboard: http://{self.host}:{self.port}/dashboard")
        logger.info("Waiting for messages from browser extension...")
        
        web.run_app(
            self.app,
            host=self.host,
            port=self.port,
            print=lambda x: None  # Suppress aiohttp startup message
        )


if __name__ == "__main__":
    # Check if aiohttp-cors is installed
    try:
        import aiohttp_cors
    except ImportError:
        print("Error: aiohttp-cors not installed. Run: poetry add aiohttp-cors")
        exit(1)
    
    # Run the server directly without asyncio.run
    try:
        server = BridgeServer()
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down bridge server...")