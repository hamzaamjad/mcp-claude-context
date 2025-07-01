# Claude Context Direct API MCP Server

## Overview
This is an improved version of the Claude Context MCP server that uses direct API access instead of browser automation. It's faster, more reliable, and doesn't get blocked by anti-automation measures.

## Key Improvements
- ✅ Direct API access (no Playwright/browser automation)
- ✅ Faster response times
- ✅ No Cloudflare blocking issues
- ✅ Lightweight - uses simple HTTP requests
- ✅ Better error handling

## Available Tools

### 1. list_conversations
Lists all your Claude.ai conversations.

**Required Parameters:**
- `session_key`: Your Claude.ai session key
- `org_id`: Your organization ID

**Optional Parameters:**
- `limit`: Maximum conversations to return (default: 50)

**Example Usage in Claude:**
```
Use the claude-context tool to list my conversations with:
- session_key: YOUR_SESSION_KEY_HERE
- org_id: YOUR_ORG_ID_HERE
```

### 2. get_conversation
Get details of a specific conversation.

**Required Parameters:**
- `session_key`: Your Claude.ai session key
- `org_id`: Your organization ID
- `conversation_id`: The conversation UUID

**Example Usage:**
```
Get conversation 597933f9-ad45-4974-bcfe-71a8a04006d9 using claude-context
```

### 3. search_conversations
Search your conversations by keyword.

**Required Parameters:**
- `session_key`: Your Claude.ai session key
- `org_id`: Your organization ID
- `query`: Search term

**Example Usage:**
```
Search for "MCP" in my conversations using claude-context
```

## Getting Your Credentials

### Session Key
1. Open claude.ai in your browser
2. Open Developer Tools (F12)
3. Go to Application → Cookies → claude.ai
4. Find `sessionKey` and copy its value

### Organization ID
1. Look for `lastActiveOrg` cookie in the same place
2. Or check the URL when viewing your conversations
3. It's a UUID like: `YOUR_ORG_ID_HERE`

## Configuration
Already configured in your Claude Desktop at:
`~/Library/Application Support/Claude/claude_desktop_config.json`

## Troubleshooting

### Session Expired
If you get authentication errors, your session key may have expired. Get a new one from your browser.

### Organization Not Found
Make sure you're using the correct organization ID from your cookies.

### Rate Limiting
The API may rate limit if you make too many requests. Wait a few minutes and try again.

## Technical Details
- Uses Claude.ai's internal API endpoint: `/api/organizations/{org_id}/chat_conversations`
- Responses are gzip-compressed JSON
- No need for Playwright or browser automation
- Caches conversations for faster subsequent access