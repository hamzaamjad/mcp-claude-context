/**
 * Enhanced background script with bulk extraction support
 */

// Bulk extraction state
let bulkExtractionState = {
  isRunning: false,
  tabId: null,
  conversations: [],
  currentIndex: 0,
  stats: { total: 0, completed: 0, failed: 0, skipped: 0 },
  options: {}
};

// Initialize
chrome.runtime.onInstalled.addListener(() => {
  console.log('Claude Context Extension installed');
  
  // Create context menu
  chrome.contextMenus.create({
    id: "extract-conversation",
    title: "Extract This Conversation",
    contexts: ["page"],
    documentUrlPatterns: ["https://claude.ai/*"]
  });
});

// Handle messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background received:', request);
  
  switch (request.type) {
    case 'bulk_progress':
      // Forward progress to popup
      chrome.runtime.sendMessage(request);
      break;
      
    case 'bulk_extraction_navigate':
      // Handle navigation for bulk extraction
      handleBulkNavigation(request.conversations, request.options, sender.tab.id);
      sendResponse({ success: true });
      break;
      
    case 'content_script_ready':
      // Check if we're in bulk extraction mode
      if (bulkExtractionState.isRunning && sender.tab.id === bulkExtractionState.tabId) {
        resumeBulkExtraction();
      }
      break;
      
    default:
      // Handle other message types...
      break;
  }
});

// Handle bulk navigation
async function handleBulkNavigation(conversations, options, tabId) {
  bulkExtractionState = {
    isRunning: true,
    tabId: tabId,
    conversations: conversations,
    currentIndex: 0,
    stats: { total: conversations.length, completed: 0, failed: 0, skipped: 0 },
    options: options
  };
  
  // Start processing
  processNextConversation();
}

// Process next conversation
async function processNextConversation() {
  if (!bulkExtractionState.isRunning || 
      bulkExtractionState.currentIndex >= bulkExtractionState.conversations.length) {
    // Extraction complete
    bulkExtractionState.isRunning = false;
    chrome.tabs.sendMessage(bulkExtractionState.tabId, {
      action: 'bulk_extraction_complete',
      stats: bulkExtractionState.stats
    });
    return;
  }
  
  const conversation = bulkExtractionState.conversations[bulkExtractionState.currentIndex];
  
  // Check if already extracted
  if (bulkExtractionState.options.skipExisting) {
    try {
      // Add a small delay to respect rate limits when checking
      await new Promise(resolve => setTimeout(resolve, 200));
      
      const response = await fetch(`http://localhost:8765/api/conversations/${conversation.id}`);
      
      // Handle rate limit response
      if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After') || '1';
        console.log(`Rate limited when checking conversation, waiting ${retryAfter}s`);
        await new Promise(resolve => setTimeout(resolve, parseInt(retryAfter) * 1000));
        // Retry processing this conversation
        setTimeout(processNextConversation, 100);
        return;
      }
      
      if (response.ok) {
        bulkExtractionState.stats.skipped++;
        bulkExtractionState.currentIndex++;
        
        // Send progress update
        chrome.runtime.sendMessage({
          type: 'bulk_progress',
          stats: bulkExtractionState.stats,
          status: 'skipped',
          current: conversation.title
        });
        
        // Move to next with rate limit aware delay
        setTimeout(processNextConversation, 300);
        return;
      }
    } catch (error) {
      // Not extracted yet, continue
    }
  }
  
  // Navigate to conversation
  chrome.tabs.update(bulkExtractionState.tabId, {
    url: conversation.url
  });
  
  // The content script will handle extraction when page loads
}

// Resume bulk extraction after navigation
async function resumeBulkExtraction() {
  if (!bulkExtractionState.isRunning) return;
  
  const conversation = bulkExtractionState.conversations[bulkExtractionState.currentIndex];
  
  // Send extraction command to content script
  chrome.tabs.sendMessage(bulkExtractionState.tabId, {
    action: 'extract_for_bulk',
    conversation: conversation
  }, async (response) => {
    if (response && response.success) {
      bulkExtractionState.stats.completed++;
    } else {
      bulkExtractionState.stats.failed++;
    }
    
    // Update progress
    chrome.runtime.sendMessage({
      type: 'bulk_progress',
      stats: bulkExtractionState.stats,
      status: 'extracting',
      current: conversation.title
    });
    
    // Move to next
    bulkExtractionState.currentIndex++;
    
    // Wait before next extraction
    const delay = bulkExtractionState.options.delayBetween || 2000;
    setTimeout(processNextConversation, delay);
  });
}

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "extract-conversation") {
    chrome.tabs.sendMessage(tab.id, { action: "extract_conversation" });
  }
});

// Handle tab updates
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Check if this is our bulk extraction tab
  if (bulkExtractionState.isRunning && 
      tabId === bulkExtractionState.tabId && 
      changeInfo.status === 'complete') {
    // Page has loaded, content script should be ready
    console.log('Bulk extraction tab loaded:', tab.url);
  }
});

// Stop bulk extraction when tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
  if (bulkExtractionState.isRunning && tabId === bulkExtractionState.tabId) {
    bulkExtractionState.isRunning = false;
    console.log('Bulk extraction stopped - tab closed');
  }
});