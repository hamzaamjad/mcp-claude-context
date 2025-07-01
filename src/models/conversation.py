"""
SQLAlchemy models for conversation data storage
"""

from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON, Integer, Float, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import datetime

Base = declarative_base()


class Conversation(Base):
    """Model for storing conversation metadata"""
    __tablename__ = 'conversations'
    
    # Primary key
    id = Column(String, primary_key=True)
    
    # Basic metadata
    title = Column(String, nullable=False, default='Untitled')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)
    extracted_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Conversation details
    model = Column(String, default='unknown')
    message_count = Column(Integer, default=0)
    
    # Additional metadata
    tags = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    # Search optimization
    search_vector = Column(Text)  # For full-text search
    embedding = Column(JSON)      # For semantic search vectors
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_conversations_created_at', 'created_at'),
        Index('idx_conversations_updated_at', 'updated_at'),
        Index('idx_conversations_model', 'model'),
    )
    
    def to_dict(self):
        """Convert conversation to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
            'model': self.model,
            'message_count': self.message_count,
            'tags': self.tags or [],
            'metadata': self.extra_data or {}
        }


class Message(Base):
    """Model for storing individual messages"""
    __tablename__ = 'messages'
    
    # Primary key
    id = Column(String, primary_key=True)
    
    # Foreign key to conversation
    conversation_id = Column(String, nullable=False)
    
    # Message details
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime)
    index = Column(Integer, default=0)  # Position in conversation
    
    # Additional metadata
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    # Search optimization
    search_vector = Column(Text)  # For full-text search
    embedding = Column(JSON)      # For semantic search vectors
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_messages_conversation_id', 'conversation_id'),
        Index('idx_messages_created_at', 'created_at'),
        Index('idx_messages_role', 'role'),
        Index('idx_messages_conversation_index', 'conversation_id', 'index'),
    )
    
    def to_dict(self):
        """Convert message to dictionary"""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'index': self.index,
            'metadata': self.extra_data or {}
        }


class SearchCache(Base):
    """Model for caching search results"""
    __tablename__ = 'search_cache'
    
    id = Column(Integer, primary_key=True)
    query = Column(String, nullable=False, unique=True)
    results = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_search_cache_query', 'query'),
        Index('idx_search_cache_expires', 'expires_at'),
    )


# Database initialization helper
def init_database(db_path: str = "data/db/conversations.db"):
    """Initialize database with tables and indexes"""
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Create tables
    Base.metadata.create_all(engine)
    
    # Enable SQLite optimizations
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))  # Write-Ahead Logging
        conn.execute(text("PRAGMA synchronous=NORMAL"))  # Faster writes
        conn.execute(text("PRAGMA cache_size=10000"))  # Larger cache
        conn.execute(text("PRAGMA temp_store=MEMORY"))  # Use memory for temp tables
        
        # Create FTS5 virtual table for full-text search
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
                id UNINDEXED,
                title,
                content,
                tokenize='porter unicode61'
            )
        """))
        
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                id UNINDEXED,
                conversation_id UNINDEXED,
                content,
                tokenize='porter unicode61'
            )
        """))
        
        # Create triggers to keep FTS tables in sync
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS conversations_ai AFTER INSERT ON conversations
            BEGIN
                INSERT INTO conversations_fts(id, title, content)
                VALUES (new.id, new.title, new.search_vector);
            END
        """))
        
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS conversations_au AFTER UPDATE ON conversations
            BEGIN
                UPDATE conversations_fts 
                SET title = new.title, content = new.search_vector
                WHERE id = new.id;
            END
        """))
        
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS conversations_ad AFTER DELETE ON conversations
            BEGIN
                DELETE FROM conversations_fts WHERE id = old.id;
            END
        """))
        
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages
            BEGIN
                INSERT INTO messages_fts(id, conversation_id, content)
                VALUES (new.id, new.conversation_id, new.content);
            END
        """))
        
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages
            BEGIN
                UPDATE messages_fts 
                SET content = new.content
                WHERE id = new.id;
            END
        """))
        
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages
            BEGIN
                DELETE FROM messages_fts WHERE id = old.id;
            END
        """))
        
        conn.commit()
    
    return engine
