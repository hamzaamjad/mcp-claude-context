"""
Text search implementation using SQLite FTS5
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class TextSearch:
    """Full-text search using SQLite FTS5"""
    
    def __init__(self, db_path: str = "data/db/conversations.db"):
        self.engine = create_engine(f'sqlite:///{db_path}')
        self._ensure_fts_tables()
    
    def _ensure_fts_tables(self):
        """Ensure FTS5 tables exist"""
        with self.engine.connect() as conn:
            # Check if FTS tables exist
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_fts'")
            )
            
            if not result.fetchall():
                logger.info("Creating FTS5 tables...")
                # These should already be created by the database init
                # but we'll ensure they exist
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
                
                conn.commit()
    
    def search_conversations(
        self, 
        query: str, 
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """Search conversations by title and content"""
        
        with self.engine.connect() as conn:
            # Search in conversations
            results = conn.execute(
                text("""
                    SELECT 
                        c.id,
                        c.title,
                        c.created_at,
                        c.updated_at,
                        c.model,
                        c.message_count,
                        c.tags,
                        snippet(conversations_fts, 2, '<mark>', '</mark>', '...', 32) as snippet,
                        rank as score
                    FROM conversations_fts
                    JOIN conversations c ON conversations_fts.id = c.id
                    WHERE conversations_fts MATCH :query
                    ORDER BY rank
                    LIMIT :limit OFFSET :offset
                """),
                {"query": query, "limit": limit, "offset": offset}
            ).fetchall()
            
            return [dict(row._mapping) for row in results]
    
    def search_messages(
        self, 
        query: str, 
        conversation_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Search messages by content"""
        
        with self.engine.connect() as conn:
            base_query = """
                SELECT 
                    m.id,
                    m.conversation_id,
                    m.role,
                    m.created_at,
                    m."index",
                    c.title as conversation_title,
                    snippet(messages_fts, 2, '<mark>', '</mark>', '...', 32) as snippet,
                    rank as score
                FROM messages_fts
                JOIN messages m ON messages_fts.id = m.id
                JOIN conversations c ON m.conversation_id = c.id
                WHERE messages_fts MATCH :query
            """
            
            params = {"query": query, "limit": limit, "offset": offset}
            
            if conversation_id:
                base_query += " AND m.conversation_id = :conversation_id"
                params["conversation_id"] = conversation_id
            
            base_query += " ORDER BY rank LIMIT :limit OFFSET :offset"
            
            results = conn.execute(text(base_query), params).fetchall()
            
            return [dict(row._mapping) for row in results]
    
    def get_search_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on prefix"""
        
        with self.engine.connect() as conn:
            # Get unique words from both conversations and messages
            results = conn.execute(
                text("""
                    SELECT DISTINCT term
                    FROM (
                        SELECT term FROM conversations_fts_vocab
                        WHERE term LIKE :prefix || '%'
                        UNION
                        SELECT term FROM messages_fts_vocab
                        WHERE term LIKE :prefix || '%'
                    )
                    ORDER BY term
                    LIMIT :limit
                """),
                {"prefix": prefix, "limit": limit}
            ).fetchall()
            
            return [row[0] for row in results]
    
    def search_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Search conversations within a date range"""
        
        with self.engine.connect() as conn:
            sql_parts = ["SELECT * FROM conversations WHERE 1=1"]
            params = {"limit": limit}
            
            if start_date:
                sql_parts.append("AND created_at >= :start_date")
                params["start_date"] = start_date
            
            if end_date:
                sql_parts.append("AND created_at <= :end_date")
                params["end_date"] = end_date
            
            if query:
                # Join with FTS table for text search
                sql_parts = [
                    "SELECT c.* FROM conversations c",
                    "JOIN conversations_fts ON c.id = conversations_fts.id",
                    "WHERE conversations_fts MATCH :query"
                ]
                params["query"] = query
                
                if start_date:
                    sql_parts.append("AND c.created_at >= :start_date")
                if end_date:
                    sql_parts.append("AND c.created_at <= :end_date")
            
            sql_parts.append("ORDER BY created_at DESC")
            sql_parts.append("LIMIT :limit")
            
            sql = " ".join(sql_parts)
            results = conn.execute(text(sql), params).fetchall()
            
            return [dict(row._mapping) for row in results]
    
    def get_conversation_context(
        self,
        conversation_id: str,
        message_index: int,
        context_size: int = 3
    ) -> Dict:
        """Get messages around a specific message for context"""
        
        with self.engine.connect() as conn:
            # Get the target message and surrounding messages
            results = conn.execute(
                text("""
                    SELECT 
                        id,
                        role,
                        content,
                        created_at,
                        "index"
                    FROM messages
                    WHERE conversation_id = :conversation_id
                    AND "index" BETWEEN :start_index AND :end_index
                    ORDER BY "index"
                """),
                {
                    "conversation_id": conversation_id,
                    "start_index": max(0, message_index - context_size),
                    "end_index": message_index + context_size
                }
            ).fetchall()
            
            messages = [dict(row._mapping) for row in results]
            
            # Get conversation details
            conv_result = conn.execute(
                text("SELECT * FROM conversations WHERE id = :id"),
                {"id": conversation_id}
            ).fetchone()
            
            return {
                "conversation": dict(conv_result._mapping) if conv_result else None,
                "messages": messages,
                "target_index": message_index
            }
    
    def rebuild_search_index(self):
        """Rebuild the FTS index from scratch"""
        logger.info("Rebuilding search index...")
        
        with self.engine.connect() as conn:
            # Clear existing FTS data
            conn.execute(text("DELETE FROM conversations_fts"))
            conn.execute(text("DELETE FROM messages_fts"))
            
            # Rebuild conversations index
            conn.execute(text("""
                INSERT INTO conversations_fts (id, title, content)
                SELECT id, title, search_vector
                FROM conversations
            """))
            
            # Rebuild messages index
            conn.execute(text("""
                INSERT INTO messages_fts (id, conversation_id, content)
                SELECT id, conversation_id, content
                FROM messages
            """))
            
            conn.commit()
            
        logger.info("Search index rebuilt successfully")
    
    def optimize_index(self):
        """Optimize the FTS index for better performance"""
        with self.engine.connect() as conn:
            conn.execute(text("INSERT INTO conversations_fts(conversations_fts) VALUES('optimize')"))
            conn.execute(text("INSERT INTO messages_fts(messages_fts) VALUES('optimize')"))
            conn.commit()
