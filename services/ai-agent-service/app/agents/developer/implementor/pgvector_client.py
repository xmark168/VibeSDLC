# app/agents/developer/implementor/pgvector_client.py
"""
pgvector client for codebase indexing and semantic search
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class PgVectorClient:
    """
    Client for pgvector database operations.
    
    Handles codebase indexing, embedding generation, and semantic search
    for code snippets and documentation.
    """
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize pgvector client.
        
        Args:
            connection_string: PostgreSQL connection string with pgvector extension
        """
        self.connection_string = connection_string or os.getenv("PGVECTOR_CONNECTION_STRING")
        self.openai_client = None
        
        if not self.connection_string:
            logger.warning("No pgvector connection string provided. Using mock mode.")
            self.mock_mode = True
            self.mock_index = {}
        else:
            self.mock_mode = False
            
        # Initialize OpenAI client for embeddings
        if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            self.openai_client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL")
            )
        else:
            logger.warning("OpenAI client not available. Using mock embeddings.")
    
    def initialize_database(self) -> bool:
        """
        Initialize database with required tables and extensions.
        
        Returns:
            True if successful, False otherwise
        """
        if self.mock_mode:
            logger.info("Mock mode: Database initialization skipped")
            return True
            
        if not PSYCOPG2_AVAILABLE:
            logger.error("psycopg2 not available. Cannot initialize database.")
            return False
        
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Enable pgvector extension
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    
                    # Create code_snippets table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS code_snippets (
                            id SERIAL PRIMARY KEY,
                            file_path TEXT NOT NULL,
                            snippet_type TEXT NOT NULL,
                            snippet_name TEXT,
                            content TEXT NOT NULL,
                            content_hash TEXT UNIQUE NOT NULL,
                            start_line INTEGER,
                            end_line INTEGER,
                            language TEXT,
                            embedding vector(1536),
                            metadata JSONB,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Create index on embedding for similarity search
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS code_snippets_embedding_idx 
                        ON code_snippets USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = 100);
                    """)
                    
                    # Create index on content hash for deduplication
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS code_snippets_hash_idx 
                        ON code_snippets (content_hash);
                    """)
                    
                    conn.commit()
                    logger.info("Database initialized successfully")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using OpenAI API.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding, or None if failed
        """
        if not self.openai_client:
            # Return mock embedding for testing
            return [0.1] * 1536
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text[:8000]  # Limit input length
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def index_code_snippet(
        self,
        file_path: str,
        snippet_type: str,
        content: str,
        snippet_name: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        language: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Index a single code snippet.
        
        Args:
            file_path: Path to the source file
            snippet_type: Type of snippet (function, class, file, etc.)
            content: Code content
            snippet_name: Name of the snippet (function/class name)
            start_line: Starting line number
            end_line: Ending line number
            language: Programming language
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        # Generate content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        if self.mock_mode:
            # Store in mock index
            self.mock_index[content_hash] = {
                "file_path": file_path,
                "snippet_type": snippet_type,
                "snippet_name": snippet_name,
                "content": content,
                "start_line": start_line,
                "end_line": end_line,
                "language": language,
                "metadata": metadata or {}
            }
            return True
        
        # Generate embedding
        embedding = self.generate_embedding(content)
        if not embedding:
            logger.error(f"Failed to generate embedding for {file_path}")
            return False
        
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Check if snippet already exists
                    cur.execute(
                        "SELECT id FROM code_snippets WHERE content_hash = %s",
                        (content_hash,)
                    )
                    
                    if cur.fetchone():
                        logger.debug(f"Snippet already indexed: {content_hash}")
                        return True
                    
                    # Insert new snippet
                    cur.execute("""
                        INSERT INTO code_snippets 
                        (file_path, snippet_type, snippet_name, content, content_hash, 
                         start_line, end_line, language, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        file_path, snippet_type, snippet_name, content, content_hash,
                        start_line, end_line, language, embedding, json.dumps(metadata or {})
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to index snippet: {e}")
            return False
    
    def search_similar_code(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.7,
        language: Optional[str] = None,
        snippet_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar code snippets.
        
        Args:
            query: Search query
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)
            language: Filter by programming language
            snippet_type: Filter by snippet type
            
        Returns:
            List of similar code snippets with metadata
        """
        if self.mock_mode:
            # Mock search - return some sample results
            results = []
            for i, (hash_key, snippet) in enumerate(self.mock_index.items()):
                if i >= limit:
                    break
                    
                # Simple keyword matching for mock
                if any(word.lower() in snippet["content"].lower() for word in query.split()):
                    results.append({
                        "similarity": 0.8,  # Mock similarity
                        "file_path": snippet["file_path"],
                        "snippet_type": snippet["snippet_type"],
                        "snippet_name": snippet["snippet_name"],
                        "content": snippet["content"][:500] + "...",
                        "start_line": snippet["start_line"],
                        "end_line": snippet["end_line"],
                        "language": snippet["language"],
                        "metadata": snippet["metadata"]
                    })
            
            return results
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []
        
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Build WHERE clause
                    where_conditions = ["1 - (embedding <=> %s) >= %s"]
                    params = [query_embedding, similarity_threshold]
                    
                    if language:
                        where_conditions.append("language = %s")
                        params.append(language)
                    
                    if snippet_type:
                        where_conditions.append("snippet_type = %s")
                        params.append(snippet_type)
                    
                    where_clause = " AND ".join(where_conditions)
                    params.append(limit)
                    
                    # Execute similarity search
                    cur.execute(f"""
                        SELECT 
                            file_path,
                            snippet_type,
                            snippet_name,
                            content,
                            start_line,
                            end_line,
                            language,
                            metadata,
                            1 - (embedding <=> %s) as similarity
                        FROM code_snippets
                        WHERE {where_clause}
                        ORDER BY embedding <=> %s
                        LIMIT %s
                    """, [query_embedding] + params + [query_embedding])
                    
                    results = []
                    for row in cur.fetchall():
                        results.append({
                            "similarity": float(row["similarity"]),
                            "file_path": row["file_path"],
                            "snippet_type": row["snippet_type"],
                            "snippet_name": row["snippet_name"],
                            "content": row["content"][:500] + "..." if len(row["content"]) > 500 else row["content"],
                            "start_line": row["start_line"],
                            "end_line": row["end_line"],
                            "language": row["language"],
                            "metadata": row["metadata"]
                        })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Failed to search similar code: {e}")
            return []
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the indexed code.
        
        Returns:
            Dictionary with index statistics
        """
        if self.mock_mode:
            return {
                "total_snippets": len(self.mock_index),
                "languages": list(set(s.get("language") for s in self.mock_index.values() if s.get("language"))),
                "snippet_types": list(set(s.get("snippet_type") for s in self.mock_index.values())),
                "mock_mode": True
            }
        
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get total count
                    cur.execute("SELECT COUNT(*) as total FROM code_snippets")
                    total = cur.fetchone()["total"]
                    
                    # Get language distribution
                    cur.execute("""
                        SELECT language, COUNT(*) as count 
                        FROM code_snippets 
                        WHERE language IS NOT NULL 
                        GROUP BY language
                    """)
                    languages = {row["language"]: row["count"] for row in cur.fetchall()}
                    
                    # Get snippet type distribution
                    cur.execute("""
                        SELECT snippet_type, COUNT(*) as count 
                        FROM code_snippets 
                        GROUP BY snippet_type
                    """)
                    snippet_types = {row["snippet_type"]: row["count"] for row in cur.fetchall()}
                    
                    return {
                        "total_snippets": total,
                        "languages": languages,
                        "snippet_types": snippet_types,
                        "mock_mode": False
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {"error": str(e)}
    
    def clear_index(self, file_path: Optional[str] = None) -> bool:
        """
        Clear the index (all or for specific file).
        
        Args:
            file_path: If provided, only clear snippets from this file
            
        Returns:
            True if successful, False otherwise
        """
        if self.mock_mode:
            if file_path:
                # Remove snippets from specific file
                to_remove = [k for k, v in self.mock_index.items() if v["file_path"] == file_path]
                for key in to_remove:
                    del self.mock_index[key]
            else:
                # Clear all
                self.mock_index.clear()
            return True
        
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    if file_path:
                        cur.execute("DELETE FROM code_snippets WHERE file_path = %s", (file_path,))
                    else:
                        cur.execute("DELETE FROM code_snippets")
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            return False
