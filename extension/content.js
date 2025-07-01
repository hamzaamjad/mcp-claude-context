/**
 * Claude Context Bridge - Content Script (v2)
 * Enhanced extraction with better title, role detection, and code block preservation
 */

console.log('[Claude Context Bridge v2] Content script loaded');

// Get conversation ID from URL
function getConversationId() {
  const match = window.location.pathname.match(/\/chat\/([a-f0-9-]+)/);
  return match ? match[1] : null;
}

// Extract conversation title with improved logic
function getConversationTitle() {
  // Strategy 1: Look for the title in the sidebar (active conversation)
  const activeConversation = document.querySelector('[data-state="active"] .truncate');
  if (activeConversation && activeConversation.textContent) {
    const title = activeConversation.textContent.trim();
    if (title && !title.includes('New chat')) {
      return title;
    }
  }
  
  // Strategy 2: Look for title in the main conversation area
  const titleSelectors = [
    'h1.text-lg.font-medium.text-text-300',
    'h1[class*="font-medium"]',
    '.conversation-header h1',
    '[role="heading"][aria-level="1"]'
  ];
  
  for (const selector of titleSelectors) {
    const element = document.querySelector(selector);
    if (element && element.textContent) {
      const text = element.textContent.trim();
      if (text && !text.includes('Claude') && text.length > 0) {
        return text;
      }
    }
  }
  
  // Strategy 3: Use first user message as title
  const firstUserMessage = document.querySelector('[data-testid*="user"]:first-of-type .prose');
  if (firstUserMessage && firstUserMessage.textContent) {
    const text = firstUserMessage.textContent.trim();
    return text.slice(0, 80) + (text.length > 80 ? '...' : '');
  }
  
  // Strategy 4: Check meta tags or document title
  const pageTitle = document.title;
  if (pageTitle && !pageTitle.includes('Claude') && pageTitle !== 'Anthropic') {
    return pageTitle;
  }
  
  return 'Untitled Conversation';
}

// Extract code blocks while preserving formatting
function extractCodeBlocks(element) {
  const codeBlocks = [];
  const preElements = element.querySelectorAll('pre');
  
  preElements.forEach(pre => {
    const codeElement = pre.querySelector('code');
    if (codeElement) {
      // Get language from class (e.g., language-python)
      const classes = codeElement.className || '';
      const langMatch = classes.match(/language-(\w+)/);
      const language = langMatch ? langMatch[1] : 'text';
      
      codeBlocks.push({
        language: language,
        code: codeElement.textContent || '',
        formatted: `\`\`\`${language}\n${codeElement.textContent || ''}\n\`\`\``
      });
    }
  });
  
  return codeBlocks;
}

// Enhanced message extraction with better role detection
function extractMessages() {
  const messages = [];
  
  // Look for message containers
  const messageContainers = document.querySelectorAll('[data-testid^="conversation-turn-"]');
  
  if (messageContainers.length === 0) {
    // Fallback to other selectors
    const alternativeSelectors = [
      '.group\\/conversation-turn',
      'div[class*="conversation-turn"]',
      'article[data-scroll-anchor="true"]'
    ];
    
    for (const selector of alternativeSelectors) {
      const elements = document.querySelectorAll(selector);
      if (elements.length > 0) {
        messageContainers.push(...Array.from(elements));
        break;
      }
    }
  }
  
  messageContainers.forEach((container, index) => {
    // Determine role based on data attributes and content
    let role = 'unknown';
    
    // Check data-testid
    const testId = container.getAttribute('data-testid') || '';
    if (testId.includes('user')) {
      role = 'user';
    } else if (testId.includes('assistant')) {
      role = 'assistant';
    }
    
    // Check for human/assistant indicators in the DOM
    if (role === 'unknown') {
      const humanIcon = container.querySelector('[data-testid="human-icon"]');
      const assistantIcon = container.querySelector('[data-testid="assistant-icon"]');
      
      if (humanIcon) {
        role = 'user';
      } else if (assistantIcon) {
        role = 'assistant';
      }
    }
    
    // Extract message content with proper formatting
    let content = '';
    const proseElements = container.querySelectorAll('.prose');
    
    if (proseElements.length > 0) {
      proseElements.forEach(prose => {
        // Clone the element to manipulate without affecting the DOM
        const clone = prose.cloneNode(true);
        
        // Handle code blocks specially
        const codeBlocks = extractCodeBlocks(clone);
        
        // Replace code blocks with placeholders
        const preElements = clone.querySelectorAll('pre');
        preElements.forEach((pre, i) => {
          const placeholder = document.createElement('div');
          placeholder.textContent = `[CODE_BLOCK_${i}]`;
          pre.replaceWith(placeholder);
        });
        
        // Get text content
        let text = clone.textContent || '';
        
        // Restore code blocks
        codeBlocks.forEach((block, i) => {
          text = text.replace(`[CODE_BLOCK_${i}]`, block.formatted);
        });
        
        content += text + '\n';
      });
    } else {
      // Fallback to getting all text content
      content = container.textContent || '';
    }
    
    content = content.trim();
    
    // Extract timestamp if available
    let timestamp = null;
    const timeElement = container.querySelector('time');
    if (timeElement) {
      timestamp = timeElement.getAttribute('datetime') || timeElement.textContent;
    }
    
    if (content && content.length > 0) {
      messages.push({
        id: `msg-${index}`,
        role: role,
        content: content,
        timestamp: timestamp || new Date().toISOString(),
        index: index
      });
    }
  });
  
  // If no messages found with primary method, try alternative extraction
  if (messages.length === 0) {
    console.log('[Claude Context Bridge v2] No messages found with primary method, trying alternative...');
    
    // Look for any divs that might contain messages
    const allDivs = document.querySelectorAll('div[class*="prose"], div[class*="whitespace-pre-wrap"]');
    let lastRole = 'user'; // Assume conversation starts with user
    
    allDivs.forEach((div, index) => {
      const content = div.textContent?.trim();
      if (content && content.length > 10) { // Skip very short content
        messages.push({
          id: `msg-${index}`,
          role: index % 2 === 0 ? 'user' : 'assistant',
          content: content,
          timestamp: new Date().toISOString(),
          index: index
        });
      }
    });
  }
  
  return messages;
}

// Extract additional conversation metadata
function extractConversationMetadata() {
  const metadata = {
    model: null,
    createdAt: null,
    lastMessageAt: null
  };
  
  // Try to find model information
  const modelElement = document.querySelector('[data-testid="model-selector"]');
  if (modelElement) {
    metadata.model = modelElement.textContent?.trim();
  }
  
  // Look for timestamps
  const timeElements = document.querySelectorAll('time');
  if (timeElements.length > 0) {
    metadata.createdAt = timeElements[0].getAttribute('datetime');
    metadata.lastMessageAt = timeElements[timeElements.length - 1].getAttribute('datetime');
  }
  
  return metadata;
}

// Send to bridge server with enhanced data
async function sendToBridgeServer(conversationId, title, messages, metadata) {
  try {
    // Send conversation metadata
    const metadataResponse = await fetch('http://localhost:8765/api/conversation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: conversationId,
        title: title,
        url: window.location.href,
        message_count: messages.length,
        created_at: metadata.createdAt,
        model: metadata.model
      })
    });
    
    if (!metadataResponse.ok) {
      throw new Error(`Metadata request failed: ${metadataResponse.status}`);
    }
    
    // Send messages
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
    
    const result = await messagesResponse.json();
    console.log('[Claude Context Bridge v2] Extraction complete:', result);
    
    return {
      success: true,
      messageCount: messages.length,
      data: { 
        title, 
        conversationId,
        metadata
      }
    };
    
  } catch (error) {
    console.error('[Claude Context Bridge v2] Error:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// Main extraction handler
async function handleExtractConversation() {
  console.log('[Claude Context Bridge v2] Starting extraction...');
  
  const conversationId = getConversationId();
  if (!conversationId) {
    return {
      success: false,
      error: 'No conversation ID found. Make sure you\'re on a conversation page.'
    };
  }
  
  const title = getConversationTitle();
  const messages = extractMessages();
  const metadata = extractConversationMetadata();
  
  console.log(`[Claude Context Bridge v2] Extracted:
    - ID: ${conversationId}
    - Title: ${title}
    - Messages: ${messages.length}
    - Model: ${metadata.model || 'unknown'}`);
  
  // Debug: Log role distribution
  const roleCount = messages.reduce((acc, msg) => {
    acc[msg.role] = (acc[msg.role] || 0) + 1;
    return acc;
  }, {});
  console.log('[Claude Context Bridge v2] Role distribution:', roleCount);
  
  return await sendToBridgeServer(conversationId, title, messages, metadata);
}

// Set up MutationObserver for real-time updates
let observer = null;
function setupObserver() {
  if (observer) {
    observer.disconnect();
  }
  
  const targetNode = document.querySelector('main') || document.body;
  
  observer = new MutationObserver((mutations) => {
    // Check if new messages were added
    const hasNewMessages = mutations.some(mutation => {
      return Array.from(mutation.addedNodes).some(node => {
        return node.nodeType === 1 && (
          node.matches?.('[data-testid^="conversation-turn-"]') ||
          node.querySelector?.('[data-testid^="conversation-turn-"]')
        );
      });
    });
    
    if (hasNewMessages) {
      console.log('[Claude Context Bridge v2] New messages detected');
      // Could trigger auto-extraction here if needed
    }
  });
  
  observer.observe(targetNode, {
    childList: true,
    subtree: true
  });
}

// Bulk extraction state
let bulkExtractionState = {
  isRunning: false,
  conversations: [],
  currentIndex: 0,
  stats: { total: 0, completed: 0, failed: 0, skipped: 0 },
  options: {}
};

// Get all conversations from sidebar
function getAllConversations() {
  const conversations = [];
  
  // Look for conversation items in the sidebar
  const conversationElements = document.querySelectorAll('a[href^="/chat/"]');
  
  conversationElements.forEach(element => {
    const href = element.getAttribute('href');
    const match = href.match(/\/chat\/([a-f0-9-]+)/);
    if (match) {
      const titleElement = element.querySelector('.truncate') || element.querySelector('[class*="truncate"]');
      conversations.push({
        id: match[1],
        title: titleElement ? titleElement.textContent.trim() : 'Untitled',
        url: `https://claude.ai${href}`,
        element: element
      });
    }
  });
  
  return conversations;
}

// Handle bulk extraction
async function handleBulkExtraction(options) {
  bulkExtractionState.isRunning = true;
  bulkExtractionState.options = options;
  bulkExtractionState.conversations = getAllConversations();
  bulkExtractionState.stats = {
    total: bulkExtractionState.conversations.length,
    completed: 0,
    failed: 0,
    skipped: 0
  };
  bulkExtractionState.currentIndex = 0;
  
  console.log(`[Claude Context Bridge v2] Starting bulk extraction of ${bulkExtractionState.stats.total} conversations`);
  
  // Send initial progress
  sendBulkProgress('started');
  
  // Start extraction
  await extractNextConversation();
}

// Extract next conversation in queue
async function extractNextConversation() {
  if (!bulkExtractionState.isRunning || bulkExtractionState.currentIndex >= bulkExtractionState.conversations.length) {
    bulkExtractionState.isRunning = false;
    sendBulkProgress('completed');
    return;
  }
  
  const conversation = bulkExtractionState.conversations[bulkExtractionState.currentIndex];
  
  // Update progress
  sendBulkProgress('extracting', conversation.title);
  
  try {
    // Check if we should skip this conversation
    if (bulkExtractionState.options.skipExisting) {
      const checkResponse = await fetch(`http://localhost:8765/api/conversations/${conversation.id}`);
      if (checkResponse.ok) {
        console.log(`[Claude Context Bridge v2] Skipping already extracted: ${conversation.title}`);
        bulkExtractionState.stats.skipped++;
        bulkExtractionState.currentIndex++;
        setTimeout(() => extractNextConversation(), 500);
        return;
      }
    }
    
    // Navigate to conversation if not already there
    if (!window.location.href.includes(conversation.id)) {
      console.log(`[Claude Context Bridge v2] Navigating to: ${conversation.title}`);
      window.location.href = conversation.url;
      // Navigation will reload the page, so extraction will stop here
      // The bulk extraction will need to be resumed from the extension
      return;
    }
    
    // Extract current conversation
    const result = await handleExtractConversation();
    
    if (result.success) {
      bulkExtractionState.stats.completed++;
    } else {
      bulkExtractionState.stats.failed++;
    }
    
  } catch (error) {
    console.error(`[Claude Context Bridge v2] Error extracting ${conversation.title}:`, error);
    bulkExtractionState.stats.failed++;
  }
  
  // Move to next conversation
  bulkExtractionState.currentIndex++;
  
  // Wait before next extraction
  const delay = bulkExtractionState.options.delayBetween || 2000;
  setTimeout(() => extractNextConversation(), delay);
}

// Send bulk extraction progress
function sendBulkProgress(status, current = null) {
  chrome.runtime.sendMessage({
    type: 'bulk_progress',
    stats: bulkExtractionState.stats,
    status: status,
    current: current
  });
}

// Get statistics
function getStatistics() {
  const conversations = getAllConversations();
  return {
    success: true,
    total: conversations.length
  };
}

// Message listener
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[Claude Context Bridge v2] Received message:', request);
  
  switch (request.action) {
    case 'extract_conversation':
    case 'extract':
      handleExtractConversation().then(sendResponse);
      return true;
      
    case 'start_monitoring':
      setupObserver();
      sendResponse({ success: true, message: 'Monitoring started' });
      break;
      
    case 'stop_monitoring':
      if (observer) {
        observer.disconnect();
        observer = null;
      }
      sendResponse({ success: true, message: 'Monitoring stopped' });
      break;
      
    case 'start_bulk_extraction':
      const conversations = getAllConversations();
      chrome.runtime.sendMessage({
        type: 'bulk_extraction_navigate',
        conversations: conversations,
        options: request.options
      });
      sendResponse({ success: true, message: 'Bulk extraction started' });
      break;
      
    case 'extract_for_bulk':
      handleExtractConversation().then(sendResponse);
      return true;
      
    case 'stop_bulk_extraction':
      bulkExtractionState.isRunning = false;
      sendResponse({ success: true, message: 'Bulk extraction stopped' });
      break;
      
    case 'get_stats':
      sendResponse(getStatistics());
      break;
      
    default:
      sendResponse({ success: false, error: 'Unknown action: ' + request.action });
  }
});

// Initialize
chrome.runtime.sendMessage({ action: 'content_script_ready' });
console.log('[Claude Context Bridge v2] Initialized');

// Auto-setup observer after page load
if (document.readyState === 'complete') {
  setupObserver();
} else {
  window.addEventListener('load', setupObserver);
}