# Claude Context Bridge - Chrome Extension Guide

## 🎉 What We Built

A complete system for extracting Claude.ai conversations with:

1. **MCP Server** (v0.2.0) - Direct API access for conversation metadata
2. **Chrome Extension** - Extracts full message content from the DOM
3. **Bridge Server** - Local server that receives and stores extracted data

## 🚀 Quick Start

### 1. Start the Bridge Server
```bash
cd /Users/hamzaamjad/mcp-claude-context
poetry run python extension/bridge_server.py
```
The server runs on http://localhost:8765

### 2. Load the Chrome Extension
1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `/Users/hamzaamjad/mcp-claude-context/extension`

### 3. Extract Conversations
1. Navigate to any Claude.ai conversation
2. Click the extension icon
3. Click "Extract Current Conversation"
4. Check the status - it should show success!

## 📁 Where Data is Saved

Extracted conversations are saved to:
```
/Users/hamzaamjad/mcp-claude-context/extracted_messages/
├── {conversation-id}/
│   ├── metadata.json      # Conversation info
│   ├── messages.json      # Full message data
│   └── conversation.txt   # Human-readable format
```

## 🔧 How It Works

1. **Extension** extracts messages from Claude.ai DOM
2. **Bridge Server** receives the data via HTTP POST
3. **Data is saved** in multiple formats for easy access
4. **MCP Server** can access the extracted data

## ✅ What's Working

- ✓ Message extraction from Claude.ai
- ✓ Proper role detection (user/assistant)
- ✓ Bridge server communication
- ✓ Data persistence in multiple formats
- ✓ Chrome extension UI with status feedback

## 🎯 Key Features

- **No Browser Automation** - Direct DOM access is more reliable
- **Local Storage** - All data stays on your machine
- **Multiple Formats** - JSON for programs, TXT for reading
- **Real-time Extraction** - Works on live conversations

## 🐛 Troubleshooting

1. **Extension not working?**
   - Reload the extension in chrome://extensions
   - Make sure you're on a conversation page (not home page)
   - Check Chrome console for errors (F12)

2. **Bridge server errors?**
   - Ensure it's running on port 8765
   - Check terminal for error messages
   - Try `curl http://localhost:8765/api/status`

3. **No messages extracted?**
   - Claude.ai might have updated their UI
   - Check console for selector errors
   - Try the manual test script

## 🚀 Next Steps

1. **Bulk Export**: Add "Export All Conversations" feature
2. **Auto-sync**: Monitor for new messages automatically
3. **Search**: Add search across all extracted conversations
4. **Analytics**: Generate insights from your conversations

## 💡 Pro Tips

- The bridge server must be running for extraction to work
- You can extract the same conversation multiple times
- Check Chrome DevTools console for detailed logs
- The MCP server can read the extracted data for other tools

Great work! The system is now fully functional for extracting and storing Claude.ai conversations locally.