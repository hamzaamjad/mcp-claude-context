"""
Notion exporter for conversations (requires Notion API key)
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import json


class NotionExporter:
    """Export conversations to Notion via API"""
    
    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
        self.api_key = api_key or os.environ.get('NOTION_API_KEY')
        self.database_id = database_id or os.environ.get('NOTION_DATABASE_ID')
        
        if not self.api_key:
            raise ValueError("Notion API key is required. Set NOTION_API_KEY environment variable.")
        
        # Note: In a real implementation, you would use the notion-client library
        # For now, this is a placeholder implementation
        
    def export_conversation(self, conversation: Dict, messages: List[Dict]) -> str:
        """Export a single conversation to Notion"""
        # Placeholder implementation
        # In reality, this would:
        # 1. Create a new page in the specified database
        # 2. Set properties (title, date, model, etc.)
        # 3. Add content blocks for each message
        # 4. Return the Notion page URL
        
        page_data = {
            'parent': {'database_id': self.database_id},
            'properties': {
                'Title': {
                    'title': [{
                        'text': {
                            'content': conversation.get('title', 'Untitled')
                        }
                    }]
                },
                'Created': {
                    'date': {
                        'start': conversation.get('created_at', datetime.now().isoformat())
                    }
                },
                'Model': {
                    'select': {
                        'name': conversation.get('model', 'Claude')
                    }
                },
                'Message Count': {
                    'number': conversation.get('message_count', len(messages))
                },
                'Tags': {
                    'multi_select': [
                        {'name': tag} for tag in conversation.get('tags', [])
                    ]
                }
            },
            'children': self._create_content_blocks(messages)
        }
        
        # Simulate API call
        page_id = f"notion-{conversation.get('id', 'unknown')}"
        
        # Save as JSON for now
        output_dir = Path("exports/notion")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{page_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(page_data, f, indent=2)
        
        return f"notion://www.notion.so/{page_id}"
    
    def export_bulk(self, conversations: List[Dict]) -> Dict[str, List[str]]:
        """Export multiple conversations to Notion"""
        results = {
            'success': [],
            'failed': []
        }
        
        for conv_data in conversations:
            try:
                url = self.export_conversation(
                    conv_data['conversation'],
                    conv_data['messages']
                )
                results['success'].append(url)
            except Exception as e:
                results['failed'].append({
                    'conversation_id': conv_data['conversation'].get('id'),
                    'error': str(e)
                })
        
        return results
    
    def _create_content_blocks(self, messages: List[Dict]) -> List[Dict]:
        """Create Notion content blocks from messages"""
        blocks = []
        
        # Add header
        blocks.append({
            'object': 'block',
            'type': 'heading_1',
            'heading_1': {
                'rich_text': [{
                    'type': 'text',
                    'text': {'content': 'Conversation'}
                }]
            }
        })
        
        # Add messages
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('created_at', '')
            
            # Role header
            role_text = "Human" if role == 'user' else "Claude" if role == 'assistant' else role.title()
            blocks.append({
                'object': 'block',
                'type': 'heading_3',
                'heading_3': {
                    'rich_text': [{
                        'type': 'text',
                        'text': {'content': f"{role_text} - {timestamp}"}
                    }]
                }
            })
            
            # Message content
            # Split content into paragraphs
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    if para.startswith('```'):
                        # Code block
                        blocks.append({
                            'object': 'block',
                            'type': 'code',
                            'code': {
                                'rich_text': [{
                                    'type': 'text',
                                    'text': {'content': para.strip('`').strip()}
                                }],
                                'language': 'plain text'
                            }
                        })
                    else:
                        # Regular paragraph
                        blocks.append({
                            'object': 'block',
                            'type': 'paragraph',
                            'paragraph': {
                                'rich_text': [{
                                    'type': 'text',
                                    'text': {'content': para}
                                }]
                            }
                        })
            
            # Add divider between messages
            blocks.append({
                'object': 'block',
                'type': 'divider',
                'divider': {}
            })
        
        return blocks
    
    def create_database(self, parent_page_id: str) -> str:
        """Create a Notion database for conversations"""
        # Placeholder for database creation
        # Would create a database with properties:
        # - Title (title)
        # - Created (date)
        # - Updated (date)
        # - Model (select)
        # - Message Count (number)
        # - Tags (multi_select)
        # - Conversation ID (text)
        
        database_schema = {
            'parent': {'page_id': parent_page_id},
            'title': [{
                'type': 'text',
                'text': {'content': 'Claude Conversations'}
            }],
            'properties': {
                'Title': {'title': {}},
                'Created': {'date': {}},
                'Updated': {'date': {}},
                'Model': {
                    'select': {
                        'options': [
                            {'name': 'Claude', 'color': 'blue'},
                            {'name': 'Claude 2', 'color': 'green'},
                            {'name': 'Claude 3', 'color': 'purple'}
                        ]
                    }
                },
                'Message Count': {'number': {}},
                'Tags': {'multi_select': {}},
                'Conversation ID': {'rich_text': {}}
            }
        }
        
        # Return mock database ID
        return "notion-database-conversations"
