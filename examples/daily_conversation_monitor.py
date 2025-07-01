#!/usr/bin/env python3
"""
Monitor Claude.ai conversations daily and alert on new activity.
This script can be run via cron to track conversation changes.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configuration
SESSION_KEY = os.getenv("CLAUDE_SESSION_KEY", "your-session-key-here")
ORG_ID = os.getenv("CLAUDE_ORG_ID", "your-org-id-here")
STATE_FILE = Path.home() / ".claude_monitor" / "last_state.json"
LOG_FILE = Path.home() / ".claude_monitor" / "activity.log"

class ConversationMonitor:
    """Monitor conversation changes over time."""
    
    def __init__(self):
        self.state_dir = STATE_FILE.parent
        self.state_dir.mkdir(exist_ok=True)
        self.previous_state = self.load_state()
        
    def load_state(self):
        """Load previous state from file."""
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def save_state(self, conversations):
        """Save current state to file."""
        state = {
            'last_check': datetime.now().isoformat(),
            'conversations': {
                conv['id']: {
                    'name': conv.get('name', 'Untitled'),
                    'updated_at': conv.get('updated_at'),
                    'created_at': conv.get('created_at')
                }
                for conv in conversations
            }
        }
        
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        
        return state
    
    def detect_changes(self, current_conversations):
        """Detect changes between previous and current state."""
        changes = {
            'new_conversations': [],
            'updated_conversations': [],
            'deleted_conversations': [],
            'renamed_conversations': []
        }
        
        if not self.previous_state:
            # First run
            changes['new_conversations'] = current_conversations
            return changes
        
        prev_convs = self.previous_state.get('conversations', {})
        curr_convs = {c['id']: c for c in current_conversations}
        
        # Check for new conversations
        for conv_id, conv in curr_convs.items():
            if conv_id not in prev_convs:
                changes['new_conversations'].append(conv)
        
        # Check for updated/renamed conversations
        for conv_id, conv in curr_convs.items():
            if conv_id in prev_convs:
                prev = prev_convs[conv_id]
                
                # Check if updated
                if conv.get('updated_at') != prev.get('updated_at'):
                    changes['updated_conversations'].append(conv)
                
                # Check if renamed
                if conv.get('name') != prev.get('name'):
                    changes['renamed_conversations'].append({
                        'conversation': conv,
                        'old_name': prev.get('name'),
                        'new_name': conv.get('name')
                    })
        
        # Check for deleted conversations
        for conv_id, prev in prev_convs.items():
            if conv_id not in curr_convs:
                changes['deleted_conversations'].append(prev)
        
        return changes
    
    def log_activity(self, message):
        """Log activity to file."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        with open(LOG_FILE, 'a') as f:
            f.write(log_entry)
        
        print(log_entry.strip())
    
    def format_time_ago(self, timestamp_str):
        """Format timestamp as 'X hours/days ago'."""
        if not timestamp_str:
            return "unknown time"
            
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(tz=timestamp.tzinfo)
        diff = now - timestamp
        
        if diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"

async def monitor_conversations():
    """Monitor conversations for changes."""
    monitor = ConversationMonitor()
    
    # Connect to MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "claude_context"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            monitor.log_activity("Starting conversation monitor...")
            
            # List all conversations
            result = await session.call_tool(
                "list_conversations",
                arguments={
                    "session_key": SESSION_KEY,
                    "org_id": ORG_ID,
                    "limit": 100
                }
            )
            
            data = json.loads(result[0].text)
            
            if data["status"] != "success":
                monitor.log_activity(f"ERROR: {data.get('error', 'Unknown error')}")
                return
            
            conversations = data['conversations']
            monitor.log_activity(f"Retrieved {len(conversations)} conversations")
            
            # Detect changes
            changes = monitor.detect_changes(conversations)
            
            # Report changes
            total_changes = sum(len(v) for v in changes.values())
            
            if total_changes == 0 and monitor.previous_state:
                monitor.log_activity("No changes detected since last check")
            else:
                # New conversations
                if changes['new_conversations']:
                    monitor.log_activity(f"\n🆕 {len(changes['new_conversations'])} NEW CONVERSATIONS:")
                    for conv in changes['new_conversations']:
                        created = monitor.format_time_ago(conv.get('created_at'))
                        monitor.log_activity(f"  - {conv.get('name', 'Untitled')} (created {created})")
                
                # Updated conversations
                if changes['updated_conversations']:
                    monitor.log_activity(f"\n📝 {len(changes['updated_conversations'])} UPDATED CONVERSATIONS:")
                    for conv in changes['updated_conversations']:
                        updated = monitor.format_time_ago(conv.get('updated_at'))
                        monitor.log_activity(f"  - {conv.get('name', 'Untitled')} (updated {updated})")
                
                # Renamed conversations
                if changes['renamed_conversations']:
                    monitor.log_activity(f"\n✏️  {len(changes['renamed_conversations'])} RENAMED CONVERSATIONS:")
                    for item in changes['renamed_conversations']:
                        old = item['old_name'] or 'Untitled'
                        new = item['new_name'] or 'Untitled'
                        monitor.log_activity(f"  - '{old}' → '{new}'")
                
                # Deleted conversations
                if changes['deleted_conversations']:
                    monitor.log_activity(f"\n🗑️  {len(changes['deleted_conversations'])} DELETED CONVERSATIONS:")
                    for conv in changes['deleted_conversations']:
                        monitor.log_activity(f"  - {conv.get('name', 'Untitled')}")
            
            # Generate daily summary if significant activity
            if total_changes > 0:
                # Look for patterns in today's conversations
                today_convs = []
                yesterday_convs = []
                now = datetime.now()
                
                for conv in conversations:
                    if conv.get('updated_at'):
                        updated = datetime.fromisoformat(conv['updated_at'].replace('Z', '+00:00'))
                        diff = now - updated
                        
                        if diff < timedelta(days=1):
                            today_convs.append(conv)
                        elif diff < timedelta(days=2):
                            yesterday_convs.append(conv)
                
                monitor.log_activity(f"\n📊 ACTIVITY SUMMARY:")
                monitor.log_activity(f"  Today: {len(today_convs)} active conversations")
                monitor.log_activity(f"  Yesterday: {len(yesterday_convs)} active conversations")
                monitor.log_activity(f"  Total tracked: {len(conversations)} conversations")
                
                # Save notification file for external processing
                if changes['new_conversations'] or changes['updated_conversations']:
                    notification_file = monitor.state_dir / "pending_notification.json"
                    with open(notification_file, 'w') as f:
                        json.dump({
                            'timestamp': datetime.now().isoformat(),
                            'changes': {
                                'new': len(changes['new_conversations']),
                                'updated': len(changes['updated_conversations']),
                                'renamed': len(changes['renamed_conversations']),
                                'deleted': len(changes['deleted_conversations'])
                            },
                            'details': changes
                        }, f, indent=2)
                    
                    monitor.log_activity(f"\n💾 Notification data saved for external processing")
            
            # Save current state
            monitor.save_state(conversations)
            monitor.log_activity("\n✅ State saved for next comparison")

def setup_cron():
    """Print cron setup instructions."""
    print("\nTo run this monitor daily, add to your crontab:")
    print("  crontab -e")
    print("\nAdd this line (runs daily at 9 AM):")
    print("  0 9 * * * /usr/bin/python3 /path/to/daily_conversation_monitor.py")
    print("\nOr for hourly monitoring:")
    print("  0 * * * * /usr/bin/python3 /path/to/daily_conversation_monitor.py")
    print("\nMake sure to set environment variables in your crontab:")
    print("  CLAUDE_SESSION_KEY='your-key'")
    print("  CLAUDE_ORG_ID='your-org-id'")

def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--setup-cron':
        setup_cron()
        return
    
    print("Claude.ai Conversation Monitor")
    print("=" * 40)
    
    if SESSION_KEY == "your-session-key-here":
        print("\n⚠️  Please set your credentials:")
        print("export CLAUDE_SESSION_KEY='your-actual-session-key'")
        print("export CLAUDE_ORG_ID='your-actual-org-id'")
        print("\nFor cron setup instructions, run:")
        print("  python3 daily_conversation_monitor.py --setup-cron")
        return
    
    try:
        asyncio.run(monitor_conversations())
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring cancelled by user")
    except Exception as e:
        # Log errors to file for cron debugging
        error_msg = f"ERROR: {str(e)}"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_dir = Path.home() / ".claude_monitor"
        log_dir.mkdir(exist_ok=True)
        
        with open(log_dir / "errors.log", 'a') as f:
            f.write(f"[{timestamp}] {error_msg}\n")
        
        print(f"\n❌ {error_msg}")
        
        # Exit with error code for cron
        sys.exit(1)

if __name__ == "__main__":
    main()
