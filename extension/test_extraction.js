// Test extraction script - paste this in Chrome console on claude.ai

// Extract conversation ID from URL
const getConversationId = () => {
  const match = window.location.pathname.match(/\/chat\/([a-f0-9-]+)/);
  return match ? match[1] : null;
};

// Extract conversation title
const getConversationTitle = () => {
  // Try multiple selectors
  const selectors = [
    'h1',
    '[data-testid="conversation-title"]',
    '.conversation-title',
    'header h1'
  ];
  
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element && element.textContent) {
      return element.textContent.trim();
    }
  }
  return 'Untitled Conversation';
};

// Extract messages
const extractMessages = () => {
  const messages = [];
  
  // Try multiple message selectors
  const messageSelectors = [
    '[data-testid^="message-"]',
    '.message-content',
    '[role="article"]',
    'div[class*="message"]'
  ];
  
  let messageElements = [];
  for (const selector of messageSelectors) {
    const elements = document.querySelectorAll(selector);
    if (elements.length > 0) {
      messageElements = elements;
      console.log(`Found ${elements.length} messages using selector: ${selector}`);
      break;
    }
  }
  
  messageElements.forEach((element, index) => {
    // Determine role
    let role = 'unknown';
    if (element.classList.contains('user-message') || element.textContent.includes('You')) {
      role = 'user';
    } else if (element.classList.contains('assistant-message') || element.textContent.includes('Claude')) {
      role = 'assistant';
    }
    
    // Extract content
    const contentElement = element.querySelector('.prose, .message-text, p') || element;
    const content = contentElement.textContent?.trim() || '';
    
    if (content) {
      messages.push({
        id: `msg-${index}`,
        role: role,
        content: content,
        timestamp: new Date().toISOString()
      });
    }
  });
  
  return messages;
};

// Test extraction
console.log('Starting extraction test...');

const conversationId = getConversationId();
const title = getConversationTitle();
const messages = extractMessages();

console.log('Extraction results:');
console.log('- Conversation ID:', conversationId);
console.log('- Title:', title);
console.log('- Messages found:', messages.length);
console.log('- First few messages:', messages.slice(0, 3));

// Send to bridge server
if (conversationId && messages.length > 0) {
  console.log('Sending to bridge server...');
  
  // First send conversation metadata
  fetch('http://localhost:8765/api/conversation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      id: conversationId,
      title: title,
      url: window.location.href,
      message_count: messages.length
    })
  })
  .then(r => r.json())
  .then(data => {
    console.log('Conversation metadata sent:', data);
    
    // Then send messages
    return fetch('http://localhost:8765/api/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_id: conversationId,
        title: title,
        messages: messages
      })
    });
  })
  .then(r => r.json())
  .then(data => {
    console.log('Messages sent:', data);
    console.log('✅ Extraction complete! Check /Users/hamzaamjad/mcp-claude-context/extracted_messages/');
  })
  .catch(error => {
    console.error('❌ Error sending to bridge server:', error);
  });
} else {
  console.error('❌ No conversation ID or messages found. Make sure you\'re on a conversation page.');
}