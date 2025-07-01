#!/usr/bin/env python3
"""
Claude.ai API Endpoint Discovery Script
This script attempts to discover API endpoints by trying common patterns
with authenticated requests using a provided session key.
"""

import requests
import json
import sys
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin
import time
import gzip
import brotli
from io import BytesIO

class ClaudeAPIExplorer:
    def __init__(self, session_key: str, base_url: str = "https://claude.ai"):
        self.session_key = session_key
        self.base_url = base_url
        self.session = requests.Session()
        self.discovered_endpoints = []
        
        # Set up headers to mimic browser requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cookie': f'sessionKey={session_key}',
            'Referer': 'https://claude.ai/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"'
        }
        self.session.headers.update(self.headers)
    
    def decode_response(self, response: requests.Response) -> Union[Dict, str]:
        """Decode response content, handling compression"""
        content = response.content
        
        # Check Content-Encoding header
        encoding = response.headers.get('Content-Encoding', '').lower()
        
        try:
            if encoding == 'gzip':
                content = gzip.decompress(content)
            elif encoding == 'br':
                content = brotli.decompress(content)
            elif encoding == 'deflate':
                content = gzip.decompress(content, 16 + gzip.MAX_WBITS)
            
            # Try to decode as text
            text_content = content.decode('utf-8') if isinstance(content, bytes) else content
            
            # Try to parse as JSON
            try:
                return json.loads(text_content)
            except json.JSONDecodeError:
                # If not JSON, return as text
                return {"text": text_content[:1000], "is_json": False}
                
        except Exception as e:
            return {"error": f"Failed to decode response: {str(e)}", "raw_length": len(content)}
    
    def test_endpoint(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Tuple[int, Optional[Dict]]:
        """Test an endpoint and return status code and response data"""
        url = urljoin(self.base_url, endpoint)
        
        try:
            if method == "GET":
                response = self.session.get(url, timeout=10)
            elif method == "POST":
                response = self.session.post(url, json=data, timeout=10)
            elif method == "PUT":
                response = self.session.put(url, json=data, timeout=10)
            elif method == "DELETE":
                response = self.session.delete(url, timeout=10)
            else:
                return -1, None
            
            # Decode and parse response
            response_data = self.decode_response(response)
            
            # Add response metadata
            if isinstance(response_data, dict):
                response_data['_metadata'] = {
                    'content_type': response.headers.get('Content-Type', ''),
                    'content_encoding': response.headers.get('Content-Encoding', ''),
                    'content_length': response.headers.get('Content-Length', '')
                }
            
            return response.status_code, response_data
            
        except requests.exceptions.Timeout:
            return -2, {"error": "Timeout"}
        except requests.exceptions.ConnectionError:
            return -3, {"error": "Connection Error"}
        except Exception as e:
            return -4, {"error": str(e)}
    
    def discover_endpoints(self, org_id: Optional[str] = None):
        """Try common API endpoint patterns"""
        
        # Common API endpoints to try
        endpoints = [
            # Basic endpoints
            ("/api/user", "GET"),
            ("/api/me", "GET"),
            ("/api/auth/user", "GET"),
            ("/api/current_user", "GET"),
            ("/api/account", "GET"),
            ("/api/profile", "GET"),
            ("/api/users/me", "GET"),
            
            # Conversation endpoints
            ("/api/conversations", "GET"),
            ("/api/conversation", "GET"),
            ("/api/chats", "GET"),
            ("/api/chat", "GET"),
            ("/api/messages", "GET"),
            ("/api/chat_conversations", "GET"),
            
            # Organization endpoints
            ("/api/organizations", "GET"),
            ("/api/orgs", "GET"),
            ("/api/workspaces", "GET"),
            ("/api/teams", "GET"),
            ("/api/accounts", "GET"),
            
            # Settings and preferences
            ("/api/settings", "GET"),
            ("/api/preferences", "GET"),
            ("/api/config", "GET"),
            ("/api/user_settings", "GET"),
            
            # Usage and billing
            ("/api/usage", "GET"),
            ("/api/billing", "GET"),
            ("/api/subscription", "GET"),
            ("/api/limits", "GET"),
            ("/api/quota", "GET"),
            ("/api/credits", "GET"),
            
            # Models and capabilities
            ("/api/models", "GET"),
            ("/api/capabilities", "GET"),
            ("/api/features", "GET"),
            ("/api/available_models", "GET"),
            
            # Claude-specific endpoints (based on common patterns)
            ("/api/bootstrap", "GET"),
            ("/api/session", "GET"),
            ("/api/auth/session", "GET"),
            ("/api/artifacts", "GET"),
            ("/api/projects", "GET"),
            ("/api/prompts", "GET"),
            ("/api/completions", "GET"),
            ("/api/threads", "GET"),
            ("/api/history", "GET"),
            
            # Potential Claude.ai specific endpoints
            ("/api/claude/conversations", "GET"),
            ("/api/claude/messages", "GET"),
            ("/api/claude/models", "GET"),
            ("/api/claude/user", "GET"),
        ]
        
        # If org_id is provided, add organization-specific endpoints
        if org_id:
            org_endpoints = [
                # Standard organization endpoints
                (f"/api/organizations/{org_id}", "GET"),
                (f"/api/organizations/{org_id}/conversations", "GET"),
                (f"/api/organizations/{org_id}/members", "GET"),
                (f"/api/organizations/{org_id}/usage", "GET"),
                (f"/api/organizations/{org_id}/settings", "GET"),
                (f"/api/organizations/{org_id}/billing", "GET"),
                (f"/api/organizations/{org_id}/models", "GET"),
                (f"/api/organizations/{org_id}/projects", "GET"),
                (f"/api/organizations/{org_id}/artifacts", "GET"),
                
                # Claude.ai specific organization endpoints
                (f"/api/organizations/{org_id}/chats", "GET"),
                (f"/api/organizations/{org_id}/chat_conversations", "GET"),
                (f"/api/organizations/{org_id}/threads", "GET"),
                (f"/api/organizations/{org_id}/completions", "GET"),
                (f"/api/organizations/{org_id}/prompts", "GET"),
                
                # Alternative patterns
                (f"/api/orgs/{org_id}", "GET"),
                (f"/api/orgs/{org_id}/conversations", "GET"),
                (f"/api/orgs/{org_id}/chats", "GET"),
                (f"/api/workspaces/{org_id}/conversations", "GET"),
                (f"/api/accounts/{org_id}/conversations", "GET"),
                (f"/api/accounts/{org_id}/chats", "GET"),
            ]
            endpoints.extend(org_endpoints)
        
        # GraphQL endpoints with different queries
        graphql_queries = [
            {"query": "{ __typename }"},
            {"query": "{ me { id name email } }"},
            {"query": "{ conversations { edges { node { id title } } } }"},
            {"query": "{ organizations { id name } }"},
        ]
        for query in graphql_queries:
            endpoints.append(("/api/graphql", "POST", query))
            endpoints.append(("/graphql", "POST", query))
        
        print(f"Testing {len(endpoints)} potential endpoints...\n")
        
        for endpoint_data in endpoints:
            if len(endpoint_data) == 3:
                endpoint, method, data = endpoint_data
            else:
                endpoint, method = endpoint_data
                data = None
            
            # Add query info for GraphQL
            query_info = ""
            if data and "query" in data:
                query_info = f" [Query: {data['query'][:50]}...]"
            
            print(f"Testing {method} {endpoint}{query_info}... ", end="", flush=True)
            
            status_code, response_data = self.test_endpoint(endpoint, method, data)
            
            # Interpret results
            if status_code == 200:
                print(f"✓ SUCCESS (200)")
                
                # Extract useful info from response
                response_info = {
                    "endpoint": endpoint,
                    "method": method,
                    "status": status_code,
                }
                
                if data:
                    response_info["request_data"] = data
                
                # Handle response data
                if isinstance(response_data, dict):
                    # Remove metadata for preview
                    preview_data = {k: v for k, v in response_data.items() if k != '_metadata'}
                    response_info["response_preview"] = str(preview_data)[:300] + "..." if len(str(preview_data)) > 300 else str(preview_data)
                    
                    # Add metadata separately if present
                    if '_metadata' in response_data:
                        response_info["metadata"] = response_data['_metadata']
                else:
                    response_info["response_preview"] = str(response_data)[:300] + "..." if len(str(response_data)) > 300 else str(response_data)
                
                self.discovered_endpoints.append(response_info)
            elif status_code == 401:
                print("✗ Unauthorized (401)")
            elif status_code == 403:
                print("✗ Forbidden (403)")
            elif status_code == 404:
                print("✗ Not Found (404)")
            elif status_code == 405:
                print("✗ Method Not Allowed (405)")
            elif status_code == 429:
                print("✗ Rate Limited (429)")
                time.sleep(2)  # Wait a bit if rate limited
            elif status_code == -2:
                print("✗ Timeout")
            elif status_code == -3:
                print("✗ Connection Error")
            elif status_code == -4:
                print(f"✗ Error: {response_data.get('error', 'Unknown')}")
            else:
                print(f"✗ Status: {status_code}")
            
            # Small delay to be respectful
            time.sleep(0.5)
        
        print("\n" + "="*50)
        print("DISCOVERY COMPLETE")
        print("="*50)
        
        if self.discovered_endpoints:
            print(f"\nFound {len(self.discovered_endpoints)} working endpoints:\n")
            for ep in self.discovered_endpoints:
                print(f"\n{ep['method']} {ep['endpoint']}")
                if 'request_data' in ep:
                    print(f"Request: {ep['request_data']}")
                if 'metadata' in ep:
                    print(f"Metadata: {ep['metadata']}")
                print(f"Response preview: {ep['response_preview']}")
        else:
            print("\nNo working endpoints found. This could mean:")
            print("- The session key is invalid or expired")
            print("- The API uses different endpoint patterns")
            print("- Additional authentication headers are required")
    
    def test_conversation_endpoints(self, conversation_id: str, org_id: Optional[str] = None):
        """Test conversation-specific endpoints"""
        print(f"\nTesting conversation-specific endpoints for ID: {conversation_id}\n")
        
        conv_endpoints = [
            (f"/api/conversations/{conversation_id}", "GET"),
            (f"/api/conversations/{conversation_id}/messages", "GET"),
            (f"/api/conversations/{conversation_id}/info", "GET"),
            (f"/api/conversations/{conversation_id}/metadata", "GET"),
            (f"/api/chats/{conversation_id}", "GET"),
            (f"/api/chats/{conversation_id}/messages", "GET"),
            (f"/api/chat_conversations/{conversation_id}", "GET"),
            (f"/api/threads/{conversation_id}", "GET"),
            (f"/api/threads/{conversation_id}/messages", "GET"),
        ]
        
        if org_id:
            conv_endpoints.extend([
                (f"/api/organizations/{org_id}/conversations/{conversation_id}", "GET"),
                (f"/api/organizations/{org_id}/conversations/{conversation_id}/messages", "GET"),
                (f"/api/organizations/{org_id}/chats/{conversation_id}", "GET"),
                (f"/api/orgs/{org_id}/conversations/{conversation_id}", "GET"),
            ])
        
        for endpoint, method in conv_endpoints:
            print(f"Testing {method} {endpoint}... ", end="", flush=True)
            status_code, response_data = self.test_endpoint(endpoint, method)
            
            if status_code == 200:
                print(f"✓ SUCCESS (200)")
                print(f"  Response preview: {str(response_data)[:200]}...")
            else:
                print(f"✗ Status: {status_code}")
            
            time.sleep(0.5)
    
    def save_results(self, filename: str = "discovered_endpoints.json"):
        """Save discovered endpoints to a JSON file"""
        with open(filename, 'w') as f:
            json.dump({
                "base_url": self.base_url,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "endpoints": self.discovered_endpoints
            }, f, indent=2)
        print(f"\nResults saved to {filename}")

def main():
    print("Claude.ai API Endpoint Discovery Tool")
    print("="*50)
    
    # Get session key from user
    if len(sys.argv) > 1:
        session_key = sys.argv[1]
    else:
        print("\nUsage: python discover_api.py <session_key> [org_id] [conversation_id]")
        print("\nTo get your session key:")
        print("1. Log into claude.ai")
        print("2. Open browser developer tools (F12)")
        print("3. Go to Application/Storage -> Cookies")
        print("4. Find and copy the 'sessionKey' value")
        session_key = input("\nEnter your session key: ").strip()
    
    if not session_key:
        print("Error: Session key is required")
        sys.exit(1)
    
    # Optional org_id and conversation_id
    org_id = sys.argv[2] if len(sys.argv) > 2 else None
    conversation_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Create explorer and run discovery
    explorer = ClaudeAPIExplorer(session_key)
    
    print(f"\nStarting API discovery...")
    if org_id:
        print(f"Including organization-specific endpoints for org_id: {org_id}")
    if conversation_id:
        print(f"Will also test conversation-specific endpoints for ID: {conversation_id}")
    print()
    
    try:
        # Main endpoint discovery
        explorer.discover_endpoints(org_id)
        
        # Test conversation-specific endpoints if ID provided
        if conversation_id:
            explorer.test_conversation_endpoints(conversation_id, org_id)
        
        # Save results if any endpoints were found
        if explorer.discovered_endpoints:
            explorer.save_results()
            
    except KeyboardInterrupt:
        print("\n\nDiscovery interrupted by user")
        if explorer.discovered_endpoints:
            print(f"Found {len(explorer.discovered_endpoints)} endpoints before interruption")
            explorer.save_results()
    except Exception as e:
        print(f"\nError during discovery: {e}")

if __name__ == "__main__":
    main()