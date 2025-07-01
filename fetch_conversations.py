#!/usr/bin/env python3
"""Fetch conversations from Claude.ai using direct API access."""

import requests
import json
import sys
from datetime import datetime

def fetch_conversations(session_key: str, org_id: str):
    """Fetch conversations from Claude.ai API."""
    
    # Set up headers
    headers = {
        'Cookie': f'sessionKey={session_key}',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate',  # Don't request brotli for now
        'Referer': 'https://claude.ai/',
        'Origin': 'https://claude.ai'
    }
    
    # API endpoint
    url = f'https://claude.ai/api/organizations/{org_id}/chat_conversations'
    
    print(f"Fetching conversations from: {url}")
    
    try:
        # Make request
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Content-Encoding: {response.headers.get('content-encoding')}")
        
        if response.status_code == 200:
            # Try to parse JSON
            try:
                data = response.json()
                print(f"\nSuccessfully fetched {len(data)} conversations!")
                
                # Display conversations
                for i, conv in enumerate(data[:5]):  # Show first 5
                    print(f"\n{i+1}. {conv.get('name', 'Untitled')}")
                    print(f"   ID: {conv.get('uuid', 'N/A')}")
                    print(f"   Created: {conv.get('created_at', 'N/A')}")
                    print(f"   Updated: {conv.get('updated_at', 'N/A')}")
                    
                if len(data) > 5:
                    print(f"\n... and {len(data) - 5} more conversations")
                
                # Save to file
                with open('conversations.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print("\nFull data saved to conversations.json")
                
                return data
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
                print(f"Response preview: {response.text[:500]}...")
                
        else:
            print(f"Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
        
    return None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python fetch_conversations.py <session_key> <org_id>")
        sys.exit(1)
        
    session_key = sys.argv[1]
    org_id = sys.argv[2]
    
    fetch_conversations(session_key, org_id)