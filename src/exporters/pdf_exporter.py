"""
PDF exporter for conversations using ReportLab
"""

import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import re

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image, Flowable, Preformatted
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.tableofcontents import TableOfContents


class ConversationTOC(TableOfContents):
    """Custom Table of Contents for conversations"""
    
    def __init__(self):
        super().__init__()
        self.levelStyles = [
            ParagraphStyle(name='TOCHeading1', fontSize=14, leading=16, 
                          leftIndent=0, fontName='Helvetica-Bold'),
            ParagraphStyle(name='TOCHeading2', fontSize=12, leading=14, 
                          leftIndent=20, fontName='Helvetica'),
        ]


class PDFExporter:
    """Export conversations to PDF format with professional styling"""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path("exports/pdf")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='ConversationTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30
        ))
        
        # Metadata style
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=12
        ))
        
        # Message header styles
        self.styles.add(ParagraphStyle(
            name='UserMessage',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#0066cc'),
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='AssistantMessage',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#008844'),
            spaceAfter=6
        ))
        
        # Code block style
        self.styles.add(ParagraphStyle(
            name='CodeBlock',
            parent=self.styles['Code'],
            fontSize=9,
            leftIndent=20,
            rightIndent=20,
            backColor=colors.HexColor('#f5f5f5'),
            borderColor=colors.HexColor('#dddddd'),
            borderWidth=1,
            borderPadding=10,
            spaceAfter=12
        ))
        
        # Content style
        self.styles.add(ParagraphStyle(
            name='MessageContent',
            parent=self.styles['Normal'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        ))
    
    def export_conversation(self, conversation: Dict, messages: List[Dict]) -> str:
        """Export a single conversation to PDF"""
        # Generate filename
        created_date = self._parse_datetime(conversation.get('created_at'))
        safe_title = self._sanitize_filename(conversation.get('title', 'Untitled'))
        filename = f"{created_date.strftime('%Y-%m-%d')}_{safe_title}.pdf"
        filepath = self.output_dir / filename
        
        # Create document
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Build content
        story = []
        
        # Add title page
        story.extend(self._create_title_page(conversation))
        
        # Add table of contents
        toc = ConversationTOC()
        story.append(toc)
        story.append(PageBreak())
        
        # Add messages
        story.extend(self._create_messages_section(messages, toc))
        
        # Add metadata page
        story.append(PageBreak())
        story.extend(self._create_metadata_section(conversation))
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_page_number, 
                 onLaterPages=self._add_page_number)
        
        return str(filepath)
    
    def export_bulk(self, conversations: List[Dict]) -> Dict[str, List[str]]:
        """Export multiple conversations to PDF"""
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
        
        return results
    
    def _create_title_page(self, conversation: Dict) -> List[Flowable]:
        """Create title page elements"""
        elements = []
        
        # Add some space at the top
        elements.append(Spacer(1, 2*inch))
        
        # Title
        title = Paragraph(
            conversation.get('title', 'Untitled Conversation'),
            self.styles['ConversationTitle']
        )
        elements.append(title)
        
        # Subtitle with model info
        model = conversation.get('model', 'Claude')
        subtitle = Paragraph(
            f"<i>Conversation with {model}</i>",
            self.styles['Metadata']
        )
        elements.append(subtitle)
        
        # Date info
        created = self._parse_datetime(conversation.get('created_at'))
        date_info = Paragraph(
            f"Created: {created.strftime('%B %d, %Y at %I:%M %p')}",
            self.styles['Metadata']
        )
        elements.append(date_info)
        
        # Message count
        msg_count = conversation.get('message_count', 0)
        count_info = Paragraph(
            f"Total Messages: {msg_count}",
            self.styles['Metadata']
        )
        elements.append(count_info)
        
        # Add page break
        elements.append(PageBreak())
        
        return elements
    
    def _create_messages_section(self, messages: List[Dict], toc: ConversationTOC) -> List[Flowable]:
        """Create messages section with proper formatting"""
        elements = []
        
        # Section header
        header = Paragraph("Conversation", self.styles['Heading1'])
        elements.append(header)
        toc.addEntry(0, "Conversation", 1)
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Process each message
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = self._parse_datetime(msg.get('created_at'))
            
            # Message header
            if role == 'user':
                header_style = self.styles['UserMessage']
                header_text = f"Human ({timestamp.strftime('%H:%M:%S')})"
            elif role == 'assistant':
                header_style = self.styles['AssistantMessage']
                header_text = f"Claude ({timestamp.strftime('%H:%M:%S')})"
            else:
                header_style = self.styles['Heading3']
                header_text = f"{role.title()} ({timestamp.strftime('%H:%M:%S')})"
            
            header_para = Paragraph(header_text, header_style)
            elements.append(header_para)
            
            # Add to TOC for every 10th message
            if i % 10 == 0:
                toc.addEntry(1, f"Message {i+1}", len(elements))
            
            # Process content
            content_elements = self._process_content(content)
            elements.extend(content_elements)
            
            # Add separator
            if i < len(messages) - 1:
                elements.append(Spacer(1, 0.2*inch))
                # Add a subtle line
                elements.append(Paragraph("<para><font color='#cccccc'>―――――――――――――――――</font></para>", 
                                        self.styles['Normal']))
                elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _process_content(self, content: str) -> List[Flowable]:
        """Process message content into flowables"""
        elements = []
        
        # Split content into paragraphs and code blocks
        parts = self._split_content(content)
        
        for part_type, part_content in parts:
            if part_type == 'code':
                # Format as code block
                code_block = Preformatted(
                    self._escape_xml(part_content),
                    self.styles['CodeBlock']
                )
                elements.append(code_block)
            elif part_type == 'bullet':
                # Format as bullet list
                bullet_items = part_content.strip().split('\n')
                for item in bullet_items:
                    if item.strip():
                        bullet_text = f"• {self._escape_xml(item.strip())}"
                        bullet_para = Paragraph(bullet_text, self.styles['MessageContent'])
                        elements.append(bullet_para)
            else:
                # Regular paragraph
                if part_content.strip():
                    para = Paragraph(
                        self._escape_xml(part_content),
                        self.styles['MessageContent']
                    )
                    elements.append(para)
        
        return elements
    
    def _split_content(self, content: str) -> List[Tuple[str, str]]:
        """Split content into different types of blocks"""
        parts = []
        
        # Pattern for code blocks
        code_pattern = r'```(.*?)```'
        
        # Pattern for bullet lists
        bullet_pattern = r'((?:^[-*•]\s+.*$\n?)+)'
        
        # Split by code blocks first
        current_pos = 0
        
        for match in re.finditer(code_pattern, content, re.DOTALL):
            # Add text before code block
            if match.start() > current_pos:
                text_before = content[current_pos:match.start()]
                parts.extend(self._process_text_block(text_before))
            
            # Add code block
            code_content = match.group(1).strip()
            if '\n' in code_content:
                # Remove language identifier if present
                lines = code_content.split('\n')
                if lines[0] and not ' ' in lines[0]:
                    code_content = '\n'.join(lines[1:])
            parts.append(('code', code_content))
            
            current_pos = match.end()
        
        # Add remaining text
        if current_pos < len(content):
            remaining_text = content[current_pos:]
            parts.extend(self._process_text_block(remaining_text))
        
        return parts
    
    def _process_text_block(self, text: str) -> List[Tuple[str, str]]:
        """Process a text block looking for bullet lists"""
        parts = []
        
        # Split by bullet lists
        bullet_pattern = r'((?:^[-*•]\s+.*$\n?)+)'
        
        current_pos = 0
        for match in re.finditer(bullet_pattern, text, re.MULTILINE):
            # Add text before bullet list
            if match.start() > current_pos:
                text_before = text[current_pos:match.start()]
                if text_before.strip():
                    parts.append(('text', text_before))
            
            # Add bullet list
            parts.append(('bullet', match.group(1)))
            current_pos = match.end()
        
        # Add remaining text
        if current_pos < len(text):
            remaining = text[current_pos:]
            if remaining.strip():
                parts.append(('text', remaining))
        
        return parts
    
    def _create_metadata_section(self, conversation: Dict) -> List[Flowable]:
        """Create metadata section"""
        elements = []
        
        # Header
        header = Paragraph("Conversation Metadata", self.styles['Heading1'])
        elements.append(header)
        elements.append(Spacer(1, 0.3*inch))
        
        # Create metadata table
        metadata_items = [
            ("Conversation ID", conversation.get('id', 'Unknown')),
            ("Title", conversation.get('title', 'Untitled')),
            ("Model", conversation.get('model', 'Unknown')),
            ("Created", self._parse_datetime(conversation.get('created_at')).strftime('%Y-%m-%d %H:%M:%S')),
            ("Updated", self._parse_datetime(conversation.get('updated_at')).strftime('%Y-%m-%d %H:%M:%S')),
            ("Message Count", str(conversation.get('message_count', 0))),
            ("Tags", ', '.join(conversation.get('tags', [])) or 'None'),
        ]
        
        # Add custom metadata
        custom_metadata = conversation.get('metadata', {})
        for key, value in custom_metadata.items():
            metadata_items.append((key.title(), str(value)))
        
        # Create table
        table_data = [[Paragraph(f"<b>{key}</b>", self.styles['Normal']), 
                      Paragraph(str(value), self.styles['Normal'])] 
                     for key, value in metadata_items]
        
        table = Table(table_data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _add_page_number(self, canvas, doc):
        """Add page numbers to PDF"""
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.grey)
        
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        
        canvas.drawRightString(
            doc.pagesize[0] - inch,
            inch / 2,
            text
        )
        
        canvas.restoreState()
    
    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters for ReportLab"""
        if not text:
            return text
        
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&apos;'
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        return text
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            title = title.replace(char, '')
        
        # Replace spaces with underscores
        title = re.sub(r'\s+', '_', title)
        
        # Remove multiple underscores
        title = re.sub(r'_+', '_', title)
        
        # Trim to reasonable length
        if len(title) > 50:
            title = title[:50]
        
        return title.strip('_')
    
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
