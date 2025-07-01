/**
 * Enhanced popup script with bulk export functionality
 */

// State management
let isExtracting = false;
let extractionStats = {
  total: 0,
  completed: 0,
  failed: 0,
  skipped: 0
};

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
  checkServerStatus();
  updateStatistics();
  
  // Event listeners
  document.getElementById('extract-current').addEventListener('click', extractCurrentConversation);
  document.getElementById('extract-all').addEventListener('click', extractAllConversations);
  document.getElementById('monitor-current').addEventListener('click', toggleMonitoring);
  document.getElementById('check-status').addEventListener('click', checkServerStatus);
  document.getElementById('refresh-status').addEventListener('click', checkServerStatus);
  document.getElementById('open-dashboard').addEventListener('click', openDashboard);
});

// Check bridge server status
async function checkServerStatus() {
  const statusEl = document.getElementById('server-connection');
  const indicatorEl = document.getElementById('server-indicator');
  
  try {
    const response = await fetch('http://localhost:8765/api/status');
    if (response.ok) {
      const data = await response.json();
      statusEl.textContent = 'Connected';
      indicatorEl.className = 'status-indicator connected';
      updateStatistics();
    } else {
      throw new Error('Server not responding');
    }
  } catch (error) {
    statusEl.textContent = 'Disconnected';
    indicatorEl.className = 'status-indicator disconnected';
    showStatus('Bridge server is not running. Please start it first.', 'error');
  }
}

// Update statistics
async function updateStatistics() {
  try {
    // Get conversation count from Claude.ai
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab.url && tab.url.includes('claude.ai')) {
      chrome.tabs.sendMessage(tab.id, { action: 'get_stats' }, (response) => {
        if (response && response.success) {
          document.getElementById('total-conversations').textContent = response.total || '-';
        }
      });
    }
    
    // Get extracted count from bridge server
    const response = await fetch('http://localhost:8765/api/conversations');
    if (response.ok) {
      const data = await response.json();
      document.getElementById('extracted-count').textContent = data.count || '0';
    }
  } catch (error) {
    console.error('Error updating statistics:', error);
  }
}

// Extract current conversation
async function extractCurrentConversation() {
  const button = document.getElementById('extract-current');
  button.disabled = true;
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab.url || !tab.url.includes('claude.ai/chat/')) {
      showStatus('Please navigate to a Claude conversation first.', 'error');
      return;
    }
    
    chrome.tabs.sendMessage(tab.id, { action: 'extract_conversation' }, (response) => {
      if (chrome.runtime.lastError) {
        showStatus('Error: ' + chrome.runtime.lastError.message, 'error');
      } else if (response.success) {
        showStatus(`Extracted "${response.data.title}" (${response.messageCount} messages)`, 'success');
        updateStatistics();
      } else {
        showStatus('Error: ' + response.error, 'error');
      }
      button.disabled = false;
    });
  } catch (error) {
    showStatus('Error: ' + error.message, 'error');
    button.disabled = false;
  }
}

// Extract all conversations
async function extractAllConversations() {
  if (isExtracting) {
    stopBulkExtraction();
    return;
  }
  
  const button = document.getElementById('extract-all');
  const progressContainer = document.getElementById('bulk-progress');
  const progressFill = document.getElementById('progress-fill');
  const progressText = document.getElementById('progress-text');
  
  // Reset stats
  extractionStats = { total: 0, completed: 0, failed: 0, skipped: 0 };
  
  // Update UI
  isExtracting = true;
  button.textContent = 'Stop Extraction';
  button.classList.add('danger');
  progressContainer.style.display = 'block';
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab.url || !tab.url.includes('claude.ai')) {
      showStatus('Please navigate to Claude.ai first.', 'error');
      stopBulkExtraction();
      return;
    }
    
    // Get options
    const skipExisting = document.getElementById('skip-existing').checked;
    const autoScroll = document.getElementById('auto-scroll').checked;
    const delayBetween = parseInt(document.getElementById('delay-between').value) * 1000;
    
    // Start bulk extraction
    chrome.tabs.sendMessage(tab.id, {
      action: 'start_bulk_extraction',
      options: { skipExisting, autoScroll, delayBetween }
    }, (response) => {
      if (chrome.runtime.lastError) {
        showStatus('Error: ' + chrome.runtime.lastError.message, 'error');
        stopBulkExtraction();
      }
    });
    
    // Listen for progress updates
    chrome.runtime.onMessage.addListener(handleBulkProgress);
    
  } catch (error) {
    showStatus('Error: ' + error.message, 'error');
    stopBulkExtraction();
  }
}

// Handle bulk extraction progress
function handleBulkProgress(message, sender, sendResponse) {
  if (message.type !== 'bulk_progress') return;
  
  const { stats, status, current } = message;
  extractionStats = stats;
  
  // Update progress bar
  const progress = stats.total > 0 ? Math.round((stats.completed + stats.failed + stats.skipped) / stats.total * 100) : 0;
  document.getElementById('progress-fill').style.width = `${progress}%`;
  document.getElementById('progress-fill').textContent = `${progress}%`;
  
  // Update progress text
  let statusText = `${stats.completed} extracted`;
  if (stats.skipped > 0) statusText += `, ${stats.skipped} skipped`;
  if (stats.failed > 0) statusText += `, ${stats.failed} failed`;
  if (current) statusText += ` - Current: ${current}`;
  
  document.getElementById('progress-text').textContent = statusText;
  
  // Check if completed
  if (status === 'completed' || status === 'stopped') {
    showStatus(`Bulk extraction ${status}. ${stats.completed} conversations extracted.`, 
               status === 'completed' ? 'success' : 'warning');
    stopBulkExtraction();
  }
}

// Stop bulk extraction
function stopBulkExtraction() {
  isExtracting = false;
  const button = document.getElementById('extract-all');
  button.textContent = 'Extract All Conversations';
  button.classList.remove('danger');
  
  // Send stop message
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, { action: 'stop_bulk_extraction' });
    }
  });
  
  // Remove progress listener
  chrome.runtime.onMessage.removeListener(handleBulkProgress);
  
  updateStatistics();
}

// Toggle real-time monitoring
async function toggleMonitoring() {
  const button = document.getElementById('monitor-current');
  const isMonitoring = button.textContent.includes('Stop');
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab.url || !tab.url.includes('claude.ai/chat/')) {
      showStatus('Please navigate to a Claude conversation first.', 'error');
      return;
    }
    
    const action = isMonitoring ? 'stop_monitoring' : 'start_monitoring';
    chrome.tabs.sendMessage(tab.id, { action }, (response) => {
      if (response && response.success) {
        button.textContent = isMonitoring ? 'Start Real-time Monitoring' : 'Stop Monitoring';
        showStatus(response.message, 'success');
      }
    });
  } catch (error) {
    showStatus('Error: ' + error.message, 'error');
  }
}

// Open analytics dashboard
function openDashboard() {
  chrome.tabs.create({ url: 'http://localhost:8765/dashboard' });
}

// Show status message
function showStatus(message, type = 'info') {
  const statusEl = document.getElementById('status');
  statusEl.textContent = message;
  statusEl.className = type;
  statusEl.style.display = 'block';
  
  // Auto-hide after 5 seconds
  setTimeout(() => {
    statusEl.style.display = 'none';
  }, 5000);
}