"""Playwright-based web extraction for Claude.ai conversations."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import json

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
from pydantic import HttpUrl

from ..models import (
    Conversation,
    ConversationMessage,
    MessageContent,
    MessageRole,
    ConversationSummary,
    ExtractionResult,
    ExtractionConfig,
    ConversationMetadata
)
from ..utils import with_retry, sanitize_url, ExtractionError

logger = logging.getLogger(__name__)


class ClaudeWebExtractor:
    """Extract conversations from Claude.ai using Playwright."""
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()
        self.browser: Optional[Browser] = None
        self.playwright = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
        
    async def initialize(self):
        """Initialize Playwright browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless
        )
        logger.info("Playwright browser initialized")
        
    async def cleanup(self):
        """Clean up browser resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright browser cleaned up")
    
    async def _create_page(self) -> Page:
        """Create a new browser page with session."""
        context = await self.browser.new_context(
            user_agent=self.config.user_agent or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        
        if self.config.session_key:
            # Set session cookie if provided - Claude uses different cookie names
            await context.add_cookies([
                {
                    "name": "sessionKey",
                    "value": self.config.session_key,
                    "domain": ".claude.ai",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax"
                },
                {
                    "name": "__Secure-next-auth.session-token",
                    "value": self.config.session_key,
                    "domain": ".claude.ai",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None"
                }
            ])
            
        page = await context.new_page()
        return page
    
    @with_retry(max_retries=3, initial_delay=2.0)
    async def extract_conversation(self, conversation_url: str) -> ExtractionResult:
        """Extract a specific conversation from Claude.ai."""
        try:
            # Sanitize URL
            conversation_url = sanitize_url(conversation_url)
            
            page = await self._create_page()
            
            try:
                # Navigate to conversation
                await page.goto(conversation_url, wait_until="networkidle", timeout=self.config.timeout * 1000)
                
                # Wait for conversation to load - try multiple selectors
                try:
                    await page.wait_for_selector(
                        "[data-testid='conversation-messages'], .conversation-messages, [role='main']", 
                        timeout=self.config.timeout * 1000
                    )
                except PlaywrightTimeout:
                    # Check if we need to authenticate
                    if await page.locator("text=Sign in").count() > 0:
                        raise ExtractionError("Authentication required. Please provide a valid session_key.")
                    raise
                
                # Extract conversation data
                conversation_data = await self._extract_conversation_data(page, conversation_url)
                
                return ExtractionResult(
                    success=True,
                    conversation=conversation_data
                )
                
            finally:
                await page.close()
            
        except ExtractionError:
            raise  # Let retry decorator handle this
        except Exception as e:
            logger.error(f"Failed to extract conversation: {e}")
            return ExtractionResult(
                success=False,
                error=str(e)
            )
    
    async def _extract_conversation_data(self, page: Page, url: str) -> Conversation:
        """Extract conversation data from the page."""
        # Extract conversation ID from URL
        parsed = urlparse(url)
        conv_id = parsed.path.split('/')[-1]
        
        # Extract title
        title = await page.evaluate("""
            () => {
                const titleEl = document.querySelector('h1, [data-testid="conversation-title"]');
                return titleEl ? titleEl.textContent.trim() : null;
            }
        """)
        
        # Extract messages
        messages_data = await page.evaluate("""
            () => {
                const messages = [];
                const messageEls = document.querySelectorAll('[data-testid^="message-"], .message-content, [role="article"]');
                
                messageEls.forEach((el, index) => {
                    const role = el.getAttribute('data-role') || 
                               (el.classList.contains('user-message') ? 'user' : 'assistant');
                    
                    const textContent = el.querySelector('.message-text, .prose, p')?.textContent?.trim() || 
                                      el.textContent?.trim() || '';
                    
                    if (textContent) {
                        messages.push({
                            id: `msg-${index}`,
                            role: role,
                            content: [{
                                type: 'text',
                                text: textContent
                            }],
                            created_at: new Date().toISOString()
                        });
                    }
                });
                
                return messages;
            }
        """)
        
        # Convert to Pydantic models
        messages = []
        for msg_data in messages_data:
            content = [MessageContent(type=c["type"], text=c.get("text")) for c in msg_data["content"]]
            message = ConversationMessage(
                id=msg_data["id"],
                role=MessageRole(msg_data["role"]),
                content=content,
                created_at=datetime.fromisoformat(msg_data["created_at"].replace('Z', '+00:00'))
            )
            messages.append(message)
        
        # Create conversation object
        conversation = Conversation(
            id=conv_id,
            title=title or f"Conversation {conv_id}",
            messages=messages,
            created_at=messages[0].created_at if messages else datetime.now(),
            updated_at=messages[-1].created_at if messages else datetime.now(),
            url=url,
            metadata=ConversationMetadata()
        )
        
        return conversation
    
    @with_retry(max_retries=3, initial_delay=2.0)
    async def list_conversations(self, limit: int = 20) -> List[ConversationSummary]:
        """List available conversations from Claude.ai."""
        try:
            page = await self._create_page()
            
            try:
                # Navigate to conversations page
                await page.goto("https://claude.ai/chats", wait_until="networkidle", timeout=self.config.timeout * 1000)
                
                # Wait for conversations list to load - try multiple selectors
                try:
                    await page.wait_for_selector(
                        "[data-testid='conversation-list'], .conversations-list, .chat-list, [role='navigation']", 
                        timeout=self.config.timeout * 1000
                    )
                except PlaywrightTimeout:
                    # Check if we need to authenticate
                    if await page.locator("text=Sign in").count() > 0:
                        raise ExtractionError("Authentication required. Please provide a valid session_key.")
                    raise
                
                # Extract conversations list
                conversations_data = await page.evaluate(f"""
                () => {{
                    const conversations = [];
                    const convEls = document.querySelectorAll('[data-testid^="conversation-item-"], .conversation-item, a[href^="/chat/"]');
                    
                    for (let i = 0; i < Math.min(convEls.length, {limit}); i++) {{
                        const el = convEls[i];
                        const href = el.getAttribute('href') || el.querySelector('a')?.getAttribute('href');
                        const title = el.querySelector('.conversation-title, h3, .title')?.textContent?.trim() || 
                                    el.textContent?.trim() || '';
                        
                        if (href) {{
                            const id = href.split('/').pop();
                            conversations.push({{
                                id: id,
                                title: title,
                                url: `https://claude.ai{href}`,
                                created_at: new Date().toISOString(),
                                updated_at: new Date().toISOString(),
                                message_count: 0
                            }});
                        }}
                    }}
                    
                    return conversations;
                }}
            """)
            
            finally:
                await page.close()
            
            # Convert to ConversationSummary objects
            summaries = []
            for conv_data in conversations_data:
                summary = ConversationSummary(
                    id=conv_data["id"],
                    title=conv_data["title"],
                    created_at=datetime.fromisoformat(conv_data["created_at"].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(conv_data["updated_at"].replace('Z', '+00:00')),
                    message_count=conv_data["message_count"],
                    url=conv_data["url"]
                )
                summaries.append(summary)
            
            return summaries
            
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return []
    
    async def monitor_conversations(self, callback, poll_interval: int = 30):
        """Monitor for new conversation updates."""
        logger.info(f"Starting conversation monitoring with {poll_interval}s interval")
        
        last_conversations = set()
        
        while True:
            try:
                # Get current conversations
                conversations = await self.list_conversations()
                current_ids = {conv.id for conv in conversations}
                
                # Check for new conversations
                new_ids = current_ids - last_conversations
                if new_ids:
                    logger.info(f"Found {len(new_ids)} new conversations")
                    for conv in conversations:
                        if conv.id in new_ids:
                            await callback(conv)
                
                last_conversations = current_ids
                
            except Exception as e:
                logger.error(f"Error during monitoring: {e}")
            
            await asyncio.sleep(poll_interval)