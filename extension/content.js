/**
 * Claude Context Bridge - Content Script (Improved)
 * Extracts conversation and message data from Claude.ai web interface
 */

console.log('[Claude Context Bridge] Content script loaded');

// Get conversation ID from URL
function getConversationId() {
  const match = window.location.pathname.match(/\/chat\/([a-f0-9-]+)/);
  return match ? match[1] : null;
}

// Extract conversation title - try multiple selectors
function getConversationTitle() {
  const selectors = [
    'h1.text-lg.font-medium',  // Current Claude UI
    'h1',
    '[data-testid="conversation-title"]',
    '.conversation-title',
    'header h1'
  ];
  
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element && element.textContent && !element.textContent.includes('Claude')) {
      return element.textContent.trim();
    }
  }
  
  // If no title found, try to get from first user message
  const firstMessage = document.querySelector('[data-testid^="message-"]');
  if (firstMessage) {
    const text = firstMessage.textContent || '';
    return text.slice(0, 50) + (text.length > 50 ? '...' : '');
  }
  
  return 'Untitled Conversation';
}

// Extract messages with better role detection
function extractMessages() {
  const messages = [];
  
  // Updated selectors for current Claude UI
  const messageSelectors = [
    'div[data-testid^="message-"]',
    'div[class*="group/message"]',
    'div[class*="message-content"]',
    'article[role="article"]'
  ];
  
  let messageElements = [];
  for (const selector of messageSelectors) {
    const elements = document.querySelectorAll(selector);
    if (elements.length > 0) {
      messageElements = Array.from(elements);
      console.log(`[Claude Context Bridge] Found ${elements.length} messages using selector: ${selector}`);
      break;
    }
  }
  
  messageElements.forEach((element, index) => {
    // Better role detection
    let role = 'unknown';
    const elementText = element.textContent || '';
    const elementClasses = element.className || '';
    
    // Check for user message indicators
    if (elementClasses.includes('user') || 
        element.querySelector('[data-testid*="user"]') ||
        element.closest('[data-testid*="user"]')) {
      role = 'user';
    }
    // Check for assistant message indicators
    else if (elementClasses.includes('assistant') || 
             element.querySelector('[data-testid*="assistant"]') ||
             element.closest('[data-testid*="assistant"]')) {
      role = 'assistant';
    }
    // Fallback: check position or content
    else if (index % 2 === 0) {
      role = 'user';  // Typically conversations start with user
    } else {
      role = 'assistant';
    }
    
    // Extract content - get all text within the message
    let content = '';
    const textElements = element.querySelectorAll('p, div.prose, div[class*="text"]');
    if (textElements.length > 0) {
      textElements.forEach(el => {
        content += el.textContent + '\n';
      });
    } else {
      content = element.textContent || '';
    }
    
    content = content.trim();
    
    if (content && content.length > 0) {
      messages.push({
        id: `msg-${index}`,
        role: role,
        content: content,
        timestamp: new Date().toISOString()
      });
    }
  });
  
  return messages;
}

// Send to bridge server
async function sendToBridgeServer(conversationId, title, messages) {
  try {
    // First send conversation metadata
    const metadataResponse = await fetch('http://localhost:8765/api/conversation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: conversationId,
        title: title,
        url: window.location.href,
        message_count: messages.length
      })
    });
    
    if (!metadataResponse.ok) {
      throw new Error(`Metadata request failed: ${metadataResponse.status}`);
    }
    
    const metadataResult = await metadataResponse.json();
    console.log('[Claude Context Bridge] Metadata sent:', metadataResult);
    
    // Then send messages
    const messagesResponse = await fetch('http://localhost:8765/api/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_id: conversationId,
        title: title,
        messages: messages
      })
    });
    
    if (!messagesResponse.ok) {
      throw new Error(`Messages request failed: ${messagesResponse.status}`);
    }
    
    const messagesResult = await messagesResponse.json();
    console.log('[Claude Context Bridge] Messages sent:', messagesResult);
    
    return {
      success: true,
      messageCount: messages.length,
      data: { title, conversationId }
    };
    
  } catch (error) {
    console.error('[Claude Context Bridge] Error sending to bridge server:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// Handle extract conversation request
async function handleExtractConversation() {
  const conversationId = getConversationId();
  if (!conversationId) {
    return {
      success: false,
      error: 'No conversation ID found. Make sure you\'re on a conversation page.'
    };
  }
  
  const title = getConversationTitle();
  const messages = extractMessages();
  
  console.log(`[Claude Context Bridge] Extracting conversation: ${conversationId}`);
  console.log(`Title: ${title}, Messages: ${messages.length}`);
  
  return await sendToBridgeServer(conversationId, title, messages);
}

// Handle extract messages request (same as extract conversation for now)
async function handleExtractMessages() {
  return handleExtractConversation();
}

// Listen for messages from popup or background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[Claude Context Bridge] Received message:', request);
  
  switch (request.action) {
    case 'extract_conversations':
    case 'extract_conversation':
    case 'extract':
      handleExtractConversation().then(sendResponse);
      return true; // Keep message channel open for async response
      
    case 'extract_messages':
      handleExtractMessages().then(sendResponse);
      return true;
      
    default:
      sendResponse({ success: false, error: 'Unknown action: ' + request.action });
  }
});

// Notify background script that content script is ready
chrome.runtime.sendMessage({ action: 'content_script_ready' });

console.log('[Claude Context Bridge] Content script initialized');