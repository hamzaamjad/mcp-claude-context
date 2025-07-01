// Popup script for Claude Context Extension

const statusDiv = document.getElementById('status');
const serverStatusSpan = document.getElementById('server-connection');

// Check bridge server status on load
checkServerStatus();

// Button handlers
document.getElementById('extract-current').addEventListener('click', extractCurrentConversation);
document.getElementById('extract-all').addEventListener('click', extractAllMessages);
document.getElementById('check-status').addEventListener('click', checkServerStatus);

async function checkServerStatus() {
  try {
    const response = await fetch('http://localhost:8765/api/status');
    if (response.ok) {
      const data = await response.json();
      serverStatusSpan.textContent = '✅ Connected';
      serverStatusSpan.style.color = 'green';
      showStatus(`Server running. ${data.conversations_cached} conversations cached.`, 'info');
    } else {
      throw new Error('Server not responding');
    }
  } catch (error) {
    serverStatusSpan.textContent = '❌ Disconnected';
    serverStatusSpan.style.color = 'red';
    showStatus('Bridge server not running. Start it with: poetry run python extension/bridge_server.py', 'error');
  }
}

async function extractCurrentConversation() {
  showStatus('Extracting conversation...', 'info');
  
  try {
    // Get active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab.url.includes('claude.ai')) {
      showStatus('Please navigate to a Claude.ai conversation', 'error');
      return;
    }
    
    // Send message to content script
    chrome.tabs.sendMessage(tab.id, { action: 'extract_conversations' }, (response) => {
      if (chrome.runtime.lastError) {
        showStatus('Failed to extract. Make sure you\'re on a conversation page.', 'error');
      } else if (response && response.success) {
        showStatus(`Extracted: ${response.data.title || 'Untitled conversation'}`, 'success');
      } else {
        showStatus(response?.error || 'Extraction failed', 'error');
      }
    });
  } catch (error) {
    showStatus(`Error: ${error.message}`, 'error');
  }
}

async function extractAllMessages() {
  showStatus('Extracting all messages...', 'info');
  
  try {
    // Get active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab.url.includes('claude.ai')) {
      showStatus('Please navigate to a Claude.ai conversation', 'error');
      return;
    }
    
    // Send message to content script
    chrome.tabs.sendMessage(tab.id, { action: 'extract_messages' }, (response) => {
      if (chrome.runtime.lastError) {
        showStatus('Failed to extract messages. Make sure you\'re on a conversation page.', 'error');
      } else if (response && response.success) {
        showStatus(`Extracted ${response.messageCount} messages`, 'success');
      } else {
        showStatus(response?.error || 'Message extraction failed', 'error');
      }
    });
  } catch (error) {
    showStatus(`Error: ${error.message}`, 'error');
  }
}

function showStatus(message, type) {
  statusDiv.textContent = message;
  statusDiv.className = type;
  statusDiv.style.display = 'block';
  
  // Auto-hide success messages
  if (type === 'success') {
    setTimeout(() => {
      statusDiv.style.display = 'none';
    }, 5000);
  }
}