"""
Unified search engine combining text and semantic search
"""

from typing import List, Dict, Optional, Tuple, Literal
from .text_search import TextSearch
from .semantic_search import SemanticSearch
import logging

logger = logging.getLogger(__name__)


class UnifiedSearchEngine:
    """Combines text and semantic search for comprehensive results"""
    
    def __init__(
        self,
        db_path: str = "data/db/conversations.db",
        semantic_model: str = 'all-MiniLM-L6-v2'
    ):
        self.text_search = TextSearch(db_path)
        self.semantic_search = SemanticSearch(semantic_model, db_path=db_path)
        self.db_path = db_path
    
    def search(
        self,
        query: str,
        search_type: Literal['text', 'semantic', 'hybrid'] = 'hybrid',
        target: Literal['conversations', 'messages', 'both'] = 'both',
        limit: int = 20,
        conversation_id: Optional[str] = None
    ) -> Dict[str, List[Dict]]:
        """
        Unified search interface
        
        Args:
            query: Search query
            search_type: Type of search to perform
            target: What to search (conversations, messages, or both)
            limit: Maximum results per category
            conversation_id: Optional filter for specific conversation
        
        Returns:
            Dictionary with 'conversations' and/or 'messages' results
        """
        
        results = {}
        
        if target in ['conversations', 'both']:
            results['conversations'] = self._search_conversations(
                query, search_type, limit
            )
        
        if target in ['messages', 'both']:
            results['messages'] = self._search_messages(
                query, search_type, limit, conversation_id
            )
        
        return results
    
    def _search_conversations(
        self,
        query: str,
        search_type: str,
        limit: int
    ) -> List[Dict]:
        """Search conversations using specified method"""
        
        if search_type == 'text':
            return self.text_search.search_conversations(query, limit)
        
        elif search_type == 'semantic':
            semantic_results = self.semantic_search.search_conversations(query, limit)
            # Convert to standard format
            return [
                {**conv, 'score': score, 'search_type': 'semantic'}
                for conv, score in semantic_results
            ]
        
        else:  # hybrid
            # Get results from both methods
            text_results = self.text_search.search_conversations(query, limit // 2)
            semantic_results = self.semantic_search.search_conversations(query, limit // 2)
            
            # Mark search type
            for r in text_results:
                r['search_type'] = 'text'
            
            semantic_formatted = [
                {**conv, 'score': score, 'search_type': 'semantic'}
                for conv, score in semantic_results
            ]
            
            # Merge and deduplicate
            return self._merge_results(text_results, semantic_formatted, limit)
    
    def _search_messages(
        self,
        query: str,
        search_type: str,
        limit: int,
        conversation_id: Optional[str] = None
    ) -> List[Dict]:
        """Search messages using specified method"""
        
        if search_type == 'text':
            return self.text_search.search_messages(query, conversation_id, limit)
        
        elif search_type == 'semantic':
            semantic_results = self.semantic_search.search_messages(
                query, limit, conversation_id=conversation_id
            )
            # Convert to standard format
            return [
                {**msg, 'score': score, 'search_type': 'semantic'}
                for msg, score in semantic_results
            ]
        
        else:  # hybrid
            # Get results from both methods
            text_results = self.text_search.search_messages(
                query, conversation_id, limit // 2
            )
            semantic_results = self.semantic_search.search_messages(
                query, limit // 2, conversation_id=conversation_id
            )
            
            # Mark search type
            for r in text_results:
                r['search_type'] = 'text'
            
            semantic_formatted = [
                {**msg, 'score': score, 'search_type': 'semantic'}
                for msg, score in semantic_results
            ]
            
            # Merge and deduplicate
            return self._merge_results(text_results, semantic_formatted, limit)
    
    def _merge_results(
        self,
        text_results: List[Dict],
        semantic_results: List[Dict],
        limit: int
    ) -> List[Dict]:
        """Merge and deduplicate results from both search methods"""
        
        # Create a dictionary to track best score for each item
        merged = {}
        
        # Process text results
        for result in text_results:
            item_id = result.get('id')
            if item_id:
                merged[item_id] = result
        
        # Process semantic results
        for result in semantic_results:
            item_id = result.get('id')
            if item_id:
                if item_id in merged:
                    # Keep the one with higher score
                    if result.get('score', 0) > merged[item_id].get('score', 0):
                        merged[item_id] = result
                    else:
                        # Mark as found by both methods
                        merged[item_id]['search_type'] = 'both'
                else:
                    merged[item_id] = result
        
        # Sort by score and return top results
        sorted_results = sorted(
            merged.values(),
            key=lambda x: x.get('score', 0),
            reverse=True
        )
        
        return sorted_results[:limit]
    
    def find_related(
        self,
        conversation_id: str,
        method: Literal['semantic', 'tags', 'both'] = 'both',
        limit: int = 10
    ) -> List[Dict]:
        """Find related conversations"""
        
        results = []
        
        if method in ['semantic', 'both']:
            semantic_results = self.semantic_search.find_similar_conversations(
                conversation_id, limit
            )
            results.extend([
                {**conv, 'score': score, 'relation_type': 'semantic'}
                for conv, score in semantic_results
            ])
        
        if method in ['tags', 'both']:
            # Get conversation tags
            from sqlalchemy import create_engine, text
            engine = create_engine(f'sqlite:///{self.db_path}')
            
            with engine.connect() as conn:
                # Get tags for the source conversation
                source_result = conn.execute(
                    text("SELECT tags FROM conversations WHERE id = :id"),
                    {"id": conversation_id}
                ).fetchone()
                
                if source_result and source_result[0]:
                    source_tags = source_result[0]
                    
                    # Find conversations with similar tags
                    tag_results = conn.execute(
                        text("""
                            SELECT *,
                                (SELECT COUNT(*) FROM json_each(tags) 
                                 WHERE value IN (SELECT value FROM json_each(:tags))) as common_tags
                            FROM conversations
                            WHERE id != :id
                            AND common_tags > 0
                            ORDER BY common_tags DESC
                            LIMIT :limit
                        """),
                        {"id": conversation_id, "tags": source_tags, "limit": limit}
                    ).fetchall()
                    
                    for row in tag_results:
                        result = dict(row._mapping)
                        result['relation_type'] = 'tags'
                        result['score'] = result['common_tags'] / len(source_tags)
                        results.append(result)
        
        # Sort by score and deduplicate
        seen_ids = set()
        unique_results = []
        
        for result in sorted(results, key=lambda x: x.get('score', 0), reverse=True):
            if result['id'] not in seen_ids:
                seen_ids.add(result['id'])
                unique_results.append(result)
                
                if len(unique_results) >= limit:
                    break
        
        return unique_results
    
    def get_search_stats(self) -> Dict:
        """Get statistics about search capabilities"""
        
        semantic_stats = self.semantic_search.get_embedding_stats()
        
        from sqlalchemy import create_engine, text
        engine = create_engine(f'sqlite:///{self.db_path}')
        
        with engine.connect() as conn:
            conv_count = conn.execute(
                text("SELECT COUNT(*) FROM conversations")
            ).scalar()
            
            msg_count = conn.execute(
                text("SELECT COUNT(*) FROM messages")
            ).scalar()
            
            # Check FTS tables
            fts_conv_count = conn.execute(
                text("SELECT COUNT(*) FROM conversations_fts")
            ).scalar()
            
            fts_msg_count = conn.execute(
                text("SELECT COUNT(*) FROM messages_fts")
            ).scalar()
        
        return {
            'database': {
                'conversations': conv_count,
                'messages': msg_count
            },
            'text_search': {
                'conversations_indexed': fts_conv_count,
                'messages_indexed': fts_msg_count,
                'engine': 'SQLite FTS5'
            },
            'semantic_search': semantic_stats
        }
    
    def rebuild_indexes(self):
        """Rebuild all search indexes"""
        logger.info("Rebuilding all search indexes...")
        
        # Rebuild text search index
        self.text_search.rebuild_search_index()
        
        # Rebuild semantic search index
        self.semantic_search.build_indexes()
        
        logger.info("All search indexes rebuilt successfully")
    
    def optimize_indexes(self):
        """Optimize all search indexes"""
        logger.info("Optimizing search indexes...")
        
        # Optimize text search
        self.text_search.optimize_index()
        
        # Semantic search optimization happens during save
        self.semantic_search.save_indexes()
        
        logger.info("Search indexes optimized")
