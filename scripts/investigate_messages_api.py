#!/usr/bin/env python3
"""
Investigate potential Claude.ai API endpoints for retrieving conversation messages.
Usage: python3 investigate_messages_api.py <session_key> <org_id> <conversation_id>
"""

import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, List, Optional

def test_endpoint(session_key: str, method: str, url: str, description: str) -> Dict:
    """Test a single API endpoint and return results."""
    print(f"\nTesting: {description}")
    print(f"  {method} {url}")
    
    start_time = time.time()
    try:
        # Create request with headers
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Claude-Context-MCP/0.2.0')
        req.add_header('Accept', 'application/json')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Origin', 'https://claude.ai')
        req.add_header('Referer', 'https://claude.ai/')
        req.add_header('Cookie', f'sessionKey={session_key}')
        
        if method == "POST":
            req.data = b'{}'
        
        # Make request
        response = urllib.request.urlopen(req)
        elapsed = time.time() - start_time
        
        # Read response
        response_data = response.read().decode('utf-8')
        status_code = response.code
        headers = dict(response.headers)
        
        result = {
            "endpoint": url,
            "method": method,
            "description": description,
            "status_code": status_code,
            "elapsed_time": elapsed,
            "success": status_code in [200, 201],
            "headers": headers,
            "response_preview": response_data[:500] if response_data else None
        }
        
        if status_code == 200:
            try:
                result["response_json"] = json.loads(response_data)
                print(f"  ✓ Success! Status: {status_code}")
            except:
                result["response_text"] = response_data
                print(f"  ✓ Success! Status: {status_code} (non-JSON response)")
        else:
            print(f"  ✗ Failed. Status: {status_code}")
        
        return result
        
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_time
        error_data = e.read().decode('utf-8') if e.read() else ""
        print(f"  ✗ HTTP Error {e.code}: {e.reason}")
        if error_data:
            print(f"  Response: {error_data[:200]}")
        return {
            "endpoint": url,
            "method": method,
            "description": description,
            "status_code": e.code,
            "elapsed_time": elapsed,
            "success": False,
            "error": f"HTTP {e.code}: {e.reason}",
            "error_response": error_data[:500] if error_data else None
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ✗ Exception: {str(e)}")
        return {
            "endpoint": url,
            "method": method,
            "description": description,
            "status_code": None,
            "elapsed_time": elapsed,
            "success": False,
            "error": str(e)
        }

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 investigate_messages_api.py <session_key> <org_id> <conversation_id>")
        sys.exit(1)
    
    session_key = sys.argv[1]
    org_id = sys.argv[2]
    conversation_id = sys.argv[3]
    
    print(f"Investigating Claude.ai message endpoints...")
    print(f"Organization ID: {org_id}")
    print(f"Conversation ID: {conversation_id}")
    print(f"Session Key: {session_key[:20]}...")
    
    base_url = "https://claude.ai/api"
    
    # List of potential endpoints to test
    endpoints_to_test = [
        # Most likely candidates
        ("GET", f"{base_url}/organizations/{org_id}/chat_conversations/{conversation_id}/messages", 
         "Organization-scoped chat conversation messages"),
        ("GET", f"{base_url}/organizations/{org_id}/conversations/{conversation_id}/messages", 
         "Organization-scoped conversation messages"),
        ("GET", f"{base_url}/conversations/{conversation_id}/messages", 
         "Direct conversation messages"),
        ("GET", f"{base_url}/messages?conversation_id={conversation_id}", 
         "Messages with query parameter"),
        ("GET", f"{base_url}/organizations/{org_id}/messages?conversation_id={conversation_id}", 
         "Organization messages with query parameter"),
        
        # Alternative patterns
        ("GET", f"{base_url}/chat_conversations/{conversation_id}/messages", 
         "Chat conversation messages"),
        ("GET", f"{base_url}/organizations/{org_id}/conversations/{conversation_id}", 
         "Full conversation data (might include messages)"),
        ("GET", f"{base_url}/organizations/{org_id}/conversations/{conversation_id}/history", 
         "Conversation history endpoint"),
        ("GET", f"{base_url}/organizations/{org_id}/conversations/{conversation_id}/tree", 
         "Conversation tree (for branching)"),
        
        # Legacy patterns
        ("GET", f"{base_url}/legacy/conversations/{conversation_id}/messages", 
         "Legacy messages endpoint"),
        ("GET", f"{base_url}/v1/organizations/{org_id}/conversations/{conversation_id}/messages", 
         "Versioned API endpoint"),
    ]
    
    results = []
    
    for method, url, description in endpoints_to_test:
        result = test_endpoint(session_key, method, url, description)
        results.append(result)
        time.sleep(0.5)  # Be polite to the API
    
    # Save results
    output_file = "/Users/hamzaamjad/mcp-claude-context/api_investigation_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "org_id": org_id,
            "conversation_id": conversation_id,
            "total_endpoints_tested": len(results),
            "successful_endpoints": sum(1 for r in results if r["success"]),
            "results": results
        }, f, indent=2)
    
    print(f"\n✓ Results saved to: {output_file}")
    
    # Print summary
    print("\nSummary:")
    successful = [r for r in results if r["success"]]
    if successful:
        print(f"Found {len(successful)} working endpoint(s):")
        for r in successful:
            print(f"  - {r['description']}: {r['endpoint']}")
    else:
        print("No working message endpoints found. This might mean:")
        print("  1. Messages are loaded via WebSocket or GraphQL with specific queries")
        print("  2. Additional authentication headers are required")
        print("  3. The API has changed since the tool was created")

if __name__ == "__main__":
    main()
