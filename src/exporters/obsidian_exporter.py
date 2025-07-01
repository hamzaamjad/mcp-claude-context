"""
Obsidian markdown exporter for conversations
"""

import os
import re
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import json


class ObsidianExporter:
    """Export conversations to Obsidian-compatible markdown format"""
    
    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = Path(vault_path) if vault_path else Path("exports/obsidian")
        self.vault_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.conversations_dir = self.vault_path / "Conversations"
        self.daily_dir = self.vault_path / "Daily Notes"
        self.tags_dir = self.vault_path / "Tags"
        
        for dir_path in [self.conversations_dir, self.daily_dir, self.tags_dir]:
            dir_path.mkdir(exist_ok=True)
    
    def export_conversation(self, conversation: Dict, messages: List[Dict]) -> str:
        """Export a single conversation to Obsidian markdown"""
        
        # Generate filename
        created_date = self._parse_datetime(conversation.get('created_at'))
        safe_title = self._sanitize_filename(conversation.get('title', 'Untitled'))
        filename = f"{created_date.strftime('%Y-%m-%d')} - {safe_title}.md"
        filepath = self.conversations_dir / filename
        
        # Generate content
        content = self._generate_frontmatter(conversation)
        content += self._generate_header(conversation)
        content += self._generate_messages(messages)
        content += self._generate_footer(conversation)
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Update daily note
        self._update_daily_note(created_date, conversation, filename)
        
        # Create tag pages
        self._create_tag_pages(conversation)
        
        return str(filepath)
    
    def export_bulk(self, conversations: List[Dict]) -> Dict[str, List[str]]:
        """Export multiple conversations"""
        results = {
            'success': [],
            'failed': []
        }
        
        for conv_data in conversations:
            try:
                filepath = self.export_conversation(
                    conv_data['conversation'],
                    conv_data['messages']
                )
                results['success'].append(filepath)
            except Exception as e:
                results['failed'].append({
                    'conversation_id': conv_data['conversation'].get('id'),
                    'error': str(e)
                })
        
        # Create index
        self._create_index(results['success'])
        
        return results
    
    def _generate_frontmatter(self, conversation: Dict) -> str:
        """Generate YAML frontmatter for Obsidian"""
        created_at = self._parse_datetime(conversation.get('created_at'))
        updated_at = self._parse_datetime(conversation.get('updated_at'))
        
        frontmatter = "---\n"
        frontmatter += f"title: \"{conversation.get('title', 'Untitled')}\"\n"
        frontmatter += f"created: {created_at.strftime('%Y-%m-%d %H:%M')}\n"
        frontmatter += f"updated: {updated_at.strftime('%Y-%m-%d %H:%M')}\n"
        frontmatter += f"model: {conversation.get('model', 'claude')}\n"
        frontmatter += f"conversation_id: {conversation.get('id')}\n"
        frontmatter += f"message_count: {conversation.get('message_count', 0)}\n"
        
        # Add tags
        tags = conversation.get('tags', [])
        if not tags:
            tags = ['claude-conversation']
        else:
            tags.append('claude-conversation')
        
        frontmatter += f"tags: [{', '.join(tags)}]\n"
        
        # Add custom metadata
        metadata = conversation.get('metadata', {})
        if metadata:
            frontmatter += "metadata:\n"
            for key, value in metadata.items():
                frontmatter += f"  {key}: {value}\n"
        
        frontmatter += "---\n\n"
        return frontmatter
    
    def _generate_header(self, conversation: Dict) -> str:
        """Generate header section"""
        header = f"# {conversation.get('title', 'Untitled Conversation')}\n\n"
        
        # Add navigation links
        header += "> [!info] Navigation\n"
        header += "> - [[Conversations Index|All Conversations]]\n"
        
        created_date = self._parse_datetime(conversation.get('created_at'))
        daily_note = created_date.strftime('%Y-%m-%d')
        header += f"> - [[Daily Notes/{daily_note}|Daily Note]]\n"
        
        # Add related conversations (placeholder for future implementation)
        header += "> - Related: `=this.related`\n\n"
        
        # Add summary section
        header += "## Summary\n\n"
        header += f"- **Model**: {conversation.get('model', 'Unknown')}\n"
        header += f"- **Messages**: {conversation.get('message_count', 0)}\n"
        header += f"- **Duration**: `=this.updated - this.created`\n\n"
        
        return header
    
    def _generate_messages(self, messages: List[Dict]) -> str:
        """Generate message content"""
        content = "## Conversation\n\n"
        
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            text = msg.get('content', '')
            timestamp = self._parse_datetime(msg.get('created_at'))
            
            # Format role
            if role == 'user':
                role_display = "👤 **Human**"
            elif role == 'assistant':
                role_display = "🤖 **Claude**"
            else:
                role_display = f"📋 **{role.title()}**"
            
            # Add message header
            content += f"### {role_display} <small>({timestamp.strftime('%H:%M:%S')})</small>\n\n"
            
            # Process message content
            text = self._process_message_content(text)
            
            content += text + "\n\n"
            
            # Add separator between messages
            if i < len(messages) - 1:
                content += "---\n\n"
        
        return content
    
    def _process_message_content(self, text: str) -> str:
        """Process message content for Obsidian compatibility"""
        # Handle code blocks
        text = self._format_code_blocks(text)
        
        # Convert URLs to Obsidian links
        text = self._convert_urls(text)
        
        # Add potential wikilinks
        text = self._add_wikilinks(text)
        
        # Handle special formatting
        text = self._handle_special_formatting(text)
        
        return text
    
    def _format_code_blocks(self, text: str) -> str:
        """Ensure code blocks are properly formatted"""
        # Fix triple backticks without language
        text = re.sub(r'```\n', '```text\n', text)
        
        # Ensure code blocks have proper spacing
        text = re.sub(r'```(\w+)\n', r'```\1\n', text)
        
        return text
    
    def _convert_urls(self, text: str) -> str:
        """Convert URLs to Obsidian external links"""
        url_pattern = r'(https?://[^\s<>"{}|\\^`\[\]]+)'
        
        def replace_url(match):
            url = match.group(1)
            # Check if URL is already in markdown link
            if text[max(0, match.start()-1)] == '(' and text[min(len(text)-1, match.end())] == ')':
                return url
            return f"[{url}]({url})"
        
        return re.sub(url_pattern, replace_url, text)
    
    def _add_wikilinks(self, text: str) -> str:
        """Add wikilinks for common terms and concepts"""
        # This is a placeholder - in a real implementation, you'd have
        # a dictionary of terms to link
        concepts = {
            'machine learning': '[[Machine Learning]]',
            'neural network': '[[Neural Networks]]',
            'python': '[[Python]]',
            'javascript': '[[JavaScript]]',
        }
        
        for term, link in concepts.items():
            # Case-insensitive replacement, but only for whole words
            pattern = rf'\b{re.escape(term)}\b'
            text = re.sub(pattern, link, text, flags=re.IGNORECASE)
        
        return text
    
    def _handle_special_formatting(self, text: str) -> str:
        """Handle special Obsidian formatting"""
        # Convert headers to proper level
        text = re.sub(r'^#{1,6}\s', lambda m: '#' * (len(m.group(0).strip()) + 2) + ' ', text, flags=re.MULTILINE)
        
        # Add callouts for important sections
        text = re.sub(r'^(Note|Warning|Important|Tip):\s*(.+)$', 
                     r'> [!\1]\n> \2', text, flags=re.MULTILINE)
        
        return text
    
    def _generate_footer(self, conversation: Dict) -> str:
        """Generate footer section"""
        footer = "\n---\n\n"
        footer += "## Metadata\n\n"
        
        # Add conversation details
        footer += "```dataview\n"
        footer += "TABLE WITHOUT ID\n"
        footer += '  "Created" as Created,\n'
        footer += '  "Updated" as Updated,\n'
        footer += '  "Model" as Model,\n'
        footer += '  "Messages" as Messages\n'
        footer += "WHERE file = this.file\n"
        footer += "```\n\n"
        
        # Add backlinks section
        footer += "## Backlinks\n\n"
        footer += "```dataview\n"
        footer += 'LIST FROM [[]] WHERE contains(file.outlinks, this.file.link)\n'
        footer += "```\n\n"
        
        # Add related conversations
        footer += "## Related Conversations\n\n"
        footer += "```dataview\n"
        footer += "TABLE title, created, message_count\n"
        footer += "FROM #claude-conversation\n"
        footer += "WHERE file != this.file\n"
        footer += "AND any(file.tags, (t) => contains(this.file.tags, t))\n"
        footer += "SORT created DESC\n"
        footer += "LIMIT 5\n"
        footer += "```\n"
        
        return footer
    
    def _update_daily_note(self, date: datetime, conversation: Dict, filename: str):
        """Update or create daily note with conversation link"""
        daily_note_path = self.daily_dir / f"{date.strftime('%Y-%m-%d')}.md"
        
        # Read existing content or create new
        if daily_note_path.exists():
            with open(daily_note_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = self._create_daily_note_template(date)
        
        # Add conversation link
        conversation_section = "\n## Claude Conversations\n\n"
        if conversation_section not in content:
            content += conversation_section
        
        # Find the conversation section and add link
        link = f"- [[Conversations/{filename[:-3]}|{conversation.get('title', 'Untitled')}]] - {date.strftime('%H:%M')}\n"
        
        # Insert link after the section header
        section_index = content.find(conversation_section) + len(conversation_section)
        content = content[:section_index] + link + content[section_index:]
        
        # Write updated content
        with open(daily_note_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_daily_note_template(self, date: datetime) -> str:
        """Create daily note template"""
        template = f"# {date.strftime('%Y-%m-%d')} - {date.strftime('%A')}\n\n"
        template += "---\n"
        template += f"date: {date.strftime('%Y-%m-%d')}\n"
        template += "tags: [daily-note]\n"
        template += "---\n\n"
        template += "## Summary\n\n\n"
        template += "## Tasks\n\n- [ ] \n\n"
        template += "## Notes\n\n\n"
        
        return template
    
    def _create_tag_pages(self, conversation: Dict):
        """Create or update tag pages"""
        tags = conversation.get('tags', [])
        
        for tag in tags:
            tag_path = self.tags_dir / f"{tag}.md"
            
            if not tag_path.exists():
                content = f"# Tag: {tag}\n\n"
                content += f"All conversations tagged with #{tag}\n\n"
                content += "```dataview\n"
                content += "TABLE title, created, message_count\n"
                content += f"FROM #claude-conversation AND #{tag}\n"
                content += "SORT created DESC\n"
                content += "```\n"
                
                with open(tag_path, 'w', encoding='utf-8') as f:
                    f.write(content)
    
    def _create_index(self, exported_files: List[str]):
        """Create main index file"""
        index_path = self.vault_path / "Conversations Index.md"
        
        content = "# Claude Conversations Index\n\n"
        content += "---\n"
        content += "tags: [index, claude-conversation]\n"
        content += "---\n\n"
        
        # Statistics
        content += "## Statistics\n\n"
        content += "```dataview\n"
        content += "TABLE WITHOUT ID\n"
        content += '  length(rows) as "Total Conversations",\n'
        content += '  sum(rows.message_count) as "Total Messages",\n'
        content += '  min(rows.created) as "First Conversation",\n'
        content += '  max(rows.created) as "Latest Conversation"\n'
        content += "FROM #claude-conversation\n"
        content += "GROUP BY true\n"
        content += "```\n\n"
        
        # Recent conversations
        content += "## Recent Conversations\n\n"
        content += "```dataview\n"
        content += "TABLE title, created, message_count, model\n"
        content += "FROM #claude-conversation\n"
        content += "SORT created DESC\n"
        content += "LIMIT 20\n"
        content += "```\n\n"
        
        # By model
        content += "## Conversations by Model\n\n"
        content += "```dataview\n"
        content += "TABLE WITHOUT ID\n"
        content += '  model as "Model",\n'
        content += '  length(rows) as "Count",\n'
        content += '  sum(rows.message_count) as "Total Messages"\n'
        content += "FROM #claude-conversation\n"
        content += "GROUP BY model\n"
        content += "```\n\n"
        
        # Search
        content += "## Search\n\n"
        content += "Use Obsidian's search with queries like:\n"
        content += "- `tag:#claude-conversation \"search term\"`\n"
        content += "- `file:(Conversations) created:2024-11`\n"
        
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            title = title.replace(char, '')
        
        # Replace spaces with hyphens
        title = re.sub(r'\s+', '-', title)
        
        # Remove multiple hyphens
        title = re.sub(r'-+', '-', title)
        
        # Trim to reasonable length
        if len(title) > 100:
            title = title[:100]
        
        return title.strip('-')
    
    def _parse_datetime(self, dt_str: Optional[str]) -> datetime:
        """Parse datetime string"""
        if not dt_str:
            return datetime.now()
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            try:
                # Try other common formats
                return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            except:
                return datetime.now()
