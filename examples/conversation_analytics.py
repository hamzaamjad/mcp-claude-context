#!/usr/bin/env python3
"""
Analyze Claude.ai conversation patterns and statistics.
This script provides insights into your conversation history.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configuration
SESSION_KEY = os.getenv("CLAUDE_SESSION_KEY", "your-session-key-here")
ORG_ID = os.getenv("CLAUDE_ORG_ID", "your-org-id-here")

class ConversationAnalyzer:
    """Analyze conversation patterns and statistics."""
    
    def __init__(self, conversations):
        self.conversations = conversations
        
    def analyze_time_patterns(self):
        """Analyze when conversations are created and updated."""
        created_by_hour = defaultdict(int)
        created_by_day = defaultdict(int)
        updated_by_day = defaultdict(int)
        
        for conv in self.conversations:
            if conv.get('created_at'):
                created = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00'))
                created_by_hour[created.hour] += 1
                created_by_day[created.strftime('%A')] += 1
            
            if conv.get('updated_at'):
                updated = datetime.fromisoformat(conv['updated_at'].replace('Z', '+00:00'))
                updated_by_day[updated.strftime('%A')] += 1
        
        return {
            'by_hour': dict(created_by_hour),
            'by_day': dict(created_by_day),
            'updated_by_day': dict(updated_by_day)
        }
    
    def analyze_topics(self):
        """Analyze conversation topics based on titles."""
        word_freq = Counter()
        topic_categories = defaultdict(list)
        
        # Common topic keywords
        categories = {
            'coding': ['code', 'python', 'javascript', 'api', 'function', 'debug', 'error', 'implementation'],
            'ai_ml': ['model', 'llm', 'ai', 'ml', 'neural', 'training', 'dataset', 'agent'],
            'project': ['project', 'mirror', 'build', 'development', 'setup', 'architecture'],
            'research': ['research', 'paper', 'study', 'analysis', 'theory'],
            'system': ['system', 'server', 'infrastructure', 'deployment', 'configuration']
        }
        
        for conv in self.conversations:
            name = conv.get('name', '').lower()
            if not name:
                continue
                
            # Word frequency
            words = name.split()
            word_freq.update(words)
            
            # Categorize
            for category, keywords in categories.items():
                if any(keyword in name for keyword in keywords):
                    topic_categories[category].append(conv['name'])
        
        return {
            'word_frequency': dict(word_freq.most_common(20)),
            'categories': {k: len(v) for k, v in topic_categories.items()},
            'category_examples': {k: v[:3] for k, v in topic_categories.items()}
        }
    
    def analyze_activity(self):
        """Analyze conversation activity over time."""
        now = datetime.now(tz=datetime.now().astimezone().tzinfo)
        
        # Time-based groupings
        last_24h = 0
        last_week = 0
        last_month = 0
        last_3_months = 0
        
        # Activity timeline
        activity_by_month = defaultdict(int)
        
        for conv in self.conversations:
            if conv.get('updated_at'):
                updated = datetime.fromisoformat(conv['updated_at'].replace('Z', '+00:00'))
                diff = now - updated
                
                if diff < timedelta(days=1):
                    last_24h += 1
                if diff < timedelta(days=7):
                    last_week += 1
                if diff < timedelta(days=30):
                    last_month += 1
                if diff < timedelta(days=90):
                    last_3_months += 1
                
                # Monthly activity
                month_key = updated.strftime('%Y-%m')
                activity_by_month[month_key] += 1
        
        return {
            'recent_activity': {
                'last_24_hours': last_24h,
                'last_week': last_week,
                'last_month': last_month,
                'last_3_months': last_3_months
            },
            'monthly_activity': dict(sorted(activity_by_month.items())[-12:])  # Last 12 months
        }
    
    def get_summary_stats(self):
        """Get overall summary statistics."""
        total = len(self.conversations)
        named = sum(1 for c in self.conversations if c.get('name'))
        starred = sum(1 for c in self.conversations if c.get('is_starred'))
        
        # Model usage
        model_usage = Counter(c.get('model', 'unknown') for c in self.conversations)
        
        # Date range
        dates = []
        for conv in self.conversations:
            if conv.get('created_at'):
                dates.append(datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00')))
        
        date_range = {
            'earliest': min(dates).strftime('%Y-%m-%d') if dates else 'N/A',
            'latest': max(dates).strftime('%Y-%m-%d') if dates else 'N/A'
        }
        
        return {
            'total_conversations': total,
            'named_conversations': named,
            'unnamed_conversations': total - named,
            'starred_conversations': starred,
            'model_usage': dict(model_usage),
            'date_range': date_range
        }

async def analyze_conversations():
    """Analyze conversations using the MCP server."""
    
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
            
            data = json.loads(result[0].text)
            
            if data["status"] != "success":
                print(f"❌ Error: {data.get('error', 'Unknown error')}")
                return
            
            conversations = data['conversations']
            print(f"✅ Analyzing {len(conversations)} conversations...\n")
            
            # Initialize analyzer
            analyzer = ConversationAnalyzer(conversations)
            
            # Summary statistics
            print("📊 SUMMARY STATISTICS")
            print("=" * 50)
            stats = analyzer.get_summary_stats()
            for key, value in stats.items():
                if isinstance(value, dict):
                    print(f"\n{key.replace('_', ' ').title()}:")
                    for k, v in value.items():
                        print(f"  {k}: {v}")
                else:
                    print(f"{key.replace('_', ' ').title()}: {value}")
            
            # Time patterns
            print("\n\n⏰ TIME PATTERNS")
            print("=" * 50)
            time_patterns = analyzer.analyze_time_patterns()
            
            print("\nMost active hours (24h format):")
            sorted_hours = sorted(time_patterns['by_hour'].items(), key=lambda x: x[1], reverse=True)[:5]
            for hour, count in sorted_hours:
                print(f"  {hour:02d}:00 - {count} conversations")
            
            print("\nActivity by day of week:")
            for day, count in sorted(time_patterns['by_day'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {day}: {count} conversations")
            
            # Topic analysis
            print("\n\n💭 TOPIC ANALYSIS")
            print("=" * 50)
            topics = analyzer.analyze_topics()
            
            print("\nMost common words in titles:")
            for word, count in list(topics['word_frequency'].items())[:10]:
                print(f"  {word}: {count}")
            
            print("\nConversation categories:")
            for category, count in sorted(topics['categories'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {category}: {count} conversations")
                if topics['category_examples'][category]:
                    print(f"    Examples: {', '.join(topics['category_examples'][category][:2])}")
            
            # Activity analysis
            print("\n\n📈 ACTIVITY ANALYSIS")
            print("=" * 50)
            activity = analyzer.analyze_activity()
            
            print("\nRecent activity:")
            for period, count in activity['recent_activity'].items():
                print(f"  {period.replace('_', ' ').title()}: {count} conversations")
            
            print("\nMonthly activity (last 6 months):")
            monthly = list(activity['monthly_activity'].items())[-6:]
            for month, count in monthly:
                bar = '█' * min(count, 50)
                print(f"  {month}: {bar} ({count})")
            
            # Search for specific patterns
            print("\n\n🔍 SPECIFIC SEARCHES")
            print("=" * 50)
            
            # Search for Mirror project
            mirror_result = await session.call_tool(
                "search_conversations",
                arguments={
                    "session_key": SESSION_KEY,
                    "org_id": ORG_ID,
                    "query": "Mirror"
                }
            )
            
            mirror_data = json.loads(mirror_result[0].text)
            if mirror_data["status"] == "success":
                print(f"\nMirror Project conversations: {mirror_data['count']}")
                for conv in mirror_data['results'][:3]:
                    print(f"  - {conv['name']}")

def main():
    """Main entry point."""
    print("Claude.ai Conversation Analytics")
    print("=" * 40)
    
    if SESSION_KEY == "your-session-key-here":
        print("\n⚠️  Please set your credentials:")
        print("export CLAUDE_SESSION_KEY='your-actual-session-key'")
        print("export CLAUDE_ORG_ID='your-actual-org-id'")
        return
    
    try:
        asyncio.run(analyze_conversations())
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
