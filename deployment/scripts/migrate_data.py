#!/usr/bin/env python3
"""
Migration script to convert JSON conversation files to SQLite database
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.models.conversation import Base, Conversation, Message

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataMigrator:
    def __init__(self, json_dir: str = "extracted_messages", db_path: str = "data/db/conversations.db"):
        self.json_dir = Path(json_dir)
        self.db_path = Path(db_path)
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup database
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def migrate(self):
        """Migrate all JSON files to database"""
        session = self.Session()
        
        try:
            # Get all JSON files
            json_files = list(self.json_dir.glob("*.json"))
            
            if not json_files:
                logger.info("No JSON files found to migrate")
                return
            
            logger.info(f"Found {len(json_files)} conversations to migrate")
            
            # Track progress
            migrated = 0
            skipped = 0
            errors = 0
            
            for json_file in json_files:
                try:
                    # Check if already migrated
                    conv_id = json_file.stem
                    existing = session.query(Conversation).filter_by(id=conv_id).first()
                    
                    if existing:
                        logger.debug(f"Skipping {json_file.name} - already migrated")
                        skipped += 1
                        continue
                    
                    # Load JSON data
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Create conversation
                    conversation = self._create_conversation(data)
                    session.add(conversation)
                    
                    # Create messages
                    for msg_data in data.get('messages', []):
                        message = self._create_message(msg_data, conv_id)
                        if message:
                            session.add(message)
                    
                    # Commit after each conversation
                    session.commit()
                    migrated += 1
                    
                    if migrated % 10 == 0:
                        logger.info(f"Progress: {migrated}/{len(json_files)} migrated")
                
                except Exception as e:
                    logger.error(f"Error migrating {json_file.name}: {e}")
                    session.rollback()
                    errors += 1
            
            # Final report
            logger.info(f"\nMigration complete:")
            logger.info(f"  Migrated: {migrated}")
            logger.info(f"  Skipped: {skipped}")
            logger.info(f"  Errors: {errors}")
            logger.info(f"  Total: {len(json_files)}")
            
            # Create indexes for better performance
            self._create_indexes(session)
            
        finally:
            session.close()
    
    def _create_conversation(self, data: dict) -> Conversation:
        """Create Conversation object from JSON data"""
        return Conversation(
            id=data.get('uuid', data.get('id')),
            title=data.get('name', data.get('title', 'Untitled')),
            created_at=self._parse_datetime(data.get('created_at')),
            updated_at=self._parse_datetime(data.get('updated_at')),
            extracted_at=datetime.utcnow(),
            model=data.get('model', 'unknown'),
            message_count=len(data.get('messages', [])),
            tags=data.get('tags', []),
            metadata={
                'original_file': data.get('original_file'),
                'extracted_by': data.get('extracted_by', 'migration')
            }
        )
    
    def _create_message(self, msg_data: dict, conversation_id: str) -> Message:
        """Create Message object from JSON data"""
        try:
            return Message(
                id=msg_data.get('uuid', msg_data.get('id')),
                conversation_id=conversation_id,
                role=msg_data.get('sender', msg_data.get('role', 'unknown')),
                content=msg_data.get('text', msg_data.get('content', '')),
                created_at=self._parse_datetime(msg_data.get('created_at')),
                index=msg_data.get('index', 0),
                metadata={
                    'attachments': msg_data.get('attachments', []),
                    'citations': msg_data.get('citations', [])
                }
            )
        except Exception as e:
            logger.warning(f"Error creating message: {e}")
            return None
    
    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime string to datetime object"""
        if not dt_str:
            return datetime.utcnow()
        
        # Try different datetime formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except:
                continue
        
        # If all fail, return current time
        logger.warning(f"Could not parse datetime: {dt_str}")
        return datetime.utcnow()
    
    def _create_indexes(self, session):
        """Create database indexes for better performance"""
        logger.info("Creating database indexes...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role)"
        ]
        
        for index_sql in indexes:
            session.execute(text(index_sql))
        
        session.commit()
        logger.info("Indexes created successfully")
    
    def verify_migration(self):
        """Verify migration was successful"""
        session = self.Session()
        
        try:
            conv_count = session.query(Conversation).count()
            msg_count = session.query(Message).count()
            
            logger.info(f"\nDatabase contents:")
            logger.info(f"  Conversations: {conv_count}")
            logger.info(f"  Messages: {msg_count}")
            
            # Sample query
            recent = session.query(Conversation)\
                .order_by(Conversation.created_at.desc())\
                .limit(5)\
                .all()
            
            if recent:
                logger.info(f"\nMost recent conversations:")
                for conv in recent:
                    logger.info(f"  - {conv.title[:50]}... ({conv.created_at})")
        
        finally:
            session.close()


def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate JSON conversations to SQLite database")
    parser.add_argument("--json-dir", default="extracted_messages", help="Directory containing JSON files")
    parser.add_argument("--db-path", default="data/db/conversations.db", help="Path to SQLite database")
    parser.add_argument("--verify", action="store_true", help="Verify migration after completion")
    
    args = parser.parse_args()
    
    # Run migration
    migrator = DataMigrator(args.json_dir, args.db_path)
    migrator.migrate()
    
    if args.verify:
        migrator.verify_migration()


if __name__ == "__main__":
    main()
