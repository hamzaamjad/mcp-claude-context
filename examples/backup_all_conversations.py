#!/usr/bin/env python3
"""
Backup all Claude.ai conversations to local storage.
This script connects to the MCP server and exports all conversations.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configuration
SESSION_KEY = os.getenv("CLAUDE_SESSION_KEY", "your-session-key-here")
ORG_ID = os.getenv("CLAUDE_ORG_ID", "your-org-id-here")
BACKUP_DIR = Path.home() / "claude_backups"

async def backup_conversations():
    """Backup all conversations using the MCP server."""
    
    # Ensure backup directory exists
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Connect to MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "claude_context"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("🔄 Fetching conversations...")
            
            # List all conversations
            result = await session.call_tool(
                "list_conversations",
                arguments={
                    "session_key": SESSION_KEY,
                    "org_id": ORG_ID,
                    "limit": 100
                }
            )
            
            conversations = json.loads(result[0].text)
            
            if conversations["status"] != "success":
                print(f"❌ Error: {conversations.get('error', 'Unknown error')}")
                return
            
            print(f"✅ Found {conversations['count']} conversations")
            
            # Export to JSON
            print("📁 Creating JSON backup...")
            json_result = await session.call_tool(
                "export_conversations",
                arguments={
                    "session_key": SESSION_KEY,
                    "org_id": ORG_ID,
                    "format": "json",
                    "include_settings": True
                }
            )
            
            json_export = json.loads(json_result[0].text)
            
            if json_export["status"] == "success":
                print(f"✅ JSON backup created: {json_export['filename']}")
                print(f"   Size: {json_export['file_size_human']}")
                
                # Copy to backup directory
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = BACKUP_DIR / f"claude_backup_{timestamp}.json"
                
                # Read the export and save to backup location
                with open(json_export['filepath'], 'r') as src:
                    backup_data = json.load(src)
                
                with open(backup_file, 'w') as dst:
                    json.dump(backup_data, dst, indent=2)
                
                print(f"✅ Backup saved to: {backup_file}")
            
            # Export to CSV
            print("📊 Creating CSV backup...")
            csv_result = await session.call_tool(
                "export_conversations",
                arguments={
                    "session_key": SESSION_KEY,
                    "org_id": ORG_ID,
                    "format": "csv"
                }
            )
            
            csv_export = json.loads(csv_result[0].text)
            
            if csv_export["status"] == "success":
                print(f"✅ CSV backup created: {csv_export['filename']}")
                
                # Copy CSV to backup directory
                csv_backup = BACKUP_DIR / f"claude_backup_{timestamp}.csv"
                with open(csv_export['filepath'], 'r') as src:
                    with open(csv_backup, 'w') as dst:
                        dst.write(src.read())
                
                print(f"✅ CSV saved to: {csv_backup}")
            
            print(f"\n🎉 Backup complete! Files saved in: {BACKUP_DIR}")

def main():
    """Main entry point."""
    print("Claude.ai Conversation Backup Tool")
    print("=" * 40)
    
    if SESSION_KEY == "your-session-key-here":
        print("\n⚠️  Please set your credentials:")
        print("export CLAUDE_SESSION_KEY='your-actual-session-key'")
        print("export CLAUDE_ORG_ID='your-actual-org-id'")
        return
    
    try:
        asyncio.run(backup_conversations())
    except KeyboardInterrupt:
        print("\n\n⚠️  Backup cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
