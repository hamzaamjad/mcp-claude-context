/**
 * Claude Context Bridge - Content Script
 * Extracts conversation and message data from Claude.ai web interface
 */

console.log('[Claude Context Bridge] Content script loaded');

// Configuration
const LOCAL_SERVER_URL = 'http://localhost:8765';  // Local MCP bridge server

/**
 * Extract conversation data from the DOM
 */
function extractConversations() {
  const conversations = [];
  
  // Look for conversation list in sidebar
  const conversationElements = document.querySelectorAll('[data-testid="conversation-item"], [role="listitem"]');
  
  conversationElements.forEach((elem) => {
    const nameElem = elem.querySelector('[class*="ConversationTitle"], [class*="conversation-name"]');
    const name = nameElem ? nameElem.textContent.trim() : 'Untitled';
    
    // Try to extract conversation ID from element attributes or links
    let conversationId = null;
    const linkElem = elem.querySelector('a[href*="/chat/"]');
    if (linkElem) {
      const match = linkElem.href.match(/\/chat\/([a-f0-9-]+)/);
      if (match) {
        conversationId = match[1];
      }
    }
    
    if (conversationId) {
      conversations.push({
        id: conversationId,
        name: name,
        url: `https://claude.ai/chat/${conversationId}`
      });
    }
  });
  
  return conversations;
}

/**
 * Extract messages from the current conversation
 */
function extractMessages() {
  const messages = [];
  
  // Look for message elements
  const messageElements = document.querySelectorAll('[data-testid="message"], [class*="Message"], [role="article"]');
  
  messageElements.forEach((elem, index) => {
    // Determine role (user or assistant)
    const isUserMessage = elem.classList.toString().includes('user') || 
                         elem.querySelector('[data-testid="user-message"]') !== null;
    
    // Extract text content
    const textElements = elem.querySelectorAll('p, div[class*="text"], div[class*="content"]');
    let content = '';
    textElements.forEach(textElem => {
      content += textElem.textContent + '\n';
    });
    
    // Extract any code blocks
    const codeBlocks = elem.querySelectorAll('pre, code');
    codeBlocks.forEach(codeElem => {
      content += '\n```\n' + codeElem.textContent + '\n```\n';
    });
    
    if (content.trim()) {
      messages.push({
        index: index,
        role: isUserMessage ? 'user' : 'assistant',
        content: content.trim(),
        timestamp: new Date().toISOString()
      });
    }
  });
  
  return messages;
}

/**
 * Extract current conversation metadata
 */
function extractCurrentConversation() {
  // Try to get conversation ID from URL
  const urlMatch = window.location.href.match(/\/chat\/([a-f0-9-]+)/);
  const conversationId = urlMatch ? urlMatch[1] : null;
  
  // Try to get conversation name from title or header
  let conversationName = document.title;
  const headerElem = document.querySelector('h1, [class*="ConversationHeader"], [class*="conversation-title"]');
  if (headerElem) {
    conversationName = headerElem.textContent.trim();
  }
  
  return {
    id: conversationId,
    name: conversationName,
    url: window.location.href,
    extractedAt: new Date().toISOString()
  };
}

/**
 * Send data to local MCP bridge server
 */
async function sendToLocalServer(endpoint, data) {
  try {
    const response = await fetch(`${LOCAL_SERVER_URL}/${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      throw new Error(`Server responded with ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('[Claude Context Bridge] Failed to send data to local server:', error);
    return { error: error.message };
  }
}

/**
 * Listen for messages from background script
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[Claude Context Bridge] Received message:', request);
  
  switch (request.action) {
    case 'extract_conversations':
      const conversations = extractConversations();
      sendResponse({ conversations });
      break;
      
    case 'extract_messages':
      const messages = extractMessages();
      const conversation = extractCurrentConversation();
      sendResponse({ conversation, messages });
      break;
      
    case 'extract_all':
      sendResponse({
        conversations: extractConversations(),
        currentConversation: extractCurrentConversation(),
        messages: extractMessages()
      });
      break;
      
    case 'sync_to_local':
      // Extract and send to local server
      const data = {
        conversations: extractConversations(),
        currentConversation: extractCurrentConversation(),
        messages: extractMessages()
      };
      sendToLocalServer('sync', data).then(result => {
        sendResponse({ success: true, result });
      }).catch(error => {
        sendResponse({ success: false, error: error.message });
      });
      return true; // Keep channel open for async response
      
    default:
      sendResponse({ error: 'Unknown action' });
  }
});

/**
 * Monitor DOM changes to detect new messages
 */
const observer = new MutationObserver((mutations) => {
  // Check if new messages were added
  const hasNewMessages = mutations.some(mutation => {
    return Array.from(mutation.addedNodes).some(node => {
      if (node.nodeType === Node.ELEMENT_NODE) {
        return node.matches('[data-testid="message"], [class*="Message"]') ||
               node.querySelector('[data-testid="message"], [class*="Message"]');
      }
      return false;
    });
  });
  
  if (hasNewMessages) {
    console.log('[Claude Context Bridge] New messages detected');
    // Auto-sync if enabled
    chrome.storage.local.get(['autoSync'], (result) => {
      if (result.autoSync) {
        const data = {
          conversation: extractCurrentConversation(),
          messages: extractMessages()
        };
        sendToLocalServer('update', data);
      }
    });
  }
});

// Start observing
const targetNode = document.body;
const config = { childList: true, subtree: true };
observer.observe(targetNode, config);

/**
 * Inject additional script for deeper access if needed
 */
function injectScript() {
  const script = document.createElement('script');
  script.src = chrome.runtime.getURL('inject.js');
  script.onload = function() {
    this.remove();
  };
  (document.head || document.documentElement).appendChild(script);
}

// Wait for page to fully load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', injectScript);
} else {
  injectScript();
}

// Notify background script that content script is ready
chrome.runtime.sendMessage({ action: 'content_script_ready' });

console.log('[Claude Context Bridge] Content script initialized');
