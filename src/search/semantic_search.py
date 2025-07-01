"""
Semantic search implementation using sentence transformers
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import json
import pickle
from pathlib import Path
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SemanticSearch:
    """Semantic search using sentence transformers and FAISS"""
    
    def __init__(
        self, 
        model_name: str = 'all-MiniLM-L6-v2',
        index_path: Optional[str] = None,
        db_path: str = "data/db/conversations.db"
    ):
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        # Paths
        self.index_path = Path(index_path) if index_path else Path("data/search_index")
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Database connection
        self.engine = create_engine(f'sqlite:///{db_path}')
        
        # FAISS indexes
        self.conversation_index = None
        self.message_index = None
        
        # Mappings
        self.conversation_id_map = []
        self.message_id_map = []
        
        # Load or create indexes
        self._load_or_create_indexes()
    
    def _load_or_create_indexes(self):
        """Load existing indexes or create new ones"""
        conv_index_file = self.index_path / "conversation_index.faiss"
        msg_index_file = self.index_path / "message_index.faiss"
        conv_map_file = self.index_path / "conversation_map.pkl"
        msg_map_file = self.index_path / "message_map.pkl"
        
        if all(f.exists() for f in [conv_index_file, msg_index_file, conv_map_file, msg_map_file]):
            # Load existing indexes
            logger.info("Loading existing semantic search indexes...")
            self.conversation_index = faiss.read_index(str(conv_index_file))
            self.message_index = faiss.read_index(str(msg_index_file))
            
            with open(conv_map_file, 'rb') as f:
                self.conversation_id_map = pickle.load(f)
            
            with open(msg_map_file, 'rb') as f:
                self.message_id_map = pickle.load(f)
        else:
            # Create new indexes
            logger.info("Creating new semantic search indexes...")
            self.conversation_index = faiss.IndexFlatL2(self.embedding_dim)
            self.message_index = faiss.IndexFlatL2(self.embedding_dim)
            self.build_indexes()
    
    def build_indexes(self):
        """Build semantic search indexes from database"""
        logger.info("Building semantic search indexes...")
        
        with self.engine.connect() as conn:
            # Index conversations
            conv_results = conn.execute(
                text("SELECT id, title, search_vector FROM conversations")
            ).fetchall()
            
            if conv_results:
                conv_texts = []
                conv_ids = []
                
                for row in conv_results:
                    conv_ids.append(row[0])
                    # Combine title and search vector for embedding
                    combined_text = f"{row[1]} {row[2] or ''}"
                    conv_texts.append(combined_text)
                
                # Create embeddings
                conv_embeddings = self.model.encode(conv_texts, show_progress_bar=True)
                
                # Add to index
                self.conversation_index.add(conv_embeddings.astype('float32'))
                self.conversation_id_map = conv_ids
            
            # Index messages
            msg_results = conn.execute(
                text("""
                    SELECT m.id, m.conversation_id, m.content, c.title
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                """)
            ).fetchall()
            
            if msg_results:
                msg_texts = []
                msg_data = []
                
                for row in msg_results:
                    msg_data.append({
                        'id': row[0],
                        'conversation_id': row[1],
                        'conversation_title': row[3]
                    })
                    msg_texts.append(row[2])
                
                # Create embeddings in batches
                batch_size = 1000
                for i in range(0, len(msg_texts), batch_size):
                    batch_texts = msg_texts[i:i+batch_size]
                    batch_embeddings = self.model.encode(batch_texts, show_progress_bar=True)
                    self.message_index.add(batch_embeddings.astype('float32'))
                
                self.message_id_map = msg_data
        
        # Save indexes
        self.save_indexes()
        logger.info("Semantic search indexes built successfully")
    
    def save_indexes(self):
        """Save indexes to disk"""
        faiss.write_index(self.conversation_index, str(self.index_path / "conversation_index.faiss"))
        faiss.write_index(self.message_index, str(self.index_path / "message_index.faiss"))
        
        with open(self.index_path / "conversation_map.pkl", 'wb') as f:
            pickle.dump(self.conversation_id_map, f)
        
        with open(self.index_path / "message_map.pkl", 'wb') as f:
            pickle.dump(self.message_id_map, f)
    
    def search_conversations(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.7
    ) -> List[Tuple[Dict, float]]:
        """Search conversations using semantic similarity"""
        
        # Check if index is empty
        if self.conversation_index.ntotal == 0:
            return []
        
        # Encode query
        query_embedding = self.model.encode([query])
        
        # Search
        distances, indices = self.conversation_index.search(
            query_embedding.astype('float32'), 
            min(top_k, self.conversation_index.ntotal)
        )
        
        # Get results
        results = []
        with self.engine.connect() as conn:
            for idx, distance in zip(indices[0], distances[0]):
                if idx < len(self.conversation_id_map):
                    # Convert L2 distance to similarity score
                    similarity = 1 / (1 + distance)
                    
                    if similarity >= threshold:
                        conv_id = self.conversation_id_map[idx]
                        conv_data = conn.execute(
                            text("SELECT * FROM conversations WHERE id = :id"),
                            {"id": conv_id}
                        ).fetchone()
                        
                        if conv_data:
                            results.append((dict(conv_data), similarity))
        
        return results
    
    def search_messages(
        self,
        query: str,
        top_k: int = 20,
        threshold: float = 0.6,
        conversation_id: Optional[str] = None
    ) -> List[Tuple[Dict, float]]:
        """Search messages using semantic similarity"""
        
        # Check if index is empty
        if self.message_index.ntotal == 0:
            return []
        
        # Encode query
        query_embedding = self.model.encode([query])
        
        # Search more if filtering by conversation
        search_k = top_k * 5 if conversation_id else top_k
        
        # Search
        distances, indices = self.message_index.search(
            query_embedding.astype('float32'),
            min(search_k, self.message_index.ntotal)
        )
        
        # Get results
        results = []
        seen_messages = set()
        
        with self.engine.connect() as conn:
            for idx, distance in zip(indices[0], distances[0]):
                if idx < len(self.message_id_map):
                    msg_data = self.message_id_map[idx]
                    
                    # Filter by conversation if specified
                    if conversation_id and msg_data['conversation_id'] != conversation_id:
                        continue
                    
                    msg_id = msg_data['id']
                    if msg_id in seen_messages:
                        continue
                    
                    seen_messages.add(msg_id)
                    
                    # Convert L2 distance to similarity score
                    similarity = 1 / (1 + distance)
                    
                    if similarity >= threshold:
                        # Get full message data
                        msg_result = conn.execute(
                            text("""
                                SELECT 
                                    m.*,
                                    c.title as conversation_title
                                FROM messages m
                                JOIN conversations c ON m.conversation_id = c.id
                                WHERE m.id = :id
                            """),
                            {"id": msg_id}
                        ).fetchone()
                        
                        if msg_result:
                            result_dict = dict(msg_result)
                            results.append((result_dict, similarity))
                            
                            if len(results) >= top_k:
                                break
        
        return results
    
    def find_similar_conversations(
        self,
        conversation_id: str,
        top_k: int = 5
    ) -> List[Tuple[Dict, float]]:
        """Find conversations similar to a given conversation"""
        
        # Get the conversation's embedding
        try:
            idx = self.conversation_id_map.index(conversation_id)
        except ValueError:
            logger.error(f"Conversation {conversation_id} not found in index")
            return []
        
        # Get embedding from index
        embedding = self.conversation_index.reconstruct(idx).reshape(1, -1)
        
        # Search for similar (excluding self)
        distances, indices = self.conversation_index.search(
            embedding.astype('float32'),
            top_k + 1  # +1 to exclude self
        )
        
        # Get results
        results = []
        with self.engine.connect() as conn:
            for idx, distance in zip(indices[0], distances[0]):
                if idx < len(self.conversation_id_map):
                    similar_id = self.conversation_id_map[idx]
                    
                    # Skip self
                    if similar_id == conversation_id:
                        continue
                    
                    conv_data = conn.execute(
                        text("SELECT * FROM conversations WHERE id = :id"),
                        {"id": similar_id}
                    ).fetchone()
                    
                    if conv_data:
                        similarity = 1 / (1 + distance)
                        results.append((dict(conv_data), similarity))
        
        return results[:top_k]
    
    def update_conversation_embedding(self, conversation_id: str, title: str, content: str):
        """Update embedding for a single conversation"""
        
        # Create new embedding
        text = f"{title} {content}"
        embedding = self.model.encode([text])[0]
        
        # Update in index
        try:
            idx = self.conversation_id_map.index(conversation_id)
            # FAISS doesn't support in-place updates, so we need to rebuild
            # In production, you might use a more sophisticated approach
            self.build_indexes()
        except ValueError:
            # New conversation, add to index
            self.conversation_index.add(embedding.reshape(1, -1).astype('float32'))
            self.conversation_id_map.append(conversation_id)
            self.save_indexes()
    
    def update_message_embedding(self, message_id: str, content: str):
        """Update embedding for a single message"""
        
        # Create new embedding
        embedding = self.model.encode([content])[0]
        
        # For now, rebuild index (in production, use incremental updates)
        self.build_indexes()
    
    def get_embedding_stats(self) -> Dict:
        """Get statistics about the semantic search indexes"""
        return {
            'model': self.model._model_name,
            'embedding_dimension': self.embedding_dim,
            'conversations_indexed': self.conversation_index.ntotal if self.conversation_index else 0,
            'messages_indexed': self.message_index.ntotal if self.message_index else 0,
            'index_size_mb': {
                'conversations': self._get_index_size('conversation_index.faiss'),
                'messages': self._get_index_size('message_index.faiss')
            }
        }
    
    def _get_index_size(self, filename: str) -> float:
        """Get size of index file in MB"""
        file_path = self.index_path / filename
        if file_path.exists():
            return file_path.stat().st_size / (1024 * 1024)
        return 0.0
