// Background script for Claude Context Extension

chrome.runtime.onInstalled.addListener(() => {
  console.log('Claude Context Extension installed');
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'CONVERSATION_EXTRACTED') {
    console.log('Conversation extracted:', request.data);
    
    // Forward to bridge server
    fetch('http://localhost:8765/api/conversation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request.data)
    })
    .then(response => response.json())
    .then(data => {
      console.log('Sent to bridge server:', data);
      sendResponse({ success: true, data });
    })
    .catch(error => {
      console.error('Failed to send to bridge server:', error);
      sendResponse({ success: false, error: error.message });
    });
    
    return true; // Keep message channel open for async response
  }
  
  if (request.type === 'MESSAGES_EXTRACTED') {
    console.log(`Extracted ${request.data.messages.length} messages`);
    
    // Forward to bridge server
    fetch('http://localhost:8765/api/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request.data)
    })
    .then(response => response.json())
    .then(data => {
      console.log('Messages sent to bridge server:', data);
      sendResponse({ success: true, data });
    })
    .catch(error => {
      console.error('Failed to send messages to bridge server:', error);
      sendResponse({ success: false, error: error.message });
    });
    
    return true; // Keep message channel open for async response
  }
});

// Create context menu
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "extract-conversation",
    title: "Extract This Conversation",
    contexts: ["page"],
    documentUrlPatterns: ["https://claude.ai/*"]
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "extract-conversation") {
    chrome.tabs.sendMessage(tab.id, { action: "extract" });
  }
});